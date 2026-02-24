# Documentation Index

## Current Status

Project phase: v1 core implementation started and committed in-repo.

As of 2026-02-22:

- v1 scope and acceptance criteria are defined.
- implementation sequencing is defined.
- handoff material for successor Codex sessions is defined.
- skill skeleton, control script, notify hook script, and baseline tests now exist.

## Read Order

1. `INSTALL.md`
2. `docs/notifications-noob-start-here.md`
3. `docs/notifications-skill-v1-acceptance-spec.md`
4. `docs/notifications-skill-v1-implementation-plan.md`
5. `docs/notifications-skill-v1-successor-handoff.md`

## What Exists vs Missing

Exists:

- install/uninstall workflow and dependency prerequisites (`INSTALL.md`)
- acceptance criteria and behavior matrix
- sandbox and config constraints
- reference-backed architecture direction
- beginner-oriented walkthrough for on/off behavior (`docs/notifications-noob-start-here.md`)
- skill entrypoint and trigger contract (`.agents/skills/notifications/SKILL.md`)
- CLI/orchestration script (`.agents/skills/notifications/scripts/notifications_ctl.py`)
- config/state mutation module (`.agents/skills/notifications/scripts/notifications_state.py`)
- notify hook script (`.agents/skills/notifications/scripts/notify_event.py`)
- automated baseline tests (`tests/test_notifications_ctl.py`, `tests/test_notifications_state.py`)

Missing (next phase):

- full manual runtime matrix evidence across terminals/OS variants

## Quick Resume Checklist

When resuming after context loss:

1. Re-read acceptance spec and confirm no product changes.
2. Re-validate docs truth on current Codex release if date has advanced materially.
3. Execute implementation plan phases in order.
4. Track progress in successor handoff checklist.
5. Run acceptance tests before any release claim.
