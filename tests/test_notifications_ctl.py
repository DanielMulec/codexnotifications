from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Protocol, cast

from tests_support import TomlTable, get_toml_table, load_module_from_path, parse_toml_text

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = (
    REPO_ROOT
    / "skill-src"
    / "notifications"
    / "scripts"
    / "notifications_ctl.py"
)
STATE_MODULE_PATH = (
    REPO_ROOT
    / "skill-src"
    / "notifications"
    / "scripts"
    / "notifications_state.py"
)


class StateModuleProtocol(Protocol):
    SKILL_NOTIFY_COMMAND: str


def load_state_module() -> StateModuleProtocol:
    return cast(
        StateModuleProtocol,
        load_module_from_path("notifications_state", STATE_MODULE_PATH),
    )

SKILL_NOTIFY_COMMAND = load_state_module().SKILL_NOTIFY_COMMAND


def parse_json_stdout(raw_stdout: str) -> dict[str, str]:
    loaded = cast(object, json.loads(raw_stdout.strip()))
    if not isinstance(loaded, dict):
        raise AssertionError("Expected notifications_ctl stdout to be a JSON object")

    payload: dict[str, str] = {}
    for key, value in loaded.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise AssertionError("Expected notifications_ctl JSON payload to contain string fields")
        payload[key] = value
    return payload


class NotificationsCtlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)

        root = Path(self.tempdir.name)
        self.config_path = root / "config.toml"
        self.snapshot_path = root / "snapshot.json"
        self.notify_script_path = root / "notify_event.py"
        self.notify_script_path.write_text("#!/usr/bin/env python3\n", encoding="utf-8")

    def run_ctl(self, *args: str, config_path: Path | None = None) -> tuple[int, dict[str, str]]:
        cfg = config_path if config_path is not None else self.config_path
        command = [
            sys.executable,
            str(SCRIPT_PATH),
            *args,
            "--config",
            str(cfg),
            "--snapshot",
            str(self.snapshot_path),
            "--notify-script",
            str(self.notify_script_path),
        ]
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
        payload = parse_json_stdout(completed.stdout)
        return completed.returncode, payload

    def read_config(self) -> TomlTable:
        if not self.config_path.exists() or not self.config_path.read_text(
            encoding="utf-8"
        ).strip():
            return {}
        return parse_toml_text(self.config_path.read_text(encoding="utf-8"))

    def test_command_parsing(self) -> None:
        return_code, payload = self.run_ctl("on")
        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "applied")

        return_code, payload = self.run_ctl("off")
        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "applied")

        return_code, payload = self.run_ctl()
        self.assertEqual(return_code, 2)
        self.assertEqual(payload["status"], "invalid-input")
        self.assertIn("Usage: $notifications on|off", payload["next_action"])

        return_code, payload = self.run_ctl("foo")
        self.assertEqual(return_code, 2)
        self.assertEqual(payload["status"], "invalid-input")
        self.assertIn("Usage: $notifications on|off", payload["next_action"])

    def test_on_from_clean_config(self) -> None:
        return_code, payload = self.run_ctl("on")
        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "applied")
        self.assertTrue(self.snapshot_path.exists())

        config = self.read_config()
        tui = get_toml_table(config, "tui")
        expected_notify: list[str] = [
            SKILL_NOTIFY_COMMAND,
            str(self.notify_script_path.resolve()),
        ]
        expected_notifications: list[str] = ["approval-requested"]
        self.assertEqual(
            config["notify"],
            expected_notify,
        )
        self.assertEqual(tui["notifications"], expected_notifications)
        self.assertEqual(tui["notification_method"], "bel")

    def test_off_restores_prior_values(self) -> None:
        original_toml = (
            'model = "gpt-5"\n'
            'notify = ["python3", "/tmp/original_notify.py"]\n\n'
            "[tui]\n"
            "notifications = true\n"
            'notification_method = "auto"\n'
        )
        self.config_path.write_text(original_toml, encoding="utf-8")
        expected_document = parse_toml_text(original_toml)

        return_code, payload = self.run_ctl("on")
        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "applied")

        return_code, payload = self.run_ctl("off")
        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "applied")

        restored_document = self.read_config()
        self.assertEqual(restored_document, expected_document)
        self.assertFalse(self.snapshot_path.exists())

    def test_on_is_idempotent(self) -> None:
        return_code, payload = self.run_ctl("on")
        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "applied")
        first_config = self.config_path.read_text(encoding="utf-8")

        return_code, payload = self.run_ctl("on")
        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "already-applied")
        second_config = self.config_path.read_text(encoding="utf-8")

        self.assertEqual(first_config, second_config)

    def test_off_is_idempotent(self) -> None:
        return_code, payload = self.run_ctl("on")
        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "applied")

        return_code, payload = self.run_ctl("off")
        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "applied")

        return_code, payload = self.run_ctl("off")
        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "already-applied")

    def test_blocked_write_returns_guidance(self) -> None:
        # Cross-platform deterministic blocked path:
        # create a file where a parent directory is expected.
        blocked_parent = Path(self.tempdir.name) / "blocked-parent-file"
        blocked_parent.write_text("x", encoding="utf-8")
        blocked_config_path = blocked_parent / "config.toml"
        return_code, payload = self.run_ctl("on", config_path=blocked_config_path)

        self.assertEqual(return_code, 3)
        self.assertEqual(payload["status"], "blocked")
        self.assertIn("sandbox_workspace_write.writable_roots", payload["next_action"])
        self.assertIn("policy that permits", payload["next_action"])
        self.assertFalse(blocked_config_path.exists())

    def test_failed_parse_returns_exit_code_4(self) -> None:
        self.config_path.write_text("[broken\n", encoding="utf-8")

        return_code, payload = self.run_ctl("on")
        self.assertEqual(return_code, 4)
        self.assertEqual(payload["status"], "failed")
        self.assertIn("Failed to parse config TOML", payload["rationale"])

    def test_off_with_malformed_snapshot_reports_warning_suffix(self) -> None:
        return_code, payload = self.run_ctl("on")
        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "applied")

        self.snapshot_path.write_text("{bad json", encoding="utf-8")

        return_code, payload = self.run_ctl("off")
        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "applied")
        self.assertIn("Snapshot format invalid", payload["rationale"])

        return_code, payload = self.run_ctl("off")
        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "already-applied")
        self.assertIn("Snapshot format invalid", payload["rationale"])

    def test_unrelated_keys_preserved_across_on_off(self) -> None:
        original_toml = (
            'model = "gpt-5"\n'
            'notify = ["python3", "/tmp/original_notify.py"]\n\n'
            "[profiles]\n"
            "default = \"dev\"\n\n"
            "[profiles.dev]\n"
            "temperature = 0.2\n\n"
            "[tui]\n"
            "notifications = true\n"
            'notification_method = "auto"\n'
        )
        self.config_path.write_text(original_toml, encoding="utf-8")
        expected_document = parse_toml_text(original_toml)

        return_code, payload = self.run_ctl("on")
        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "applied")

        return_code, payload = self.run_ctl("off")
        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "applied")

        self.assertEqual(self.read_config(), expected_document)

    def test_comments_preserved_across_on_off(self) -> None:
        original_toml = (
            "# user note: keep my model stable\n"
            'model = "gpt-5"\n'
            'notify = ["python3", "/tmp/original_notify.py"]\n\n'
            "[tui]\n"
            "# user note: I prefer auto mode\n"
            "notifications = true\n"
            'notification_method = "auto"\n'
        )
        self.config_path.write_text(original_toml, encoding="utf-8")

        return_code, payload = self.run_ctl("on")
        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "applied")

        return_code, payload = self.run_ctl("off")
        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "applied")

        restored_text = self.config_path.read_text(encoding="utf-8")
        self.assertIn("# user note: keep my model stable", restored_text)
        self.assertIn("# user note: I prefer auto mode", restored_text)


if __name__ == "__main__":
    unittest.main()
