# Global-Only Skill Detection Migration Proposal

Date: 2026-04-11  
Owner: CTO proposal for Daniel (CEO/CPO) approval  
Status: Proposal only, no implementation in this document

## Objective

Eliminate duplicate `notifications` skill detection across Codex CLI and Codex App by ensuring normal runtime discovery resolves only one installed global skill copy per machine.

## Current Problem

The repository currently keeps the skill source under `.agents/skills/notifications`, which can be auto-detected in local workspace contexts while a separate installed copy exists under `${CODEX_HOME:-$HOME/.codex}/skills/notifications`.

Result:
- some environments detect both copies
- UX ambiguity about which copy executes
- increased risk of installed-vs-repo drift during validation

## Proposed Action

Move the repository skill source out of the auto-discovery path and keep global install as the single runtime target.

## Plan

1. Move source of truth in this repo:
- from `.agents/skills/notifications`
- to `skill-src/notifications`

2. Update all repository references:
- docs (`README.md`, `INSTALL.md`, developer docs)
- tests and tooling paths (`tests/*`, `pyproject.toml`)

3. Remove repo-local fallback in the skill execution snippet:
- remove `.agents/skills/...` fallback path from `SKILL.md`
- keep explicit global path usage only

4. Keep install behavior global-only:
- `$skill-installer` and manual instructions point to `skill-src/notifications`
- install destination remains `${CODEX_HOME:-$HOME/.codex}/skills/notifications`

5. Validate on macOS, Linux, Windows:
- verify only global skill is detected after install
- verify `$notifications on|off` behavior remains unchanged

## Better Alternatives Considered

1. Keep `.agents/skills/...` and accept duplicates.
- Rejected: preserves current UX confusion and drift risk.

2. Keep `.agents/skills/...` but add naming/version guards.
- Rejected: mitigates symptoms but keeps dual-discovery architecture.

3. Remove repository copy entirely and develop only in global directory.
- Rejected: poor reproducibility, weak reviewability, and brittle CI/testing in repo context.

## Risks

1. Path migration breakage:
- tests, docs, or tooling may still reference old `.agents/skills/...` path.

2. Installer mismatch:
- install instructions may temporarily drift during transition.

3. Consumer disruption:
- users following cached old docs may target stale path.

## Risk Controls

1. One-pass path audit with strict grep before merge.
2. Full required local quality gate:
- `ruff check .`
- `mypy`
- `python3 -m unittest discover -s tests -v` (or `py -m unittest discover -s tests -v` on Windows when `python3` alias is unavailable)
3. Explicit CHANGELOG and MIGRATIONS updates for upgrade clarity.
4. Cross-platform smoke validation against freshly installed global skill.

## Rollback Plan

If migration introduces regressions:

1. Revert the migration commit(s) on `main`.
2. Restore previous source path `.agents/skills/notifications`.
3. Re-run quality gate and platform smoke checks.
4. Publish rollback note in `CHANGELOG.md`.

Rollback impact:
- low data risk (documentation/pathing only)
- moderate operational risk (temporary install guidance churn)

## Expected Outcome

1. Codex CLI/App detect one authoritative global `notifications` skill in standard usage.
2. Development remains repository-based and reviewable.
3. Installed-vs-repo alignment improves because runtime source is unambiguous.

## Verification Method

Functional:
1. Install from repo path `skill-src/notifications` into global skills dir.
2. Restart Codex CLI/App.
3. Confirm single `notifications` skill entry is detected.
4. Run `$notifications on` then `$notifications off`.
5. Confirm expected config mutation, snapshot behavior, and idempotency.

Static/automated:
1. `ruff check .`
2. `mypy`
3. `python3 -m unittest discover -s tests -v` (or `py -m unittest discover -s tests -v` on Windows when `python3` alias is unavailable)

Cross-platform:
1. Repeat functional verification on macOS.
2. Repeat functional verification on Linux.
3. Repeat functional verification on Windows.

## Approval Needed (Go/No-Go)

Implementation should start only after explicit Daniel approval of this proposal.
