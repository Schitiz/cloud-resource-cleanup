# AZ-2 review

## Coding summary

Rung AZ-2: `crc/azu/nic.py` is a registered `Cleaner` (`@register("azure", "nic")`), with `NIC` kept
as a thin adapter. Status: complete; ruff, mypy strict, lint-imports and pytest are green (`make check` equivalent).

- Cleaner: `AzureNicCleaner` (`plan()` = `list_all` twice, as main, plus policy filtering,
  read-only; `apply()` = `begin_delete(rg, name).result()` in plan order with main's three attempts,
  swallowed errors and log lines; failed NICs are also reported in `Result.failed`). SDK behind the
  `NicNetworkClient` / `NicOperations` / `DeletePoller` Protocols; the client factory is injected
  through the constructor. Filtering: `policy.nic_name_included` and `policy.nic_name_excluded`
  (FILTER_VARIANTS.md section 3, `azu/nic.py`). `exception_regex` is still evaluated for every
  unattached NIC and guarded by truthiness, as on main. No age gate and no tag filter exist on main,
  so `crc.core.age` is not used (recorded as a pending bug).
- Adapter: `NIC(resource_group, dry_run, name_regex, exception_regex)` keeps `delete()`,
  `get_deleted`, `delete_count`, `nics_names_to_delete`, `base`, `dry_run`, `name_regex`,
  `exception_regex`. `delete()` iterates the lazy `list_all()` and decides and deletes NIC by NIC,
  so call order (paging interleaved with deletes, one client lookup per attempt), mid-run error
  behaviour and the cumulative list are those of main. `crc.py` is unchanged.
- Cleaner path: `plan()` lists and filters everything first, then `apply()` deletes. The only
  differences from main are the interleaving of paging and deletes, and that a listing or decision
  error (`None` name, non-string exception entry, paging error) now happens before any delete
  instead of after earlier deletes. Summary log lines are the same: dry run logs the "which will be
  deleted" warning from `plan()`, a real run logs the two "deleted" warnings from `apply()`; an
  empty `name_regex` logs "No Azure NICs to delete." from `plan()` and `apply()` does nothing.
- Tests: baseline `pytest -q` 3037 passed; now 3203 passed (+166): `tests/test_azure_nic_parity.py`
  (60 cases through the adapter, the same 60 through the registered Cleaner, 28 quirk checks, plus
  the double-listing, subscription-wide/resource-group, repeated-delete and factory tests, 152 in
  all), `tests/test_azure_nic.py` (14 focused `plan()` / `apply()` tests). All existing tests
  unchanged. Oracle: `tests/legacy/azu_nic.txt` is byte-identical to `git show main:crc/azu/nic.py`.
- The module has no age gate and lists no regions, so there are no age edges and no region fallback
  or region auth-error cases to cover.
- Ratchet: `crc/azu/nic.py` removed from ruff `extend-exclude` and the mypy override `crc.azu.nic`.
  No per-SDK mypy override was needed.
- Open issues: new bugs and quirks in `docs/refactor/bugs/pending/AZ-2.md` (11 rows, ID `NEW`).
  No existing BUGS.md row is specific to this module (BUG-017 and BUG-028 concern `crc.py`).
- Needed changes outside this lane (not made): `crc/README.md`, `tests/README.md` and
  `tests/legacy/README.md` should list `tests/legacy/azu_nic.txt`, `tests/test_azure_nic_parity.py`,
  `tests/test_azure_nic.py` and `tests/helpers_azure_nic.py`. `FILTER_VARIANTS.md` section 3: the
  `azu/nic.py` row can cite `policy.nic_name_included` / `policy.nic_name_excluded`, and add that
  `exception_regex` is evaluated for every unattached NIC (even when `name_regex` did not match).
  No core change needed. `STATUS.md` and `BUGS.md` rows are for the integrator.
