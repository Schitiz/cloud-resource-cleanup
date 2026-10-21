# crc.cli

## Purpose

The command line layer of `crc.py`: the argparse definition of every flag, the input validators
that `main()` runs on the parsed values, and the `CRC` class that `main()` drives. `crc.py` imports
`get_argparser`, the validators, `CRC` and the constants back under the same names, so `main()`
(which looks `get_argparser`, `CRC` and `Snapshot` up in the `crc.py` module globals) and the tests
that load `crc.py` by path keep working. The parsed arguments stay a plain `dict`, as on `main`.

- `args.py`: `get_argparser()`, split into one private `_add_*_args` function per group of flags; the flag order is the order of `main`, which fixes the `--help` text and the key order of the returned dict. JSON and Python-literal values (`--age '{"days": 1}'`, `--filter_tags "{'k': ['v']}"`) go through `ast.literal_eval`.
- `validate.py`: the type validators and the InfluxDB field checks.
- `constants.py`: `CLOUDS`, `RESOURCES`, the report labels (`DELETED`, `VMS`, ...) and the operation map.
- `base.py`: `CRCBase`, the constructor and the run settings every operation reads.
- `notify.py`: `NotifyMixin`, the Slack and InfluxDB methods (`notify_*`, `get_msg`, `ping_on_slack`, `write_influxdb`).
- `vm_ops.py`: `VmOps`, the VM, spot VM, spot instance request and stop operations; it holds the VM and spot adapter imports.
- `resource_ops.py`: `ResourceOps`, the IP, keypair, NIC, disk, VPC and KMS operations; it holds those adapter imports.
- `runner.py`: `CRC`, composed from `VmOps` and `ResourceOps`.

## Public API

- `get_argparser()`: parse the process arguments and return them as a dict; exits with code 2 on a usage error.
- `is_valid_type()`: raise ValueError when a value is not an instance of the expected type.
- `is_valid_list()`: no value or a list passes, anything else raises ValueError.
- `is_valid_dict()`: no value or a dict passes, anything else raises ValueError.
- `are_values_of_dict_lists()`: no value or a dict whose values are all lists passes, anything else raises ValueError.
- `validate_influxdb_inputs()`: require url, org and bucket in the InfluxDB dict, else raise ValueError.
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
- Known quirks (kept): `docs/refactor/bugs/pending/CLI-1.md`, `docs/refactor/bugs/pending/CLI-2.md`.

## Extension Rules

1. A new flag is added to the matching `_add_*_args` group in `args.py`, with a row in the parity
   table of `tests/test_cli_args_parity.py`, and only in a rung that allows a new flag.
2. Keep each file under 400 lines and each function within the ruff limits; split by group of
   flags or by responsibility (notify, vm, resources), not by line count.
3. `args.py` and `validate.py` import no cloud package, no `crc.notify`, no SDK; the adapter and
   notifier imports live in `notify.py`, `vm_ops.py` and `resource_ops.py` only.
