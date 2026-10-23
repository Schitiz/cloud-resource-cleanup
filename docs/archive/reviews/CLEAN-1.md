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
