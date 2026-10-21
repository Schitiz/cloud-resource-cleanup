# crc.aws

## Purpose

Legacy AWS cleaners (boto3). They delete or stop leftover EC2, EBS, network, key and KMS resources across regions.

**Partly refactored.** `keypairs.py` (R4a), `elastic_ips.py` (R4b), `kms.py` (R4c), `vpc.py` with `vpc_api.py` (AWS-1), `snapshot.py` (AWS-2) and `vm.py` with `vm_cleaner.py`, `vm_api.py`, `vm_scan.py` (AWS-3) are `Cleaner`s (no behaviour change); every other module is legacy, not yet refactored, and the same as on `main`. Any change must follow `ARCHITECTURE.md` and the refactor rung for this package in `docs/refactor/PLAN.md` (Rung R4+), with `make check` green.

Modules (operations and filters as catalogued in `docs/refactor/FILTER_VARIANTS.md`):

- `_base.py`: `get_all_regions` (region list via `describe_regions`)
- `connectivity.py`: `log_skipped_region` (unreachable regions are logged and skipped)
- `disk/`: package (`__init__.py` keeps the import path `crc.aws.disk`): `DiskCleaner` (registered as `aws` / `disk`) and the `Disk` adapter: deletes available EBS volumes (`delete_volume`); tags, regex, `yb_task` and Kubernetes skips, CloudWatch detach age; opt-in `--cloud aws --resource disk`. See `crc/aws/disk/README.md`
- `elastic_ips.py`: `ElasticIpCleaner` (registered as `aws` / `ip`) and the `ElasticIPs` adapter: releases unassociated, tagged Elastic IPs (`release_address`)
- `keypairs.py`: `KeyPairCleaner` (registered as `aws` / `keypair`) and the `KeyPairs` adapter: deletes key pairs by name regex (`delete_key_pair`)
- `kms.py`: `KmsCleaner` (registered as `aws` / `kms`) and the `Kms` adapter: schedules key deletion (`schedule_key_deletion`) for keys matching description and user ARN
- `snapshot.py`: `SnapshotCleaner` (registered as `aws` / `snapshot`) and the `Snapshot` adapter: deletes snapshots older than `age_days` (`delete_snapshot`) that carry no exception tag and back no AMI
- `spot_instance_requests.py`: `SpotInstanceRequests`: cancels spot requests, terminates instances, deletes leftover volumes
- `vm.py`: `VM` adapter of the VM cleaner (`delete()`, `stop()`, `find_instances_with_tag()`) and its `VmRuntime`
- `vm_cleaner.py`: `VmCleaner` (registered as `aws` / `vm`): terminates (`terminate_instances`) or stops (`stop_instances`) running instances
- `vm_api.py`: typed Protocols of the boto3 EC2 client calls the VM cleaner and the tag scan use
- `vm_scan.py`: read-only scan of instances by tag across regions (`find_instances_with_tag`)
- `vpc.py`: `VpcCleaner` (registered as `aws` / `vpc`) and the `VPC` adapter: tears down and deletes VPCs matching an EC2 `tag:key` filter (`delete_vpc`)
- `vpc_api.py`: typed Protocols of the boto3 EC2 client, resource and resource objects the VPC cleaner uses

## Public API

