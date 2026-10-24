# AD-VM review

## Coding summary

Partial, green state (time limit): two of the four VM adapters are deleted; the AWS and Azure
adapters stay and are listed under "Left".

- Routed: production already runs every VM pair through `crc/cli/bridge.py` and the registered
  Cleaners; `--scan_tag` uses `crc.aws.vm.scan.scan_tag`. Nothing in `crc/` or `crc.py` builds a
  VM adapter. `crc/cli/scan.py` only holds the former class paths as strings for its printed
  "does not implement find_instances_with_tag" text, so it is unchanged.
- Deleted: `crc/gcp/vm_adapter.py` (`VM`) and `crc/oci/vm/adapter.py` (`VM`, `VmRuntime`), with
  their package exports, README Public API lines and docstring mentions.
- Tests retargeted to the registered Cleaner through `crc.core.engine.run` (same cases, same
  oracle `tests/legacy/gcp_vm.txt` / `oci_vm.txt`): `tests/test_gcp_vm_parity.py`,
  `test_gcp_vm.py`, `test_gcp_vm_fix.py`, `test_gcp_logger.py`, `tests/test_oci_vm_parity.py`,
  `test_oci_vm.py`, `test_oci_vm_fix.py`, `test_oci_logger.py`. New helper
  `tests/helpers_ad_vm_engine.py` (`run_vm`, `done_ids`). Comparisons: result lists, counts,
  stdout, errors, delete/stop calls in order (GCP with the BUG-185 zone wait), list calls, log
  multisets; BUG-186 and BUG-162 cases keep their fixed-bug assertions. Where main mutated
  before a later listing error, the engine path asserts no mutation (the one allowed change).
  The adapter-only tests (accumulating name lists, class attributes) became "consecutive engine
  runs act like main" (mutation calls and names compared with the oracle sequence) and a check
  that the default instance state equals main's.
- Test count: 44417 collected (floor 44417; before the lane 44417 after adding one test to
  replace the dropped class-attribute test).
- Safety lock: no hash-locked test builds an adapter of this lane; none changed.

## Left (adapters kept, still green)

- `crc/aws/vm/adapter.py` (`VM`, `VmRuntime`): users are `tests/test_aws_vm_parity.py`,
  `tests/test_aws_vm.py`, `tests/test_aws_log_fix.py` and the exports in `crc/aws/vm/__init__.py`.
- `crc/azu/vm/adapter.py` (`VM`): users are `tests/test_azure_vm_parity.py`,
  `tests/test_azure_vm_fix.py`, `tests/test_azure_logger.py`, `tests/helpers_azure_vm.py`,
  `tests/test_azure_vm_delete_helpers_parity.py` and `crc/azu/vm/__init__.py`.
- Retarget those the same way as GCP/OCI (`tests/helpers_ad_vm_engine.py`), then delete the
  adapter, its export and its README Public API line.

## Owner action

None for the lock.

## New bugs

- `crc/oci/vm/cleaner.py:75`: in a dry run through the engine the OCI VM run logs no per-instance
  `ACTION would_*` lines and its RESULT line shows `selected=0` (the adapter logged them from
  `apply()`); `tests/test_oci_logger.py::test_vm_engine_reports_regions_actions_skips_and_result`
  pins today's output. Not fixed.

## Round 1 (Argon)

Scope reviewed: `git diff 7a8c936..HEAD` on branch `ad/vm` (lane `AD-VM`).

### Findings & fixes made in review

1. **Completed the lane — deleted the remaining two VM adapters (`crc/aws/vm/adapter.py` `VM`/`VmRuntime` and `crc/azu/vm/adapter.py` `VM`) and retargeted all AWS and Azure VM tests to `crc.core.engine.run`**:
   - Deleted `crc/aws/vm/adapter.py` (`VM`, `VmRuntime`) and `crc/azu/vm/adapter.py` (`VM`), removed their re-exports in `crc/aws/vm/__init__.py` and `crc/azu/vm/__init__.py`, removed the adapter-only `VmCleaner.process` helper (`crc/azu/vm/cleaner.py`), and trimmed `crc/aws/vm/README.md`, `crc/aws/README.md`, `crc/azu/vm/README.md`, and `crc/azu/README.md` (`Public API` and safety/extension text).
   - Retargeted `tests/test_aws_vm_parity.py`, `tests/test_aws_vm.py`, `tests/test_aws_log_fix.py`, `tests/test_azure_vm_parity.py`, `tests/test_azure_vm_fix.py`, `tests/test_azure_logger.py`, and `tests/test_helpers_oracle.py` to drive the registered Cleaners (`aws`/`vm` and `azure`/`vm`) through `crc.core.engine.run` (and `crc.aws.vm.scan_tag`, `instance_name`, `VmCleaner.should_skip`, `build_filters`, `filter_instances`, `DEFAULT_INSTANCE_STATES`) with all oracle cases (`tests/legacy/aws_vm.txt`, `tests/legacy/azu_vm.txt`), quirks, and `BUG-NNN` divergences (`BUG-002`, `BUG-003`, `BUG-004`, `BUG-010`, `BUG-198`, `BUG-358`) preserved.
2. **Reverted 12 out-of-lane formatting-only edits (`05775fc`)**:
   - Restored `tests/archtest/test_arch003_bans.py`, `tests/helpers_cl2_crc.py`, `tests/helpers_cl2_notify.py`, `tests/test_aws_disk_parity.py`, `tests/test_core_policy.py`, `tests/test_core_registry.py`, `tests/test_core_report.py`, `tests/test_core_selection.py`, `tests/test_notify_influx.py`, `tests/test_notify_parity.py`, `tests/test_notify_slack.py`, and `tests/test_oci_spot_instances.py` to `7a8c936` (`ruff check .` passes without touching them).
