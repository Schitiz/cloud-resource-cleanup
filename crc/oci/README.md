# crc.oci

## Purpose

OCI cleaners (oci SDK). They delete or stop leftover instances and volumes across regions.

**Partly refactored.** `disk/` (rung OCI-1, a subpackage since rung ST-OCI-DISK) is a `Cleaner` registered as `oci` / `disk` (no behaviour change; see its README); `vm.py` (rung OCI-2) is a `Cleaner` registered as `oci` / `vm` (no behaviour change); `spot_vm/` (rung OCI-3) is a subpackage with a `Cleaner` registered as `oci` / `spot_instances` (no behaviour change; see its README); the shared helpers `connectivity.py` and `__init__.py` (rung PL-OCI) are strict-clean (no behaviour change); `_base.py` is typed and parity-tested but stays legacy because it reads `os.environ`, which ARCH-003 bans in non-legacy cloud modules. Any change must follow `ARCHITECTURE.md` and the refactor rung for this package in `docs/refactor/PLAN.md` (Rung R4+), with `make check` green.

Modules (operations and filters as catalogued in `docs/refactor/FILTER_VARIANTS.md`):

- `_base.py` (legacy; typed and parity-tested in rung PL-OCI, kept on the ratchet for its environment read): `Base`: API signing key config from `OCI_PRIVATE_KEY_CONTENT` / `OCI_PRIVATE_KEY_FILE`, identity, compute and block storage clients cached per region, region and availability domain lookup
- `connectivity.py` (refactored, rung PL-OCI): `CONNECTIVITY_ERRORS` and `log_skipped_region`
- `disk/`: the disk cleaner subpackage (`DiskCleaner` registered as `oci` / `disk`, the `Disk` adapter and the SDK Protocols); deletes available block and boot volumes not attached; freeform tag any-key filter
- `spot_vm/`: the Spot VM cleaner subpackage (`SpotVmCleaner`, the `SpotVM` adapter, the SDK Protocols and the leftover volume handling); terminates preemptible instances and deletes leftover volumes; skips OKE and instance pool members
- `vm.py`: `VmCleaner` (registered as `oci` / `vm`) and the `VM` adapter: terminates (`terminate_instance`) or stops (`instance_action` with `STOP`) `RUNNING` instances; freeform tag all-keys filter
- `vm_api.py`: the typed Protocols of the OCI calls the VM cleaner uses and their SDK implementation

## Public API

vm.py and vm_api.py are refactored, so the names below are synced with this README by
ARCH-002; so are the shared helpers connectivity.py and __init__.py (rung PL-OCI). _base.py (Base) is legacy: it reads the private key environment variables, which ARCH-003 bans in non-legacy cloud modules. The disk and spot_vm subpackages have their own README and symbol list. The package __init__.py holds only a copyright comment and declares
no __all__.

- `log_skipped_region()`: logs the warning that a region (or one call in it) was skipped for a connectivity error; used with CONNECTIVITY_ERRORS, the tuple of the three SDK errors (ConnectTimeout, RequestException, ServiceError) that skip a region.
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
- Known bugs and quirks (do not fix outside a behaviour-fix rung): `docs/refactor/BUGS.md` rows `BUG-004`; new OCI disk quirks are queued in `docs/refactor/bugs/pending/OCI-1.md` and `docs/refactor/bugs/pending/ST-OCI-DISK.md`, VM quirks in `docs/refactor/bugs/pending/OCI-2.md`.
- OCI disk (SAF-006 to SAF-013): see `crc/oci/disk/README.md`.
- OCI VM (SAF-006 to SAF-013): `plan()` only lists and decides (ARCH-005); `apply()` is the only caller of `terminate_instance` / `stop_instance`; only instances in an allowed state (`RUNNING` by default) are candidates; `filter_tags` needs every key (`FILTER_VARIANTS.md`); an empty age matches every instance (SAF-006) and `MAX_AGE` can shorten the age (SAF-010); the age of an instance with a custom age tag fails open to `--age` (SAF-009, BUG-004). A failed terminate or stop is logged and skipped, never raised, as on main; list and region errors are not isolated per instance (connectivity errors skip the region, other errors propagate). New VM quirks are queued in `docs/refactor/bugs/pending/OCI-2.md`.
- OCI Spot VMs skip OKE and instance pool members (SAF-045); `--resource spot_instances` needs an explicit `--cloud oci` (SAF-037).
- OCI shared helpers (`Base`, `connectivity.py`; no SAF ID names them, the AWS analogues are SAF-001 and SAF-004; parity-tested against `tests/legacy/oci_base.txt` and `tests/legacy/oci_connectivity.txt`): `Base()` fails closed before any SDK call when neither `OCI_PRIVATE_KEY_CONTENT` nor `OCI_PRIVATE_KEY_FILE` is set (KeyError; the content wins when both are set); the compartment, tenancy, user and fingerprint are constants, so only that compartment is ever listed; clients are built once per region and cached; `get_all_regions` falls back to the home region `us-sanjose-1` only when `list_region_subscriptions` raises a connectivity error (`ConnectTimeout`, `RequestException` or any `ServiceError`, so an auth error also takes that path, `BUG-101`, `BUG-107`) and propagates every other error; `get_availability_domains` does not catch anything and caches only on success. New quirks of these modules are queued in `docs/refactor/bugs/pending/PL-OCI.md`.
- Do not call real cloud APIs in tests; mock every SDK client.

## Extension Rules

1. Do not edit the modules to add features or fix bugs in a refactor rung; behaviour fixes are
   separate rungs (`docs/refactor/PLAN.md`).
2. New resources go in a new module with the `Cleaner` contract (`ARCHITECTURE.md`, "Add a resource
   cleaner"), not as another legacy class. Follow `disk/` and `vm.py`: pure policy from `crc.core.policy`,
   age from `crc.core.age`, SDK calls behind a Protocol in a `*_api.py` module, injected through the
   constructor.
3. `plan()` of `VmCleaner` (and `DiskCleaner`, see `disk/README.md`) stays read-only: every mutating call belongs in `apply()` / `remove()`.
4. Refactoring a module means removing it from the ruff `extend-exclude` and mypy override lists in
   the same change (the legacy ratchet only shrinks), then updating this README and its symbol list.
5. Record every new bug or quirk in `docs/refactor/BUGS.md` with its `main` file:line (parallel
   lanes use `docs/refactor/bugs/pending/`).
