# crc.aws

## Purpose

Legacy AWS cleaners (boto3). They delete or stop leftover EC2, EBS, network, key and KMS resources across regions.

**Partly refactored.** `keypairs.py` (R4a), `elastic_ips.py` (R4b), `kms.py` (R4c) and `vpc.py` with `vpc_api.py` (AWS-1) are `Cleaner`s (no behaviour change); every other module is legacy, not yet refactored, and the same as on `main`. Any change must follow `ARCHITECTURE.md` and the refactor rung for this package in `docs/refactor/PLAN.md` (Rung R4+), with `make check` green.

Modules (operations and filters as catalogued in `docs/refactor/FILTER_VARIANTS.md`):

- `_base.py`: `get_all_regions` (region list via `describe_regions`)
- `connectivity.py`: `log_skipped_region` (unreachable regions are logged and skipped)
- `disk.py`: `Disk`: deletes available EBS volumes (`delete_volume`); tags, regex, `yb_task` and Kubernetes skips, CloudWatch detach age; opt-in `--cloud aws --resource disk`
- `elastic_ips.py`: `ElasticIpCleaner` (registered as `aws` / `ip`) and the `ElasticIPs` adapter: releases unassociated, tagged Elastic IPs (`release_address`)
- `keypairs.py`: `KeyPairCleaner` (registered as `aws` / `keypair`) and the `KeyPairs` adapter: deletes key pairs by name regex (`delete_key_pair`)
- `kms.py`: `KmsCleaner` (registered as `aws` / `kms`) and the `Kms` adapter: schedules key deletion (`schedule_key_deletion`) for keys matching description and user ARN
- `snapshot.py`: `Snapshot`: deletes snapshots older than `age_days` (`delete_snapshot`)
- `spot_instance_requests.py`: `SpotInstanceRequests`: cancels spot requests, terminates instances, deletes leftover volumes
- `vm.py`: `VM`: terminates (`terminate_instances`) or stops (`stop_instances`) running instances
- `vpc.py`: `VpcCleaner` (registered as `aws` / `vpc`) and the `VPC` adapter: tears down and deletes VPCs matching an EC2 `tag:key` filter (`delete_vpc`)
- `vpc_api.py`: typed Protocols of the boto3 EC2 client, resource and resource objects the VPC cleaner uses

## Public API

keypairs.py, elastic_ips.py, kms.py, vpc.py and vpc_api.py are refactored, so the names below are synced with this README by ARCH-002. The
other modules (get_all_regions, log_skipped_region, Disk, Snapshot,
SpotInstanceRequests, VM) are legacy; each has delete(), VM also stop().
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
- `KmsClient`: Protocol of the five KMS calls used (get_paginator, list_resource_tags, describe_key, get_key_policy, schedule_key_deletion); tests pass fakes.
- `KmsPaginator`: Protocol of the list_keys paginator (paginate).
- `KmsRuntime`: frozen dataclass with the injected client factory and clock (now) of Kms.
- `KmsSettings`: frozen dataclass with the filters and thresholds of one run (filter_tags, exception_tags, description, user, pending window, age, custom age tag key).
- `KmsCleaner`: the Cleaner (supports, read-only plan, mutating apply, plus connect_and_list, plan_keys and schedule used by the adapter).
- `build_kms_cleaner()`: registry factory behind @register("aws", "kms"); reads filter_tags, exception_tags, kms_key_description, kms_user, kms_pending_window, age and custom_age_tag_key from RunContext.options.
- `Kms`: adapter crc.py calls (delete(), get_deleted, kms_keys_to_delete); runs the cleaner in the order of main.
- `Deletable`, `Collection`, `InternetGateway`, `RouteTableAssociation`, `RouteTable`, `Instance`, `Subnet`, `SecurityGroup`, `NetworkAcl`, `DhcpOptionsHandle`, `Vpc`, `VpcCollection`: Protocols (vpc_api.py) of the boto3 EC2 resource objects the VPC teardown walks; tests pass fakes.
- `Ec2Resource`, `Ec2Client`: Protocols (vpc_api.py) of the boto3 EC2 resource (vpcs.filter, DhcpOptions, VpcPeeringConnection) and the four client calls used (describe_vpc_endpoints, delete_vpc_endpoints, describe_vpc_peering_connections, delete_vpc).
- `VpcRuntime`: frozen dataclass with the injected client factory, resource factory and region lister of VPC (no clock: the module has no age gate).
- `VpcCleaner`: the Cleaner (supports, read-only plan, mutating apply, plus build_filter, list_vpcs, plan_region, apply_region, is_protected, should_skip and delete_vpc used by the adapter).
- `build_vpc_cleaner()`: registry factory behind @register("aws", "vpc"); reads filter_tags, exception_tags and notags from RunContext.options.
- `VPC`: adapter crc.py calls (delete(), get_deleted, delete_count, vpc_ids_to_delete, get_vpc_ids); runs the cleaner region by region, VPC by VPC, in the order of main.

## Safety Invariants

