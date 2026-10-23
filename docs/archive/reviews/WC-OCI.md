## Coding summary

Lane WC-OCI: delete the dead OCI disk adapter and trim the OCI READMEs. Complete, nothing left.

- **Routed:** `(oci, disk)` already ran through `crc/cli/bridge.py` and the registered `DiskCleaner` (`NotifyMode.REPORT_THEN_RERAISE`); this lane changed no routing.
- **Deleted:** `crc.oci.disk.Disk` (`crc/oci/disk/adapter.py`), its package re-export, its README Public API line, and the now-unused `DiskRuntime` and `Clock` (`crc/oci/disk/settings.py`) plus the adapter-only aliases `_LIST_CONTEXT` and `_log_summary` in `cleaner.py`. Production had no user of `Disk` (`crc/cli/scan.py` uses the VM adapters only). `crc/oci/vm` and `crc/oci/spot_vm` code is untouched; their READMEs got text-only edits.
- **Shimmed:** none. The five hash-locked adapters and their tests are untouched.
- **Tests retargeted to `crc.core.engine.run`** (oracle `tests/legacy/oci_disk.txt`, all cases kept):
  - `tests/test_oci_disk_parity.py`: `test_matches_main`, `test_quirk_is_preserved`, `test_disk_diverges_from_oracle` and `test_unknown_attachments_keep_the_volumes` now run the registered Cleaner through the engine. `test_cleaner_protocol_matches_main` keeps the direct `plan()` / `apply()` path. Both compare reads and deletes in order, results, count, log lines (reordered plan, apply, summary), stdout and errors. BUG-096/097/098 divergences and BUG-353/358 level changes are still asserted. One quirk case changes under the allowed plan-before-apply difference: `unexpected-error-in-boot-volume-after-volume-delete` now asserts the error and no delete (fewer deletes).
  - `tests/test_oci_disk_fix.py` and `tests/test_oci_logger.py`: use the new helper `tests/helpers_wc_oci_disk.py` (`run_disk`, engine run with injected fake APIs). In the logger test the non-dry-run REGION line now comes before the ACTION lines (plan lists before apply deletes); the dry-run order is unchanged.
- **CLI parity tests:** unchanged. They already reach the cleaners through the bridge seam (`tests/test_cli_bridge_oci.py` patches `crc.oci.disk.cleaner.api_for` and `Base`).
- **READMEs trimmed:** `crc/oci/README.md`, `crc/oci/disk/README.md`, `crc/oci/vm/README.md`, `crc/oci/spot_vm/README.md` describe only the current code. Rung names, refactor history, legacy-path wording and links to moved docs are removed.
- **Test count:** 44415 before, 44415 after (ARCH-008 floor 44415, unchanged). `make check` is green.

### Owner actions

- None for this lane. `crc/oci/vm/adapter.py` and `crc/oci/spot_vm/adapter.py` remain for the CLI scan and the locked test.
- `tests/archtest/legacy_baseline.txt` still lists `crc/oci/disk.py`, which no longer exists. It is stale but harmless, and `tests/archtest` was out of scope.

## New bugs

None.


## Round 1 (Argon)

Scope reviewed: `git diff 302612d..HEAD` on branch `wc/oci` (lane `WC-OCI`).

### Findings & fixes made in review

- **Residual legacy/rung wording in OCI READMEs and docstrings**:
  - `crc/oci/spot_vm/README.md:61-62` still contained `(as the legacy SpotVM reported them)` and `(as on main)`.
  - `crc/oci/README.md:7,49` still referenced the `legacy ratchet`.
  - `crc/oci/_logger.py:3` still mentioned `(rung LOG-OCI)` in its module docstring, and `crc/oci/disk/attachments.py:59` and `crc/oci/disk/cleaner.py:76` still mentioned `legacy Disk.delete()` / `legacy adapter` in their docstrings.
  - Trimmed those remaining phrases in `crc/oci/README.md`, `crc/oci/spot_vm/README.md`, `crc/oci/_logger.py`, `crc/oci/disk/attachments.py`, and `crc/oci/disk/cleaner.py`.

### Checklist verification

