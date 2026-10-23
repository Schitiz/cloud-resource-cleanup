# Copyright (c) Yugabyte, Inc.

"""Legacy `VPC` adapter of the AWS VPC cleaner (`crc.aws.vpc.cleaner.VpcCleaner`), the class
`crc.py` uses. It keeps its constructor and attributes and drives the cleaner region by region,
VPC by VPC, in the exact call order of the original implementation."""

import logging
from collections.abc import Iterable, Mapping
from typing import Any

from crc.aws import _regionlog
from crc.aws.connectivity import CONNECTIVITY_ERRORS
from crc.aws.vpc.cleaner import VpcCleaner
from crc.aws.vpc.client import Vpc
from crc.aws.vpc.runtime import (
    DEFAULT_REGION,
    SERVICE_NAME,
    TagSpec,
    VpcRuntime,
    log_summary,
    skip_region,
)
from crc.core import logger
from crc.service import Service


class VPC(Service):
    """Legacy entry point used by `crc.py`: deletes the VPCs that match `filter_tags` (EC2 tag
    filter) and are not protected by `exception_tags` / `notags`. In dry run it only lists them.

    Attributes: `vpc_ids_to_delete` (ids deleted, or listed in a dry run), `filter_tags`,
    `exception_tags`, `notags`, `dry_run`. `get_deleted` and `delete_count` read the result.
    """

    service_name = SERVICE_NAME
    default_region_name = DEFAULT_REGION

    def __init__(
        self,
        dry_run: bool,
        filter_tags: TagSpec | None,
        exception_tags: TagSpec | None,
        notags: TagSpec | None,
        runtime: VpcRuntime | None = None,
    ) -> None:
        super().__init__()
        self.vpc_ids_to_delete: list[str] = []
        self.dry_run = dry_run
        self.filter_tags = filter_tags
        self.exception_tags = exception_tags
        self.notags = notags
        self._runtime = runtime or VpcRuntime()

    @property
    def get_deleted(self) -> list[str]:
        """Ids of the VPCs deleted (listed in a dry run)."""
        return self.vpc_ids_to_delete

    @property
    def delete_count(self) -> int:
        """Number of VPCs deleted (listed in a dry run); logs the count."""
        count = len(self.vpc_ids_to_delete)
        logging.info(f"count of items in vpc_ids_to_delete: {count}")
        return count

    def _cleaner(self) -> VpcCleaner:
        runtime = self._runtime
        cleaner = VpcCleaner(
            runtime.client_factory,
            runtime.resource_factory,
            runtime.list_regions,
            self.filter_tags,
            self.exception_tags,
            self.notags,
        )
        cleaner.sleep = runtime.sleep
        return cleaner

    def _get_filter(self) -> list[dict[str, Any]]:
        return self._cleaner().build_filter()

    def _should_skip_vpc(self, tags: Iterable[Mapping[str, str]]) -> bool:
        return self._cleaner().should_skip(tags)

    def get_vpc_ids(self, vpcs: Iterable[Vpc]) -> list[str]:
        """Ids of the given boto3 VPC objects."""
        return [vpc.id for vpc in vpcs]

    def delete(self) -> None:
        """Delete (or, in a dry run, only list) the matching VPCs of every region."""
        runtime = self._runtime
        cleaner = self._cleaner()
        cleaner.require_filter_tags()
        vpc_filter = cleaner.build_filter()
        run = logger.current()
        for region in runtime.list_regions():
            started = _regionlog.start()
            try:
                client = runtime.client_factory(region)
                ec2 = runtime.resource_factory(region)
                listed = cleaner.list_vpcs(ec2, vpc_filter)
                vpcs = [vpc for vpc in listed if not self._skip_default(cleaner, vpc)]
                self.vpc_ids_to_delete.extend(self.get_vpc_ids(vpcs))
                if self.dry_run:
                    for vpc in vpcs:
                        run.action("would_delete", region, vpc.id)
                    _regionlog.region_done(region, len(listed), len(vpcs), started)
                    continue
                selected = 0
                for vpc in vpcs:
                    if cleaner.is_protected(vpc):
                        run.skip("protected")
                        continue
                    selected += 1
                    if not cleaner.delete_vpc(client, ec2, vpc, region=region):
                        self.vpc_ids_to_delete.remove(vpc.id)
                _regionlog.region_done(region, len(listed), selected, started)
            except CONNECTIVITY_ERRORS as e:
                skip_region(region, e)
        log_summary(self.vpc_ids_to_delete, dry_run=self.dry_run)

    @staticmethod
    def _skip_default(cleaner: VpcCleaner, vpc: Vpc) -> bool:
        if not cleaner.is_default(vpc):
            return False
        logger.current().skip("default_vpc")
        return True
