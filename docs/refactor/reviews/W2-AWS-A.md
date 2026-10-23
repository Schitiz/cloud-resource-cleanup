## Coding summary

Lane W2-AWS-A, structure only, no behaviour change. Every owned file is now at most 250 lines (`wc -l`). All five flat modules except `disk/cleaner.py` became subpackages whose `__init__.py` re-exports every name the old module exported, so `crc.py`, `crc/cli` and the tests import from the same paths. No test, oracle or guardrail file was edited.

### Files split (before -> after, lines)

| Old file | Before | After |
|----------|-------:|-------|
| `crc/aws/keypairs.py` | 279 | `keypairs/cleaner.py` 162, `adapter.py` 75, `client.py` 45, `__init__.py` 20 |
| `crc/aws/elastic_ips.py` | 301 | `elastic_ips/cleaner.py` 178, `adapter.py` 84, `client.py` 43, `__init__.py` 20 |
| `crc/aws/kms.py` | 378 | `kms/cleaner.py` 207, `adapter.py` 90, `client.py` 65, `tags.py` 33, `settings.py` 22, `__init__.py` 22 |
| `crc/aws/snapshot.py` | 373 | `snapshot/cleaner.py` 192, `adapter.py` 91, `protection.py` 61, `client.py` 52, `__init__.py` 20 |
| `crc/aws/disk/cleaner.py` | 277 | `disk/cleaner.py` 217, `guard.py` 66 (region error policy, summary lines), `client.py` 86 (now holds `DiskRuntime`) |

Legacy adapter classes (`KeyPairs`, `ElasticIPs`, `Kms`, `Snapshot`) each sit alone in `adapter.py`. `Disk` already lived in `disk/__init__.py`, so it was not moved.

### Helpers extracted

New `crc/aws/_common.py` (50 lines): `ec2_regions` (was `_all_regions` in 3 files), `skip_region` (was `_skip_region` in 3 files, `_regionlog.region_skipped` + `log_skipped_region`), `group_by_region` (the by-region grouping in `apply()` of 4 cleaners), `log_deleted_summary` (the three identical summary-line functions of key pairs, Elastic IPs and KMS). `disk/guard.py` holds `region_guard` and `log_summary` (moved out of `DiskCleaner`; the methods stay and delegate, so `Disk` is unchanged).

Patch targets: tests patch only `boto3.client`, `boto3.session.Session`, `crc.service.init_logging`, `crc.aws._regionlog.clock` and `crc.aws.disk.boto3.client` / `crc.aws.disk.get_all_regions`; none of them moved. `boto3.client(...)` is still looked up on the `boto3` module at call time in every new `client.py`. The legacy private helper names used by the oracle tests (`Snapshot._get_snapshots_used_by_amis`, `_is_protected`, `Kms._should_skip_kms`, `ElasticIPs._should_skip_instance`) are kept.

### Tests and runtime

- `pytest -q` at base `cea0a8a`: 43010 passed (2m39s).
- `pytest -q` after: 43010 passed (same count).
- `make check` runtime: 2m43s wall (pytest 2m37s).
- ruff, mypy (strict), lint-imports (5 kept) and ARCH-001..005 / SAF-LOCK are green.

## Owner action

- Cross-cloud candidates (not touched, `crc/core` and other clouds are out of lane): the `_log_summary` "number of X deleted / List of X deleted / will be deleted" triple exists with the same shape in every cloud; the `by_region` grouping loop is probably repeated in `crc/azu`, `crc/gcp`, `crc/oci` cleaners. A `crc/core` helper for both would remove the AWS-only `_common.log_deleted_summary` and `group_by_region`.
- Lane W2-AWS-B may reuse `crc.aws._common.group_by_region`, `skip_region` and `ec2_regions`; `crc/aws/vm`, `vpc` and `spot_instance_requests` still have their own copies (`Candidate` grouping, `get_all_regions("ec2", "us-west-2")`). Not touched here.
- Still above 250 (other lane): `spot_instance_requests/cleaner.py` 296, `spot_instance_requests/volumes.py` 320, `vm/cleaner.py` 380, `vpc/cleaner.py` 383.

## New bugs

None found. Observation only, not changed: `kms/cleaner.py` `plan_keys` catches `BaseException` (also `KeyboardInterrupt`), inherited from the bare `except:` of `main` (already BUG-055 area).
