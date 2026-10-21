## Coding summary

**Rung OCI-1: `crc/oci/disk.py` is a registered `Cleaner` (`@register("oci", "disk")`). Status: done, `make check` green.**

- **What changed.** `DiskCleaner` (`plan()` lists regions, volumes, boot volumes and attachments and decides; `apply()` calls `delete_volume` / `delete_boot_volume`). `Disk` keeps its name, constructor (plus an optional trailing `runtime: DiskRuntime | None`), attributes (`disk_names_to_delete`, `dry_run`, `filter_tags`, `exception_tags`, `age`, `custom_age_tag_key`, `notags`), `get_deleted`, `count` and `delete()`, and still subclasses `Service` and `Base`. `crc.py` is unchanged. The OCI SDK sits behind the `VolumeApi` Protocol in the new `crc/oci/disk_api.py` (split out because ARCH-004 caps files at 400 lines); `Base` still builds the clients and caches them per region, so SDK call order is the same as on main. Filtering uses `policy.normalize_tags`, `policy.should_skip_by_tags` (exception any, notags all) and `policy.filter_tags_any_key`; age uses `core_age.get_retention_age`, `policy.effective_age` and `core_age.is_old`.
- **Parity.** `tests/legacy/oci_disk.txt` is the exact `git show main:crc/oci/disk.py`. `tests/test_oci_disk_parity.py` runs 77 cases twice (the `Disk` adapter and the registered Cleaner via `plan()` then `apply()`) plus a quirk table. The adapter path matches main on SDK calls in order, results, counts, log records, stdout and errors. The Cleaner path matches on results, stdout, error type and message, the non-mutating calls in order, the delete calls in order, the multiset of log records and the summary lines. Differences by design, all in the Cleaner path only: all reads precede all deletes; per-volume log lines are therefore not interleaved with "Deleting ..." lines; on an error raised mid-run `plan()` fails before any delete while main may have deleted earlier volumes (pending bug 9); `count` logging exists only on the adapter. Region-listing errors (connectivity and auth fall back to `us-sanjose-1`, unexpected errors propagate) are covered.
- **Tests.** Before: 2703 passed. After: 2913 passed (+210): 188 in `tests/test_oci_disk_parity.py`, 22 in `tests/test_oci_disk.py` (plan read-only, apply, registry, real pagination). Every existing test passes unchanged. `ruff check .`, `mypy` (strict) and `lint-imports` are clean.
- **pyproject.toml.** Removed `crc/oci/disk.py` from the ruff `extend-exclude` and `crc.oci.disk` from the mypy override list; added one per-SDK override `module = ["oci", "oci.*"]` with `ignore_missing_imports = true` (the oci package ships no `py.typed`). Nothing was added to the ratchet. `disk_api.py` is a new, checked module.
- **Open issues.** 12 new bugs and quirks (two high: a connectivity or auth error while listing attachments leaves the attached set empty so attached volumes are deleted) are in `docs/refactor/bugs/pending/OCI-1.md`; BUG-004 (fail-open custom age tag) applies to this module and is unchanged. I had to create `docs/refactor/bugs/README.md` and `docs/refactor/bugs/pending/README.md` because ARCH-002 requires a README in every docs directory with files; other lanes will likely add the same two files (resolve add/add conflicts by keeping either).
- **Needed changes outside this lane (not made).**
  - `crc/README.md` and `crc/core/README.md`: say that `oci` / `disk` is now registered (they list only `aws` keypair, ip and kms).
  - `docs/refactor/FILTER_VARIANTS.md`, `crc/oci/disk.py` row in section 5: since OCI-1 the module filters through `policy.should_skip_by_tags`, `policy.filter_tags_any_key` and `policy.effective_age` (line numbers still cite `main`, frozen in `tests/legacy/oci_disk.txt`); no variant changed, so no new policy function was needed and `crc/core/**` is untouched.
  - `tests/README.md` and `tests/legacy/README.md`: list `test_oci_disk.py`, `test_oci_disk_parity.py` and the `oci_disk.txt` oracle.
  - `docs/refactor/STATUS.md`: record rung OCI-1.

## Round 1 (Argon)

