## Coding summary

Status: PARTIAL (green, time limit). Step (1) is done and `dispatch.HANDLERS` is gone from production
code; steps (2) and (3) are only started.

### Done
- Step (1): the two warn-only pairs are skip-only routes: AWS `spot_instances`
  (`skips.aws_spot_instances`) and `spot_instance_requests` on Azure, GCP and OCI
  (`skips.non_aws_spot_instance_requests`), both with `options=skips.no_options` and no registered
  cleaner. The warnings, the RUN START / RESULT lines and the lack of Slack/Influx are the legacy
  ones (`Route.skip` runs after RUN START and builds nothing). Every (cloud, kind) pair is now in a
  route table; `dispatch.HANDLERS`, the six handlers and `Handler` are deleted; `_run_handler` is
  now `_run_pair` and only calls `bridge.run_routed`.
- `tests/test_cli_bridge_parity.py::test_every_routed_pair_has_a_registered_cleaner` exempts
  skip-only routes (`route.options is skips.no_options`, which must carry a `skip`), and stays
  strict for the rest. Route-table assertions in the azu, gcp and parity bridge tests list the
  new routes; `test_cli_main_parity.install_routed_fakes` registers no fake cleaner for them
  (the oracle `FakeCRC` still gets the same flags for every other pair).
- The legacy side of `test_cli_bridge_azu.py`, `test_cli_bridge_gcp.py` (via
  `tests/helpers_gcp_bridge.py`) and `test_cli_bridge_oci.py` no longer needs the production
  handlers.

### Left (not done)
- Step (2): the legacy side of those bridge tests (and `test_cli_bridge_aws.py`,
  `test_cli_crc_parity.py` legacy side, `test_cli_bridge_parity.py`) still runs the current `CRC`
  methods. For the three bridge files above the old handler table lives on in
  `tests/helpers_legacy_handlers.py` (a copy of the deleted handlers, tests only), so they compare
  the routed path with the current legacy CRC as before. Retargeting them to
  `tests/helpers_oracle.load_legacy_crc()` needs care: `tests/legacy/*.txt` emit no run-log lines
  (RUN START, ACTION, REGION, RESULT), so the log-line comparison of those tests can only be
  asserted against the routed side, and every BUG-NNN divergence between the oracle adapters and
  the current ones has to be asserted explicitly.
- Step (3): nothing else deleted. `crc/cli/notify.py`, `adapter_args.py`, `report_calls.py`,
  `vm_ops.py`, `resource_ops.py` and the `crc.py` re-exports are still used by the retained legacy
  side of the tests (`CRC` is also the object `bridge` reads `slack_client`, `get_msg`, ... from,
  and `scan.py` uses `scan_instances_with_tag`). Delete them after the tests above are retargeted.
- Cleaner-based copies of the five locked tests: `test_aws_disk_engine.py`,
  `test_aws_spot_instance_requests_engine.py`, `test_azu_spot_vm_engine.py`,
  `test_gcp_spot_vm_engine.py` already exist; the OCI copy was not checked.

### Numbers
- `crc/` lines (all `*.py`): 19346 before, 19280 after (-66 net: `dispatch.py` handlers minus the new skips).
- Test count: 44364 before this lane (ENG-CLEAN floor 44373); `make check` runs 44399 after.

### Owner actions
- None. No
  hash-locked test and no `tests/legacy/*.txt` was edited.

## New bugs
- None found.

## Round 1 (Argon)

Scope reviewed: `git diff d4f9b66..HEAD` on branch `eng/clean1` (lane `CLEAN-1`).

### Findings & fixes made in review

1. **Removed vacuous legacy patches in `tests/test_cli_dispatch_fix.py` and retargeted additional test files to `load_legacy_crc()`**:
   - `tests/test_cli_dispatch_fix.py` still imported `crc.cli.resource_ops` and had dead `FakeAdapter` and `FakeNIC` patches on `resource_ops` in `test_bug_017_cloud_all_real_crc_does_not_build_skipped_clouds` (`adapter_attr` was always `None`) and `test_bug_017_cloud_all_nic_real_crc_deletes_nothing` (unreached because `nic` is routed through `FakeCleaners`). Removed `resource_ops`, `FakeAdapter`, and `FakeNIC`, and asserted `cleaners.runs` directly.
   - Retargeted `tests/test_core_engine.py` (`crc_cli` fixture and `test_notifier_order_and_influx_fail_open_match_crc_py`) and `tests/test_core_report.py` (`crc_cli` fixture and `test_spot_vm_notification_and_disk_message`) from loading `crc.py` and patching `crc.cli.resource_ops` / `crc.cli.vm_ops` to `tests.helpers_oracle.load_legacy_crc()`.
   - Retargeted the `oracle` loaders in `tests/test_cli_args_parity.py`, `tests/test_cli_crc_parity.py`, `tests/test_cli_bridge_parity.py`, `tests/test_cli_bridge_aws.py`, `tests/test_cli_bridge_oci.py`, and `tests/test_cli_main_parity.py` (`ORACLE_MODULE` and `RUN_ORACLE`) to `load_legacy_crc()`, and deleted the unused `provide_legacy_keypairs()` helper from `tests/helpers_cli_routes.py`.
   - Added the missing `("gcp", "spot_instance_requests")` warn-only skip case to `tests/test_cli_route_skip.py::test_pairs_a_cloud_does_not_have_warn_and_run_nothing`.
   - Updated stale docstrings and README descriptions in `crc/cli/bridge.py::route_for`, `crc/cli/routes/__init__.py`, and `crc/cli/README.md` that still described falling back to a legacy handler in `dispatch.py`.
