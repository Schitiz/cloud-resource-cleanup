## Coding summary

Rung LOG-0 (core lane of the LOG family, contract in `docs/refactor/LOGGING.md`). Log text and
levels only; no selection, deletion, Slack or Influx behaviour, CLI flag or exit code changed.

Files changed:

- `docs/refactor/BUGS.md`: BUG-356 to BUG-362 added (BUG-357 in the medium group, the rest at the
  end of the low group; main `file:line` verified with `git show main:<path>`; all "exists on
  main: yes", status "open; fixed by the LOG lane that names it"); counts line corrected to 362 rows.
- `docs/refactor/PLAN.md` (owner-approved edit, 2026-10-22): LOG-0, LOG-AWS1, LOG-AWS2, LOG-AZU,
  LOG-GCP, LOG-OCI rows ("May edit CLEANUP_SAFETY.md: no") and a sentence pointing to LOGGING.md.
- `docs/refactor/LOGGING.md` (new): the contract (why, bugs, rules, line formats, parity-test rule).
- `docs/refactor/STATUS.md`: LOG-0 row.
- `crc/core/runlog.py` (new), `crc/core/README.md` (Public API: `RunLog`, `begin`, `current`,
  `finish`; invariant about DEBUG age lines). Not re-exported from `crc.core.__init__` (generic
  names); callers use `from crc.core import runlog`.
- `crc/core/age.py`: the five per-resource age-check messages (main `service.py:231,252,259,263,
  294,297`) are DEBUG with unchanged text (BUG-356). "Found '<key>' tag" and "Overwriting resource
  age" stay INFO (not in the contract list).
- `crc/cli/dispatch.py`: `begin()` / `finish()` around every handler call in `run_dispatch` (try/
  finally; one RUN START / RESULT pair per cloud x resource pass, also `--cloud all`).
- Tests: `tests/test_core_runlog.py` (new), `tests/helpers_log_fix.py` (new, `expected_logs`,
  `expected_outcome`), `tests/test_log_fix_helpers.py` (new), `tests/test_cli_runlog.py` (new),
  `tests/test_crc_service_is_old_parity.py` and `tests/test_crc_service_parity.py` (every `_logs`
  comparison goes through `expected_outcome(old, {"BUG-356"})`, plus an explicit
  oracle != new case), `tests/test_core_age.py` (three log-level assertions now DEBUG, plus a check
  that nothing is logged at INFO).

Bug IDs handled: BUG-356 (fixed). BUG-360 and BUG-362 plumbing (runlog, CLI header and footer) is
in place; the rows stay open until the cloud lanes call `current().region/action/skip/fail`.
BUG-357, 358, 359, 361 are for the cloud lanes.

Test count: 42213 before (at 5f6ddcf), 42256 after. `make check` steps (ruff, mypy, lint-imports,
pytest) green on Python 3.12.3.

Left / notes:

- No Azure resource-group loop exists in `crc/cli` (a single `--resource_group` per run), so there
  is one RUN START / RESULT pair per cloud x resource pass.
- The CLI parity test (`tests/test_cli_main_parity.py`) collects WARNING and above only, so the
  INFO RUN START / RESULT lines never reach it and it stays equal to the oracle; the new lines are
  asserted exactly in `tests/test_cli_runlog.py`.
- `RUN START` / `RESULT` are also printed when the AWS EBS opt-in refusal or an AWS-only/skip
  warning handler returns early (zero counts); the exception still propagates unchanged.
- No locked safety test asserts these log levels; none was touched.
- `RunLog.region_skipped` accepts the error for the future; the contract logs nothing for it.

## Round 1 (Argon)

Scope reviewed: `git diff 5f6ddcf..HEAD` on branch `logging/core` (rung `LOG-0`, core lane of the `LOG` behaviour-fix family).

### Checks

1. **Behaviour & scope (`crc/core/age.py`, `crc/core/runlog.py`, `crc/cli/dispatch.py`)**:
   - Only the five per-resource age-check messages from `main:crc/service.py:231,252,259,263,294,297` in `crc/core/age.py` moved from `INFO`/`WARNING` to `DEBUG` with identical text (`BUG-356`). Other log lines (`Found '<key>' tag`, `Overwriting resource age`, `validated_retention_age` warnings, `parse_literal` errors) are untouched.
   - `crc/cli/dispatch.py` wraps each cleaner handler invocation in `runlog.begin(...)` / `try ... finally: runlog.finish()`, emitting one `RUN START` / `RESULT` pair per `--cloud` x `--resource` pass and letting exceptions propagate unchanged.
   - No changes to selection, deletion/stopping, SDK call order, Slack messages, InfluxDB points, CLI flags, exit codes, or cloud package logging.
2. **Line formats & levels (`crc/core/runlog.py`, `docs/refactor/LOGGING.md`)**:
   - `RUN START`, `REGION`, `ACTION`, `SKIPPED`, `ERRORS`, `FAILED`, and `RESULT` match the contract's key names, key order, log levels (`INFO` vs `ERROR`), `<region|->` / `<name|->` fallbacks, `<ExceptionType>: <message>` formatting, and compact sorted JSON option serialisation (`json.dumps(sort_keys=True, separators=(",", ":"))`) for the 9 specified option keys in order.
   - `current()` returns a fresh unattached `RunLog` when no run is active so cleaners and unit tests log nothing extra. Clock is injectable (default `time.monotonic`).
3. **Parity tests & oracles (`tests/helpers_log_fix.py`, `tests/test_crc_service_is_old_parity.py`, `tests/test_crc_service_parity.py`, `tests/test_cli_main_parity.py`)**:
   - All frozen oracles under `tests/legacy/` are untouched.
   - `expected_logs` / `expected_outcome` in `tests/helpers_log_fix.py` rewrites only log levels for `BUG-356` and never drops or alters message text.
   - Added `test_bug_356_retention_age_lines_differ_from_oracle_and_are_debug` in `tests/test_crc_service_parity.py` so both `crc.service` parity test modules explicitly assert `old[2] != new[2]` on `BUG-356` cases, and added `test_bug_360_main_logs_run_start_and_result_around_each_cleaner_pass` in `tests/test_cli_main_parity.py` to assert `INFO`-level `RUN START` / `RESULT` divergence against the `main()` oracle (`BUG-360`).
4. **Safety lock**:
   - `tests/archtest/safety_lock.json` and all five hash-locked safety test files are untouched.
5. **Docs & READMEs (`docs/refactor/BUGS.md`, `docs/refactor/PLAN.md`, `docs/refactor/LOGGING.md`, `docs/refactor/STATUS.md`, `crc/core/README.md`, `crc/cli/README.md`, `tests/README.md`, `docs/refactor/README.md`)**:
   - Verified every `main` `file:line` citation in `BUGS.md` (`BUG-356` to `BUG-362`, sorted by risk, counts updated to 362) and `LOGGING.md` against `git show main:<path>`.
   - `PLAN.md` has the owner-approved `LOG-0`, `LOG-AWS1`, `LOG-AWS2`, `LOG-AZU`, `LOG-GCP`, `LOG-OCI` rows and reference to `docs/refactor/LOGGING.md`.
   - Updated `docs/refactor/README.md`, `tests/README.md`, and `crc/cli/README.md` to reference `LOGGING.md`, `runlog`, `helpers_log_fix.py`, `test_log_fix_helpers.py`, and `test_cli_runlog.py`.

### Gates & test count

- `python3 -m ruff check .`: passed
- `python3 -m mypy`: passed (207 source files)
- `lint-imports`: passed (5 contracts kept, 0 broken)
- `python3 -m pytest -q`: 42258 passed (42213 before at `5f6ddcf`, 42256 after coder, 42258 after review additions)

VERDICT: APPROVE

