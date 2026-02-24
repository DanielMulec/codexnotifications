# Install and Uninstall

This guide covers how to install, verify, and uninstall the `notifications` skill on user machines.

## 1. Skill Location Norms (Codex CLI)

User-installed skills are typically placed under:

- `${CODEX_HOME:-$HOME/.codex}/skills/<skill-name>`

Project-local development fallback used by this repository:

- `.agents/skills/notifications`

## 2. Install the Skill

### Option A (recommended): install via `$skill-installer`

Inside Codex, ask the installer skill to install from this repo path:

- repo: `DanielMulec/codexnotifications`
- path: `.agents/skills/notifications`

Then restart Codex CLI.

### Option B: manual copy

1. Copy this folder into your Codex user skills directory as `notifications`:

- source: `.agents/skills/notifications`
- destination: `${CODEX_HOME:-$HOME/.codex}/skills/notifications`

2. Restart Codex CLI.

## 3. Install Python Dependency (`tomlkit`)

This skill requires `tomlkit` for TOML parse/edit/write in `notifications_state.py`.

### macOS / Linux

```bash
python3 -m pip install --user tomlkit
```

If your Python is externally managed (PEP 668), use:

```bash
python3 -m pip install --user --break-system-packages tomlkit
```

### Windows (PowerShell)

```powershell
py -m pip install --user tomlkit
```

Notes:

- Dependency install is user-controlled and explicit.
- This skill does not auto-install Python packages at runtime.

## 4. Verify Install

Run:

```bash
SCRIPT_PATH="${CODEX_HOME:-$HOME/.codex}/skills/notifications/scripts/notifications_ctl.py"
python3 "$SCRIPT_PATH" --help
```

Expected JSON includes:

- `"status": "invalid-input"`
- `"next_action": "Usage: $notifications on|off"`

If you see a dependency error for `tomlkit`, install `tomlkit` in the same Python environment used by `python3`.

## 5. Safe Uninstall

1. Turn notifications policy off first (restores user state/snapshot when available):

```bash
SCRIPT_PATH="${CODEX_HOME:-$HOME/.codex}/skills/notifications/scripts/notifications_ctl.py"
if [ -f "$SCRIPT_PATH" ]; then
  python3 "$SCRIPT_PATH" off
fi
```

2. Remove the installed skill directory:

```bash
rm -rf "${CODEX_HOME:-$HOME/.codex}/skills/notifications"
```

3. Restart Codex CLI.

Windows PowerShell equivalent:

```powershell
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$scriptPath = Join-Path $codexHome "skills/notifications/scripts/notifications_ctl.py"
if (Test-Path $scriptPath) { py $scriptPath off }
Remove-Item -Recurse -Force (Join-Path $codexHome "skills/notifications")
```

## 6. Dependency Removal Policy

`tomlkit` is not removed automatically during skill uninstall, to avoid breaking other user tooling.

If a user wants to remove it manually, they can do so in their Python environment using `pip uninstall tomlkit`.
