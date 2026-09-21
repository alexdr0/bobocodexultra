import json
import argparse
import os
import runpy
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch


TOOL = Path(__file__).resolve().parents[1] / "openrouter-codex"
tool = runpy.run_path(str(TOOL))


class OpenRouterCodexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / ".codex"
        self.home.mkdir()
        env = patch.dict(os.environ, {"CODEX_HOME": str(self.home)})
        env.start()
        self.addCleanup(env.stop)

    def test_profile_and_catalog_are_keyless_and_parseable(self):
        with patch.dict(tool["prepare"].__globals__, {"ensure_macos": lambda: None}):
            tool["prepare"]()
        profile = (self.home / "openrouter.config.toml").read_text()
        config = tomllib.loads(profile)
        catalog = json.loads((self.home / "openrouter-codex-models.json").read_text())
        self.assertEqual(len(catalog["models"]), 5)
        self.assertTrue(all(m["display_name"].endswith(" (BCU)") for m in catalog["models"]))
        self.assertTrue(all(m["display_name"].count("(BCU)") == 1 for m in catalog["models"]))
        self.assertEqual(config["model_provider"], "openrouter")
        self.assertEqual(config["model_providers"]["openrouter"]["auth"]["command"], "/usr/bin/security")
        self.assertNotIn("sk-or-", profile)
        self.assertTrue(all(m["base_instructions"] == tool["BASE_INSTRUCTIONS"] for m in catalog["models"]))

    def test_desktop_round_trip_preserves_original_exactly(self):
        original = b'model = "gpt-6-astra"\nmodel_reasoning_effort = "xhigh"\n\n[desktop]\nappearance = "dark"\n'
        (self.home / "config.toml").write_bytes(original)
        with patch.dict(tool["prepare"].__globals__, {"ensure_macos": lambda: None, "key_exists": lambda: True}):
            tool["prepare"]()
            tool["desktop_on"]()
            active = tomllib.loads((self.home / "config.toml").read_text())
            self.assertEqual(active["model_provider"], "openrouter")
            self.assertEqual(active["desktop"]["appearance"], "dark")
            tool["desktop_off"]()
        self.assertEqual((self.home / "config.toml").read_bytes(), original)
        self.assertEqual(len(list((self.home / "openrouter-codex-backups").glob("*.toml"))), 1)

    def test_restoration_refuses_to_discard_intervening_edits(self):
        (self.home / "config.toml").write_text('model = "gpt-6-astra"\n')
        with patch.dict(tool["prepare"].__globals__, {"ensure_macos": lambda: None, "key_exists": lambda: True}):
            tool["prepare"]()
            tool["desktop_on"]()
            config = self.home / "config.toml"
            config.write_text(config.read_text() + "# user change\n")
            with self.assertRaises(tool["SetupError"]):
                tool["desktop_off"]()
        self.assertTrue((self.home / "openrouter-codex-state.json").exists())

    def test_selected_models_update_profile_catalog_and_active_desktop(self):
        original = b'model = "gpt-6-astra"\n[desktop]\nappearance = "dark"\n'
        (self.home / "config.toml").write_bytes(original)
        with patch.dict(tool["prepare"].__globals__, {"ensure_macos": lambda: None, "key_exists": lambda: True}):
            tool["prepare"]()
            tool["desktop_on"]()
            selected = tool["selection"]()
            selected["models"] = [{"id": "deepseek/deepseek-v4.1-flash", "name": "DeepSeek V4.1 Flash",
                                   "context_length": 1048576, "images": False}]
            selected["default"] = selected["models"][0]["id"]
            tool["update_selection"](selected)
            config = tomllib.loads((self.home / "config.toml").read_text())
            profile = tomllib.loads((self.home / "openrouter.config.toml").read_text())
            catalog = json.loads((self.home / "openrouter-codex-models.json").read_text())
            self.assertEqual(config["model"], "deepseek/deepseek-v4.1-flash")
            self.assertEqual(profile["model"], config["model"])
            self.assertEqual([m["slug"] for m in catalog["models"]], [config["model"]])
            self.assertEqual(catalog["models"][0]["display_name"], "DeepSeek V4.1 Flash (BCU)")
            tool["update_selection"](tool["selection"]())
            self.assertEqual(json.loads((self.home / "openrouter-codex-models.json").read_text())["models"][0]["display_name"],
                             "DeepSeek V4.1 Flash (BCU)")
            tool["desktop_off"]()
        self.assertEqual((self.home / "config.toml").read_bytes(), original)

    def test_external_catalog_edit_is_preserved(self):
        with patch.dict(tool["prepare"].__globals__, {"ensure_macos": lambda: None}):
            tool["prepare"]()
            catalog = self.home / "openrouter-codex-models.json"
            catalog.write_text(catalog.read_text() + "\n")
            chosen = tool["selection"]()
            with self.assertRaises(tool["SetupError"]):
                tool["update_selection"](chosen)
        self.assertTrue(catalog.read_text().endswith("\n\n"))

    def test_label_sync_preserves_unrelated_desktop_edit(self):
        (self.home / "config.toml").write_text('model = "gpt-6-astra"\nservice_tier = "default"\n')
        with patch.dict(tool["prepare"].__globals__, {"ensure_macos": lambda: None, "key_exists": lambda: True}):
            tool["prepare"]()
            tool["desktop_on"]()
            config = self.home / "config.toml"
            edited = config.read_bytes().replace(b'service_tier = "default"', b'service_tier = "priority"')
            config.write_bytes(edited)
            tool["update_selection"](tool["selection"]())
            self.assertEqual(config.read_bytes(), edited)
            catalog = json.loads((self.home / "openrouter-codex-models.json").read_text())
            self.assertTrue(all(m["display_name"].endswith(" (BCU)") for m in catalog["models"]))
            with self.assertRaises(tool["SetupError"]):
                tool["desktop_off"]()

    def test_default_change_preserves_dirty_desktop_setting_and_restore_guard(self):
        (self.home / "config.toml").write_text('model = "gpt-6-astra"\nservice_tier = "default"\n')
        with patch.dict(tool["prepare"].__globals__, {"ensure_macos": lambda: None, "key_exists": lambda: True}):
            tool["prepare"]()
            tool["desktop_on"]()
            config = self.home / "config.toml"
            config.write_bytes(config.read_bytes().replace(b'service_tier = "default"', b'service_tier = "priority"'))
            state_before = (self.home / "openrouter-codex-state.json").read_bytes()
            chosen = tool["selection"]()
            chosen["default"] = "moonshotai/kimi-k3"
            tool["update_selection"](chosen)
            active = tomllib.loads(config.read_text())
            self.assertEqual(active["model"], "moonshotai/kimi-k3")
            self.assertEqual(active["service_tier"], "priority")
            self.assertEqual((self.home / "openrouter-codex-state.json").read_bytes(), state_before)
            with self.assertRaises(tool["SetupError"]):
                tool["desktop_off"]()

    def test_named_and_legacy_commands_and_docs_work_without_a_key(self):
        for command, expected in ((["docs", "model"], "model add [author/model-id]"),
                                  (["model", "list"], "anthropic/claude-opus-5"),
                                  (["models", "list"], "anthropic/claude-opus-5")):
            result = subprocess.run([sys.executable, str(TOOL), "--no-color", *command],
                                    text=True, capture_output=True, check=True)
            self.assertIn(expected, result.stdout)
            self.assertNotIn("\033[", result.stdout)

    def test_manager_refuses_noninteractive_output_without_changes(self):
        result = subprocess.run([sys.executable, str(TOOL), "model", "manage"],
                                text=True, capture_output=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("interactive terminal", result.stderr)
        self.assertFalse((self.home / "openrouter-codex-selection.json").exists())

    def test_install_creates_two_names_and_is_idempotent(self):
        with patch.object(Path, "home", return_value=Path(self.temp.name)):
            tool["install"]()
            primary = Path(self.temp.name) / ".local/bin/bobocodexultra"
            alias = primary.with_name("boboultracodex")
            self.assertTrue(primary.is_file())
            self.assertEqual(os.readlink(alias), primary.name)
            self.assertEqual(primary.with_name("bcu_games.py").read_bytes(),
                             TOOL.with_name("bcu_games.py").read_bytes())
            tool["install"]()
            self.assertEqual(primary.read_bytes(), TOOL.read_bytes())

    def test_model_names_cannot_inject_terminal_control_sequences(self):
        record = tool["model_record"]({"id": "author/model", "name": "Nice\033[31m\r\nBad",
                                       "context_length": 100000, "architecture": {"input_modalities": ["text"]}})
        self.assertNotIn("\033", record["name"])
        self.assertNotIn("\n", record["name"])
        self.assertEqual(tool["selector_name"]("OpenRouter · Example (BCU) (BCU)"), "Example (BCU)")

    def test_add_default_remove_keep_dynamic_selector_markers(self):
        new = {"id": "deepseek/deepseek-v4.1-flash", "name": "DeepSeek V4.1 Flash",
               "context_length": 1048576, "architecture": {"input_modalities": ["text"]}}
        with patch.dict(tool["prepare"].__globals__, {
            "ensure_macos": lambda: None,
            "openrouter_models": lambda query, limit: [new],
        }):
            tool["prepare"]()
            commands = tool["model_commands"]
            commands(argparse.Namespace(action="add", model=new["id"]))
            commands(argparse.Namespace(action="default", model=new["id"]))
            commands(argparse.Namespace(action="remove", model="moonshotai/kimi-k3"))
            selected = tool["selection"]()
            catalog = json.loads((self.home / "openrouter-codex-models.json").read_text())["models"]
            self.assertEqual(selected["default"], new["id"])
            self.assertEqual([m["slug"] for m in catalog], [m["id"] for m in selected["models"]])
            self.assertTrue(all(m["display_name"].endswith(" (BCU)") for m in catalog))
            self.assertEqual(catalog[-1]["display_name"], "DeepSeek V4.1 Flash (BCU)")

    def test_native_reset_preserves_unrelated_changes_and_removes_bcu(self):
        original = (b'model = "gpt-6-astra"\nmodel_reasoning_effort = "xhigh"\n'
                    b'service_tier = "default"\n\n[desktop]\nappearance = "dark"\n')
        (self.home / "config.toml").write_bytes(original)
        with patch.dict(tool["prepare"].__globals__, {"ensure_macos": lambda: None, "key_exists": lambda: True}):
            tool["prepare"]()
            tool["desktop_on"]()
            config = self.home / "config.toml"
            edited = config.read_text().replace('service_tier = "default"', 'service_tier = "priority"')
            edited = edited.replace('appearance = "dark"', 'appearance = "light"')
            config.write_text(edited)
            tool["native_reset"]()
        reset = tomllib.loads((self.home / "config.toml").read_text())
        self.assertEqual(reset["model"], "gpt-6-astra")
        self.assertEqual(reset["model_reasoning_effort"], "xhigh")
        self.assertEqual(reset["service_tier"], "priority")
        self.assertEqual(reset["desktop"]["appearance"], "light")
        self.assertNotIn("model_provider", reset)
        self.assertNotIn("openrouter", reset.get("model_providers", {}))
        self.assertFalse((self.home / "openrouter-codex-state.json").exists())
        self.assertEqual(len(list((self.home / "openrouter-codex-backups").glob("pre-native-reset-*.toml"))), 1)

    def test_native_reset_removes_bcu_keys_absent_from_original(self):
        (self.home / "config.toml").write_text('service_tier = "default"\n')
        with patch.dict(tool["prepare"].__globals__, {"ensure_macos": lambda: None, "key_exists": lambda: True}):
            tool["prepare"]()
            tool["desktop_on"]()
            tool["native_reset"]()
        reset = tomllib.loads((self.home / "config.toml").read_text())
        self.assertNotIn("model", reset)
        self.assertNotIn("model_provider", reset)
        self.assertNotIn("model_catalog_json", reset)
        self.assertNotIn("model_reasoning_effort", reset)

    def test_label_sync_does_not_touch_diverged_desktop_config(self):
        (self.home / "config.toml").write_text('model = "gpt-6-astra"\n')
        with patch.dict(tool["prepare"].__globals__, {"ensure_macos": lambda: None, "key_exists": lambda: True}):
            tool["prepare"]()
            tool["desktop_on"]()
            config = self.home / "config.toml"
            diverged = config.read_text().replace('model = "anthropic/claude-opus-5"', 'model = "different/model"')
            config.write_text(diverged)
            tool["sync_selection_artifacts"]()
            self.assertEqual(config.read_text(), diverged)
            catalog = json.loads((self.home / "openrouter-codex-models.json").read_text())["models"]
            self.assertTrue(all(not m["display_name"].startswith("OpenRouter") for m in catalog))

    def test_manager_search_sort_multiple_selection_and_unlisted_preservation(self):
        chosen = {"default": "anthropic/claude-opus-5", "models": [
            {"id": "anthropic/claude-opus-5", "name": "Claude Opus 5", "context_length": 1000000, "images": True},
            {"id": "retired/model", "name": "Retired", "context_length": 32000, "images": False},
        ]}
        live = [
            {"id": "deepseek/deepseek-v4.1-flash", "name": "DeepSeek Flash", "description": "coding tools",
             "context_length": 1048576, "pricing": {"prompt": "0.0000003", "completion": "0.0000012"},
             "supported_parameters": ["tools"], "architecture": {"input_modalities": ["text"]}},
            {"id": "anthropic/claude-opus-5", "name": "Claude Opus 5", "description": "agentic tools",
             "context_length": 1000000, "pricing": {"prompt": "0.000005", "completion": "0.000025"},
             "supported_parameters": ["tools"], "architecture": {"input_modalities": ["text", "image"]}},
        ]
        with patch.dict(tool["manager_catalog"].__globals__, {"openrouter_models": lambda query, limit: live}):
            available = tool["manager_catalog"](chosen)
        self.assertTrue(available[-1]["_unavailable"])
        self.assertEqual([m["id"] for m in tool["manager_view"](available, set(), "opus agentic", "popular")],
                         ["anthropic/claude-opus-5"])
        self.assertEqual(tool["manager_view"](available, set(), "", "input price")[0]["id"],
                         "deepseek/deepseek-v4.1-flash")
        self.assertEqual(tool["manager_view"](available, {"retired/model"}, "", "selected first")[0]["id"],
                         "retired/model")
        result = tool["manager_result"](chosen, {"retired/model", "deepseek/deepseek-v4.1-flash"},
                                        "deepseek/deepseek-v4.1-flash", available)
        self.assertEqual([m["id"] for m in result["models"]], ["retired/model", "deepseek/deepseek-v4.1-flash"])
        self.assertEqual(result["default"], "deepseek/deepseek-v4.1-flash")

    def test_local_usage_reads_only_openrouter_and_avoids_format_double_count(self):
        sessions = self.home / "sessions/2026/09/21"
        sessions.mkdir(parents=True)
        rollout = sessions / "rollout.jsonl"
        rows = [
            {"timestamp": "2026-09-21T10:00:00Z", "type": "session_meta",
             "payload": {"model_provider": "openrouter"}},
            {"timestamp": "2026-09-21T10:00:01Z", "type": "turn_context",
             "payload": {"model": "author/model"}},
            {"timestamp": "2026-09-21T10:00:02Z", "type": "event_msg",
             "payload": {"type": "token_count", "info": {"last_token_usage": {
                 "input_tokens": 999, "cached_input_tokens": 0, "cache_write_input_tokens": 0,
                 "output_tokens": 1, "reasoning_output_tokens": 0, "total_tokens": 1000}}}},
            {"timestamp": "2026-09-21T10:00:03Z", "type": "token_usage_record",
             "payload": {"turn_id": "turn-1", "turn_token_usage": {
                 "input_tokens": 100, "cached_input_tokens": 20, "cache_write_input_tokens": 10,
                 "output_tokens": 5, "reasoning_output_tokens": 2, "total_tokens": 105}}},
        ]
        rollout.write_text("".join(json.dumps(row) + "\n" for row in rows))
        records, unreadable = tool["local_usage_records"](self.home)
        self.assertEqual(unreadable, 0)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["total_tokens"], 105)

    def test_estimated_cost_uses_cache_rates_without_double_counting(self):
        record = {"model": "author/model", "input_tokens": 100, "cached_input_tokens": 20,
                  "cache_write_input_tokens": 10, "output_tokens": 5,
                  "reasoning_output_tokens": 2, "total_tokens": 105}
        prices = {"author/model": {"prompt": "0.000001", "completion": "0.000002",
                                    "cache_read": "0.0000001", "cache_write": "0.0000015"}}
        cost, discounted = tool["estimate_record_cost"](record, prices)
        self.assertTrue(discounted)
        self.assertEqual(cost, tool["Decimal"]("0.000097"))


if __name__ == "__main__":
    unittest.main()
