from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


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


if __name__ == "__main__":
    unittest.main()
