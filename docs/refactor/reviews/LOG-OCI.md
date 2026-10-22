## Coding summary

Rung LOG-OCI (OCI lane of the LOG family, contract in `docs/refactor/LOGGING.md`). Log text and
levels only: nothing selected, deleted, stopped, posted or written differs, no CLI flag, no exit
code, SDK call order unchanged.

Files changed:

- `crc/oci/_runlog.py` (new, private): glue to `crc.core.runlog` (`region_started/done/skipped`,
  `record_action/skip/failure`). `monotonic` is bound by name so the spot VM terminate-wait tests
  that patch `time.monotonic` are not disturbed.
- `crc/oci/vm/{cleaner,adapter}.py`, `crc/oci/disk/{cleaner,adapter}.py`: age-check freeform tag
  dict `logging.info(tags)` -> `logging.debug` (BUG-353 disk, BUG-358 vm and disk); REGION per walked
  region (`scanned` = resources listed, `selected` = candidates); `region_skipped` where the
  connectivity error skips the region; one ACTION per resource in `act()` / `remove()` (kind
  `deleted|stopped`, or `would_*` in a dry run); `skip()` with reasons `state`, `attached`,
  `exception_tag`, `filter_mismatch`, `too_young` from `decide()`; `fail()` where the per-resource
  error line is logged. `VmCleaner.apply()` in a dry run emits the `would_*` ACTION lines.
- `crc/oci/spot_vm/{decide,leftovers,cleaner,adapter}.py`: skip reasons (`state`, `not_preemptible`,
  `oke_member`, `exception_tag`, `filter_mismatch`, `too_young`, `leftover_exception_tag`);
  "Skipping leftover volume ..." INFO -> DEBUG; REGION / region_skipped; ACTION for each instance
  and each leftover volume (volume lines have `region=-`, `name=-`); `fail()` for attachment-list,
  poll, timeout, get_volume, delete_volume and per-instance errors. `SpotVM._process` gains an
  optional `region` argument and returns 1/0 (selected); no behaviour change.
- `crc/oci/README.md`: module list and logging invariant.
- Tests: `tests/helpers_log_fix.py` (rules `BUG-353`, `BUG-358`; `BUG-361`/`BUG-362` are identity
  rules because new lines only appear in an attached run), `tests/test_oci_{vm,disk,spot_instances}_parity.py`
  (every `logs` comparison goes through `expected_logs(old.logs, BUGS)`; new
  `test_*_diverges_from_oracle` cases assert oracle != new, text and calls equal, only DEBUG
  levels differ), `tests/test_oci_runlog.py` (new: exact REGION / ACTION / SKIPPED / ERRORS /
  FAILED / RESULT lines for vm, disk and spot VM adapters and cleaners; dry run and real run,
  a failure, a skipped region, no run means no new lines).

Bug IDs handled: BUG-353 (OCI tag dict level), BUG-358 (OCI vm and disk tag dumps; also the OCI
per-resource "Skipping leftover volume" line, tagged BUG-358 in the helper), BUG-361 (REGION per
region, `region_skipped`), BUG-362 (`fail()` calls). BUG-356/357/359/360 are other lanes.

Test count: 42256 before (at 7437ac5), 42276 after. `make check` green (ruff, mypy, lint-imports, pytest) on Python 3.12.3.

Left / notes:

- "Updating age for instance/volume/preemptible instance" lines stay INFO (they are not in the
  contract list and only appear for resources with a custom age tag).
- `region_skipped` is called where a region is skipped on a list failure. The region subscription
  fallback in `Base.get_all_regions` and the partial skips (attachments, boot attachments) only keep
  their warning: they do not skip a whole named region.
- A non-connectivity listing error in spot VM (`failed listing instances`) is recorded with
  `fail(region, "-", e)`.
- Contract question: the spot VM leftover volumes are reported as ACTION lines (id = volume OCID),
  so `selected` / `done` of `oci spot_instances` count instances plus volumes. Drop the volume
  ACTION lines if the dry-run pipeline expects instances only.
- No locked safety test (`tests/test_oci_spot_vm.py`) asserts these levels; none was touched.
- The runlog API had everything needed; no workaround.

## Round 1 (Argon)

### Findings

1. **FIXED (in-scope consistency): `crc/oci/spot_vm/{adapter,cleaner,leftovers}.py` region propagation on leftover volume `ACTION` and `FAILED` lines.**
   - Before this fix, `SpotVmCleaner.terminate()` (live run) emitted `ACTION deleted ... region=<region> id=<volume_id> name=-`, whereas `SpotVmCleaner.apply()` (dry run) and `SpotVM._delete_volume()` (adapter) emitted `region=-` for the same leftover volumes, and `leftovers.py` (`attached_volume_ids`, `wait_terminated`, `volume_passes_tag_check`, `delete_leftover`) always recorded `fail(None, ...)` (`region=-`) even when called inside a regional pass.
   - Threaded `region: str | None = None` through `leftovers.py` and `SpotVM._region` (with class default `None` so direct unit-test calls without `delete()` still work and hook signatures for `tests/test_oci_spot_vm.py` remain unchanged), and aligned `SpotVmCleaner.apply()` dry-run volume `ACTION` lines to pass `region=candidate.region` in per-candidate order. Updated `tests/test_oci_runlog.py` and parametrized `test_spot_vm_cleaner_plan_apply_reports` over live and dry-run modes.

### Checklist

1. **Behaviour / log-only contract**: Verified against `git diff 7437ac5..HEAD` and the oracle parity suites. Only log levels (`logging.info(tags)` -> `logging.debug(tags)` in `crc/oci/disk/cleaner.py` and `crc/oci/vm/cleaner.py`; `"Skipping leftover volume ..."` -> `logging.debug` in `crc/oci/spot_vm/leftovers.py`) and `crc.core.runlog` reporting calls (`crc/oci/_runlog.py`) changed. Selection, deletion/stopping, SDK call order, Slack messages, InfluxDB points, CLI flags, and exit codes are unchanged.
2. **Line formats**: `REGION`, `ACTION`, `SKIPPED`, `ERRORS`, `FAILED`, and `RESULT` lines match `docs/refactor/LOGGING.md` and `crc/core/runlog.py` key names, order, and log levels.
3. **Parity tests**: `tests/legacy/oci_{disk,vm,spot_vm}.txt` are untouched. All log comparisons go through `expected_logs(old.logs, BUGS)` with in-scope bug IDs (`BUG-353`, `BUG-358`, `BUG-361`, `BUG-362`), changing only the level of the documented lines to `DEBUG` without dropping or altering message text. Each parity module includes a `test_*_diverges_from_oracle` test proving `old.logs != new.logs` on matching cases while calls and message texts remain identical.
4. **Locked safety tests**: `tests/archtest/safety_lock.json` and all 5 locked safety test files (`tests/test_oci_spot_vm.py`, etc.) are untouched.
5. **READMEs & docs (ARCH-002)**: `crc/oci/README.md` documents `_runlog.py` and its symbols; `crc/oci/{disk,vm,spot_vm}/README.md` remain in sync. Protected files (`AGENTS.md`, `ARCHITECTURE.md`, `CLEANUP_SAFETY.md`, `docs/refactor/PLAN.md`, `docs/refactor/BUGS.md`, `docs/refactor/STATUS.md`, `.cursor/**`, `tests/archtest/**`, `crc/core/**`, `crc/cli/**`) are untouched.
6. **Gates & test count**: `make check` passed (`ruff check .`, `mypy` on 209 source files, `lint-imports` 5/5 contracts kept, `pytest -q`: **42277 passed**).

VERDICT: APPROVE