- Authoritative text: `CLEANUP_SAFETY.md`. Applicable IDs: SAF-006 to SAF-013 (age gates, shared by all clouds), SAF-001, SAF-003, SAF-004, SAF-014, SAF-015, SAF-016, SAF-017 to SAF-020, SAF-025, SAF-026 to SAF-037.
- Filtering per module: `docs/refactor/FILTER_VARIANTS.md` sections 2 (AWS), 6 and 7.
- Known bugs and quirks (do not fix outside a behaviour-fix rung): `docs/refactor/BUGS.md` rows `BUG-004`, `BUG-007`, `BUG-008`, `BUG-011`, `BUG-012`, `BUG-014`, `BUG-015`, `BUG-020`, `BUG-021`, `BUG-022`, `BUG-051` to `BUG-061`.
- The AWS EBS cleanup needs `--cloud aws --resource disk` (SAF-014); spot requests cancel before terminate (SAF-028).
- Key pairs (R4a): `plan()` only calls `describe_key_pairs`; `delete_key_pair` is called from `apply_region()` only and never in a dry run (SAF-006: an empty age matches every key pair, an empty `name_regex` matches every name). `KeyPairs.delete()` keeps the call order of `main`: per region client, describe, then deletes, so a later region error leaves earlier regions deleted. Connectivity errors skip the region; every other error propagates (CLEANUP_SAFETY.md). Quirks in `BUGS.md`: `BUG-045` to `BUG-048`.
- Elastic IPs (R4b): `plan()` only calls `describe_addresses`; `release_address` is called from `apply_region()` only and never in a dry run. Only addresses without `NetworkInterfaceId` that carry a `Tags` key are considered (BUG-020); there is no age gate (BUG-053), so the filter is the only protection: an empty `filter_tags` selects every tagged unassociated address. Exception tags skip an address (`policy.aws_eip_should_skip`); `notags` raises `TypeError` as on `main` (BUG-011). Connectivity errors skip the region (SAF-001, `describe_regions` falls back to the static list, other errors propagate, SAF-004); every other error propagates and nothing is isolated per address (CLEANUP_SAFETY.md). `ElasticIPs.delete()` keeps the call order of `main` (per region: client, describe, releases). Quirks in `BUGS.md`: `BUG-051` to `BUG-054`.
- KMS (R4c): `plan()` calls `list_keys`, `list_resource_tags`, `describe_key` and `get_key_policy` only; `schedule_key_deletion` is called from `apply()` (and `Kms.delete()`) only and never in a dry run. Works in `us-west-2` only; a connectivity error there skips the cleanup (SAF-001) and every other list error propagates (SAF-004). Per key, any error skips that key (a bare `except:` on `main`, so keeping it fails closed, but a key found for the user before the error stays selected: BUG-055); the age gate is `is_old` with the fail-open custom age tag that never matches (SAF-006 to SAF-010, BUG-004, BUG-008) and `filter_tags` needs every (key, value) pair (`policy.filter_tags_exact_pairs`, BUG-007, BUG-014); exception tags raise `KeyError` for any tagged key and so skip it (BUG-015). The same key can be scheduled twice and a scheduling error aborts the run without a record of earlier keys (BUG-056, BUG-057). Quirks in `BUGS.md`: `BUG-055` to `BUG-061`.
- VPC (AWS-1): `plan()` only lists (`ec2.vpcs.filter` with the server side `tag:key` filter) and decides protection; every mutating call (`associate_with_vpc`, gateway, route table, instance, endpoint, security group, peering, ACL, interface, subnet and `delete_vpc`) is in `apply()` / `apply_region()` / `VpcCleaner.delete_vpc()` and never runs in a dry run. There is no age gate and no default-VPC guard, so an empty `filter_tags` selects every VPC of every region (NEW in `docs/refactor/bugs/pending/AWS-1.md`); only the EC2 tag filter, `exception_tags` and `notags` protect a VPC. Protection (`policy.exception_tags_any`, `policy.notags_all`) is evaluated on the boto3 Vpc resource, not on its tags, so with `exception_tags` or `notags` set a real run raises `TypeError` before anything is deleted and every listed VPC, protected or not, is recorded as deleted (BUG-012). Connectivity errors skip the region (SAF-001, `describe_regions` falls back to the static list, other errors propagate, SAF-004); every other error propagates and nothing is isolated per VPC (CLEANUP_SAFETY.md); only `delete_vpc` is retried 5 times and its errors are swallowed. `VPC.delete()` keeps the call order of `main` (per region: client, resource, listing, then for each VPC protection check and teardown). The Cleaner path decides protection for a whole region in `plan()`, so after an aborted region it logs the `Tags and notags not present` warning of VPCs `main` never reached. Quirks: BUG-012, BUG-021 and the AWS-1 entries.
- Do not call real cloud APIs in tests; mock every SDK client.

## Extension Rules

1. Do not edit these modules to add features or fix bugs in a refactor rung; behaviour fixes are
   separate rungs (`docs/refactor/PLAN.md`).
2. New resources go in a new module with the `Cleaner` contract (`ARCHITECTURE.md`, "Add a resource
   cleaner"), not as another legacy class.
3. VPC changes need `tests/test_aws_vpc_parity.py` (oracle `tests/legacy/aws_vpc.txt`, a frozen copy of `main`, never edit it) and `tests/test_aws_vpc.py` to stay green; key pair changes need `tests/test_aws_keypair_parity.py` (oracle `tests/legacy/aws_keypairs.txt`, a frozen copy of `main`, never edit it) to stay green; Elastic IP changes need `tests/test_aws_ip_parity.py` (oracle `tests/legacy/aws_elastic_ips.txt`); KMS changes need `tests/test_aws_kms_parity.py` (oracle `tests/legacy/aws_kms.txt`).
4. Refactoring a module means removing it from the ruff `extend-exclude` and mypy override lists in
   the same change (the legacy ratchet only shrinks), then updating this README and its symbol list.
5. Record every new bug or quirk in `docs/refactor/BUGS.md` with its `main` file:line.
