"""Native desktop bridge and distributable bundle safety checks."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import plistlib
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

import test_openrouter_codex as fixtures

tool = fixtures.tool


class DesktopTests(unittest.TestCase):
    setUp = fixtures.OpenRouterCodexTests.setUp

    def test_snapshot_is_read_only_and_excludes_private_config(self):
        config = self.home / "config.toml"
        original = 'private_value = "not-for-desktop"\n[agents]\nenabled = true\ndefault_subagent_model = "author/model"\n'
        config.write_text(original)
        with patch.dict(tool["desktop_snapshot"].__globals__, {
            "key_exists": lambda: self.fail("Snapshot must not use Keychain"),
        }):
            snapshot = tool["desktop_snapshot"]()
        self.assertNotIn("not-for-desktop", json.dumps(snapshot))
        self.assertNotIn(str(self.home), json.dumps(snapshot))
        self.assertEqual(snapshot["agent_model"], "author/model")
        self.assertEqual(snapshot["traffic"]["openrouter_model_concurrency"], 2)
        self.assertEqual(config.read_text(), original)
        self.assertFalse((self.home / "openrouter-codex-selection.json").exists())

    def test_status_command_is_pure_json(self):
        output = io.StringIO()
        with patch.object(sys, "argv", ["bobocodexultra", "app", "status"]), redirect_stdout(output):
            tool["main"]()
        self.assertIn("models", json.loads(output.getvalue()))

    def test_save_traffic_preserves_other_limits_and_does_not_restart(self):
        path = self.home / "bcu/traffic.json"
        path.parent.mkdir()
        original = '{"native_concurrency": 7, "jitter": 0.5}\n'
        path.write_text(original)
        with patch.dict(tool["desktop_traffic"].__globals__, {
            "mixed_on": lambda: self.fail("Saving limits must not restart routing"),
        }):
            tool["desktop_traffic"](["openrouter_concurrency=4", "openrouter_model_concurrency=1"])
        settings = json.loads(path.read_text())
        self.assertEqual(settings["native_concurrency"], 7)
        self.assertEqual(settings["jitter"], 0.5)
        self.assertEqual(settings["openrouter_concurrency"], 4)
        self.assertEqual(next(path.parent.glob("traffic.backup-*.json")).read_text(), original)

    def test_invalid_traffic_never_replaces_existing_file(self):
        path = self.home / "bcu/traffic.json"
        path.parent.mkdir()
        path.write_text('{"openrouter_concurrency": 3}')
        original = path.read_bytes()
        for updates in (["unknown=4"], ["queue_limit=999"], ["openrouter_concurrency=1.5"],
                        ["max_attempts=true"], ["jitter=NaN"], ["backoff_base=30", "backoff_max=2"]):
            with self.subTest(updates=updates), self.assertRaises((ValueError, tool["SetupError"])):
                tool["desktop_traffic"](updates)
            self.assertEqual(path.read_bytes(), original)

    def test_symlinked_traffic_is_refused(self):
        path = self.home / "bcu/traffic.json"
        path.parent.mkdir()
        other = self.home / "untouched.json"
        other.write_text("{}")
        path.symlink_to(other)
        with self.assertRaises(tool["SetupError"]):
            tool["desktop_traffic"](["queue_limit=20"])
        self.assertEqual(other.read_text(), "{}")

    def fake_build_command(self, args, **kwargs):
        if args[0] == "/usr/bin/swiftc":
            Path(args[args.index("-o") + 1]).write_bytes(b"test executable")
        elif "--export-icon" in args:
            Path(args[-1]).write_bytes(b"test icon")
        elif args[0] == "/usr/bin/iconutil":
            Path(args[-1]).write_bytes(b"test icns")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def test_distribution_bundle_has_no_local_python_or_user_data(self):
        destination = Path(self.temp.name) / "Bobo Codex Ultra.app"
        with patch.dict(tool["build_desktop_bundle"].__globals__, {"ensure_macos": lambda: None}), \
                patch("subprocess.run", side_effect=self.fake_build_command):
            tool["build_desktop_bundle"](destination)
        info = plistlib.loads((destination / "Contents/Info.plist").read_bytes())
        self.assertNotIn("BCUPythonExecutable", info)
        self.assertEqual(info["CFBundleIdentifier"], "com.bobocodexultra.menubar")
        self.assertEqual(info["CFBundleShortVersionString"], "0.3.0")
        names = {file.name for file in (destination / "Contents/Resources").iterdir()}
        self.assertEqual(names, {"AppIcon.icns", "openrouter-codex", "BCUStatus.swift", "bcu_router.py",
                                 "bcu_games.py", "bcu_doom_render.py", "LICENSE", "INTER-LICENSE.txt"})
        self.assertEqual((destination / "Contents/Resources/openrouter-codex").read_bytes(), fixtures.TOOL.read_bytes())

    def test_bundle_refuses_unrelated_app_and_symlink(self):
        destination = Path(self.temp.name) / "Unrelated.app"
        destination.mkdir()
        with self.assertRaises(tool["SetupError"]):
            tool["build_desktop_bundle"](destination)
        link = destination.with_name("Linked.app")
        link.symlink_to(destination)
        with self.assertRaises(tool["SetupError"]):
            tool["build_desktop_bundle"](link)

