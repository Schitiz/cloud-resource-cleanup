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

## Round 1 (Argon)

Scope reviewed: `git diff 2bd8e67..HEAD` on branch `cl2/oci` (`tests/test_cli_bridge_oci.py`, `tests/helpers_cl2_oci.py`, `tests/helpers_cl2_oci_runlog.py`, `tests/archtest/test_count_floor.txt`, `docs/archive/reviews/CL2-OCI.md`).

### Findings

- **BLOCKING**: None. No code changes required in review.

### Checklist verification

1. **No legacy CLI or current OCI adapter imports/calls (`grep` + runtime poisoning check)**:
   - `tests/test_cli_bridge_oci.py`, `tests/helpers_cl2_oci.py`, and `tests/helpers_cl2_oci_runlog.py` do not import `crc.cli.resource_ops`, `crc.cli.vm_ops`, `crc.cli.notify`, `crc.cli.adapter_args`, `crc.cli.report_calls`, `tests.helpers_legacy_handlers`, or the current OCI adapter classes (`crc.oci.disk.Disk`, `crc.oci.vm.VM`, `crc.oci.spot_vm.SpotVM`).
   - `NewCRC` (`crc.cli.runner.CRC`) is only instantiated on the routed side as the context holder passed to `dispatch._run_pair` -> `bridge.run_routed`; no `delete_*`, `stop_*`, or `notify_*` method of `NewCRC` is called. Poisoning all methods of `ResourceOps`, `VmOps`, `NotifyMixin.notify_*`, `adapter_args`, `report_calls`, and the current OCI `Disk`, `VM`, and `SpotVM` adapters with `AssertionError` still passes all 107 tests in `tests/test_cli_bridge_oci.py`.
2. **Parity comparisons, frozen run-log data, case counts, and BUG-NNN divergences**:
   - The legacy side runs `oracle` (`tests.helpers_oracle.load_legacy_crc()`), driving `tests/legacy/crc_main.txt` with `OCI_Disk`, `OCI_VM`, and `OCI_SpotVM` bound to `tests/legacy/oci_{disk,vm,spot_vm}.txt` (verified by `test_the_legacy_side_runs_the_frozen_oracles`).
   - All 96 parametrized cases in `test_routed_pair_matches_the_legacy_adapter` and all 8 cases in `test_the_comparison_is_not_vacuous` are preserved (104 -> 107 cases total in `tests/test_cli_bridge_oci.py`).
   - Every previous assertion (`result`, `stdout`, `run[0]`, `run[-1]`, per-tag `ACTION`/`SKIPPED`/`ERRORS`/`FAILED`, `sorted(run)`, `slack`, `influx`, mutating `calls`, `all_calls`, and `other` logs — now also checking logger name in addition to level and message) is preserved.
   - `FROZEN_RUN_LINES` in `tests/helpers_cl2_oci_runlog.py` was cross-checked directly against the `2bd8e67` legacy side across all 96 `(kind, dry, mode, second)` combinations: every case matches 100% verbatim and is never derived from the routed side, while the legacy side also asserts that the frozen oracle emits no `crc.run` lines.
   - Fixed-bug divergences are asserted explicitly with their `BUG-NNN` IDs: `BUG-408` (later-region listing error halts `plan()` before any mutation on `disk` and `vm`), `BUG-353` and `BUG-358` (`expected_logs(oracle_logs, {"BUG-353", "BUG-358"}, RULES)` from `tests/log_fix_oci.py`), and `BUG-255` (`_expected_all_calls` adds the exact `("list_volume_attachments", "vol-a")` / `("list_volume_attachments", "vol-d")` leftover-volume attachment reads on `spot_instances`).
3. **Non-vacuity / mutation check**:
   - Deliberately mutating `DiskCleaner.apply` to drop one candidate delete and mutating `SlackNotifier.send` to alter a Slack section label both cause `pytest -q tests/test_cli_bridge_oci.py` to fail immediately (`rc=1`).
4. **Owned files and boundaries**:
   - Only `tests/test_cli_bridge_oci.py`, `tests/helpers_cl2_oci.py`, `tests/helpers_cl2_oci_runlog.py`, `tests/archtest/test_count_floor.txt` (via `make raise-test-floor`), and `docs/archive/reviews/CL2-OCI.md` changed relative to `2bd8e67`. Zero production files (`crc/**`), `tests/legacy/*.txt`, or hash-locked safety tests were touched.

### Gates & Test Count

Ran `pip install -r requirements.txt -r requirements-dev.txt` followed by `make check`:

| Gate | Result |
|------|--------|
| `python3 -m ruff check .` | All checks passed! |
| `python3 -m mypy` | Success: no issues found in 366 source files |
| `lint-imports` | Contracts: 5 kept, 0 broken (220 files, 1242 dependencies) |
| `python3 -m pytest -q -n auto` | **44403 passed in 61.07s** |
| `python3 -m tests.archtest.test_count check` | `ARCH-008: 44403 tests, floor 44403` |

Total `make check` runtime: **1m23.4s** (`pytest`: 61.07s). Test count: **44,403** (up from 44,400 at `2bd8e67`).

VERDICT: APPROVE

