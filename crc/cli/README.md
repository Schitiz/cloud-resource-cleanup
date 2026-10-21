# crc.cli

## Purpose

The command line layer of `crc.py`: the argparse definition of every flag and the input
validators that `main()` runs on the parsed values. Nothing here touches a cloud, a notifier or
an SDK. `crc.py` imports `get_argparser` and the validators back under the same names, so
`main()` (which looks `get_argparser` up in the `crc.py` module globals) and the tests that load
`crc.py` by path keep working. The parsed arguments stay a plain `dict`, as on `main`.

- `args.py`: `get_argparser()`, split into one private `_add_*_args` function per group of flags; the flag order is the order of `main`, which fixes the `--help` text and the key order of the returned dict. JSON and Python-literal values (`--age '{"days": 1}'`, `--filter_tags "{'k': ['v']}"`) go through `ast.literal_eval`.
- `validate.py`: the type validators and the InfluxDB field checks.

## Public API

- `get_argparser()`: parse the process arguments and return them as a dict; exits with code 2 on a usage error.
- `is_valid_type()`: raise ValueError when a value is not an instance of the expected type.
- `is_valid_list()`: no value or a list passes, anything else raises ValueError.
- `is_valid_dict()`: no value or a dict passes, anything else raises ValueError.
- `are_values_of_dict_lists()`: no value or a dict whose values are all lists passes, anything else raises ValueError.
- `validate_influxdb_inputs()`: require url, org and bucket in the InfluxDB dict, else raise ValueError.

## Safety Invariants

- Every flag, default, choice, metavar, help text, literal value form, error type and message,
  and the order of the flags stay exactly as on `main` (`tests/legacy/crc_main.txt` is the
  oracle, `tests/test_cli_args_parity.py` compares both).
- `ast.literal_eval` is the `type=` of the literal flags and must stay that function (argparse
  prints its name in the usage error).
- Jenkins jobs run `python crc.py <flags>`; a flag may never be renamed, removed or re-typed here.
- Known quirks (kept): `docs/refactor/bugs/pending/CLI-1.md`.

## Extension Rules

1. A new flag is added to the matching `_add_*_args` group in `args.py`, with a row in the parity
   table of `tests/test_cli_args_parity.py`, and only in a rung that allows a new flag.
2. Keep each file under 400 lines and each function within the ruff limits; split by group of
   flags, not by line count.
3. `crc.cli` imports no cloud package, no `crc.notify`, no SDK.