keypairs.py, elastic_ips.py, kms.py, snapshot.py, vm.py, vm_cleaner.py, vm_api.py, vm_scan.py, vpc.py and vpc_api.py are refactored, so the names below are synced with this README by ARCH-002. The
other modules (get_all_regions, log_skipped_region, Disk,
SpotInstanceRequests) are legacy; each has delete().
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
- `SnapshotClient`: Protocol of the three EC2 calls used, describe_snapshots, describe_images and delete_snapshot; tests pass fakes.
- `SnapshotRuntime`: frozen dataclass with the injected client factory, region lister and clock (now, UTC) of Snapshot.
- `SnapshotCleaner`: the Cleaner (supports, read-only plan, mutating apply, plus check_age, iter_region, delete_one and is_protected used by the adapter).
- `build_snapshot_cleaner()`: registry factory behind @register("aws", "snapshot"); reads age_days (default 90, the value crc.py passes) and exception_tags from RunContext.options.
- `Snapshot`: adapter crc.py calls (delete(), get_deleted, delete_count, deleted_snapshots); runs the cleaner region by region, snapshot by snapshot, in the order of main.
- `VmClient`: Protocol of the four EC2 calls used, describe_instances, describe_network_interfaces, terminate_instances and stop_instances; tests pass fakes.
- `VmPaginator`: Protocol of the describe_instances paginator (paginate) used by the tag scan.
- `VmScanClient`: Protocol of the EC2 client surface of the tag scan (get_paginator, exceptions).
- `VmSession`: Protocol of the boto3 session call of the tag scan (get_available_regions).
- `VmSettings`: frozen dataclass with the filters and thresholds of one run (filter_tags, exception_tags, notags, age, custom_age_tag_key, instance_state).
- `VmCleaner`: the Cleaner (supports, read-only plan, mutating apply, plus build_filters, filter_instances, apply_region and should_skip used by the adapter).
- `build_vm_cleaner()`: registry factory behind @register("aws", "vm"); reads filter_tags, exception_tags, notags, age, custom_age_tag_key and instance_state from RunContext.options.
- `boto3_client()`: default client factory of the VM cleaner (boto3.client("ec2", region_name=...)).
- `all_regions()`: default region lister of the VM cleaner (get_all_regions("ec2", "us-west-2")).
- `skip_region()`: logs a region skipped for a connectivity error (context "ec2 vm <operation>").
- `log_summary()`: the closing warnings of a VM run (no instances, number and list deleted or stopped, or the dry-run list).
- `dry_run_names()`: what a VM dry run records, names for delete but instance ids for stop (as on main).
- `instance_name()`: value of the first Name tag of an instance, or None.
- `find_instances_with_tag()`: read-only scan of instances carrying a tag in every region (vm_scan.py).
- `VmRuntime`: frozen dataclass with the injected client factory, region lister, clock (now, UTC), scan client factory and session factory of VM.
- `VM`: adapter crc.py calls (delete(), stop(), get_deleted, get_stopped, delete_count, stopped_count, find_instances_with_tag(), instance_names_to_delete, instance_names_to_stop); runs the cleaner region by region in the order of main; tests replace its runtime attribute with fakes.
- `Deletable`, `Collection`, `InternetGateway`, `RouteTableAssociation`, `RouteTable`, `Instance`, `Subnet`, `SecurityGroup`, `NetworkAcl`, `DhcpOptionsHandle`, `Vpc`, `VpcCollection`: Protocols (vpc_api.py) of the boto3 EC2 resource objects the VPC teardown walks; tests pass fakes.
- `Ec2Resource`, `Ec2Client`: Protocols (vpc_api.py) of the boto3 EC2 resource (vpcs.filter, DhcpOptions, VpcPeeringConnection) and the four client calls used (describe_vpc_endpoints, delete_vpc_endpoints, describe_vpc_peering_connections, delete_vpc).
- `VpcRuntime`: frozen dataclass with the injected client factory, resource factory and region lister of VPC (no clock: the module has no age gate).
- `VpcCleaner`: the Cleaner (supports, read-only plan, mutating apply, plus build_filter, list_vpcs, plan_region, apply_region, is_protected, should_skip and delete_vpc used by the adapter).
- `build_vpc_cleaner()`: registry factory behind @register("aws", "vpc"); reads filter_tags, exception_tags and notags from RunContext.options.
- `VPC`: adapter crc.py calls (delete(), get_deleted, delete_count, vpc_ids_to_delete, get_vpc_ids); runs the cleaner region by region, VPC by VPC, in the order of main.

### spot_instance_requests

Refactored in AWS-5 into the subpackage crc/aws/spot_instance_requests/ (its own README lists the names). The old import path still works: crc.py imports SpotInstanceRequests, a thin adapter over the registered Cleaner (cloud aws, kind spot_instance_requests) with the same constructor, delete(), get_deleted, delete_count, spot_requests_to_delete, instance_ids_to_delete and volumes_to_delete.

