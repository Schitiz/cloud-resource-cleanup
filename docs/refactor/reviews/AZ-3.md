# AZ-3 review

## Coding summary

Rung AZ-3: `crc/azu/disk.py` is a registered `Cleaner` (`@register("azure", "disk")`), with `Disk`
kept as a thin adapter. Status: complete; ruff, mypy strict, lint-imports and pytest are green (`make check` equivalent).

- Cleaner: `AzureDiskCleaner` (`plan()` = `disks.list` plus filtering, read-only; `apply()` =
  `disks.begin_delete(resource_group, name)` in plan order). SDK behind the `DiskComputeClient` /
  `DiskOperations` / `SdkDisk` Protocols, client factory injected through the constructor.
  Filtering: `policy.filter_tags_any_key`, `policy.exception_tags_any`, `policy.notags_all` (all
  three evaluated for every disk, as main), age through `core_age.get_retention_age` and
  `core_age.is_old` with `policy.effective_age`, state through `policy.state_is_substring_of_any`
  (FILTER_VARIANTS.md section 3, `azu/disk.py`). Tags are copied with `dict(disk.tags)` instead of
  `policy.normalize_tags`, so non-string tag values behave exactly as on main. The module stays one
  file (about 300 lines, no function over the ruff limits), so no subpackage split.
- Adapter: `Disk(resource_group, dry_run, filter_tags, exception_tags, age, custom_age_tag_key,
  notags)` keeps `delete()`, `get_deleted`, `count`, `disks_names_to_delete`, `base`,
  `default_disk_state` and the constructor attributes; it adds `clock` (defaults to
  `datetime.datetime.now`, read once per disk as main does). `delete()` iterates the lazy listing and
  decides and deletes disk by disk, so call order, mid-run error behaviour and the cumulative list
  are those of main. `crc.py` is unchanged.
- Cleaner path: `plan()` lists and decides every disk first, then `apply()` deletes, using the single
  `RunContext.now`. Differences from main: paging is no longer interleaved with deletes, and a
  listing or decision error now happens before any delete (and decision logs precede the "Deleted
  disk" logs). Summary lines are the same: dry run logs the "which will be deleted" warning from
  `plan()`, a real run logs the two "deleted" warnings from `apply()`.
- Tests: baseline `pytest -q` 3715 passed; now 3919 passed (+204): `tests/test_azure_disk_parity.py`
  (77 cases through the adapter, the same 77 through the registered Cleaner, 34 quirk checks, plus
  interleaving, repeated-delete and factory tests), `tests/test_azure_disk.py` (13 focused `plan()` /
  `apply()` / adapter tests). All existing tests unchanged. Oracle: `tests/legacy/azu_disk.txt` is
  byte-identical to `git show main:crc/azu/disk.py`, run with a frozen clock. The module lists no
  regions, so there is no region fallback or region auth-error case to cover.
- Ratchet: `crc/azu/disk.py` removed from ruff `extend-exclude` and the mypy override `crc.azu.disk`.
  No per-SDK mypy override was needed.
- Open issues: new bugs and quirks in `docs/refactor/bugs/pending/AZ-3.md` (9 rows, ID `NEW`);
  existing rows `BUG-004` and `BUG-019` apply and are unchanged.
- Needed changes outside this lane (not made): `crc/README.md`, `tests/README.md` and
  `tests/legacy/README.md` should list `tests/legacy/azu_disk.txt`, `tests/test_azure_disk_parity.py`,
  `tests/test_azure_disk.py` and `tests/helpers_azure_disk.py`. `FILTER_VARIANTS.md` section 3: the
  `azu/disk.py` row can cite `policy.filter_tags_any_key`, `policy.exception_tags_any`,
  `policy.notags_all`, `policy.state_is_substring_of_any` and `policy.effective_age`. No core change
  needed. `STATUS.md` and `BUGS.md` rows are for the integrator.
