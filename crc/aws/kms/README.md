# crc.aws.kms

## Purpose

AWS KMS key cleaner (R4c): schedules deletion of enabled keys matching description, tags, age and user ARN (us-west-2 only). Split into a package in W2-AWS-A; `from crc.aws.kms import ...` keeps working.

Modules:

- `client.py`: KMS Protocols, default factory, runtime.
- `settings.py`: `KmsSettings`.
- `tags.py`: tag reading and filter matching.
- `cleaner.py`: the Cleaner and its registry factory.
- `adapter.py`: the legacy `Kms` class.

## Public API

- `KmsPaginator`: Protocol of the list_keys paginator (paginate).
- `KmsClient`: Protocol of the five KMS calls used (get_paginator, list_resource_tags, describe_key, get_key_policy, schedule_key_deletion); tests pass fakes.
- `boto3_client()`: default KMS client factory.
- `KmsRuntime`: frozen dataclass with the injected client factory and clock (now) of Kms.
- `KmsSettings`: frozen dataclass with the filters and thresholds of one run.
- `NotOursError`: the key policy has no AWS principal to compare with kms_user.
- `tag_pairs()`: (TagKey, TagValue) pairs of one key; a malformed tag raises and the key is skipped.
- `matches_filter()`: every filter key present with any of its values (BUG-007, BUG-014).
- `KmsCleaner`: the Cleaner (supports, read-only plan, mutating apply, plus connect_and_list, plan_keys and schedule used by the adapter).
- `build_kms_cleaner()`: registry factory behind the aws / kms registration; reads filter_tags, exception_tags, kms_key_description, kms_user, kms_pending_window, age and custom_age_tag_key from RunContext.options.
- `log_summary()`: the summary lines logged once the cleanup is done.
- `log_would_delete()`: run-log ACTION lines of the keys a dry run would schedule.
- `Kms`: adapter crc.py calls (delete(), get_deleted, kms_keys_to_delete); runs the cleaner in the order of main.

## Safety Invariants

- Authoritative invariants and quirks: `crc/aws/README.md` (Safety Invariants) and `CLEANUP_SAFETY.md`; this package keeps them unchanged (W2-AWS-A split, no behaviour change).
- `plan()` and what it calls stay read-only (ARCH-005); every mutating call stays in `apply()` / `apply_region()` and never runs in a dry run. Tests: `tests/test_aws_kms.py`, `tests/test_aws_kms_fix.py`, `tests/test_aws_kms_parity.py` (oracle `tests/legacy/aws_kms.txt`, never edit it).

## Extension Rules

1. Structure-only changes in a refactor wave; behaviour fixes are separate rungs (`docs/refactor/PLAN.md`).
2. The adapter in `adapter.py` is the legacy entry point of `crc/cli`; keep it separate so it can be deleted in one move.
3. Shared AWS helpers live in `crc/aws/_common.py`; keep this package free of copies.
4. Import path `crc.aws.kms` must keep re-exporting every public name (see `__init__.py`).
5. Keep every file at 250 lines or fewer.
