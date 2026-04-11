# Notifications Skill Implementation Plan

Date: 2026-04-11  
Status: Active execution plan (current state only)

## Objective

Ship a release-candidate notifications skill with green quality gates and stable behavior on macOS, Linux, and Windows, while minimizing expensive full-matrix reruns.

## Current Focus

### Done

- Safe-off fallback custom-TUI clobber bug is fixed.
- Bundle A targeted revalidation is complete.

### Open

- Windows hardening bundle:
  - fix Windows `mypy` gate failure (`notifications_state.py` platform-branch unreachable warning)
  - fix Windows test portability and determinism issues
  - finalize Windows PowerShell fallback timeout strategy
  - finalize `python3` vs interpreter-fallback validation contract for Windows
- macOS detection boundary check:
  - run one clean-room recheck to confirm whether repo-cwd-only skill resolution is a reproducible runtime issue or a validation artifact
- Operational readiness:
  - keep Linux dependency-readiness checks explicit in validation workflow

## Active Bundle Plan

### Bundle B: Windows Hardening (merged old B + C)

Scope:

- `mypy` issue in `skill-src/notifications/scripts/notifications_state.py`
- Windows-related failing tests in:
  - `tests/test_notifications_state.py`
  - `tests/test_notifications_ctl.py`
- Windows fallback behavior in:
  - `skill-src/notifications/scripts/notify_event.py`
- Windows command/gate contract documentation updates where needed

Acceptance criteria:

- `mypy` passes on Windows and non-Windows hosts.
- Windows unit tests pass without path-escaping or permission-model flakiness.
- Windows PowerShell stage is either:
  - reliable within its timeout budget, or
  - intentionally demoted/retained with explicit contract wording.
- Validation commands and documented launcher policy are consistent for Windows hosts.

## Validation Strategy

### After each commit (always)

- `ruff check .`
- `mypy`
- `python3 -m unittest discover -s tests -v`

### Targeted rerun after Bundle B

- Windows-focused rerun:
  - quality gates
  - `$notifications on/off` CLI behavior
  - Windows backend fallback order and timeout behavior
  - interpreter-path/launcher contract checks

### Full matrix checkpoint

Run full macOS + Linux + Windows matrix after Bundle B and after macOS detection-boundary disposition (closed as artifact or fixed if reproducible).

## Release Gate (v0.4.0)

Release candidate is eligible only when:

- all required gates are green
- Windows hardening acceptance criteria are met
- macOS detection-boundary item is resolved (artifact or implemented fix)
- `CHANGELOG.md` and `MIGRATIONS.md` reflect final shipped behavior and user actions
