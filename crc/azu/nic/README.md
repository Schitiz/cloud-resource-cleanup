# crc.azu.nic

## Purpose

Azure NIC cleaner. `AzureNicCleaner` is a registered `Cleaner` (`@register("azure", "nic")`) that deletes NICs not in use whose name matches `name_regex`; `NIC` is the adapter `crc.py` uses.

Modules (split by responsibility in W2-AZU, no behaviour change):

- `client.py`: SDK Protocols
- `cleaner.py`: `AzureNicCleaner`, pattern compilation and the registry factory
- `adapter.py`: the legacy `NIC` class

## Public API

- `NicOperations`: Protocol of the two network_interfaces calls used, list and begin_delete (positional arguments); tests pass fakes.
- `NicNetworkClient`: Protocol of the network client part used (the network_interfaces operations).
- `AzureNicCleaner`: the Cleaner (supports, read-only plan, mutating apply, plus prepare (compiles name_regex / exception_regex, ValueError before any SDK call), list_nics, decide and attempt_delete used by the adapter); the client factory is injected through the constructor.
- `build_nic_cleaner()`: registry factory behind @register("azure", "nic"); reads resource_group, name_regex and exception_regex from RunContext.options and builds the client from the Azure base.
- `NIC`: adapter crc.py calls (delete(), get_deleted, delete_count, nics_names_to_delete, base); runs the cleaner NIC by NIC in the order of main.
- `DeletePoller`: Protocol of the handle begin_delete returns (result()).
- `log_none_to_delete()`: logs the "No Azure NICs to delete." warning (shared by the cleaner and the adapter).
- `DELETE_ATTEMPTS`: the three delete attempts per NIC.

## Safety Invariants

- Authoritative text: `CLEANUP_SAFETY.md`; the per-module invariants are in `crc/azu/README.md` (Azure NICs (AZ-2)). `plan()` makes no mutating call and never in a dry run (ARCH-005); the delete calls run from `apply()` and the adapter only.
- Patterns are compiled before any SDK call (`ValueError` when invalid); a failed delete is retried three times, logged and swallowed; no tag filter and no age gate (SAF-011 not met).
- Do not call real cloud APIs in tests; mock every SDK client.

## Extension Rules

1. Structure only in a refactor rung: keep call order, log text and swallowed errors as on `main`; behaviour fixes are separate rungs (`docs/refactor/PLAN.md`).
2. Reach the SDK only through the Protocols in `client.py`; shared log and skip helpers live in `crc/azu/_common.py`.
3. `from crc.azu.nic import ...` must keep working for every public name; update this README with any public change.
