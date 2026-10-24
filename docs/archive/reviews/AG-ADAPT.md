## Coding summary

Partial state, green (`make check`): step (1a) and the wording fix of step (3) are done; the adapter
deletion (1b) and the selection and policy cleanup (2) are left.

- Routed: `--scan_tag` no longer builds the four VM adapters. `crc.cli.scan.scan_instances_with_tag`
  calls `crc.aws.vm.scan.scan_tag` (new, default boto3 session, scan client and region lister) for
  AWS. Azure, GCP and OCI raise the same `NotImplementedError` text as before, naming the former
  adapter class (`crc.azu.vm.adapter.VM`, `crc.gcp.vm_adapter.VM`, `crc.oci.vm.adapter.VM`), after
  `_prepare_scan` repeated the observable set-up of the adapter constructors (`Service()` logging
  init, Azure `Base(resource_group)` env and credential reads, OCI `Base()` key check, GCP
  `ComputeVmClient()`), so a missing credential is still reported as `error scanning: ...`.
  An unknown cloud still raises the same ValueError before any set-up.
- Adapters deleted or shimmed: none yet. `VM`, `VmRuntime` and the other adapter classes are
  unused by production now (READMEs say so) and only tests import them.
- CLI parity tests: `tests/helpers_wa2_scan.py` now patches `crc.cli.scan._prepare_scan` and
  `crc.aws.vm.scan.scan_tag` instead of the VM classes. `test_cli_scan_parity.py` compares the
  oracle (`crc_main.txt` on fakes) with the routed scan with the same grid and fields; changes:
  non-AWS clouds are compared against the oracle with no finder (production reality; the old
  cases gave Azure/GCP/OCI fake finders no production class has), fake class texts are mapped to
  the production class texts, and the `new` (adapter constructor) entries are replaced by an
  assertion that the set-up ran exactly once per cloud. New tests: exact NotImplementedError text
  per cloud, direct AWS call, set-up per cloud, missing-credential errors.
- Wording (BUG-004): "fail open" became "fail closed" in `crc/aws/vm/README.md`,
  `crc/azu/vm/README.md` and `crc/gcp/README.md` (`get_retention_age` fails closed).
- Test count: floor 44415 before, 44422 after (7 new tests; floor raised).
- Owner actions: none.

## Left (not done, out of time)

1. Delete the four VM adapter classes and exports, and retarget `test_{aws,azure,gcp,oci}_vm_parity.py`
   (about 3900 lines), `test_*_vm.py`, `test_*_vm_fix.py`, the logger tests, `test_cli_bridge_aws.py`
   and `test_oci_spot_instances*.py` (they import the adapters) to the registered cleaners via
   `crc.core.engine.run`.
2. `build_selection` / `SelectionOptions` (BUG-371): production never calls them, but
   `tests/test_core_selection.py` compares them with `crc_main.txt` over an exhaustive grid; I did not
   verify that the CLI tests cover every case, so nothing was deleted. The dead policy helpers (BUG-370)
   were not examined.

## New bugs

- `crc/cli/scan.py` `_prepare_scan`: the scan still runs the Azure/OCI/GCP set-up (credential reads,
  logging init that prints and truncates `logs/crc.log`) only to print "scan not implemented"; it is
  kept for exact output and can go once the owner accepts a changed message for those clouds.
