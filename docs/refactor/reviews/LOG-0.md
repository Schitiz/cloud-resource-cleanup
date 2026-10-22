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
