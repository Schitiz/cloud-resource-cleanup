## Coding summary

Lane AG-CLI (branch `ag/cli`): let agents add CLI flags and resource kinds safely, and pin the
Jenkins contract. Only tests and test helpers changed; nothing under `crc/**`, no docs besides this
file, no guardrail file except `tests/archtest/test_count_floor.txt` (raised with
`make raise-test-floor`).

**What is routed / adapters deleted or shimmed:** nothing. No route, adapter or `crc/**` file was
touched (lane scope). Unrouted kinds keep their path; there is no partial state to finish.

**How the CLI parity tests now reach the cleaners:** unchanged (`tests/helpers_cli_routes.FakeCleaners`
patches `bridge.build_registry` / `bridge.build_notifiers`). New: `tests/helpers_ag_cli_jenkins.py`
runs `crc.cli.main.main` on each production command with `FakeCleaners`, fake `WebClient` /
`InfluxDBClient`, a fake scan and notifier, and a scrubbed environment (no cloud call, no
credentials).

### 1. Additive compatibility contract

One table, `tests/helpers_ag_cli_added.py` (`ADDED_FLAGS`, `ADDED_CHOICES`, `ADDED_RESOURCES`,
`RESOURCE_HELP`, all empty today). The comparison helpers are in `tests/helpers_ag_cli_args.py`.

- `tests/test_cli_args_parity.py`: all 4,000+ exact comparisons with the oracle (`crc_main.txt`)
  stay (result dict and key order, exit code, usage, error and help text, validators). The new
  parser is compared after `strip_additions` removed only the flags and choices listed in ADDED, so a
  listed addition cannot hide a change of an oracle flag. `test_raw_parser_definition_matches_main`
  now calls `check_additions`: every oracle action keeps option strings, dest, nargs, const,
  default, type, required, metavar, choices (oracle order kept, extras must be listed) and help
  (only the declared help may differ, and only for an option with a listed new choice), in the
  same order; an extra flag must be in `ADDED_FLAGS` with its expected default and help and must be
  optional; parser fields, `_defaults` and mutually exclusive groups are compared. New tests:
  listed flags parse with their default, help and example value forms; listed resource choices
  parse; `--help` lists them; a new long flag may not turn a unique abbreviation of an oracle flag
  (`--dry`, `--f`) ambiguous (`allow_abbrev` is part of the contract); self-tests prove an unlisted
  flag or resource choice fails with `add it to the ADDED table in tests/helpers_ag_cli_added.py
  (with default and help)`, a listed one passes, and a changed default, removed choice, retyped
  flag, renamed dest or removed flag always fails.
- `tests/test_cli_bridge_parity.py`: `test_route_tables_route_every_oracle_kind_and_only_added_extras`
  (replaces `test_route_tables_route_the_aws_kinds`, which asserted the exact dict): the set of
  clouds is unchanged, every oracle kind is still routed, any extra routed pair must be in
  `ADDED_RESOURCES`, and an ADDED pair that is not routed fails as stale. Same asserts as before
  for `is_routed_kind` / `route_for`.
- `tests/test_cli_main_parity.py`: the new-side run (`run_new`) and the script entry point test
  (`test_script_entry_point_matches_oracle`, which runs `crc.py` in a subprocess) strip the listed
  additions before comparing with the oracle, so usage and error text stay exact. With an empty table the
  entry-point test still runs `python crc.py` itself. `install_routed_fakes` no longer demands an
  oracle `ROUTED_CALLS` entry for an ADDED pair; new
  `test_added_resources_reach_their_cleaner_through_main` runs each ADDED pair through `main()` and
  checks the cleaner is reached with the flags (empty today, so it collects nothing).
