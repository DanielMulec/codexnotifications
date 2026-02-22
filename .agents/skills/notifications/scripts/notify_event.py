#!/usr/bin/env python3
"""Notify hook script for Codex completion events."""

from __future__ import annotations

import json
import platform
import subprocess
import sys

SUPPORTED_EVENT = "agent-turn-complete"


def log_error(message: str) -> None:
    print(f"notify_event: {message}", file=sys.stderr)


def run_command(command: list[str]) -> bool:
    try:
        completed = subprocess.run(
            command,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
    except OSError:
        return False
    except subprocess.SubprocessError:
        return False

    return completed.returncode == 0


def try_play_sound() -> bool:
    system = platform.system().lower()

    if system == "darwin":
        if run_command(["afplay", "/System/Library/Sounds/Glass.aiff"]):
            return True
        if run_command(["osascript", "-e", "beep"]):
            return True
    elif system == "windows":
        if run_command(
            ["powershell", "-NoProfile", "-Command", "[console]::beep(880,180)"]
        ):
            return True
    else:
        if run_command(["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"]):
            return True
        if run_command(["canberra-gtk-play", "-i", "complete", "-d", "codex"]):
            return True

    try:
        sys.stdout.write("\a")
        sys.stdout.flush()
    except OSError:
        return False
    return True


def parse_payload(raw_payload: str) -> dict[str, object] | None:
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        log_error("invalid JSON payload")
        return None

    if not isinstance(payload, dict):
        log_error("payload is not an object")
        return None

    return payload


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv
    if len(args) < 2:
        log_error("missing JSON payload")
        return 0

    payload = parse_payload(args[1])
    if payload is None:
        return 0

    if payload.get("event") != SUPPORTED_EVENT:
        return 0

    if not try_play_sound():
        log_error("no supported sound backend succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
