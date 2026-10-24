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
- `crc/cli/README.md` (`## Purpose` bullets for `constants.py` and `pairs.py`, plus extension rule 3) and `AGENTS.md`: mention the single place `crc/core/kinds.py`.

## Left over

Nothing unrouted; no partial state.


## Round 1 (Argon)

Reviewed `git diff f8ed6dd..HEAD` against the Lane F-KIND specification, the two third-round audits (`AGENT-NATIVE-AUDIT-3.md` and `AGENT-NATIVE-AUDIT-3-GPT.md`), and the final wave contract.

### Findings

1. **Fixed (lane ownership boundary in `crc/cli/README.md` and `crc/core/README.md`):**
   - `crc/cli/README.md:15-16` was edited inside `## Purpose`, whereas the lane contract excludes `README.md` text outside the `## Public API` lines of newly added symbols (lane `F-DOCS` owns non-API README prose). Reverted `crc/cli/README.md` to `f8ed6dd` and added the `constants.py`/`pairs.py` note to `## Docs to update (lane F-DOCS)` above.
   - In `crc/core/README.md:130-145`, removed the dangling `(see Purpose)` reference and left the pre-existing `- KIND_LABELS:` line untouched so only the `## Public API` block for the newly added `crc/core/kinds.py` symbols (`Kind`, `KINDS`, `KIND_NAMES`, `ALL_KINDS`, `EXPLICIT_KINDS`, `KINDS_BY_NAME`) is added.
2. **Fixed (`tests/helpers_ag_cli_added.py` compatibility in `tests/test_core_kinds.py`):**
   - `test_parser_choices_keep_their_order`, `test_expansion_constants_keep_their_order`, `test_pair_rules_keep_their_content`, and `test_report_labels_are_unchanged` previously compared derived values against hardcoded 10-kind literals without filtering `added_table.added_kinds()`, which would fail if a future kind were added via `tests/helpers_ag_cli_added.py`. Updated those four tests in `tests/test_core_kinds.py` to assert both exact derivation from `KINDS` (`[*KIND_NAMES, "all"]`, `ALL_KINDS`, `EXPLICIT_KINDS`, `SUPPORTED_CLOUDS`, `KIND_LABELS`) and exact match of the non-`added_kinds()` entries to the 10 oracle kinds, plus consistency between `ADDED_RESOURCES` and `KINDS_BY_NAME`.

### Checklist Verification

1. **Every item of the lane task done and true:**
   - `crc/core/kinds.py` defines `@dataclass(frozen=True, slots=True) class Kind` (`name`, `label`, `in_all`, `clouds`, `unsupported`, `explicit_only` property, `unsupported_message()` method, and `__post_init__` check that `clouds` and `unsupported` are set together) and the frozen `KINDS` tuple (all 10 resource kinds in `--resource` choices order, whose `in_all=True` subsequence is the exact `--resource all` order), plus `KIND_NAMES`, `ALL_KINDS`, `EXPLICIT_KINDS`, and `KINDS_BY_NAME`.
   - `crc/cli/args.py:28` derives `--resource` choices as `[*KIND_NAMES, "all"]`; `--resource` help text remains hand-written in `crc/cli/args.py:30-35` (stated in the review summary: prose with a different order and per-kind annotations, checked byte-for-byte by parity tests).
   - `crc/core/selection.py:15-16` derives `RESOURCES = ALL_KINDS` and `EXTRA_RESOURCES = EXPLICIT_KINDS`; `crc/cli/constants.py:6` derives `RESOURCES = list(_RESOURCES)`.
   - `crc/cli/pairs.py:8-29` derives `SUPPORTED_CLOUDS`, `AWS_ONLY_RESOURCES`, and `_unsupported_message()` from `KINDS` and `KINDS_BY_NAME`.
   - `crc/core/engine.py:23` derives `KIND_LABELS = {kind.name: kind.label for kind in KINDS}`.
   - `tests/test_core_selection.py:145` derives `SUPPORTED_ON = {kind.name: kind.clouds for kind in KINDS if kind.clouds is not None}` instead of hardcoding the dict.
   - `tests/test_core_kinds.py:161-166` (`test_every_supported_pair_has_a_route_and_every_route_a_supported_pair`) verifies that every supported `(cloud, kind)` pair in `KINDS` has a route in `bridge.TABLES` and every route in `bridge.TABLES` is a supported pair in `KINDS`.
   - `ARCHITECTURE.md` add-a-cleaner updates are listed under `## Docs to update (lane F-DOCS)`.
