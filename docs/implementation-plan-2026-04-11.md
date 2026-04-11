# Notifications Skill Implementation Plan

Date: 2026-04-11  
Scope: Prioritized fixes from latest Windows/Linux/macOS validation reports  
Status: Revised after post-Bundle-A reruns (2026-04-11)

## Objective

Resolve highest-risk runtime issues first while reducing expensive full-matrix reruns.

This plan explicitly balances:
- Runtime correctness risk
- User-facing blast radius
- Validation cost (Windows CLI+App ~60 minutes, Linux CLI ~20 minutes, plus macOS validation)

## Evidence Summary

Primary source reports used for prioritization:
- Windows: [/Users/danielmulec/utm-shared/utm-shared/notification-skill-validation-report-2026-04-10.md](/Users/danielmulec/utm-shared/utm-shared/notification-skill-validation-report-2026-04-10.md)
- Linux: [/Users/danielmulec/utm-shared/utm-shared/notifications-skill-linux-validation-report-2026-04-10.md](/Users/danielmulec/utm-shared/utm-shared/notifications-skill-linux-validation-report-2026-04-10.md)
- macOS: [/Users/danielmulec/utm-shared/utm-shared/notifications-skill-macos-validation-report-2026-04-11.md](/Users/danielmulec/utm-shared/utm-shared/notifications-skill-macos-validation-report-2026-04-11.md)
- Windows rerun: [/Users/danielmulec/utm-shared/utm-shared/windows-validation-report-2026-04-11-rerun.md](/Users/danielmulec/utm-shared/utm-shared/windows-validation-report-2026-04-11-rerun.md)
- Windows CLI rerun after reinstall: [/Users/danielmulec/utm-shared/utm-shared/windows-validation-report-2026-04-11-rerun-after-reinstall.md](/Users/danielmulec/utm-shared/utm-shared/windows-validation-report-2026-04-11-rerun-after-reinstall.md)
- Linux rerun: [/Users/danielmulec/utm-shared/utm-shared/notifications-skill-linux-validation-report-2026-04-11-rerun.md](/Users/danielmulec/utm-shared/utm-shared/notifications-skill-linux-validation-report-2026-04-11-rerun.md)
- macOS rerun: [/Users/danielmulec/utm-shared/utm-shared/notifications-skill-macos-validation-report-2026-04-11-rerun.md](/Users/danielmulec/utm-shared/utm-shared/notifications-skill-macos-validation-report-2026-04-11-rerun.md)

Note:
- Linux reports currently exist under two filenames with identical content/hash:
  - `/Users/danielmulec/utm-shared/utm-shared/notifications-skill-linux-validation-report-2026-04-10.md`
  - `/Users/danielmulec/utm-shared/utm-shared/codex-linux-notifications-skill-validation-report-2026-04-10.md`

## Prioritized Issue Ledger

### 1) Cross-platform fallback safe-off clobbers custom TUI settings when snapshot is missing

Priority: Closed (fixed in Bundle A)

