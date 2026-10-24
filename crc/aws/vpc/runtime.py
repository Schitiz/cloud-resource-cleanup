# Copyright (c) Yugabyte, Inc.

"""Constants, client factories and logging helpers of the AWS VPC cleaner."""

import logging
from collections.abc import Callable, Mapping, Sequence

import boto3

from crc.aws import _regionlog
from crc.aws._base import get_all_regions
from crc.aws.connectivity import log_skipped_region
from crc.aws.vpc.client import Ec2Client, Ec2Resource

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


def skip_region(region: str, error: BaseException) -> None:
    _regionlog.region_skipped(region, error)
    log_skipped_region(region, SKIP_CONTEXT, error)


def log_summary(deleted: Sequence[str], *, dry_run: bool) -> None:
    items = list(deleted)
    if dry_run:
        logging.warning("List of AWS VPCs (Total: %s) which will be deleted: %s", len(items), items)
    else:
        logging.warning("Number of AWS VPCs deleted: %s", len(items))
        logging.warning("List of AWS VPCs deleted: %s", items)
