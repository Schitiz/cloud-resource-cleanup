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
