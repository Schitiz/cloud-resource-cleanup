## Coding summary

Rung LOG-FIX2 (owner-approved 2026-10-23; contract `docs/refactor/LOGGING.md`). Fixes the two
log-only regressions of the Jenkins dry run `crc-dry-run-compare` build 5 (A main 544441b vs B
8073087). Log text only: nothing selected, deleted, stopped, posted or written differs, no CLI
flag, no exit code, no oracle, no locked safety test edited.

Bug IDs handled: BUG-364 (RUN START printed when logging is initialised), BUG-365 (FAILED line
always one line). Both new rows, exist on main: no, severity low, status "fixed in LOG-FIX2".

Files changed:

- `crc/core/logger.py`: new public `logging_ready()` (emits the current run's held RUN START;
  no-op without a current run or held header; idempotent) backed by `RunLog.release_header()`.
  The existing fallbacks stay (next run-log line, `finish()`). `_error_text` collapses the
  message of the FAILED line: split on line breaks, strip, drop empty parts, join with ` | `
  (`error=<ExceptionType>: <message>` otherwise unchanged; per-resource error lines untouched).
- `crc/utils.py`: `init_logging` calls `logging_ready()` after the handlers are added (imports
  `crc.core.logger`, allowed by the import-linter contracts; `crc.core` imports nothing new).
- Docs: `docs/refactor/LOGGING.md`, `crc/core/README.md` (Public API), `docs/refactor/BUGS.md`
  (BUG-364, BUG-365 after BUG-363; Counts 365 rows, low 271), `PLAN.md` and `STATUS.md`
  (LOG-FIX2 row).
- Tests: `tests/test_cli_logging_init.py` (fake cleaner logs its own line right after
  `init_logging`; RUN START appears exactly once, before that line and before RESULT, on the
  console and in the file); `tests/test_core_logger.py` (`logging_ready` with no run, with a held
  header called twice, after emission, unattached run; multi-line FAILED message gives one line,
  single-line message unchanged).

Test count (pytest -q): 42438 before (8073087, per `STATUS.md`), 42444 after (6 new tests in `tests/test_core_logger.py`, 0 removed; the CLI test was extended in place). `make check` green.

Left: nothing.
