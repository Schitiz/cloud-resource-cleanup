# Copyright (c) Yugabyte, Inc.

"""`Disk`, the legacy class `crc.py` uses; it keeps its constructor, attributes and result
shapes and runs `DiskCleaner` disk by disk, in the exact call order of the original
implementation."""

import datetime
import logging
from typing import ClassVar

from crc.core import age as core_age
from crc.gcp._common import TIME_FORMAT, Clock
from crc.gcp.disk_cleaner import DiskCleaner
from crc.gcp.disk_client import _SERVICE_NAME, _SERVICE_VERSION, ComputeDiskClient, GcpDiskClient
from crc.gcp.disk_settings import Deleted, DiskSettings, _log_summary
from crc.service import Service


class Disk(Service):
    """Legacy entry point used by `crc.py`: deletes unattached GCP disks (see `DiskCleaner`);
    in a dry run it only lists them. `age` is stored, never used; `notags` and `name_regex` are
    applied.

    Attributes: `service_name`, `service_version`, `time_format`, `default_disk_state`,
    `disk_names_to_delete` (a list of names, or with `slack_notify_users` a dict of owner to
    names), and the constructor arguments. `get_deleted` and `count` read the result.
    """

    service_name = _SERVICE_NAME
    service_version = _SERVICE_VERSION
    time_format = TIME_FORMAT
    default_disk_state: ClassVar[list[str]] = ["Unattached"]

    def __init__(  # noqa: PLR0913, PLR0917 - the eleven parameters are the public signature
        self,
        dry_run: bool,
        project_id: str,
        filter_labels: dict[str, list[str]],
        exception_labels: dict[str, list[str]],
        age: int,
        custom_age_tag_key: str,
        detach_age: core_age.AgeSpec | int,
        notags: dict[str, list[str]],
        name_regex: list[str],
        exception_regex: list[str],
        slack_notify_users: bool,
        slack_user_label: str,
        client: GcpDiskClient | None = None,
        clock: Clock = datetime.datetime.now,
    ) -> None:
        super().__init__()
        self.dry_run = dry_run
        self.project_id = project_id
        self.filter_labels = filter_labels
        self.exception_labels = exception_labels
        self.age = age
        self.custom_age_tag_key = custom_age_tag_key
        self.detach_age = detach_age
        self.notags = notags
        self.name_regex = name_regex
        self.exception_regex = exception_regex
        self.slack_notify_users = slack_notify_users
        self.slack_user_label = slack_user_label
        self._client: GcpDiskClient = client or ComputeDiskClient()
        self._clock = clock
        self.disk_names_to_delete: Deleted = {} if self.slack_notify_users else []

    @property
    def get_deleted(self) -> Deleted:
        """Disks deleted (listed in a dry run): names, or owner to names."""
        return self.disk_names_to_delete

    @property
    def count(self) -> int:
        """Entries of `disk_names_to_delete` (owners with `slack_notify_users`); logs it."""
        count = len(self.disk_names_to_delete)
        logging.info(f"count of items in disk_names_to_delete: {count}")
        return count

    def _cleaner(self) -> DiskCleaner:
        settings = DiskSettings(
            project_id=self.project_id,
            filter_labels=self.filter_labels,
            exception_labels=self.exception_labels,
            exception_regex=self.exception_regex,
            custom_age_tag_key=self.custom_age_tag_key,
            detach_age=self.detach_age,
            slack_notify_users=self.slack_notify_users,
            slack_user_label=self.slack_user_label,
            notags=self.notags,
            name_regex=self.name_regex,
        )
        return DiskCleaner(self._client, settings)

    def delete(self, disk_state: list[str] = default_disk_state) -> None:
        """Delete (or, in a dry run, only list) the matching disks of every zone, disk by disk.
        `disk_state` is accepted and ignored, as on main."""
        cleaner = self._cleaner()
        try:
            for zone_obj in cleaner.zones():
                zone = zone_obj["name"]
                for candidate in cleaner.plan_zone(zone, self._clock):
                    cleaner.apply_disk(
                        zone, candidate, self.disk_names_to_delete, dry_run=self.dry_run
                    )
            _log_summary(self.disk_names_to_delete, dry_run=self.dry_run)
        finally:
            self._client.close()
