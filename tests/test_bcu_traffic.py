"""Offline contention, overload-recovery and cancellation integration tests."""
import concurrent.futures
from contextlib import closing
import http.client
import json
import sqlite3
import threading
import time
import unittest
from unittest.mock import Mock

import test_bcu_router as fixtures

bcu = fixtures.bcu


def eventually(predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("Timed out waiting for scheduler state")


class SchedulingTests(unittest.TestCase):
    def scheduler(self, **overrides):
        return bcu.Traffic(bcu.traffic_settings(overrides={"jitter": 0} | overrides))

    def test_cooling_model_does_not_block_another_model_or_native(self):
        traffic = self.scheduler(openrouter_concurrency=1)
        first = traffic.acquire("openrouter", "slow", time.monotonic() + 2, lambda: False)
        traffic.cooldown(first, 0.2)
        traffic.release(first)
        with concurrent.futures.ThreadPoolExecutor() as pool:
            waiting = pool.submit(traffic.acquire, "openrouter", "slow", time.monotonic() + 2, lambda: False)
            eventually(lambda: traffic.snapshot()["queued"]["openrouter"] == 1)
            other = traffic.acquire("openrouter", "other", time.monotonic() + 2, lambda: False)
            native = traffic.acquire("native", "native", time.monotonic() + 2, lambda: False)
            self.assertFalse(waiting.done())
            traffic.release(other)
            traffic.release(native)
            recovered = waiting.result(timeout=2)
            traffic.success(recovered)
            traffic.release(recovered)
        self.assertEqual(traffic.snapshot()["active"], {"native": 0, "openrouter": 0})
        self.assertEqual(traffic.snapshot()["models"], [])

    def test_cooldown_allows_only_one_recovery_probe_and_ignores_stale_success(self):
        traffic = self.scheduler(openrouter_model_concurrency=4)
        leases = [traffic.acquire("openrouter", "model", time.monotonic() + 2, lambda: False) for _ in range(2)]
        traffic.cooldown(leases[0], 0.1)
        traffic.success(leases[1])  # Started before the failure; cannot clear it.
        for lease in leases:
            traffic.release(lease)
        self.assertTrue(traffic.snapshot()["models"][0]["recovering"])
        with concurrent.futures.ThreadPoolExecutor() as pool:
            probes = [pool.submit(traffic.acquire, "openrouter", "model", time.monotonic() + 2, lambda: False) for _ in range(3)]
            eventually(lambda: sum(f.done() for f in probes) == 1)
            self.assertEqual(traffic.snapshot()["active"]["openrouter"], 1)
            self.assertEqual(traffic.snapshot()["queued"]["openrouter"], 2)
            first = next(f for f in probes if f.done())
            traffic.success(first.result())
            traffic.release(first.result())
            for probe in probes:
                if probe is not first:
                    traffic.release(probe.result(timeout=2))

    def test_queue_limit_cancellation_and_memory_budget(self):
        traffic = self.scheduler(openrouter_concurrency=1, queue_limit=1, body_budget_mb=1)
        occupied = traffic.acquire("openrouter", "model", time.monotonic() + 2, lambda: False)
        cancelled = threading.Event()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            pending = pool.submit(traffic.acquire, "openrouter", "model", time.monotonic() + 2, cancelled.is_set)
            eventually(lambda: traffic.snapshot()["queued"]["openrouter"] == 1)
            with self.assertRaises(bcu.TrafficBusy):
                traffic.acquire("openrouter", "model", time.monotonic() + 2, lambda: False)
            cancelled.set()
            with self.assertRaises(bcu.ClientGone):
                pending.result(timeout=2)
        traffic.release(occupied)
        traffic.resize(0, 1024 * 1024)
        with self.assertRaises(bcu.TrafficBusy):
            traffic.resize(0, 1)
        traffic.resize(1024 * 1024, 0)
        self.assertEqual(traffic.snapshot()["buffered_bytes"], 0)
        self.assertEqual(traffic.snapshot()["metrics"]["cancelled"], 1)

    def test_long_retry_hint_is_not_shortened_to_fit_wait_budget(self):
        traffic = self.scheduler()
        lease = traffic.acquire("openrouter", "model", time.monotonic() + 2, lambda: False)
        traffic.cooldown(lease, 600)
        traffic.release(lease)
        with self.assertRaises(bcu.TrafficBusy) as caught:
            traffic.acquire("openrouter", "model", time.monotonic() + 0.1, lambda: False)
        self.assertGreaterEqual(caught.exception.retry_after, 599)

    def test_settings_reject_unbounded_or_unknown_values(self):
        for overrides in ({"max_attempts": 100}, {"queue_limit": True}, {"request_timeout": float("nan")},
                          {"request_timeout": 10**1000}, {"openrouter_concurrency": 0}, {"typo": 1}):
            with self.subTest(overrides=str(overrides)[:100]), self.assertRaises(ValueError):
                bcu.traffic_settings(overrides=overrides)


class TrafficIntegrationTests(unittest.TestCase):
    setUp = fixtures.RouterTests.setUp
    request = fixtures.RouterTests.request
    traffic_options = {"max_attempts": 3, "request_timeout": 3,
                       "backoff_base": 0.01, "backoff_max": 0.1, "jitter": 0,
                       "native_concurrency": 2, "native_model_concurrency": 2,
                       "openrouter_concurrency": 2, "openrouter_model_concurrency": 1}

    def test_429_then_503_recover_without_client_resubmission(self):
        attempts = [(429, {"Retry-After": "1"}, b"{}"), (503, {}, b"{}"), None]
        self.upstream.failure = lambda body: attempts.pop(0)
        reader = self.server.key_reader = Mock(return_value="test-openrouter-key")
        started = time.monotonic()
        status, body = self.request()
        self.assertGreaterEqual(time.monotonic() - started, 1)
        self.assertEqual(status, 200)
        self.assertEqual(len(self.upstream.requests), 3)
        self.assertEqual(len({request[3] for request in self.upstream.requests}), 1)
        reader.assert_called_once()
        metrics = self.server.traffic.snapshot()["metrics"]
        self.assertEqual((metrics["retries"], metrics["recovered"]), (2, 1))
        self.assertEqual(self.server.traffic.snapshot()["buffered_bytes"], 0)
        with closing(sqlite3.connect(self.home / "usage.sqlite3")) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM usage").fetchone()[0], 1)

    def test_mixed_twenty_four_request_burst_is_queued_and_drained(self):
        lock = threading.Lock()
        active = {"native": 0, "openrouter": 0}
        peaks = dict(active)

        def busy(body):
            route = "openrouter" if body["model"] == "author/model" else "native"
            with lock:
                active[route] += 1
                peaks[route] = max(peaks[route], active[route])
            time.sleep(0.04)
            with lock:
                active[route] -= 1

        self.upstream.before_response = busy
        with concurrent.futures.ThreadPoolExecutor(max_workers=24) as pool:
            results = list(pool.map(self.request, ["author/model", "gpt-native"] * 12))
        self.assertTrue(all(status == 200 for status, _ in results))
        self.assertEqual(peaks, {"native": 2, "openrouter": 1})
        traffic = self.server.traffic.snapshot()
        self.assertGreater(traffic["metrics"]["queued_total"], 0)
        self.assertEqual(traffic["active"], {"native": 0, "openrouter": 0})
        self.assertEqual(traffic["queued"], {"native": 0, "openrouter": 0})
        self.assertEqual(traffic["buffered_bytes"], 0)

    def test_exhausted_retries_stop_at_configured_attempt_count(self):
        self.upstream.failure = (429, {}, b'{"error":{"code":"rate_limit_exceeded"}}')
        status, body = self.request()
        self.assertEqual(status, 429)
        self.assertEqual(len(self.upstream.requests), 3)
        self.assertIn(b"3 BCU attempt(s)", body)
        self.assertEqual(self.server.traffic.snapshot()["metrics"]["retries"], 2)

    def test_retry_wait_releases_capacity_for_other_models_and_native(self):
        attempts = []

        def failure(body):
            if body["model"] == "author/model":
                attempts.append(time.monotonic())
                if len(attempts) == 1:
                    return 429, {"Retry-After": "1"}, b"{}"

        self.upstream.failure = failure
        routes = bcu.read_json(self.routes)
        routes["bcu_models"].append("author/other")
        bcu.write_json(self.routes, routes)
        with concurrent.futures.ThreadPoolExecutor() as pool:
            cooling = pool.submit(self.request)
            eventually(lambda: self.server.traffic.snapshot()["queued"]["openrouter"] == 1)
            self.assertEqual(self.server.traffic.snapshot()["active"]["openrouter"], 0)
            self.assertEqual(self.request(model="gpt-native")[0], 200)
            self.assertEqual(self.request(model="author/other")[0], 200)
            self.assertFalse(cooling.done())
            self.assertEqual(cooling.result(timeout=3)[0], 200)
        self.assertGreaterEqual(attempts[1] - attempts[0], 1)

    def test_auth_credit_and_known_quota_failures_are_not_retried(self):
        for status, error in ((401, "authentication"), (402, "payment_required"),
                              (403, "permission_denied"), (400, "invalid_request"), (429, "insufficient_quota")):
            with self.subTest(status=status):
                before = len(self.upstream.requests)
                self.upstream.failure = (status, {}, json.dumps({"error": {"code": error}}).encode())
                self.assertEqual(self.request()[0], status)
                self.assertEqual(len(self.upstream.requests) - before, 1)

    def test_native_retry_keeps_exact_auth_and_body(self):
        failures = [(503, {}, b'{"error":{"code":"server_is_overloaded"}}'), None]
        self.upstream.failure = lambda body: failures.pop(0)
        raw = fixtures.zstd.compress(json.dumps({"model": "gpt-native", "input": "native private history"}).encode())
        self.assertEqual(self.request(raw=raw, headers={"Content-Encoding": "zstd"})[0], 200)
        self.assertEqual(len(self.upstream.requests), 2)
        for _, headers, _, sent in self.upstream.requests:
            self.assertEqual(headers["Authorization"], "Bearer native-secret")
            self.assertEqual(sent, raw)

    def test_temporary_inflight_budget_can_retry_but_not_ordinary_billing(self):
        error = {"error": {"code": "payment_required", "metadata": {"limit_source": "openrouter_in_flight_budget"}}}
        failures = [(402, {"Retry-After": "0"}, json.dumps(error).encode()), None]
        self.upstream.failure = lambda body: failures.pop(0)
        self.assertEqual(self.request()[0], 200)
        self.assertEqual(len(self.upstream.requests), 2)

    def test_stream_failure_and_unknown_connection_failure_are_not_replayed(self):
        self.upstream.events = [{"type": "response.output_text.delta", "delta": "partial"},
                                {"type": "response.failed", "response": {"status": "failed", "error": {"code": "server_error"}}}]
        status, body = self.request(payload={"model": "author/model", "input": "test", "stream": True})
        self.assertEqual(status, 200)
        self.assertIn(b"response.failed", body)
        self.assertEqual(len(self.upstream.requests), 1)
        self.upstream.drop_connection = True
        self.assertEqual(self.request()[0], 502)
        self.assertEqual(len(self.upstream.requests), 2)

    def test_disconnected_queued_request_never_reads_key_or_calls_upstream(self):
        reader = self.server.key_reader = Mock(return_value="test-key")
        lease = self.server.traffic.acquire("openrouter", "author/model", time.monotonic() + 2, lambda: False)
        client = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=2)
        client.request("POST", "/v1/responses", json.dumps({"model": "author/model", "input": "cancel me"}),
                       {"Content-Type": "application/json"})
        eventually(lambda: self.server.traffic.snapshot()["queued"]["openrouter"] == 1)
        client.close()
        eventually(lambda: self.server.traffic.snapshot()["metrics"]["cancelled"] == 1)
        self.server.traffic.release(lease)
        eventually(lambda: self.server.traffic.snapshot()["buffered_bytes"] == 0)
        reader.assert_not_called()
        self.assertEqual(len(self.upstream.requests), 0)

    def test_long_hint_returns_original_response_without_early_retry(self):
        self.upstream.failure = (429, {"Retry-After": "600"}, b"{}")
        status, _, headers = self.request(with_headers=True)
        self.assertEqual((status, headers["retry-after"]), (429, "600"))
        self.assertEqual(len(self.upstream.requests), 1)

    def test_disconnect_during_retry_wait_prevents_another_attempt(self):
        self.upstream.failure = (429, {"Retry-After": "1"}, b"{}")
        client = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=2)
        client.request("POST", "/v1/responses", json.dumps({"model": "author/model", "input": "cancel during backoff"}),
                       {"Content-Type": "application/json"})
        eventually(lambda: self.server.traffic.snapshot()["queued"]["openrouter"] == 1)
        client.close()
        eventually(lambda: self.server.traffic.snapshot()["metrics"]["cancelled"] == 1)
        eventually(lambda: self.server.traffic.snapshot()["buffered_bytes"] == 0)
        self.assertEqual(len(self.upstream.requests), 1)
        self.assertEqual(self.server.traffic.snapshot()["metrics"]["retries"], 0)