Evidence:
- Linux reproduction and impact: [notifications-skill-linux-validation-report-2026-04-10.md#L12](/Users/danielmulec/utm-shared/utm-shared/notifications-skill-linux-validation-report-2026-04-10.md#L12)
- macOS reproduction and checklist failure: [notifications-skill-macos-validation-report-2026-04-11.md#L28](/Users/danielmulec/utm-shared/utm-shared/notifications-skill-macos-validation-report-2026-04-11.md#L28)

Why fix now:
- Real user-visible behavior bug in recovery path.
- Reproduced on more than one OS, so not host-specific.
- Violates stated contract "remove only skill-managed overrides."

Risk if deferred:
- Users with missing/corrupt snapshot can lose custom `tui.notifications` preference.

Acceptance criteria:
- If snapshot missing and `notify` matches skill but TUI settings are custom, `off` removes only skill-owned values and does not force custom `tui.notifications` to `false`.
- Linux and macOS targeted matrix checks for this scenario pass.

Current status evidence:
- macOS rerun confirms no repro: [notifications-skill-macos-validation-report-2026-04-11-rerun.md#L43](/Users/danielmulec/utm-shared/utm-shared/notifications-skill-macos-validation-report-2026-04-11-rerun.md#L43)
- Linux rerun confirms no repro: [notifications-skill-linux-validation-report-2026-04-11-rerun.md#L52](/Users/danielmulec/utm-shared/utm-shared/notifications-skill-linux-validation-report-2026-04-11-rerun.md#L52)
- Windows rerun confirms no repro in corrected scenario: [windows-validation-report-2026-04-11-rerun-after-reinstall.md#L98](/Users/danielmulec/utm-shared/utm-shared/windows-validation-report-2026-04-11-rerun-after-reinstall.md#L98)

### 2) Windows command contract mismatch (`python3` first-call fragility)

Priority: P1 (partially resolved, still open at gate layer)

Evidence:
- Original finding: [notification-skill-validation-report-2026-04-10.md#L17](/Users/danielmulec/utm-shared/utm-shared/notification-skill-validation-report-2026-04-10.md#L17)
- Reconfirmed in addendum: [notification-skill-validation-report-2026-04-10.md#L241](/Users/danielmulec/utm-shared/utm-shared/notification-skill-validation-report-2026-04-10.md#L241)

Why fix now:
- High-frequency failure mode on Windows hosts without a real `python3` binary.
- Impacts first-attempt skill execution reliability.

Risk if deferred:
- Continued "fails first, recovers on retry" behavior in real Windows usage.

Acceptance criteria:
- Windows skill invocation succeeds without relying on `python3` alias availability.
- Contract docs and runtime behavior are aligned (no contradictory launcher guidance).

Current status evidence:
- Runtime interpreter stability after reinstall: [windows-validation-report-2026-04-11-rerun.md#L112](/Users/danielmulec/utm-shared/utm-shared/windows-validation-report-2026-04-11-rerun.md#L112)
- `python3` gate command still fails on host: [windows-validation-report-2026-04-11-rerun.md#L44](/Users/danielmulec/utm-shared/utm-shared/windows-validation-report-2026-04-11-rerun.md#L44), [windows-validation-report-2026-04-11-rerun-after-reinstall.md#L40](/Users/danielmulec/utm-shared/utm-shared/windows-validation-report-2026-04-11-rerun-after-reinstall.md#L40)

### 3) Windows PowerShell fallback effectively unreachable due to timeout budget

Priority: P1 (open, behavior clarified by reruns)

Evidence:
- First addendum: [notification-skill-validation-report-2026-04-10.md#L132](/Users/danielmulec/utm-shared/utm-shared/notification-skill-validation-report-2026-04-10.md#L132)
- Reconfirmed in second addendum: [notification-skill-validation-report-2026-04-10.md#L250](/Users/danielmulec/utm-shared/utm-shared/notification-skill-validation-report-2026-04-10.md#L250)

Why fix now:
- Current documented fallback order is not reliably realized on observed host timing.
- This is a behavior-contract integrity issue for Windows fallback strategy.

Risk if deferred:
- PowerShell fallback appears available on paper but is practically skipped due to timeout.

Acceptance criteria:
- Under forced Windows fallback conditions, PowerShell path can succeed within configured timeout budget or is intentionally reprioritized/documented.
- Windows fallback order test evidence is deterministic.

Current status evidence:
- Forced cascade can reach PowerShell stage: [windows-validation-report-2026-04-11-rerun-after-reinstall.md#L78](/Users/danielmulec/utm-shared/utm-shared/windows-validation-report-2026-04-11-rerun-after-reinstall.md#L78)
- Live helper still fails in this environment due to timeout sensitivity: [windows-validation-report-2026-04-11-rerun-after-reinstall.md#L91](/Users/danielmulec/utm-shared/utm-shared/windows-validation-report-2026-04-11-rerun-after-reinstall.md#L91)

### 4) Windows test portability and blocked-write determinism issues

Priority: P1 (promoted due to repeated gate failures)

Evidence:
- Path/TOML portability failure: [notification-skill-validation-report-2026-04-10.md#L26](/Users/danielmulec/utm-shared/utm-shared/notification-skill-validation-report-2026-04-10.md#L26)
- Blocked-write environment sensitivity: [notification-skill-validation-report-2026-04-10.md#L33](/Users/danielmulec/utm-shared/utm-shared/notification-skill-validation-report-2026-04-10.md#L33)

Why fix later than P1:
- Primarily confidence infrastructure, not direct runtime behavior on successful paths.

Risk if deferred:
- Reduced trust in Windows CI/local test outcomes.

Acceptance criteria:
- Windows unit suite no longer fails due to path escaping assumptions.
- Blocked-write test logic is robust against elevated/admin-like host conditions.

Current status evidence:
- Rerun still reports TOML/path fixture escaping errors and blocked-write mismatch: [windows-validation-report-2026-04-11-rerun.md#L54](/Users/danielmulec/utm-shared/utm-shared/windows-validation-report-2026-04-11-rerun.md#L54)

### 5) Process hygiene and operational guardrails

Priority: P3

Evidence:
- Installed-vs-repo mismatch finding: [notification-skill-validation-report-2026-04-10.md#L141](/Users/danielmulec/utm-shared/utm-shared/notification-skill-validation-report-2026-04-10.md#L141)
- Linux dependency readiness note: [notifications-skill-linux-validation-report-2026-04-10.md#L69](/Users/danielmulec/utm-shared/utm-shared/notifications-skill-linux-validation-report-2026-04-10.md#L69)

Why this is lower priority:
- Mostly operational/documentation clarity and validation hygiene, not core runtime logic.

Acceptance criteria:
- Validation flow always declares exact installed-vs-repo version alignment.
- Dependency readiness checks are explicit in operator workflow.

Current status evidence:
- Linux dependency readiness remains a host-level operational issue (`tomlkit` missing in host `python3`): [notifications-skill-linux-validation-report-2026-04-11-rerun.md#L28](/Users/danielmulec/utm-shared/utm-shared/notifications-skill-linux-validation-report-2026-04-11-rerun.md#L28)
- Windows CLI rerun flags install/source mismatch that must be normalized in validation procedure before asserting release readiness: [windows-validation-report-2026-04-11-rerun-after-reinstall.md#L18](/Users/danielmulec/utm-shared/utm-shared/windows-validation-report-2026-04-11-rerun-after-reinstall.md#L18)

### 6) macOS migration objective gap: repo-context skill resolution still active

Priority: P1 (validation + possible runtime contract issue)

Evidence:
- Repo cwd resolves `$notifications` without installed skill copy, outside repo cwd does not: [notifications-skill-macos-validation-report-2026-04-11-rerun.md#L23](/Users/danielmulec/utm-shared/utm-shared/notifications-skill-macos-validation-report-2026-04-11-rerun.md#L23)
- Checklist marks global-only detection objective as failing in rerun: [notifications-skill-macos-validation-report-2026-04-11-rerun.md#L132](/Users/danielmulec/utm-shared/utm-shared/notifications-skill-macos-validation-report-2026-04-11-rerun.md#L132)

Why fix/validate now:
- Migration objective was to eliminate repo-context-dependent resolution behavior.
- If reproducible after clean restart/reinstall, this is a release-contract gap.

Risk if deferred:
- Ambiguous runtime behavior across cwd boundaries; hard to support/debug installs.

Acceptance criteria:
- Clean-room verification confirms one of:
  - repo-context resolution issue is not reproducible (validation artifact closed), or
  - behavior is reproducible and fixed/documented explicitly before release.

### 7) Windows static gate failure: mypy unreachable statement in platform branch

Priority: P1 (release gate)

Evidence:
- `mypy` rerun failure: [windows-validation-report-2026-04-11-rerun.md#L40](/Users/danielmulec/utm-shared/utm-shared/windows-validation-report-2026-04-11-rerun.md#L40)
- same failure in rerun-after-reinstall: [windows-validation-report-2026-04-11-rerun-after-reinstall.md#L39](/Users/danielmulec/utm-shared/utm-shared/windows-validation-report-2026-04-11-rerun-after-reinstall.md#L39)
- code location: [`skill-src/notifications/scripts/notifications_state.py:92`](/Users/danielmulec/Projekte/codexnotifications/skill-src/notifications/scripts/notifications_state.py#L92)

Why fix now:
- Required gate is failing.
- This blocks release even if runtime behavior appears correct.

Risk if deferred:
- Windows validation remains non-green; repeated false-negative confidence on release readiness.

Acceptance criteria:
- `mypy` passes consistently on supported validation hosts, including Windows.

## Chronological Implementation Sequence

1. Bundle A is complete (Issue #1 fixed; Issue #2 runtime portion improved).
2. Run macOS clean-room detection-boundary recheck for Issue #6 before code change:
   - reinstall from current `main`
   - restart Codex
   - execute repo-cwd vs outside-cwd detection test again
3. Implement Windows Hardening Bundle (Bundle B):
   - Issue #7 (`mypy` unreachable branch gate)
   - Issue #4 (Windows test portability + blocked-write determinism)
   - remaining Issue #2 contract/gate alignment (`python3` command baseline vs launcher policy)
   - Issue #3 PowerShell timeout strategy (either make reliable or intentionally demote and document)
4. Run Windows-targeted rerun after Bundle B (CLI + app fallback/order checks + full gates).
5. If Issue #6 reproduces after clean-room recheck, implement Bundle C (migration boundary fix/documentation).
6. Run Full Matrix Checkpoint (macOS + Linux + Windows) only after Bundle B (and Bundle C if needed).

## Validation Cadence (Cost-Optimized)

### Always run after every code commit (cheap gates)

- `ruff check .`
- `mypy`
- `python3 -m unittest discover -s tests -v`

### Targeted revalidation rules

After each runtime bundle, run only the touched behavior matrix segments:
- Bundle A:
  - Linux + macOS safe-off-without-snapshot custom-TUI preservation scenario
  - Windows first-call `$notifications on|off` launcher reliability scenario
- Bundle B:
  - Windows `mypy` + unittest gates
  - Windows forced fallback path verification for PowerShell stage
  - Windows launcher/command contract checks (`python3` baseline vs selected interpreter policy)
- Bundle C (if needed):
  - macOS repo-cwd vs outside-cwd detection boundary checks

### Full matrix checkpoints

- Checkpoint 1:
  - Run complete macOS + Windows + Linux validation only after Windows Hardening Bundle (Bundle B) is merged.
- Checkpoint 2 (conditional):
  - If macOS migration-boundary issue reproduces and requires code change, rerun full matrix after Bundle C.

## Counterpoint / Guardrails

- Batching every 2-3 fixes is efficient only when fixes are tightly related in the same runtime surface.
- Batching unrelated backend changes increases diagnosis cost if regression appears.
- Rule of thumb:
  - max 2 tightly-coupled runtime fixes per bundle before targeted rerun.
  - if bundle touches independent OS/backend paths, split earlier.

## Recommended Next Action

Start with the macOS clean-room detection-boundary recheck for Issue #6, then execute Bundle B as a single Windows hardening pass so we pay for one Windows rerun instead of multiple.
