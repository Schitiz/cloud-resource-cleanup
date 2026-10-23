## Coding summary

Wave W2, lane W2-AZU: structure-only split of the five Azure files above 250 lines. No behaviour change. `make check` green (ruff, mypy strict, lint-imports 5 kept, pytest, ARCH-001..005, SAF-LOCK). Runtime of `make check`: 2m49s (pytest 163 s).

Tests: `pytest -q` 43010 passed at cea0a8a, 43010 passed after. No test, `tests/legacy/*.txt` or hash-locked file was edited; no test import line needed changing (every old import path still works).

### Files split (before -> after, `wc -l`)

| Old file | Before | After |
|----------|-------:|-------|
| `crc/azu/ip.py` | 265 | package `crc/azu/ip/`: `client.py` 32, `cleaner.py` 144, `adapter.py` (`IP`) 95, `__init__.py` 15 |
| `crc/azu/nic.py` | 342 | package `crc/azu/nic/`: `client.py` 40, `cleaner.py` 216, `adapter.py` (`NIC`) 97, `__init__.py` 17 |
| `crc/azu/disk.py` | 344 | package `crc/azu/disk/`: `client.py` 67, `cleaner.py` 182, `adapter.py` (`Disk`) 109, `__init__.py` 29 |
| `crc/azu/spot_vm/cleaner.py` | 278 | `cleaner.py` 248 + new `config.py` 61 (`SpotVmConfig`, `STOPPED_POWER_STATES`, `TagSpec`, `log_summary`, `old_enough`) |
| `crc/azu/vm/cleaner.py` | 327 | `cleaner.py` 234 + new `settings.py` 75 (`VmSettings`, `Tally`, `log_summary`, `Clock`, `TagSpec`), `helpers.py` 39 (`tally_of`, `power_state`, `log_processing_error`, constants), `selection.py` 37 (`skip_reason`, `is_old`) |

Import paths: `crc.azu.ip|nic|disk` are packages that re-export every old public name (`IP`, `NIC`, `Disk`, cleaners, factories, Protocols, `DiskSettings`, `DELETE_ATTEMPTS`, ...). `crc.azu.spot_vm.cleaner` and `crc.azu.vm.cleaner` re-export the moved names through `__all__`, so `crc.azu.spot_vm.__init__`, `crc.azu.vm.adapter` and the tests import unchanged. Existing mock targets (`crc.azu._base.*`, `crc.azu.vm_delete_helpers.time.sleep`, `crc.azu.spot_vm.Base|begin_delete_vm_and_wait|delete_vm_primary_nic`) are unmoved, so the patches still apply. The ip/nic/disk adapters (`IP`, `NIC`, `Disk`) are each in their own `adapter.py`, deletable in one move.

### Helpers extracted (`crc/azu/_common.py`, 35 lines)

- `kept(reason)`: the `_kept` static method that was copied in `AzureIpCleaner` and `AzureNicCleaner`.
- `log_would_delete(resource_group, candidates)`: the dry-run ACTION loop copied in the three `plan()` methods.
- `log_delete_summary(noun, deleted, dry_run=, number_word=)`: the three `_log_summary` functions (ip, nic, disk), same text per kind (the NIC one keeps its capital "Number").

READMEs updated: `crc/azu/README.md`, `crc/azu/vm/README.md`, `crc/azu/spot_vm/README.md`; new short READMEs for `crc/azu/ip`, `nic`, `disk`.

### Owner action

- Cross-cloud candidates (not touched, other clouds and `crc/core` are out of lane): the `TagSpec` and `Clock` aliases and the `DeletePoller` Protocol are re-declared in many cloud modules; the "plan loop + dry-run ACTION lines + closing delete summary" pattern repeats in every cloud's ip/nic/disk cleaners; a `kept(reason)` helper (count a skip and return `(None, reason)`) could live in `crc/core` next to the logger.
- After the wave merges, the `crc/azu/*/adapter.py` classes (`IP`, `NIC`, `Disk`, `VM`, `SpotVM`) are the single-move deletion targets once `crc/cli` stops using them.
- `crc/azu/spot_vm/__init__.py` (239 lines, not in this lane) still holds the `SpotVM` adapter; it is under 250 but should move to `adapter.py` for consistency.

## New bugs

No new behavioural bugs. Quirks seen, recorded as-is and not fixed:

- `crc/azu/nic/cleaner.py:146`: `list_nics` issues the list call twice and discards the first (documented BUG-111 behaviour kept on purpose).
- `crc/azu/disk/adapter.py:30`: `Disk.default_disk_state` duplicates `DEFAULT_DISK_STATES` (`crc/azu/disk/cleaner.py`); two sources for one default.
- `crc/azu/spot_vm/config.py:35`: `log_summary` logs "No Azure Spot VMs ... to delete." and then still logs the three empty "List of ..." lines.
