# crc.azu

## Purpose

Legacy Azure cleaners (azure-mgmt SDK). They delete or stop leftover VMs, disks, IPs and NICs in one resource group.

**Mostly legacy.** `ip.py` (rung AZ-1), `nic.py` (rung AZ-2), `disk.py` (rung AZ-3), `vm/` (rung AZ-4) and `spot_vm/` (rung AZ-5) are refactored into registered `Cleaner`s; the other modules are the same as on `main` (no behaviour change). Any change must follow `ARCHITECTURE.md` and the refactor rung for this package in `docs/refactor/PLAN.md` (Rung R4+), with `make check` green.

Modules (operations and filters as catalogued in `docs/refactor/FILTER_VARIANTS.md`):

- `_base.py`: `Base`: compute and network clients for a resource group
- `disk.py`: `AzureDiskCleaner` (registered as `azure`/`disk`) and the legacy adapter `Disk`: deletes unattached managed disks (`begin_delete`); any-key tag filter, age gate
- `ip.py`: `AzureIpCleaner` (registered as `azure`/`ip`) and the legacy adapter `IP`: deletes IPs without an IP configuration (`begin_delete`); any-key tag filter
- `nic.py`: `AzureNicCleaner` (registered as `azure`/`nic`) and the legacy adapter `NIC`: deletes NICs not attached to a VM (`begin_delete(...).result()`, three attempts); plain substring name filters
- `spot_vm/`: `AzureSpotVmCleaner` (registered as `azure`/`spot_instances`) and the legacy adapter `SpotVM`: deletes stopped or deallocated Spot VMs and their leftover disks and NICs (subpackage with its own README, rung AZ-5)
- `vm/`: subpackage (own README): `VmCleaner` (registered as `azure`/`vm`) and the legacy adapter `VM`: deletes (via `vm_delete_helpers`) or stops (`begin_power_off`) VMs by status; `from crc.azu.vm import VM` still works
- `vm_delete_helpers.py`: `begin_delete_vm_and_wait`, `delete_vm_primary_nic`: delete helpers, no filtering

## Public API

The ip, nic and disk modules are refactored, so the names below are synced with this README by ARCH-002.
The vm and spot_vm subpackages document their own API in their own READMEs. The other modules (Base, begin_delete_vm_and_wait, delete_vm_primary_nic) are
legacy. The package init holds only a
copyright comment and declares no export list.

- `PublicIpOperations`: Protocol of the two public IP calls used, list_all and begin_delete; tests pass fakes.
- `IpNetworkClient`: Protocol of the network client part used (the public_ip_addresses operations).
- `AzureIpCleaner`: the Cleaner (supports, read-only plan, mutating apply, plus list_ips, decide and delete_candidate used by the adapter); the client factory is injected through the constructor.
- `build_ip_cleaner()`: registry factory behind @register("azure", "ip"); reads resource_group, filter_tags, exception_tags and notags from RunContext.options and builds the client from the legacy Base.
- `IP`: adapter crc.py calls (delete(), get_deleted, count, deleted_ips, base); runs the cleaner IP by IP in the order of main.
- `DeletePoller`: Protocol of the handle begin_delete returns (result()).
- `NicOperations`: Protocol of the two network_interfaces calls used, list_all and begin_delete (positional arguments); tests pass fakes.
- `NicNetworkClient`: Protocol of the network client part used (the network_interfaces operations).
- `AzureNicCleaner`: the Cleaner (supports, read-only plan, mutating apply, plus list_nics, decide and attempt_delete used by the adapter); the client factory is injected through the constructor.
- `build_nic_cleaner()`: registry factory behind @register("azure", "nic"); reads resource_group, name_regex and exception_regex from RunContext.options and builds the client from the legacy Base.
- `NIC`: adapter crc.py calls (delete(), get_deleted, delete_count, nics_names_to_delete, base); runs the cleaner NIC by NIC in the order of main.
- `SdkDisk`: Protocol of the Azure disk fields read (name, tags, time_created, disk_state).
- `DiskOperations`: Protocol of the two disks calls used, list and begin_delete (positional arguments); tests pass fakes.
- `DiskComputeClient`: Protocol of the compute client part used (the disks operations).
- `DiskSettings`: frozen dataclass of the filters and age gate (filter_tags, exception_tags, notags, age, custom_age_tag_key, disk_states).
- `AzureDiskCleaner`: the Cleaner (supports, read-only plan, mutating apply, plus list_disks, decide and delete_disk used by the adapter); the client factory is injected through the constructor.
- `build_disk_cleaner()`: registry factory behind @register("azure", "disk"); reads resource_group, filter_tags, exception_tags, notags, age and custom_age_tag_key from RunContext.options and builds the client from the legacy Base.
- `Disk`: adapter crc.py calls (delete(), get_deleted, count, disks_names_to_delete, base, clock); runs the cleaner disk by disk in the order of main, reading the clock once per listed disk (main reads it once per tag-matching disk).

