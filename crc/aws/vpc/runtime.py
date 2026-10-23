# Copyright (c) Yugabyte, Inc.

"""Constants, injected collaborators and logging helpers of the AWS VPC cleaner."""

import logging
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

import boto3

from crc.aws import _regionlog
from crc.aws._base import get_all_regions
from crc.aws.connectivity import log_skipped_region
from crc.aws.vpc.client import Ec2Client, Ec2Resource
from crc.aws.vpc.delete import Sleeper

SERVICE_NAME = "ec2"
DEFAULT_REGION = "us-west-2"
SKIP_CONTEXT = "VPC cleanup"
PROTECTED = "protected"

TagSpec = Mapping[str, Sequence[str]]


ClientFactory = Callable[[str], Ec2Client]
ResourceFactory = Callable[[str], Ec2Resource]
RegionLister = Callable[[], Sequence[str]]


def boto3_client(region: str) -> Ec2Client:
    client: Ec2Client = boto3.client(SERVICE_NAME, region_name=region)
    return client


def boto3_resource(region: str) -> Ec2Resource:
    resource: Ec2Resource = boto3.resource(SERVICE_NAME, region_name=region)
    return resource


def all_regions() -> Sequence[str]:
    return get_all_regions(SERVICE_NAME, DEFAULT_REGION)


@dataclass(frozen=True, slots=True)
class VpcRuntime:
    """Injected collaborators of `VPC`: the SDK client and resource factories, the region
    lister and the sleep between `delete_vpc` retries (no clock: the module has no age gate)."""

    client_factory: ClientFactory = boto3_client
    resource_factory: ResourceFactory = boto3_resource
    list_regions: RegionLister = all_regions
    sleep: Sleeper = time.sleep


def skip_region(region: str, error: BaseException) -> None:
    _regionlog.region_skipped(region, error)
    log_skipped_region(region, SKIP_CONTEXT, error)


def log_summary(deleted: Sequence[str], *, dry_run: bool) -> None:
    items = list(deleted)
    if dry_run:
        logging.warning(f"List of AWS VPCs (Total: {len(items)}) which will be deleted: {items}")
    else:
        logging.warning(f"Number of AWS VPCs deleted: {len(items)}")
        logging.warning(f"List of AWS VPCs deleted: {items}")
