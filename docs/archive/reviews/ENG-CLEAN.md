## Coding summary

Status: PARTIAL (green). The time limit allowed step (1) of the task only; steps (2) and (3)
(deleting the legacy code) are left for the next run. Test count before 44364; after 44373 (floor raised;
new file `tests/test_cli_route_skip.py`). `make check` is green.

### Done
- `Route.skip` (`crc/cli/routes/__init__.py`, type `Skip`): runs first in `bridge.run_routed`
  (after RUN START, before `Route.precheck`, registry, notifiers and `init_run_logging`); when it
  returns True nothing is built, called or reported, as the legacy `_spot_instances` handler did
  (warning, SAF-037). `crc/cli/routes/skips.py` holds `explicit_cloud_spot`, the exact warning of
  the handler.
- Routed `spot_instances` for GCP (`routes/gcp.py`, skip under `--cloud all`, precheck raising
  `project_id is required for GCP Spot VM cleanup` before the cleaner as `delete_spot_instances`
  did) and OCI (`routes/oci.py`, skip under `--cloud all`). Every cloud-kind pair that runs a
  cleaner is now engine-routed.
- BUG-409 row (BUGS.md) and one sentence in CLEANUP_SAFETY.md (plan lists all regions before apply
  for GCP and OCI spot_instances).
- Tests retargeted: `ROUTED_CALLS` for gcp and oci `spot_instances` (`tests/helpers_cli_routes_gcp.py`,
  `tests/routed_calls_oci.py`), `test_cli_main_parity.py` (oracle FakeCRC raises the GCP project
  error as the real method), route-table assertions in `test_cli_bridge_gcp.py` and
  `test_cli_bridge_parity.py`, `test_core_selection.py` passes a project id. New
  `tests/test_cli_route_skip.py` covers the skip, the precheck and the no-notifier guarantee.

### Left (not done)
- Warn-only pairs still use legacy handlers in `crc/cli/dispatch.py` `HANDLERS`: `spot_instances`
  on AWS and `spot_instance_requests` off AWS. They need a skip-only route that does not need a
  registered cleaner (`tests/test_cli_bridge_parity.py::test_every_routed_pair_has_a_registered_cleaner`
  requires a cleaner per route; I tried and reverted this).
- Deleting the legacy code: CRC methods and `crc/cli/notify.py`, `HANDLERS`, `adapter_args.py`,
  the `crc.py` adapter re-exports and the adapter classes; the five hash-locked adapters stay.
  Blockers found: `test_cli_bridge_{azu,gcp,oci}.py`, `test_cli_bridge_parity.py`,
  `test_cli_crc_parity.py`, `test_cli_dispatch_fix.py` and the module parity tests build the legacy
  side through `HANDLERS` / `CRC` and the adapters; each needs retargeting to the Cleaner through
  `engine.run` with the same oracle cases first.
- `crc/core/selection.py` still has no production user besides tests; deletion needs the CLI tests
  to cover every case of `tests/test_core_selection.py`. Owner action: decide after the legacy
  deletion. `crc/` line count unchanged by this run.
- Cleaner-based copies of the 5 locked tests (`tests/test_<name>_engine.py`): the files
  `test_aws_disk_engine.py`, `test_aws_spot_instance_requests_engine.py` and
  `test_azu_spot_vm_engine.py` already existed; GCP and OCI copies were not checked.

### Owner actions
- None needed for the safety lock files (no locked test edited).

### New bugs
- None found.
