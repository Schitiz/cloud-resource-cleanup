# Copyright (c) Yugabyte, Inc.

"""Typed EC2 client Protocol, default factories and the injected runtime of the key pair cleaner."""

import datetime
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import boto3

from crc.aws._common import EC2_SERVICE_NAME, ec2_regions


class KeyPairClient(Protocol):
    """The two EC2 calls this cleaner uses."""

    def describe_key_pairs(self) -> Mapping[str, Any]:
        """List the key pairs of the client's region."""
        ...

    def delete_key_pair(self, *, KeyName: str) -> Mapping[str, Any]:
        """Delete one key pair by name."""
        ...


ClientFactory = Callable[[str], KeyPairClient]
RegionLister = Callable[[], Sequence[str]]
Clock = Callable[[], datetime.datetime]


def boto3_client(region: str) -> KeyPairClient:
    """Default EC2 client factory."""
    client: KeyPairClient = boto3.client(EC2_SERVICE_NAME, region_name=region)
    return client


@dataclass(frozen=True, slots=True)
class KeyPairRuntime:
    """Injected collaborators of `KeyPairs`: the SDK client factory, the region lister and the
    clock that supplies `now` (the cleaner itself never reads the clock)."""

    client_factory: ClientFactory = boto3_client
    list_regions: RegionLister = ec2_regions
    clock: Clock = datetime.datetime.now
