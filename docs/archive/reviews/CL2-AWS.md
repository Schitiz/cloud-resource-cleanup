## Coding summary

Lane CL2-AWS (test-only): `tests/test_cli_bridge_aws.py` no longer reaches the current legacy CLI code.

- **What is routed:** nothing changed in production. Every AWS kind (ip, kms, vpc, vm delete/stop, spot_instance_requests, disk) was already routed through `crc/cli/bridge.py`; the test drives `bridge.run_routed` with a fake cleaner (and the real `VmCleaner` in the last test).
- **Adapters deleted or shimmed:** none (production untouched).
- **How the parity tests now reach the cleaners:** the legacy side was already `load_legacy_crc()` (`tests/legacy/crc_main.txt` bound to the module oracles), so no legacy-CLI behaviour had to be re-frozen and no run-log line data was needed: the compared stdout, Slack, Influx and exception records are identical to the oracle's without any run-log assertions. The only link to current legacy code was the import of fakes (`Scenario`, `Logs`, `make_fake`, `build`, `scenario_grid`, the `oracle` fixture, constants) from `tests/test_cli_crc_parity.py`, which imports `crc.cli.resource_ops` and `crc.cli.vm_ops`. Those fakes now live in `tests/helpers_cl2_aws.py` (a copy; the `oracle` fixture uses `load_legacy_crc("legacy_crc_main_cl2_aws")`). The test only imports `crc.cli.runner.CRC` as the context object for the bridge.
- **Verification:** grep of both files finds no import of `resource_ops`, `vm_ops`, `notify`, `adapter_args`, `report_calls`, `helpers_legacy_handlers` and no call of CRC `delete_*`/`stop_*`/`notify_*`. Re-running the test with all 18 `delete_*`/`stop_*`/`notify_*` methods of the current `CRC` MRO replaced by raising stubs still passes all cases.
- **Test count:** `tests/test_cli_bridge_aws.py` 675 before and after; whole suite 44400 before and after (floor unchanged, no `raise-test-floor` needed). `make check` green.
- **Owner actions:** none. Note for the integrator: `crc/cli/runner.py` still imports `ResourceOps`/`VmOps` (production), so the final deletion lane must keep `CRC` importable without them; `tests/helpers_cl2_aws.py` is independent of that.

## New bugs

None found.
