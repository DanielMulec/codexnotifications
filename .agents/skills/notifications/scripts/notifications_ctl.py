#!/usr/bin/env python3
"""Control script for $notifications on|off."""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import errno
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import tomllib
from typing import Any

USAGE_TEXT = "Usage: $notifications on|off"
SNAPSHOT_FILENAME = ".codex-notifications-v1-snapshot.json"
ALLOWED_COMMANDS = {"on", "off"}

STATUS_APPLIED = "applied"
STATUS_ALREADY_APPLIED = "already-applied"
STATUS_BLOCKED = "blocked"
STATUS_INVALID_INPUT = "invalid-input"
STATUS_FAILED = "failed"

_BARE_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def build_result(
    action: str, status: str, rationale: str, next_action: str = ""
) -> dict[str, str]:
    return {
        "action": action,
        "status": status,
        "rationale": rationale,
        "next_action": next_action,
    }


def emit_result(result: dict[str, str]) -> None:
    print(json.dumps(result, ensure_ascii=True))


def is_permission_block(exc: BaseException) -> bool:
    if isinstance(exc, PermissionError):
        return True
    if isinstance(exc, OSError):
        return exc.errno in {errno.EACCES, errno.EPERM, errno.EROFS}
    return False


def resolve_config_path(config_override: str | None) -> Path:
    if config_override:
        return Path(config_override).expanduser()

    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "config.toml"

    return Path.home() / ".codex" / "config.toml"


def resolve_snapshot_path(config_path: Path, snapshot_override: str | None) -> Path:
    if snapshot_override:
        return Path(snapshot_override).expanduser()
    return config_path.parent / SNAPSHOT_FILENAME


def resolve_notify_script_path(notify_override: str | None) -> Path:
    if notify_override:
        return Path(notify_override).expanduser().resolve()
    return Path(__file__).resolve().with_name("notify_event.py")


def prepare_config_directory(config_path: Path) -> tuple[bool, str | None]:
    parent = config_path.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return (
            False,
            f"Cannot create config directory '{parent}': {exc}",
        )

    probe_path: Path | None = None
    try:
        fd, raw_path = tempfile.mkstemp(
            prefix=".codexnotifications-write-probe-",
            dir=parent,
        )
        os.close(fd)
        probe_path = Path(raw_path)
    except OSError as exc:
        return (
            False,
            f"Config directory '{parent}' is not writable: {exc}",
        )
    finally:
        if probe_path is not None:
            try:
                probe_path.unlink(missing_ok=True)
            except OSError:
                pass

    return True, None


def load_toml_document(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return {}

    parsed = tomllib.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("TOML root must be a table")
    return parsed


def format_key(key: str) -> str:
    if _BARE_KEY_RE.match(key):
        return key
    return json.dumps(key, ensure_ascii=True)


def format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value):
            return "nan"
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=True)
    if isinstance(value, list):
        return "[" + ", ".join(format_value(item) for item in value) + "]"
    if isinstance(value, dt.datetime):
        return value.isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, dt.time):
        return value.isoformat()
    if isinstance(value, dict):
        parts = [
            f"{format_key(str(key))} = {format_value(item)}"
            for key, item in value.items()
        ]
        return "{ " + ", ".join(parts) + " }"

    raise TypeError(f"Unsupported TOML value type: {type(value).__name__}")


def emit_table(lines: list[str], path_parts: tuple[str, ...], table: dict[str, Any]) -> None:
    lines.append("[" + ".".join(format_key(part) for part in path_parts) + "]")

    scalars: list[tuple[str, Any]] = []
    tables: list[tuple[str, dict[str, Any]]] = []
    for key, value in table.items():
        if isinstance(value, dict):
            tables.append((key, value))
        else:
            scalars.append((key, value))

    for key, value in scalars:
        lines.append(f"{format_key(key)} = {format_value(value)}")

    if scalars and tables:
        lines.append("")

    for index, (key, child) in enumerate(tables):
        emit_table(lines, path_parts + (key,), child)
        if index != len(tables) - 1:
            lines.append("")


