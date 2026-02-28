# Notifications Skill for Codex CLI

Turn Codex CLI notification sounds on or off with:

- `$notifications on`
- `$notifications off`

This repository ships a production-ready global skill that configures Codex notifications with safe state handling and clean rollback behavior.

## What This Skill Is About

The `notifications` skill adds a simple user-facing switch for completion sounds and approval-request coverage in Codex CLI.

Instead of hand-editing `config.toml`, you run one command:

- `$notifications on` to enable the policy
- `$notifications off` to disable it

## Why This Skill Exists

Codex notification behavior can vary across environments. This skill standardizes setup and avoids fragile manual config edits.

It is designed to:

- keep behavior consistent across macOS, Linux, and Windows
- preserve and restore prior user notification settings using a snapshot
- keep commands idempotent (`on` + `on`, `off` + `off` are safe)
- return structured status output for clear troubleshooting

## What Happens Under the Hood

When enabled, the skill updates global Codex config to use the bundled notify hook and approval-request sound settings.

When disabled, it restores prior values from snapshot when available, or applies a safe fallback that only removes skill-managed overrides.

Core files:

- `.agents/skills/notifications/SKILL.md`
- `.agents/skills/notifications/scripts/notifications_ctl.py`
- `.agents/skills/notifications/scripts/notifications_state.py`
- `.agents/skills/notifications/scripts/notify_event.py`

## Requirements

- Codex CLI (with skills support)
- Python 3
- Python package `tomlkit` in the same Python environment used by `python3`

Install dependency:

```bash
python3 -m pip install --user tomlkit
```

If your Python is externally managed (PEP 668), use:

```bash
python3 -m pip install --user --break-system-packages tomlkit
```

Windows PowerShell:

```powershell
py -m pip install --user tomlkit
```

## Install in Codex CLI

### Option A (Recommended): `$skill-installer`

Inside Codex, install from:

- repo: `DanielMulec/codexnotifications`
- path: `.agents/skills/notifications`

Then restart Codex CLI.

### Option B: Manual copy

1. Clone this repository.
2. Copy `.agents/skills/notifications` to `${CODEX_HOME:-$HOME/.codex}/skills/notifications`.
3. Restart Codex CLI.

## Quick Start

After install and restart:

```text
$notifications on
$notifications off
```

You can also verify the script directly:

```bash
SCRIPT_PATH="${CODEX_HOME:-$HOME/.codex}/skills/notifications/scripts/notifications_ctl.py"
python3 "$SCRIPT_PATH" --help
```

Expected JSON includes:

- `"status": "invalid-input"`
- `"next_action": "Usage: $notifications on|off"`

## Troubleshooting

- No sound after `$notifications on`:
  restart Codex CLI and try again.
- Windows after upgrading this skill:
  reinstall the skill, then run `$notifications on` once so `notify` is rewritten with a stable Windows interpreter command.
- Write blocked / permission errors:
  allow writes to your global Codex config directory (`${CODEX_HOME:-$HOME/.codex}`) or rerun with the required policy/permissions.
- `tomlkit` dependency error:
  install `tomlkit` in the same interpreter used by `python3`.
- Windows hook diagnostics (optional):
  set `CODEX_NOTIFY_LOG` to override hook log path and `CODEX_NOTIFY_WAV` to force a specific WAV file.

Windows PowerShell examples:

```powershell
$env:CODEX_NOTIFY_LOG = "$HOME\.codex\log\notify_hook.log"
$env:CODEX_NOTIFY_WAV = "$env:WINDIR\Media\chimes.wav"
```

## Uninstall / Rollback

For safe uninstall (including `off` first, then folder removal), use:

- `INSTALL.md`

## Quality and Verification

Install dev tooling:

```bash
python3 -m pip install -r requirements-dev.txt
```

Run local quality checks:

```bash
ruff check .
mypy
```

Run tests:

```bash
python3 -m unittest discover -s tests -v
```

Version history:

- `CHANGELOG.md`

## More Documentation

- `INSTALL.md`
- `MIGRATIONS.md`
- `docs/notifications-noob-start-here.md`

## Contact

- LinkedIn: `linkedin.com/in/dmulec`
- X: `x.com/danielmulec`
