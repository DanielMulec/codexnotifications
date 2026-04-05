# Type Safety and Refactor Plan

This document defines the implementation plan for tightening typing, reducing dynamic behavior, and preserving runtime behavior across macOS, Linux, and Windows.

Status: planning only. No runtime behavior changes are implemented by this document.

## Objective

Ship the next implementation release with:

- stricter static analysis over the whole repo, not only the skill scripts
- no explicit `Any` in production code
- sharply reduced implicit `Any` in tests and helpers
- a single Python `3.11+` baseline across runtime, tests, and tooling
- stable runtime behavior for `$notifications on` and `$notifications off` on macOS, Linux, and Windows

## Core Decision: Python Version Policy

The project baseline is Python `3.11+`.

Reasoning:

- Python `3.10` reaches end-of-life in October 2026
- Python `3.11+` gives a cleaner standard-library baseline, including `tomllib`
- one project-wide floor is simpler than mixing a `3.10` runtime policy with `3.11`-leaning tests and tooling
- macOS, Linux, and Windows all have strong Python `3.11+` availability, so the compatibility cost is acceptable

Implementation consequence:

- move `ruff` and `mypy` targets to Python `3.11`
- keep `tomllib` as the standard-library TOML reader in tests and tooling where it is useful
- update `README.md`, `INSTALL.md`, `CHANGELOG.md`, and `MIGRATIONS.md` alongside the implementation

## Current Problems To Address

1. Static analysis scope is too narrow.
   Today `mypy` only gates `.agents/skills/notifications/scripts`, so test typing debt is hidden.

2. Production code contains explicit `Any` roots.
   `notifications_state.py` and `notify_event.py` use `Any` in places that taint large portions of control flow.

3. Production orchestration is under-annotated.
   `notifications_ctl.py` still has untyped orchestration parameters.

4. Tests rely on dynamic module loading patterns.
   `self.mod` is created dynamically and produces large `attr-defined` noise under repo-wide checking.

5. Test fixture data is typed too loosely.
   Nested TOML structures are declared as `dict[str, object]`, then indexed like shaped dictionaries.

6. JSON/TOML parsing boundaries are not normalized.
   `json.loads` and test parsing helpers allow broad untyped values to spread.

7. Project policy is inconsistent.
   Tests already lean on Python `3.11` stdlib features while tooling configuration still targets `3.10`.

## Refactor Principles

- Preserve user-visible behavior first.
- Tighten static analysis in small steps.
- Remove dynamic typing at boundaries before chasing downstream errors.
- Keep cross-platform behavior verified after every meaningful phase.
- Prefer explicit shaped types or small protocols over `Any`.

## Step-by-Step Plan

### Phase 0: Freeze Behavior Before Refactor

Goal:

- establish the current behavior contract before structural changes

Actions:

- review and preserve current tests for `on`, `off`, idempotency, snapshot restore, blocked writes, and Windows sound fallback ordering
- document the runtime invariants that must not change during the refactor
- confirm current behavior manually on macOS, Linux, and Windows before deeper edits

Verification:

- `ruff check .`
- `mypy`
- `python3 -m unittest discover -s tests -v`
- one manual smoke pass per OS

Manual testing at this phase:

- run one baseline smoke pass on macOS, Linux, and Windows before the first runtime code edit
- capture the exact observed behavior for:
  - `$notifications on`
  - `$notifications off`
  - idempotency (`on/on`, `off/off`)
  - sound backend selection and fallback
  - snapshot creation and cleanup

### Phase 1: Align the Project to Python 3.11+

Goal:

- make runtime, tests, docs, and tooling agree on Python `3.11+`

Actions:

- update project tooling configuration to Python `3.11`
- update install and upgrade documentation to require Python `3.11+`
- keep test parsing on stdlib `tomllib`
- rerun `mypy` over tests explicitly, not only over scripts

Why this phase comes first:

- otherwise repo-wide type-checking and docs remain incoherent

Verification:

- `python3 -m mypy tests --python-version 3.11 --check-untyped-defs`
- same unit test suite on all three OS targets

### Phase 2: Type the Public and Internal Data Shapes

Goal:

- replace broad dictionaries and untyped payload flow with explicit shapes

Actions:

- define snapshot-state structures for:
  - captured key state
  - prior snapshot payload
  - parsed event payload
- define a typed representation for the optional Windows sound backend surface
- move parsing/normalization into small boundary helpers that return shaped values

Expected result:

- explicit `Any` roots are isolated and then removable
- downstream `misc` noise drops substantially

Verification:

- targeted unit tests around snapshot loading, snapshot restore, and payload parsing

### Phase 3: Remove Production `Any`

Goal:

- eliminate explicit `Any` from shipped scripts

