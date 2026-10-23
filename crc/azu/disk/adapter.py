# Copyright (c) Yugabyte, Inc.

"""`Disk`: the legacy class `crc.py` uses.

It keeps its constructor and attributes and runs the cleaner disk by disk, in the exact call order
of the original (listing is lazy, so paging and deletes interleave).
"""

import datetime
import logging
from typing import ClassVar

from crc.azu import _logger
from crc.azu._base import Base
from crc.azu._common import log_delete_summary
from crc.azu.disk.cleaner import AzureDiskCleaner, DiskSettings
from crc.azu.disk.client import AgeSpec, Clock, TagSpec
from crc.service import Service


class Disk(Service):
    """
    A class for managing Disks on Azure.

    Attributes: `disks_names_to_delete` (names deleted, or listed in a dry run), `base`,
    `dry_run`, `filter_tags`, `exception_tags`, `age`, `custom_age_tag_key`, `notags`, `clock`.
    `get_deleted` and `count` read the result.
    """

    default_disk_state: ClassVar[list[str]] = ["Unattached"]
    """The default_disk_state variable specifies the default state of disks when querying."""

    def __init__(  # noqa: PLR0913, PLR0917 - the seven parameters are the public signature
        self,
        resource_group: str,
        dry_run: bool,
        filter_tags: TagSpec | None,
        exception_tags: TagSpec | None,
        age: AgeSpec | None,
        custom_age_tag_key: str | None,
        notags: TagSpec | None,
    ) -> None:
        """
        Initialize the Disk management class.

        :param dry_run: When True the class only lists the disks that match the filter and
        exception tags and performs no operation on them.
        :param filter_tags: A dictionary of tags to filter disks by.
        :param exception_tags: A dictionary of tags to exclude disks by.
        :param age: A dictionary specifying the age threshold for deleting disks.
        :param custom_age_tag_key: Tag name to overwrite the age condition.
        :param notags: A dictionary of tags to filter resources that do not have the specified tags.
        """
        super().__init__()
        self.disks_names_to_delete: list[str] = []
        self.base = Base(resource_group)
        self.dry_run = dry_run
        self.filter_tags = filter_tags
        self.exception_tags = exception_tags
        self.age = age
        self.custom_age_tag_key = custom_age_tag_key
        self.notags = notags
        self.clock: Clock = datetime.datetime.now

    @property
    def get_deleted(self) -> list[str]:
        """
        Returns the list of items in the disks_names_to_delete list (read-only property).
        """
        return self.disks_names_to_delete

    @property
    def count(self) -> int:
        """
        Returns the count of items in the disks_names_to_delete list (read-only property).
        """
        count = len(self.disks_names_to_delete)
        logging.info(f"count of items in disks_names_to_delete: {count}")
        return count

    def _cleaner(self) -> AzureDiskCleaner:
        settings = DiskSettings(
            filter_tags=self.filter_tags,
            exception_tags=self.exception_tags,
            notags=self.notags,
            age=self.age,
            custom_age_tag_key=self.custom_age_tag_key,
            disk_states=self.default_disk_state,
        )
        return AzureDiskCleaner(self.base.get_compute_client, self.base.resource_group, settings)

    def delete(self) -> None:
        """
        Deletes disks that match filter_tags, do not match exception_tags or notags, and are
        older than the age. In dry_run mode it only lists the matching disks.
        """
        cleaner = self._cleaner()
        started = _logger.started()
        scanned = selected = 0
        for disk in cleaner.list_disks():
            scanned += 1
            candidate, _ = cleaner.decide(disk, self.clock())
            if candidate is None:
                continue
            selected += 1
            if cleaner.delete_disk(candidate.id, dry_run=self.dry_run) is None:
                self.disks_names_to_delete.append(candidate.id)
        _logger.region_done(self.base.resource_group, scanned, selected, started)
        log_delete_summary("Disks", self.disks_names_to_delete, dry_run=self.dry_run)