1. **Production code & locked adapters intact**:
   - Only `crc.oci.disk.Disk` (`crc/oci/disk/adapter.py`), `DiskRuntime` / `Clock` (`crc/oci/disk/settings.py`), and the private adapter-only aliases `_LIST_CONTEXT` / `_log_summary` (`crc/oci/disk/cleaner.py`) were deleted.
   - `crc/cli/scan.py` (which uses `crc.oci.vm.VM`), `crc/cli/routes/oci.py`, `build_disk_cleaner` (`@register("oci", "disk")`), `crc.oci.vm.VM`, and the five adapters used by the hash-locked safety tests (`crc.aws.disk.Disk`, `crc.aws.spot_instance_requests.SpotInstanceRequests`, `crc.azu.spot_vm.SpotVM`, `crc.gcp.spot_vm.SpotVM`, `crc.oci.spot_vm.SpotVM`) are untouched.
2. **Module parity tests retargeted to `crc.core.engine.run` & non-vacuous**:
   - `tests/test_oci_disk_parity.py` keeps all 66 oracle cases against `tests/legacy/oci_disk.txt`. `test_matches_main`, `test_quirk_is_preserved`, `test_disk_diverges_from_oracle` (`BUG-353`, `BUG-358`), and `test_unknown_attachments_keep_the_volumes` (`BUG-096`, `BUG-097`, `BUG-098`) run `build_disk_cleaner` through `crc.core.engine.run`, while `test_cleaner_protocol_matches_main` also exercises `plan()` / `apply()` directly. Both assert reads and deletes in order, deleted names, count, reordered log lines (`plan_logs + apply_logs + summary_logs`), stdout, and raised errors. Under the allowed plan-before-apply change (`BUG-408`), `unexpected-error-in-boot-volume-after-volume-delete` asserts the error and zero deletes (`ENGINE_QUIRKS`).
   - `tests/test_oci_disk_fix.py` (`test_engine_keeps_volumes_with_unknown_attachments`) and `tests/test_oci_logger.py` (`test_disk_engine_reports_regions_actions_skips_and_result`, `test_disk_failed_delete_is_listed_at_the_end`) drive `DiskCleaner(..., engine=True)` through `crc.core.engine.run` via `tests/helpers_wc_oci_disk.py::run_disk`.
   - Deliberate mutation checks (reverted locally without committing):
     - Mutating `crc/oci/disk/decide.py` (`filter_tags_any_key` -> `filter_tags_all_keys`) failed 4 tests in `tests/test_oci_disk_parity.py`.
     - Mutating `crc/oci/disk/cleaner.py` (`api.delete_volume(candidate.id)` -> `pass`) failed 79 tests in `tests/test_oci_disk_parity.py`.
3. **Deleted names gone & READMEs trimmed**:
   - Grepped `crc/`, `crc.py`, and `tests/` for `crc.oci.disk.adapter`, `crc.oci.disk.Disk`, `from crc.oci.disk import.*Disk\b`, `_LIST_CONTEXT`, and OCI `DiskRuntime`: zero matches outside `tests/legacy/crc_main.txt` (frozen oracle).
   - `crc/oci/README.md`, `crc/oci/disk/README.md`, `crc/oci/spot_vm/README.md`, and `crc/oci/vm/README.md` describe only the current code with no rung names, refactor history, legacy-path wording, or links to moved docs.
4. **No locked, oracle, or out-of-scope files touched**:
   - `git diff --name-only 302612d..HEAD` touches only `crc/oci/**` (with `spot_vm` and `vm` limited to README text), `tests/helpers_wc_oci_disk.py`, `tests/test_oci_disk_fix.py`, `tests/test_oci_disk_parity.py`, `tests/test_oci_logger.py`, and `docs/archive/reviews/WC-OCI.md`. No hash-locked test, `tests/legacy/*.txt` oracle, or `tests/archtest/**` file was modified.
5. **Size limits & Public API sync**:
   - All Python files in `crc/oci/` and `tests/helpers_wc_oci_disk.py` are at or below 250 lines (largest in `crc/oci/disk/`: `cleaner.py` at 237 lines, `api.py` at 180 lines) and all functions are at or below 60 lines (largest in `crc/oci/disk/`: `DiskCleaner.plan` at 45 lines). `ARCH-002` and `ARCH-004` are green.
6. **Gates & test count**:
   - After `pip install -r requirements.txt -r requirements-dev.txt`, `make check` passed in `1m07.8s` wall time:
     - `python3 -m ruff check .`: passed
     - `python3 -m mypy`: passed (`Success: no issues found in 372 source files`)
     - `lint-imports`: passed (`5 kept, 0 broken`)
     - `python3 -m pytest -q -n auto`: `44415 passed in 58.90s`
     - `python3 -m tests.archtest.test_count check`: `ARCH-008: 44415 tests, floor 44415`

VERDICT: APPROVE