2. **Blocking — Incomplete task scope (steps (2) and (3) partially remaining)**:
   - **Step (1) complete**: `dispatch.HANDLERS`, `Handler`, and all 6 handlers in `crc/cli/dispatch.py` are deleted; AWS `spot_instances` and non-AWS `spot_instance_requests` are skip-only routes (`skips.no_options`, `skips.aws_spot_instances`, `skips.non_aws_spot_instance_requests`), and `test_cli_bridge_parity.py::test_every_routed_pair_has_a_registered_cleaner` exempts `skips.no_options` routes while requiring `route.skip is not None`.
   - **Step (2) remaining**: `tests/test_cli_bridge_azu.py`, `tests/test_cli_bridge_gcp.py` (via `tests/helpers_gcp_bridge.py` and `tests/helpers_legacy_handlers.py`), `tests/test_cli_bridge_oci.py` (which patches `oracle_module.OCI_*` with current `Disk`/`VM`/`SpotVM` adapters), `tests/test_cli_crc_parity.py` (its `NewCRC` side), and `tests/test_notify_parity.py` (its `current` fixture) still exercise `crc.cli.runner.CRC` (`resource_ops.py`, `vm_ops.py`, `notify.py`, `adapter_args.py`, `report_calls.py`).
   - **Step (3) remaining**: `crc/cli/notify.py`, `crc/cli/adapter_args.py`, `crc/cli/report_calls.py`, `crc/cli/resource_ops.py`, the non-scan methods in `crc/cli/vm_ops.py`, and the unused adapter re-exports in `crc.py` are still retained for the tests above. `crc/` Python line count is 19,346 before (`d4f9b66`) and 19,279 after (`-67` lines).

### Checklist verification

1. **CLI result parity for every routed pair**: All pairs in `bridge.TABLES` (including the 4 skip-only spot routes: AWS `spot_instances`, and Azure, GCP, OCI `spot_instance_requests`) match legacy behaviour: same `RUN START` / `RESULT` lines, same logger (`crc.cli.dispatch`) and warning messages, no Slack/Influx messages, no cleaner built or called, and dry run never mutates.
2. **Parity tests non-vacuous**: With `test_cli_dispatch_fix.py` cleaned up, all CLI and module parity tests reach real or recording fake cleaners and assert the oracle facts.
3. **Hash-locked safety tests & engine copies**: All 5 hash-locked test files (`tests/test_aws_disk.py`, `tests/test_aws_spot_instance_requests.py`, `tests/test_azu_spot_vm.py`, `tests/test_gcp_spot_vm.py`, `tests/test_oci_spot_vm.py`) and `tests/archtest/safety_lock.json` are untouched and passing. All 5 engine copies (`tests/test_aws_disk_engine.py`, `tests/test_aws_spot_instance_requests_engine.py`, `tests/test_azu_spot_vm_engine.py`, `tests/test_gcp_spot_vm_engine.py`, `tests/test_oci_spot_vm_engine.py`) exist and pass, covering all locked SAF cases.
4. **Protected files**: No oracle (`tests/legacy/*.txt`), archtest (`tests/archtest/*.py`, `safety_lock.json`, `frozen_inputs.json`), guardrail (`AGENTS.md`, `ARCHITECTURE.md`, `.cursor/**`, `pyproject.toml`, `Makefile`), or `requirements*.txt` file was edited; `tests/archtest/test_count_floor.txt` raised to `44400` via `make raise-test-floor`.
5. **Limits & README sync**: All touched source files are well under 250 lines and functions under 60 lines (`ARCH-004`); `crc/cli/README.md` and `crc/cli/routes/README.md` are in sync (`ARCH-002`).

### Gates & test count

- `python3 -m ruff check .`: passed
- `python3 -m mypy`: passed (364 source files)
- `lint-imports`: passed (5 contracts kept, 0 broken)
- `python3 -m pytest -q -n auto`: **44400 passed in 55.01s** (`make check` total ~62s)
- `python3 -m tests.archtest.test_count check`: `ARCH-008: 44400 tests, floor 44400`

VERDICT: CHANGES_REQUESTED
