# Notifications Skill v1 Successor Handoff

## 1. Objective

Allow a new Codex session to continue implementation without relying on previous chat history.

## 2. Current Project State (as of 2026-02-22)

Status:

- Analysis complete
- Acceptance criteria complete
- Core implementation created (needs runtime validation pass)

Existing docs:

- `docs/notifications-skill-v1-acceptance-spec.md`
- `docs/notifications-skill-v1-implementation-plan.md`
- `docs/README.md`

Implementation artifacts now present:

- `.agents/skills/notifications/SKILL.md`
- `.agents/skills/notifications/agents/openai.yaml`
- `.agents/skills/notifications/scripts/notifications_ctl.py`
- `.agents/skills/notifications/scripts/notifications_state.py`
- `.agents/skills/notifications/scripts/notify_event.py`
- `tests/test_notifications_ctl.py`
- `tests/test_notifications_state.py`

## 3. Product Decisions Already Locked

1. Skill UX is fixed:
   - `$notifications on`
   - `$notifications off`
2. v1 architecture is fixed:
   - `notify` for completion
   - `tui.notifications=["approval-requested"]` + `notification_method="bel"` for approval path
3. Goal is graceful cross-platform, not absolute universal terminal parity.
4. Approval sound while focused is best-effort in v1.
5. Strict mode is v2 scope.

## 4. Truths Verified from Sources

- `notify` and `tui.notifications` can be used together.
- `notify` currently supports `agent-turn-complete`.
- `tui.notifications` supports filtered events including `approval-requested`.
- `tui.notification_method` is global and supports `auto | osc9 | bel`.
- Global config writes in workspace-write depend on writable roots.

## 5. Open Questions for Implementation Session

Remaining open items after initial coding pass:

1. Validate runtime behavior matrix manually across representative terminals/OS environments.
2. Confirm external packaging/install workflow for users outside this repository.
3. Decide whether strict-mode v2 scoping should begin immediately after v1 validation.

Resolved assumptions in this repo:

- Skill lookup path supports global (`${CODEX_HOME:-$HOME/.codex}/skills/notifications`) with local project fallback.
- Snapshot persistence uses adjacent file next to target config (`.codex-notifications-v1-snapshot.json` by default).
- Notify script uses host-native commands with BEL fallback.
- Config mutation module requires `tomlkit` in the Python runtime used by the control script.

## 6. Successor Execution Checklist

### A. Revalidation (must-do)

- Re-check Codex version and schema keys.
- Re-check docs for notify event coverage.
- Re-check skill install path conventions.

### B. Build

- Extend tests and runtime checks from current baseline implementation.

### C. Verify

- Run all required acceptance tests from the acceptance spec.

### D. Publish

- Commit with clear scoped messages.
- Update docs with any observed behavior deltas.
- Push and provide exact commit SHA.

## 7. Anti-Drift Rules

- Do not alter v1 scope without explicit product decision.
- Do not mark v1 complete unless required matrix rows pass.
- Do not claim focused approval sound as guaranteed.
- Do not introduce full sidecar strict mode in v1.

## 8. Suggested First Commands for Next Session

1. `git pull`
2. `sed -n '1,260p' docs/notifications-skill-v1-acceptance-spec.md`
3. `sed -n '1,320p' docs/notifications-skill-v1-implementation-plan.md`
4. Revalidate current Codex docs/schema before coding.

## 9. Decision Change Log

If future sessions change a locked decision, append:

- date (YYYY-MM-DD)
- decision changed
- reason
- impact on acceptance spec

No changes logged yet.
