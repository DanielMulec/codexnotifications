#!/usr/bin/env python3
"""Notify hook script for Codex completion events."""

from __future__ import annotations

import datetime as dt
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

SUPPORTED_EVENT = "agent-turn-complete"
WINDOWS_MEDIA_FILENAMES = (
    "chimes.wav",
    "Windows Notify.wav",
    "Windows Notify System Generic.wav",
    "notify.wav",
)
WINDOWS_BEEP_PATTERN = (
    (880, 120),
    (988, 120),
    (1047, 160),
)
_LAST_BACKEND = "none"


def set_last_backend(backend: str) -> None:
    # Keep selected backend visible for diagnostics emitted by main().
    global _LAST_BACKEND
    _LAST_BACKEND = backend


def get_last_backend() -> str:
    # Tiny accessor keeps tests and logging independent from global internals.
    return _LAST_BACKEND


def _debug_log_path() -> Path:
    # Optional override is useful for runtime tests and controlled environments.
    override = os.environ.get("CODEX_NOTIFY_LOG")
    if override:
        return Path(override).expanduser()

    # Default location aligns with Codex user-level state.
    return Path.home() / ".codex" / "log" / "notify_hook.log"


def _debug_log_targets() -> list[Path]:
    # Primary target is configurable/default path.
    # Fallback target is local cwd file when primary path is not writable.
    primary = _debug_log_path()
    try:
        fallback = Path.cwd() / "notify_hook.log"
    except OSError:
        # If cwd is unavailable, keep only the primary target.
        return [primary]

    if fallback == primary:
        return [primary]
    return [primary, fallback]


def log_debug_event(event: str, **fields: object) -> None:
    # Best-effort JSONL debug trace:
    # - never raises
    # - never writes to stdout
    # - includes timestamp and process id for correlation
    payload: dict[str, object] = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "event": event,
        "pid": os.getpid(),
    }
    payload.update(fields)
    line = json.dumps(payload, ensure_ascii=True)

    try:
        targets = _debug_log_targets()
    except OSError:
        return

    for target in targets:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(line + "\n")
            return
        except OSError:
            continue


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


def windows_candidate_wav_paths() -> list[Path]:
    # Candidate ordering is intentional:
    # 1) explicit user override
    # 2) common system media files
    candidates: list[Path] = []

    wav_override = os.environ.get("CODEX_NOTIFY_WAV")
    if wav_override:
        candidates.append(Path(wav_override).expanduser())

    windir = os.environ.get("WINDIR") or os.environ.get("SystemRoot")
    if windir:
        media_root = Path(windir).expanduser() / "Media"
        for filename in WINDOWS_MEDIA_FILENAMES:
            candidates.append(media_root / filename)

    return candidates


def _load_winsound() -> Any | None:
    # `winsound` exists on Windows only; load lazily for cross-platform execution.
    try:
        import importlib

        return importlib.import_module("winsound")
    except ImportError:
        return None


def play_windows_wav_file() -> tuple[bool, str]:
    # Prefer synchronous WAV playback so hook process lifetime does not
    # terminate sound output early on short-lived invocations.
    winsound = _load_winsound()
    if winsound is None:
        return False, "windows:winsound-unavailable"

    for wav_path in windows_candidate_wav_paths():
        try:
            if not wav_path.is_file():
                continue
            winsound.PlaySound(str(wav_path), winsound.SND_FILENAME)
            return True, f"windows:winsound.PlaySound(file:{wav_path.name})"
        except (RuntimeError, OSError):
            continue

    return False, "windows:winsound.file-none"


def play_windows_beep_chime() -> tuple[bool, str]:
    # Deterministic three-note chime avoids user sound-scheme dependency.
    winsound = _load_winsound()
    if winsound is None:
        return False, "windows:winsound-unavailable"

    try:
        for frequency, duration in WINDOWS_BEEP_PATTERN:
            winsound.Beep(frequency, duration)
        return True, "windows:winsound.Beep(chime)"
    except (RuntimeError, OSError):
        return False, "windows:winsound.Beep-failed"


