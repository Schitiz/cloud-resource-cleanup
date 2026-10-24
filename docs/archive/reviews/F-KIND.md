# F-KIND review

## Coding summary

**What is routed.** Every resource kind is now declared once, in `crc/core/kinds.py`
(`Kind`: name, report label, `in_all`, `clouds`, unsupported-pair message template; `explicit_only`
is `not in_all`). It lives in `crc/core` because `crc/cli` imports core, never the reverse
(import-linter), and the engine labels need it. Derived from `KINDS`:

- the `--resource` parser choices (`crc/cli/args.py`: `[*KIND_NAMES, "all"]`),
- `crc.core.selection.RESOURCES` / `EXTRA_RESOURCES` and `crc.cli.constants.RESOURCES`,
- `crc.cli.pairs.SUPPORTED_CLOUDS`, `AWS_ONLY_RESOURCES` and `_unsupported_message`,
- `crc.core.engine.KIND_LABELS`,
- `tests/test_core_selection.py` `SUPPORTED_ON` (now built from `KINDS`, not hardcoded).

One table order serves both lists: the parser order is `disk, ip, keypair, vm, vpc, kms, nic,
spot_instance_requests, spot_instances, snapshot`, and the `in_all` kinds in that order are exactly
the old `--resource all` order. Nothing had to stay hand-written; the `--resource` help text stays
hand-written in `args.py` (it is prose, in a different order, with annotations, and the parity
tests compare it byte for byte). `CLOUDS` stays a literal (not a kind).

New test `tests/test_core_kinds.py` locks the derived values to the old literals (choices order,
`RESOURCES`, `EXTRA_RESOURCES`, `SUPPORTED_CLOUDS`, every unsupported-pair message, every label) and
adds the route-table completeness check: every supported `(cloud, kind)` has a route and every
route is a supported pair (a kind with `clouds=None` is supported, so routed, on all four clouds;
the warn-only spot pairs are skip routes).

**Adapters deleted or shimmed.** None; no adapter was involved. `crc/cli/pairs.py` keeps its
public names (`SUPPORTED_CLOUDS`, `AWS_ONLY_RESOURCES`, `is_supported_pair`, `_unsupported_message`)
as derived values, so `dispatch.py` re-exports and the tests are unchanged.
`UNSUPPORTED_PAIR_MESSAGES` (a private-use dict, no importer) is gone; its text is in the table.

**How the CLI parity tests reach the cleaners.** Unchanged: CLI -> `bridge` -> route tables ->
`engine.run` -> `FakeCleaners` (`tests/helpers_cli_routes.py`). No parity test, oracle or Jenkins
contract assertion was edited; all pass as before.

**Tests.** Before: 44,597 (floor 44,597) passed + 1 skipped. After: 44,612 passed + 1 skipped
(44,613 collected, floor raised with `make raise-test-floor`). `make check` green.

**Owner actions.** None. No guardrail file, oracle or `frozen_inputs` change.

**New bugs.** None.

## Docs to update (lane F-DOCS)

- `ARCHITECTURE.md` add-a-cleaner steps (around lines 115-128): replace the separate edits of
  `crc/cli/constants.py`, `crc/cli/args.py` choices, `crc/core/selection.py`, `crc/cli/pairs.py`
  and `KIND_LABELS` in `crc/core/engine.py` with one: add a `Kind(...)` entry to `KINDS` in
  `crc/core/kinds.py` (position = `--resource` choices order; keep `in_all` kinds in the old
  expansion order). Still separate: the label constant in `crc/core/report.py` (if new), the
  hand-written `--resource` help text in `crc/cli/args.py`, the route in
  `crc/cli/routes/<cloud>.py` (the completeness test fails without it), the cleaner, and the
  `tests/helpers_ag_cli_added.py` entry (`ADDED_RESOURCES`, `RESOURCE_HELP`).
- `tests/test_core_selection.py` no longer needs a `SUPPORTED_ON` edit.
- `AGENTS.md` / `crc/cli/README.md` extension rule 3: mention the single place `crc/core/kinds.py`.

## Left over

Nothing unrouted; no partial state.
