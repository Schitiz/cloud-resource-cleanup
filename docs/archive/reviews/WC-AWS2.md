## Coding summary

Lane WC-AWS2 (branch `wc/aws2`): deleted the dead `crc.aws.snapshot.Snapshot` and `crc.aws.vpc.VPC` adapter classes and trimmed the AWS READMEs.

**Routed.** Nothing new to route in this lane: `aws` / `snapshot` and `aws` / `vpc` were already engine-routed through `crc/cli/bridge.py` and `crc/cli/routes/aws.py`. No production module used either adapter (`git grep` over `crc/`, `crc.py`, `tests/` found users only in tests).

**Adapters deleted.**
- `Snapshot`: `crc/aws/snapshot/adapter.py` removed, its re-export and README line removed, and the now-unused `SnapshotRuntime`, `Clock` and `_UTC_CLOCK` removed from `client.py`.
- `VPC`: `crc/aws/vpc/adapter.py` removed, its re-export and README line removed, and the now-unused `VpcRuntime` removed from `runtime.py`, `cleaner.py` and `__init__.py`.
- Not touched: the five adapters of the hash-locked safety tests (aws `Disk`, aws `SpotInstanceRequests`, azure/gcp/oci `SpotVM`) and those tests; `VM` stays (used by `crc/cli/scan.py`).

**Tests retargeted** (same oracle cases and assertions; the Cleaner now runs through `crc.core.engine.run` via the new `tests/helpers_wc_aws2_engine.py`, `run_through_engine`):
- `tests/test_aws_snapshot_parity.py`, `tests/test_aws_vpc_parity.py`: every case still compares against `tests/legacy/aws_snapshot.txt` / `aws_vpc.txt` on SDK calls, results, log lines, stdout and errors. Where the adapter interleaved list and delete per region, the comparison splits the plan and delete streams (as the existing protocol tests did). Adapter-method cases (`_is_protected`, `_get_snapshots_used_by_amis`, `_should_skip_vpc`, `_get_filter`, `get_vpc_ids`) now compare the Cleaner or helper function against the oracle method. The constructor/runtime-injection case was ported to the Cleaner constructor.
- `tests/test_aws_snapshot.py`, `tests/test_aws_snapshot_fix.py`, `tests/test_aws_vpc_fix.py`, `tests/test_aws_misc_logger.py`: adapter use replaced by engine runs of the Cleaner. In `test_aws_snapshot_fix.py` the 15 "adapter" parameters of `test_diverging_case_has_the_fixed_outcome` (adapter deleted as it went) are gone with the class; 15 new dry-run engine cases (`test_diverging_case_in_a_dry_run_through_the_engine_never_deletes`) keep the count.
- Allowed ENG difference asserted explicitly: a listing error in a later region stops the run before any delete (`ENGINE_QUIRKS` in the VPC parity test: `list-client-error-propagates`, `missing-vpc-endpoints-key`).

**CLI parity tests.** Not changed in this lane; they already reach the registered cleaners through the bridge seam.

**Tests count.** Before 44415, after 44415 (floor unchanged, `make raise-test-floor` not needed).

**READMEs trimmed** to current code (no rung names, refactor history, adapter or legacy-path wording): `crc/aws/README.md` (whole file, except the elastic_ips and kms lines, left for WC-AWS1), `snapshot`, `vpc`, `keypairs`, `vm`, `disk`, `spot_instance_requests` (text only). Moved-doc links updated (`FILTER_VARIANTS.md` -> `docs/archive/FILTER_VARIANTS.md`; `docs/refactor/PLAN.md` references removed).

**Owner actions.**
- `tests/archtest/legacy_baseline.txt` still lists `crc/aws/snapshot.py` and `crc/aws/vpc.py` (paths that no longer exist); outside this lane's files.
- The `elastic_ips` and `kms` bullets in `crc/aws/README.md` (module list and Safety Invariants) still carry rung names (R4b, R4c, FIX-AWS-KMS) and `ElasticIPs` / `Kms` adapter wording: left verbatim for lane WC-AWS1.
- The READMEs of `elastic_ips` and `kms` were not edited (WC-AWS1).

## New bugs

None found.


## Round 1 (Argon)

### Findings

