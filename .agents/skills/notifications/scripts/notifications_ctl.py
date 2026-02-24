#!/usr/bin/env python3
"""Control script for $notifications on|off."""

from __future__ import annotations

import argparse
import json
import sys

USAGE_TEXT = "Usage: $notifications on|off"
ALLOWED_COMMANDS = {"on", "off"}

STATUS_APPLIED = "applied"
STATUS_ALREADY_APPLIED = "already-applied"
STATUS_BLOCKED = "blocked"
STATUS_INVALID_INPUT = "invalid-input"
STATUS_FAILED = "failed"

_STATE_IMPORT_ERROR: Exception | None = None

# Import state helpers once at module load so command execution can fail fast
# with a clear dependency message if `tomlkit` or the module is unavailable.
try:
    from notifications_state import (  # type: ignore
        apply_on_state,
        apply_safe_off_without_snapshot,
        apply_snapshot_restore,
        capture_prior_state,
        is_permission_block,
        is_target_on,
        load_snapshot,
        load_toml_document,
        prepare_config_directory,
        remove_snapshot,
        resolve_config_path,
        resolve_notify_script_path,
        resolve_snapshot_path,
        write_snapshot,
        write_toml_document,
    )
except Exception as exc:  # pragma: no cover - exercised via CLI dependency-failure path
    _STATE_IMPORT_ERROR = exc


def build_result(
    action: str, status: str, rationale: str, next_action: str = ""
) -> dict[str, str]:
    # Unified response shape used by all command outcomes.
    return {
        "action": action,
        "status": status,
        "rationale": rationale,
        "next_action": next_action,
    }


def emit_result(result: dict[str, str]) -> None:
    # CLI contract: always emit machine-readable JSON.
    print(json.dumps(result, ensure_ascii=True))


def blocked_result(action: str, reason: str) -> dict[str, str]:
    # "blocked" means policy/permissions prevented touching global config.
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
    # "failed" means an unexpected runtime or data error (not policy block).
    return build_result(
        action=action,
        status=STATUS_FAILED,
        rationale=reason,
        next_action="Inspect the error and rerun after correcting the config or filesystem state.",
    )


def result_from_exception(
    action: str,
    exc: BaseException,
    blocked_reason_prefix: str,
    failed_reason_prefix: str,
) -> dict[str, str]:
    # One place to map exceptions into user-facing status buckets.
    # This keeps error wording consistent across on/off/read/write paths.
    if is_permission_block(exc):
        return blocked_result(action, f"{blocked_reason_prefix}: {exc}")
    return failed_result(action, f"{failed_reason_prefix}: {exc}")


def execute_on(document, config_path, snapshot_path, notify_script_path) -> dict[str, str]:
    # "on" flow:
    # 1) short-circuit if already in target state
    # 2) snapshot previous user values
    # 3) apply target values + persist
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
        # Snapshot is written before config mutation so "off" has restore data.
        write_snapshot(snapshot_path, config_path, prior_state)
        write_toml_document(config_path, document)
    except BaseException as exc:
        # If writes fail, remove the new snapshot so we do not advertise a restorable state.
        try:
            remove_snapshot(snapshot_path)
        except OSError:
            pass
        return result_from_exception(
            action=action,
            exc=exc,
            blocked_reason_prefix="Global config write blocked",
            failed_reason_prefix="Failed to apply notifications on",
        )

    return build_result(
        action=action,
        status=STATUS_APPLIED,
        rationale="Snapshot saved and global config updated for completion and approval alerts.",
    )


def execute_off(
    document,
    config_path,
    snapshot_path,
    notify_script_path,
) -> dict[str, str]:
    # "off" flow prefers exact restore from snapshot.
    # If snapshot is missing/broken, use a safe fallback that only removes
    # values this skill controls.
    action = "$notifications off"

    prior_state, snapshot_warning = load_snapshot(snapshot_path)
    # Keep snapshot read errors visible while still attempting a safe "off" path.
    warning_suffix = f" ({snapshot_warning})" if snapshot_warning else ""

    if prior_state is not None:
        # Snapshot restore path: put prior values back exactly as captured.
        changed = apply_snapshot_restore(document, prior_state)
        try:
            if changed:
                write_toml_document(config_path, document)
            remove_snapshot(snapshot_path)
        except BaseException as exc:
            return result_from_exception(
                action=action,
                exc=exc,
                blocked_reason_prefix="Global config write blocked",
                failed_reason_prefix="Failed to apply notifications off",
            )

        return build_result(
            action=action,
            status=STATUS_APPLIED,
            rationale="Restored prior user notification settings from snapshot" + warning_suffix + ".",
        )

    changed = apply_safe_off_without_snapshot(document, notify_script_path)
    if not changed:
        # Already off (or nothing skill-managed to change).
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
        return result_from_exception(
            action=action,
            exc=exc,
            blocked_reason_prefix="Global config write blocked",
            failed_reason_prefix="Failed to apply notifications off",
        )

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
    # Shared orchestration for both commands:
    # validate input -> resolve paths -> verify writability -> load config
    # -> delegate to on/off flow.
    action = f"$notifications {command}"

    if command not in ALLOWED_COMMANDS:
        return build_result(
            action=action,
            status=STATUS_INVALID_INPUT,
            rationale=f"Invalid command argument '{command}'.",
            next_action=USAGE_TEXT,
        )

    if _STATE_IMPORT_ERROR is not None:
        return failed_result(
            action,
            "State module dependency initialization failed: "
            + f"{_STATE_IMPORT_ERROR}. Install runtime dependency with 'python3 -m pip install tomlkit'.",
        )

    config_path = resolve_config_path(config_override)
    snapshot_path = resolve_snapshot_path(config_path, snapshot_override)
    notify_script_path = resolve_notify_script_path(notify_override)

    # Catch write-denied situations early to provide clear guidance.
    writable, blocked_reason = prepare_config_directory(config_path)
    if not writable:
        return blocked_result(action, blocked_reason or "Config path is not writable.")

    try:
        document = load_toml_document(config_path)
    except BaseException as exc:
        return result_from_exception(
            action=action,
            exc=exc,
            blocked_reason_prefix="Global config read blocked",
            failed_reason_prefix="Failed to parse config TOML",
        )

    if command == "on":
        return execute_on(document, config_path, snapshot_path, notify_script_path)
    return execute_off(document, config_path, snapshot_path, notify_script_path)


def parse_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    # Keep parsing permissive so main() can return structured JSON errors
    # instead of argparse's default raw stderr/exit behavior.
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("command", nargs="?")
    parser.add_argument("--config")
    parser.add_argument("--snapshot")
    parser.add_argument("--notify-script")
    parser.add_argument("-h", "--help", action="store_true")
    return parser.parse_known_args(argv)


def exit_code_for_status(status: str) -> int:
    # Exit codes are stable so shell wrappers can react programmatically.
    if status in {STATUS_APPLIED, STATUS_ALREADY_APPLIED}:
        return 0
    if status == STATUS_INVALID_INPUT:
        return 2
    if status == STATUS_BLOCKED:
        return 3
    return 4


def main(argv: list[str] | None = None) -> int:
    # CLI entrypoint: parse -> validate -> execute -> emit one JSON result.
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
