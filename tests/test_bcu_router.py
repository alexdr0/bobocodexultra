import concurrent.futures
from contextlib import closing
from compression import zstd
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time
import tomllib
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "bcu_router.py"
spec = importlib.util.spec_from_file_location("bcu_router_test", SOURCE)
bcu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bcu)


class Upstream(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def do_POST(self):
        raw = self.rfile.read(int(self.headers["Content-Length"]))
        decoded = zstd.decompress(raw) if self.headers.get("Content-Encoding") == "zstd" else raw
        body = json.loads(decoded)
        self.server.requests.append((self.path, dict(self.headers), body, raw))
        result = {"id": "resp-" + str(time.time_ns()), "object": "response", "status": "completed",
                  "output": [], "usage": {"input_tokens": 10, "output_tokens": 3, "total_tokens": 13,
                                          "input_tokens_details": {"cached_tokens": 2}}}
        if body.get("stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Connection", "close")
            self.end_headers()
            events = [{"type": "response.output_text.delta", "delta": "hello"},
                      {"type": "response.completed", "response": result}]
            for event in events:
                self.wfile.write(("data: " + json.dumps(event) + "\n\n").encode())
                self.wfile.flush()
            self.close_connection = True
        else:
            encoded = json.dumps(result).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
        self.upstream.requests = []
        threading.Thread(target=self.upstream.serve_forever, daemon=True).start()
        self.addCleanup(self.upstream.server_close)
        self.addCleanup(self.upstream.shutdown)
        base = f"http://127.0.0.1:{self.upstream.server_port}"
        self.routes = self.home / "routes.json"
        bcu.write_json(self.routes, {"home": str(self.home), "native_base": base + "/native/v1",
                       "native_models": ["gpt-native", "ollama:cloud"],
                       "bcu_models": ["author/model"], "known_bcu_models": ["author/model", "retired/model"]})
        self.server = bcu.RouterServer(("127.0.0.1", 0), self.routes,
                                      key_reader=lambda: "test-openrouter-key", openrouter_base=base + "/router/v1")
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def request(self, model="author/model", payload=None, headers=None, path="/v1/responses", raw=None):
        c = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        body = raw or json.dumps(payload or {"model": model, "input": "test"}).encode()
        h = {"Content-Type": "application/json", "Authorization": "Bearer native-secret",
             "ChatGPT-Account-ID": "test-account", "Cookie": "native-cookie"}
        h.update(headers or {})
        c.request("POST", path, body, h)
        r = c.getresponse()
        result = r.status, r.read()
        c.close()
        return result

    def test_native_and_ollama_preserve_auth_body_and_endpoint(self):
        for model in ("gpt-native", "ollama:cloud"):
            raw = zstd.compress(json.dumps({"model": model, "input": "native history"}).encode())
            self.assertEqual(self.request(raw=raw, headers={"Content-Encoding": "zstd"})[0], 200)
            path, headers, payload, forwarded = self.upstream.requests[-1]
            self.assertEqual(path, "/native/v1/responses")
            self.assertEqual(headers["Authorization"], "Bearer native-secret")
            self.assertEqual(headers["ChatGPT-Account-ID"], "test-account")
            self.assertEqual(forwarded, raw)

    def test_openrouter_strips_native_credentials_and_normalizes(self):
        payload = {"model": "author/model", "input": "hello", "store": True,
                   "service_tier": "priority", "client_metadata": {"account": "private"},
                   "reasoning": {"effort": "xhigh", "summary": "auto"}}
        raw = zstd.compress(json.dumps(payload).encode())
        status, body = self.request(raw=raw, headers={"Content-Encoding": "zstd", "X-Private": "hidden"})
        self.assertEqual(status, 200)
        path, headers, payload, _ = self.upstream.requests[-1]
        self.assertEqual(path, "/router/v1/responses")
        self.assertEqual(headers["Authorization"], "Bearer test-openrouter-key")
        self.assertNotIn("ChatGPT-Account-ID", headers)
        self.assertNotIn("Cookie", headers)
        self.assertNotIn("X-Private", headers)
        self.assertFalse(payload["store"])
        self.assertNotIn("service_tier", payload)
        self.assertEqual(payload["reasoning"], {"effort": "high"})

    def test_streaming_and_ledger_store_usage_without_text(self):
        status, raw = self.request(payload={"model": "author/model", "input": "secret prompt", "stream": True})
        self.assertEqual(status, 200)
        self.assertIn(b'response.output_text.delta', raw)
        self.assertIn(b'response.completed', raw)
        with closing(sqlite3.connect(self.home / "usage.sqlite3")) as db:
            rows = db.execute("SELECT model,data FROM usage").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(json.loads(rows[0][1])["total_tokens"], 13)
        self.assertNotIn("secret prompt", str(rows))
        self.assertNotIn("hello", str(rows))

    def test_concurrent_subagent_requests_route_independently(self):
        with concurrent.futures.ThreadPoolExecutor() as pool:
            results = list(pool.map(self.request, ["gpt-native", "author/model", "ollama:cloud", "author/model"]))
        self.assertTrue(all(status == 200 for status, _ in results))
        self.assertEqual(sum(path == "/router/v1/responses" for path, *_ in self.upstream.requests), 2)

    def test_disabled_unknown_and_browser_requests_never_leave_localhost(self):
        for model in ("retired/model", "unknown-model"):
            self.assertEqual(self.request(model)[0], 400)
        self.assertEqual(self.request(headers={"Origin": "https://evil.example"})[0], 403)
        self.assertEqual(self.request(headers={"Host": "evil.example"})[0], 403)
        self.assertEqual(self.request(path="/arbitrary")[0], 404)
        self.assertEqual(len(self.upstream.requests), 0)

    def test_live_model_changes_and_no_redirect_following(self):
        value = bcu.read_json(self.routes)
        value["bcu_models"].append("new/model")
        bcu.write_json(self.routes, value)
        self.assertEqual(self.request("new/model")[0], 200)

    def test_websocket_falls_back_to_http(self):
        c = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        c.request("GET", "/v1/responses", headers={"Upgrade": "websocket", "Connection": "Upgrade"})
        r = c.getresponse()
        self.assertEqual(r.status, 426)
        r.read()
        c.close()

    def test_namespaced_and_custom_tool_round_trip(self):
        payload = {"model": "author/model", "input": [
            {"type": "custom_tool_call", "name": "apply_patch", "namespace": "functions", "call_id": "call-1", "input": "patch"},
            {"type": "custom_tool_call_output", "call_id": "call-1", "output": "ok"},
            {"type": "agent_message", "author": "child", "recipient": "parent", "content": [{"type": "input_text", "text": "done"}]}],
            "tools": [{"type": "namespace", "name": "functions", "tools": [
                {"type": "custom", "name": "apply_patch"}, {"type": "function", "name": "spawn_agent", "parameters": {"type": "object"}}]}]}
        converted, bridge = bcu.normalize(payload)
        self.assertEqual(converted["input"][0]["name"], "bcu_tool_0")
        self.assertEqual(converted["input"][1]["type"], "function_call_output")
        self.assertIn("done", str(converted["input"][2]))
        start = bridge.event({"type": "response.output_item.added", "item": {"type": "function_call", "id": "fc1", "name": "bcu_tool_0", "arguments": ""}})[0]
        self.assertEqual(start["item"]["type"], "custom_tool_call")
        self.assertEqual(start["item"]["namespace"], "functions")
        self.assertEqual(bridge.event({"type": "response.function_call_arguments.delta", "item_id": "fc1", "delta": "partial"}), [])
        done = bridge.event({"type": "response.function_call_arguments.done", "item_id": "fc1", "arguments": '{"input":"patch"}'})
        self.assertEqual(done[0]["delta"], "patch")
        self.assertEqual(done[1]["input"], "patch")

    def test_tool_search_expands_discovered_tools_and_restores_client_calls(self):
        payload = {"model": "author/model", "tools": [{"type": "tool_search", "execution": "client", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}}],
                   "input": [{"type": "tool_search_call", "call_id": "ts1", "arguments": {"query": "read file"}},
                             {"type": "tool_search_output", "call_id": "ts1", "tools": [
                                 {"type": "namespace", "name": "files", "tools": [{"type": "function", "name": "read", "parameters": {"type": "object"}}]}]}]}
        converted, bridge = bcu.normalize(payload)
        self.assertEqual(len(converted["tools"]), 2)
        self.assertEqual(converted["input"][0]["type"], "function_call")
        self.assertEqual(converted["input"][1]["type"], "function_call_output")
        result = bridge.output({"type": "function_call", "call_id": "ts2", "name": "bcu_tool_0", "arguments": '{"query":"next"}'})
        self.assertEqual(result["type"], "tool_search_call")
        self.assertEqual(result["execution"], "client")
        self.assertEqual(result["arguments"], {"query": "next"})

    def test_switch_back_to_native_removes_only_bcu_reasoning(self):
        payload = {"model": "gpt-native", "input": [
            {"type": "reasoning", "id": "rs_bcu_test", "encrypted_content": "not-portable"},
            {"type": "reasoning", "id": "rs_native", "encrypted_content": "native-state"},
            {"type": "message", "role": "user", "content": "visible history"}]}
        raw = zstd.compress(json.dumps(payload).encode())
        self.assertEqual(self.request(raw=raw, headers={"Content-Encoding": "zstd"})[0], 200)
        _, headers, sent, _ = self.upstream.requests[-1]
        self.assertNotIn("Content-Encoding", headers)
        self.assertEqual(sent["input"], payload["input"][1:])

    def test_reasoning_stream_ids_remain_consistent_after_tagging(self):
        bridge = bcu.ToolBridge({})
        start = bridge.event({"type": "response.output_item.added", "item": {"type": "reasoning", "id": "rs_test"}})[0]
        delta = bridge.event({"type": "response.reasoning_summary_text.delta", "item_id": "rs_test", "delta": "test"})[0]
        self.assertEqual(start["item"]["id"], delta["item_id"])
        self.assertTrue(delta["item_id"].startswith("rs_bcu_"))


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        bcu.write_json(self.home / "native.json", {"models": [{"slug": "gpt-native"}, {"slug": "ollama:cloud"}]})
        bcu.write_json(self.home / "openrouter-codex-models.json", {"models": [{"slug": "author/model", "display_name": "Model (BCU)"}]})
        self.original = (f'model = "gpt-native"\nmodel_catalog_json = "{self.home / "native.json"}"\n'
                         'openai_base_url = "http://127.0.0.1:11434/api/codex/v1"\nservice_tier = "default"\n\n[desktop]\nappearance = "dark"\n').encode()
        (self.home / "config.toml").write_bytes(self.original)
        self.control = bcu.Controller(self.home)
        self.control.plist = self.home / "test.plist"
        p = patch.object(bcu.Controller, "service_start")
        p.start()
        self.addCleanup(p.stop)

    def test_combined_catalog_keeps_native_default_and_restores_exactly(self):
        self.control.enable()
        parsed = tomllib.loads(self.control.config.read_text())
        self.assertEqual(parsed["model"], "gpt-native")
        self.assertEqual(parsed["model_provider"], "openai")
        self.assertEqual(parsed["openai_base_url"], bcu.BASE)
        self.assertEqual([m["slug"] for m in bcu.read_json(self.control.catalog)["models"]], ["gpt-native", "ollama:cloud", "author/model"])
        self.control.enable()
        self.control.disable()
        self.assertEqual(self.control.config.read_bytes(), self.original)

    def test_off_preserves_unrelated_edits_and_restores_native_model(self):
        self.control.enable()
        changed = self.control.config.read_text().replace('service_tier = "default"', 'service_tier = "priority"').replace('model = "gpt-native"', 'model = "author/model"')
        self.control.config.write_text(changed)
        self.control.disable()
        parsed = tomllib.loads(self.control.config.read_text())
        self.assertEqual(parsed["service_tier"], "priority")
        self.assertEqual(parsed["model"], "gpt-native")
        self.assertEqual(parsed["openai_base_url"], "http://127.0.0.1:11434/api/codex/v1")
        self.assertNotIn("model_provider", parsed)

    def test_failed_service_start_does_not_activate_config(self):
        with patch.object(bcu.Controller, "service_start", side_effect=ValueError("not ready")):
            with self.assertRaises(ValueError):
                self.control.enable()
        self.assertEqual(self.control.config.read_bytes(), self.original)
        self.assertFalse(self.control.state.exists())

    def test_removal_reserves_bcu_ids_and_refreshes_native_additions(self):
        self.control.enable()
        bcu.write_json(self.home / "openrouter-codex-models.json", {"models": [{"slug": "new/model"}]})
        bcu.write_json(self.home / "native.json", {"models": [{"slug": "gpt-native"}, {"slug": "new-native"}]})
        self.control.refresh()
        routes = bcu.read_json(self.control.routes)
        self.assertIn("author/model", routes["known_bcu_models"])
        self.assertNotIn("author/model", routes["bcu_models"])
        self.assertIn("new-native", routes["native_models"])


if __name__ == "__main__":
    unittest.main()
