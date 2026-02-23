---
name: notifications
description: Toggle Codex notification behavior with $notifications on and $notifications off. Use when notification sound policy must be enabled or disabled.
---

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
3. Parse the script JSON result.
4. Return a natural-language response (do not return raw JSON unless the user explicitly asks for it).

```bash
SCRIPT_PATH="${CODEX_HOME:-$HOME/.codex}/skills/notifications/scripts/notifications_ctl.py"
if [ ! -f "$SCRIPT_PATH" ] && [ -f ".agents/skills/notifications/scripts/notifications_ctl.py" ]; then
  SCRIPT_PATH=".agents/skills/notifications/scripts/notifications_ctl.py"
fi
python3 "$SCRIPT_PATH" <on_or_off>
```

## Response Mapping (Natural Language)

Use the control script response fields (`action`, `status`, `rationale`, `next_action`) and map them to human-friendly output.

For `status = applied`:

- If action is `$notifications on`:
  `Notifications are now on. You should hear a sound when Codex finishes a response. If you do not hear a sound, restart Codex CLI and try again.`
- If action is `$notifications off`:
  `Notifications are now off. You should no longer hear completion sounds. If you still hear a sound, restart Codex CLI and try again.`

For `status = already-applied`:

- If action is `$notifications on`:
  `Notifications are already on. If you do not hear a sound, restart Codex CLI and try again.`
- If action is `$notifications off`:
  `Notifications are already off. If you still hear a sound, restart Codex CLI and try again.`

For `status = blocked`:

- Say the action could not be applied due to write restrictions.
- Include the script rationale in plain language.
- Include the script next action.

For `status = invalid-input`:

- Return:
  `Invalid command. Usage: $notifications on|off`

For `status = failed`:

- Say the operation failed.
- Include a concise reason from `rationale`.
- Include `next_action` guidance.

## Notes

- The control script handles config mutation, snapshot/restore, idempotency, and blocked-write messaging.
- Do not perform manual config edits if the control script succeeds.