- `tests/test_core_selection.py` (resource expansion only): `test_all_expansion_order_follows_crc_py`
  keeps the oracle `CLOUDS` and `RESOURCES` order and requires every extra to be in
  `ADDED_RESOURCES` (`in_all` for `--resource all`); `EXTRA_RESOURCES` is pinned too. One edit
  beyond that test, needed so an added kind does not fail the oracle grid: the parametrization of
  `test_exhaustive_grid_matches_crc_main` takes the oracle kinds (`ORACLE_KINDS`, identical to
  today's list).

**Throwaway experiment (not committed; `crc/**` and the ADDED table reverted afterwards):** added
`--fake_flag` and a `fake_kind` resource (choice in `args.py`, `Route(_ip)` in `routes/aws.py`,
`EXTRA_RESOURCES` in `crc/core/selection.py`).
1. ADDED empty: `check_additions` failed with `the parser has a flag ['--fake_flag'] (dest
   'fake_flag') that the oracle crc_main.txt does not; add it to the ADDED table in
   tests/helpers_ag_cli_added.py (with default and help)`; the route test with `routed pairs
   [('aws', 'fake_kind')] are not in the oracle; add it to the ADDED table ...`; the selection test
   with `extra resources ['fake_kind'] differ from ADDED_RESOURCES; add it to the ADDED table ...`;
   the abbreviation test with `--f meant ['filter_tags'], now ['fake_flag', 'filter_tags']: a new
   long flag must not start with '--f'; pick another name` (so the flag was renamed
   `--zz_fake_flag`).
2. ADDED filled (flag with an example, `AddedResource("fake_kind", ("aws",))`): args, bridge-route,
   selection, main parity (8,000+ cases and the script entry point), crc parity and the Jenkins
   contract were green (30,898 passed). The only red tests were genuine requirements of a new kind, not
   oracle comparisons: `no report label for resource kind 'fake_kind'` (`KIND_LABELS` in
   `crc/core/engine.py`, surfaced by the new main test; fixed in the experiment) and
   `test_every_routed_pair_has_a_registered_cleaner` (the experiment registered no cleaner).

### 2. Jenkins contract

`tests/test_jenkins_contract.py` (142 tests) reads `tests/fixtures/jenkins_commands.txt` (47
commands, unedited; `$RESOURCE_GROUP` / `${AWS_JENKINS_SLAVE}` are substituted from fixed test
values, as the Jenkins shell would). Per command: shlex split; `get_argparser`; `read_options`,
`check_tokens`, `check_flag_combinations`, `resolve_targets`, `validate_values`, `check_scan_tag`,
`validate_targets`; `route_for` for every pair; `main()` offline asserting exit code 0 (scan command:
`SystemExit(0)`), the (cloud, kind) pairs that ran, operation, dry run, the options each fake cleaner
received, the `MAX_AGE` value seen while it ran and its reset afterwards, the Slack channel passed to
the notifiers, the scan tag, and the number of Slack / Influx clients built. Expected data is frozen
in `tests/helpers_ag_cli_jenkins_expected.json` (keyed by index plus a hash of the command text, so
a refreshed fixture without refreshed data fails). A second test derives flags independently of the
JSON (`ast.literal_eval` of the argv values, dry run, channel, `MAX_AGE`). Proof it bites: with
`age` dropped from the AWS keypair route options, 4 tests failed (the two keypair commands, in both
the frozen and the independent test).

### Test count

Before 44,415 (floor 44,415); after 44,569 (+154: 142 contract tests, 12 added args/bridge/main
tests). The floor is raised to 44,569 in `tests/archtest/test_count_floor.txt`.

## Owner action

None required. If another lane also raises `test_count_floor.txt`, the integrator keeps the larger
value. Optional: when the triggers repo changes, refresh `tests/fixtures/jenkins_commands.txt` and
regenerate `tests/helpers_ag_cli_jenkins_expected.json` (it is data; review the diff as a contract
change).

## New bugs

None found in `crc/**`. Notes for the docs lane (AG-DOCS): `AGENTS.md` ("Workflow: change a CLI
flag") and `crc/cli/README.md` (Extension Rules 1 and 3) should now name
`tests/helpers_ag_cli_added.py` as the place to list a new flag, choice or kind, and say that a new
kind also needs a `KIND_LABELS` entry in `crc/core/engine.py` and a registered cleaner.

## Left over

Nothing planned is left. Not covered: a new `--cloud` choice (the route-table test fails on a new
cloud on purpose), and `tests/test_cli_crc_parity.py` (not in this lane) is unchanged and still
exact against the oracle.

## Round 1 (Argon)

### Findings & Fixes Applied in Review

1. **`strip_additions` over-stripping fixed (`tests/helpers_ag_cli_args.py`):**
   - Previously, `strip_additions(new, old)` removed *any* non-oracle action (`previous is None`) whether or not it was listed in `ADDED_FLAGS`, and unconditionally overwrote `action.choices = previous.choices` and `action.help = previous.help` on every oracle action before `parse_args()`. That meant the 600+ `_compare()` cases in `test_cli_args_parity.py` and the 8,000+ cases in `test_cli_main_parity.py` ran with the oracle's choices and help copied onto `new` (leaving only `test_raw_parser_definition_matches_main` to catch choice/help regressions).
   - Tightened `strip_additions` so it removes an action only when `_flag_of(action) is not None` (explicitly listed in `ADDED_FLAGS`) and removes only choices listed in `added_choices(action.option_strings)` (restoring `previous.help` only when `action.help` matches the listed `ADDED` help). With an empty `ADDED` table, `strip_additions` now leaves the parser untouched.
2. **`test_added_resource_choices_parse_and_are_listed_in_help` (`tests/test_cli_args_parity.py`) & route-table self-test (`tests/test_cli_bridge_parity.py`):**
   - Added the missing `-h` assertion when `RESOURCE_HELP is not None`, asserted that `strip_additions` leaves unlisted flags and choices in place, added `test_unlisted_or_missing_route_fails_route_table_check` in `tests/test_cli_bridge_parity.py`, and passed `--resource_group rg --project_id proj` in `test_added_resources_reach_their_cleaner_through_main` so future Azure/GCP added kinds with prechecks also work.
3. **Independent Jenkins contract flag checks (`tests/test_jenkins_contract.py`) & `test_core_selection.py` cleanup:**
   - Added `--detach_age` and `--name_regex` to `LITERAL_FLAGS` in `tests/test_jenkins_contract.py` and removed the `if name in options` guard in `test_command_reaches_its_cleaner_with_the_flags` (except `(snapshot, age)` which maps to `age_days`), so dropping an option key from a route fails the independent check as well as the frozen-JSON check.
   - Reverted an unrelated 4-line formatting diff in `tests/test_core_selection.py:run_crc_main` and pinned `list(RESOURCES[: len(oracle.RESOURCES)]) == oracle.RESOURCES` in `test_all_expansion_order_follows_crc_py`.

### Verification & Gates

1. **Task completeness & throwaway local experiments (reverted before commit):**
   - Added unlisted `--zz_fake_flag` and `fake_kind` (`crc/cli/args.py`, `crc/cli/routes/aws.py`, `crc/core/selection.py`, `crc/core/engine.py`): `test_cli_args_parity.py`, `test_cli_bridge_parity.py`, and `test_core_selection.py` all failed with `add it to the ADDED table in tests/helpers_ag_cli_added.py (with default and help)`.
   - Listed both in `tests/helpers_ag_cli_added.py`: `test_cli_args_parity.py`, `test_core_selection.py`, `test_jenkins_contract.py`, `test_cli_bridge_parity.py` (route check), and `test_cli_main_parity.py` (`test_script_entry_point_matches_oracle` and `test_added_resources_reach_their_cleaner_through_main`) all passed.
   - Broke `crc/cli/routes/aws.py:_disk` by dropping `detach_age`: `tests/test_jenkins_contract.py` failed on both AWS disk Jenkins commands (`11-d68c09d92b` and `12-3a215916af`).
2. **No CLI/behaviour change:** `crc/**` and `crc.py` are untouched; `python3 crc.py --help` output is unchanged.
3. **No weakened checks or touched locks:** `tests/archtest/safety_lock.json`, `update_safety_lock.py`, the 5 hash-locked safety tests, `tests/legacy/*.txt`, `requirements.txt`, `tests/archtest/frozen_inputs.json`, and `tests/fixtures/jenkins_commands.txt` are untouched. `test_route_tables_route_the_aws_kinds` was replaced by `test_route_tables_route_every_oracle_kind_and_only_added_extras` + `test_unlisted_or_missing_route_fails_route_table_check`.
4. **Lane ownership:** Only `docs/archive/reviews/AG-CLI.md`, `tests/archtest/test_count_floor.txt`, `tests/helpers_ag_cli_{added,args,jenkins}.py`, `tests/helpers_ag_cli_jenkins_expected.json`, `tests/test_cli_{args,bridge,main}_parity.py`, `tests/test_core_selection.py`, and `tests/test_jenkins_contract.py` changed in `a0b3d09..HEAD`.
5. **Size & API limits:** New `.py` files are `60`, `215`, `156`, and `138` lines (`<= 250`); longest function in new files is `run_command` (`52` lines, `<= 60`); `ARCH-002` README Public API check is green.
6. **`make check`:** `ruff check .`, `mypy` (371 files), `lint-imports` (5 contracts), `pytest -q -n auto`, and `ARCH-008` all green: **44,569 passed, 1 skipped in 52.94s** (total `make check` wall time **59.94s**; collected **44,570** tests, floor raised to **44,570**).

VERDICT: APPROVE
