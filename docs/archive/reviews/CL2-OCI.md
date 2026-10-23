## Coding summary

Lane CL2-OCI, test-only. Status: DONE, `make check` green (44403 tests).

### What is routed / deleted / shimmed
- Nothing in `crc/**` changed. No adapter was deleted or shimmed; production already routes the OCI
  pairs (`disk`, `vm` delete and stop, `spot_instances`) through `crc/cli/bridge.py`.

### How `tests/test_cli_bridge_oci.py` reaches the cleaners now
- Legacy side: `load_legacy_crc()` (`tests/legacy/crc_main.txt`) with `OCI_Disk`, `OCI_VM`,
  `OCI_SpotVM` bound to `tests/legacy/oci_{disk,vm,spot_vm}.txt`. `CRC.delete_disks`,
  `delete_vm`, `stop_vm`, `delete_spot_instances` of that oracle run unchanged. The file no
  longer imports `crc.oci.disk/vm/spot_vm` adapters, `crc.core.logger` or any legacy CLI module,
  and no longer patches the oracle module with current adapter classes.
- `tests/helpers_cl2_oci.py`: shims that bind `oci.core.ComputeClient`, `BlockstorageClient`,
  `oci.identity.IdentityClient` and `oci.pagination` to the same fake API objects the routed path
  uses (so SDK calls land in the same `calls` lists), plus a fixed clock for the oracle modules.
- Run-log lines (RUN START, ACTION, REGION, SKIPPED, ERRORS, FAILED, RESULT): the oracles emit none
  (the test asserts that). Expected lines are frozen in `tests/helpers_cl2_oci_runlog.py`, captured
  from the then-current legacy side (2bd8e67) for all 24 (resource, operation, dry, second-region
  error) combinations (they do not depend on the Slack/Influx mode; checked while capturing). The
  routed side is asserted against that data, never against itself.
- Explicit divergences from the oracle (nothing loosened):
  - BUG-353 / BUG-358 (log levels): `expected_logs(..., RULES)` from `tests/log_fix_oci.py`.
  - BUG-408 (listing error in a later region stops the pair before any mutation): as before.
  - BUG-255 (spot): the routed path also reads the attachments of each leftover volume before
    deleting it; `_expected_all_calls` adds exactly those reads to the oracle's calls.
  - Test seam: the routed side takes regions from the patched `regions_of`, so the oracle's single
    "Retrieved list of OCI regions" line is excluded from the log comparison (nothing else).
  - Compartment: the routed fake clients now use the real `COMPARTMENT_ID`, so list calls match the
    oracle's instead of the old `"cmp"` stand-in.

### Numbers
- Test count: 44400 before (floor) / 44403 after. `test_cli_bridge_oci.py`: 104 cases before
  (96 pair cases + 8 non-vacuity cases), 107 after (+3 `test_the_legacy_side_runs_the_frozen_oracles`).
- Floor raised with `make raise-test-floor`.

### Owner actions
- None. No hash-locked test, `tests/legacy/*.txt` or `tests/archtest/**` file edited (the floor
  file is the only archtest file changed, via `make raise-test-floor`).

## New bugs
- None found.
