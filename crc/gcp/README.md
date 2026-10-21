# crc.gcp

## Purpose

Legacy GCP cleaners (google-cloud-compute). They delete or stop leftover instances, disks and addresses.

**Partly refactored.** `ip.py` (GCP-1) is a `Cleaner` (no behaviour change); every other module is legacy, not yet refactored, and the same as on `main`. Any change must follow `ARCHITECTURE.md` and the refactor rung for this package in `docs/refactor/PLAN.md` (Rung R4+), with `make check` green.

Modules (operations and filters as catalogued in `docs/refactor/FILTER_VARIANTS.md`):

- `_base.py`: `get_gcp_regions`
- `disk.py`: `Disk`: deletes unattached disks by `last_detach_timestamp`; label any-key filter; `notags`, `name_regex` and `age` are not used
- `ip.py`: `IpCleaner` (registered as `gcp` / `ip`) and the `IP` adapter: deletes RESERVED addresses (`AddressesClient().delete`); substring name filters, exception filter inverted
- `spot_vm.py`: `SpotVM`: deletes preemptible or Spot VMs and leftover disks; skips GKE and managed instance group members
- `vm.py`: `VM`: deletes or stops (`stop`) RUNNING instances by labels

## Public API

ip.py is refactored, so the names below are synced with this README by ARCH-002. The other
modules (get_gcp_regions, Disk, SpotVM, VM) are legacy; each has delete(), VM also stop().
__init__.py holds only a copyright comment and declares no __all__.

- `AddressView`: Protocol of the two address fields read (name, status); tests pass fakes.
- `GcpIpClient`: Protocol of the three Compute Engine calls used (list_regions, list_addresses, delete_address); tests pass fakes.
- `ComputeIpClient`: the google-cloud-compute implementation of `GcpIpClient`; like main it builds a new RegionsClient or AddressesClient for every call.
- `IpCleaner`: the Cleaner (supports, read-only plan, mutating apply, plus regions, plan_region and apply_region used by the adapter).
- `build_ip_cleaner()`: registry factory behind @register("gcp", "ip"); reads project_id, name_regex and exception_regex from RunContext.options and raises ValueError without a project_id.
- `IP`: adapter crc.py calls (delete(), get_deleted, count, deleted_ips, default_state); runs the cleaner region by region in the order of main. The optional fifth constructor argument injects a client.

## Safety Invariants

- Authoritative text: `CLEANUP_SAFETY.md`. Applicable IDs: SAF-006 to SAF-013 (age gates, shared by all clouds), SAF-021 to SAF-024, SAF-037, SAF-039, SAF-041, SAF-043, SAF-044, SAF-045.
- Filtering per module: `docs/refactor/FILTER_VARIANTS.md` sections 4 (GCP), 6 and 7.
- Known bugs and quirks (do not fix outside a behaviour-fix rung): `docs/refactor/BUGS.md` rows `BUG-001`, `BUG-004`, `BUG-005`, `BUG-006`, `BUG-023`.
- `GCP_Disk` uses `--detach_age`, never `--age` (SAF-021, SAF-022); Spot VMs skip GKE and instance group members (SAF-045).
- GCP IP (GCP-1): `plan()` only calls `RegionsClient().list` and `AddressesClient().list`; `AddressesClient().delete` is called from `apply_region()` only and never in a dry run. There is no age gate and no tag filter, so the name filter is the only protection: an empty `filter_regex` selects every RESERVED address (`policy.filter_substring_matches`), and the exception filter is inverted (`policy.gcp_ip_exception_excludes`, BUG-001). No SAF ID is specific to this module. Region and address listing errors and delete errors propagate unchanged (nothing is isolated or skipped, there is no connectivity fallback); a delete error loses the record of the addresses of that region already deleted. `IP.delete()` keeps the call order of `main` (per region: list, filter, deletes); the registered Cleaner lists every region first, then deletes. Quirks are in `docs/refactor/bugs/pending/GCP-1.md`.
- Do not call real cloud APIs in tests; mock every SDK client.

## Extension Rules

1. Do not edit these modules to add features or fix bugs in a refactor rung; behaviour fixes are
   separate rungs (`docs/refactor/PLAN.md`).
2. New resources go in a new module with the `Cleaner` contract (`ARCHITECTURE.md`, "Add a resource
   cleaner"), not as another legacy class.
3. Refactoring a module means removing it from the ruff `extend-exclude` and mypy override lists in
   the same change (the legacy ratchet only shrinks), then updating this README and its symbol list.
4. GCP IP changes need `tests/test_gcp_ip_parity.py` (oracle `tests/legacy/gcp_ip.txt`, a frozen copy of `main`, never edit it) to stay green.
5. Record every new bug or quirk in `docs/refactor/BUGS.md` with its `main` file:line.