Actions:

- refactor `_unwrap_value`, snapshot helpers, and `winsound` loading around shaped types or protocols
- annotate `execute_on` and `execute_off` in `notifications_ctl.py`
- make `json.loads` boundaries return validated, typed values before business logic consumes them

Exit criteria:

- no explicit `Any` in production code
- no untyped production function definitions

Verification:

- `python3 -m mypy .agents/skills/notifications/scripts --check-untyped-defs --disallow-untyped-defs --disallow-incomplete-defs --disallow-any-explicit --disallow-any-generics --disallow-any-expr --disallow-any-decorated --warn-return-any`

Manual testing at this phase:

- after any meaningful runtime edit in:
  - `.agents/skills/notifications/scripts/notifications_ctl.py`
  - `.agents/skills/notifications/scripts/notifications_state.py`
  - `.agents/skills/notifications/scripts/notify_event.py`
- run a targeted smoke test on the affected OS immediately
- when Phase 3 is complete, run a full macOS/Linux/Windows smoke pass before moving on

### Phase 4: Refactor the Test Harness

Goal:

- make tests statically understandable without weakening runtime coverage

Actions:

- replace dynamic `self.mod` patterns with typed module handles or narrower wrappers
- give helper loaders explicit return types
- replace loose `dict[str, object]` expectations with shaped assertions or typed helper accessors
- keep OS-specific test logic explicit and locally scoped

Expected result:

- `attr-defined` noise disappears
- nested-indexing failures become proper shape checks instead of `object` indexing

Verification:

- `python3 -m mypy tests --python-version 3.11 --check-untyped-defs`

### Phase 5: Expand the Official `mypy` Gate

Goal:

- move from partial enforcement to repo-wide enforcement

Actions:

- widen `pyproject.toml` scope from the script directory to the whole repo
- enable stricter flags in a staged order:
  - `disallow_untyped_defs`
  - `disallow_incomplete_defs`
  - explicit-`Any` bans
  - selected `Any`-expression restrictions as the codebase permits
- avoid flipping every strict flag at once if it obscures actionable errors

Pragmatic note:

- the correct end state is stricter than today
- the pragmatic rollout is staged so contributors can still read failures and ship fixes safely

Verification:

- repo-wide `mypy` must become a stable default developer command

### Phase 6: Cross-Platform Runtime Validation

Goal:

- prove the refactor preserved behavior on macOS, Linux, and Windows

Actions per OS:

- install the skill cleanly
- run `$notifications on`
- verify config mutation and snapshot creation
- run a supported event through `notify_event.py`
- run `$notifications off`
- verify restore behavior and snapshot cleanup
- rerun idempotency checks

Platform-specific focus:

- macOS: `afplay`, then `osascript`, then terminal bell fallback
- Linux: `paplay`, then `canberra-gtk-play`, then terminal bell fallback
- Windows: WAV playback, `winsound.Beep`, PowerShell chime, alias fallback, plus interpreter-path stability after upgrade

Verification artifact:

- keep a short manual test log per OS in the implementation PR description or release notes draft

## Manual Testing Cadence

Run manual testing at these points:

1. Phase 0 baseline
   Run one smoke pass on macOS, Linux, and Windows before the first runtime refactor edit.

2. After any shipped runtime behavior change
   If a change touches `notifications_ctl.py`, `notifications_state.py`, or `notify_event.py`, run a targeted smoke test immediately on the affected OS.

3. End of Phase 3
   Once production typing/refactor work is complete, run a full three-OS smoke pass before spending time polishing the test harness.

4. End of Phase 5 / start of Phase 6
   Run the full release-candidate manual validation matrix on macOS, Linux, and Windows.

5. Immediately before release
   Re-run the final release-candidate manual checks if any runtime commit lands after the prior full manual pass.

## Current Runtime Follow-Up

### 2026-04-05 macOS smoke finding

A targeted manual smoke pass on macOS against the installed skill found that the
normal supported-event path selected `osascript -e beep` instead of the
documented primary backend `afplay`.

Observed behavior:

- `afplay /System/Library/Sounds/Glass.aiff` was present and exited successfully
- on this host it took about `3.4s` wall-clock to complete
- the current `run_command(...)` helper in `notify_event.py` uses
  `timeout=2`, so the `afplay` attempt is treated as a failure and the hook
  falls through to `osascript`

Chosen remediation proposal:

- keep backend order unchanged on macOS: `afplay`, then `osascript`, then
  terminal bell fallback
- replace the single hard-coded command timeout in `notify_event.py` with
  backend-specific timeouts
- give `afplay` a larger timeout budget while keeping the other command paths
  tight so Linux and Windows failure latency does not increase unnecessarily
