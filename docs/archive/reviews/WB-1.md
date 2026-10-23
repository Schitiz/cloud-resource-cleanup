## Coding summary

Lane WB-1: the legacy CLI layer is deleted. Every (cloud, kind) pair already ran through
`crc/cli/bridge.py` and the route tables; nothing was left on a legacy path, so no kind was kept
unrouted and no partial state was needed.

**Deleted**
- `crc/cli/resource_ops.py`, `adapter_args.py`, `report_calls.py`, `vm_ops.py`, `notify.py` and
  `base.py` (`CRCBase` was only the base of the mixins; its constructor and attributes moved).
- `tests/helpers_legacy_handlers.py` (no test imported it).
- The re-exports of `crc.py` that nothing needs: it now exports `main`, `get_argparser` and the
  validators (`is_valid_*`, `are_values_of_dict_lists`, `validate_influxdb_inputs`,
  `_validate_influxdb_input`), which the tests and `python crc.py` use. The adapter classes,
  `CRC`, `Snapshot`, `WebClient`, `InfluxDBClient`, `Point`, the constants and `notify_cleanup`
  are no longer re-exported. No Jenkins command uses them (Jenkins runs `python crc.py <flags>`).

**Kept and moved**
- `crc/cli/runner.py`: `CRC` is now the run context the bridge reads: the constructor with the
  GCP `project_id` check, the attributes (`slack_client`, `slack_channel`, `influxdb_client`,
  `influxdb_bucket`, `resource_suffix` only with `influxdb_conn` (BUG-030), ...) and `get_msg`
  (the AWS `snapshot` console line). No `notify_*`, `write_influxdb`, `ping_on_slack` or
  operation method is left on it.
- `crc/cli/scan.py`: `scan_instances_with_tag(crc, tag_key, tag_value)` (was `CRC.scan_instances_with_tag`
  and `_get_vm`), same adapter selection, arguments, errors and messages. `_find_hits` looks it up
  in `scan` at call time.

**Routed, shimmed and deleted adapters**: routing unchanged (all pairs were routed). No adapter
class in `crc/<cloud>/**` was touched (the next wave deletes them per cloud); the hash-locked
safety tests and `tests/archtest/**` are untouched.

**How the CLI parity tests reach the cleaners**: unchanged for the routed pairs (the fake
cleaners of `tests/helpers_cli_routes.FakeCleaners` through `bridge.build_registry` and
`bridge.build_notifiers`). The fake `CRC` of the parity tests stays the context object. Only the
scan path moved: `test_cli_main_parity.py` (`run_new`), `test_cli_route_fix.py` and
`test_cli_logger.py` patch `crc.cli.scan.scan_instances_with_tag` (a call-time seam) with a
function that calls the fake `CRC.scan_instances_with_tag`, so the same events as the oracle
(`crc.scan_instances_with_tag` with the tag arguments) are recorded and asserted.
`test_cli_scan_parity.py` drives `crc.cli.scan.scan_instances_with_tag(context, key, value)` on
the same scenario grid as `main`'s `CRC.scan_instances_with_tag` (oracle `load_legacy_crc`) and
compares every field as before. `test_core_selection.py::test_all_expansion_order_follows_crc_py`
compares with the oracle module (`load_legacy_crc`) instead of `crc.py`'s old re-exports.
`test_crc_py_reexports_the_names_the_contract_needs` lists the names `crc.py` still exports and
checks them on both modules.

**Tests deleted**: none. Every test that touched deleted code was retargeted, not removed, so
no replacement table is needed. `tests/helpers_legacy_handlers.py` was an unreferenced helper
(no test names).

**Test count**: 44415 before, 44415 after (floor 44415, ARCH-008 green; no `raise-test-floor`
needed).

**crc/ Python lines**: 19279 before, 18563 after (-716; `crc.py` itself 102 -> 28 lines).

**Gates**: ruff, lint-imports (5 kept), the full pytest run and ARCH-008 are green. `mypy` reports
the same 7 `import-untyped` errors for `google.cloud`/`azure.*` on this VM before and after my
change (Python 3.12, SDK stubs missing; pyproject targets 3.11); I added no mypy error.
`make check` stops at that step on this VM, so the remaining steps were run by hand.

**Owner actions**: none for the locked tests or BUGS.md/CLEANUP_SAFETY.md (not touched in this
lane). Possible follow-up for the docs lane: `AGENTS.md` still names `HANDLERS`,
`crc/cli/vm_ops.py` and `crc/cli/resource_ops.py` in "Workflow: add or change a cleaner";
`ARCHITECTURE.md` and `CLEANUP_SAFETY.md` may mention the deleted modules.

## What is left

- `crc/cli/constants.py`: `DELETED`, `STOPPED`, `NICS`, `DISKS`, `VMS`, `IPS`, `KEYPAIRS`, `KMS`,
  `SPOT_INSTANCE_REQUEST` and `OPERATIONS` have no production reader now (only `CLOUDS` is used,
  by `scan.py`); its docstring still says "shared by the CRC class and `crc.py`". Not removed
  because tests may read them; remove in the docs/cleanup lane after checking.
- Adapter classes in `crc/<cloud>/**` (next wave); `scan.py` still builds the VM adapters of the
  four clouds, so that wave must give `--scan_tag` a Cleaner or keep the VM adapter's
  `find_instances_with_tag`.
- Tests and test docstrings that mention "legacy `CRC` methods" as oracle history are left, since
  the oracle is `tests/legacy/crc_main.txt`.

## New bugs

None found.
