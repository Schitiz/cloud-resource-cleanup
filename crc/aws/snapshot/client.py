# Copyright (c) Yugabyte, Inc.

"""Typed EC2 client Protocol, default factories and the injected runtime of the snapshot cleaner."""

import datetime
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import partial
from typing import Any, Protocol

import boto3

from crc.aws._common import EC2_SERVICE_NAME, ec2_regions


class SnapshotClient(Protocol):
    """The three EC2 calls this cleaner uses."""

    def describe_snapshots(self, *, OwnerIds: Sequence[str]) -> Mapping[str, Any]:
        """List the snapshots of the given owners in the client's region."""
        ...

    def describe_images(self, *, Owners: Sequence[str]) -> Mapping[str, Any]:
        """List the AMIs of the given owners in the client's region."""
        ...

    def delete_snapshot(self, *, SnapshotId: str) -> Mapping[str, Any]:
        """Delete one snapshot by id."""
        ...

ClientFactory = Callable[[str], SnapshotClient]
RegionLister = Callable[[], Sequence[str]]
Clock = Callable[[], datetime.datetime]


def boto3_client(region: str) -> SnapshotClient:
    """Default EC2 client factory."""
    client: SnapshotClient = boto3.client(EC2_SERVICE_NAME, region_name=region)
    return client


_UTC_CLOCK: Clock = partial(datetime.datetime.now, datetime.UTC)


@dataclass(frozen=True, slots=True)
class SnapshotRuntime:
    """Injected collaborators of `Snapshot`: the SDK client factory, the region lister and the
    clock that supplies `now` (the cleaner itself never reads the clock)."""

    client_factory: ClientFactory = boto3_client
    list_regions: RegionLister = ec2_regions
    clock: Clock = _UTC_CLOCK
