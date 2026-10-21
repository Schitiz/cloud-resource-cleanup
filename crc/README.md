# crc

## Purpose

Top-level package of the cleanup tool. The CLI entry point is `crc.py` in the repository root
(same name as this package); the cloud code lives in the sub-packages. Direct modules:

- `service.py`: `Service`, the base class of every cleaner (age gate, custom age tag, `is_old`).
  Age handling delegates to `crc/core/age.py`.
- `notifications.py`: `human_readable_timedelta`, `send_slack_message`, `notify_cleanup`.
- `utils.py`: `init_logging`.
- `core/` (refactored, see `crc/core/README.md`), `aws/`, `azu/`, `gcp/`, `oci/` (legacy, one README each).

`crc/__init__.py` holds only a copyright comment. The modules directly in `crc/` are legacy,
not yet refactored; any change must follow `ARCHITECTURE.md` and the refactor rung that owns them.

## Public API

Not synced with ARCH-002 (the direct modules are legacy and `crc/__init__.py` has no `__all__`).

- `Service`: age gate and logging base class (`crc/service.py`).
- `init_logging()`: log file setup (`crc/utils.py`).
- `human_readable_timedelta()`, `send_slack_message()`, `notify_cleanup()`: Slack helpers (`crc/notifications.py`).

## Safety Invariants

- Authoritative text: `CLEANUP_SAFETY.md` (age gates SAF-006 to SAF-013).
- Dependency rules (import-linter): cloud packages never import each other; `crc.core` never
  imports a cloud package, `crc.notifications`, `crc.service` or an SDK.
- Known bugs and quirks of these modules: `docs/refactor/BUGS.md` rows `BUG-016`, `BUG-024` to
  `BUG-027`, `BUG-004` (age handling on `main`: `crc/service.py`).
- Log messages are part of the behaviour; keep them identical.

## Extension Rules

1. New code for cloud resources goes in `crc/<cloud>/` following `ARCHITECTURE.md`; shared pure
   logic goes in `crc/core/`.
2. Do not add modules to the legacy lists in `pyproject.toml`; refactoring a module removes it.
3. A new sub-directory needs a `README.md` with the four sections (ARCH-002).
4. Record every new bug or quirk in `docs/refactor/BUGS.md` with its `main` file:line.