Scope reviewed: `git diff 9b5c85a..HEAD` (`crc/oci/disk.py`, `crc/oci/disk_api.py`, `crc/oci/README.md`, `pyproject.toml`, `docs/refactor/bugs/pending/OCI-1.md`, `docs/refactor/bugs/README.md`, `docs/refactor/bugs/pending/README.md`, `tests/legacy/oci_disk.txt`, `tests/test_oci_disk.py`, `tests/test_oci_disk_parity.py`) against `git show main:crc/oci/disk.py`, `AGENTS.md`, `docs/refactor/BUGS.md`, `docs/refactor/FILTER_VARIANTS.md`, and `.cursor/skills/crc-python-refactor/REVIEW_CHECKLIST.md`.

### 1. Behaviour parity with `git show main:crc/oci/disk.py`

- **SDK calls (order and arguments)** (`crc/oci/disk.py:120-139`, `:146-158`, `:160-190`, `:220-226`, `:367-377`, `crc/oci/disk_api.py:120-179` vs `main:crc/oci/disk.py:63-100`, `:169-219`):
  - `get_all_regions()` runs first via `regions_of(base)` (creating cached `IdentityClient` and calling `list_region_subscriptions(self.tenancy_id)`, falling back to `["us-sanjose-1"]` on `CONNECTIVITY_ERRORS` and propagating non-connectivity errors).
  - For each region, `api_for(base)(region)` calls `base.get_compute_client(region)` then `base.get_blockstorage_client(region)`, `list_region` calls `oci.pagination.list_call_get_all_results` for `list_volumes(compartment_id=self.compartment_id)` then `list_boot_volumes(compartment_id=self.compartment_id)`, `attached_volume_ids` calls `list_call_get_all_results` for `list_volume_attachments(compartment_id=self.compartment_id)`, and `attached_boot_volume_ids` calls `get_availability_domains(region)` (`list_availability_domains(compartment_id=self.tenancy_id)`) then `list_call_get_all_results` for `list_boot_volume_attachments(availability_domain=ad, compartment_id=self.compartment_id)`.
  - In `Disk.delete()`, `delete_volume(volume.id)` runs per matching block volume before boot attachments are listed, and `delete_boot_volume(volume.id)` runs per matching boot volume before moving to the next region.
- **Filter and age decisions** (`crc/oci/disk.py:45`, `:173-174`, `:186-187`, `:250-280` vs `main:crc/oci/disk.py:17`, `:76`, `:96`, `:102-168`):
  - Only `lifecycle_state == "AVAILABLE"` volumes whose `id` is not in `attached_ids` (`ATTACHED`, `ATTACHING`) are considered.
  - Filtering uses `policy.normalize_tags`, `policy.should_skip_by_tags` (`exception_tags` any key, `notags` all keys), and `policy.filter_tags_any_key` (`filter_tags` any key, empty passes).
  - Age uses `core_age.get_retention_age` (fail-open per `BUG-004`, `SAF-009`), `policy.effective_age`, and `core_age.is_old` (`SAF-006`, `SAF-010`).
- **Log lines, printed messages, errors, and dry-run path** (`crc/oci/disk.py:83-92`, `:124-126`, `:175-176`, `:188-189`, `:220-231`, `:272-277`, `:345-348` vs `main:crc/oci/disk.py:60`, `:78-79`, `:98-99`, `:145-148`, `:169-177`, `:198-200`, `:220-231`):
  - Every `logging.debug`, `logging.info`, `logging.warning`, and `logging.error` message matches `main`.
  - `CONNECTIVITY_ERRORS` skip the region during volume listing or leave the attachment set partial/empty during attachment listing; per-volume `delete_volume` / `delete_boot_volume` errors catch `Exception`, log `Error occurred while deleting {kind} {name}: {e}`, and omit the volume from `disk_names_to_delete` / `Result.succeeded`.
  - In dry run, no delete call is made, matching `display_name`s are appended to `disk_names_to_delete` / `Plan.candidates`, and the dry-run summary warning is logged.

### 2. Oracle and parity test verification (`tests/legacy/oci_disk.txt`, `tests/test_oci_disk_parity.py`)