def play_windows_powershell_chime() -> tuple[bool, str]:
    # PowerShell console beep fallback is useful when winsound backends
    # are unavailable in the current Python runtime.
    script = (
        "[console]::beep(880,120); Start-Sleep -Milliseconds 40; "
        "[console]::beep(988,120); Start-Sleep -Milliseconds 40; "
        "[console]::beep(1047,160)"
    )
    if run_command(["powershell", "-NoProfile", "-Command", script]):
        return True, "windows:powershell.console-beep"
    return False, "windows:powershell.console-beep-failed"


def play_windows_alias_fallback() -> tuple[bool, str]:
    # Alias-based sounds depend on per-user scheme/mixer state, so this is a
    # late fallback rather than primary backend.
    winsound = _load_winsound()
    if winsound is None:
        return False, "windows:winsound-unavailable"

    try:
        winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS)
        return True, "windows:winsound.PlaySound(SystemAsterisk)"
    except (RuntimeError, OSError):
        pass

    try:
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
        return True, "windows:winsound.MessageBeep(MB_ICONASTERISK)"
    except (RuntimeError, OSError):
        return False, "windows:winsound.alias-failed"


def try_play_sound() -> bool:
    # Backend strategy:
    # 1) Try OS-native sound tools first
    # 2) Fall back to terminal bell as last resort
    set_last_backend("none")
    system = platform.system().lower()

    if system == "darwin":
        # macOS: prefer afplay, then AppleScript beep fallback.
        if run_command(["afplay", "/System/Library/Sounds/Glass.aiff"]):
            set_last_backend("darwin:afplay")
            return True
        if run_command(["osascript", "-e", "beep"]):
            set_last_backend("darwin:osascript-beep")
            return True
    elif system == "windows":
        # Windows cascade:
        # 1) deterministic WAV file playback (sync)
        # 2) deterministic winsound chime
        # 3) PowerShell console chime
        # 4) alias/system fallback
        for backend_fn in (
            play_windows_wav_file,
            play_windows_beep_chime,
            play_windows_powershell_chime,
            play_windows_alias_fallback,
        ):
            ok, backend = backend_fn()
            if ok:
                set_last_backend(backend)
                return True
    else:
        # Linux/Unix: try common desktop audio tools.
        if run_command(["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"]):
            set_last_backend("linux:paplay")
            return True
        if run_command(["canberra-gtk-play", "-i", "complete", "-d", "codex"]):
            set_last_backend("linux:canberra-gtk-play")
            return True

    try:
        # Terminal bell fallback keeps behavior usable on minimal systems.
        sys.stdout.write("\a")
        sys.stdout.flush()
        set_last_backend("terminal-bell")
    except OSError:
        # Some non-interactive environments may not support terminal bell output.
        set_last_backend("none")
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


def is_supported_event(event_name: str | None) -> bool:
    # Accept canonical event plus compatible `*-turn-complete` variants.
    if not isinstance(event_name, str):
        return False
    if event_name == SUPPORTED_EVENT:
        return True
    return event_name.endswith("-turn-complete")


def main(argv: list[str] | None = None) -> int:
    # Never hard-fail the caller: always exit 0 and log locally on errors.
    # Notification hooks should not break core Codex operations.
    args = argv if argv is not None else sys.argv
    log_debug_event("invoke", argv_len=len(args))
    if len(args) < 2:
        # Missing payload is non-fatal: log and return success.
        log_error("missing JSON payload")
        log_debug_event("missing-payload")
        return 0

    # Parse input payload from argv[1].
    payload = parse_payload(args[1])
    if payload is None:
        # Invalid payload is ignored to avoid interrupting Codex flow.
        log_debug_event("invalid-payload", raw=args[1][:512])
        return 0

    event_name = event_type(payload)
    log_debug_event(
        "parsed-payload",
        payload_keys=sorted(payload.keys()),
        event_name=event_name,
    )

    # Ignore unrelated events to keep this hook narrowly scoped.
    if not is_supported_event(event_name):
        log_debug_event("ignored-event", event_name=event_name)
        return 0

    # Best-effort sound output: log if all backends fail, but still exit 0.
    success = try_play_sound()
    log_debug_event(
        "play-attempt",
        ok=success,
        backend=get_last_backend(),
        event_name=event_name,
    )
    if not success:
        log_error("no supported sound backend succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
