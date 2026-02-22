# Notifications Skill v1 Acceptance Spec

## 1. Purpose

Define v1 acceptance criteria for a global Codex skill invoked as:

- `$notifications on`
- `$notifications off`

This document is design/analysis only. No implementation code is included.

## 2. Scope (v1)

### In scope

- Global enable/disable of Codex notification sound behavior through user-level Codex config.
- Combined model:
  - `notify` hook for completion sounds (`agent-turn-complete`).
  - `tui.notifications` for approval prompts (`approval-requested`) with forced `bel`.
- Graceful cross-platform behavior (macOS, Linux, Windows), best-effort where platform/terminal capabilities differ.
- Works with default sandbox constraints by failing safely with actionable guidance when global config is not writable.

### Out of scope

- Guaranteed identical behavior across every terminal emulator.
- Guaranteed focused-window approval sound via built-in TUI notifications.
- Per-event `tui.notification_method` (not supported by current config model).
- Full "strict mode" event sidecar implementation (reserved for v2).

## 3. Source-Based Constraints (as of 2026-02-22)

- `notify` is a top-level config key for an external command.
- `notify` currently supports `agent-turn-complete`.
- `tui.notifications` supports boolean or filtered list (including `approval-requested` and `agent-turn-complete`).
- `tui.notification_method` is global for TUI notifications and supports `auto | osc9 | bel`.
- `notify` and `tui.notifications` are separate mechanisms and can be used together.
- In workspace-write sandbox, writing outside writable roots is blocked unless configured via writable roots.

## 4. Command Contract

### Accepted commands

- `$notifications on`
- `$notifications off`

### Rejected commands (must return clear usage)

- `$notifications`
- `$notifications enable`
- `$notifications yes`
- Any other argument not equal to `on` or `off`

### Expected response style

Each invocation must return:

- action attempted
- result status (`applied`, `already-applied`, `blocked`, `invalid-input`, `failed`)
- short rationale
- next action when blocked/failed

## 5. Config Contract (Normative)

### 5.1 "On" target state

When `$notifications on` succeeds, effective config must include:

```toml
notify = ["python3", "<ABSOLUTE_PATH_TO_NOTIFY_SCRIPT>"]

[tui]
notifications = ["approval-requested"]
notification_method = "bel"
```

Notes:

- `notify` handles completion signal.
- `tui.notifications` is restricted to approval-only to avoid duplicate completion sounds.
- `notification_method = "bel"` is forced in v1 for approval prompt path.

### 5.2 "Off" target state

When `$notifications off` succeeds:

- `notify` must be disabled (empty or removed, per implementation choice).
- approval notification override must be disabled (`tui.notifications = false`) or restored from prior snapshot.
- no notification sound should be emitted by this skill policy.

### 5.3 State preservation

`$notifications on` must snapshot prior user values for:

- `notify`
- `tui.notifications`
- `tui.notification_method`

`$notifications off` must restore from snapshot if available; otherwise disable safely.

### 5.4 Idempotency

- Re-running `$notifications on` on an already-on state must not duplicate config entries.
- Re-running `$notifications off` on an already-off state must not produce new changes.

## 6. Behavior Matrix (Acceptance)

Legend:

- `Required`: must pass to accept v1.
- `Best-effort`: non-blocking for v1 if capability limits prevent sound.

| Skill state | Terminal focus | Event | Expected sound outcome | Mechanism | Acceptance level |
|---|---|---|---|---|---|
| on | focused | agent-turn-complete | sound plays | `notify` hook | Required |
| on | unfocused | agent-turn-complete | sound plays | `notify` hook | Required |
| on | focused | approval-requested | may play, not guaranteed | `tui.notifications` + `bel` | Best-effort |
| on | unfocused | approval-requested | sound should play when BEL is supported | `tui.notifications` + `bel` | Best-effort |
| off | focused | agent-turn-complete | no skill-driven sound | none | Required |
| off | unfocused | agent-turn-complete | no skill-driven sound | none | Required |
| off | focused | approval-requested | no skill-driven sound | none | Required |
| off | unfocused | approval-requested | no skill-driven sound | none | Required |

## 7. Sandbox and Permission Behavior

### 7.1 Writable global config

If global config path is writable, command applies directly.

Config path resolution:

- `$CODEX_HOME/config.toml` when `CODEX_HOME` is set
- otherwise `~/.codex/config.toml`

### 7.2 Non-writable global config

If blocked by sandbox policy, command must:

- not partially mutate config
- return `blocked`
- explain exact reason (config path not writable under current sandbox roots)
- provide concrete next-step options:
  - add config directory to writable roots (`sandbox_workspace_write.writable_roots`)
  - rerun with a policy that permits this write

### 7.3 Python note

Using Python for mutation does not bypass sandbox restrictions. It is subject to the same writable-root policy.

## 8. Runtime Robustness Requirements

- Notify script errors must not crash Codex session.
- Failures should be logged and surfaced succinctly.
- Unsupported BEL behavior in a terminal is tolerated in v1 (best-effort path).
- Invalid JSON payload passed to notify hook must fail gracefully.

## 9. Test Cases (Minimum)

### 9.1 Command parsing

- `$notifications on` -> valid
- `$notifications off` -> valid
- `$notifications` -> invalid-input with usage
- `$notifications foo` -> invalid-input with usage

### 9.2 Config mutation

- On from clean config -> writes target keys exactly once
- On from existing conflicting values -> snapshots and overrides
- Off after On -> restores prior values
- On twice -> no duplicate keys, no drift
- Off twice -> stable, no further edits

### 9.3 Sandbox behavior

- Writable config path -> applied
- Non-writable config path -> blocked + guidance, zero partial writes

### 9.4 Runtime behavior (manual/automated where possible)

- Completion event triggers notify hook in focused terminal
- Completion event triggers notify hook in unfocused terminal
- Approval event attempts BEL when unfocused and TUI notifications are enabled for approval
- Off state emits no skill-driven notification sounds

## 10. Definition of Done for v1

v1 is accepted when all are true:

- Command contract in Section 4 passes.
- Config contract in Section 5 passes, including idempotency and restore behavior.
- Required rows in Section 6 pass.
- Best-effort rows in Section 6 are documented with platform limits and do not break flow.
- Section 7 sandbox behavior is implemented exactly.
- Test cases in Section 9 are completed and results recorded.

## 11. Planned v2: Strict Mode (Design Placeholder)

Strict mode will introduce a local event sidecar/wrapper that:

- subscribes to Codex event stream directly
- handles both completion and approval with deterministic local sound policy
- supports per-event sound differentiation independent of TUI focus behavior

This is intentionally excluded from v1 to keep first release simple and shippable.

## 12. References

- https://developers.openai.com/codex/config-advanced/
- https://developers.openai.com/codex/config-reference/
- https://developers.openai.com/codex/config-sample/
- https://developers.openai.com/codex/config-schema.json
