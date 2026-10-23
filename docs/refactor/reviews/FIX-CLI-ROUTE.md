# FIX-CLI-ROUTE review

## Coding summary

Rung FIX-CLI-ROUTE (wave FIX-1): behaviour fix for `BUG-009`, `BUG-084` and `BUG-344` in `crc/cli/`.

- **Bugs fixed.**
  - `BUG-009` and `BUG-084` (`snapshot` and `vpc` ran the AWS class for every cloud). They are AWS-only now. `--cloud aws` is unchanged. Any other single cloud raises `ValueError("--resource <r> is AWS-only; use --cloud aws (got --cloud <c>)")` from `dispatch.check_aws_only_resources`, which `main()` calls after the clients are built and before `MAX_AGE` is set, so no `CRC`, `Snapshot` or `VPC` object exists yet and the environment is untouched. `--cloud all` runs them once, in the `aws` pass; each other cloud pass logs `WARNING --resource <r> is AWS-only; other clouds are not supported, skipped for <cloud>` and counts `SKIPPED reason=aws_only_resource` in its run log. The `Snapshot` handler also calls the check itself, so a direct `run_dispatch` caller cannot reach AWS from another single cloud.
  - `BUG-344` (an empty `--scan_tag ''` skipped the read-only scan and ran the destructive path). `inputs.check_scan_tag` raises `ValueError("--scan_tag must not be empty; use KEY=VALUE format, e.g. auto_clean=false")` for an empty or whitespace-only value, after the clients are built and before `MAX_AGE` is set. A blank tag used to raise "must be in KEY=VALUE format" from `run_scan` after `MAX_AGE` was set (whitespace) or run the destructive path (empty); both now fail before any cleaner. An absent `--scan_tag` and a non-blank one are unchanged.
- **Scan path.** The AWS-only check is skipped when `--scan_tag` is set, so the read-only scan of `--cloud azure --resource snapshot --scan_tag k=v` still works as on `main` (it never reaches a cleaner).
- **Production commands.** `--cloud aws --resource snapshot --age ... --exception_tags ...` and `--cloud aws --resource vm --scan_tag autoclean=false --dry_run` give the same calls, prints and exit code as before (`tests/test_cli_route_fix.py`, and every unmarked parity case).
- **Bugs left.** None of the three.
- **Files changed.** `crc/cli/dispatch.py`, `crc/cli/inputs.py`, `crc/cli/main.py`, `crc/cli/README.md`, `tests/test_cli_main_parity.py`, new `tests/test_cli_route_fix.py`, `tests/test_core_selection.py` (see below), this file.
- **Parity test.** `tests/test_cli_main_parity.py`: `diverges()` marks a case with `BUG-009`, `BUG-084` or `BUG-344` only when the oracle run reached the buggy path; `expected_fixed()` derives the exact new events, stdout, stderr, result, `MAX_AGE` and added warnings from the oracle outcome, and the test also asserts the new outcome differs from the oracle. Every other case still asserts full equality. `test_every_fixed_bug_has_diverging_cases` proves all three IDs are exercised. The oracle `tests/legacy/crc_main.txt` is untouched.
- **`tests/test_core_selection.py`.** It compares `crc.core.selection.build_selection` with `main()`. `build_selection` (outside this rung) still lists `snapshot` and `vpc` for every cloud, so those pairs (`BUG-009`, `BUG-084`) now assert the fixed `main()` outcome (ValueError for one non-AWS cloud; AWS only plus the warnings for `all`) while still asserting `build_selection` unchanged. No other case or expected value changed. See "New bugs" for the follow-up.
- **Tests.** Before: 42444 collected (`pytest --collect-only` at 182466d). After: 42468 (+24: 23 in `tests/test_cli_route_fix.py`, 1 `test_every_fixed_bug_has_diverging_cases`). `make check` (ruff, mypy, lint-imports, pytest) green.
- **Owner actions.** None for hash-locked tests (none touched). `CLEANUP_SAFETY.md` is not changed by this fix (see the proposal below, optional).

## Owner action

Optional, `CLEANUP_SAFETY.md`: no destructive invariant is removed. If the owner wants the new rule recorded, add under the CLI invariants: "`snapshot` and `vpc` are AWS-only. `main()` raises `ValueError` for any single non-AWS cloud before a cleaner is built, and under `--cloud all` runs them in the AWS pass only. An empty or blank `--scan_tag` raises `ValueError` before any cleaner runs."

## Owner decision

None. No production command changes: Jenkins uses `--cloud aws --resource snapshot` and `--cloud aws --resource vm --scan_tag autoclean=false --dry_run`.

## New bugs

- `crc/core/selection.py` (`build_selection`, `RESOURCES` use): still selects `snapshot` for every cloud and `vpc` for every cloud, which no longer matches `main()` after this fix. Exists on main: yes (same shape as `BUG-009` / `BUG-084`). Not fixed here (outside the rung); `tests/test_core_selection.py` pins the difference for the two bugs.
- `crc/cli/main.py:52` (`if options.scan_tag:`): a non-string `--scan_tag` cannot happen (argparse gives `str`), so only the blank-string case is guarded; `check_scan_tag` uses `str(scan_tag).strip()` to be safe. No bug.
- `crc/cli/dispatch.py` `_snapshot`: under `--cloud all` the snapshot pass still prints the message with the AWS `CRC` and sends no Slack or Influx notification (`BUG-040` shape, unchanged). Exists on main: yes.
