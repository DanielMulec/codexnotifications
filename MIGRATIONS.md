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
| `0.3.0` | `Unreleased` | All | None | Tooling and code-quality baseline only; runtime contract unchanged. |

## Migration Policy

- Add a migration entry when any of these change:
  - Config key names or value semantics
  - Snapshot schema or restore behavior
  - Notify command/path format that prior installs still reference
  - Runtime behavior requiring user action after update
- If no user action is required, record `None` explicitly to keep upgrade intent clear.
