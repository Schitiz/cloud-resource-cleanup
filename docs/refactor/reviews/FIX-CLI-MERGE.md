# FIX-CLI-MERGE review

## Coding summary

Rung FIX-CLI-MERGE (wave FIX-1): merge `origin/fix/cli-route` (FIX-CLI-ROUTE: BUG-009, BUG-084, BUG-344) into `fix/cli-merged` (FIX-CLI-ALL: BUG-017, BUG-018) so both sets of fixes hold with one rule set.

- **Bugs fixed (all five, plus BUG-344).** BUG-017, BUG-018, BUG-009 (routing part), BUG-084 (routing part), BUG-344. Bugs left: none new. The parts of BUG-009 / BUG-084 that FIX-CLI-ROUTE left open (hard-coded `age_days=90`, no Slack/Influx for `snapshot`) stay open, see `docs/refactor/reviews/FIX-CLI-ROUTE.md` "Owner decision".
- **Conflicts and resolution.**
  - `crc/cli/dispatch.py` (semantic conflict, git merged it without markers): ROUTE's `check_aws_only_resources` + `_skip_non_aws` and ALL's `validate_targets` were two mechanisms for the same job. I removed the first pair and expressed the AWS-only resources through ALL's pair table: `SUPPORTED_CLOUDS["snapshot"] = SUPPORTED_CLOUDS["vpc"] = ("aws",)`. The error text for them is ROUTE's (`--resource <r> is AWS-only; use --cloud aws (got --cloud <c>)`), via `_unsupported_message`. The `_vpc` and `_snapshot` handlers lost their skip call.
  - `crc/cli/main.py` (auto-merged, edited): the early check before `set_max_age` now calls `validate_targets(targets)` (only when `--scan_tag` is not set, so the read-only scan of `--cloud azure --resource snapshot --scan_tag k=v` still works); `run_dispatch` still calls it too for direct callers. One rule, one place.
  - `crc/cli/README.md`: both Safety Invariant texts merged into one "One pair rule" invariant; Public API list updated (`check_aws_only_resources` removed).
  - `tests/test_cli_main_parity.py`: both bug tables kept. `diverges()`/`expected_fixed()` (ROUTE, BUG-009/084/344) are checked first, then `diverging_outcome()` (ALL, BUG-017/018), then plain oracle equality. Both "diverging cases exist" tests are kept.
  - `tests/test_core_selection.py`: kept ALL's `run_main_after_fix` and added `snapshot` and `vpc` (`("aws",)`) to its `SUPPORTED_ON` table. ROUTE's separate `aws_only_bug` / `assert_aws_only_fix` helpers became redundant and were dropped.
- **Interacting cases (tests adapted, each marked).**
  1. `--cloud all --resource snapshot|vpc`: ALL's rule skips the unsupported clouds without building their `CRC` and logs `<r> is not supported on <cloud>; skipped under --cloud all` with `SKIPPED reason=unsupported_cloud_resource`. ROUTE's text `--resource <r> is AWS-only; ...` and reason `aws_only_resource` are gone. Adapted: `fixed_all` in `tests/test_cli_main_parity.py` (no `CRC` event for azure/gcp/oci, new warning text), `tests/test_cli_route_fix.py` (two assertions on the warning text and the skip reason).
  2. `MAX_AGE` timing: ROUTE failed before `set_max_age`, ALL after it. Now every up-front pair error (BUG-017, BUG-018, BUG-009, BUG-084) comes before `set_max_age`, so `MAX_AGE` is untouched and nothing is printed. Adapted: `without_reset` in `tests/test_cli_main_parity.py` (ALL's expected outcome). This only stops earlier and leaves less state behind.
  3. `tests/test_core_selection.py`: the AWS-only pairs are now covered by ALL's helper (same outcome: ValueError for one cloud, AWS only plus skip warnings for `all`). ROUTE's extra check that `build_selection`'s AWS item equals what ran was dropped with its helper.
  4. Blank `--scan_tag` beats an unsupported pair (BUG-344 is checked first in `main()` and in `diverges()`).
- **Files changed.** `crc/cli/dispatch.py`, `crc/cli/main.py`, `crc/cli/README.md`, `tests/test_cli_main_parity.py`, `tests/test_core_selection.py`, `tests/test_cli_route_fix.py`, new `tests/test_cli_merge_fix.py` (13 tests: shared table, every unsupported single-cloud pair fails before state changes, `--cloud all` disk and nic, AWS-only under `all`, blank tag precedence, scan path, production commands), this file. Nothing under `tests/legacy/`, `tests/archtest/`, locked tests, PLAN/STATUS/BUGS or `CLEANUP_SAFETY.md` was touched.
- **Tests (`pytest -q`).** 42479 at 2bf120a (FIX-CLI-ALL tip), 42513 after (+34: the ROUTE tests plus the 13 new ones in `tests/test_cli_merge_fix.py`; no test of either rung was removed except the two `tests/test_core_selection.py` helpers noted above). `make check` (ruff, mypy, lint-imports, pytest) green.
- **Production commands.** `crc.py --cloud aws --resource vm --scan_tag autoclean=false --dry_run` and `crc.py --cloud aws --resource snapshot --age '{"days": 90}' ...` run with the same calls, output and exit code (`tests/test_cli_merge_fix.py`, `tests/test_cli_route_fix.py`, unmarked parity cases). No Jenkins command uses `--cloud all` or an unsupported pair.
- **Owner actions.** None for locked tests. Optional `CLEANUP_SAFETY.md` text: see "Owner action".

## Owner action

Optional, `CLEANUP_SAFETY.md` (CLI invariants): "Before any cleaner runs, `dispatch.validate_targets` checks every (cloud, resource) pair. An unsupported pair (`keypair`, `kms` off AWS; `nic` off Azure; `ip` on OCI; `snapshot`, `vpc` off AWS) of an explicit cloud raises `ValueError`; under `--cloud all` it is skipped with a warning only when no supported pair follows it, otherwise it raises. `--cloud all --resource disk|all` raises. An empty or blank `--scan_tag` raises `ValueError`."

## New bugs

- `crc/core/selection.py` `build_selection` still models `main` (lists unsupported pairs as selected). Exists on main: yes. Not fixed (outside this rung); `tests/test_core_selection.py` pins the difference.
