"""Shared-router accounting, pricing fallbacks, and rollout isolation."""
from contextlib import closing, redirect_stdout
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

import test_openrouter_codex as fixtures

tool = fixtures.tool


class UsageTests(unittest.TestCase):
    setUp = fixtures.OpenRouterCodexTests.setUp

    def record(self, response_id="response-1", model="author/model", cost="0.0123", stamp=None,
               incoming=100, outgoing=10, cached=40, reasoning=3):
        path = self.home / "bcu/usage.sqlite3"
        path.parent.mkdir(exist_ok=True)
        with closing(sqlite3.connect(path)) as db:
            db.execute("CREATE TABLE IF NOT EXISTS usage (id TEXT PRIMARY KEY, timestamp REAL, model TEXT, data TEXT)")
            data = {"input_tokens": incoming, "output_tokens": outgoing, "total_tokens": incoming + outgoing,
                    "input_tokens_details": {"cached_tokens": cached},
                    "output_tokens_details": {"reasoning_tokens": reasoning}, "cost": cost}
            db.execute("INSERT OR REPLACE INTO usage VALUES (?, ?, ?, ?)",
                       (response_id, (stamp or datetime.now(timezone.utc)).timestamp(), model, json.dumps(data)))
            db.commit()

    def rollout(self, provider="openrouter", model="author/legacy", name="legacy"):
        path = self.home / "sessions" / (name + ".jsonl")
        path.parent.mkdir(exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()
        lines = [
            {"type": "session_meta", "payload": {"model_provider": provider, "id": name}},
            {"type": "turn_context", "payload": {"model": model}},
            {"type": "token_usage_record", "timestamp": now, "payload": {
                "turn_id": "turn-1", "usage": {"input_tokens": 20, "output_tokens": 5, "total_tokens": 25}}},
        ]
        path.write_text("".join(json.dumps(line) + "\n" for line in lines))
        return path

    def prices(self):
        (self.home / "openrouter-codex-usage-prices.json").write_text(json.dumps({
            "fetched_at": datetime.now(timezone.utc).isoformat(), "prices": {
                model: {"prompt": "0.001", "completion": "0.002", "cache_read": "0.0001"}
                for model in ("author/model", "author/legacy")}}))

    def test_desktop_ledger_is_used_without_rollout_double_counting(self):
        self.record()
        self.record()  # The ledger's response ID is unique.
        native = self.rollout(provider="openai", model="author/model", name="shared")
        # Native/shared histories must be skipped after metadata, even if the
        # remaining file is huge, truncated, or contains stale duplicate tokens.
        with native.open("a") as handle:
            handle.write("invalid trailing content\n")
        self.rollout()
        self.prices()
        report = tool["build_usage_report"](30, True)
        self.assertEqual(report["summary"]["desktop_requests"], 1)
        self.assertEqual(report["summary"]["legacy_records"], 1)
        self.assertEqual(report["total_tokens"], 135)
        self.assertEqual(report["unreadable_files"], 0)
        self.assertEqual(report["models"]["author/model"]["reported_cost_usd"], 0.0123)
        self.assertEqual(report["models"]["author/legacy"]["estimated_cost_usd"], 0.03)
        self.assertAlmostEqual(report["total_cost_usd"], 0.0423)

    def test_reported_zero_and_retired_models_need_no_catalog_or_key(self):
        self.record(model="retired/model", cost=0)
        with patch.dict(tool["build_usage_report"].__globals__, {
            "openrouter_pricing_catalog": lambda: self.fail("Unexpected network request"),
            "key_exists": lambda: self.fail("Unexpected Keychain access"),
        }):
            report = tool["build_usage_report"](0, False)
        self.assertEqual(report["total_tokens"], 110)
        self.assertEqual(report["total_cost_usd"], 0)
        self.assertEqual(report["summary"]["reported_records"], 1)
        self.assertEqual(report["summary"]["cost_source"], "reported")

    def test_missing_cost_estimates_cache_without_adding_reasoning_twice(self):
        self.record(cost=None)
        self.prices()
        report = tool["build_usage_report"](30, True)
        self.assertEqual(report["summary"]["total_tokens"], 110)
        self.assertEqual(report["summary"]["output_tokens"], 10)
        self.assertEqual(report["summary"]["reasoning_output_tokens"], 3)
        self.assertAlmostEqual(report["total_cost_usd"], 0.084)
        self.assertEqual(report["summary"]["cost_source"], "estimated")

    def test_unknown_price_keeps_partial_subtotal_and_tokens(self):
        self.record()
        self.record(response_id="unknown", model="retired/model", cost=None)
        report = tool["build_usage_report"](30, True)
        self.assertEqual(report["total_tokens"], 220)
        self.assertIsNone(report["total_cost_usd"])
        self.assertEqual(report["summary"]["known_cost_usd"], 0.0123)
        self.assertEqual(report["summary"]["unpriced_records"], 1)
        self.assertTrue(report["warnings"])

    def test_date_filter_and_all_time(self):
        self.record(response_id="old", stamp=datetime.now(timezone.utc) - timedelta(days=40))
        self.record(response_id="new")
        self.assertEqual(tool["build_usage_report"](30, True)["records"], 1)
        self.assertEqual(tool["build_usage_report"](0, True)["records"], 2)

    def test_missing_corrupt_and_invalid_ledgers_do_not_fake_complete_totals(self):
        path = self.home / "bcu/usage.sqlite3"
        report = tool["build_usage_report"](30, True)
        self.assertEqual(report["ledger_status"], "missing")
        self.assertFalse(path.exists())
        self.record()
        with closing(sqlite3.connect(path)) as db:
            db.execute("INSERT INTO usage VALUES (?, ?, ?, ?)",
                       ("bad", datetime.now(timezone.utc).timestamp(), "author/model", "not json"))
            db.commit()
        report = tool["build_usage_report"](30, True)
        self.assertEqual(report["records"], 1)
        self.assertEqual(report["invalid_ledger_records"], 1)
        self.assertFalse(report["data_complete"])
        path.write_bytes(b"not a SQLite database")
        report = tool["build_usage_report"](30, True)
        self.assertEqual(report["ledger_status"], "unreadable")
        self.assertIsNone(report["total_cost_usd"])
        self.assertTrue(report["warnings"])

    def test_corrupt_pricing_cache_and_network_failure_preserve_report(self):
        self.record(cost=None)
        (self.home / "openrouter-codex-usage-prices.json").write_text("bad cache")
        with patch.dict(tool["usage_prices"].__globals__, {
            "openrouter_pricing_catalog": lambda: (_ for _ in ()).throw(tool["SetupError"]("offline")),
        }):
            report = tool["build_usage_report"](30, False)
        self.assertEqual(report["total_tokens"], 110)
        self.assertIsNone(report["total_cost_usd"])

    def test_json_output_is_clean_and_negative_period_rejected(self):
        self.record()
        output = io.StringIO()
        with redirect_stdout(output):
            tool["usage"](30, True, True)
        report = json.loads(output.getvalue())
        self.assertEqual(report["schema_version"], 2)
        self.assertNotIn(str(self.home), output.getvalue())
        with self.assertRaises(tool["SetupError"]):
            tool["usage"](-1, True, True)
        with self.assertRaises(tool["SetupError"]):
            tool["usage"](30, True, True, True)

