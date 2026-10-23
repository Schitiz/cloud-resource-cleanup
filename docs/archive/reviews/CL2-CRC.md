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

## Round 1 (Argon)

Scope reviewed: `git diff 2bd8e67..HEAD` on branch `cl2/crc` (lane `CL2-CRC`).

### Findings & fixes made in review

1. **Eliminated remaining calls to `CRC.notify_*` and `crc/cli/notify.py` methods on `crc.cli.runner.CRC`** (`tests/test_cli_crc_parity.py`, `tests/helpers_cl2_crc.py`):
   - In `7a7d6fa`, `direct_cases()` set `routed = None` whenever `name not in NOTIFY_SPECS`, which caused `nic_none`, `vm_none`, and `disk_4`..`disk_7` (1,440 test cases) as well as `lookup_known`, `lookup_unknown`, `groups`, `write_list`, `write_empty`, `write_dict`, `write_none`, `ping_dict`, `ping_empty`, `ping_list`, and `ping_no_len` to fall through to `execute(NewCRC, ...)` and call `NewCRC.notify_deleted_*_via_slack`, `NewCRC.slack_lookup_user_by_email`, `NewCRC.get_user_groups_list`, `NewCRC.write_influxdb`, and `NewCRC.ping_on_slack`.
   - Routed `ping_dict` and `ping_empty` through `NOTIFY_SPECS` (`Op("disk")`), and wired `DIRECT_ACTIONS` for the remaining direct cases through `SlackNotifier` (`lookup_user_by_email`, `user_groups`, `ping_owners_raw` with `BUG-033`), `InfluxNotifier` (`write`), `NewCRC.get_msg` (`nic_none`, `vm_none`), and the `BUG-031` non-list/non-dict no-op (`disk_4`..`disk_6`), Remove-proofing `crc/cli/notify.py` so `NewCRC` is only ever called for `__init__`, `get_msg`, and `scan_instances_with_tag`.
2. **Restored `"adapters"` and `"reads"` comparisons across `OPERATION_CASES` and `test_delete_disks_result_shapes_match_main`** (`tests/helpers_cl2_crc.py`, `tests/test_cli_crc_parity.py`):
   - Populated `Op.flags` in `ROUTED` with each operation's actual CLI flags (including `resource_states=["RUNNING"]`, `[]`, and `None` for the three `delete_vm` variants, `DISK_FLAGS`, `KMS_FLAGS`, etc.) and reconstructed the adapter constructor `(args, kwargs)` in `RoutedCleaner.plan` and the `(adapter, "delete" | "stop", ...)` call in `RoutedCleaner.apply` (or `plan` in dry-run) purely from `RunContext` (`context.dry_run`, `context.operation`, `context.options`).
   - Added `"adapters"` to `OP_COMPARED` (`("result", "adapters", "slack", "influx", "stdout")`) and restored `for key in old:` (including `"adapters"` and `"reads"`) for `scan`, `scan_unsupported`, `ctor`, and `get_msg_*`.
3. **Completed `slack="off"` notify comparison, unrepresentable disk shapes, and `BUG-084`/`BUG-017` route rejection assertions** (`tests/test_cli_crc_parity.py`):
   - In `compare_notify`, when `slack == "off"`, asserted both that `bridge.build_notifiers` gates on `crc.slack_client` (sending nothing) and that `run_routed(..., force_slack=True)` matches `oracle.CRC.notify_*` on all `COMPARED` keys (including owner-dict disk stdout and `TypeError`). Also removed the duplicate `return old` on line 125.
   - In `test_delete_disks_result_shapes_match_main`, replaced the vacuous `assert outcome["result"][0] in {"ok", "error"}` on non-representable disk values (`("d1",)`, `None`, `"d1"`, `{"alice": None}`) with `_unrepresentable_disk_run` (checking routed disk options, `BUG-031` / `ping_owners_raw` Slack behaviour, and `InfluxNotifier.write`) compared against `old` across all `OP_COMPARED` keys.
   - When `bridge.route_for(case.cloud, op.kind)` is `None`, asserted `dispatch.validate_targets` raises `ValueError` for known clouds and asserted the `BUG-084` / `BUG-017` fixed-bug divergence for `("azure", "vpc")` against `old["result"]`.

### Checklist verification

1. **No legacy CLI imports or calls**: Grepped `tests/test_cli_crc_parity.py`, `tests/test_cli_bridge_parity.py`, and `tests/helpers_cl2_crc.py` — zero imports of `crc.cli.resource_ops`, `vm_ops`, `notify`, `adapter_args`, `report_calls`, or `tests.helpers_legacy_handlers`. Verified by poisoning all methods on `crc.cli.runner.CRC` except `__init__`, `get_msg`, `scan_instances_with_tag`, and `_get_vm`: all 11,940 tests in the two owned files pass.
2. **All comparisons and case counts preserved**: 11,940 tests in `tests/test_cli_crc_parity.py` + `tests/test_cli_bridge_parity.py` (unchanged); every case compares against `tests.helpers_oracle.load_legacy_crc()` with `BUG-084`/`BUG-017`, `BUG-031`, and `BUG-033` explicitly marked.
3. **Non-vacuous (mutation check)**: Verified locally (not committed) that mutating `crc.core.report.get_msg` (Slack message text) and `crc.cli.routes.aws._vm` (routed cleaner options) each cause immediate failures in `tests/test_cli_bridge_parity.py` and `tests/test_cli_crc_parity.py`.
4. **Owned files only**: Only `tests/test_cli_crc_parity.py`, `tests/helpers_cl2_crc.py`, and `docs/archive/reviews/CL2-CRC.md` are modified in `2bd8e67..HEAD`; zero production, oracle, safety-lock, or archtest files touched.

### Gates & test count

- `python3 -m ruff check .`: passed
- `python3 -m mypy`: passed (365 source files)
- `lint-imports`: passed (5 contracts kept, 0 broken)
- `python3 -m pytest -q -n auto`: **44400 passed in 56.26s** (`make check` total ~75s; owned files: **11940 passed in 19.00s**)
- `python3 -m tests.archtest.test_count check`: `ARCH-008: 44400 tests, floor 44400`

VERDICT: APPROVE
