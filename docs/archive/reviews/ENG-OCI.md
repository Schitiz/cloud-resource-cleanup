## Coding summary

Lane ENG-OCI (branch `eng/oci`): the OCI `disk` and `vm` (delete and stop) pairs run through `crc.core.engine`. Green partial state: `spot_instances` keeps the legacy path (see Owner action).

**Routed**: `crc/cli/routes/oci.py` has `disk` (`NotifyMode.REPORT_THEN_RERAISE`, as `delete_disks` reported before it re-raised) and `vm` (`NotifyMode.REPORT`; `--resource_states` becomes `instance_state` for delete only). The bridge, dispatch, `vm_ops`, `resource_ops` and `notify` are untouched.

**Cleaner changes (`crc/oci/**`)**: ENG-1's round 1 found that routed cleaners lost dry-run behaviour, because the engine never calls `apply()` in a dry run. Both OCI cleaners are built by their factory with `engine=True`, which makes a dry-run `plan()` (a) log the `ACTION would_delete` / `would_stop` lines per region, before the REGION line, so `RESULT selected=` and the ACTION lines match the legacy run, and (b) return candidates whose `id` is the display name, because `Report.from_plan` reads the id and the legacy adapters reported names to Slack and Influx (not OCIDs). Directly built cleaners (`engine=False`, the adapters and the existing unit tests) behave as before. `DiskCleaner` also exposes `partial_succeeded` (names listed so far in a dry run, names deleted so far in `apply()`), which the bridge reports before it re-raises. Attachment helpers moved to `crc/oci/disk/attachments.py` (ARCH-004).

**Adapters deleted or shimmed**: none. `Disk` and `VM` stay as they are: the oracle `tests/legacy/crc_main.txt` imports them, their module parity tests are thousands of cases, and `scan_instances_with_tag` uses `crc.oci.vm.VM`. They are dead for production `disk` / `vm` and are left for the cleanup lane. `SpotVM` is untouched (hash-locked test, still used in production).

**How the CLI parity tests reach the cleaners**: `tests/helpers_cli_routes.FakeCleaners` registers a fake for every pair of `bridge.TABLES`, so `oci` / `disk` and `oci` / `vm` reach a recording fake cleaner. To keep the other lanes' merges simple the per-cloud oracle call tables are new files, `tests/routed_calls_<cloud>.py` (here `tests/routed_calls_oci.py`: the oracle method, the option keys in oracle argument order, `None` for arguments the OCI adapters never read, and the stop method); `test_cli_main_parity.py` loads `routed_calls_<cloud>` by name (`cloud_calls`, `routed_call`, `strip_unused_args` now work for any cloud; AWS behaviour is unchanged). `tests/test_cli_bridge_parity.py` only had its expected route table updated (`"oci": ["disk", "vm"]`). `test_cli_crc_parity.py` and `test_cli_args_parity.py` need no change (the `CRC` methods are still there).

**New `tests/test_cli_bridge_oci.py` (78 tests)**: runs the oracle `CRC` with the real `Disk` / `VM` adapters and the bridge (`dispatch._run_handler`) with the real `DiskCleaner` / `VmCleaner` from their registered factories on the same fake SDK API (2 regions, skipped, young, attached, failing-delete and STOPPED resources), dry run and real run, 4 Slack/Influx modes, and a second region that is fine, raises a connectivity error, or raises an unexpected error. It compares the run-log lines (RUN START, ACTION in order, SKIPPED, ERRORS, FAILED, RESULT, REGION as a sorted set), all other log records, Slack calls and recipients, Influx points, stdout, the raised exception, and the mutating and listing SDK calls. A non-vacuity test asserts ACTION lines, display names in Slack and Influx and that a real run mutates; with `engine=False` 39 of the 78 tests fail.

**`tests/test_oci_spot_vm_engine.py` (16 tests)**: Cleaner-based copy of the locked `tests/test_oci_spot_vm.py` (all 15 cases: preemptible, OKE and pool guard, attached and detached volumes, list failure, volume exception tags, dry run without API, filter tags, positive age, terminate-wait-delete order, no terminate when attachments fail, volume delete after a failed wait). For the owner to swap in and relock; the locked file and `safety_lock.json` are untouched.

**BUGS.md / CLEANUP_SAFETY.md**: BUG-408 (low group end, fixed in ENG-OCI: plan-all-regions-before-apply for OCI disk and vm), counts line updated; BUG-408 added to the engine path bullet of `CLEANUP_SAFETY.md`.

**Test count**: before 43820 (floor at the start of the lane), after 43914 (floor raised with `make raise-test-floor`). `make check` (ruff, mypy strict, lint-imports, ARCH-001..009, SAF-LOCK) is green.

**Owner actions**
- `oci` / `spot_instances` is not routed. Under `--cloud all` the legacy handler `dispatch._spot_instances` logs a warning and returns between RUN START and RESULT (SAF-037), with no Slack or Influx. Once a pair has a route `dispatch._run_handler` skips the handler, so a routed pair would run (and notify) under `--cloud all`. `Route.precheck` can only raise, not skip. The bridge needs a way to skip a pair: for example `Route.skip: Callable[[Any, Options, Targets], bool]` (log the warning and return True), checked in `run_routed` right after `precheck`; the same gap blocks GCP `spot_instances`. Then route it with an options builder `{filter_tags, exception_tags, notags, age, custom_age_tag_key}` and `NotifyMode.REPORT` (the report already carries the `Disk` section of leftover volumes with `notify_empty` False), and add the OCI `spot_instances` cases to `tests/test_cli_bridge_oci.py`.
- Review, swap in and relock `tests/test_oci_spot_vm_engine.py`.
- Cleanup lane: `Disk` and `VM` adapters and their `CRC` branches are unused in production for OCI `disk` and `vm` (`delete_disks` and `delete_vm` / `stop_vm` stay for Azure and GCP); the oracle imports them, so a stand-in is needed (`provide_legacy_*`).
- Docs lane: `crc/core/README.md` still says `crc/cli` runs the adapter classes.
- Merge note: `tests/test_cli_bridge_parity.py` (`"oci": ["disk", "vm"]`) and the `bridge.TABLES` loops in `test_cli_main_parity.py` are the only shared test lines edited.

