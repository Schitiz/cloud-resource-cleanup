# Copyright (c) Yugabyte, Inc.

"""Legacy `Kms` adapter used by `crc.py`: runs the cleaner in the exact call order of the
original implementation. Delete this module with its callers."""

from collections.abc import Mapping, Sequence
from typing import Any

from crc.aws._common import DEFAULT_REGION
from crc.core import age as core_age
from crc.service import Service

from .cleaner import KmsCleaner, log_summary, log_would_delete
from .client import SERVICE_NAME, KmsRuntime
from .settings import KmsSettings
from .tags import TagSpec


class Kms(Service):
    """Legacy entry point used by `crc.py`: schedules deletion of the matching KMS keys. In dry
    run it only lists them.

    Attributes: `kms_keys_to_delete` (key ids scheduled, or listed in a dry run, accumulated over
    calls), the constructor arguments, `get_deleted` and the `delete()` method.
    """

    service_name = SERVICE_NAME
    default_region_name = DEFAULT_REGION

    def __init__(  # noqa: PLR0913, PLR0917 - the eight parameters are the public signature
        self,
        dry_run: bool,
        filter_tags: TagSpec | None,
        exception_tags: TagSpec | None,
        kms_key_descriptiom: str,
        kms_user: str,
        kms_pending_window: int,
        age: core_age.AgeSpec,
        custom_age_tag_key: str,
        runtime: KmsRuntime | None = None,
    ) -> None:
        super().__init__()
        self.kms_keys_to_delete: list[str] = []
        self.dry_run = dry_run
        self.filter_tags = filter_tags
        self.exception_tags = exception_tags
        self.kms_key_description = kms_key_descriptiom
        self.kms_user = kms_user
        self.kms_pending_window = kms_pending_window
        self.age = age
        self.custom_age_tag_key = custom_age_tag_key
        self._runtime = runtime or KmsRuntime()

    @property
    def get_deleted(self) -> list[str]:
        """Key ids scheduled for deletion (listed in a dry run)."""
        return self.kms_keys_to_delete

    def _cleaner(self) -> KmsCleaner:
        return KmsCleaner(
            self._runtime.client_factory,
            KmsSettings(
                self.filter_tags,
                self.exception_tags,
                self.kms_key_description,
                self.kms_user,
                self.kms_pending_window,
                self.age,
                self.custom_age_tag_key,
            ),
        )

    def _should_skip_kms(self, tags: Sequence[Mapping[str, Any]]) -> bool:
        return self._cleaner().should_skip(tags)

    def delete(self) -> None:
        """Schedule (or, in a dry run, only list) the matching keys."""
        cleaner = self._cleaner()
        opened = cleaner.connect_and_list()
        if opened is None:
            return
        client, keys = opened
        plan = cleaner.plan_keys(client, keys, self._runtime.clock)
        active = [c.id for c in plan.candidates]
        if self.dry_run:
            log_would_delete(active)
        else:
            cleaner.schedule(client, active)
        self.kms_keys_to_delete.extend(active)
        log_summary(self.kms_keys_to_delete, dry_run=self.dry_run)
