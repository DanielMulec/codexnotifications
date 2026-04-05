# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Python tooling baseline via `pyproject.toml`:
  - Ruff linting (`E,F,W,I,UP,B,C90`)
  - McCabe complexity check (`C901`, max complexity `10`)
  - Mypy type-checking configuration for skill scripts
- Refactor planning documentation for the next implementation cycle:
  - staged type-safety and maintainability plan
  - cross-platform verification matrix for macOS, Linux, and Windows
  - explicit Python-version policy decision to standardize on `3.11+`

### Changed
- Updated notification scripts and tests formatting/import order to satisfy Ruff.
- Improved cross-platform typing for Windows sound backends in `notify_event.py`.
- Clarified that the current `mypy` gate only covers the bundled skill scripts and that repo-wide strict typing is planned work, not completed work.
- Added the repository workflow rule that all work stays on `main` unless Daniel explicitly requests an exception.
- Expanded the refactor plan with explicit manual-testing cadence, checklist, and backend-specific validation notes.
- Started the refactor implementation:
  - moved Ruff and Mypy to a Python `3.11` baseline
  - widened Mypy scope from the skill scripts into tests and typed test helpers
  - removed explicit `Any` from production notification scripts
- Restored the intended macOS notify-hook primary backend path by giving `afplay` a backend-specific timeout budget instead of forcing an early fallback to `osascript`.
- Added macOS regression coverage for `afplay`, `osascript`, and terminal bell backend selection in `notify_event.py`.

### Upgrade Notes
- Planned next implementation release will require Python `3.11+`.
- Users still on Python `3.10` will need to upgrade their interpreter before adopting that release.
- macOS users do not need to rerun `$notifications on`; after updating, supported events should use `afplay` first again when it is available and healthy.

### Versioning Plan
- Next intended implementation release: `0.4.0`
- Intended tag: `v0.4.0`
- Release goal: ship the typed/refactored codebase without changing user-facing notification behavior across macOS, Linux, and Windows.

## [0.3.0] - 2026-02-27

### Changed
- Improved Windows notification reliability and hook diagnostics.

### Upgrade Notes
- Windows users upgrading from `0.2.0` should run `$notifications on` once after updating.
- Reason: rewrites `notify` command to a stable interpreter path used by this version.

## [0.2.0] - 2026-02-24

### Added
- Beginner-facing docs and installation/uninstallation guidance.
- Public-facing README suitable for open-source onboarding.

### Changed
- Refactored notification state handling and adopted `tomlkit` for safer config mutation.
- Improved UX messaging and readability of notification control flows.

### Upgrade Notes
- No manual migration required from `0.1.0`.

## [0.1.0] - 2026-02-22

### Added
- Initial notifications skill implementation:
  - `$notifications on|off` control flow
  - Snapshot/restore state handling
  - Notify hook script and core unit tests

### Upgrade Notes
- Initial release, no migration path applies.