- Diffed `tests/legacy/oci_disk.txt` against `git show main:crc/oci/disk.py`: byte-identical (SHA-256 `62768f3419b4a371d173957e9e0e5642132c447f296d9d570cf2c68819e23270`, 0 lines of diff).
- Verified `tests/test_oci_disk_parity.py` runs both the oracle and the refactored code (`Disk` and `build_disk_cleaner`) on the same `FakeOci` fakes across 77 cases and 28 quirk assertions.
- Tested a deliberate one-line behaviour change in `crc/oci/disk.py` (`return None` instead of `return "does not match filter_tags"` in `_skip_reason`), confirmed `pytest -q tests/test_oci_disk_parity.py` failed (15 failed), and reverted it.

### 3. Architecture, scope, and lane rules

- `DiskCleaner` implements `Cleaner` (`cloud = "oci"`, `kind = "disk"`, `supports`, read-only `plan`, mutating `apply`) and is registered with `@register("oci", "disk")` on `build_disk_cleaner`.
- `plan()` never mutates (`ARCH-005` passes on `crc/oci/disk.py` and `crc/oci/disk_api.py`).
- SDK sits behind typed `VolumeApi`, `SdkVolume`, and `SdkAttachment` `Protocol`s in `crc/oci/disk_api.py`.
- `crc/oci/disk.py` (`crc.oci.disk`) was removed from both legacy ratchet lists in `pyproject.toml`; nothing was added to the ratchet (`ARCH-001`), and the `module = ["oci", "oci.*"]` mypy override is per-SDK.
- `crc.py`, `crc/core/**`, other clouds' packages, and all files forbidden by the lane rules are untouched; `crc/oci/README.md` is accurate and passes `ARCH-002` symbol sync.
- Verified all 12 rows in `docs/refactor/bugs/pending/OCI-1.md` against `git show main:crc/oci/disk.py`, `git show main:crc/oci/_base.py`, and `git show main:crc/oci/connectivity.py`.

### BLOCKING (fixed)

1. **`docs/refactor/bugs/pending/OCI-1.md` violated `docs/refactor/BUGS.md` Rules 4 and 5** (`docs/refactor/bugs/pending/OCI-1.md:9-22`):
   - Three rows used invalid `Effect` values (`run succeeds with undeleted leftovers`, `run fails after a partial delete`, `reports the wrong thing`) outside the four allowed by `BUGS.md` Rule 5 (`deletes what it should keep`, `keeps what it should delete`, `run fails`, `cosmetic`), and rows were not sorted by risk (`high`, `medium`, `low`) per Rule 4 (`low` row 4 was placed above `medium` rows 5-7, and `medium` row 11 was placed at the bottom).
   - Fixed the `Effect` values (`keeps what it should delete` and `cosmetic`), sorted the table by risk (`high` 2, `medium` 5, `low` 5), and tightened two end-line citations (`:169-177`, `:186-200`, `:186-218`).
2. **`tests/test_oci_disk_parity.py` did not record `oci.pagination.list_call_get_all_results` calls in `FakeOci.calls` and only compared `sorted(new.logs) == sorted(old_logs)` in `test_cleaner_protocol_matches_main`** (`tests/test_oci_disk_parity.py:519-526`, `:670-709`):
   - Recorded `("list_call_get_all_results", fn.__name__)` in `FakeOci.paginate` so bypassing pagination on any of the four list calls fails parity.
   - Replaced the unordered `sorted(new.logs)` check in `test_cleaner_protocol_matches_main` with an ordered comparison `new.logs == plan_logs + apply_logs + summary_logs`.

### NIT (left)

- If `DiskCleaner.apply()` is called directly with `dry_run=True`, the dry-run summary warning is logged a second time after `plan()` (`crc/oci/disk.py:139-140`, `:157`). `crc.core.engine.run` never calls `apply()` in dry run (`crc/core/engine.py:99-100`).
- `DiskRuntime.clock` defaults to `datetime.datetime.now` (as a function reference, not a call, so `ARCH-003` passes) to keep `Disk()` backwards-compatible until `crc.py` is wired to `engine.run`.

### Gates

`pip install -r requirements.txt -r requirements-dev.txt` then `make check`:

| Gate | Result |
|------|--------|
| `ruff check .` | All checks passed |
| `mypy` (`crc`, `tests`) | Success: no issues found in 86 source files |
| `lint-imports` | Contracts: 5 kept, 0 broken |
| `pytest -q` | 2913 passed |

Test count: 2703 before OCI-1 (`9b5c85a`), 2913 after OCI-1 (+210).

VERDICT: APPROVE
