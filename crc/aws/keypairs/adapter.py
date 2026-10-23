# Copyright (c) Yugabyte, Inc.

"""Legacy `KeyPairs` adapter used by `crc.py`: runs the cleaner region by region, in the exact
call order of the original implementation. Delete this module with its callers."""

import logging

from crc.aws._common import DEFAULT_REGION, EC2_SERVICE_NAME, skip_region
from crc.aws.connectivity import CONNECTIVITY_ERRORS
from crc.core import age as core_age
from crc.service import Service

from .cleaner import SKIP_CONTEXT, KeyPairCleaner, log_summary
from .client import KeyPairRuntime


class KeyPairs(Service):
    """Legacy entry point used by `crc.py`: deletes key pairs that match the name regexes,
    skips the exception regexes and are older than `age`. In dry run it only lists them.

    Attributes: `deleted_keypairs` (names deleted, or listed in a dry run), `name_regex`,
    `exception_regex`, `age`, `dry_run`. `get_deleted` and `count` read the result.
    """

    service_name = EC2_SERVICE_NAME
    default_region_name = DEFAULT_REGION

    def __init__(
        self,
        dry_run: bool,
        name_regex: list[str] | None,
        exception_regex: list[str] | None,
        age: core_age.AgeSpec | int | None,
        runtime: KeyPairRuntime | None = None,
    ) -> None:
        super().__init__()
        self.deleted_keypairs: list[str] = []
        self.dry_run = dry_run
        self.name_regex = name_regex
        self.exception_regex = exception_regex
        self.age = age
        self._runtime = runtime or KeyPairRuntime()

    @property
    def get_deleted(self) -> list[str]:
        """Names of the key pairs deleted (listed in a dry run)."""
        return self.deleted_keypairs

    @property
    def count(self) -> int:
        """Number of key pairs deleted (listed in a dry run); logs the count."""
        count = len(self.deleted_keypairs)
        logging.info(f"count of items in deleted_keypairs: {count}")
        return count

    def delete(self) -> None:
        """Delete (or, in a dry run, only list) the matching key pairs of every region."""
        runtime = self._runtime
        cleaner = KeyPairCleaner(
            runtime.client_factory,
            runtime.list_regions,
            self.name_regex,
            self.exception_regex,
            self.age,
        )
        for region in runtime.list_regions():
            try:
                client = runtime.client_factory(region)
                region_plan = cleaner.plan_region(client, region, runtime.clock())
                cleaner.apply_region(
                    client, region_plan.candidates, self.deleted_keypairs, dry_run=self.dry_run
                )
            except CONNECTIVITY_ERRORS as e:
                skip_region(region, SKIP_CONTEXT, e)
        log_summary(self.deleted_keypairs, dry_run=self.dry_run)
