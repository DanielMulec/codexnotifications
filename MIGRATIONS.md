# Migrations

This document defines upgrade actions between released versions.

Migration in this project means: preserving existing user configuration and
notification behavior safely across upgrades, without corrupting config files or
breaking notify hook execution.

## Compatibility Matrix

| From | To | Affected Users | Required Action | Why |
|---|---|---|---|---|
| `0.1.0` | `0.2.0` | All | None | No persistent schema break introduced. |
| `0.2.0` | `0.3.0` | Windows | Run `$notifications on` once after update. | Rewrites `notify` command to a stable interpreter path for Windows. |
| `0.3.0` | `Unreleased` | All | None | Current unreleased state includes in-progress refactor work and a macOS backend timing fix; treat the `0.4.0` rows below as the release-target upgrade guidance. |
| `0.3.0` | `0.4.0` | All users on Python `3.10` | Upgrade Python to `3.11+` before updating. | Project support floor is planned to move to Python `3.11+`. |
| `0.3.0` | `0.4.0` | macOS | None | Restores `afplay` as the intended primary backend by giving it a backend-specific timeout budget. |

## Migration Policy

- Add a migration entry when any of these change:
  - Config key names or value semantics
  - Snapshot schema or restore behavior
  - Notify command/path format that prior installs still reference
  - Runtime behavior requiring user action after update
- If no user action is required, record `None` explicitly to keep upgrade intent clear.

## Planned Next Release

- Target release under active planning: `0.4.0`
- Intended upgrade posture: `0.3.0 -> 0.4.0` requires Python `3.11+`
- Constraint: if the implementation also changes snapshot semantics or Windows upgrade behavior, this document must be updated again before release