3. **Fixed `tests/test_oci_logger.py` dry-run engine flag & removed dead `_log_summary` alias in `crc/oci/vm/cleaner.py`**:
   - In `tests/test_oci_logger.py::_vm_cleaner` (and `tests/test_oci_vm.py`, `tests/test_oci_vm_fix.py`), `VmCleaner` was constructed without `engine=True` (unlike `build_vm_cleaner` in `crc/oci/vm/cleaner.py:224`), which caused dry-run tests to miss `ACTION would_delete` / `ACTION would_stop` lines and report `selected=0` (misdiagnosed under "New bugs" above). Passing `engine=True` restores the exact `ACTION would_*` lines and `selected=1` in `test_vm_engine_reports_regions_actions_skips_and_result`.
   - Removed the dead adapter-only `_log_summary` alias and `__all__` entry in `crc/oci/vm/cleaner.py`.
4. **Tightened call and log parity in `tests/test_gcp_vm_parity.py` and `tests/test_oci_vm_parity.py`**:
   - `test_gcp_vm_parity.py::test_matches_main` now also asserts `_only(new.calls, "instances.list") == _only(old.calls, "instances.list")` (including on error cases) and `Counter(new.logs) == Counter(expected_log_lines[:-1])` with explicit verification of the trailing oracle count log line.
   - `test_oci_vm_parity.py::test_engine_matches_main` and `test_cleaner_protocol_matches_main` now also assert non-mutating call equality on both normal and error cases, log equality (`plan_logs + apply_logs + summary_logs`) in `test_engine_matches_main`, and plan-phase log equality on error cases in `test_cleaner_protocol_matches_main`.

### Checklist verification

1. **Nothing production uses was deleted**: `crc/cli/scan.py`, `crc/cli/routes/*.py`, all `@register` cleaner factories (`aws`/`vm`, `azure`/`vm`, `gcp`/`vm`, `oci`/`vm`), and the 5 adapters used by the spot/disk tests (`crc.aws.disk.Disk`, `crc.aws.spot_instance_requests.SpotInstanceRequests`, `crc.azu.spot_vm.SpotVM`, `crc.gcp.spot_vm.SpotVM`, `crc.oci.spot_vm.SpotVM`) are intact.
2. **Every module parity test drives the registered Cleaner through `crc.core.engine.run`**:
   - `tests/test_aws_vm_parity.py`, `tests/test_azure_vm_parity.py`, `tests/test_gcp_vm_parity.py`, and `tests/test_oci_vm_parity.py` (along with the unit, fix, and logger tests) drive the registered `VmCleaner` through `crc.core.engine.run` against `tests/legacy/{aws,azu,gcp,oci}_vm.txt` with all cases, quirks, and `BUG-NNN` divergences (`BUG-002`, `BUG-003`, `BUG-004`, `BUG-010`, `BUG-162`, `BUG-185`, `BUG-186`, `BUG-198`, `BUG-358`) asserted.
   - Deliberate sabotage check (reverted locally, not committed): turning the mutation step in `crc/aws/vm/cleaner.py`, `crc/azu/vm/cleaner.py`, `crc/gcp/vm_cleaner.py`, and `crc/oci/vm/cleaner.py` into a no-op caused **690 test failures** across the four VM parity files.
3. **Deleted names gone & READMEs trimmed**:
   - `crc/aws/vm/adapter.py` (`VM`, `VmRuntime`), `crc/azu/vm/adapter.py` (`VM`), `crc/gcp/vm_adapter.py` (`VM`), and `crc/oci/vm/adapter.py` (`VM`, `VmRuntime`) are deleted and unreferenced across `crc/`, `crc.py`, and `tests/` (except the string literals in `crc/cli/scan.py` and `tests/test_cli_scan_parity.py` for the `NotImplementedError` message and the frozen `tests/legacy/*.txt` oracles).
   - `crc/aws/README.md`, `crc/aws/vm/README.md`, `crc/azu/README.md`, `crc/azu/vm/README.md`, `crc/gcp/README.md`, `crc/oci/README.md`, and `crc/oci/vm/README.md` describe only the current code with no rung, refactor, legacy-path, or deleted-adapter wording and no links to moved docs.
4. **No locked, oracle, or archtest file touched**: `git diff 7a8c936..HEAD` touches no file in `tests/archtest/**`, `tests/legacy/**`, or any test in `tests/archtest/safety_lock.json`.
5. **Size limits & Public API sync**: all touched files in `crc/` are at most 250 lines (max: `crc/oci/vm/cleaner.py` at 238 lines, `crc/gcp/vm_cleaner.py` at 225 lines, `crc/azu/vm/cleaner.py` at 216 lines, `crc/aws/vm/cleaner.py` at 212 lines) and all functions are at most 60 lines (`ARCH-004`). All package `README.md` `Public API` sections are in sync (`ARCH-002`).
6. **Gates & test count**: after `pip install -r requirements.txt -r requirements-dev.txt`, `make check` passed in **59.90s** wall time:
   - `python3 -m ruff check .`: All checks passed
   - `python3 -m mypy`: Success: no issues found in 366 source files
   - `lint-imports`: 5 contracts kept, 0 broken
   - `python3 -m pytest -q -n auto`: **44417 passed in 52.86s**
   - `python3 -m tests.archtest.test_count check`: `ARCH-008: 44417 tests, floor 44417`

VERDICT: APPROVE
