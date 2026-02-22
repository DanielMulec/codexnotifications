# Notifications Skill v1 Implementation Plan

## 1. Goal

Implement a global Codex skill triggered by:

- `$notifications on`
- `$notifications off`

v1 target behavior and acceptance gates are defined in:

- `docs/notifications-skill-v1-acceptance-spec.md`

## 2. Design Summary

v1 uses two mechanisms together:

- `notify` hook for completion sound (`agent-turn-complete`)
- `tui.notifications = ["approval-requested"]` with `tui.notification_method = "bel"` for approval path

Rationale:

- `notify` currently supports completion events.
- TUI supports approval filtering.
- this avoids duplicate completion alerts.

## 3. Proposed Deliverables

### Repository deliverables

- skill folder with `SKILL.md`
- optional `agents/openai.yaml` metadata
- script(s) for config mutation and status checks
- script for notify hook event handling
- test fixtures for config roundtrip tests
- docs updates as implementation truth evolves

### Runtime deliverables

- command parser behavior for `on|off`
- safe global config mutation with backup/snapshot
- idempotent on/off operations
- blocked-write fallback messaging under restricted sandbox

## 4. Implementation Phases

### Phase 0: Preconditions

Tasks:

- Confirm active Codex version and config schema keys still match assumptions.
- Confirm target global skill install root for current environment.
- Confirm global config path resolution (`$CODEX_HOME/config.toml` fallback `~/.codex/config.toml`).

Exit criteria:

- No breaking changes in schema/CLI assumptions.

### Phase 1: Skill Skeleton

Tasks:

- Create skill directory structure.
- Write `SKILL.md` trigger semantics for `$notifications on|off`.
- Add concise operational guidance and error behavior in `SKILL.md`.

Exit criteria:

- Skill can be discovered and invoked.
- Invocation instructions are unambiguous.

### Phase 2: Config Mutation Engine

Tasks:

- Implement deterministic read/parse/write for TOML config.
- Implement snapshot/restore strategy for keys:
  - `notify`
  - `tui.notifications`
  - `tui.notification_method`
- Enforce idempotency.

Behavior requirements:

- Never duplicate keys or create invalid TOML.
- Preserve unrelated user config keys and formatting as much as practical.
- Fail safely on parse/write errors.

Exit criteria:

- Roundtrip tests pass for on/off/on/off sequences.

### Phase 3: Notify Hook Script

Tasks:

- Implement notify handler script receiving JSON payload.
- Handle only supported completion event in v1.
- Emit deterministic sound path for completion signal.

Behavior requirements:

- Unknown/malformed payload does not crash session.
- Nonzero subprocess errors are handled and surfaced clearly.

Exit criteria:

- Completion sound works in focused and unfocused terminal scenarios (subject to host capability).

### Phase 4: Sandbox-Aware Fallback

Tasks:

- Detect write permission failure for global config path.
- Return blocked result with clear remediation steps.

Required remediation guidance:

- add config directory to `sandbox_workspace_write.writable_roots`
- rerun with a policy that permits the write

Exit criteria:

- Blocked path has zero partial writes and actionable message.

### Phase 5: Acceptance Testing

Tasks:

- Execute command parsing tests.
- Execute config mutation and idempotency tests.
- Execute focused/unfocused runtime checks for completion and approval.

Exit criteria:

- Required rows in acceptance matrix pass.
- Best-effort rows documented with observed terminal/OS behavior.

### Phase 6: Packaging Readiness (v1.1 candidate)

Tasks:

- Define sharable install method for other users.
- Add versioning and release notes process.
- Add reproducible smoke test instructions.

Exit criteria:

- A third party can install and validate with minimal manual setup.

## 5. Algorithms (Normative)

### 5.1 On flow

1. Resolve config path.
2. Verify writable access.
3. Load TOML.
4. Save prior key state snapshot.
5. Set:
   - `notify = [python3, notify_script_path]`
   - `tui.notifications = ["approval-requested"]`
   - `tui.notification_method = "bel"`
6. Persist config atomically.
7. Return `applied` or `already-applied`.

### 5.2 Off flow

1. Resolve config path.
2. Verify writable access.
3. Load TOML.
4. Restore snapshot when available; otherwise disable safely.
5. Persist config atomically.
6. Return `applied` or `already-applied`.

## 6. Risk Register

Risk:

- TUI approval sound may not fire while terminal is focused.
Mitigation:
- classify as best-effort in v1, plan strict mode in v2.

Risk:

- Global config write blocked by sandbox.
Mitigation:
- blocked result with exact remediation.

Risk:

- Unknown changes in Codex schema or skill path conventions.
Mitigation:
- precondition checks in Phase 0 before coding.

Risk:

- User custom config formatting churn.
Mitigation:
- minimal-diff writer strategy and config backups.

## 7. Definition of Implementation Complete

Implementation is complete only when all conditions hold:

- every required acceptance criterion passes
- idempotency is verified
- blocked-write behavior is verified
- docs reflect observed behavior on tested platforms
- release claim includes known limitations explicitly
