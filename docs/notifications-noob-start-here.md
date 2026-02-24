# Notifications Noob Start Here

This guide explains exactly how `$notifications on` and `$notifications off` work, with examples from this repo.

It is written for early-stage Python/Codex users without assuming prior familiarity with TOML internals.

## 1. Quick Orientation

The behavior is implemented by three files:

1. `.agents/skills/notifications/scripts/notify_event.py`  
   Small runtime hook that plays sound for completion events.
2. `tests/test_notifications_ctl.py`  
   Concrete examples of expected behavior (`on`, `off`, idempotency, blocked write).
3. `.agents/skills/notifications/scripts/notifications_ctl.py`  
   Main control script that edits `config.toml`, snapshots prior state, and restores it.

## 2. Step-by-Step: `$notifications on`

1. Command parser accepts only `on` or `off`.  
   Invalid usage returns `Usage: $notifications on|off`.
2. Config path is resolved:
   - `$CODEX_HOME/config.toml` if `CODEX_HOME` is set
   - otherwise `~/.codex/config.toml`
3. Script checks whether config directory is writable.
4. Current `config.toml` is loaded.
5. Prior values for `notify`, `tui.notifications`, and `tui.notification_method` are captured.
6. Script sets target "on" values:

```toml
notify = ["python3", "<absolute path to notify_event.py>"]

[tui]
notifications = ["approval-requested"]
notification_method = "bel"
```

7. Snapshot is written to JSON file.
8. Updated TOML is written atomically.
9. JSON result is emitted with status:
   - `applied` if changes were made
   - `already-applied` if config already matched target

## 3. Step-by-Step: `$notifications off`

1. Script looks for snapshot file.
2. If snapshot exists and is valid:
   - restore prior values
   - write config (if changed)
   - delete snapshot
3. If snapshot does not exist:
   - disable only skill-managed values safely
   - avoid touching unrelated user config
4. JSON result is emitted with status:
   - `applied` if changes were made
   - `already-applied` if nothing needed changing

## 4. Before/After Examples

### Example A: Clean config -> `on`

Before `config.toml`:

```toml
```

After `config.toml`:

```toml
notify = ["python3", "/abs/path/to/notify_event.py"]

[tui]
notifications = ["approval-requested"]
notification_method = "bel"
```

Snapshot file (`.codex-notifications-v1-snapshot.json`):

```json
{
  "version": 1,
  "created_at": "2026-02-24T12:34:56.000000+00:00",
  "config_path": "/home/user/.codex/config.toml",
  "prior": {
    "notify": {
      "present": false
    },
    "tui.notifications": {
      "present": false
    },
    "tui.notification_method": {
      "present": false
    }
  }
}
```

### Example B: Existing custom config -> `on` -> `off`

Before `config.toml`:

```toml
model = "gpt-5"
notify = ["python3", "/tmp/original_notify.py"]

[tui]
notifications = true
notification_method = "auto"
```

After `on`:

```toml
model = "gpt-5"
notify = ["python3", "/abs/path/to/notify_event.py"]

[tui]
notifications = ["approval-requested"]
notification_method = "bel"
```

After `off` (restored from snapshot):

```toml
model = "gpt-5"
notify = ["python3", "/tmp/original_notify.py"]

[tui]
notifications = true
notification_method = "auto"
```

## 5. Function Map (notifications_ctl.py)

| Function | Plain-English purpose |
|---|---|
| `build_result` | Build standard JSON result payload. |
| `emit_result` | Print result payload as JSON. |
| `is_permission_block` | Detect permission/sandbox write-read block errors. |
| `resolve_config_path` | Resolve global Codex config path. |
| `resolve_snapshot_path` | Resolve snapshot file path. |
| `resolve_notify_script_path` | Resolve absolute path to `notify_event.py`. |
| `prepare_config_directory` | Ensure config directory exists and is writable. |
| `load_toml_document` | Read and parse TOML into Python dict. |
| `format_key` | Serialize a TOML key safely. |
| `format_value` | Serialize a TOML value safely. |
| `emit_table` | Recursively serialize TOML table sections. |
| `dump_toml_document` | Convert full TOML dict back to TOML text. |
| `atomic_write_text` | Write file safely via temp file + replace. |
| `write_toml_document` | Serialize and atomically write TOML config. |
| `key_state` | Store key presence/value for snapshot data. |
| `capture_prior_state` | Capture prior values before applying `on`. |
| `write_snapshot` | Persist prior state to snapshot JSON file. |
| `load_snapshot` | Load and validate snapshot JSON. |
| `remove_snapshot` | Delete snapshot file. |
| `normalized_path` | Normalize and resolve a filesystem path. |
| `notify_target_value` | Build target `notify` command value. |
| `is_skill_notify_value` | Check if current `notify` is this skill's value. |
| `is_target_on` | Detect if config already matches "on" state. |
| `apply_on_state` | Apply "on" settings to in-memory config. |
| `restore_key` | Restore top-level key from snapshot state. |
| `restore_tui_key` | Restore nested `[tui]` key from snapshot state. |
| `apply_snapshot_restore` | Restore all tracked keys and report change. |
| `apply_safe_off_without_snapshot` | Turn off skill-managed settings when snapshot is missing. |
| `blocked_result` | Build blocked result with remediation guidance. |
| `failed_result` | Build generic failure result. |
| `execute_on` | Full `on` flow (snapshot + apply + write). |
| `execute_off` | Full `off` flow (restore or safe fallback). |
| `execute_command` | Route command + shared setup and error handling. |
| `parse_args` | Parse CLI args and help flags. |
| `exit_code_for_status` | Map status to process exit code. |
| `main` | CLI entrypoint and top-level orchestration. |

## 6. Tiny Glossary

- `TOML`: Config file format used by Codex (`config.toml`).
- `Atomic write`: Write to temp file, then replace original in one final step to reduce corruption risk.
- `Idempotent`: Running the same command again does not keep changing state.
- `Snapshot`: Saved copy of previous key values so `off` can restore user settings.
- `Sandbox block`: Environment policy prevented reading/writing the global config path.

## 7. Recommended Reading Order

1. `.agents/skills/notifications/scripts/notify_event.py`  
   Shortest file; easiest entry point.
2. `tests/test_notifications_ctl.py`  
   Shows expected behavior as executable examples.
3. `.agents/skills/notifications/scripts/notifications_ctl.py`  
   Read with test file open beside it.
