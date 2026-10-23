## Coding summary

Lane CL2-AZU (test-only). `tests/test_cli_bridge_azu.py` no longer runs the legacy CLI code.

- **Routed / deleted / shimmed:** nothing in `crc/**` changed. No adapter was deleted or shimmed.
- **How the parity tests reach the cleaners now:**
  - Routed side: unchanged. `cli_dispatch._run_pair` runs `bridge.run_routed` and the registered
    cleaner, with `crc.cli.runner.CRC` only as the context object the bridge reads.
  - Legacy side: `main`'s frozen code. `tests/helpers_oracle.load_legacy_crc()` gives `crc_main.txt`
    with the Azure adapters bound to their module oracles. `tests/helpers_cl2_azu.run_oracle_pair`
    repeats the Azure branches of `main()`'s resource loop on that `CRC`. The fake Slack and Influx
    clients and `build` are copies in `tests/helpers_cl2_azu.py`, so the test no longer imports
    `tests.test_cli_crc_parity` (which imports `crc.cli.vm_ops` and `resource_ops`). The Influx fake
    records `SYNCHRONOUS` by name instead of an object address.
  - Run-log lines (RUN START, REGION, ACTION, SKIPPED, ERRORS, FAILED, RESULT): captured once from
    the former legacy handlers (current adapters through `CRC.delete_*` / `stop_*` and
    `run_legacy_handler`) for all 58 (kind, variant, dry) combinations and frozen in
    `tests/helpers_cl2_azu_frozen.py` (`RUN_LOG`). The routed side is asserted against that data.
  - Explicit divergences from `main` (fixed bugs), asserted against the oracle, never against the
    routed side:
    - BUG-358: the raw tag-dict INFO lines per VM or disk are gone (VM and disk kinds).
    - BUG-356: "Skipping leftover Spot disk" lines are DEBUG (`spot_instances`).
    - BUG-003: stop deallocates where `main` powers off (derived from the oracle's mutations).
    - BUG-013 / BUG-077 (IP), BUG-113 (NIC regex), BUG-174 (disk delete isolated): the outcome
      differs (result, Slack, Influx, stdout, logs, mutations). The pre-routing outcome of the
      differing fields is frozen in `FIXED` (45 cases); the test asserts each frozen value differs
      from `main` and a test checks every `FIXED` group has its BUG id.
- **Test count:** before 44400 collected (`test_cli_bridge_azu.py`: 292), after 44408
  (`test_cli_bridge_azu.py`: 300). Same 290 parametrized pair cases and 2 route tests, plus 8 new
  checks (`test_frozen_divergences_are_all_marked_with_a_bug`, and 7 for the BUG-358 / BUG-356 /
  BUG-003 divergences being present in `main`). Floor raised to 44408 with `make raise-test-floor`.
- **Gates:** `make check` green (ruff, mypy, import-linter, 44408 passed, ARCH-008).
- **Grep:** `tests/test_cli_bridge_azu.py`, `tests/helpers_cli_azu.py` and the new
  `tests/helpers_cl2_azu*.py` do not import `crc.cli.resource_ops`, `vm_ops`, `notify`,
  `adapter_args`, `report_calls` or `tests.helpers_legacy_handlers`, and call `delete_*`/`stop_*`
  only on `main`'s oracle `CRC`.
- **Owner actions:** if another lane's test floor conflicts, the integrator resolves it. The
  integrator can delete `tests/helpers_legacy_handlers.py` once the other bridge lanes are off it.
- **Left:** nothing for this file.

## New bugs

None.
