## Coding summary

Lane ENG-0 (branch `eng/bridge`): the bridge from the CLI to `crc.core.engine`, with AWS `keypair` routed end to end as the pattern. Partial state, green: everything else keeps the legacy path.

**Routed**: `aws` / `keypair` only. `crc/cli/routes/aws.py` holds `ROUTES`; `azu.py`, `gcp.py`, `oci.py` exist with empty tables. `crc/cli/bridge.py` (`route_for`, `is_routed_kind`, `run_routed`, `build_registry`, `build_notifiers`) builds the `RunContext` and a one pair `Selection` from the parsed flags and calls `crc.core.engine.run` with the registered cleaner. `dispatch._run_handler` checks the route first, then the legacy handler; `logger.begin` / `finish` still wrap every pair, so RUN START / RESULT, validate_targets, the cloud-all skip and exit codes are unchanged. The Slack then Influx notifiers are the existing `crc.notify.SlackNotifier` (fail open False) and `InfluxNotifier` (fail open True); `build_notifiers` adds each only when its client is set, and none when `Route.notify` is False (the place for `vpc`, BUG-084).

**Adapters deleted or shimmed**: `crc/aws/keypairs/adapter.py` (`KeyPairs`), `KeyPairRuntime`, `CRC.delete_keypairs`, the `_keypair` handler and the `KeyPairs` re-export of `crc.py` are deleted. No shims: Disk, SpotInstanceRequests and the azure/gcp/oci SpotVM adapters are untouched, so the 5 hash-locked tests are untouched and pass. The keypair cleaner's `plan()` now logs the `would_delete` actions per region in a dry run (the engine never calls `apply()` then), which keeps the dry-run RESULT counters identical.

**How the CLI parity tests reach the cleaners**: `tests/helpers_cli_routes.py` (`FakeCleaners`) registers a recording fake cleaner for every routed pair in a `Registry` and patches `bridge.build_registry` (and `bridge.build_notifiers` to no notifiers), both looked up at call time. `test_cli_main_parity.py` (`ROUTED_CALLS`, `install_routed_fakes`) records the same `crc.delete_keypairs <cloud> [name_regex, exception_regex, age]` event from `context.options` and the same `crc_fail` error, so the oracle events compare equal and the table is not vacuous. `test_cli_logger.py`, `test_cli_logging_init.py`, `test_cli_dispatch_fix.py` and `test_core_selection.py` use the same seam. `tests/test_cli_bridge_parity.py` (new) runs the oracle `CRC.delete_keypairs` and `bridge.run_routed` on the same fake Slack and Influx clients over dry run x Slack mode x Influx mode x id sets and error cases: Slack calls, Influx calls, stdout and error are equal. `tests/test_aws_keypair_parity.py` now drives the Cleaner through `engine.run` against the oracle (`aws_keypairs.txt`); the delete order and delete calls are equal, later-region listing errors only ever delete less.

**Oracle note**: `tests/legacy/crc_main.txt` does `from crc.aws.keypairs import KeyPairs` at import. It cannot be edited, so the parity tests that load it call `tests.helpers_cli_routes.provide_legacy_keypairs()` (an empty stand-in class, replaced by fakes before use) and the subprocess `RUN_ORACLE` in `test_cli_main_parity.py` sets it. Every future adapter deletion needs the same stand-in for its name.

**BUGS.md / CLEANUP_SAFETY.md**: one new row BUG-383 (low group end, fixed in ENG-0) and one bullet under "Failure handling" in CLEANUP_SAFETY.md (there is no explicit plan/apply section); nothing else edited in either.

**Test count**: before 43075 (floor), after 43077; floor raised with `make raise-test-floor`.

**Owner actions**
- Review and swap in/relock the Cleaner-based copies of the 5 locked tests: not written in this lane (see "Left to do").
- Docs lane: `crc/core/README.md` still says the CLI runs the adapters and engine wiring is deferred; `docs/refactor/STATUS.md` lines about `KeyPairs` are stale; PLAN.md untouched.

## Left to do (not done in this lane, time)

- Route AWS `ip`, `kms`, `snapshot` (the "if time allows" part). Pattern: `crc/cli/README.md`, Extension Rules, item 3. Snapshot needs `Route.notify`/label handling: today's `Snapshot` branch prints a message and sends no Slack or Influx (BUG-009, BUG-084), so route it only with `notify=False` and the same print.
- The 5 `tests/test_<name>_engine.py` Cleaner copies of the locked safety tests (aws Disk, aws SpotInstanceRequests, azure/gcp/oci SpotVM). They are not needed yet because those adapters were not touched; the locked tests still build the adapters and pass.
- The disk route will need `Route.precheck` for the AWS opt-in gate, and a decision for `delete_disks`, which sends Slack and Influx before it re-raises a `delete()` error, while the engine skips notifiers when `apply()` raises (difference to resolve in the disk lane).
- The Azure VM route also sends the NIC Slack message after the VM message (`notify_deleted_vm_via_slack`); the engine report has to carry it.

## New bugs

- `crc/cli/notify.py:~113`: `CRC.notify_deleted_keypair_via_slack` is now dead code in production (kept only because `test_cli_crc_parity.py` still exercises it).
- No other new bugs found.

## Round 1 (Argon)

Scope reviewed: `git diff 0240820..HEAD` on branch `eng/bridge` (lane `ENG-0`).

### Findings & fixes made in review

