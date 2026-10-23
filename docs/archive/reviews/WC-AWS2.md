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
