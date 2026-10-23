# crc.aws.snapshot

## Purpose

AWS EBS snapshot cleaner (AWS-2): deletes snapshots older than age_days that carry no exception tag and back no AMI, in every region. Split into a package in W2-AWS-A; `from crc.aws.snapshot import ...` keeps working.

Modules:

- `client.py`: EC2 Protocol, default factory, runtime.
- `protection.py`: tag reading, exception-tag protection and AMI usage.
- `cleaner.py`: the Cleaner and its registry factory.
- `adapter.py`: the legacy `Snapshot` class.

## Public API

- `SnapshotClient`: Protocol of the three EC2 calls used, describe_snapshots, describe_images and delete_snapshot; tests pass fakes.
- `boto3_client()`: default EC2 client factory.
- `SnapshotRuntime`: frozen dataclass with the injected client factory, region lister and clock (now, UTC) of Snapshot.
- `is_tag_list()`: whether tags is a list of mappings.
- `read_tags()`: tag map of a list of tag entries (BUG-144 tolerant reading).
- `is_protected()`: whether an exception tag protects the snapshot (logs the matching key).
- `used_by_amis()`: snapshot ids that back an AMI of the account in the client's region.
- `SnapshotCleaner`: the Cleaner (supports, read-only plan, mutating apply, plus check_age, iter_region, delete_one and is_protected used by the adapter).
- `build_snapshot_cleaner()`: registry factory behind the aws / snapshot registration; reads age_days (default 90) and exception_tags from RunContext.options.
- `skip_failed_region()`: records a non-connectivity region error and skips the region (BUG-149).
- `Snapshot`: adapter crc.py calls (delete(), get_deleted, delete_count, deleted_snapshots); runs the cleaner region by region, snapshot by snapshot, in the order of main.

## Safety Invariants

- Authoritative invariants and quirks: `crc/aws/README.md` (Safety Invariants) and `CLEANUP_SAFETY.md`; this package keeps them unchanged (W2-AWS-A split, no behaviour change).
- `plan()` and what it calls stay read-only (ARCH-005); every mutating call stays in `apply()` / `delete_one()` and never runs in a dry run. Tests: `tests/test_aws_snapshot.py`, `tests/test_aws_snapshot_fix.py`, `tests/test_aws_snapshot_parity.py` (oracle `tests/legacy/aws_snapshot.txt`, never edit it).

## Extension Rules

1. Structure-only changes in a refactor wave; behaviour fixes are separate rungs (`docs/refactor/PLAN.md`).
2. The adapter in `adapter.py` is the legacy entry point of `crc/cli`; keep it separate so it can be deleted in one move.
3. Shared AWS helpers live in `crc/aws/_common.py`; keep this package free of copies.
4. Import path `crc.aws.snapshot` must keep re-exporting every public name (see `__init__.py`).
5. Keep every file at 250 lines or fewer.