def dump_toml_document(document: dict[str, Any]) -> str:
    lines: list[str] = []

    root_scalars: list[tuple[str, Any]] = []
    root_tables: list[tuple[str, dict[str, Any]]] = []
    for key, value in document.items():
        if isinstance(value, dict):
            root_tables.append((key, value))
        else:
            root_scalars.append((key, value))

    for key, value in root_scalars:
        lines.append(f"{format_key(key)} = {format_value(value)}")

    if root_scalars and root_tables:
        lines.append("")

    for index, (key, table) in enumerate(root_tables):
        emit_table(lines, (key,), table)
        if index != len(root_tables) - 1:
            lines.append("")

    serialized = "\n".join(lines).rstrip()
    return (serialized + "\n") if serialized else ""


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_raw = tempfile.mkstemp(prefix=f".{path.name}.tmp-", dir=path.parent)
    temp_path = Path(temp_raw)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())

        if path.exists():
            try:
                os.chmod(temp_path, path.stat().st_mode & 0o777)
            except OSError:
                pass

        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def write_toml_document(path: Path, document: dict[str, Any]) -> None:
    atomic_write_text(path, dump_toml_document(document))


def key_state(value_present: bool, value: Any | None = None) -> dict[str, Any]:
    if value_present:
        return {"present": True, "value": copy.deepcopy(value)}
    return {"present": False}


def capture_prior_state(document: dict[str, Any]) -> dict[str, Any]:
    prior: dict[str, Any] = {}
    prior["notify"] = key_state("notify" in document, document.get("notify"))

    tui = document.get("tui")
    if isinstance(tui, dict):
        prior["tui.notifications"] = key_state(
            "notifications" in tui, tui.get("notifications")
        )
        prior["tui.notification_method"] = key_state(
            "notification_method" in tui, tui.get("notification_method")
        )
    else:
        prior["tui.notifications"] = key_state(False)
        prior["tui.notification_method"] = key_state(False)

    return prior


