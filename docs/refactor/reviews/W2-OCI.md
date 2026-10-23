## Coding summary

Lane W2-OCI (structure only, no behaviour change). Base commit `cea0a8a`.

### Files split (lines before -> after)

| File | Before | After | New modules |
|------|--------|-------|-------------|
| `crc/oci/disk/cleaner.py` | 346 | 249 | `disk/settings.py` (76: `DiskSettings`, `DiskRuntime`, constants, skip keys, summary log), `disk/decide.py` (72: `skip_reason`, `is_old`, `in_use`, `sort_decisions`) |
| `crc/oci/spot_vm/cleaner.py` | 292 | 209 | `spot_vm/report.py` (47: summary/error logging, dry-run records), `spot_vm/terminate.py` (95: `terminate_instance`, `with_checked_volumes`, `owner_of`) |
| `crc/oci/vm/cleaner.py` | 281 | 231 | `vm/settings.py` (78: `VmSettings`, skip keys, `log_summary`, `log_for`) |

The legacy adapters (`Disk`, `SpotVM`, `VM`) were already in their own `adapter.py`; untouched.
Every name previously importable from the old modules is still importable from the same path
(re-exported from the cleaner modules; `__init__.py` files unchanged). No test string patch
target names a moved symbol (`crc.oci._logger.*` and the global `oci.pagination` patches are
unaffected, and the cleaners still reach `leftovers.*` through the module).

### Helpers extracted

- `crc/oci/_common.py`: `group_by_region()`, the by-region grouping that was written out in both
  `DiskCleaner.apply()` and `VmCleaner.apply()`.
- `disk/decide.py`: `in_use()` (the ATTACHED/ATTACHING filter written twice for volume and boot
  volume attachments), `sort_decisions()` (replaced the 10-parameter `_decide_all`).
- `spot_vm/terminate.py`: `owner_of()` (the `VolumeOwner` construction was repeated).

### Tests

- `pytest -q` before (cea0a8a): 43010 passed. After: 43010 passed (no test added or edited).
- `make check` (ruff, mypy, lint-imports, pytest): green; runtime about 3 minutes (about 160 s of it pytest).
- READMEs updated: `crc/oci/README.md`, `crc/oci/disk/README.md`, `crc/oci/spot_vm/README.md`, `crc/oci/vm/README.md` (module lists and Public API symbols).

## Owner action

- `group_by_region` (candidates grouped by region before `apply()`) has the same shape in other
  clouds' cleaners; a `crc/core` helper could serve all clouds (not done here: out of lane).
- The `__all__` re-export blocks in `disk/cleaner.py` and `vm/cleaner.py` (including the private
  `_LIST_CONTEXT` and `_log_summary`, which the adapters import) can be dropped once the adapters
  import from `settings.py` directly or are deleted.
- The 250-line limit is met with no margin in `disk/cleaner.py` (249).

## New bugs

None found.

## Round 1 (Argon)

Scope reviewed: `git diff cea0a8a..HEAD` (`crc/oci/README.md`, `crc/oci/_common.py`, `crc/oci/disk/README.md`, `crc/oci/disk/cleaner.py`, `crc/oci/disk/decide.py`, `crc/oci/disk/settings.py`, `crc/oci/spot_vm/README.md`, `crc/oci/spot_vm/cleaner.py`, `crc/oci/spot_vm/report.py`, `crc/oci/spot_vm/terminate.py`, `crc/oci/vm/README.md`, `crc/oci/vm/cleaner.py`, `crc/oci/vm/settings.py`, `docs/refactor/reviews/W2-OCI.md`).

### Checklist verification

1. **No behaviour change (`git diff --color-moved=zebra cea0a8a..HEAD`)**:
   - `crc/oci/_common.py`: `group_by_region()` extracts the identical `by_region.setdefault(candidate.region, []).append(candidate)` grouping loop previously inlined in `DiskCleaner.apply()` and `VmCleaner.apply()`.
   - `crc/oci/disk/`: `settings.py` extracts `DiskRuntime`, `DiskSettings`, `SKIP_KEYS`, `IN_USE_ATTACHMENT_STATES`, constants, and `log_summary` verbatim from `disk/cleaner.py`; `decide.py` extracts `skip_reason()`, `is_old()`, `sort_decisions()` (replacing `_decide_all` with identical evaluation and append order), and `in_use()` (shared between block volume and boot volume attachment filtering). All conditions, defaults, SDK call ordering, exception handling, and log strings are unchanged.
   - `crc/oci/spot_vm/`: `report.py` extracts `VOLUMES_LABEL`, `log_summary()`, `log_instance_error()`, and `record_dry_run()` verbatim from `spot_vm/cleaner.py`; `terminate.py` extracts `owner_of()`, `with_checked_volumes()`, and `terminate_instance()` verbatim (`SpotVmCleaner.terminate()` delegates directly to `terminate_instance()`). Zero logic or log text changes.
   - `crc/oci/vm/`: `settings.py` extracts `DEFAULT_INSTANCE_STATES`, `TagSpec`, `SKIP_KEYS`, `EVALUATION_FAILED`, `Clock`, `VmSettings`, `log_summary()`, and `log_for()` verbatim from `vm/cleaner.py`. Zero logic or log text changes.
