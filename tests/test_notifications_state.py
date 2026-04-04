from __future__ import annotations

import unittest
from pathlib import Path
from typing import ClassVar, Protocol, cast
from unittest import mock

import tomlkit
from tomlkit.toml_document import TOMLDocument

from tests_support import TomlTable, get_toml_table, load_module_from_path, parse_toml_text

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    REPO_ROOT
    / ".agents"
    / "skills"
    / "notifications"
    / "scripts"
    / "notifications_state.py"
)


class NotificationsStateModule(Protocol):
    SKILL_NOTIFY_COMMAND: str
    sys: object
    shutil: object

    def _resolve_skill_python_command(self) -> str:
        ...

    def is_skill_notify_value(self, value: object | None, notify_script_path: Path) -> bool:
        ...

    def apply_on_state(self, document: TOMLDocument, notify_script_path: Path) -> bool:
        ...

    def is_target_on(self, document: TOMLDocument, notify_script_path: Path) -> bool:
        ...

    def apply_snapshot_restore(
        self, document: TOMLDocument, prior_state: dict[str, object]
    ) -> bool:
        ...

    def apply_safe_off_without_snapshot(
        self, document: TOMLDocument, notify_script_path: Path
    ) -> bool:
        ...

    def capture_prior_state(self, document: TOMLDocument) -> dict[str, object]:
        ...


def load_module() -> NotificationsStateModule:
    return cast(
        NotificationsStateModule,
        load_module_from_path("notifications_state", MODULE_PATH),
    )


def document_to_dict(document: TOMLDocument) -> TomlTable:
    raw = tomlkit.dumps(document)
    if not raw.strip():
        return {}
    return parse_toml_text(raw)


class NotificationsStateTests(unittest.TestCase):
    mod: ClassVar[NotificationsStateModule]

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = load_module()

    def test_is_skill_notify_value_accepts_toml_array(self) -> None:
        notify_path = Path("/tmp/notify_event.py").resolve()
        notify_command = self.mod.SKILL_NOTIFY_COMMAND
        document = tomlkit.parse(
            f'notify = ["{notify_command}", "{notify_path}"]\n'
        )

        self.assertTrue(self.mod.is_skill_notify_value(document.get("notify"), notify_path))

    def test_apply_on_state_is_idempotent_after_first_apply(self) -> None:
        notify_path = Path("/tmp/notify_event.py").resolve()
        document = tomlkit.document()
        document["model"] = "gpt-5"

        first_changed = self.mod.apply_on_state(document, notify_path)
        second_changed = self.mod.apply_on_state(document, notify_path)

        self.assertTrue(first_changed)
        self.assertFalse(second_changed)
        self.assertTrue(self.mod.is_target_on(document, notify_path))

        parsed = document_to_dict(document)
        self.assertEqual(parsed["model"], "gpt-5")

    def test_apply_snapshot_restore_restores_values(self) -> None:
        document = tomlkit.parse(
            'model = "gpt-5"\n'
            'notify = ["python3", "/tmp/skill_notify.py"]\n\n'
            "[tui]\n"
            'notifications = ["approval-requested"]\n'
            'notification_method = "bel"\n'
        )
        prior_state = {
            "notify": {"present": True, "value": ["python3", "/tmp/original_notify.py"]},
            "tui.notifications": {"present": True, "value": True},
            "tui.notification_method": {"present": True, "value": "auto"},
        }

        changed = self.mod.apply_snapshot_restore(document, prior_state)

        self.assertTrue(changed)
        parsed = document_to_dict(document)
        self.assertEqual(parsed["model"], "gpt-5")
        self.assertEqual(parsed["notify"], ["python3", "/tmp/original_notify.py"])
        tui = get_toml_table(parsed, "tui")
        self.assertEqual(tui["notifications"], True)
        self.assertEqual(tui["notification_method"], "auto")

    def test_apply_safe_off_without_snapshot_is_idempotent(self) -> None:
        notify_path = Path("/tmp/notify_event.py").resolve()
        notify_command = self.mod.SKILL_NOTIFY_COMMAND
        document = tomlkit.parse(
            'model = "gpt-5"\n'
            f'notify = ["{notify_command}", "{notify_path}"]\n\n'
            "[tui]\n"
            'notifications = ["approval-requested"]\n'
            'notification_method = "bel"\n'
        )

        first_changed = self.mod.apply_safe_off_without_snapshot(document, notify_path)
        second_changed = self.mod.apply_safe_off_without_snapshot(document, notify_path)

        self.assertTrue(first_changed)
        self.assertFalse(second_changed)

        parsed = document_to_dict(document)
        self.assertEqual(parsed["model"], "gpt-5")
        self.assertNotIn("notify", parsed)
        tui = get_toml_table(parsed, "tui")
        self.assertEqual(tui["notifications"], False)
        self.assertEqual(tui["notification_method"], "bel")

    def test_capture_prior_state_returns_plain_python_values(self) -> None:
        document = tomlkit.parse(
            'notify = ["python3", "/tmp/original_notify.py"]\n\n'
            "[tui]\n"
            'notifications = ["approval-requested"]\n'
            'notification_method = "bel"\n'
        )

        prior_state = self.mod.capture_prior_state(document)

        self.assertEqual(
            prior_state["notify"],
            {"present": True, "value": ["python3", "/tmp/original_notify.py"]},
        )
        self.assertEqual(
            prior_state["tui.notifications"],
            {"present": True, "value": ["approval-requested"]},
        )
        self.assertEqual(
            prior_state["tui.notification_method"],
            {"present": True, "value": "bel"},
        )

    def test_resolve_skill_python_command_windows_prefers_sys_executable(self) -> None:
        with (
            mock.patch.object(self.mod.sys, "platform", "win32"),
            mock.patch.object(self.mod.sys, "executable", "/tmp/python-from-sys.exe"),
            mock.patch.object(self.mod.shutil, "which", return_value=None),
        ):
            command = self.mod._resolve_skill_python_command()

        self.assertEqual(command, str(Path("/tmp/python-from-sys.exe").resolve()))

    def test_resolve_skill_python_command_windows_uses_python_fallback(self) -> None:
        def which_side_effect(binary: str) -> str | None:
            mapping = {
                "python": "/tmp/python-from-which.exe",
                "py": "/tmp/python-launcher.exe",
            }
            return mapping.get(binary)

        with (
            mock.patch.object(self.mod.sys, "platform", "win32"),
            mock.patch.object(self.mod.sys, "executable", ""),
            mock.patch.object(self.mod.shutil, "which", side_effect=which_side_effect),
        ):
            command = self.mod._resolve_skill_python_command()

        self.assertEqual(command, str(Path("/tmp/python-from-which.exe").resolve()))


if __name__ == "__main__":
    unittest.main()
