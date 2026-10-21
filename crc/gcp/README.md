# crc.gcp

## Purpose

Legacy GCP cleaners (google-cloud-compute). They delete or stop leftover instances, disks and addresses.

**Legacy, not yet refactored.** The code is the same as on `main` (no behaviour change). Any change must follow `ARCHITECTURE.md` and the refactor rung for this package in `docs/refactor/PLAN.md` (Rung R4+), with `make check` green.

Modules (operations and filters as catalogued in `docs/refactor/FILTER_VARIANTS.md`):

- `_base.py`: `get_gcp_regions`
- `disk.py`: `Disk`: deletes unattached disks by `last_detach_timestamp`; label any-key filter; `notags`, `name_regex` and `age` are not used
- `ip.py`: `IP`: deletes RESERVED addresses; substring name filters, exception filter inverted
- `spot_vm.py`: `SpotVM`: deletes preemptible or Spot VMs and leftover disks; skips GKE and managed instance group members
- `vm.py`: `VM`: deletes or stops (`stop`) RUNNING instances by labels

## Public API

Legacy package: the names below are not synced with this README by ARCH-002 until the package
is refactored. `__init__.py` holds only a copyright comment and declares no `__all__`.

- `get_gcp_regions()`
- `Disk`, `IP`, `SpotVM`, `VM` (each has `delete()`; `VM` also `stop()`)

## Safety Invariants

- Authoritative text: `CLEANUP_SAFETY.md`. Applicable IDs: SAF-006 to SAF-013 (age gates, shared by all clouds), SAF-021 to SAF-024, SAF-037, SAF-039, SAF-041, SAF-043, SAF-044, SAF-045.
- Filtering per module: `docs/refactor/FILTER_VARIANTS.md` sections 4 (GCP), 6 and 7.
- Known bugs and quirks (do not fix outside a behaviour-fix rung): `docs/refactor/BUGS.md` rows `BUG-001`, `BUG-004`, `BUG-005`, `BUG-006`, `BUG-023`.
- `GCP_Disk` uses `--detach_age`, never `--age` (SAF-021, SAF-022); Spot VMs skip GKE and instance group members (SAF-045).
- Do not call real cloud APIs in tests; mock every SDK client.

## Extension Rules

1. Do not edit these modules to add features or fix bugs in a refactor rung; behaviour fixes are
   separate rungs (`docs/refactor/PLAN.md`).
2. New resources go in a new module with the `Cleaner` contract (`ARCHITECTURE.md`, "Add a resource
   cleaner"), not as another legacy class.
3. Refactoring a module means removing it from the ruff `extend-exclude` and mypy override lists in
   the same change (the legacy ratchet only shrinks), then updating this README and its symbol list.
4. Record every new bug or quirk in `docs/refactor/BUGS.md` with its `main` file:line.
