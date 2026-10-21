# Refactor status

| Rung | State | Notes |
|------|-------|-------|
| R0a | done, reviewed: APPROVE | Added pyproject (ruff, mypy strict, import-linter, pytest config), requirements-dev.txt, Makefile `check`, Cursor environment, AGENTS.md/CLAUDE.md, ARCHITECTURE.md, CODEOWNERS, Cursor rules and project skill. Review (`docs/refactor/reviews/R0a.md`) replaced the whole-tree exemptions with a per-file legacy list (new files are checked), added mypy `files` guard; 110 tests before and after. |
| R0b | done, reviewed: APPROVE | Added `tests/archtest/` (ARCH-001..005, SAF-LOCK, each with self-tests, README, `legacy_baseline.txt`, `safety_lock.json`, owner-only `update_safety_lock.py`), `[SAF-001]`..`[SAF-046]` tags in `CLEANUP_SAFETY.md`, pinned `requirements-dev.txt`, `.github/workflows/ci.yml` (Python 3.11, `make check`), pointers in AGENTS.md and ARCHITECTURE.md. Review (`docs/refactor/reviews/R0b.md`) removed 4 wrong test mappings in `safety_lock.json` (`SAF-015`, `SAF-032`, `SAF-034`) and moved `SAF-034` to `gaps`. No change to `crc.py`, `crc/` or existing tests. pytest: 110 existing + 80 archtest = 190 passed. 30 of 46 SAF IDs locked to 61 existing test entries; 16 gaps. |
| R1a | done, reviewed: APPROVE | Moved age handling out of `crc/service.py` into new pure `crc/core/age.py` (`AgeSpec`, `AGE_KEYS`, `require_positive_age`, `lookup_custom_age_tag`, `validated_retention_age`, `parse_literal`, `get_retention_age`, `get_min_age`, `is_old`) with `crc/core/__init__.py` (`__all__`) and `crc/core/README.md` (ARCH-002). `Service` keeps every method and signature and delegates to `crc.core.age`; `crc/service.py` stays in the legacy ratchet. Enabled the two import-linter contracts from the TODO (core must not import `crc.aws/azu/gcp/oci/notifications/service`, nor boto3, botocore, azure, google, oci, slack_sdk, influxdb_client; `include_external_packages = true` added so SDK names are checked). Added `tests/test_core_age.py`. Review (`docs/refactor/reviews/R1a.md`) added coverage for the `not (set(age) & AGE_KEYS)` branch in `require_positive_age`. No behaviour change: an ad hoc differential run of old vs new `Service` over 2758 input combinations (return values, exception types and messages, log records) was identical. pytest: 190 before, 348 after (190 existing unchanged + 158 new). Policy (tag/regex filtering) untouched. |
| R1b | done, review pending | Added `docs/refactor/FILTER_VARIANTS.md` (how every module under `crc/aws`, `azu`, `gcp`, `oci` filters today, with `file:line`, plus a Variants section) and pure `crc/core/policy.py`: `normalize_tags` (AWS Key/Value and KMS TagKey/TagValue lists, dict-like and GCP map tags), one explicitly named function per variant (`filter_tags_any_key`, `filter_tags_all_keys`, `filter_tags_glob_all_keys`, `filter_tags_exact_pairs`, `should_skip_by_tags`, `aws_eip_should_skip`, regex search / match / substring variants, Azure state substring variants, yb_task, Kubernetes, GKE / MIG, OKE, AWS disk age floor, snapshot cutoff, `UntaggedMode`). `crc/core/__init__.py` `__all__` and `crc/core/README.md` synced (ARCH-002). Added `tests/test_core_policy.py` (table-driven, every function and variant). Nothing wired; no module outside `crc/core` changed, no import-linter or archtest change. pytest: 348 before, 553 after (348 existing unchanged + 205 new). |

Open issues (R0a):

- Core layer import-linter contract is a commented TODO until `crc/core` exists.
- `.cursor/environment.json` needs `python3.11` on the image; `make check` uses
  `.venv/bin` when present, otherwise tools on `PATH`.
- CODEOWNERS only takes effect once branch protection requires code owner review.
- `crc.py` (module) and `crc/` (package) share the name `crc`; mypy checks only
  `crc/` and `tests/` (`files`), so the CLI rung must resolve the clash.

Open issues (R0b):

- SAF gaps with no existing test (not invented): SAF-001, 002, 004, 005, 006, 009, 010,
  014, 016, 021, 022, 023, 024, 034, 036, 037. Later rungs that add tests should ask the owner
  to map them with `tests/archtest/update_safety_lock.py --map`.
- SAF-LOCK hashes use a custom version-stable AST dump; verified identical on Python 3.11.17
  and 3.12.3. `update_safety_lock.py` is owner-only and its files are in CODEOWNERS (only
  enforced with branch protection).
- Pins (pytest 9.1.1, ruff 0.17.1, mypy 2.4.0, import-linter 2.15, types-python-dateutil
  2.9.0.20260807) passed `make check` on 3.11.17 and 3.12.3. The CI workflow has not run on
  GitHub yet.
