# Copyright (c) Yugabyte, Inc.

"""`VM`, the legacy class `crc.py` uses; it keeps its constructor, attributes and result shapes
and runs `VmCleaner` instance by instance, in the exact call order of the original
implementation."""

import datetime
import logging
from collections.abc import Sequence
from typing import ClassVar

from crc.core.cleaner import Operation
from crc.gcp._common import TIME_FORMAT, Clock
from crc.gcp.vm_cleaner import VmCleaner
from crc.gcp.vm_client import _SERVICE_NAME, _SERVICE_VERSION, ComputeVmClient, GcpVmClient
from crc.gcp.vm_settings import VmSettings, _log_summary
from crc.service import Service


class VM(Service):
    """Legacy entry point used by `crc.py`: deletes (`delete`) or stops (`stop`) GCP instances
    (see `VmCleaner`); in a dry run it only lists them.

    Attributes: `service_name`, `service_version`, `default_instance_state`, `time_format`,
    `instance_names_to_delete`, `instance_names_to_stop` (lists of names, accumulated over
    calls) and the constructor arguments. `get_deleted`, `delete_count`, `get_stopped` and
    `stopped_count` read the results.
    """

    service_name = _SERVICE_NAME
    service_version = _SERVICE_VERSION
    default_instance_state: ClassVar[list[str]] = ["RUNNING"]
    time_format = TIME_FORMAT

    def __init__(  # noqa: PLR0913, PLR0917 - the seven parameters are the public signature
        self,
        dry_run: bool,
        project_id: str,
        filter_labels: dict[str, list[str]],
        exception_labels: dict[str, list[str]],
        age: int,
        custom_age_tag_key: str,
        notags: dict[str, list[str]],
        client: GcpVmClient | None = None,
        clock: Clock = datetime.datetime.now,
    ) -> None:
        super().__init__()
        self.instance_names_to_delete: list[str] = []
        self.instance_names_to_stop: list[str] = []
        self.dry_run = dry_run
        self.project_id = project_id
        self.filter_labels = filter_labels
        self.exception_labels = exception_labels
        self.age = age
        self.custom_age_tag_key = custom_age_tag_key
        self.notags = notags
        self._client: GcpVmClient = client or ComputeVmClient()
        self._clock = clock

    @property
    def get_deleted(self) -> list[str]:
        """Instances deleted (listed in a dry run)."""
        return self.instance_names_to_delete

    @property
    def delete_count(self) -> int:
        """Number of entries of `instance_names_to_delete`; logs the count."""
        count = len(self.instance_names_to_delete)
        logging.info(f"count of items in instance_names_to_delete: {count}")
        return count

    @property
    def get_stopped(self) -> list[str]:
        """Instances stopped (listed in a dry run)."""
        return self.instance_names_to_stop

    @property
    def stopped_count(self) -> int:
        """Number of entries of `instance_names_to_stop`; logs the count."""
        count = len(self.instance_names_to_stop)
        logging.info(f"count of items in instance_names_to_stop: {count}")
        return count

    def _perform_operation(self, operation: Operation, instance_state: Sequence[str]) -> None:
        settings = VmSettings(
            project_id=self.project_id,
            filter_labels=self.filter_labels,
            exception_labels=self.exception_labels,
            notags=self.notags,
            age=self.age,
            custom_age_tag_key=self.custom_age_tag_key,
            instance_state=instance_state,
        )
        cleaner = VmCleaner(self._client, settings)
        recorded = (
            self.instance_names_to_delete
            if operation is Operation.DELETE
            else self.instance_names_to_stop
        )
        for zone_obj in cleaner.zones():
            zone = zone_obj["name"]
            for candidate in cleaner.plan_zone(zone, self._clock):
                cleaner.apply_instance(candidate, operation, recorded, dry_run=self.dry_run)
        _log_summary(
            operation,
            self.instance_names_to_delete,
            self.instance_names_to_stop,
            dry_run=self.dry_run,
        )

    def delete(self, instance_state: list[str] = default_instance_state) -> None:
        """Delete (or, in a dry run, only list) the matching instances of every zone,
        instance by instance."""
        self._perform_operation(Operation.DELETE, instance_state)

    def stop(self) -> None:
        """Stop (or, in a dry run, only list) the matching instances of every zone."""
        self._perform_operation(Operation.STOP, self.default_instance_state)