Safety Invariants: plan() only describes (a dry run is plan() alone and also performs the reads of the real path); tag, cancel, terminate, wait and delete happen in apply() in the order of CLEANUP_SAFETY.md (SAF-028 to SAF-033). Cancel before terminate; a failed tag or cancel aborts; leftover volumes are protected by their own exception, notags and sensitive yb_task tags; untagged requests and bad custom age tags are kept. Quirks: BUG-004, BUG-021, BUG-022 and docs/refactor/bugs/pending/AWS-5.md.

Extension Rules: changes need tests/test_aws_spot_instance_requests_parity.py (oracle tests/legacy/aws_spot_instance_requests.txt, a frozen copy of main, never edit it), tests/test_aws_spot_instance_requests_cleaner.py and tests/test_aws_spot_instance_requests.py to stay green.

### disk

The EBS disk cleaner is a subpackage with its own README (crc/aws/disk/README.md) that lists its public names. It exports the Cleaner (registered as aws / disk), the legacy adapter class that crc.py calls, the runtime dataclass and the registry factory, with the typed Protocols of the boto3 EC2 and CloudWatch calls it uses in client.py.

## Safety Invariants

- Authoritative text: `CLEANUP_SAFETY.md`. Applicable IDs: SAF-006 to SAF-013 (age gates, shared by all clouds), SAF-001, SAF-003, SAF-004, SAF-014, SAF-015, SAF-016, SAF-017 to SAF-020, SAF-025, SAF-026 to SAF-037.
- Filtering per module: `docs/refactor/FILTER_VARIANTS.md` sections 2 (AWS), 6 and 7.
- Known bugs and quirks (do not fix outside a behaviour-fix rung): `docs/refactor/BUGS.md` rows `BUG-004`, `BUG-007`, `BUG-008`, `BUG-011`, `BUG-012`, `BUG-014`, `BUG-015`, `BUG-020`, `BUG-021`, `BUG-022`, `BUG-051` to `BUG-061`, and for snapshots `BUG-009`, `BUG-040` and the AWS-2 entries (`docs/refactor/bugs/pending/AWS-2.md`).
- The AWS EBS cleanup needs `--cloud aws --resource disk` (SAF-014); spot requests cancel before terminate (SAF-028).
- Key pairs (R4a): `plan()` only calls `describe_key_pairs`; `delete_key_pair` is called from `apply_region()` only and never in a dry run (SAF-006: an empty age matches every key pair, an empty `name_regex` matches every name). `KeyPairs.delete()` keeps the call order of `main`: per region client, describe, then deletes, so a later region error leaves earlier regions deleted. Connectivity errors skip the region; every other error propagates (CLEANUP_SAFETY.md). Quirks in `BUGS.md`: `BUG-045` to `BUG-048`.
- Elastic IPs (R4b): `plan()` only calls `describe_addresses`; `release_address` is called from `apply_region()` only and never in a dry run. Only addresses without `NetworkInterfaceId` that carry a `Tags` key are considered (BUG-020); there is no age gate (BUG-053), so the filter is the only protection: an empty `filter_tags` selects every tagged unassociated address. Exception tags skip an address (`policy.aws_eip_should_skip`); `notags` raises `TypeError` as on `main` (BUG-011). Connectivity errors skip the region (SAF-001, `describe_regions` falls back to the static list, other errors propagate, SAF-004); every other error propagates and nothing is isolated per address (CLEANUP_SAFETY.md). `ElasticIPs.delete()` keeps the call order of `main` (per region: client, describe, releases). Quirks in `BUGS.md`: `BUG-051` to `BUG-054`.
- KMS (R4c): `plan()` calls `list_keys`, `list_resource_tags`, `describe_key` and `get_key_policy` only; `schedule_key_deletion` is called from `apply()` (and `Kms.delete()`) only and never in a dry run. Works in `us-west-2` only; a connectivity error there skips the cleanup (SAF-001) and every other list error propagates (SAF-004). Per key, any error skips that key (a bare `except:` on `main`, so keeping it fails closed, but a key found for the user before the error stays selected: BUG-055); the age gate is `is_old` with the fail-open custom age tag that never matches (SAF-006 to SAF-010, BUG-004, BUG-008) and `filter_tags` needs every (key, value) pair (`policy.filter_tags_exact_pairs`, BUG-007, BUG-014); exception tags raise `KeyError` for any tagged key and so skip it (BUG-015). The same key can be scheduled twice and a scheduling error aborts the run without a record of earlier keys (BUG-056, BUG-057). Quirks in `BUGS.md`: `BUG-055` to `BUG-061`.
- VPC (AWS-1): `plan()` only lists (`ec2.vpcs.filter` with the server side `tag:key` filter) and decides protection; every mutating call (`associate_with_vpc`, gateway, route table, instance, endpoint, security group, peering, ACL, interface, subnet and `delete_vpc`) is in `apply()` / `apply_region()` / `VpcCleaner.delete_vpc()` and never runs in a dry run. There is no age gate and no default-VPC guard, so an empty `filter_tags` selects every VPC of every region (NEW in `docs/refactor/bugs/pending/AWS-1.md`); only the EC2 tag filter, `exception_tags` and `notags` protect a VPC. Protection (`policy.exception_tags_any`, `policy.notags_all`) is evaluated on the boto3 Vpc resource, not on its tags, so with `exception_tags` or `notags` set a real run raises `TypeError` before anything is deleted and every listed VPC, protected or not, is recorded as deleted (BUG-012). Connectivity errors skip the region (SAF-001, `describe_regions` falls back to the static list, other errors propagate, SAF-004); every other error propagates and nothing is isolated per VPC (CLEANUP_SAFETY.md); only `delete_vpc` is retried 5 times and its errors are swallowed. `VPC.delete()` keeps the call order of `main` (per region: client, resource, listing, then for each VPC protection check and teardown). The Cleaner path decides protection for a whole region in `plan()`, so after an aborted region it logs the `Tags and notags not present` warning of VPCs `main` never reached. Quirks: BUG-012, BUG-021 and the AWS-1 entries.
- Snapshots (AWS-2): `plan()` only calls `describe_snapshots` and `describe_images`; `delete_snapshot` is called from `apply()` (and `Snapshot.delete()` through `SnapshotCleaner.delete_one`) only and never in a dry run (the age gate is its own day cutoff, not `is_old`, so SAF-006 to SAF-013 do not apply as written: `policy.snapshot_old_enough`, a snapshot started exactly at `now - age_days` is old, `StartTime` after it is kept; a non-numeric or overflowing `age_days` raises `TypeError` / `OverflowError` before any call, while `0`, negative or `True` are accepted by `timedelta`). There is no `filter_tags`, `notags` or name filter, so every old snapshot of the account in every region is selected unless an exception tag (`policy.exception_tags_any`, one key at a time so the log names the first matching key and a tag entry without `Key` or `Value` raises `KeyError` as on `main`) or an AMI of the same account and region protects it (AWS-2 entries in `docs/refactor/bugs/pending/AWS-2.md`). Connectivity errors skip the region (SAF-001, `describe_regions` falls back to the static list, other errors propagate, SAF-004); every other listing error propagates and nothing is isolated per snapshot; a `delete_snapshot` error of any kind is logged and swallowed and the snapshot is not recorded. `Snapshot.delete()` keeps the call order of `main` (per region: client, `describe_snapshots`, `describe_images`, then per snapshot the decision and the delete). The Cleaner path lists every region before deleting, so a listing error in a later region is raised before earlier regions are deleted, and its skip log lines come before the `Deleted snapshot` lines. Quirks: `BUG-009`, `BUG-040`, the AWS-2 entries.
- VMs (AWS-3): `plan()` only calls `describe_instances` and `describe_network_interfaces`; `terminate_instances` and `stop_instances` are called from `apply()` / `apply_region()` (and `VM.delete()` / `VM.stop()` through them) only and never in a dry run. The only server side filters are the instance state (default `running`) and `tag:key` filters (BUG-021); an instance needs a `Tags` key (BUG-020) and a `Name` tag, exception tags (any key, checked tag by tag) and notags (all keys) skip it, and its age is the attach time of its first network interface compared with `--age` or the fail-open custom age tag (`core.age.is_old`, `policy.effective_age`, SAF-006 to SAF-010, BUG-004): an empty age matches every instance and `MAX_AGE` can shorten it. Any error while judging one instance is logged and keeps the instance (fail closed), including connectivity errors; a `describe_instances` connectivity error skips the region (SAF-001, `describe_regions` falls back to the static list, other errors propagate, SAF-004). Termination and stop errors are isolated per instance (logged, instance not recorded). A dry run of `stop` records instance ids, not names (AWS-3 entries in `docs/refactor/bugs/pending/AWS-3.md`). `VM.delete()` keeps the call order of `main` (per region: client, describe, per-instance decision and NIC lookup, then the calls). The Cleaner path lists every region before it mutates, so with several regions a listing error is raised before earlier regions are terminated and its mutating log lines come after all listing lines; the closing summary is logged by `plan()` in a dry run and by `apply()` otherwise. Quirks: BUG-004, BUG-020, BUG-021 and the AWS-3 entries.
- Do not call real cloud APIs in tests; mock every SDK client.