1. **BLOCKING (fixed): Routed pairs no longer called `Service.__init__()` (`crc.service.init_logging("logs/crc.log")`)** (`crc/cli/bridge.py`, `tests/helpers_cli_routes.py`, `tests/test_cli_bridge_parity.py`, `tests/test_cli_logging_init.py`):
   - Deleting `KeyPairs(Service)` removed the `super().__init__()` (`Service.__init__`) call that every legacy adapter ran before its cleaner. Without it, a real CLI run of a routed pair never called `init_logging("logs/crc.log")`, never printed `Setting loglevel to logging: DEBUG`, never created `logs/crc.log` or attached the root `FileHandler`/`StreamHandler`, never released the held `RUN START` header via `run_log.logging_ready()` (`BUG-364`), dropped `INFO`/`DEBUG` lines (`RUN START`, `REGION`, `ACTION`, `SKIPPED`, `RESULT`), and triggered `logging.basicConfig()` on the first `logging.warning` call (`BUG-363`).
   - Added `init_run_logging()` in `crc/cli/bridge.py` (calling `Service()`) and called it in `run_routed()` right after `route.precheck` and before `engine.run`, matching the exact point `Service.__init__` ran in every legacy adapter. `FakeCleaners.install` in `tests/helpers_cli_routes.py` patches `bridge.init_run_logging` for fake-cleaner unit tests, `test_cli_logging_init.py::test_cli_path_with_init_logging_in_cleaner_adds_no_stray_handler` now exercises the real `bridge.init_run_logging()` path (instead of calling `init_logging` inside the test callback), and `test_cli_bridge_parity.py::test_bridge_reaches_the_cleaner_with_the_flags` asserts `crc.service.init_logging("logs/crc.log")` is called.
2. **BLOCKING (fixed): `tests/test_cli_args_parity.py` failed with 4,034 `ImportError`s when run in isolation** (`tests/test_cli_args_parity.py`):
   - `tests/test_cli_args_parity.py` loads `tests/legacy/crc_main.txt` in its `oracle` fixture (`from crc.aws.keypairs import KeyPairs`) without calling `provide_legacy_keypairs()`. It only passed under `pytest -n auto` when another CLI parity file happened to be imported first in the same worker. Added `provide_legacy_keypairs()` to `tests/test_cli_args_parity.py`.
3. **Test & factory tightening (fixed)** (`crc/aws/keypairs/cleaner.py`, `tests/test_aws_keypair_parity.py`, `tests/test_cli_main_parity.py`, `tests/test_cli_dispatch_fix.py`, `tests/test_core_selection.py`, `tests/README.md`):
   - `build_keypair_cleaner` in `crc/aws/keypairs/cleaner.py` now passes `options.get("name_regex")` and `options.get("exception_regex")` directly to `KeyPairCleaner` as `KeyPairs.delete()` did instead of eagerly wrapping them in `list(... or ())`.
   - Restored log parity assertion `assert new.logs == expected_logs(old.logs[:-1], LOG_BUGS, rules=RULES)` in `test_aws_keypair_parity.py::test_engine_matches_main` for all dry-run and single-region cases.
   - Asserted `context.dry_run` in `test_cli_main_parity.py::install_routed_fakes`, restored the `"keypair"` case in `test_cli_dispatch_fix.py::test_bug_017_cloud_all_real_crc_does_not_build_skipped_clouds`, removed dead `"delete_keypairs"` from `METHOD_KINDS` in `test_core_selection.py`, and listed `test_cli_bridge_parity.py` and `helpers_cli_routes.py` in `tests/README.md`.

### Checklist verification

1. **CLI result parity for routed `aws` / `keypair`**: selection, mutations and order within each region, `RUN START` / `RESULT` lines, `Service` / `init_logging` startup, Slack text, Influx points, log lines, exceptions and exit codes, `validate_targets`, and `--dry_run` non-mutation match the legacy path; the only behaviour change is plan-all-regions-before-apply, recorded in `BUG-383` (`docs/refactor/BUGS.md`) and one bullet in `CLEANUP_SAFETY.md`.
2. **Parity tests non-vacuous**: `test_cli_main_parity.py`, `test_cli_bridge_parity.py`, `test_cli_crc_parity.py`, `test_cli_args_parity.py`, and `test_aws_keypair_parity.py` all reach real or recording fake cleaners and assert the oracle facts.
3. **Hash-locked safety tests**: the 5 locked test files (`test_aws_disk.py`, `test_aws_spot_instance_requests.py`, `test_azu_spot_vm.py`, `test_gcp_spot_vm.py`, `test_oci_spot_vm.py`) and `tests/archtest/safety_lock.json` are untouched and passing (their adapters remain on the legacy path in this lane).
4. **Protected files**: no oracle (`tests/legacy/*.txt`), archtest (`tests/archtest/*.py`), guardrail (`AGENTS.md`, `ARCHITECTURE.md`, `.cursor/**`, `pyproject.toml`, `Makefile`, `docs/refactor/PLAN.md`, `docs/refactor/STATUS.md`), or `requirements*.txt` file was edited; `test_count_floor.txt` raised to `43078` via `make raise-test-floor`.
5. **Limits & README sync**: all touched non-legacy, non-test files are at most 250 lines and functions at most 60 lines (`ARCH-004`); all package READMEs (`crc/cli/README.md`, `crc/cli/routes/README.md`, `crc/aws/README.md`, `crc/aws/keypairs/README.md`, `tests/README.md`) are in sync (`ARCH-002`).

### Gates & test count

- `python3 -m ruff check .`: passed
- `python3 -m mypy`: passed (337 source files)
- `lint-imports`: passed (5 contracts kept, 0 broken)
- `python3 -m pytest -q -n auto`: **43078 passed in 53.94s**
- `python3 -m tests.archtest.test_count check`: `ARCH-008: 43078 tests, floor 43078`

VERDICT: APPROVE
