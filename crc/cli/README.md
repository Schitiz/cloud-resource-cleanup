# crc.cli

## Purpose

The command line layer of `crc.py`: the argparse definition of every flag, the input validators,
the `CRC` class that does the work per cloud, the bridge to `crc.core.engine` for the routed kinds, and `main()` which wires them. `crc.py` is a thin
entry point: it imports `main`, `get_argparser`, the validators, `CRC`, `Snapshot` and the constants
back under the same names (and keeps `if __name__ == "__main__": main()`), so the tests that load
`crc.py` by path and `python crc.py <flags>` in Jenkins keep working. The parsed arguments stay a
plain `dict`, as on `main`.

- `args.py` and `args_run.py`: `get_argparser()`, split into one private `_add_*_args` function per group of flags (selection and filter flags in `args.py`, age, notify and resource flags in `args_run.py`); the flag order is the order of `main`, which fixes the `--help` text and the key order of the returned dict. JSON and Python-literal values (`--age '{"days": 1}'`, `--filter_tags "{'k': ['v']}"`) go through `ast.literal_eval`.
- `validate.py`: the type validators and the InfluxDB field checks.
- `constants.py`: `CLOUDS`, `RESOURCES`, the report labels (`DELETED`, `VMS`, ...) and the operation map.
- `base.py`: `CRCBase`, the constructor and the run settings every operation reads.
- `notify.py`: `NotifyMixin`, the Slack and InfluxDB methods (`notify_*`, `get_msg`, `ping_on_slack`, `write_influxdb`).
- `vm_ops.py`: `VmOps`, the VM, spot VM, spot instance request and stop operations; it holds the VM and spot adapter imports.
- `adapter_args.py`: the constructor arguments of the adapter classes per cloud (`vm_arguments`, `ip_arguments`, `disk_arguments`); the classes themselves stay looked up in `vm_ops` and `resource_ops`.
- `report_calls.py`: `report_result`, the Slack then Influx call every operation ends with.
- `pairs.py`: the supported (cloud, resource) pairs and the unsupported-pair message; `dispatch.py` re-exports them.
- `resource_ops.py`: `ResourceOps`, the IP, keypair, NIC, disk, VPC and KMS operations; it holds those adapter imports.
- `runner.py`: `CRC`, composed from `VmOps` and `ResourceOps`.
- `main.py`: `main()`, which composes the modules below in the order of `main` on the main branch.
- `inputs.py`: `Options` (every flag read with `.get`), `Tokens`, `Targets`, `read_options`, `read_tokens`, and the checks in the order `main` ran them (`check_tokens`, `check_flag_combinations`, `resolve_targets`, `validate_values`).
- `clients.py`: the Slack `WebClient` and `InfluxDBClient` construction (the InfluxDB field check runs right before it) and the `MAX_AGE` environment write with its print, and its reset.
- `context.py`: `RunContext` (the settings every `CRC` of a run shares) and `make_crc`, the one place that builds `CRC(...)` for `main`.
- `scan.py`: `run_scan`, the read-only `--scan_tag` path; it wraps each cloud pass in `crc.core.logger.begin()` / `finish()` (`operation=scan`), prints, notifies Slack and always exits with code 0.
- `bridge.py`: `route_for`, `run_routed`, `init_run_logging`, `build_registry`, `build_notifiers`: the engine bridge. A pair whose kind is in the route table of its cloud (`routes/aws.py`, `azu.py`, `gcp.py`, `oci.py`) initialises logging via `Service`, runs `crc.core.engine.run` with the registered cleaner, a `RunContext` and a one pair `Selection`, then the Slack and Influx notifiers (Slack first, only when a Slack client is set; Influx only when an Influx client is set) and the route's extra notifiers. The route's `NotifyMode` picks none (`vpc`, `snapshot`), report (default) or report then re-raise (`disk`: a `plan()` or `apply()` error is reported with `partial_succeeded`, then raised again); `Route.precheck` is the AWS disk opt-in gate and `Route.after` prints the snapshot line. `init_run_logging`, `build_registry` and `build_notifiers` are looked up in `bridge` at call time: the seam the CLI parity tests patch (`tests/helpers_cli_routes.py`).
- `routes/`: the route tables (see `routes/README.md`).
- `dispatch.py`: `run_dispatch`, the cloud and resource loops: one small handler per resource wrapped in `crc.core.logger.begin()` / `finish()` (`try`/`finally`), the pair validation (`validate_targets`, including the AWS-only `snapshot` and `vpc`) with the AWS disk opt-in breaker, the spot warnings, and the legacy handlers of the kinds some cloud still runs on `CRC` (`disk`, `ip`, `nic`, `vm`, `spot_instance_requests`, `spot_instances`). The AWS pairs of every kind the Azure `disk`, `ip`, `nic`, `spot_instances` and `vm` pairs and the GCP `disk`, `ip` and `vm` pairs run through `bridge` (GCP `spot_instances` keeps its handler); `kms`, `snapshot` and `vpc` have no legacy handler left.

