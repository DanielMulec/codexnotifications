# Notifications Skill

Toggle Codex notification behavior with:

- `$notifications on`
- `$notifications off`

## Trigger Rules

Use this skill only when the user explicitly invokes `$notifications`.

Accepted forms:

- `$notifications on`
- `$notifications off`

Rejected forms:

- `$notifications`
- `$notifications <anything-other-than-on-or-off>`

For rejected forms, return invalid usage:

`Usage: $notifications on|off`

## Execution Contract

1. Parse the single argument (`on` or `off`) from the user command.
2. Run the control script.
3. Return the script's JSON result directly.

```bash
SCRIPT_PATH="${CODEX_HOME:-$HOME/.codex}/skills/notifications/scripts/notifications_ctl.py"
if [ ! -f "$SCRIPT_PATH" ] && [ -f ".agents/skills/notifications/scripts/notifications_ctl.py" ]; then
  SCRIPT_PATH=".agents/skills/notifications/scripts/notifications_ctl.py"
fi
python3 "$SCRIPT_PATH" <on_or_off>
```

## Notes

- The control script handles config mutation, snapshot/restore, idempotency, and blocked-write messaging.
- Do not perform manual config edits if the control script succeeds.
