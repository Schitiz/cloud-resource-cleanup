# Copyright (c) Yugabyte, Inc.

"""`IP`, the legacy class `crc.py` uses; it keeps its constructor and attributes and runs
`IpCleaner` region by region, in the exact call order of the original implementation."""

import logging
from collections.abc import Sequence

from crc.gcp.ip_cleaner import _RESERVED, IpCleaner, _log_summary
from crc.gcp.ip_client import ComputeIpClient, GcpIpClient
from crc.service import Service


class IP(Service):
    """Legacy entry point used by `crc.py`: deletes RESERVED GCP addresses whose name contains
    a `filter_regex` entry and does not contain an `exception_regex` entry. In dry run it only
    lists them.

    Attributes: `default_state` ("RESERVED"), `deleted_ips` (names deleted, or listed in a dry
    run), `dry_run`, `project_id`, `filter_regex`, `exception_regex`. `get_deleted` and `count`
    read the result.
    """

    default_state = _RESERVED

    def __init__(
        self,
        dry_run: bool,
        project_id: str,
        filter_regex: Sequence[str] | None,
        exception_regex: Sequence[str] | None,
        client: GcpIpClient | None = None,
    ) -> None:
        super().__init__()
        self.deleted_ips: list[str] = []
        self.dry_run = dry_run
        self.project_id = project_id
        self.filter_regex = filter_regex
        self.exception_regex = exception_regex
        self._client: GcpIpClient = client or ComputeIpClient()

    @property
    def get_deleted(self) -> list[str]:
        """Names of the addresses deleted (listed in a dry run)."""
        return self.deleted_ips

    @property
    def count(self) -> int:
        """Number of addresses deleted (listed in a dry run); logs the count."""
        count = len(self.deleted_ips)
        logging.info(f"count of items in deleted_ips: {count}")
        return count

    def _cleaner(self) -> IpCleaner:
        return IpCleaner(
            self._client,
            self.project_id,
            self.filter_regex,
            self.exception_regex,
            self.default_state,
        )

    def delete(self) -> None:
        """Delete (or, in a dry run, only list) the matching addresses of every region."""
        cleaner = self._cleaner()
        for region in cleaner.regions():
            region_plan = cleaner.plan_region(region)
            deleted = cleaner.apply_region(region, region_plan.candidates, dry_run=self.dry_run)
            self.deleted_ips.extend(deleted)
        _log_summary(self.deleted_ips, dry_run=self.dry_run)
