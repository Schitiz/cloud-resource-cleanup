# crc.oci

## Purpose

Legacy OCI cleaners (oci SDK). They delete or stop leftover instances and volumes across regions.

**Legacy, not yet refactored.** The code is the same as on `main` (no behaviour change). Any change must follow `ARCHITECTURE.md` and the refactor rung for this package in `docs/refactor/PLAN.md` (Rung R4+), with `make check` green.

Modules (operations and filters as catalogued in `docs/refactor/FILTER_VARIANTS.md`):

- `_base.py`: `Base`: identity, compute and block storage clients, region and availability domain lookup
- `connectivity.py`: `log_skipped_region`
- `disk.py`: `Disk`: deletes available block and boot volumes not attached; freeform tag any-key filter
- `spot_vm.py`: `SpotVM`: terminates preemptible instances and deletes leftover volumes; skips OKE and instance pool members
- `vm.py`: `VM`: terminates (`terminate_instance`) or stops (`instance_action`) RUNNING instances

## Public API

Legacy package: the names below are not synced with this README by ARCH-002 until the package
is refactored. `__init__.py` holds only a copyright comment and declares no `__all__`.

- `Base`, `log_skipped_region()`
- `Disk`, `SpotVM`, `VM` (each has `delete()`; `VM` also `stop()`)

## Safety Invariants

- Authoritative text: `CLEANUP_SAFETY.md`. Applicable IDs: SAF-006 to SAF-013 (age gates, shared by all clouds), SAF-037, SAF-040, SAF-041, SAF-043, SAF-044, SAF-045, SAF-046.
- Filtering per module: `docs/refactor/FILTER_VARIANTS.md` sections 5 (OCI), 6 and 7.
- Known bugs and quirks (do not fix outside a behaviour-fix rung): `docs/refactor/BUGS.md` rows `BUG-004`.
- OCI Spot VMs skip OKE and instance pool members (SAF-045); `--resource spot_instances` needs an explicit `--cloud oci` (SAF-037).
- Do not call real cloud APIs in tests; mock every SDK client.

## Extension Rules

1. Do not edit these modules to add features or fix bugs in a refactor rung; behaviour fixes are
   separate rungs (`docs/refactor/PLAN.md`).
2. New resources go in a new module with the `Cleaner` contract (`ARCHITECTURE.md`, "Add a resource
   cleaner"), not as another legacy class.
3. Refactoring a module means removing it from the ruff `extend-exclude` and mypy override lists in
   the same change (the legacy ratchet only shrinks), then updating this README and its symbol list.
4. Record every new bug or quirk in `docs/refactor/BUGS.md` with its `main` file:line.
