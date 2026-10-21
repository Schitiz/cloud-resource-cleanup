# AZ-4 review

## Coding summary

Rung AZ-4: `crc/azu/vm.py` is now the subpackage `crc/azu/vm/` with a registered `Cleaner`
(`@register("azure", "vm")`) and the legacy `VM` kept as a thin adapter. Status: complete; ruff,
mypy strict, lint-imports and pytest are green (`make check` equivalent).

- Split by responsibility (the old module plus Protocols would pass the ARCH-004 400-line limit):
  `client.py` (SDK Protocols), `cleaner.py` (`VmSettings`, `Tally`, `log_summary`, `VmCleaner`,
  `build_vm_cleaner`), `adapter.py` (`VM`), each documented in `crc/azu/vm/README.md`. The old
  import path `from crc.azu.vm import VM` works through the package `__init__.py` (`__all__`).
- Cleaner: `plan()` lists the subscription (`list_all`), filters through `crc.core.policy`
  (`skip_untagged(SKIP)`, `should_skip_by_tags`, `filter_tags_all_keys`; FILTER_VARIANTS.md section 3,
  `azu/vm.py`), ages through `crc.core.age` (`get_retention_age`, `effective_age`, `is_old`) and
  reads `instance_view` for the VMs that pass (`policy.status_contains_any_allowed`); it makes no
  mutating call and logs the dry-run summary. `apply()` deletes (`begin_delete(...).result(timeout=3600)`
  then the unchanged `delete_vm_primary_nic` helper) or `begin_power_off`s, in plan order, with main's
  per-VM swallow-and-log and its summary lines. SDK behind the `VmComputeClient` / `VmOperations` /
  `VmNetworkClient` / `NicOperations` Protocols; client factories are injected through the constructor.
  `crc/azu/vm_delete_helpers.py` is unchanged (still legacy, shared with `SpotVM`).
- Adapter: `VM(resource_group, dry_run, filter_tags, exception_tags, age, custom_age_tag_key, notags)`
  keeps `delete()`, `stop()`, `get_deleted`, `delete_count`, `get_deleted_nic`, `nic_delete_count`,
  `get_stopped`, `stopped_count`, the name lists, `base` and the constructor attributes, plus one
  optional trailing `clock` argument (default `datetime.datetime.now`) so tests can fix the time. It
  iterates the lazy listing and decides, reads status and acts VM by VM, so the call order, mid-run
  error behaviour and cumulative lists are those of main. The private helpers of the old class
  (`_perform_operation` internals, `_should_*`, `_get_vm_status`, `_delete_vm`, `_stop_vm`) are gone;
  nothing used them. `crc.py` is unchanged.
- Cleaner path: `plan()` decides on every VM and reads every status before `apply()` mutates, so
  paging, status reads and mutations are no longer interleaved, and an age or listing error now
  happens before any delete instead of after earlier ones. A dry run builds no network client (main
  builds it without calling it). The summary log lines are the same: dry run logs from `plan()`,
  a real run from `apply()`. The factory maps `instance_state=None` to the default `["running"]`
  (an empty list means nothing, as for a direct `delete([])`; `crc.py` already maps `[]` to the default).
- Tests: baseline `pytest -q` 4681 passed; now 4965 passed (+284): `tests/test_azure_vm_parity.py`
  (102 cases through the adapter, the same 102 through the registered Cleaner, 57 quirk checks,
  plus subscription-wide/resource-group, power-off, repeated-delete and factory tests, 266 in all),
  `tests/test_azure_vm.py` (18 focused `plan()` / `apply()` tests). All existing tests unchanged.
  Oracle: `tests/legacy/azu_vm.txt` is byte-identical to `git show main:crc/azu/vm.py`. The module
  lists no regions, so there is no region fallback or region auth-error case; list errors,
  mid-listing errors, status errors, delete errors, NIC retry/404 paths, `MAX_AGE`, custom age tags
  and age edges are covered. Memory addresses in log text are masked in the comparison.
- Ratchet: `crc/azu/vm.py` removed from ruff `extend-exclude` and `crc.azu.vm` from the mypy override
  (the subpackage modules are checked). No per-SDK mypy override was needed.
- Open issues: new bugs and quirks in `docs/refactor/bugs/pending/AZ-4.md` (10 rows, ID `NEW`).
  BUG-002, BUG-003, BUG-004, BUG-010 and BUG-028 are preserved, not fixed.
- Needed changes outside this lane (not made): `crc/README.md`, `tests/README.md` and
  `tests/legacy/README.md` should list `crc/azu/vm/`, `tests/legacy/azu_vm.txt`,
  `tests/test_azure_vm_parity.py`, `tests/test_azure_vm.py` and `tests/helpers_azure_vm.py`.
  `FILTER_VARIANTS.md` section 3, `azu/vm.py` row: the location is now `crc/azu/vm/cleaner.py`
  (`policy.skip_untagged`, `should_skip_by_tags`, `filter_tags_all_keys`,
  `status_contains_any_allowed`, `get_retention_age` + `is_old`); the semantics are unchanged.
  No core change needed.
