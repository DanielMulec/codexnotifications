#!/usr/bin/env python3
"""Notify hook script for Codex completion events."""

from __future__ import annotations

import json
import platform
import subprocess
import sys

SUPPORTED_EVENT = "agent-turn-complete"


def log_error(message: str) -> None:
    # Send diagnostics to stderr so stdout remains clean for callers.
    print(f"notify_event: {message}", file=sys.stderr)


def run_command(command: list[str]) -> bool:
    # Run a backend command quietly and treat non-zero/exception as failure.
    # Timeouts keep notification hooks from stalling the main CLI flow.
    try:
        completed = subprocess.run(
            command,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
    except OSError:
        # Command/binary missing or not executable.
        return False
    except subprocess.SubprocessError:
        # Timeout or subprocess runtime failure.
        return False

    # Only explicit exit code 0 counts as success.
    return completed.returncode == 0


def try_play_sound() -> bool:
    # Backend strategy:
    # 1) Try OS-native sound tools first
    # 2) Fall back to terminal bell as last resort
    system = platform.system().lower()

    if system == "darwin":
        # macOS: prefer afplay, then AppleScript beep fallback.
        if run_command(["afplay", "/System/Library/Sounds/Glass.aiff"]):
            return True
        if run_command(["osascript", "-e", "beep"]):
            return True
    elif system == "windows":
        # Windows: use powershell console beep when available.
        if run_command(
            ["powershell", "-NoProfile", "-Command", "[console]::beep(880,180)"]
        ):
            return True
    else:
        # Linux/Unix: try common desktop audio tools.
        if run_command(["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"]):
            return True
        if run_command(["canberra-gtk-play", "-i", "complete", "-d", "codex"]):
            return True

    try:
        # Terminal bell fallback keeps behavior usable on minimal systems.
        sys.stdout.write("\a")
        sys.stdout.flush()
    except OSError:
        # Some non-interactive environments may not support terminal bell output.
        return False
    # Terminal bell write succeeded.
    return True


def parse_payload(raw_payload: str) -> dict[str, object] | None:
    # Hook input is expected to be one JSON object argument.
    # Return None for invalid payloads so caller can no-op safely.
    try:
        # Payload is passed as one JSON string argument by Codex hook runtime.
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        log_error("invalid JSON payload")
        return None

    if not isinstance(payload, dict):
        log_error("payload is not an object")
        return None

    return payload


def event_type(payload: dict[str, object]) -> str | None:
    # Support both current "type" and legacy "event" field names.
    event_value = payload.get("type")
    if isinstance(event_value, str):
        # Current field used by modern payload format.
        return event_value

    legacy_value = payload.get("event")
    if isinstance(legacy_value, str):
        # Backward compatibility for older payload shape.
        return legacy_value

    return None


def main(argv: list[str] | None = None) -> int:
    # Never hard-fail the caller: always exit 0 and log locally on errors.
    # Notification hooks should not break core Codex operations.
    args = argv if argv is not None else sys.argv
    if len(args) < 2:
        # Missing payload is non-fatal: log and return success.
        log_error("missing JSON payload")
        return 0

    # Parse input payload from argv[1].
    payload = parse_payload(args[1])
    if payload is None:
        # Invalid payload is ignored to avoid interrupting Codex flow.
        return 0

    # Ignore unrelated events to keep this hook narrowly scoped.
    if event_type(payload) != SUPPORTED_EVENT:
        return 0

    # Best-effort sound output: log if all backends fail, but still exit 0.
    if not try_play_sound():
        log_error("no supported sound backend succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
