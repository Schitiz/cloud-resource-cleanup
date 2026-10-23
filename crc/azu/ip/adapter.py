# Copyright (c) Yugabyte, Inc.

"""`IP`: the legacy class `crc.py` uses.

It keeps its constructor and attributes and runs the cleaner IP by IP, in the call order of the
original.
"""

import logging

from crc.azu import _logger
from crc.azu._base import Base
from crc.azu._common import log_delete_summary
from crc.azu.ip.cleaner import AzureIpCleaner
from crc.azu.ip.client import TagSpec
from crc.service import Service


class IP(Service):
    """
    Class for managing public IP addresses in Azure.

    Attributes: `deleted_ips` (names deleted, or listed in a dry run), `base`, `dry_run`,
    `filter_tags`, `exception_tags`, `notags`. `get_deleted` and `count` read the result.
    """

    def __init__(
        self,
        resource_group: str,
        dry_run: bool,
        filter_tags: TagSpec | None,
        exception_tags: TagSpec | None,
        notags: TagSpec | None,
    ) -> None:
        """
        Initialize the IP class with filter and exception tags.
        :param dry_run: When True the class only lists the IP addresses that match the filter
        and exception tags and performs no operation on them.
        :param filter_tags: dict containing key-value pairs to filter IP addresses by
        :param exception_tags: dict containing key-value pairs to exclude IP addresses by
        :param notags: dict containing key-value pairs to skip IP addresses that carry all of them
        """
        super().__init__()
        self.deleted_ips: list[str] = []
        self.base = Base(resource_group)
        self.dry_run = dry_run
        self.filter_tags = filter_tags
        self.exception_tags = exception_tags
        self.notags = notags

    @property
    def get_deleted(self) -> list[str]:
        """
        Return the list of deleted IP addresses.
        """
        return self.deleted_ips

    @property
    def count(self) -> int:
        """
        Return the count of deleted IP addresses.
        """
        count = len(self.deleted_ips)
        logging.info(f"count of items in deleted_ips: {count}")
        return count

    def _cleaner(self) -> AzureIpCleaner:
        return AzureIpCleaner(
            self.base.get_network_client,
            self.base.resource_group,
            self.filter_tags,
            self.exception_tags,
            self.notags,
        )

    def delete(self) -> None:
        """
        Delete public IP addresses that match the filter and exception tags.
        """
        cleaner = self._cleaner()
        started = _logger.started()
        scanned = selected = 0
        for ip in cleaner.list_ips():
            scanned += 1
            candidate, _ = cleaner.decide(ip)
            if candidate is None:
                continue
            selected += 1
            if not self.dry_run:
                cleaner.delete_candidate(candidate)
            else:
                _logger.acted("would_delete", self.base.resource_group, candidate.id)
            self.deleted_ips.append(candidate.id)
        _logger.region_done(self.base.resource_group, scanned, selected, started)
        log_delete_summary("IPs", self.deleted_ips, dry_run=self.dry_run)
