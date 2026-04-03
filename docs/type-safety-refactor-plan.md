# Type Safety and Refactor Plan

This document defines the implementation plan for tightening typing, reducing dynamic behavior, and preserving runtime behavior across macOS, Linux, and Windows.

Status: planning only. No runtime behavior changes are implemented by this document.

## Objective

Ship the next implementation release with:

- stricter static analysis over the whole repo, not only the skill scripts
- no explicit `Any` in production code
- sharply reduced implicit `Any` in tests and helpers
- stable runtime behavior for `$notifications on` and `$notifications off` on macOS, Linux, and Windows

## Core Decision: Python Version Policy

The pragmatic and correct baseline is to keep the project typed and tested against Python `3.10` for now.

Reasoning:

- runtime code does not currently need Python `3.11+` features
- the current `3.11+` dependency is coming from test-side `tomllib`, not from the shipped skill
- raising the project floor for a test helper would reduce compatibility without a product benefit
- macOS, Linux, and Windows environments are easier to support when the runtime floor stays broader

Implementation consequence:

- keep `ruff` and `mypy` targets aligned to Python `3.10` unless the refactor reveals a concrete need to raise them
- replace or abstract test-side `tomllib` usage so tests remain compatible with the chosen baseline
- if a later implementation phase requires `3.11+`, update `README.md`, `INSTALL.md`, `CHANGELOG.md`, and `MIGRATIONS.md` in the same change series

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

### Phase 1: Fix the Python-Version Mismatch Without Raising Runtime Floor

Goal:

- make tests compatible with the chosen Python `3.10` baseline

Actions:

- remove direct dependency on `tomllib` in tests, or add a compatibility import path that works on `3.10`
- keep dev tooling and docs aligned with the chosen baseline
- rerun `mypy` over tests explicitly, not only over scripts

Why this phase comes first:

- otherwise repo-wide type-checking is polluted by an avoidable version-policy mismatch

Verification:

- `python3 -m mypy tests --check-untyped-defs`
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

- `python3 -m mypy tests --python-version 3.10 --check-untyped-defs`

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

### Phase 7: Release and Upgrade Review

Goal:

- ship the refactor safely

Actions:

- update `CHANGELOG.md` with actual completed changes
- update `MIGRATIONS.md` if any platform now requires explicit user action
- tag the release as `v0.4.0` if the refactor lands without changing the existing runtime contract

Rollback plan:

- if cross-platform behavior regresses, revert the refactor branch and keep the pre-refactor release line intact
- if only strict typing configuration proves too aggressive, keep runtime refactors and relax only the specific gating flag that blocks adoption

## Proposed Quality Gates After Refactor

- `ruff check .`
- `mypy`
- `python3 -m unittest discover -s tests -v`

Recommended `mypy` end state:

- repo-wide scope
- no explicit `Any` in production code
- no untyped production functions
- tests checked under the same supported Python baseline unless a documented exception exists

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
