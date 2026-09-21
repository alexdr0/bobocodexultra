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
from types import SimpleNamespace
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

    def test_prepare_upgrades_only_a_checksum_owned_legacy_reasoning_catalog(self):
        globals_ = tool["prepare"].__globals__
        with patch.dict(globals_, {"ensure_macos": lambda: None}):
            tool["prepare"]()
            path = self.home / "openrouter-codex-models.json"
            old = json.loads(path.read_text())
            for model in old["models"]:
                model["supported_reasoning_levels"] = [{"effort": "high", "description": "High reasoning"}]
            legacy = (json.dumps(old, indent=2) + "\n").encode()
            path.write_bytes(legacy)
            selected = self.home / "openrouter-codex-selection.json"
            record = json.loads(selected.read_text())
            record["catalog_sha256"] = tool["sha"](legacy)
            selected.write_text(json.dumps(record))
            tool["prepare"]()
        upgraded = json.loads(path.read_text())["models"]
        self.assertTrue(all([level["effort"] for level in m["supported_reasoning_levels"]]
                            == ["low", "medium", "high"] for m in upgraded))
        backups = list(self.home.glob("openrouter-codex-models.json.backup-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), legacy)

    def test_doctor_identifies_catalog_that_locks_gui_thinking(self):
        chosen = tool["selection"]()
        stale = json.loads(tool["catalog_bytes"](self.home, chosen))
        for model in stale["models"]:
            model["supported_reasoning_levels"] = [{"effort": "high"}]
        catalog = self.home / "bcu" / "models.json"
        catalog.parent.mkdir()
        catalog.write_text(json.dumps(stale))
        controller = SimpleNamespace(state=self.home / "absent-state.json", catalog=catalog)
        recorded = []
        with patch.dict(tool["doctor"].__globals__, {
            "mixed_controller": lambda: controller,
            "router_module": lambda: SimpleNamespace(health=lambda: {}),
            "key_exists": lambda: False,
        }), patch.object(tool["UI"], "row", side_effect=lambda *args, **kwargs: recorded.append(args)):
            tool["doctor"]()
        self.assertIn("model sync", next(args[1] for args in recorded if args[0] == "GUI THINKING"))

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
                                  (["docs", "agents"], "agents setup"),
                                  (["docs", "setup"], "setup --check"),
                                  (["reasoning"], "anthropic/claude-opus-5"),
                                  (["agents", "status"], "Codex default"),
                                  (["model", "list"], "anthropic/claude-opus-5"),
                                  (["models", "list"], "anthropic/claude-opus-5")):
            result = subprocess.run([sys.executable, str(TOOL), "--no-color", *command],
                                    text=True, capture_output=True, check=True)
            self.assertIn(expected, result.stdout)
            self.assertNotIn("\033[", result.stdout)

    def test_setup_preflight_is_read_only_and_noninteractive_cli_rejects_wizard(self):
        with patch.dict(tool["setup_checks"].__globals__, {"ensure_macos": lambda: None}):
            with patch.object(tool["shutil"], "which", return_value="/usr/local/bin/codex"):
                self.assertEqual(tool["setup_checks"](), [])
        self.assertEqual(list(self.home.iterdir()), [])
        result = subprocess.run([sys.executable, str(TOOL), "setup"],
                                text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn("interactive terminal", result.stderr)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_setup_wizard_reuses_key_and_only_runs_approved_steps(self):
        actions = []
        globals_ = tool["setup_wizard"].__globals__
        overrides = {
            "setup_checks": lambda: [],
            "install": lambda: actions.append("install"),
            "prepare": lambda: actions.append("prepare"),
            "model_manager": lambda chosen: actions.append("models"),
            "key_exists": lambda: True,
            "save_key": lambda: actions.append("key"),
            "mixed_on": lambda: actions.append("desktop"),
            "agents_command": lambda action: actions.append("agents:" + action),
            "setup_confirm": lambda prompt, default=True: {
                "Browse": True, "Replace": False, "Enable": True, "Set": True,
            }[prompt.split()[0]],
        }
        with patch.dict(globals_, overrides):
            with patch.dict(os.environ, {"TERM": "xterm-256color"}), \
                 patch.object(sys.stdin, "isatty", return_value=True), \
                 patch.object(sys.stdout, "isatty", return_value=True), \
                 patch.object(sys.stderr, "isatty", return_value=True):
                tool["setup_wizard"]()
        self.assertEqual(actions, ["install", "prepare", "models", "desktop", "agents:setup"])
        self.assertEqual(list(self.home.iterdir()), [])

    def test_setup_check_aborts_before_writing_and_does_not_prompt(self):
        with patch.dict(tool["setup_wizard"].__globals__, {
            "setup_checks": lambda: ["Codex CLI missing"],
            "install": lambda: self.fail("must not install after failed preflight"),
        }):
            with self.assertRaisesRegex(tool["SetupError"], "Codex CLI missing"):
                tool["setup_wizard"](True)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_setup_declining_key_never_activates_desktop(self):
        actions = []
        with patch.dict(tool["setup_wizard"].__globals__, {
            "setup_checks": lambda: [],
            "install": lambda: actions.append("install"),
            "prepare": lambda: actions.append("prepare"),
            "key_exists": lambda: False,
            "save_key": lambda: self.fail("key entry was declined"),
            "mixed_on": lambda: self.fail("must not activate without a key"),
            "setup_confirm": lambda prompt, default=True: False,
        }):
            with patch.dict(os.environ, {"TERM": "dumb"}), \
                 patch.object(sys.stdin, "isatty", return_value=True), \
                 patch.object(sys.stdout, "isatty", return_value=True), \
                 patch.object(sys.stderr, "isatty", return_value=True):
                with self.assertRaisesRegex(tool["SetupError"], "before desktop activation"):
                    tool["setup_wizard"]()
        self.assertEqual(actions, ["install", "prepare"])
        self.assertEqual(list(self.home.iterdir()), [])

    def test_reasoning_per_model_updates_selector_and_cli_profile(self):
        chosen = tool["selection"]()
        default = chosen["default"]
        other = chosen["models"][0]["id"]
        if other == default:
            other = chosen["models"][1]["id"]
        tool["reasoning_command"]("low", default)
        tool["reasoning_command"]("medium", other)
        chosen = tool["selection"]()
        models = {m["slug"]: m for m in json.loads((self.home / "openrouter-codex-models.json").read_text())["models"]}
        self.assertEqual(models[default]["default_reasoning_level"], "low")
        self.assertEqual(models[other]["default_reasoning_level"], "medium")
        self.assertEqual([level["effort"] for level in models[default]["supported_reasoning_levels"]],
                         ["low", "medium", "high"])
        self.assertEqual(tomllib.loads((self.home / "openrouter.config.toml").read_text())["model_reasoning_effort"], "low")
        self.assertEqual(tool["manager_result"](chosen, {default}, default, [])['models'][0]['reasoning_effort'], "low")
        staged = tool["manager_result"](chosen, {default}, default, [], {default: "medium"})
        self.assertEqual(staged["models"][0]["reasoning_effort"], "medium")
        self.assertEqual(tool["manager_result"](chosen, {default}, default, [])["models"][0]["reasoning_effort"], "low")
        chosen["default"] = other
        tool["update_selection"](chosen)
        self.assertEqual(tomllib.loads((self.home / "openrouter.config.toml").read_text())["model_reasoning_effort"], "medium")
        with self.assertRaises(tool["SetupError"]):
            tool["reasoning_command"]("low", "unselected/model")

    def test_reasoning_cli_persists_without_key_or_network(self):
        result = subprocess.run([sys.executable, str(TOOL), "--no-color", "reasoning", "medium",
                                 "--model", "anthropic/claude-opus-5"],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        chosen = tool["selection"]()
        self.assertEqual(tool["selected_effort"](chosen), "medium")
        self.assertEqual(tomllib.loads((self.home / "openrouter.config.toml").read_text())["model_reasoning_effort"],
                         "medium")

    def test_agents_setup_and_restore_preserve_unrelated_codex_edits(self):
        config = self.home / "config.toml"
        config.write_text('model = "gpt-native"\nmodel_reasoning_effort = "xhigh"\n'
                          '[agents]\nenabled = false\n# Keep my own agent notes\n'
                          '[agents.reviewer]\ndescription = "private role"\n'
                          '[desktop]\nappearance = "dark"\n')
        tool["agents_command"]("setup", effort="medium", limit=3)
        active = tomllib.loads(config.read_text())
        self.assertEqual(active["model_reasoning_effort"], "xhigh")
        self.assertEqual(active["agents"]["default_subagent_model"], tool["selection"]()["default"])
        self.assertEqual(active["agents"]["default_subagent_reasoning_effort"], "medium")
        self.assertEqual(active["agents"]["max_concurrent_threads_per_session"], 3)
        self.assertTrue((self.home / "bcu/agents-state.json").exists())
        tool["agents_command"]("setup", effort="low", limit=2)
        config.write_text(config.read_text().replace('appearance = "dark"', 'appearance = "light"'))
        tool["agents_command"]("restore")
        restored = tomllib.loads(config.read_text())
        self.assertFalse(restored["agents"]["enabled"])
        self.assertNotIn("default_subagent_model", restored["agents"])
        self.assertNotIn("default_subagent_reasoning_effort", restored["agents"])
        self.assertNotIn("max_concurrent_threads_per_session", restored["agents"])
        self.assertEqual(restored["desktop"]["appearance"], "light")
        self.assertIn("# Keep my own agent notes", config.read_text())
        self.assertFalse((self.home / "bcu/agents-state.json").exists())

    def test_agents_refuse_to_overwrite_external_changes(self):
        config = self.home / "config.toml"
        config.write_text('[agents]\nmax_concurrent_threads_per_session = 5\n')
        tool["agents_command"]("setup")
        config.write_text(config.read_text().replace('max_concurrent_threads_per_session = 2',
                                                      'max_concurrent_threads_per_session = 7'))
        with self.assertRaises(tool["SetupError"]):
            tool["agents_command"]("restore")
        self.assertIn("max_concurrent_threads_per_session = 7", config.read_text())

    def test_agents_setup_handles_missing_table_and_rejects_bad_model(self):
        config = self.home / "config.toml"
        config.write_text('model = "gpt-native"\n[agents.reviewer]\ndescription = "Reviewer"\n')
        with self.assertRaises(tool["SetupError"]):
            tool["agents_command"]("setup", "other/model")
        tool["agents_command"]("setup")
        self.assertTrue(tomllib.loads(config.read_text())["agents"]["enabled"])
        tool["agents_command"]("restore")
        self.assertNotIn("default_subagent_model", tomllib.loads(config.read_text())["agents"])

    def test_off_restores_bcu_agent_defaults_and_removal_is_guarded(self):
        config = self.home / "config.toml"
        config.write_text('model = "gpt-native"\n[desktop]\nappearance = "dark"\n')
        tool["agents_command"]("setup")
        selected = tool["selection"]()
        selected["models"] = [m for m in selected["models"] if m["id"] != selected["default"]]
        selected["default"] = selected["models"][0]["id"]
        with self.assertRaisesRegex(tool["SetupError"], "subagent default"):
            tool["update_selection"](selected)
        with patch.dict(tool["mixed_off"].__globals__, {"mixed_controller": lambda: type(
                "StoppedRouter", (), {"disable": lambda self: None})()}):
            tool["mixed_off"]()
        restored = tomllib.loads(config.read_text())
        self.assertNotIn("default_subagent_model", restored.get("agents", {}))
        self.assertEqual(restored["desktop"]["appearance"], "dark")
        self.assertFalse((self.home / "bcu/agents-state.json").exists())

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
            self.assertEqual(primary.with_name("bcu_doom_render.py").read_bytes(),
                             TOOL.with_name("bcu_doom_render.py").read_bytes())
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
