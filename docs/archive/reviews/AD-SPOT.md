# AD-SPOT review

## Coding summary

Partial, green state (time limit). No adapter class was deleted in this pass; all five
(`crc.aws.disk.Disk`, `crc.aws.spot_instance_requests.SpotInstanceRequests`, `crc.azu.spot_vm.SpotVM`,
`crc.gcp.spot_vm.SpotVM`, `crc.oci.spot_vm.SpotVM`) are still importable.

- Routed: production already runs every `(cloud, kind)` through `crc/cli/bridge.py` and the registered
  Cleaners; no production module in `crc/` or `crc.py` imports any of the five adapters (checked with
  `git grep`). Nothing in this lane touched production code.
- Done: `tests/test_oci_spot_instances_parity.py` no longer builds the OCI `SpotVM` adapter. Every case
  (same `CASES`, quirks, BUG-255, BUG-358, repeated-delete) now drives the registered Cleaner through
  `crc.core.engine.run` (new helper `tests/helpers_ad_spot_engine.py`) and is compared with the
  oracle `tests/legacy/oci_spot_vm.txt`. The adapter-only test `test_adapter_matches_main` became
  `test_engine_matches_main` (same cases: error, stdout, resources, mutation order). The
  repeated-delete test runs the engine twice; it compares mutating calls in order, `list_*` reads and
  non-summary logs as sets (the engine does not accumulate `get_deleted` across runs, and a second
  adapter run polled `get_instance` a different number of times).
- Test count: 44417 before and after (floor 44417, ARCH-008 green). `make check` green.
- CLI parity tests (`test_cli_*_parity.py`) were not changed in this pass.

## Owner action

None found: the hash-locked tests (`tests/archtest/safety_lock.json`) are all per function and none of
the locked functions builds an adapter (they use `*_engine.py`, `*Cleaner` and `crc.cli` tests).
Note that unlocked tests in locked files still build adapters (see Left).

## Left (unrouted for deletion; the adapters stay until these are retargeted)

Delete each adapter module, its package export and its README Public API line after retargeting:

- OCI `SpotVM` (`crc/oci/spot_vm/adapter.py`, `SpotVmRuntime`): `tests/test_oci_logger.py:384`,
  `tests/test_oci_spot_instances.py:228`.
- GCP `SpotVM` (`crc/gcp/spot_vm/adapter.py`, `settings.py` if only it uses it):
  `tests/test_gcp_spot_instances_parity.py` (adapter path), `tests/test_gcp_spot_instances.py:170`,
  `tests/test_gcp_spot_vm_fix.py:119,165,269`.
- Azure `SpotVM` (class in `crc/azu/spot_vm/__init__.py`, `config.py`/`removal.py` helpers it alone
  uses): `tests/test_azure_spot_instances_parity.py`, `tests/test_azure_logger.py:354`.
- AWS `SpotInstanceRequests` (`crc/aws/spot_instance_requests/adapter.py`, `runtime.py`):
  `tests/test_aws_spot_instance_requests_parity.py`, `tests/test_aws_spot_instance_requests_cleaner.py:140`.
- AWS `Disk` (class in `crc/aws/disk/__init__.py`): `tests/test_aws_disk_parity.py`,
  `tests/test_aws_disk_fix.py:214,265`, `tests/test_aws_disk_cleaner.py:191`.
- Strings `OCI_SpotVM`, `AZU_SpotVM`, `GCP_SpotVM`, `SpotInstanceRequests` in `tests/helpers_cl2_crc.py`,
  `tests/test_cli_bridge_*.py`, `tests/test_core_engine.py` name the frozen oracle's classes (not the
  adapters); review before the final cleanup.

Pattern to reuse: `tests/helpers_ad_spot_engine.run_through_engine(cloud, kind, factory, context)`.

## New bugs

None found.