## Public API

- `route_for()`: the route of a (cloud, kind) pair, or None when the pair keeps the legacy handler (module bridge.py).
- `is_routed_kind()`: True when at least one cloud routes the kind.
- `run_routed()`: run one routed pair through the engine with its notifiers.
- `init_run_logging()`: initialise the log file and root handlers as Service did in every adapter; patched by the parity tests.
- `build_registry()`: the registry the routed cleaners come from; patched by the parity tests.
- `build_notifiers()`: the Slack then Influx notifiers of a routed pair; patched by the parity tests.
- `main()`: the CLI entry (module main.py); crc.py re-exports it. It is not re-exported from the package init module, so the name `main` on the package stays the module.
- `run_scan()`: the read-only scan path of the scan_tag flag; prints, notifies Slack and exits with code 0.
- `run_dispatch()`: the cloud and resource loops, with the AWS disk breaker.
- `validate_targets()`: check every (cloud, resource) pair before the first cleaner (BUG-017, BUG-018, BUG-009, BUG-084); raise an error, or return the pairs to skip under cloud all.
- `is_supported_pair()`: False for a pair whose CRC method raises for that cloud (keypair and kms off AWS, nic off Azure, ip on OCI) or that is AWS-only (snapshot and vpc off AWS).
- `Options`: frozen value of every parsed flag; `read_options()` builds it from the argument dict.
- `Tokens`: frozen value of the two environment tokens; `read_tokens()` builds it.
- `Targets`: frozen value of the expanded clouds and resources; `resolve_targets()` builds it.
- `check_tokens()`: raise OSError when a Slack channel or InfluxDB is set without its token.
- `check_flag_combinations()`: raise ValueError on stop for non-vm, all without all, user label, KMS flags.
- `check_scan_tag()`: raise ValueError for an empty or blank scan_tag flag (BUG-344).
- `validate_values()`: the list and dict type checks of the flag values.
- `build_slack_client()`, `build_influxdb_client()`: construct the clients (InfluxDB field check first), or return None.
- `set_max_age()`, `reset_max_age()`: write and remove the MAX_AGE environment variable, with the prints.
- `RunContext`: frozen value of the settings every `CRC` of a run shares; `make_crc()` builds `CRC` from it.
- `get_argparser()`: parse the process arguments and return them as a dict; exits with code 2 on a usage error.
- `is_valid_type()`: raise ValueError when a value is not an instance of the expected type.
- `is_valid_list()`: no value or a list passes, anything else raises ValueError.
- `is_valid_dict()`: no value or a dict passes, anything else raises ValueError.
- `are_values_of_dict_lists()`: no value or a dict whose values are all lists passes, anything else raises ValueError.
- `validate_influxdb_inputs()`: require url, org and bucket in the InfluxDB dict, else raise ValueError.
- `DiskArgs`: frozen value of the nine delete_disks arguments (module adapter_args.py).
- `vm_arguments()`, `ip_arguments()`, `disk_arguments()`: positional (and for GCP disks keyword) adapter arguments of the cloud of a `CRC`.
- `report_result()`: Slack when a client is set, then Influx of the result attribute when a client is set.
- `CRC`: the cleanup object built per cloud (module runner.py); every public method of the run keeps its name, signature and call order.
- `CRCBase`: constructor and run settings (cloud, dry run, notags, the Slack and Influx clients).
- `NotifyMixin`: Slack and Influx methods of `CRC`.
- `VmOps`: VM, spot and stop operations of `CRC`.
- `ResourceOps`: IP, keypair, NIC, disk, VPC and KMS operations of `CRC`.

## Safety Invariants

- Every flag, default, choice, metavar, help text, literal value form, error type and message,
  and the order of the flags stay exactly as on `main` (`tests/legacy/crc_main.txt` is the
  oracle, `tests/test_cli_args_parity.py` compares both).
- `ast.literal_eval` is the `type=` of the literal flags and must stay that function (argparse
  prints its name in the usage error).
- Jenkins jobs run `python crc.py <flags>`; a flag may never be renamed, removed or re-typed here.
- `CRC` keeps the call order of `main`: adapter constructor, `delete()` / `stop()`, Slack, then
  Influx; `delete_disks` runs Slack and Influx before it re-raises a `delete()` error. The adapter
  classes are looked up in the module of the mixin that uses them (`vm_ops`, `resource_ops`) at
  call time. `tests/test_cli_crc_parity.py` runs the oracle CRC and this one on the same fakes.
