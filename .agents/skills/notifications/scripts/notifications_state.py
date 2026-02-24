#!/usr/bin/env python3
"""State and config mutation helpers for notifications control."""

from __future__ import annotations

import copy
import datetime as dt
import errno
import json
import os
from pathlib import Path
import tempfile
from typing import Any

import tomlkit
from tomlkit.toml_document import TOMLDocument

SNAPSHOT_FILENAME = ".codex-notifications-v1-snapshot.json"
# Canonical values this skill writes when notifications are enabled.
SKILL_NOTIFY_COMMAND = "python3"
TARGET_TUI_NOTIFICATIONS = ("approval-requested",)
TARGET_TUI_NOTIFICATION_METHOD = "bel"


def is_permission_block(exc: BaseException) -> bool:
    # Normalize platform-specific permission errors into one boolean check
    # so callers can map them to a stable "blocked" result.
    if isinstance(exc, PermissionError):
        return True
    if isinstance(exc, OSError):
        return exc.errno in {errno.EACCES, errno.EPERM, errno.EROFS}
    return False


def resolve_config_path(config_override: str | None) -> Path:
    # Resolve user config in priority order:
    # explicit override -> CODEX_HOME -> default ~/.codex.
    if config_override:
        return Path(config_override).expanduser()

    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "config.toml"

    return Path.home() / ".codex" / "config.toml"


def resolve_snapshot_path(config_path: Path, snapshot_override: str | None) -> Path:
    # Snapshot lives next to the target config unless explicitly overridden.
    if snapshot_override:
        return Path(snapshot_override).expanduser()
    return config_path.parent / SNAPSHOT_FILENAME


def resolve_notify_script_path(notify_override: str | None) -> Path:
    # Resolve to an absolute script path so notify matching is deterministic.
    if notify_override:
        return Path(notify_override).expanduser().resolve()
    return Path(__file__).resolve().with_name("notify_event.py")


def prepare_config_directory(config_path: Path) -> tuple[bool, str | None]:
    # Ensure parent directory exists and is writable before any read/write
    # to avoid partial work and confusing mid-flight failures.
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
        # Probe writes fail fast when sandbox rules or permissions block mutations.
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


def load_toml_document(path: Path) -> TOMLDocument:
    # Missing or empty config is treated as an empty document so "on" can
    # initialize settings without special caller logic.
    if not path.exists():
        return tomlkit.document()

    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return tomlkit.document()

    parsed = tomlkit.parse(raw)
    if not isinstance(parsed, TOMLDocument):
        raise ValueError("TOML root must be a table")
    return parsed


def atomic_write_text(path: Path, content: str) -> None:
    # Atomic write pattern:
    # 1) write to temp file in same directory
    # 2) fsync
    # 3) replace destination
    # This protects config files from partial writes.
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_raw = tempfile.mkstemp(prefix=f".{path.name}.tmp-", dir=path.parent)
    temp_path = Path(temp_raw)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            # fsync + replace avoids half-written files if the process exits mid-write.
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


def write_toml_document(path: Path, document: TOMLDocument) -> None:
    # Dedicated helper keeps TOML serialization and write semantics centralized.
    content = tomlkit.dumps(document)
    atomic_write_text(path, content)


def _unwrap_value(value: Any) -> Any:
    # Convert tomlkit container/item types into plain Python values so
    # equality checks and JSON snapshots are stable and predictable.
    if hasattr(value, "unwrap"):
        value = value.unwrap()

    if isinstance(value, dict):
        return {str(key): _unwrap_value(item) for key, item in value.items()}

    if isinstance(value, list):
        return [_unwrap_value(item) for item in value]

    return value


def key_state(value_present: bool, value: Any | None = None) -> dict[str, Any]:
    # Snapshot format stores both key presence and value to distinguish
    # "key absent" from "key present with false/empty value".
    if value_present:
        return {"present": True, "value": copy.deepcopy(_unwrap_value(value))}
    return {"present": False}