### disk

- AWS-4: plan() only lists volumes (describe_volumes paginator) and queries CloudWatch get_metric_data; delete_volume is called from apply() and apply_region() only and never in a dry run. An age gate is required (age and/or detach_age), CreateTime is compared with a floor that ignores MAX_AGE, and a missing CreateTime, invalid custom age tag or incomplete CloudWatch answer keeps the volume (SAF-006, SAF-010, SAF-014). Region errors never propagate (connectivity and unauthorised errors skip the region, others are logged and flagged); describe_regions errors other than connectivity propagate. The adapter keeps the call and log order of main; the Cleaner path lists every region before deleting. Quirks: BUG-004, BUG-022 and docs/refactor/bugs/pending/AWS-4.md.

## Extension Rules

1. Do not edit these modules to add features or fix bugs in a refactor rung; behaviour fixes are
   separate rungs (`docs/refactor/PLAN.md`).
2. New resources go in a new module with the `Cleaner` contract (`ARCHITECTURE.md`, "Add a resource
   cleaner"), not as another legacy class.
3. VM changes need `tests/test_aws_vm_parity.py` (oracle `tests/legacy/aws_vm.txt`, a frozen copy of `main`, never edit it) and `tests/test_aws_vm.py` to stay green; snapshot changes need `tests/test_aws_snapshot_parity.py` (oracle `tests/legacy/aws_snapshot.txt`, a frozen copy of `main`, never edit it) and `tests/test_aws_snapshot.py` to stay green; VPC changes need `tests/test_aws_vpc_parity.py` (oracle `tests/legacy/aws_vpc.txt`, a frozen copy of `main`, never edit it) and `tests/test_aws_vpc.py` to stay green; key pair changes need `tests/test_aws_keypair_parity.py` (oracle `tests/legacy/aws_keypairs.txt`, a frozen copy of `main`, never edit it) to stay green; Elastic IP changes need `tests/test_aws_ip_parity.py` (oracle `tests/legacy/aws_elastic_ips.txt`); KMS changes need `tests/test_aws_kms_parity.py` (oracle `tests/legacy/aws_kms.txt`).
4. Refactoring a module means removing it from the ruff `extend-exclude` and mypy override lists in
   the same change (the legacy ratchet only shrinks), then updating this README and its symbol list.
5. Record every new bug or quirk in `docs/refactor/BUGS.md` with its `main` file:line.

### disk

Disk changes need tests/test_aws_disk_parity.py (oracle tests/legacy/aws_disk.txt, a frozen copy of main, never edit it), tests/test_aws_disk_cleaner.py and tests/test_aws_disk.py to stay green.
