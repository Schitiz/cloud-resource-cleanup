# Copyright (c) Yugabyte, Inc.

"""`NIC`: the legacy class `crc.py` uses.

It keeps its constructor and attributes and runs the cleaner NIC by NIC, in the call order of the
original.
"""

import logging
from collections.abc import Sequence

from crc.azu import _logger
from crc.azu._base import Base
from crc.azu._common import log_delete_summary
from crc.azu.nic.cleaner import AzureNicCleaner, log_none_to_delete
from crc.service import Service


class NIC(Service):
    """
    This class provides an implementation of the Service class for managing NICs on Azure Cloud.
    By default, it cleans all NICs of the resource group that are not in use.

    Attributes: `nics_names_to_delete` (names deleted, or listed in a dry run), `base`,
    `dry_run`, `name_regex`, `exception_regex`. `get_deleted` and `delete_count` read the result.
    """

    def __init__(
        self,
        resource_group: str,
        dry_run: bool,
        name_regex: Sequence[str] | None,
        exception_regex: Sequence[str] | None,
    ) -> None:
        """
        Initializes the object with filter and exception tags to be used when searching for NICs.

        :param dry_run: When True the class only lists the NICs that match the filter and not the
                        exception names and performs no operation on them.
        :param name_regex: List containing filter regex.
        :param exception_regex: List containing exception names.
        """
        super().__init__()
        self.nics_names_to_delete: list[str] = []
        self.base = Base(resource_group)
        self.dry_run = dry_run
        self.name_regex = name_regex
        self.exception_regex = exception_regex

    @property
    def get_deleted(self) -> list[str]:
        """
        Returns the list of items in the nics_names_to_delete list.
        """
        return self.nics_names_to_delete

    @property
    def delete_count(self) -> int:
        """
        Returns the count of items in the nics_names_to_delete list.
        """
        count = len(self.nics_names_to_delete)
        logging.info(f"Count of items in nics_names_to_delete: {count}")
        return count

    def _cleaner(self) -> AzureNicCleaner:
        return AzureNicCleaner(
            self.base.get_network_client,
            self.base.resource_group,
            self.name_regex,
            self.exception_regex,
        )

    def delete(self) -> None:
        """
        Deletes NICs that match name_regex and do not match exception_regex.
        In dry_run mode it only lists the matching NICs and performs no operation on them.
        """
        cleaner = self._cleaner()
        if not cleaner.prepare():
            log_none_to_delete()
            return
        started = _logger.started()
        scanned = selected = 0
        for nic in cleaner.list_nics():
            scanned += 1
            candidate, _ = cleaner.decide(nic)
            if candidate is None:
                continue
            selected += 1
            if cleaner.attempt_delete(candidate.id, dry_run=self.dry_run) is None:
                self.nics_names_to_delete.append(candidate.id)
        _logger.region_done(self.base.resource_group, scanned, selected, started)

        log_delete_summary(
            "NICs", self.nics_names_to_delete, dry_run=self.dry_run, number_word="Number"
        )
