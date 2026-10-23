## Coding summary

Lane WA-2 (test only): the CLI parity cases for the `CRC` constructor and `scan_instances_with_tag` no longer depend on the module that defines the method.

- **Routed.** Nothing in production changed. The two case groups moved out of `tests/test_cli_crc_parity.py` (blocks removed: the `scan` and `scan_unsupported` entries of `OPERATIONS`, `test_constructor_matches_main`, and the `NewCRC` fallback in `compare` that looked up `NewCRC.scan_instances_with_tag.__module__` and patched adapter names in it; the fallback now runs `execute(NewCRC, [], case)` for the remaining `get_msg` cases, which WA-1 owns and which touch no adapter).
  - `tests/test_cli_scan_parity.py` (new): 480 `scan` + 480 `scan_unsupported` cases, same grid (5 clouds x full/empty x dry-run x 4 Slack modes x 6 Influx modes), same oracle (`load_legacy_crc()`), same compared fields (`result`, `attributes`, `adapters`, `reads`, `slack`, `influx`, `stdout`), plus one anti-vacuity test.
  - `tests/test_cli_runner_parity.py` (new): the 30 constructor cases (cloud, dry_run, notags, resource group, project id, Slack and Influx settings), same inputs and comparison.
  - `tests/helpers_wa2_scan.py` (new): `execute_scan` drives `crc.cli.runner.CRC`.
- **Adapters deleted or shimmed.** None deleted, none added. `tests/helpers_wa2_scan.py` patches the SDK-facing VM classes through their own modules: the `VM` attribute of `crc.aws.vm`, `crc.azu.vm`, `crc.gcp.vm`, `crc.oci.vm` (a seam looked up at call time) and, in place on the class object, its `__init__` and `find_instances_with_tag` (so code that already bound the class, as `vm_ops.py` does today and `scan.py` may later, is reached whichever module holds it). The class `__module__`/`__qualname__` are set to the oracle fake's so the `NotImplementedError` text (`type(vm)`) matches; `__qualname__` is restored explicitly. Only AWS defines `find_instances_with_tag`; the other clouds' real classes lack it, so the patch gives them the fake's behaviour (or removes the method for `scan_supported=False`).
- **How the CLI parity tests reach the cleaners.** Constructor cases need no patching. Scan cases build `CRC` as `crc.cli.runner.CRC`; `_get_vm`/`vm_arguments` construct the (patched) VM class of the cloud, and the call lands on the fake `find_instances_with_tag`. No test imports `crc.cli.vm_ops` or patches a name in it (`grep -rn "cli.vm_ops" tests` is empty; the only `vm_ops` hit is a local variable in `tests/test_azure_vm_delete_helpers_parity.py`). When `scan_instances_with_tag` moves to `crc/cli/scan.py` these cases keep working unchanged, provided `CRC` still builds the VM class with `vm_arguments`' argument order.
- **Test count.** Before 44411, after 44412 (+1: `test_scan_cases_are_not_vacuous`); 960 scan and 30 constructor cases moved unchanged. `tests/archtest/test_count_floor.txt` raised to 44412 with `make raise-test-floor`. `make check` green (ruff, mypy, import-linter, pytest, archtests).
- **Owner actions.** None. If WA-1 edits the same `compare` fallback in `tests/test_cli_crc_parity.py` the integrator may need to resolve a textual conflict on the three lines I changed; the floor file may conflict with other lanes (take the higher value).
- **Left over.** Nothing. Production `CRC.scan_instances_with_tag` and `crc/cli/vm_ops.py` are untouched (later lane).

## New bugs

None.