2. **Import paths and test patch targets**:
   - Package `__init__.py` files (`crc/oci/disk/__init__.py`, `crc/oci/spot_vm/__init__.py`, `crc/oci/vm/__init__.py`) and legacy `adapter.py` files are untouched.
   - `disk/cleaner.py`, `spot_vm/cleaner.py`, and `vm/cleaner.py` re-export all moved symbols (including `_LIST_CONTEXT` and `_log_summary` used by `disk/adapter.py` and `vm/adapter.py`, and `log_summary` / `log_instance_error` used by `spot_vm/adapter.py`).
   - All `monkeypatch` / `mock.patch` targets in `tests/test_oci*.py` (`crc.oci._logger.record_skip`, `crc.oci._logger.record_failure`, `crc.oci._logger.logger.current`, `crc.oci.spot_vm.oci.pagination.list_call_get_all_results`, `crc.oci.spot_vm.Base.__init__`, and `crc.oci.spot_vm.leftovers.time`) resolve to the live code paths unchanged.
3. **Tests and forbidden files**:
   - Zero test files edited (`git diff cea0a8a..HEAD -- tests/` is empty); all 5 hash-locked safety tests and `tests/legacy/*.txt` are untouched (`SAF-LOCK` green).
   - No forbidden files (`AGENTS.md`, `ARCHITECTURE.md`, `CLEANUP_SAFETY.md`, other `docs/refactor/*.md`, `.cursor/**`, `tests/archtest/**`, `pyproject.toml`, `Makefile`, `requirements*.txt`, `.github/**`, `crc/core/**`, or other clouds) were modified.
4. **File sizes and split seams**:
   - Every `.py` file under `crc/oci/` is at or below 250 lines (`wc -l`): `disk/cleaner.py` (249), `spot_vm/adapter.py` (241), `vm/cleaner.py` (231), `spot_vm/cleaner.py` (209), `spot_vm/leftovers.py` (200), `spot_vm/client.py` (192), `disk/api.py` (180), `vm/adapter.py` (151), `_base.py` (135), `disk/adapter.py` (131), `spot_vm/decide.py` (116), `vm/client.py` (104), `spot_vm/terminate.py` (95), `vm/settings.py` (78), `disk/settings.py` (76), `disk/decide.py` (72), `_logger.py` (58), `spot_vm/report.py` (47), `vm/__init__.py` (34), `connectivity.py` (29), `_common.py` (15), `spot_vm/__init__.py` (11), `disk/__init__.py` (8), `__init__.py` (1).
   - Splits follow clean domain seams (`settings`, `decide`, `report`, `terminate`, `_common`), and extracted helpers (`group_by_region`, `in_use`, `sort_decisions`, `owner_of`) eliminate real duplication.
5. **READMEs**:
   - `crc/oci/README.md`, `crc/oci/disk/README.md`, `crc/oci/spot_vm/README.md`, and `crc/oci/vm/README.md` are concise and in sync with `ARCH-002`.

### Findings

- **BLOCKING**: None.
- **NIT (left)**: `crc/oci/disk/cleaner.py` is 249 lines (1 line under the 250-line cap); trimming the `__all__` re-export block once `disk/adapter.py` imports from `disk/settings.py` (noted under `## Owner action`) will give comfortable headroom.

### Gates

`pip install -r requirements.txt -r requirements-dev.txt` then `make check`:

| Gate | Result |
|------|--------|
| `ruff check .` | All checks passed! |
| `mypy` | Success: no issues found in 257 source files |
| `lint-imports` | Contracts: 5 kept, 0 broken (149 files, 860 dependencies) |
| `pytest -q` | 43010 passed in 161.55s (0:02:41) |

Total `make check` runtime: 3m0.87s (`pytest -q`: 161.55s).
Test count: 43010 passed vs 43010 at base `cea0a8a` (unchanged).

VERDICT: APPROVE

