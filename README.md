# codexnotifications

Planning and implementation repository for a global Codex notifications skill.

Primary goal:

- provide `$notifications on` and `$notifications off` skill commands
- enable reliable completion notifications and approval-request notification coverage
- keep behavior graceful across macOS/Linux/Windows and common terminal setups

Current implementation artifacts:

- `.agents/skills/notifications/SKILL.md`
- `.agents/skills/notifications/scripts/notifications_ctl.py`
- `.agents/skills/notifications/scripts/notifications_state.py`
- `.agents/skills/notifications/scripts/notify_event.py`
- `tests/test_notifications_ctl.py`
- `tests/test_notifications_state.py`

Install Python dependency:

```bash
python3 -m pip install -r requirements.txt
```

Run tests:

```bash
python3 -m unittest discover -s tests -v
```

Start with docs:

- `docs/README.md`
- `docs/notifications-noob-start-here.md`
- `docs/notifications-skill-v1-acceptance-spec.md`
