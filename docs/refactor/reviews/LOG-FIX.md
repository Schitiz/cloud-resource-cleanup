## Coding summary

Rung LOG-FIX (owner-approved 2026-10-22; contract `docs/refactor/LOGGING.md`). Fixes the
regressions of the Jenkins dry run `crc-dry-run-compare` build 4 in the LOG work. Log text and
levels only: nothing selected, deleted, stopped, posted or written differs, no CLI flag, no exit
code, no oracle edited.

Bug IDs handled: BUG-363 (new, fixed in LOG-FIX; exists on main: no); BUG-361 follow-up (REGION
level); BUG-360 follow-up (`--scan_tag` path).

Files changed:

- `crc/core/logger.py`: `RunLog` writes through `logging.getLogger("crc.run")` (never a
  module-level `logging.*` call, which runs `basicConfig()` on a root logger without handlers).
  `begin()` holds the RUN START line (`RunLog.hold_header`) until the first run-log line emitted
  after the root logger has handlers, then emits it once before that line; `finish()` emits a
  still-held RUN START before SKIPPED/ERRORS/RESULT. `RunLog.region()` logs DEBUG when
  `selected == 0`, INFO otherwise (a skipped region never calls `region()`; counters unchanged).
- `crc/cli/dispatch.py`: the three `logging.warning` calls of the spot handlers (they run before
  any cleaner, so before `init_logging`) use a module logger (`_LOG`). Grep of `crc/` for other
  module-level `logging.*` calls in the CLI path: `crc/cli/*`, `crc/service.py`, `crc/notify/*`
  and `crc/notifications.py` have none besides these and `init_logging` itself (called after the
  handlers exist); all cleaner code runs after `Service.__init__`.
- `crc/cli/scan.py`: `_scan_cloud` wraps the scan in `logger.begin(cloud, "vm", "scan", True,
  ...)` / `logger.finish()` in a try/finally (one pair per cloud); the old body is
  `_scan_and_report`, unchanged. Options come from `dispatch._run_options`.
- Docs: `docs/refactor/LOGGING.md` (named logger, held header, REGION level, scan), `BUGS.md`
  (BUG-363), `PLAN.md` and `STATUS.md` (LOG-FIX row).
- Tests: new `tests/test_cli_logging_init.py` (CLI path from a root logger without handlers with
  a fake cleaner that calls `init_logging`: only the init_logging handlers exist afterwards, no
  line printed twice, RUN START once before REGION and RESULT; no-handler run still emits
  RUN START then RESULT; dispatch warning does not run basicConfig; no module-level logging call
  in logger/dispatch/scan; fails on the old code). Updated `tests/test_core_logger.py` (REGION
  DEBUG when nothing selected) and `tests/test_cli_main_parity.py` (scan pass now logs RUN START /
  RESULT with operation=scan; outcome still equal to the oracle).

Test count (pytest -q): 42432 before (df0c911), 42437 after (4 new tests in `tests/test_cli_logging_init.py`, 1 new in `tests/test_core_logger.py`, 0 removed; `tests/test_oci_logger.py` and `tests/test_gcp_logger.py` updated for the DEBUG REGION level). `make check` green.

Left: nothing. Parity tests of the cloud lanes needed no change
(they assert oracle lines only).

No locked safety test asserts these log levels; no `## Owner action`.