2. **Byte-identical CLI/runtime behaviour & untouched parity/Jenkins contracts:**
   - Ran `python3 crc.py --help` on `HEAD` and on base `f8ed6dd`: byte-identical (`8,432` bytes).
   - `tests/test_jenkins_contract.py` (142 passed) and all `tests/test_*_parity.py` suites are completely untouched in `git diff f8ed6dd..HEAD` and pass.
3. **No check or test weakened; locked files untouched; negative test of new check:**
   - `tests/legacy/*.txt`, `tests/archtest/safety_lock.json`, `tests/archtest/frozen_inputs.json`, and `docs/refactor/BUGS.md` are untouched.
   - Locally mutated `Kind("ip", ...)` in `crc/core/kinds.py` first to `clouds=("aws", "azure", "oci")` and then to `clouds=("aws", "azure")`: `test_every_supported_pair_has_a_route_and_every_route_a_supported_pair` failed immediately with `AssertionError: supported pair without a route: [('oci', 'ip')]` and `AssertionError: route of a pair the kind table does not support: [('gcp', 'ip')]`. Reverted both local mutations.
4. **Only owned files changed:**
   - Changed files (`git diff --name-only f8ed6dd..HEAD`): `crc/cli/args.py`, `crc/cli/constants.py`, `crc/cli/pairs.py`, `crc/core/README.md` (`## Public API` lines of `kinds.py` only), `crc/core/__init__.py`, `crc/core/engine.py` (`KIND_LABELS` only), `crc/core/kinds.py`, `crc/core/selection.py`, `docs/archive/reviews/F-KIND.md`, `tests/archtest/test_count_floor.txt`, `tests/test_core_kinds.py`, `tests/test_core_selection.py`.
5. **Size limits & README Public API sync:**
   - All touched non-test files are `<= 250` lines (max `198` lines in `crc/core/__init__.py`, `195` in `crc/core/README.md`, `128` in `crc/cli/args.py`, `98` in `crc/core/engine.py`, `88` in `crc/core/kinds.py`, `29` in `crc/cli/pairs.py`, `24` in `crc/core/selection.py`, `6` in `crc/cli/constants.py`; `tests/test_core_kinds.py` is `175` lines).
   - All functions in touched `crc/` modules and `tests/test_core_kinds.py` are `<= 60` lines (max `53` lines in `_add_filter_args`, `28` in `test_expansion_constants_keep_their_order`, `21` in `_run_one`, `5` in `Kind.unsupported_message`).
   - `ARCH-002` and `ARCH-004` pass (29/29).

### Gates

Ran `pip install -r requirements.txt -r requirements-dev.txt -c constraints.txt && make check`:
- `ruff check .`: All checks passed!
- `ruff format --check .`: 372 files already formatted
- `mypy`: Success: no issues found in 371 source files
- `lint-imports`: Contracts: 5 kept, 0 broken
- `pytest -q -n auto`: **44,612 passed, 1 skipped in 58.08s** (`44,613` collected, up from `44,597` at `f8ed6dd`, `+16`)
- `python3 -m tests.archtest.test_count check`: `ARCH-008: 44613 tests, floor 44613`
- Total `make check` runtime: **1m06.1s** wall clock

VERDICT: APPROVE