## Safety Invariants

- Authoritative text: `CLEANUP_SAFETY.md`. Applicable IDs: SAF-006 to SAF-013 (age gates, shared by all clouds), SAF-005, SAF-038, SAF-041, SAF-042, SAF-044.
- Filtering per module: `docs/refactor/FILTER_VARIANTS.md` sections 3 (Azure), 6 and 7.
- Known bugs and quirks (do not fix outside a behaviour-fix rung): `docs/refactor/BUGS.md` rows `BUG-002`, `BUG-003`, `BUG-004`, `BUG-010`, `BUG-013`, `BUG-019`.
- Azure IPs (AZ-1): `plan()` only calls `list_all`; `begin_delete` is called from `apply()` (and `IP.delete()`) only and never in a dry run. There is no age gate (SAF-011 is not met: an empty `filter_tags` selects every unattached IP) and `list_all` is subscription-wide while the delete uses the configured resource group; untagged IPs raise `TypeError` when `exception_tags` or `notags` is set (BUG-013). Nothing is isolated per IP: every error propagates and a later error leaves earlier IPs deleted. Quirks in `docs/refactor/bugs/pending/AZ-1.md`.
- Azure NICs (AZ-2): `plan()` only calls `list_all` (twice, as main does); `begin_delete(...).result()` is called from `apply()` (and `NIC.delete()`) only and never in a dry run. An empty `name_regex` logs a warning and returns before any call. Selection is any unattached NIC (`virtual_machine` falsy) whose name contains a `name_regex` entry and no `exception_regex` entry (plain substrings, not regexes). There is no tag filter and no age gate (SAF-011 is not met), `list_all` is subscription-wide while the delete uses the configured resource group, and a failed delete is retried up to three times, logged and swallowed (the NIC is then missing from `get_deleted` and the run still succeeds). Quirks in `docs/refactor/bugs/pending/AZ-2.md`.
- Azure disks (AZ-3): `plan()` only calls `disks.list`; `disks.begin_delete(resource_group, name)` is called from `apply()` (and `Disk.delete()`) only and never in a dry run. Selection (an empty `filter_tags` selects every disk, so SAF-011 is not met by the tag filter): `filter_tags` any key (empty selects all, untagged disks match only when no filter), `exception_tags` any key, `notags` all keys, age through `core_age.get_retention_age` (custom age tag fails open, BUG-004) and `core_age.is_old`, then the state test, which is a substring test (BUG-019). Nothing is isolated per disk: every error propagates and earlier disks stay deleted; the delete poller is not awaited; `list` is subscription-wide while the delete uses the configured resource group. Quirks in `docs/refactor/bugs/pending/AZ-3.md`.
- Azure VMs (AZ-4): see `crc/azu/vm/README.md`. `plan()` only calls `list_all` and `instance_view`; the VM and NIC deletes and `begin_power_off` run from `apply()` (and `VM.delete()` / `VM.stop()`) only, never in a dry run. Untagged VMs are skipped (SAF-042), age goes through `crc.core.age`, per-VM errors are logged and swallowed, and BUG-002, BUG-003, BUG-010 are preserved. Quirks in `docs/refactor/bugs/pending/AZ-4.md`.
- Azure Spot VMs (AZ-5): see `crc/azu/spot_vm/README.md`; `plan()` is read-only, `SpotVM.delete` re-raises when the list call fails (SAF-005), Spot VMs without tags are skipped (SAF-042).
- Do not call real cloud APIs in tests; mock every SDK client.

## Extension Rules

1. Do not edit these modules to add features or fix bugs in a refactor rung; behaviour fixes are
   separate rungs (`docs/refactor/PLAN.md`).
2. New resources go in a new module with the `Cleaner` contract (`ARCHITECTURE.md`, "Add a resource
   cleaner"), not as another legacy class.
3. A new or refactored module follows `ip.py`, `nic.py`, `disk.py`, `vm/` and `spot_vm/`: a Cleaner with an injected client Protocol, `@register("azure", ...)`, a parity test against a frozen oracle in `tests/legacy/`. Refactoring a module means removing it from the ruff `extend-exclude` and mypy override lists in
   the same change (the legacy ratchet only shrinks), then updating this README and its symbol list.
4. Record every new bug or quirk in `docs/refactor/BUGS.md` with its `main` file:line.
