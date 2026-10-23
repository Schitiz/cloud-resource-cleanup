# Copyright (c) Yugabyte, Inc.

"""Typed EC2 client Protocol, default factory and injected runtime of the Elastic IP cleaner."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import boto3

from crc.aws._common import EC2_SERVICE_NAME, ec2_regions

TagSpec = Mapping[str, Sequence[str]]


class ElasticIpClient(Protocol):
    """The two EC2 calls this cleaner uses."""

    def describe_addresses(self) -> Mapping[str, Any]:
        """List the Elastic IP addresses of the client's region."""
        ...

    def release_address(self, *, AllocationId: str) -> Mapping[str, Any]:
        """Release one Elastic IP by allocation id."""
        ...


ClientFactory = Callable[[str], ElasticIpClient]
RegionLister = Callable[[], Sequence[str]]


def boto3_client(region: str) -> ElasticIpClient:
    """Default EC2 client factory."""
    client: ElasticIpClient = boto3.client(EC2_SERVICE_NAME, region_name=region)
    return client


@dataclass(frozen=True, slots=True)
class ElasticIpRuntime:
    """Injected collaborators of the cleaner: the SDK client factory and the region lister."""

    client_factory: ClientFactory = boto3_client
    list_regions: RegionLister = ec2_regions
