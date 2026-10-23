# crc.aws.vpc

## Purpose

AWS VPC cleaner (AWS-1, subpackage since ST-AWS-VPC). Tears down and deletes the VPCs of every region that match an EC2 `tag:key` filter and are not protected by `exception_tags` / `notags`. The old import path `crc.aws.vpc` keeps working: the package `__init__.py` re-exports every public name, including the `VPC` class `crc.py` uses.

Modules:

- `cleaner.py`: `VpcCleaner` (`plan()` lists and decides protection, `apply()` tears down and deletes), its registry factory, the runtime dataclass and the `VPC` adapter.
- `teardown.py`: `tear_down()`, the detach and delete steps of everything a VPC owns, in the order of `main` without the instance termination, and `has_instances()` (the read-only instance scan).
- `delete.py`: `delete_vpc_with_retries()`, `delete_vpc` retried on `DependencyViolation` only.
- `client.py`: typed Protocols of the boto3 EC2 client, resource and resource objects the VPC teardown walks.

## Public API

- `VPC`: adapter that crc.py calls (delete(), get_deleted, delete_count, vpc_ids_to_delete, get_vpc_ids); runs the cleaner region by region, VPC by VPC, in the order of main.
- `VpcCleaner`: the Cleaner (supports, read-only plan, mutating apply, plus require_filter_tags, build_filter, list_vpcs, plan_region, apply_region, is_default, is_protected, should_skip and delete_vpc used by the adapter; apply_region and delete_vpc report which VPCs were kept; the `sleep` attribute is the injected sleep between delete retries).
- `VpcRuntime`: frozen dataclass with the injected client factory, resource factory and region lister of VPC (and the sleep between delete retries; no clock: the module has no age gate).
- `build_vpc_cleaner()`: registry factory behind @register("aws", "vpc"); reads filter_tags, exception_tags and notags from RunContext.options.
- `has_instances()`: (teardown.py) read-only scan, True when a subnet of the VPC has an instance; the VPC is then kept (BUG-088).
- `delete_vpc_with_retries()`: (delete.py) delete_vpc retried on DependencyViolation only, other errors recorded and the VPC skipped (BUG-087).
- `tear_down()`: (teardown.py) detaches and deletes the gateways, route tables, endpoints, security groups, peering connections, network ACLs, subnets and interfaces of one VPC, in the order of the original implementation; called by the VPC cleaner before it deletes the VPC.
- `Deletable`, `Collection`, `InternetGateway`, `RouteTableAssociation`, `RouteTable`, `Instance`, `Subnet`, `SecurityGroup`, `NetworkAcl`, `DhcpOptionsHandle`, `Vpc`, `VpcCollection`: Protocols (client.py) of the boto3 EC2 resource objects the VPC teardown walks; tests pass fakes.
- `Ec2Resource`, `Ec2Client`: Protocols (client.py) of the boto3 EC2 resource (vpcs.filter, DhcpOptions, VpcPeeringConnection) and the four client calls used (describe_vpc_endpoints, delete_vpc_endpoints, describe_vpc_peering_connections, delete_vpc).

## Safety Invariants

- `plan()` only lists (`ec2.vpcs.filter` with the server side `tag:key` filter) and decides protection; every mutating call (`associate_with_vpc`, gateway, route table, endpoint, security group, peering, ACL, interface, subnet and `delete_vpc`) is in `apply()` / `apply_region()` / `VpcCleaner.delete_vpc()` and never runs in a dry run. There is no age gate (the age part of BUG-083 is a later rung).
- Empty `filter_tags` raises `ValueError` before any SDK call (`require_filter_tags`, dry run too): it would select every VPC of every region (BUG-083, fixed in FIX-AWS-VPC). A default VPC (`is_default` not explicitly `False`) is never touched: it is skipped (`skip("default_vpc")`), is not a candidate and is not listed as deleted (BUG-083).
- Protection (`policy.exception_tags_any`, `policy.notags_all`) is evaluated on the VPC's tags (`vpc.tags`, `None` is no tags) (BUG-012, fixed). A VPC skipped as protected is still recorded in the deleted list of the run, as on `main` (second half of BUG-012, left open).
- Instances are never terminated. A VPC that still has an instance in any subnet is kept before anything is detached or deleted (`has_instances`, `skip("has_instances")`) and is not listed as deleted (BUG-088, fixed). The check runs in real runs only, so a dry run may still list such a VPC.
- `delete_vpc` is retried (up to 5 attempts, injected sleep of 3 s between attempts) only on a `ClientError` with code `DependencyViolation`; any other error is logged, recorded with `run.fail` and the VPC is skipped and not listed as deleted (BUG-087, fixed in FIX-AWS-VPC, `delete.py`).
- Connectivity errors skip the region (SAF-001, `describe_regions` falls back to the static list, other errors propagate, SAF-004); every other teardown error propagates and nothing is isolated per VPC (CLEANUP_SAFETY.md). `VPC.delete()` keeps the call order of `main` (per region: client, resource, listing, then for each VPC protection check, instance scan and teardown). The Cleaner path decides protection for a whole region in `plan()`, so after an aborted region it logs the `Tags and notags not present` warning of VPCs `main` never reached. Quirks: BUG-021, BUG-084 to BUG-086 and BUG-089 to BUG-095 (AWS-1).
- Do not call real cloud APIs in tests; mock every SDK client.

## Extension Rules

1. No behaviour change in a refactor rung; behaviour fixes are separate rungs (`docs/refactor/PLAN.md`).
2. Keep filtering in `crc.core.policy`; no clock or environment reads here (ARCH-003).
3. Keep every mutating call in `apply()` / `apply_region()` / `VpcCleaner.delete_vpc()`; `plan()` and what it calls stay read-only (ARCH-005).
4. Changes need `tests/test_aws_vpc_parity.py` (oracle `tests/legacy/aws_vpc.txt`, a frozen copy of `main`, never edit it) and `tests/test_aws_vpc.py` to stay green.
5. Every file stays under 400 lines; split by responsibility and keep this README in sync with the public names.
