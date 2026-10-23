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