- ARCH-002 covers sub-directories of `crc/`, not `crc/` itself. ARCH-005 also follows
  `self.`/`cls.` methods and same-module functions transitively from `plan`.

Open issues (R1a):

- `crc.core.age.is_old` still reads the `MAX_AGE` environment variable (kept for exact
  behaviour, as the task required). This conflicts with the "no env reads" ideal in the
  skill (3.1); moving the read to the caller (CLI boundary) is a later rung.
- `get_retention_age` is typed `-> Any` in core because it returns the parsed literal (dict,
  int, ...), not `str` as the legacy annotation claims; `Service.get_retention_age` keeps the
  old annotation. `Service._lookup_custom_age_tag` and `Service._parse_literal` remain as thin
  delegates to `lookup_custom_age_tag` and `parse_literal` (now public in core).
- Preserved quirks, covered by tests, not fixed here: `True` is accepted as age 1 day;
  `get_retention_age` returns `{'days': inf}` for `1e999` and unvalidated dicts; `MAX_AGE`
  that is not a dict raises (`SyntaxError`, `AttributeError`) instead of failing closed;
  `is_old` ignores unknown keys (all-unknown returns False); `{}` in `MAX_AGE` makes `is_old`
  return False.
- `include_external_packages = true` makes import-linter graph external packages; the SDK
  contract uses direct and indirect checks (no `allow_indirect_imports`).
- Local `make check` was run on Python 3.12.3 (3.11 not installed in this VM); CI uses 3.11.
  Tests avoid assertions on interpreter-specific `ast` error text.

Proposed SAF mappings (R1a; owner to apply with `tests/archtest/update_safety_lock.py --map`,
`safety_lock.json` not edited):

- SAF-006 (`is_old({})` returns True): `tests/test_core_age.py::test_is_old_empty_age_matches_all[age0]`
  (also `[0]`, `[None]`, which set `MAX_AGE` to prove the empty age ignores it).
- SAF-009 (modules calling `get_retention_age` alone fail open): `tests/test_core_age.py::test_get_retention_age`
  (unparseable, empty and TypeError-style tags return None) and `tests/test_core_age.py::test_get_retention_age_logs`.
- SAF-010 (`MAX_AGE` can shorten a floor inside `is_old`, including to zero):
  `tests/test_core_age.py::test_is_old_max_age_override[age3-{'days': 0}-delta3-outcome3]`
  and `tests/test_core_age.py::test_is_old_max_age_message_text`.

Open issues (R1b):

- Quirks are preserved, not fixed (see `FILTER_VARIANTS.md` section 7): AWS Elastic IP notags never
  skips; GCP IP exception_regex is inverted; GCP disk ignores notags and name_regex; KMS
  multi-value filter never matches; Azure disk state is a substring test (`"attached"` passes
  `"Unattached"`); Azure IP raises on `None` tags with exception_tags/notags (policy returns
  False); AWS VPC calls `_should_skip_vpc` with a resource instead of tags.
- Untagged handling of AWS VM and Elastic IP depends on the `Tags` key being absent; the wiring
  rung must decide that before `normalize_tags`.
- The EC2 server-side `tag:key` filter (AWS VM, VPC, spot) stays in the cleaners; its behaviour
  with an empty value list was not verified.
- Policy covers filtering only. Age functions stay in `crc.core.age`; `effective_age`,
  `aws_disk_creation_floor`, `is_older_than_floor` and `snapshot_old_enough` are thin helpers.
- Local `make check` ran on Python 3.12.3 (3.11 not installed), dependencies installed with
  `pip --user`.

Proposed SAF mappings (R1b; owner to apply with `tests/archtest/update_safety_lock.py --map`,
`safety_lock.json` not edited). Policy-level tests that back existing SAF IDs (cleaner-level
tests still own the wired behaviour):

- SAF-042 (Azure skips untagged Spot VMs): `tests/test_core_policy.py::test_skip_untagged[tags0-UntaggedMode.SKIP-False-True]`
  (policy only; the Azure wiring rung must add the cleaner test).
- SAF-045 (GCP skips GKE / MIG, OCI skips OKE / instance-pool): `tests/test_core_policy.py::test_gcp_managed_or_gke`
  and `tests/test_core_policy.py::test_oci_managed_or_oke` (all parametrised cases).
- SAF-044 and SAF-032 (volume-owned exception/notags and sensitive yb_task protection):
  `tests/test_core_policy.py::test_should_skip_by_tags`, `::test_yb_task_variants` and
  `::test_is_sensitive_yb_task` (policy only).

Gaps: `CLEANUP_SAFETY.md` has no SAF ID for the generic "empty exception_tags or notags never
skips, untagged never matches notags" rule, for the AWS disk Kubernetes CSI skip, or for the
quirks listed above. Proposed new IDs (owner decides): SAF-047 policy tag skip rules
(`test_should_skip_by_tags`, `test_exception_and_notags`, `test_aws_eip_should_skip_ignores_notags`),
SAF-048 AWS disk Kubernetes volume skip (`test_aws_disk_skips_kubernetes`,
`test_aws_kubernetes_volume`).
