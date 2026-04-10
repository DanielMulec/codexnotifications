from __future__ import annotations

import json
import os
import tempfile
import unittest
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import ClassVar, Protocol, cast
from unittest import mock

from tests_support import load_module_from_path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    REPO_ROOT
    / ".agents"
    / "skills"
    / "notifications"
    / "scripts"
    / "notify_event.py"
)


class StdoutProtocol(Protocol):
    def write(self, text: str) -> int:
        ...

    def flush(self) -> None:
        ...


class SysProtocol(Protocol):
    stdout: StdoutProtocol


class NotifyEventModule(Protocol):
    platform: object
    sys: SysProtocol
    play_windows_wav_file: object
    play_windows_beep_chime: object
    play_windows_powershell_chime: object
    try_play_sound: Callable[[], bool]

    def run_command(
        self, command: list[str], timeout_seconds: float = ...
    ) -> bool:
        ...

    def event_type(self, payload: Mapping[str, object]) -> str | None:
        ...

    def is_supported_event(self, event_name: str | None) -> bool:
        ...

    def main(self, argv: list[str] | None = None) -> int:
        ...

    def get_last_backend(self) -> str:
        ...


def load_module() -> NotifyEventModule:
    return cast(NotifyEventModule, load_module_from_path("notify_event", MODULE_PATH))


class NotifyEventTests(unittest.TestCase):
    mod: ClassVar[NotifyEventModule]

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
        events: list[dict[str, object]] = []
        for line in lines:
            if not line.strip():
                continue
            loaded = cast(object, json.loads(line))
            if not isinstance(loaded, dict):
                raise AssertionError("Expected notify hook log lines to be JSON objects")
            event: dict[str, object] = {}
            for key, value in loaded.items():
                if not isinstance(key, str):
                    raise AssertionError("Expected notify hook log keys to be strings")
                event[key] = value
            events.append(event)
        return events

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
        payload: dict[str, str] = {"type": "agent-turn-complete"}

        def fake_try_play_sound() -> bool:
            calls.append("played")
            return True

        with mock.patch.object(self.mod, "try_play_sound", new=fake_try_play_sound):
            exit_code = self.mod.main(["notify_event.py", json.dumps(payload)])

        self.assertEqual(exit_code, 0)
        expected_calls: list[str] = ["played"]
        self.assertEqual(calls, expected_calls)

    def test_main_ignores_unknown_type(self) -> None:
        calls: list[str] = []
        payload: dict[str, str] = {"type": "other"}

        def fake_try_play_sound() -> bool:
            calls.append("played")
            return True

        with mock.patch.object(self.mod, "try_play_sound", new=fake_try_play_sound):
            exit_code = self.mod.main(["notify_event.py", json.dumps(payload)])

        self.assertEqual(exit_code, 0)
        expected_calls: list[str] = []
        self.assertEqual(calls, expected_calls)

    def test_try_play_sound_macos_prefers_afplay_with_extended_timeout(self) -> None:
        calls: list[tuple[list[str], float]] = []

        def fake_run_command(command: list[str], timeout_seconds: float = 2.0) -> bool:
            calls.append((command, timeout_seconds))
            return command[0] == "afplay"

        with (
            mock.patch.object(self.mod.platform, "system", return_value="Darwin"),
            mock.patch.object(self.mod, "run_command", new=fake_run_command),
        ):
            success = self.mod.try_play_sound()

        self.assertTrue(success)
        self.assertEqual(self.mod.get_last_backend(), "darwin:afplay")
        expected_calls: list[tuple[list[str], float]] = [
            (["afplay", "/System/Library/Sounds/Glass.aiff"], 5.0)
        ]
        self.assertEqual(
            calls,
            expected_calls,
        )

    def test_try_play_sound_macos_falls_back_to_osascript(self) -> None:
        calls: list[tuple[list[str], float]] = []

        def fake_run_command(command: list[str], timeout_seconds: float = 2.0) -> bool:
            calls.append((command, timeout_seconds))
            return command[0] == "osascript"

        with (
            mock.patch.object(self.mod.platform, "system", return_value="Darwin"),
            mock.patch.object(self.mod, "run_command", new=fake_run_command),
        ):
            success = self.mod.try_play_sound()

        self.assertTrue(success)
        self.assertEqual(self.mod.get_last_backend(), "darwin:osascript-beep")
        expected_calls: list[tuple[list[str], float]] = [
            (["afplay", "/System/Library/Sounds/Glass.aiff"], 5.0),
            (["osascript", "-e", "beep"], 2.0),
        ]
        self.assertEqual(
            calls,
            expected_calls,
        )

    def test_try_play_sound_macos_falls_back_to_terminal_bell(self) -> None:
        calls: list[tuple[list[str], float]] = []

        def fake_run_command(command: list[str], timeout_seconds: float = 2.0) -> bool:
            calls.append((command, timeout_seconds))
            return False

        with (
            mock.patch.object(self.mod.platform, "system", return_value="Darwin"),
            mock.patch.object(self.mod, "run_command", new=fake_run_command),
            mock.patch.object(self.mod.sys.stdout, "write", return_value=1) as write_mock,
            mock.patch.object(self.mod.sys.stdout, "flush") as flush_mock,
        ):
            success = self.mod.try_play_sound()

        self.assertTrue(success)
        self.assertEqual(self.mod.get_last_backend(), "terminal-bell")
        expected_calls: list[tuple[list[str], float]] = [
            (["afplay", "/System/Library/Sounds/Glass.aiff"], 5.0),
            (["osascript", "-e", "beep"], 2.0),
        ]
        self.assertEqual(
            calls,
            expected_calls,
        )
        write_mock.assert_called_once_with("\a")
        flush_mock.assert_called_once_with()

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
