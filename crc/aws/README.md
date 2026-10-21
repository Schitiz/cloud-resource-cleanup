# crc.aws

## Purpose

Legacy AWS cleaners (boto3). They delete or stop leftover EC2, EBS, network, key and KMS resources across regions.

**Partly refactored.** `keypairs.py` (R4a) and `elastic_ips.py` (R4b) are `Cleaner`s (no behaviour change); every other module is legacy, not yet refactored, and the same as on `main`. Any change must follow `ARCHITECTURE.md` and the refactor rung for this package in `docs/refactor/PLAN.md` (Rung R4+), with `make check` green.

Modules (operations and filters as catalogued in `docs/refactor/FILTER_VARIANTS.md`):

- `_base.py`: `get_all_regions` (region list via `describe_regions`)
- `connectivity.py`: `log_skipped_region` (unreachable regions are logged and skipped)
- `disk.py`: `Disk`: deletes available EBS volumes (`delete_volume`); tags, regex, `yb_task` and Kubernetes skips, CloudWatch detach age; opt-in `--cloud aws --resource disk`
- `elastic_ips.py`: `ElasticIpCleaner` (registered as `aws` / `ip`) and the `ElasticIPs` adapter: releases unassociated, tagged Elastic IPs (`release_address`)
- `keypairs.py`: `KeyPairCleaner` (registered as `aws` / `keypair`) and the `KeyPairs` adapter: deletes key pairs by name regex (`delete_key_pair`)
- `kms.py`: `Kms`: schedules key deletion (`schedule_key_deletion`) for keys matching description and user ARN
- `snapshot.py`: `Snapshot`: deletes snapshots older than `age_days` (`delete_snapshot`)
- `spot_instance_requests.py`: `SpotInstanceRequests`: cancels spot requests, terminates instances, deletes leftover volumes
- `vm.py`: `VM`: terminates (`terminate_instances`) or stops (`stop_instances`) running instances
- `vpc.py`: `VPC`: deletes VPCs (`delete_vpc`)

## Public API

keypairs.py and elastic_ips.py are refactored, so the names below are synced with this README by ARCH-002. The
other modules (get_all_regions, log_skipped_region, Disk, Kms, Snapshot,
SpotInstanceRequests, VM, VPC) are legacy; each has delete(), VM also stop().
__init__.py holds only a copyright comment and declares no __all__.

- `KeyPairClient`: Protocol of the two EC2 calls used, describe_key_pairs and delete_key_pair; tests pass fakes.
- `KeyPairRuntime`: frozen dataclass with the injected client factory, region lister and clock (now) of KeyPairs.
- `KeyPairCleaner`: the Cleaner (supports, read-only plan, mutating apply, plus per-region plan_region and apply_region).
- `build_keypair_cleaner()`: registry factory behind @register("aws", "keypair"); reads name_regex, exception_regex and age from RunContext.options.
- `KeyPairs`: adapter crc.py calls (delete(), get_deleted, count, deleted_keypairs); runs the cleaner region by region in the order of main.
- `ElasticIpClient`: Protocol of the two EC2 calls used, describe_addresses and release_address; tests pass fakes.
- `ElasticIpRuntime`: frozen dataclass with the injected client factory and region lister of ElasticIPs (no clock: the module has no age gate).
- `ElasticIpCleaner`: the Cleaner (supports, read-only plan, mutating apply, plus per-region plan_region and apply_region).
- `build_elastic_ip_cleaner()`: registry factory behind @register("aws", "ip"); reads filter_tags, exception_tags and notags from RunContext.options.
- `ElasticIPs`: adapter crc.py calls (delete(), get_deleted, count, deleted_ips); runs the cleaner region by region in the order of main.

## Safety Invariants

- Authoritative text: `CLEANUP_SAFETY.md`. Applicable IDs: SAF-006 to SAF-013 (age gates, shared by all clouds), SAF-001, SAF-003, SAF-004, SAF-014, SAF-015, SAF-016, SAF-017 to SAF-020, SAF-025, SAF-026 to SAF-037.
- Filtering per module: `docs/refactor/FILTER_VARIANTS.md` sections 2 (AWS), 6 and 7.
- Known bugs and quirks (do not fix outside a behaviour-fix rung): `docs/refactor/BUGS.md` rows `BUG-004`, `BUG-007`, `BUG-008`, `BUG-011`, `BUG-012`, `BUG-014`, `BUG-015`, `BUG-020`, `BUG-021`, `BUG-022`, `BUG-051` to `BUG-053`.
- The AWS EBS cleanup needs `--cloud aws --resource disk` (SAF-014); spot requests cancel before terminate (SAF-028).
- Key pairs (R4a): `plan()` only calls `describe_key_pairs`; `delete_key_pair` is called from `apply_region()` only and never in a dry run (SAF-006: an empty age matches every key pair, an empty `name_regex` matches every name). `KeyPairs.delete()` keeps the call order of `main`: per region client, describe, then deletes, so a later region error leaves earlier regions deleted. Connectivity errors skip the region; every other error propagates (CLEANUP_SAFETY.md). Quirks in `BUGS.md`: `BUG-045` to `BUG-048`.
- Elastic IPs (R4b): `plan()` only calls `describe_addresses`; `release_address` is called from `apply_region()` only and never in a dry run. Only addresses without `NetworkInterfaceId` that carry a `Tags` key are considered (BUG-020); there is no age gate (BUG-053), so the filter is the only protection: an empty `filter_tags` selects every tagged unassociated address. Exception tags skip an address (`policy.aws_eip_should_skip`); `notags` raises `TypeError` as on `main` (BUG-011). Connectivity errors skip the region (SAF-001, `describe_regions` falls back to the static list, other errors propagate, SAF-004); every other error propagates and nothing is isolated per address (CLEANUP_SAFETY.md). `ElasticIPs.delete()` keeps the call order of `main` (per region: client, describe, releases). Quirks in `BUGS.md`: `BUG-051` to `BUG-053`.
- Do not call real cloud APIs in tests; mock every SDK client.

## Extension Rules

1. Do not edit these modules to add features or fix bugs in a refactor rung; behaviour fixes are
   separate rungs (`docs/refactor/PLAN.md`).
2. New resources go in a new module with the `Cleaner` contract (`ARCHITECTURE.md`, "Add a resource
   cleaner"), not as another legacy class.
3. Key pair changes need `tests/test_aws_keypair_parity.py` (oracle `tests/legacy/aws_keypairs.txt`, a frozen copy of `main`, never edit it) to stay green; Elastic IP changes need `tests/test_aws_ip_parity.py` (oracle `tests/legacy/aws_elastic_ips.txt`).
4. Refactoring a module means removing it from the ruff `extend-exclude` and mypy override lists in
   the same change (the legacy ratchet only shrinks), then updating this README and its symbol list.
5. Record every new bug or quirk in `docs/refactor/BUGS.md` with its `main` file:line.
