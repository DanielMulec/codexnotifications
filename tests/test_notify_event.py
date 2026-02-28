from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    REPO_ROOT
    / ".agents"
    / "skills"
    / "notifications"
    / "scripts"
    / "notify_event.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("notify_event", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load notify_event module spec")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NotifyEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = load_module()

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)

        self.log_path = Path(self.tempdir.name) / "notify_hook.log"
        self.previous_log_override = os.environ.get("CODEX_NOTIFY_LOG")
        self.previous_wav_override = os.environ.get("CODEX_NOTIFY_WAV")
        os.environ["CODEX_NOTIFY_LOG"] = str(self.log_path)

        self.addCleanup(self._restore_env)

    def _restore_env(self) -> None:
        if self.previous_log_override is None:
            os.environ.pop("CODEX_NOTIFY_LOG", None)
        else:
            os.environ["CODEX_NOTIFY_LOG"] = self.previous_log_override

        if self.previous_wav_override is None:
            os.environ.pop("CODEX_NOTIFY_WAV", None)
        else:
            os.environ["CODEX_NOTIFY_WAV"] = self.previous_wav_override

    def read_log_events(self) -> list[dict[str, object]]:
        if not self.log_path.exists():
            return []
        lines = self.log_path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def test_event_type_prefers_type(self) -> None:
        payload = {
            "type": "agent-turn-complete",
            "event": "legacy-other-event",
        }
        self.assertEqual(self.mod.event_type(payload), "agent-turn-complete")

    def test_event_type_falls_back_to_event(self) -> None:
        payload = {"event": "agent-turn-complete"}
        self.assertEqual(self.mod.event_type(payload), "agent-turn-complete")

    def test_event_type_returns_none_when_missing(self) -> None:
        payload = {"foo": "bar"}
        self.assertIsNone(self.mod.event_type(payload))

    def test_is_supported_event_accepts_turn_complete_variants(self) -> None:
        self.assertTrue(self.mod.is_supported_event("agent-turn-complete"))
        self.assertTrue(self.mod.is_supported_event("assistant-turn-complete"))
        self.assertFalse(self.mod.is_supported_event("approval-requested"))

    def test_main_accepts_type_payload(self) -> None:
        calls: list[str] = []

        def fake_try_play_sound() -> bool:
            calls.append("played")
            return True

        original = self.mod.try_play_sound
        self.mod.try_play_sound = fake_try_play_sound
        try:
            exit_code = self.mod.main(
                ["notify_event.py", json.dumps({"type": "agent-turn-complete"})]
            )
        finally:
            self.mod.try_play_sound = original

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls, ["played"])

    def test_main_ignores_unknown_type(self) -> None:
        calls: list[str] = []

        def fake_try_play_sound() -> bool:
            calls.append("played")
            return True

        original = self.mod.try_play_sound
        self.mod.try_play_sound = fake_try_play_sound
        try:
            exit_code = self.mod.main(["notify_event.py", json.dumps({"type": "other"})])
        finally:
            self.mod.try_play_sound = original

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls, [])

    def test_try_play_sound_windows_prefers_first_successful_backend(self) -> None:
        with (
            mock.patch.object(self.mod.platform, "system", return_value="Windows"),
            mock.patch.object(
                self.mod,
                "play_windows_wav_file",
                return_value=(False, "windows:wav-failed"),
            ),
            mock.patch.object(
                self.mod,
                "play_windows_beep_chime",
                return_value=(True, "windows:winsound.Beep(chime)"),
            ) as beep_mock,
            mock.patch.object(
                self.mod,
                "play_windows_powershell_chime",
                return_value=(True, "windows:powershell.console-beep"),
            ) as ps_mock,
        ):
            success = self.mod.try_play_sound()

        self.assertTrue(success)
        self.assertEqual(self.mod.get_last_backend(), "windows:winsound.Beep(chime)")
        self.assertTrue(beep_mock.called)
        self.assertFalse(ps_mock.called)

    def test_main_invalid_json_logs_invalid_payload_event(self) -> None:
        exit_code = self.mod.main(["notify_event.py", "{bad json"])
        self.assertEqual(exit_code, 0)

        events = self.read_log_events()
        event_names = [str(item.get("event")) for item in events]
        self.assertIn("invoke", event_names)
        self.assertIn("invalid-payload", event_names)


if __name__ == "__main__":
    unittest.main()