- add macOS regression coverage in `tests/test_notify_event.py` for:
  - primary-path selection
  - `osascript` fallback selection
  - terminal bell fallback selection

Why this proposal is preferred:

- raising the timeout globally would broaden latency risk across non-macOS
  backends
- reordering macOS to prefer `osascript` first would change the intended product
  behavior instead of fixing the regression
- async fire-and-forget `afplay` handling is possible, but it adds more process
  lifecycle complexity than this case needs

Verification for the fix:

- run `ruff check .`
- run `mypy`
- run `python3 -m unittest discover -s tests -v`
- rerun the targeted macOS smoke flow with a disposable `CODEX_HOME`
- confirm the normal supported-event path now reports `darwin:afplay`
- confirm forced fallback still reports `darwin:osascript-beep`
- confirm double-failure still reports `terminal-bell`

## Manual Testing Checklist

Use this checklist for the Phase 0 baseline and the final release-candidate pass.

### Shared setup

- use Python `3.11+`
- use a disposable `CODEX_HOME`
- test both:
  - clean skill install
  - upgrade path from the currently released skill

### Shared functional checks

- run `$notifications on`
- verify `config.toml` contains the expected:
  - `notify`
  - `tui.notifications`
  - `tui.notification_method`
- verify the snapshot file is created
- trigger a supported event through `notify_event.py`
- confirm audible output or intended fallback
- run `$notifications off`
- verify prior values restore correctly, or safe fallback applies correctly when no valid snapshot exists
- verify the snapshot file is removed after restore
- run `on` twice and `off` twice to confirm idempotency
- verify invalid payloads do not break the hook process
- verify command JSON and exit behavior remain stable

### Platform-specific checks

The platform checks below are derived from the current runtime implementation in `.agents/skills/notifications/scripts/notify_event.py` and should be updated if backend order changes.

- macOS:
  - verify `afplay` first
  - verify `osascript -e beep` fallback
  - verify terminal bell fallback if both prior backends are unavailable

- Linux:
  - verify `paplay` first
  - verify `canberra-gtk-play` fallback
  - verify terminal bell fallback if prior backends are unavailable

- Windows:
  - verify WAV playback through `winsound.PlaySound(..., SND_FILENAME)`
  - verify deterministic `winsound.Beep(...)` chime fallback
  - verify PowerShell console-beep fallback
  - verify alias fallback through `winsound.PlaySound(..., SND_ALIAS)` and `winsound.MessageBeep(...)`
  - verify interpreter-path stability after upgrade

### What manual testing is not for

- malformed snapshot and blocked-write edge cases should stay primarily automated unless a refactor directly changes that logic
- manual testing should focus on user-visible runtime behavior, upgrade behavior, and OS-specific backend behavior

### Phase 7: Release and Upgrade Review

Goal:

- ship the refactor safely

Actions:

- update `CHANGELOG.md` with actual completed changes
- update `MIGRATIONS.md` if any platform now requires explicit user action
- tag the release as `v0.4.0` if the refactor lands without changing the existing runtime contract

Rollback plan:

- if cross-platform behavior regresses, revert the refactor commits on `main` and keep the pre-refactor release line intact
- if only strict typing configuration proves too aggressive, keep runtime refactors and relax only the specific gating flag that blocks adoption

Release-policy rollback note:

- the Python `3.11+` support-floor decision should only be reversed by an explicit product decision, not as an incidental implementation convenience

## Proposed Quality Gates After Refactor

- `ruff check .`
- `mypy`
- `python3 -m unittest discover -s tests -v`

Recommended `mypy` end state:

- repo-wide scope
- no explicit `Any` in production code
- no untyped production functions
- tests checked under the same `3.11+` supported baseline as the shipped project

## Cross-Platform Test Matrix

| Area | macOS | Linux | Windows |
|---|---|---|---|
| `$notifications on` writes config | Required | Required | Required |
| snapshot file creation | Required | Required | Required |
| notify hook event parsing | Required | Required | Required |
| primary sound backend path | `afplay` | `paplay` or `canberra-gtk-play` | WAV or `winsound` |
| fallback path | terminal bell | terminal bell | PowerShell or alias fallback |
| `$notifications off` restore | Required | Required | Required |
| idempotency (`on/on`, `off/off`) | Required | Required | Required |
| upgrade stability of interpreter path | N/A | N/A | Required |

## Definition of Done

The refactor is done when all of the following are true:

- repo-wide `mypy` is part of the normal gate
- production code has no explicit `Any`
- production orchestration is fully annotated
- tests no longer rely on dynamic untyped module handles
- docs and migration notes reflect the actual shipped policy
- macOS, Linux, and Windows behavior matches the pre-refactor contract
