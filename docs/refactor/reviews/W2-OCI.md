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
