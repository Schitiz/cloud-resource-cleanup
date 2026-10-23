## Coding summary

Status: PARTIAL (green, time limit). Test-only lane CL2-CRC; no production file touched.

### What is routed
- `tests/test_cli_crc_parity.py` operation cases (`delete_vm`, `stop_vm`, spot, spot requests, `ip`,
  `nic`, `disks`, `vpc`, `kms`, all 5 clouds, all Slack/Influx modes, dry run, delete errors) no longer
  call `CRC.delete_*`/`stop_*` of `crc.cli.runner.CRC`. The oracle side is
  `load_legacy_crc()` (main's `CRC` on main's adapters); the other side is
  `bridge.run_routed` with the production route of the pair (`bridge.route_for`) and a recording fake
  cleaner (`tests/helpers_cl2_crc.py` `RoutedCleaner`, registered through a `Registry` patched into
  `bridge.build_registry`). Slack calls, Influx points, stdout and the result/exception are compared
  exactly. `notify_*` direct cases: the oracle `notify_*` against the same routed pair with Slack only.
- Pairs no route reaches (`route_for` is None: `other`, `ip` on OCI, `nic` off Azure, `vpc`/`kms`/keypair
  off AWS, the Azure-only alias on GCP) assert that the production table has no route and that the
  oracle raises main's error. Skip-only routes (AWS `spot_instances`, `spot_instance_requests` off AWS)
  assert nothing is built, sent or written.
- `tests/test_cli_bridge_parity.py` already ran the oracle against `bridge.run_routed`; only the shared
  fakes moved (its imports from `tests.test_cli_crc_parity` still work, names re-exported).
- Nothing deleted or shimmed in `crc/`.

### Left (not done; time limit)
- (b) Run-log lines (RUN START, REGION, ACTION, SKIPPED, ERRORS, RESULT) were not frozen: these tests
  never compared them (the log goes to the logger, not stdout; `init_run_logging` is patched).
- Adapter constructor arguments and method order, attribute reads (`adapters`/`reads` keys of the old
  comparison) have no routed equivalent with a fake cleaner and are no longer compared here; the options
  the routes pass to the cleaner are asserted by `test_cli_bridge_{aws,azu,gcp,oci}.py`.
- Disk result shapes the report cannot carry (`None`, a str, a tuple, `{"alice": None}`) and the
  `*_none` notify cases (`get_deleted=None`) only run the oracle (asserts ok/error), no routed side.
- With no Slack client, the oracle `notify_*` still posts and prints "Failed to send message"; the bridge
  builds no Slack notifier then. Asserted as that divergence (routed sends nothing); for owner-dict disk
  values the oracle's own stdout in that mode is not compared.
- Still compared against `CRC` of `crc.cli.runner` (methods of `notify.py`, not `notify_*`): `get_msg`,
  `slack_lookup_user_by_email`, `get_user_groups_list`, `write_influxdb`, `ping_on_slack`, the
  constructor attributes, and the `scan_instances_with_tag` cases (which patch the adapters in the module
  `CRC.scan_instances_with_tag` is defined in, found via `__module__`, no import of `vm_ops`). A later
  lane must move these to `crc.notify` / the notifiers before deleting `notify.py` and `vm_ops.py`.

### Numbers
- Test count of the two owned files: 11940 before, 11940 after (floor unchanged).

### Owner actions
- None.

## New bugs
- None found.
