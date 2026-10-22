## Coding summary

Rung LOG-AWS2 (AWS KMS, snapshot, keypairs, Elastic IPs, VPC). Log text and levels only: no
selection, deletion, SDK call or order, Slack, Influx, flag or exit code changed.

Files changed:

- `crc/aws/_regionlog.py` (new, private): `start`, `region_done`, `region_skipped`, thin wrappers
  over `crc.core.runlog.current()` with an injectable `clock` for `seconds=`.
- `crc/aws/kms.py`: `KEY SKIPPED <id>` WARNING -> DEBUG, same text (BUG-357); the bare `except
  BaseException` is unchanged, it only counts `skip("unreadable")`, or `skip("not_ours")` when the
  key policy has no `Principal.AWS` (a private `_NotOursError` replaces the `KeyError`/`TypeError`
  of that one lookup; the key is still skipped and a key found earlier stays selected). Also
  `skip("exception_tag")`, `region()`, `action("would_delete"/"deleted")`, `fail()` on a scheduling
  error (the error still propagates), `region_skipped()`.
- `crc/aws/snapshot.py`: `Skipping snapshot X, used by AMI` INFO -> DEBUG and `skip("used_by_ami")`
  (BUG-359); `Snap X has tag K` INFO -> DEBUG (per-resource skip line, contract rule 1);
  `skip("too_young" / "exception_tag")`; `delete_one` (new keyword `region`) reports
  `would_delete` / `deleted` / `fail`; `REGION` per region; `region_skipped`.
- `crc/aws/keypairs.py`: `not old enough` and `in exception_regex` INFO -> DEBUG; skips
  `too_young`, `exception_regex`, `name_regex_mismatch`; `REGION` in `plan_region`;
  `ACTION`/`fail` in `apply_region` (errors still propagate); `region_skipped`.
- `crc/aws/elastic_ips.py`: skips `exception_tag`, `no_filter_match`; `REGION` in `plan_region`;
  `ACTION`/`fail` in `apply_region`; `region_skipped`.
- `crc/aws/vpc/cleaner.py`, `crc/aws/vpc/teardown.py` (new): the teardown helpers moved out of
  `cleaner.py` unchanged (ARCH-004, 400 lines) as `tear_down`; `delete_vpc(..., region=None)`;
  `ACTION deleted` after `delete_vpc` succeeds, `fail()` when the five retries fail (the error lines
  stay) or a teardown step raises (still propagates), `would_delete` in a dry run, `skip("protected")`,
  `REGION`, `region_skipped`.
- READMEs of `crc/aws` and `crc/aws/vpc` (Public API, invariants).
- Tests: `tests/helpers_log_fix.py` (rules BUG-357, BUG-359; BUG-356 also covers the two keypair
  skip lines), `tests/test_aws_{kms,snapshot,keypair}_parity.py` (log comparisons go through
  `expected_logs`, plus explicit oracle != new cases), `tests/test_aws_misc_runlog.py` (new: exact
  `REGION/ACTION/SKIPPED/ERRORS/FAILED/RESULT` lines per cleaner for dry run, real run, failure,
  skipped region, unattached run). `test_aws_elastic_ips`/`vpc` parity needed no change (their
  oracle logs are unchanged).

Bug IDs handled: BUG-357 (fixed), BUG-359 (fixed), BUG-361 and BUG-362 for these five modules
(REGION lines, `region_skipped`, `fail`). The rows are shared with other lanes, so their status in
`BUGS.md` is left to the integrator.

Test count: 42256 before (LOG-0 at 7437ac5), 42284 after (full run: 42283 passed plus the ARCH-002 test fixed afterwards). `make check` steps (ruff, mypy, lint-imports, pytest) green on
Python 3.12.3.

Left / notes:

- `crc/aws/_base.py` and `connectivity.py` are untouched: `get_all_regions` is global (not per
  region) and `log_skipped_region` is shared with the AWS1 lane, so the skipped-region count is
  taken in each module's own `_skip_region` wrapper (no double counting if AWS1 does the same
  in its modules).
