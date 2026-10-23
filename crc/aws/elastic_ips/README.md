# crc.aws.elastic_ips

## Purpose

AWS Elastic IP cleaner (R4b): releases unassociated, tagged Elastic IPs that match the filters in every region. Split into a package in W2-AWS-A; `from crc.aws.elastic_ips import ...` keeps working.

Modules:

- `client.py`: EC2 Protocol, default factory, runtime.
- `cleaner.py`: the Cleaner and its registry factory.
- `adapter.py`: the legacy `ElasticIPs` class.

## Public API

- `ElasticIpClient`: Protocol of the two EC2 calls used, describe_addresses and release_address; tests pass fakes.
- `boto3_client()`: default EC2 client factory.
- `ElasticIpRuntime`: frozen dataclass with the injected client factory and region lister of ElasticIPs (no clock: no age gate).
- `ElasticIpCleaner`: the Cleaner (supports, read-only plan, mutating apply, plus per-region plan_region and apply_region).
- `build_elastic_ip_cleaner()`: registry factory behind the aws / ip registration; reads filter_tags, exception_tags and notags from RunContext.options.
- `log_summary()`: the summary lines logged once all regions are done.
- `ElasticIPs`: adapter crc.py calls (delete(), get_deleted, count, deleted_ips); runs the cleaner region by region in the order of main.

## Safety Invariants

- Authoritative invariants and quirks: `crc/aws/README.md` (Safety Invariants) and `CLEANUP_SAFETY.md`; this package keeps them unchanged (W2-AWS-A split, no behaviour change).
- `plan()` and what it calls stay read-only (ARCH-005); every mutating call stays in `apply()` / `apply_region()` and never runs in a dry run. Tests: `tests/test_aws_elastic_ips.py`, `tests/test_aws_elastic_ips_fix.py`, `tests/test_aws_ip_parity.py` (oracle `tests/legacy/aws_elastic_ips.txt`, never edit it).

## Extension Rules

1. Structure-only changes in a refactor wave; behaviour fixes are separate rungs (`docs/refactor/PLAN.md`).
2. The adapter in `adapter.py` is the legacy entry point of `crc/cli`; keep it separate so it can be deleted in one move.
3. Shared AWS helpers live in `crc/aws/_common.py`; keep this package free of copies.
4. Import path `crc.aws.elastic_ips` must keep re-exporting every public name (see `__init__.py`).
5. Keep every file at 250 lines or fewer.
