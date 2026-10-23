# Copyright (c) Yugabyte, Inc.

"""Legacy `ElasticIPs` adapter used by `crc.py`: runs the cleaner region by region, in the exact
call order of the original implementation. Delete this module with its callers."""

import logging
from collections.abc import Mapping, Sequence
from typing import Any

from crc.aws._common import DEFAULT_REGION, EC2_SERVICE_NAME, skip_region
from crc.aws.connectivity import CONNECTIVITY_ERRORS
from crc.service import Service

from .cleaner import SKIP_CONTEXT, ElasticIpCleaner, log_summary
from .client import ElasticIpRuntime, TagSpec


class ElasticIPs(Service):
    """Legacy entry point used by `crc.py`: releases unassociated Elastic IPs that match
    `filter_tags` and are not in `exception_tags`. In dry run it only lists them.

    Attributes: `deleted_ips` (public IPs released, or listed in a dry run), `filter_tags`,
    `exception_tags`, `notags`, `dry_run`. `get_deleted` and `count` read the result.
    """

    service_name = EC2_SERVICE_NAME
    default_region_name = DEFAULT_REGION

    def __init__(
        self,
        dry_run: bool,
        filter_tags: TagSpec | None,
        exception_tags: TagSpec | None,
        notags: TagSpec | None,
        runtime: ElasticIpRuntime | None = None,
    ) -> None:
        super().__init__()
        self.deleted_ips: list[str] = []
        self.dry_run = dry_run
        self.filter_tags = filter_tags
        self.exception_tags = exception_tags
        self.notags = notags
        self._runtime = runtime or ElasticIpRuntime()

    @property
    def get_deleted(self) -> list[str]:
        """Public IPs released (listed in a dry run)."""
        return self.deleted_ips

    @property
    def count(self) -> int:
        """Number of Elastic IPs released (listed in a dry run); logs the count."""
        count = len(self.deleted_ips)
        logging.info(f"count of items in deleted_ips: {count}")
        return count

    def _cleaner(self) -> ElasticIpCleaner:
        runtime = self._runtime
        return ElasticIpCleaner(
            runtime.client_factory,
            runtime.list_regions,
            self.filter_tags,
            self.exception_tags,
            self.notags,
        )

    def _should_skip_instance(self, tags: Sequence[Mapping[str, Any]]) -> bool:
        return self._cleaner().should_skip(tags)

    def delete(self) -> None:
        """Release (or, in a dry run, only list) the matching Elastic IPs of every region."""
        runtime = self._runtime
        cleaner = self._cleaner()
        for region in runtime.list_regions():
            try:
                client = runtime.client_factory(region)
                region_plan = cleaner.plan_region(client, region)
                released = cleaner.apply_region(
                    client, region_plan.candidates, dry_run=self.dry_run
                )
                self.deleted_ips.extend(released)
            except CONNECTIVITY_ERRORS as e:
                skip_region(region, SKIP_CONTEXT, e)
        log_summary(self.deleted_ips, dry_run=self.dry_run)
