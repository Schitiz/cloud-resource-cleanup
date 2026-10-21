# crc

## Purpose

Top-level package of the cleanup tool. The CLI entry point is `crc.py` in the repository root
(same name as this package); the cloud code lives in the sub-packages. Direct modules:

- `service.py` (refactored, strict-typed): `Service`, the base class of every cleaner (age gate,
  custom age tag, `is_old`). Age handling delegates to `crc/core/age.py`; the constructor calls
  `init_logging` for `logs/crc.log`. Parity oracle: `tests/legacy/crc_service.txt`,
  `tests/test_crc_service_parity.py`.
- `notifications.py`: compatibility shim re-exporting the Slack helpers that moved to `notify/slack.py`.
- `utils.py` (refactored, strict-typed): `init_logging`, `LOG_FORMATTER`. Parity oracle:
  `tests/legacy/crc_utils.txt`, `tests/test_crc_utils_parity.py`, unit tests `tests/test_crc_utils.py`.
- `core/` (refactored, see `crc/core/README.md`), `notify/` (refactored, see `crc/notify/README.md`), `aws/`, `azu/`, `gcp/`, `oci/` (legacy, one README each).

`crc/__init__.py` holds only a copyright comment. `service.py` and `utils.py` are refactored (rung
PL-CORE, no behaviour change); `notifications.py` is a shim; any change must follow
`ARCHITECTURE.md`.

## Public API

`crc/__init__.py` has no `__all__` (it holds only a copyright comment).

- `Service` (`crc/service.py`): age gate and logging base class. Attributes `logs_dir`, `logs_file`,
  `AGE_KEYS`; methods `require_positive_age`, `validated_retention_age`, `get_min_age`, `is_old`,
  `get_retention_age`; private helpers `_lookup_custom_age_tag`, `_parse_literal`. Aliases `AgeSpec`
  and `Tags` are type aliases for annotations.
- `init_logging()`, `LOG_FORMATTER` (`crc/utils.py`): log file setup.
- `human_readable_timedelta()`, `send_slack_message()`, `notify_cleanup()`: Slack helpers, now defined in `crc/notify/slack.py` and re-exported by `crc/notifications.py`.

## Safety Invariants

- Authoritative text: `CLEANUP_SAFETY.md` (age gates SAF-006 to SAF-013).
- Dependency rules (import-linter): cloud packages never import each other; `crc.core` never
  imports a cloud package, `crc.notifications`, `crc.service`, `crc.notify` or an SDK; `crc.notify`
  imports `crc.core` only (never a cloud package or `crc.service`).
- Notification bugs and quirks (`BUG-028` to `BUG-034`, `BUG-041`, `BUG-042`) are listed in
  `docs/refactor/BUGS.md`; their behaviour now lives in `crc/notify`, see its README.
- Known bugs and quirks of these modules: `docs/refactor/BUGS.md` rows `BUG-016`, `BUG-024` to
  `BUG-027`, `BUG-004` (age handling on `main`: `crc/service.py`).
- Log messages are part of the behaviour; keep them identical.
- SAF-LOG-001: `init_logging` mutates the root logger (level, one file handler in `mode="w"`, one
  console handler, WARNING for `azure`, `msrest`, `urllib3`), creates the log directory and prints
  `Setting loglevel to logging: <LEVEL>`; tests must use `tmp_path` and restore the handlers.
- SAF-AGE-001: every `Service` age method delegates to `crc.core.age` and matches `main`'s
  `crc/service.py` (oracle `tests/legacy/crc_service.txt`), including the `MAX_AGE` read in
  `is_old`, empty age returning True and literal parsing. Pending quirks:
  `docs/refactor/bugs/pending/PL-CORE.md`.

## Extension Rules

1. New code for cloud resources goes in `crc/<cloud>/` following `ARCHITECTURE.md`; shared pure
   logic goes in `crc/core/`.
2. Do not add modules to the legacy lists in `pyproject.toml`; refactoring a module removes it.
3. A new sub-directory needs a `README.md` with the four sections (ARCH-002).
4. Record every new bug or quirk in `docs/refactor/BUGS.md` with its `main` file:line.
5. A change to `service.py` or `utils.py` must keep `tests/test_crc_service_parity.py` and
   `tests/test_crc_utils_parity.py` green and only add cases; the oracles stay byte-identical to
   `main`.
