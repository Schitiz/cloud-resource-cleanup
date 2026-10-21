# crc.oci

## Purpose

OCI cleaners (oci SDK). They delete or stop leftover instances and volumes across regions.

**Partly refactored.** `disk.py` (rung OCI-1) is a `Cleaner` registered as `oci` / `disk` (no behaviour change); `vm.py` (rung OCI-2) is a `Cleaner` registered as `oci` / `vm` (no behaviour change); `spot_vm.py` is legacy, not yet refactored, and the same as on `main`. Any change must follow `ARCHITECTURE.md` and the refactor rung for this package in `docs/refactor/PLAN.md` (Rung R4+), with `make check` green.

Modules (operations and filters as catalogued in `docs/refactor/FILTER_VARIANTS.md`):

- `_base.py`: `Base`: identity, compute and block storage clients, region and availability domain lookup
- `connectivity.py`: `log_skipped_region`
- `disk.py`: `DiskCleaner` (registered as `oci` / `disk`) and the `Disk` adapter: deletes available block and boot volumes not attached (`delete_volume`, `delete_boot_volume`); freeform tag any-key filter
- `disk_api.py`: the typed Protocols of the OCI calls the disk cleaner uses and their SDK implementation
- `spot_vm.py`: `SpotVM`: terminates preemptible instances and deletes leftover volumes; skips OKE and instance pool members
- `vm.py`: `VmCleaner` (registered as `oci` / `vm`) and the `VM` adapter: terminates (`terminate_instance`) or stops (`instance_action` with `STOP`) `RUNNING` instances; freeform tag all-keys filter
- `vm_api.py`: the typed Protocols of the OCI calls the VM cleaner uses and their SDK implementation

## Public API

disk.py and disk_api.py are refactored, so the names below are synced with this README by
ARCH-002. vm.py and vm_api.py are refactored too. The other modules (Base, log_skipped_region, SpotVM) are legacy; SpotVM has delete(). The package __init__.py holds only a copyright comment and declares
no __all__.

- `SdkVolume`: Protocol of the attributes read from an OCI volume or boot volume.
- `SdkAttachment`: Protocol of the attributes read from a volume or boot volume attachment.
- `VolumeApi`: Protocol of the seven OCI calls the disk cleaner uses (list volumes, boot volumes, attachments, availability domains, delete volume, delete boot volume); tests pass fakes.
- `OciVolumeApi`: `VolumeApi` over the compute and block storage clients of one region; pages through every result.
- `api_for()`: builds the per-region `VolumeApi` factory on top of Base, which caches clients per region.
- `regions_of()`: builds the region lister from get_all_regions of Base.
- `DiskRuntime`: frozen dataclass with the injected API factory, region lister and clock (now) of `Disk`; unset parts come from Base.
- `DiskSettings`: frozen dataclass with the filters and thresholds of one run (filter tags, exception tags, notags, age, custom age tag key).
- `DiskCleaner`: the Cleaner (supports, read-only plan, mutating apply, plus list_region, attached_volume_ids, attached_boot_volume_ids, decide and remove used by the adapter).
- `build_disk_cleaner()`: registry factory behind @register("oci", "disk"); reads filter_tags, exception_tags, notags, age and custom_age_tag_key from RunContext.options.
- `Disk`: adapter crc.py calls (delete(), get_deleted, count, disk_names_to_delete); subclasses Service and Base; decides and deletes volume by volume in the order of main.
- `SdkInstance`: Protocol of the attributes read from an OCI compute instance.
- `ComputeApi`: Protocol of the three OCI calls the VM cleaner uses (list instances, terminate instance, stop instance); tests pass fakes.
- `OciComputeApi`: `ComputeApi` over the compute client of one region; pages through every result and maps stop to the instance_action call with the STOP action.
- `compute_api_for()`: builds the per-region `ComputeApi` factory on top of Base, which caches clients per region.
- `VmRuntime`: frozen dataclass with the injected API factory, region lister and clock (now) of `VM`; unset parts come from Base.
- `VmSettings`: frozen dataclass with the filters and thresholds of one run (filter tags, exception tags, notags, age, custom age tag key, allowed instance states).
- `VmCleaner`: the Cleaner (supports delete and stop, read-only plan, mutating apply, plus decide and act used by the adapter).
- `build_vm_cleaner()`: registry factory behind @register("oci", "vm"); reads filter_tags, exception_tags, notags, age, custom_age_tag_key and (delete only; stop always uses RUNNING, as on main) instance_state from RunContext.options.
- `VM`: adapter crc.py calls (delete(), stop(), get_deleted, get_stopped, delete_count, stopped_count, instance_names_to_delete, instance_names_to_stop); subclasses Service and Base; decides and acts instance by instance in the order of main.

