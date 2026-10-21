# crc.azu

## Purpose

Legacy Azure cleaners (azure-mgmt SDK). They delete or stop leftover VMs, disks, IPs and NICs in one resource group.

**Mostly legacy.** `ip.py` is refactored (rung AZ-1) into a registered `Cleaner`; the other modules are the same as on `main` (no behaviour change). Any change must follow `ARCHITECTURE.md` and the refactor rung for this package in `docs/refactor/PLAN.md` (Rung R4+), with `make check` green.

Modules (operations and filters as catalogued in `docs/refactor/FILTER_VARIANTS.md`):

- `_base.py`: `Base`: compute and network clients for a resource group
- `disk.py`: `Disk`: deletes unattached managed disks (`begin_delete`); any-key tag filter
- `ip.py`: `AzureIpCleaner` (registered as `azure`/`ip`) and the legacy adapter `IP`: deletes IPs without an IP configuration (`begin_delete`); any-key tag filter
- `nic.py`: `NIC`: deletes NICs not attached to a VM; substring name filters
- `spot_vm.py`: `SpotVM`: deletes stopped or deallocated Spot VMs and their leftover disks and NICs
- `vm.py`: `VM`: deletes (via `vm_delete_helpers`) or stops (`begin_power_off`) VMs by status
- `vm_delete_helpers.py`: `begin_delete_vm_and_wait`, `delete_vm_primary_nic`: delete helpers, no filtering

## Public API

The ip module is refactored, so the names below are synced with this README by ARCH-002. The other
modules (Base, Disk, NIC, SpotVM, VM, begin_delete_vm_and_wait, delete_vm_primary_nic) are legacy:
each of Disk, NIC, SpotVM and VM has delete(), VM also stop(). The package init holds only a
copyright comment and declares no export list.

- `PublicIpOperations`: Protocol of the two public IP calls used, list_all and begin_delete; tests pass fakes.
- `IpNetworkClient`: Protocol of the network client part used (the public_ip_addresses operations).
- `AzureIpCleaner`: the Cleaner (supports, read-only plan, mutating apply, plus list_ips, decide and delete_candidate used by the adapter); the client factory is injected through the constructor.
- `build_ip_cleaner()`: registry factory behind @register("azure", "ip"); reads resource_group, filter_tags, exception_tags and notags from RunContext.options and builds the client from the legacy Base.
- `IP`: adapter crc.py calls (delete(), get_deleted, count, deleted_ips, base); runs the cleaner IP by IP in the order of main.

## Safety Invariants

- Authoritative text: `CLEANUP_SAFETY.md`. Applicable IDs: SAF-006 to SAF-013 (age gates, shared by all clouds), SAF-005, SAF-038, SAF-041, SAF-042, SAF-044.
- Filtering per module: `docs/refactor/FILTER_VARIANTS.md` sections 3 (Azure), 6 and 7.
- Known bugs and quirks (do not fix outside a behaviour-fix rung): `docs/refactor/BUGS.md` rows `BUG-002`, `BUG-003`, `BUG-004`, `BUG-010`, `BUG-013`, `BUG-019`.
- Azure IPs (AZ-1): `plan()` only calls `list_all`; `begin_delete` is called from `apply()` (and `IP.delete()`) only and never in a dry run. There is no age gate (SAF-006 is not met: an empty `filter_tags` selects every unattached IP) and `list_all` is subscription-wide while the delete uses the configured resource group; untagged IPs raise `TypeError` when `exception_tags` or `notags` is set (BUG-013). Nothing is isolated per IP: every error propagates and a later error leaves earlier IPs deleted. Quirks in `docs/refactor/bugs/pending/AZ-1.md`.
- `SpotVM.delete` re-raises when the list call fails (SAF-005); Spot VMs without tags are skipped (SAF-042).
- Do not call real cloud APIs in tests; mock every SDK client.

## Extension Rules

1. Do not edit these modules to add features or fix bugs in a refactor rung; behaviour fixes are
   separate rungs (`docs/refactor/PLAN.md`).
2. New resources go in a new module with the `Cleaner` contract (`ARCHITECTURE.md`, "Add a resource
   cleaner"), not as another legacy class.
3. A new or refactored module follows `ip.py`: a Cleaner with an injected client Protocol, `@register("azure", ...)`, a parity test against a frozen oracle in `tests/legacy/`. Refactoring a module means removing it from the ruff `extend-exclude` and mypy override lists in
   the same change (the legacy ratchet only shrinks), then updating this README and its symbol list.
4. Record every new bug or quirk in `docs/refactor/BUGS.md` with its `main` file:line.