def write_snapshot(
    snapshot_path: Path, config_path: Path, prior_state: dict[str, Any]
) -> None:
    payload = {
        "version": 1,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "config_path": str(config_path),
        "prior": prior_state,
    }
    atomic_write_text(snapshot_path, json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def load_snapshot(snapshot_path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not snapshot_path.exists():
        return None, None

    try:
        raw = snapshot_path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"Snapshot read failed: {exc}"

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"Snapshot format invalid: {exc}"

    if not isinstance(payload, dict):
        return None, "Snapshot format invalid: root is not an object"

    prior = payload.get("prior")
    if not isinstance(prior, dict):
        return None, "Snapshot format invalid: missing 'prior' object"

    return prior, None


def remove_snapshot(snapshot_path: Path) -> None:
    snapshot_path.unlink(missing_ok=True)


def normalized_path(path_value: str) -> str:
    return str(Path(path_value).expanduser().resolve())


def notify_target_value(notify_script_path: Path) -> list[str]:
    return ["python3", str(notify_script_path)]


def is_skill_notify_value(value: Any, notify_script_path: Path) -> bool:
    if not isinstance(value, list) or len(value) != 2:
        return False

    command, script_path = value
    if command != "python3" or not isinstance(script_path, str):
        return False

    try:
        return normalized_path(script_path) == str(notify_script_path)
    except OSError:
        return False


def is_target_on(document: dict[str, Any], notify_script_path: Path) -> bool:
    notify_ok = is_skill_notify_value(document.get("notify"), notify_script_path)
    tui = document.get("tui")
    if not isinstance(tui, dict):
        return False

    return (
        notify_ok
        and tui.get("notifications") == ["approval-requested"]
        and tui.get("notification_method") == "bel"
    )


def apply_on_state(document: dict[str, Any], notify_script_path: Path) -> bool:
    changed = False

    target_notify = notify_target_value(notify_script_path)
    if document.get("notify") != target_notify:
        document["notify"] = target_notify
        changed = True

    tui = document.get("tui")
    if not isinstance(tui, dict):
        tui = {}
        document["tui"] = tui
        changed = True

    if tui.get("notifications") != ["approval-requested"]:
        tui["notifications"] = ["approval-requested"]
        changed = True

    if tui.get("notification_method") != "bel":
        tui["notification_method"] = "bel"
        changed = True

    return changed


def restore_key(document: dict[str, Any], key: str, state: dict[str, Any] | None) -> None:
    if state and state.get("present"):
        document[key] = copy.deepcopy(state.get("value"))
    else:
        document.pop(key, None)


def restore_tui_key(
    document: dict[str, Any], key: str, state: dict[str, Any] | None
) -> None:
    tui = document.get("tui")
    if state and state.get("present"):
        if not isinstance(tui, dict):
            tui = {}
            document["tui"] = tui
        tui[key] = copy.deepcopy(state.get("value"))
        return

    if isinstance(tui, dict):
        tui.pop(key, None)
        if not tui:
            document.pop("tui", None)


def apply_snapshot_restore(document: dict[str, Any], prior_state: dict[str, Any]) -> bool:
    before = copy.deepcopy(document)

    restore_key(document, "notify", prior_state.get("notify"))
    restore_tui_key(document, "notifications", prior_state.get("tui.notifications"))
    restore_tui_key(
        document,
        "notification_method",
        prior_state.get("tui.notification_method"),
    )

    return before != document


def apply_safe_off_without_snapshot(
    document: dict[str, Any], notify_script_path: Path
) -> bool:
    changed = False

    notify_value = document.get("notify")
    skill_notify = is_skill_notify_value(notify_value, notify_script_path)
    if skill_notify:
        document.pop("notify", None)
        changed = True

    tui = document.get("tui")
    if isinstance(tui, dict):
        notifications = tui.get("notifications")
        notification_method = tui.get("notification_method")
        skill_approval_override = (
            notifications == ["approval-requested"] and notification_method == "bel"
        )
        if (skill_notify or skill_approval_override) and notifications is not False:
            tui["notifications"] = False
            changed = True

    return changed


def blocked_result(action: str, reason: str) -> dict[str, str]:
    return build_result(
        action=action,
        status=STATUS_BLOCKED,
        rationale=reason,
        next_action=(
            "Add the config directory to sandbox_workspace_write.writable_roots or rerun "
            "with a policy that permits writing the global Codex config."
        ),
    )


def failed_result(action: str, reason: str) -> dict[str, str]:
    return build_result(
        action=action,
        status=STATUS_FAILED,
        rationale=reason,
        next_action="Inspect the error and rerun after correcting the config or filesystem state.",
    )


def execute_on(
    document: dict[str, Any], config_path: Path, snapshot_path: Path, notify_script_path: Path
) -> dict[str, str]:
    action = "$notifications on"

    if is_target_on(document, notify_script_path):
        return build_result(
            action=action,
            status=STATUS_ALREADY_APPLIED,
            rationale="Config already matches the v1 notifications-on target state.",
        )

    prior_state = capture_prior_state(document)
    apply_on_state(document, notify_script_path)

    try:
        write_snapshot(snapshot_path, config_path, prior_state)
        write_toml_document(config_path, document)
    except BaseException as exc:
        try:
            remove_snapshot(snapshot_path)
        except OSError:
            pass
        if is_permission_block(exc):
            return blocked_result(action, f"Global config write blocked: {exc}")
        return failed_result(action, f"Failed to apply notifications on: {exc}")

    return build_result(
        action=action,
        status=STATUS_APPLIED,
        rationale="Snapshot saved and global config updated for completion and approval alerts.",
    )


def execute_off(
    document: dict[str, Any],
    config_path: Path,
    snapshot_path: Path,
    notify_script_path: Path,
) -> dict[str, str]:
    action = "$notifications off"

    prior_state, snapshot_warning = load_snapshot(snapshot_path)
    warning_suffix = f" ({snapshot_warning})" if snapshot_warning else ""

    if prior_state is not None:
        changed = apply_snapshot_restore(document, prior_state)
        try:
            if changed:
                write_toml_document(config_path, document)
            remove_snapshot(snapshot_path)
        except BaseException as exc:
            if is_permission_block(exc):
                return blocked_result(action, f"Global config write blocked: {exc}")
            return failed_result(action, f"Failed to apply notifications off: {exc}")

        return build_result(
            action=action,
            status=STATUS_APPLIED,
            rationale="Restored prior user notification settings from snapshot" + warning_suffix + ".",
        )

    changed = apply_safe_off_without_snapshot(document, notify_script_path)
    if not changed:
        return build_result(
            action=action,
            status=STATUS_ALREADY_APPLIED,
            rationale="Notifications policy is already off and no snapshot restore was required"
            + warning_suffix
            + ".",
        )

    try:
        write_toml_document(config_path, document)
    except BaseException as exc:
        if is_permission_block(exc):
            return blocked_result(action, f"Global config write blocked: {exc}")
        return failed_result(action, f"Failed to apply notifications off: {exc}")

    return build_result(
        action=action,
        status=STATUS_APPLIED,
        rationale="Disabled skill-managed notification overrides without snapshot restore"
        + warning_suffix
        + ".",
    )


def execute_command(
    command: str,
    config_override: str | None,
    snapshot_override: str | None,
    notify_override: str | None,
) -> dict[str, str]:
    action = f"$notifications {command}"

    if command not in ALLOWED_COMMANDS:
        return build_result(
            action=action,
            status=STATUS_INVALID_INPUT,
            rationale=f"Invalid command argument '{command}'.",
            next_action=USAGE_TEXT,
        )

    config_path = resolve_config_path(config_override)
    snapshot_path = resolve_snapshot_path(config_path, snapshot_override)
    notify_script_path = resolve_notify_script_path(notify_override)

    writable, blocked_reason = prepare_config_directory(config_path)
    if not writable:
        return blocked_result(action, blocked_reason or "Config path is not writable.")

    try:
        document = load_toml_document(config_path)
    except BaseException as exc:
        if is_permission_block(exc):
            return blocked_result(action, f"Global config read blocked: {exc}")
        return failed_result(action, f"Failed to parse config TOML: {exc}")

    if command == "on":
        return execute_on(document, config_path, snapshot_path, notify_script_path)
    return execute_off(document, config_path, snapshot_path, notify_script_path)


def parse_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("command", nargs="?")
    parser.add_argument("--config")
    parser.add_argument("--snapshot")
    parser.add_argument("--notify-script")
    parser.add_argument("-h", "--help", action="store_true")
    return parser.parse_known_args(argv)


def exit_code_for_status(status: str) -> int:
    if status in {STATUS_APPLIED, STATUS_ALREADY_APPLIED}:
        return 0
    if status == STATUS_INVALID_INPUT:
        return 2
    if status == STATUS_BLOCKED:
        return 3
    return 4


def main(argv: list[str] | None = None) -> int:
    cli_argv = argv if argv is not None else sys.argv[1:]

    try:
        args, extras = parse_args(cli_argv)
    except BaseException as exc:
        result = failed_result("$notifications <parse>", f"Argument parsing failed: {exc}")
        emit_result(result)
        return exit_code_for_status(result["status"])

    if args.help:
        emit_result(
            build_result(
                action="$notifications help",
                status=STATUS_INVALID_INPUT,
                rationale="Help requested.",
                next_action=USAGE_TEXT,
            )
        )
        return 2

    if extras or args.command is None:
        result = build_result(
            action="$notifications <missing>",
            status=STATUS_INVALID_INPUT,
            rationale="Command requires exactly one argument: on or off.",
            next_action=USAGE_TEXT,
        )
        emit_result(result)
        return exit_code_for_status(result["status"])

    result = execute_command(
        command=args.command,
        config_override=args.config,
        snapshot_override=args.snapshot,
        notify_override=args.notify_script,
    )
    emit_result(result)
    return exit_code_for_status(result["status"])


if __name__ == "__main__":
    raise SystemExit(main())