## New bugs

- `crc/oci/disk/cleaner.py` `plan()` (real run, error in a later region): the legacy `delete_disks` reported the volumes of earlier regions to Slack and Influx before it re-raised; routed, nothing was deleted yet, so the report is empty (covered by BUG-408, fewer deletes).
- `crc/oci/vm/cleaner.py:_is_old` / `crc/oci/disk/decide.py`: unchanged quirks (not touched). The routed cleaner uses `options.get("age") or {}` where the adapter passes `age` as is; a `None` age behaves as an empty age in both (every resource old enough, SAF-006), so no difference was found.

## Round 1 (Argon)

Scope reviewed: `git diff 6a98441..HEAD` on branch `eng/oci` (lane `ENG-OCI`).

### Findings & fixes made in review

1. **Prepared `SpotVmCleaner` for engine dry-run parity and added `spot_instances` bridge parity tests** (`crc/oci/spot_vm/cleaner.py`, `crc/oci/spot_vm/README.md`, `crc/cli/routes/oci.py`, `tests/test_cli_bridge_oci.py`, `tests/test_oci_spot_vm_engine.py`):
   - Leaving `"spot_instances"` out of `crc/cli/routes/oci.py::ROUTES` is required because `dispatch._spot_instances` warns and returns without Slack/Influx under `--cloud all` (`SAF-037`) and `Route.precheck` cannot skip a pair without editing `crc/cli/bridge.py` / `crc/cli/routes/__init__.py` (which are off-limits in this lane).
   - However, `SpotVmCleaner` built by `build_spot_vm_cleaner` still lacked `engine=True`: when run through `crc.core.engine` in a dry run (`engine.run` skips `apply()`), it omitted per-region `ACTION would_delete` lines (for both instances and leftover volumes), reported `selected=0` in `RESULT`, and left `Candidate.id` as the instance OCID instead of the display name in `Report.from_plan`.
   - Added `engine: bool = False` to `SpotVmCleaner.__init__` (passed as `engine=True` by `build_spot_vm_cleaner`), added `_spot_instances` options builder to `crc/cli/routes/oci.py`, and added `spot_instances` to `KINDS` in `tests/test_cli_bridge_oci.py` (now 104 tests across `disk`, `vm` delete, `vm` stop, and `spot_instances`). Synced `crc/oci/spot_vm/README.md` and the SAF list in `tests/test_oci_spot_vm_engine.py`.

### Checklist verification

1. **CLI result parity for all OCI pairs (`disk`, `vm` delete/stop routed in `ROUTES`; `spot_instances` tested via `Route(_spot_instances)`)**: selection, mutations and order within each region, `RUN START` / `RESULT` lines, `Service` / `init_logging` startup, Slack text and recipients, Influx points, console and log lines, exceptions and exit codes, `NotifyMode.REPORT_THEN_RERAISE` (`disk` via `partial_succeeded`), and `--dry_run` non-mutation match the legacy path; the only behaviour change is plan-all-regions-before-apply, recorded in `BUG-408` (`docs/refactor/BUGS.md`) and one clause in `CLEANUP_SAFETY.md`.
2. **Parity tests non-vacuous**: `test_cli_main_parity.py` (via `tests/routed_calls_oci.py` and `FakeCleaners`), `test_cli_bridge_oci.py` (104 tests running real `DiskCleaner`, `VmCleaner`, and `SpotVmCleaner` against `oracle.CRC`), `test_cli_bridge_parity.py`, `test_cli_crc_parity.py`, `test_cli_args_parity.py`, `test_cli_dispatch_fix.py`, `test_core_selection.py`, and all `test_oci_*_parity.py` files reach real or recording fake cleaners and assert the oracle facts.
3. **Hash-locked safety tests**: all 5 locked test files and `tests/archtest/safety_lock.json` are untouched and passing; `tests/test_oci_spot_vm_engine.py` (16 tests) covers all 15 test cases and all SAF IDs (`SAF-040`, `SAF-041`, `SAF-043`, `SAF-044`, `SAF-045`, `SAF-046`) locked to `tests/test_oci_spot_vm.py`.
4. **Protected files**: no oracle (`tests/legacy/*.txt`), archtest (`tests/archtest/*.py`), guardrail (`AGENTS.md`, `ARCHITECTURE.md`, `.cursor/**`, `pyproject.toml`, `Makefile`), `requirements*.txt`, or shared CLI bridge/dispatch file was edited; `test_count_floor.txt` raised to `43940` via `make raise-test-floor`.
5. **Limits & README sync**: all touched non-legacy, non-test files are at most 250 lines and functions at most 60 lines (`ARCH-004`); all package READMEs (`crc/cli`, `crc/cli/routes`, `crc/oci`, `crc/oci/disk`, `crc/oci/vm`, `crc/oci/spot_vm`) are in sync (`ARCH-002`).

### Gates & test count

- `python3 -m ruff check .`: passed
- `python3 -m mypy`: passed (343 source files)
- `lint-imports`: passed (5 contracts kept, 0 broken)
- `python3 -m pytest -q -n auto`: **43940 passed in 60.21s** (`make check` wall time ~74s)
- `python3 -m tests.archtest.test_count check`: `ARCH-008: 43940 tests, floor 43940`

VERDICT: APPROVE
