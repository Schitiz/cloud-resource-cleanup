# crc.aws.keypairs

## Purpose

AWS EC2 key pair cleaner (R4a): deletes key pairs by name regex, exception regex and age in every region. Split into a package in W2-AWS-A; `from crc.aws.keypairs import ...` keeps working.

Modules:

- `client.py`: EC2 Protocol, default factory, runtime.
- `cleaner.py`: the Cleaner and its registry factory.

## Public API

- `KeyPairClient`: Protocol of the two EC2 calls used, describe_key_pairs and delete_key_pair; tests pass fakes.
- `boto3_client()`: default EC2 client factory.
- `KeyPairCleaner`: the Cleaner (supports, read-only plan, mutating apply, plus per-region plan_region and apply_region).
- `build_keypair_cleaner()`: registry factory behind the aws / keypair registration; reads name_regex, exception_regex and age from RunContext.options.
- `log_summary()`: the summary lines logged once all regions are done.

## Safety Invariants

- Authoritative invariants and quirks: `crc/aws/README.md` (Safety Invariants) and `CLEANUP_SAFETY.md`; this package keeps them unchanged (W2-AWS-A split, no behaviour change). Through the engine `plan()` lists every region before `apply()` deletes (ENG-0): a listing error in a later region now stops the run before any delete. In a dry run `plan()` logs the `would_delete` actions per region, since the engine never calls `apply()` then.
- `plan()` and what it calls stay read-only (ARCH-005); every mutating call stays in `apply()` / `apply_region()` and never runs in a dry run. Tests: `tests/test_aws_keypairs.py`, `tests/test_aws_keypair_parity.py` (oracle `tests/legacy/aws_keypairs.txt`, never edit it).

## Extension Rules

1. Structure-only changes in a refactor wave; behaviour fixes are separate rungs (`docs/refactor/PLAN.md`).
2. `crc/cli` runs the Cleaner through `crc.core.engine` (route `aws` / `keypair` in `crc/cli/routes/aws.py`); the `KeyPairs` adapter was deleted in ENG-0.
3. Shared AWS helpers live in `crc/aws/_common.py`; keep this package free of copies.
4. Import path `crc.aws.keypairs` must keep re-exporting every public name (see `__init__.py`).
5. Keep every file at 250 lines or fewer.