def capture_prior_state(document: TOMLDocument) -> dict[str, Any]:
    # Capture only keys this skill may mutate so restore is focused and safe.
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
    # Snapshot is JSON for easy debugging and compatibility with tooling.
    payload = {
        "version": 1,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "config_path": str(config_path),
        "prior": prior_state,
    }
    atomic_write_text(snapshot_path, json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def load_snapshot(snapshot_path: Path) -> tuple[dict[str, Any] | None, str | None]:
    # Returns:
    # - (prior_state, None) when valid
    # - (None, warning_message) when malformed/unreadable
    # This lets callers continue with safe fallback while surfacing context.
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
    # Best-effort cleanup; caller decides whether errors matter.
    snapshot_path.unlink(missing_ok=True)


def normalized_path(path_value: str) -> str:
    # Normalize for reliable path comparisons across relative/tilde input.
    return str(Path(path_value).expanduser().resolve())


def notify_target_value(notify_script_path: Path) -> list[str]:
    # Final shape expected in config.toml for the notify hook command.
    return [SKILL_NOTIFY_COMMAND, str(notify_script_path)]


def is_skill_notify_value(value: Any, notify_script_path: Path) -> bool:
    # True only when notify points to this skill's exact hook command/path.
    unwrapped = _unwrap_value(value)
    if not isinstance(unwrapped, list) or len(unwrapped) != 2:
        return False

    command, script_path = unwrapped
    if command != SKILL_NOTIFY_COMMAND or not isinstance(script_path, str):
        return False

    try:
        return normalized_path(script_path) == str(notify_script_path)
    except OSError:
        return False


def is_target_on(document: TOMLDocument, notify_script_path: Path) -> bool:
    # Detect full "on" state across all controlled keys.
    notify_ok = is_skill_notify_value(document.get("notify"), notify_script_path)
    tui = document.get("tui")
    if not isinstance(tui, dict):
        return False

    return (
        notify_ok
        and _unwrap_value(tui.get("notifications")) == list(TARGET_TUI_NOTIFICATIONS)
        and _unwrap_value(tui.get("notification_method"))
        == TARGET_TUI_NOTIFICATION_METHOD
    )


def apply_on_state(document: TOMLDocument, notify_script_path: Path) -> bool:
    # Mutate in-memory document to target "on" values.
    # Returns True when at least one key changed.
    changed = False

    target_notify = notify_target_value(notify_script_path)
    if _unwrap_value(document.get("notify")) != target_notify:
        document["notify"] = target_notify
        changed = True

    tui = document.get("tui")
    if not isinstance(tui, dict):
        # Create [tui] section only when needed.
        tui = tomlkit.table()
        document["tui"] = tui
        changed = True

    target_notifications = list(TARGET_TUI_NOTIFICATIONS)
    if _unwrap_value(tui.get("notifications")) != target_notifications:
        tui["notifications"] = target_notifications
        changed = True

    if _unwrap_value(tui.get("notification_method")) != TARGET_TUI_NOTIFICATION_METHOD:
        tui["notification_method"] = TARGET_TUI_NOTIFICATION_METHOD
        changed = True

    return changed


def restore_key(document: TOMLDocument, key: str, state: dict[str, Any] | None) -> None:
    # Restore top-level key to previous value or remove if previously absent.
    if state and state.get("present"):
        document[key] = copy.deepcopy(state.get("value"))
    else:
        document.pop(key, None)


def restore_tui_key(
    document: TOMLDocument, key: str, state: dict[str, Any] | None
) -> None:
    # Same restore semantics as restore_key, but scoped to [tui] table.
    tui = document.get("tui")
    if state and state.get("present"):
        if not isinstance(tui, dict):
            # Recreate [tui] if prior state says key existed.
            tui = tomlkit.table()
            document["tui"] = tui
        tui[key] = copy.deepcopy(state.get("value"))
        return

    if isinstance(tui, dict):
        tui.pop(key, None)
        if not tui:
            # Remove empty [tui] table to keep config tidy.
            document.pop("tui", None)


def apply_snapshot_restore(document: TOMLDocument, prior_state: dict[str, Any]) -> bool:
    # Serialize before/after so callers can keep a strict idempotency contract.
    before = tomlkit.dumps(document)

    restore_key(document, "notify", prior_state.get("notify"))
    restore_tui_key(document, "notifications", prior_state.get("tui.notifications"))
    restore_tui_key(
        document,
        "notification_method",
        prior_state.get("tui.notification_method"),
    )

    after = tomlkit.dumps(document)
    return before != after


def apply_safe_off_without_snapshot(
    document: TOMLDocument, notify_script_path: Path
) -> bool:
    # Fallback path when no valid snapshot exists.
    # Goal: undo only this skill's known overrides and avoid touching
    # unrelated custom user settings.
    changed = False

    notify_value = document.get("notify")
    skill_notify = is_skill_notify_value(notify_value, notify_script_path)
    if skill_notify:
        document.pop("notify", None)
        changed = True

    tui = document.get("tui")
    if isinstance(tui, dict):
        notifications = _unwrap_value(tui.get("notifications"))
        notification_method = _unwrap_value(tui.get("notification_method"))
        skill_approval_override = (
            notifications == list(TARGET_TUI_NOTIFICATIONS)
            and notification_method == TARGET_TUI_NOTIFICATION_METHOD
        )
        # Without a snapshot, only disable the exact skill override and leave custom values alone.
        if (skill_notify or skill_approval_override) and notifications is not False:
            tui["notifications"] = False
            changed = True

    return changed
