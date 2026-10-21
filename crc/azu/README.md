# crc.azu

## Purpose

Legacy Azure cleaners (azure-mgmt SDK). They delete or stop leftover VMs, disks, IPs and NICs in one resource group.

**Legacy, not yet refactored.** The code is the same as on `main` (no behaviour change). Any change must follow `ARCHITECTURE.md` and the refactor rung for this package in `docs/refactor/PLAN.md` (Rung R4+), with `make check` green.

Modules (operations and filters as catalogued in `docs/refactor/FILTER_VARIANTS.md`):

- `_base.py`: `Base`: compute and network clients for a resource group
- `disk.py`: `Disk`: deletes unattached managed disks (`begin_delete`); any-key tag filter
- `ip.py`: `IP`: deletes IPs without an IP configuration (`begin_delete`); any-key tag filter
- `nic.py`: `NIC`: deletes NICs not attached to a VM; substring name filters
- `spot_vm.py`: `SpotVM`: deletes stopped or deallocated Spot VMs and their leftover disks and NICs
- `vm.py`: `VM`: deletes (via `vm_delete_helpers`) or stops (`begin_power_off`) VMs by status
- `vm_delete_helpers.py`: `begin_delete_vm_and_wait`, `delete_vm_primary_nic`: delete helpers, no filtering

## Public API

Legacy package: the names below are not synced with this README by ARCH-002 until the package
is refactored. `__init__.py` holds only a copyright comment and declares no `__all__`.

- `Base`
- `Disk`, `IP`, `NIC`, `SpotVM`, `VM` (each has `delete()`; `VM` also `stop()`)
- `begin_delete_vm_and_wait()`, `delete_vm_primary_nic()`

## Safety Invariants

- Authoritative text: `CLEANUP_SAFETY.md`. Applicable IDs: SAF-006 to SAF-013 (age gates, shared by all clouds), SAF-005, SAF-038, SAF-041, SAF-042, SAF-044.
- Filtering per module: `docs/refactor/FILTER_VARIANTS.md` sections 3 (Azure), 6 and 7.
- Known bugs and quirks (do not fix outside a behaviour-fix rung): `docs/refactor/BUGS.md` rows `BUG-002`, `BUG-003`, `BUG-004`, `BUG-010`, `BUG-013`, `BUG-019`.
- `SpotVM.delete` re-raises when the list call fails (SAF-005); Spot VMs without tags are skipped (SAF-042).
- Do not call real cloud APIs in tests; mock every SDK client.

## Extension Rules

1. Do not edit these modules to add features or fix bugs in a refactor rung; behaviour fixes are
   separate rungs (`docs/refactor/PLAN.md`).
2. New resources go in a new module with the `Cleaner` contract (`ARCHITECTURE.md`, "Add a resource
   cleaner"), not as another legacy class.
3. Refactoring a module means removing it from the ruff `extend-exclude` and mypy override lists in
   the same change (the legacy ratchet only shrinks), then updating this README and its symbol list.
4. Record every new bug or quirk in `docs/refactor/BUGS.md` with its `main` file:line.