## Safety Invariants

- Authoritative text: `CLEANUP_SAFETY.md`. Applicable IDs: SAF-006 to SAF-013 (age gates, shared by all clouds), SAF-037, SAF-040, SAF-041, SAF-043, SAF-044, SAF-045, SAF-046.
- Filtering per module: `docs/refactor/FILTER_VARIANTS.md` sections 5 (OCI), 6 and 7.
- Known bugs and quirks (do not fix outside a behaviour-fix rung): `docs/refactor/BUGS.md` rows `BUG-004`; new OCI disk quirks are queued in `docs/refactor/bugs/pending/OCI-1.md`, VM quirks in `docs/refactor/bugs/pending/OCI-2.md`.
- OCI disk (SAF-006 to SAF-013): `plan()` only lists and decides (ARCH-005); `apply()` is the only caller of `delete_volume` / `delete_boot_volume`; only `AVAILABLE` volumes that are not `ATTACHED` / `ATTACHING` are candidates; an empty age matches every volume (SAF-006) and `MAX_AGE` can shorten the age (SAF-010); the age of a volume with a custom age tag fails open to `--age` (SAF-009, BUG-004). A failed delete is logged and skipped, never raised, as on main.
- OCI VM (SAF-006 to SAF-013): `plan()` only lists and decides (ARCH-005); `apply()` is the only caller of `terminate_instance` / `stop_instance`; only instances in an allowed state (`RUNNING` by default) are candidates; `filter_tags` needs every key (`FILTER_VARIANTS.md`); an empty age matches every instance (SAF-006) and `MAX_AGE` can shorten the age (SAF-010); the age of an instance with a custom age tag fails open to `--age` (SAF-009, BUG-004). A failed terminate or stop is logged and skipped, never raised, as on main; list and region errors are not isolated per instance (connectivity errors skip the region, other errors propagate). New VM quirks are queued in `docs/refactor/bugs/pending/OCI-2.md`.
- OCI Spot VMs skip OKE and instance pool members (SAF-045); `--resource spot_instances` needs an explicit `--cloud oci` (SAF-037).
- Do not call real cloud APIs in tests; mock every SDK client.

## Extension Rules

1. Do not edit the legacy module (`spot_vm.py`) to add features or fix bugs in a refactor
   rung; behaviour fixes are separate rungs (`docs/refactor/PLAN.md`).
2. New resources go in a new module with the `Cleaner` contract (`ARCHITECTURE.md`, "Add a resource
   cleaner"), not as another legacy class. Follow `disk.py` and `vm.py`: pure policy from `crc.core.policy`,
   age from `crc.core.age`, SDK calls behind a Protocol in a `*_api.py` module, injected through the
   constructor.
3. `plan()` of `DiskCleaner` and `VmCleaner` stays read-only: every mutating call belongs in `apply()` / `remove()`.
4. Refactoring a module means removing it from the ruff `extend-exclude` and mypy override lists in
   the same change (the legacy ratchet only shrinks), then updating this README and its symbol list.
5. Record every new bug or quirk in `docs/refactor/BUGS.md` with its `main` file:line (parallel
   lanes use `docs/refactor/bugs/pending/`).
