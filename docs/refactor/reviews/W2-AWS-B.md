## Coding summary

Wave W2 lane W2-AWS-B: structure-only split of the four large AWS files, no behaviour change. Every owned file is now at most 250 lines (`wc -l`). No flat `crc/aws/*.py` module and no `crc/aws/_common.py` was touched. No test, `tests/legacy/*.txt` oracle, hash-locked safety test or guardrail file was edited.

**Files split (before -> after lines)**

- `crc/aws/spot_instance_requests/cleaner.py` 296 -> 196. New: `runtime.py` (42: `SpotRuntime`, `Clock`, `settings_from_options`), `regions.py` (64: `list_matches`, `guarded_sweep`, `guarded_cleanup`), `summary.py` (32: `log_summary`). `cleaner.py` re-exports all of them, so the adapter and `__init__` imports are unchanged. The adapter was already in `adapter.py`.
- `crc/aws/spot_instance_requests/volumes.py` 320 -> 42 (facade). New: `volume_tags.py` (86: `ERRORS`, `error_code`, tag reads, `volume_ok_to_delete`, `filter_deletable_leftover_volumes`), `lookups.py` (138: instance volumes, leftover-marked volumes, `inspect_instance`), `sweep.py` (127: `live_spot_request_tags`, sweep gates, `run_sweep`). `volumes.py` re-exports every old name (`__all__`), so `leftover.py`, `cleanup.py` and `preview.py` import unchanged.
- `crc/aws/vm/cleaner.py` 380 -> 205. New: `settings.py` (56: constants, aliases, `boto3_client`, `all_regions`, `VmSettings`, `settings_from_options`), `reporting.py` (70: `ACTED`, `skip_region`, `note_region`, `note_dry_run`, `log_summary`, `summarise`, `dry_run_names`), `judge.py` (144: `InstanceJudge` with the per-instance decision: tags, exception tags, Name tag, age). `VmCleaner` keeps `build_filters`, `filter_instances`, `should_skip`, `apply_region` (the latter two delegate to the judge). `cleaner.py` re-exports every old public name, so `tests/test_aws_vm*.py`, `adapter.py` and `__init__` keep working. The adapter was already in `adapter.py`.
- `crc/aws/vpc/cleaner.py` 383 -> 234. New: `adapter.py` (127: the legacy `VPC` class, one move so it can be deleted later) and `runtime.py` (67: constants, `VpcRuntime`, default factories, `skip_region`, `log_summary`; formerly private `_` names, now public inside the package). `crc/aws/vpc/__init__.py` now imports `VPC` from `adapter` and `VpcRuntime` from `runtime`; `from crc.aws.vpc import VPC, VpcCleaner, VpcRuntime, build_vpc_cleaner` is unchanged. `crc.aws.vpc.cleaner.VPC` / `VpcRuntime` are no longer importable from `cleaner` (nothing in `crc/`, `crc.py` or `tests/` imported them from there).

**Helpers extracted**

- spot: `volume_tags._volume_tags` (the `describe_volumes` + tag filter shared by `describe_volume_tag_list` and `volume_tag_keys`), `volume_tags.error_code` (was `_error_code`, used by two modules now).
- vm: `reporting.ACTED` (the delete/stop action table, was a private constant used by two classes' code paths).
- Otherwise no duplicated logic inside the owned files needed deduplication.

**Patch targets.** No test patches a string target in these modules (`mock.patch.object(s, "VOLUME_POLL_INTERVAL_SEC", 0)` patches the adapter class attribute in `adapter.py`, unchanged; the string patches in the vm/vpc tests target `boto3.*` and `crc.service.init_logging`). Parity and cleaner tests pass.

**READMEs** updated: `spot_instance_requests`, `vm`, `vpc` (module lists, new public names, 250-line target).

**Tests / gates.** `pytest -q`: 43010 passed at `cea0a8a`, 43010 passed after (same count, no test added or removed). `make check` (ruff, mypy strict, lint-imports, pytest incl. ARCH-001..005 and SAF-LOCK) green. Runtime of `make check`: 3m34s at the base commit (pytest 193s), 3m00s after (pytest 174s).

## Owner action

- `crc/aws/vm/scan.py` (not owned by this lane's list, flat-package sibling) defines `SERVICE_NAME` and `RegionLister` again; these duplicate `crc/aws/vm/settings.py` (same values) and could import from there.
- `crc/aws/vm/settings.py`, `crc/aws/vpc/runtime.py` and the spot `client.py` each carry the same trio (boto3 client factory, region lister via `crc.aws._base.get_all_regions`, `SERVICE_NAME`/`DEFAULT_REGION` constants) and the same `skip_region` pattern (`log_skipped_region` + `logger.current().region_skipped`). A shared `crc/aws/_common.py` helper (lane W2-AWS-A) could replace these; `crc/aws/vpc/runtime.py::skip_region` also calls `_regionlog.region_skipped`, the vm and spot ones call `logger.current().region_skipped` directly.
- `crc/aws/vpc/runtime.py::log_summary`, `crc/aws/vm/reporting.py::log_summary` and the spot `summary.py::log_summary` are three different closing-summary shapes; not mergeable without changing log text.

## New bugs

- `crc/aws/vm/judge.py:111`: the "instance doesn't have Name Tag" error line interpolates `name`, which is always `None`/empty at that point, so the log reads "None instance doesn't have Name Tag" (same text as before the split; the ERROR is also recorded at line 66 with the instance id).
- `crc/aws/vm/judge.py:75`: `should_skip` logs the WARNING "Tags and notags not present" once per instance when neither exception tags nor notags are configured (noisy, unchanged).
