# Documentation Index

## Current Status

Project phase: v1 core implementation started and committed in-repo.

As of 2026-02-22:

- v1 scope and acceptance criteria are defined.
- implementation sequencing is defined.
- handoff material for successor Codex sessions is defined.
- skill skeleton, control script, notify hook script, and baseline tests now exist.

## Read Order

1. `docs/notifications-noob-start-here.md`
2. `docs/notifications-skill-v1-acceptance-spec.md`
3. `docs/notifications-skill-v1-implementation-plan.md`
4. `docs/notifications-skill-v1-successor-handoff.md`

## What Exists vs Missing

Exists:

- acceptance criteria and behavior matrix
- sandbox and config constraints
- reference-backed architecture direction
- beginner-oriented walkthrough for on/off behavior (`docs/notifications-noob-start-here.md`)
- skill entrypoint and trigger contract (`.agents/skills/notifications/SKILL.md`)
- config mutation engine (`.agents/skills/notifications/scripts/notifications_ctl.py`)
- notify hook script (`.agents/skills/notifications/scripts/notify_event.py`)
- automated baseline tests (`tests/test_notifications_ctl.py`)

Missing (next phase):

- packaging/install workflow for external users
- full manual runtime matrix evidence across terminals/OS variants

## Quick Resume Checklist

When resuming after context loss:

1. Re-read acceptance spec and confirm no product changes.
2. Re-validate docs truth on current Codex release if date has advanced materially.
3. Execute implementation plan phases in order.
4. Track progress in successor handoff checklist.
5. Run acceptance tests before any release claim.