- Order inside a region: legacy paths that delete as they go print `ACTION` lines before `REGION`
  (snapshot, VPC); `plan_region` of keypairs and Elastic IPs prints `REGION` before the deletions.
- `Snap X has tag K` (snapshot) and the two keypair skip lines are not in the contract's explicit
  list; moved to DEBUG as per-resource "skipping X because Y" lines (rule 1). Revert the three
  `logging.debug` calls if the owner wants them at INFO.
- `ruff format` is not enforced on the repo (19 files already differ at 7437ac5); not run on the tree.
- No locked safety test asserts these log levels; none was touched.
- New bugs found: none beyond BUG-012/015/056 already recorded (VPC lists protected VPCs as selected
  in plan; `ACTION` lines only count VPCs actually deleted or, in a dry run, listed).

## Round 1 (Argon)

Scope reviewed: `git diff 7437ac5..HEAD` (commits `87ba285`, `aac2d93`).

Findings:

- None (0 blocking, 0 nit).
- Verified (1) behaviour and safety: only log levels and `crc.core.runlog` / `crc.aws._regionlog` calls changed across `crc/aws/{kms,snapshot,keypairs,elastic_ips}.py` and `crc/aws/vpc/{cleaner,teardown}.py`. Selection, deletion, SDK call order, Slack messages, InfluxDB points, CLI flags and exit codes are unchanged. In `kms.py`, the bare `except BaseException` behaviour is preserved (`KEY SKIPPED <id>` moved from `WARNING` to `DEBUG` with identical text, and `skip("not_ours")` vs `skip("unreadable")` distinguished via private `_NotOursError` on missing `Principal.AWS`). In `snapshot.py`, `Skipping snapshot <id>, used by AMI` and `Snap <id> has tag <key>` moved from `INFO` to `DEBUG` with `skip("used_by_ami")` / `skip("exception_tag")` / `skip("too_young")`. In `keypairs.py`, per-keypair skip lines moved from `INFO` to `DEBUG`. `crc/aws/_base.py`, `crc/aws/connectivity.py`, `crc/core`, `crc/cli`, other cloud packages, and `docs/refactor/{BUGS,STATUS,PLAN}.md` are untouched.
- Verified (2) contract line formats: `REGION`, `ACTION` (`would_delete` / `deleted`), `SKIPPED`, `ERRORS`, `FAILED` and `RESULT` lines match `docs/refactor/LOGGING.md` key names, order and log levels across dry runs, real runs, failures and skipped regions (`tests/test_aws_misc_runlog.py`).
- Verified (3) parity tests and oracles: `tests/legacy/*.txt` are untouched; `tests/helpers_log_fix.py` adds `BUG-357` and `BUG-359` rules (and extends `BUG-356` for the two per-keypair skip lines) that rewrite log levels only without dropping or altering message text; parity tests assert `new.logs == expected_logs(old.logs, LOG_BUGS)`, `old.logs != new.logs` on diverging cases, and exact equality on all non-log fields.
- Verified (4) locked safety tests: `tests/archtest/safety_lock.json` and all locked safety test files are untouched.
- Verified (5) documentation and architecture guardrails: `crc/aws/README.md` and `crc/aws/vpc/README.md` document the new public symbols (`start`, `region_done`, `region_skipped` in `crc/aws/_regionlog.py`; `tear_down` in `crc/aws/vpc/teardown.py`), satisfying ARCH-001..005.

Gates (`pip install -r requirements.txt -r requirements-dev.txt && make check`):

- `ruff check`: passed
- `mypy`: passed (strict, 121 source files)
- `lint-imports`: passed (3 contracts kept, 0 broken)
- `pytest -q`: `42284 passed` (up from 42256 at `7437ac5`)

VERDICT: APPROVE