- **Check (1) Production paths**: Verified that `crc/cli/scan.py` (which uses the 4 cloud `VM` classes), `crc/cli/routes/aws.py`, `crc.aws.snapshot.build_snapshot_cleaner` (`@register("aws", "snapshot")`), `crc.aws.vpc.build_vpc_cleaner` (`@register("aws", "vpc")`), and the five adapters built by the hash-locked safety tests (`crc.aws.disk.Disk`, `crc.aws.spot_instance_requests.SpotInstanceRequests`, and `azure`/`gcp`/`oci` `SpotVM`) remain intact and importable. Only the dead `crc.aws.snapshot.Snapshot` (`crc/aws/snapshot/adapter.py`, `SnapshotRuntime`, `Clock`, `_UTC_CLOCK`) and `crc.aws.vpc.VPC` (`crc/aws/vpc/adapter.py`, `VpcRuntime`) adapters and their unused runtime wrappers were deleted.
- **Check (2) Parity & unit tests**: Confirmed `tests/test_aws_snapshot_parity.py`, `tests/test_aws_vpc_parity.py`, `tests/test_aws_snapshot_fix.py`, `tests/test_aws_vpc_fix.py`, `tests/test_aws_snapshot.py` and `tests/test_aws_misc_logger.py` drive the registered `SnapshotCleaner` and `VpcCleaner` through `crc.core.engine.run` (via `tests/helpers_wc_aws2_engine.py::run_through_engine` and local `Registry` helpers). All 55 snapshot oracle cases (including 15 `DIVERGES` cases with `BUG-144` / `BUG-149`), 25 snapshot `QUIRKS`, 66 VPC oracle cases, 22 VPC `QUIRKS` (with `ENGINE_QUIRKS` for `list-client-error-propagates` and `missing-vpc-endpoints-key`), and 17 VPC `DIVERGING` cases (`BUG-012`, `BUG-083`, `BUG-087`, `BUG-088`) are preserved without dropping cases or loosening comparisons. Locally broke `SnapshotCleaner._decide` (skipping `exception_tag` protection) and `VpcCleaner.is_default` (returning `False`) and confirmed `tests/test_aws_snapshot_parity.py` (26 failures) and `tests/test_aws_vpc_parity.py` (2 failures) fail immediately before restoring both.
- **Check (3) Deleted names & READMEs**: Confirmed via `rg` across `crc/`, `crc.py` and `tests/` that `crc.aws.snapshot.Snapshot`, `SnapshotRuntime`, `crc.aws.vpc.VPC` and `VpcRuntime` have no remaining references (only oracle ` _load_oracle().Snapshot` / `_load_oracle().VPC` and CLI route event tags remain). Reviewed `crc/aws/README.md` (excluding `elastic_ips` and `kms` lines reserved for WC-AWS1) and the READMEs of `snapshot`, `vpc`, `keypairs`, `vm`, `disk`, and `spot_instance_requests`; trimmed two minor leftover phrases in `crc/aws/vm/README.md` (`(as on main)` and `(or the adapter clock)` -> `(or the VM clock)`) and updated the file-length line in `crc/aws/disk/README.md` (`400` -> `250`).
- **Check (4) Locked files**: Confirmed `git diff 302612d..HEAD` touches no hash-locked safety test file, no `tests/legacy/*.txt` oracle file, and no `tests/archtest/**` file.
- **Check (5) Size limits & Public API**: Every touched file in `crc/aws/**` is well under the 250-line file limit and 60-line function limit (largest is `crc/aws/vpc/cleaner.py` at 243 lines, max function `plan_region` at 32 lines; `tests/helpers_wc_aws2_engine.py` is 56 lines, max function 34 lines). All package `README.md` Public API sections are in sync with `__all__` and module symbols (ARCH-002 green).
- **Check (6) Gates, test count & runtime**: After `pip install -r requirements.txt -r requirements-dev.txt` and clearing stale `.mypy_cache`, full `make check` is green:
  - `ruff check .`: passed (`All checks passed!`)
  - `mypy`: passed (`Success: no issues found in 371 source files`)
  - `lint-imports`: 5 kept, 0 broken
  - `pytest -q -n auto`: `44415 passed in 54.57s`
  - `ARCH-008`: 44415 tests, floor 44415 (ARCH-001..009 and SAF-LOCK all green)

VERDICT: APPROVE