- `main()` keeps the order of `main` on the main branch: parse flags, read the two tokens, `SLACK_BOT_TOKEN` then `INFLUXDB_TOKEN` errors, stop-only-for-vm, all-needs-all, slack user label, KMS description and user, the list and dict type checks, the Slack client, the InfluxDB field check and client, `MAX_AGE` set, then the scan path (exit) or the loops, then `MAX_AGE` reset. Errors keep their type (`OSError`, which `EnvironmentError` is an alias of) and message.
- `scan.py` never deletes: it forces `dry_run`, builds `CRC` per cloud and only calls `scan_instances_with_tag`; it always ends in `sys.exit(0)`.
- The AWS EBS breaker lives in `Route.precheck` of the AWS disk route (`routes/aws.py`) and, since FIX-CLI-ALL (BUG-018), also in `dispatch.validate_targets`: any `aws` + `disk` pair that is not `--cloud aws --resource disk` (so `--cloud all --resource disk|all`) raises `ValueError` before any cleaner of any cloud runs; it does not run.
- One pair rule (FIX-CLI-ALL BUG-017 merged with FIX-CLI-ROUTE BUG-009/BUG-084, as FIX-CLI-MERGE): `dispatch.SUPPORTED_CLOUDS` lists the clouds each resource runs on, and `dispatch.validate_targets` checks every (cloud, resource) pair before the first cleaner. `main()` calls it before `MAX_AGE` is set (not on the read-only `--scan_tag` path) and `run_dispatch` calls it again. The pairs are `keypair` and `kms` (AWS), `nic` (Azure), `ip` (not OCI) and `snapshot` and `vpc` (AWS only). An unsupported pair of an explicit cloud raises `ValueError` up front (the `CRC` message; `--resource <r> is AWS-only; use --cloud aws (got --cloud <c>)` for `snapshot` and `vpc`), so nothing runs and `MAX_AGE` is untouched. Under `--cloud all` it also raises up front when a supported pair would run after it (`--cloud all --resource nic`: `main` stopped on aws, so Azure NICs are never deleted); otherwise it is skipped with a WARNING (`<r> is not supported on <cloud>; skipped under --cloud all`) plus a `RUN START` / `SKIPPED reason=unsupported_cloud_resource` / `RESULT` log triple. So `--cloud all --resource snapshot|vpc` runs once, for AWS. `CRC`, `Snapshot`, `WebClient`, `InfluxDBClient` and `notify_cleanup` are looked up in `context`, `dispatch`, `clients` and `scan` at call time; `tests/test_cli_main_parity.py` runs the oracle `main()` and this one on recording fakes.
- An empty or blank `--scan_tag` raises `ValueError` from `inputs.check_scan_tag` before `MAX_AGE` is set and before any cleaner runs (BUG-344, fixed in FIX-CLI-ROUTE); it used to be falsy, skip the read-only scan and run the destructive cleanup.
- Known quirks (kept): `docs/refactor/BUGS.md` rows `BUG-028` to `BUG-044`, `BUG-333` to `BUG-350` except `BUG-344`. `BUG-009` and `BUG-084` keep only the hard-coded `age_days=90` and the missing Slack and Influx notification of `snapshot`.

## Extension Rules

1. A new flag is added to the matching `_add_*_args` group in `args.py`, with a row in the parity
   table of `tests/test_cli_args_parity.py`, and only in a rung that allows a new flag.
2. Keep each file under 400 lines and each function within the ruff limits; split by group of
   flags or by responsibility (notify, vm, resources), not by line count.
3. Route a kind through the engine (pattern: AWS `keypair`, `routes/aws.py`). In the cloud's route file
   add an options builder (flags to the keys the registered factory reads from `RunContext.options`)
   and `"kind": Route(builder)` to `ROUTES`, and import the cleaner package so it registers. Then delete
   the adapter, its `CRC` method and its `dispatch.HANDLERS` entry (keep the entry while any supported
   cloud still runs the kind on the legacy path: a supported pair with neither a route nor a handler
   runs nothing between RUN START and RESULT), and retarget the tests: the
   adapter's parity test drives the Cleaner through `engine.run` with the same oracle cases; the CLI
   parity tests (`test_cli_main_parity.py` `ROUTED_CALLS` (AWS; every other cloud has its own `tests/helpers_routed_<cloud>.py` with a `ROUTED_CALLS` table, so lanes do not edit one shared table), `test_cli_logger.py`) use
   `tests/helpers_cli_routes.FakeCleaners`, which patches `bridge.build_registry` and
   `bridge.build_notifiers` so the fake cleaner records the flags it received; add the kind to
   `tests/test_cli_bridge_parity.py` to compare Slack, Influx, output and errors with the oracle `CRC`.
   Gates the legacy handler raised (the AWS disk opt-in) go in `Route.precheck`. Note that the engine
   skips Slack and Influx when `apply()` raises, where `delete_disks` reported first.
4. `args.py`, `validate.py`, `constants.py` and `inputs.py` import no cloud package, no `crc.notify`, no SDK; the SDK client, adapter and
   notifier imports live in `clients.py`, `notify.py`, `vm_ops.py`, `resource_ops.py`, `scan.py` and `dispatch.py` only.
