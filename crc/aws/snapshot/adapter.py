# Copyright (c) Yugabyte, Inc.

"""Legacy `Snapshot` adapter used by `crc.py`: runs the cleaner region by region, snapshot by
snapshot, in the exact call order of the original implementation. Delete this module with its
callers."""

from typing import Any

from crc.aws import _regionlog
from crc.aws._common import EC2_SERVICE_NAME, skip_region
from crc.aws.connectivity import CONNECTIVITY_ERRORS
from crc.core.cleaner import Candidate
from crc.service import Service

from .cleaner import SKIP_CONTEXT, SnapshotCleaner, skip_failed_region
from .client import SnapshotClient, SnapshotRuntime
from .protection import is_protected, used_by_amis


class Snapshot(Service):
    """Legacy entry point used by `crc.py`: deletes snapshots at least `age_days` old that
    have no exception tag and are not used by an AMI. In dry run it only lists them.

    Attributes: `deleted_snapshots` (ids deleted, or listed in a dry run), `dry_run`,
    `age_days`, `exception_tags`. `get_deleted` and `delete_count` read the result.
    """

    service_name = EC2_SERVICE_NAME

    def __init__(
        self,
        dry_run: bool,
        age_days: Any,
        exception_tags: Any,
        runtime: SnapshotRuntime | None = None,
    ) -> None:
        super().__init__()
        self.dry_run = dry_run
        self.age_days = age_days
        self.exception_tags = exception_tags
        self.deleted_snapshots: list[str] = []
        self._runtime = runtime or SnapshotRuntime()

    @property
    def get_deleted(self) -> list[str]:
        """Ids of the snapshots deleted (listed in a dry run)."""
        return self.deleted_snapshots

    @property
    def delete_count(self) -> int:
        """Number of snapshots deleted (listed in a dry run)."""
        return len(self.deleted_snapshots)

    def _cleaner(self) -> SnapshotCleaner:
        runtime = self._runtime
        return SnapshotCleaner(
            runtime.client_factory, runtime.list_regions, self.age_days, self.exception_tags
        )

    def _is_protected(self, tags: Any, snap_id: str) -> bool:
        return is_protected(tags, snap_id, self.exception_tags)

    def _get_snapshots_used_by_amis(self, ec2: SnapshotClient) -> set[str]:
        return used_by_amis(ec2)

    def delete(self) -> None:
        """Delete (or, in a dry run, only list) the matching snapshots of every region."""
        runtime = self._runtime
        cleaner = self._cleaner()
        now = runtime.clock()
        cleaner.check_age(now)
        for region in runtime.list_regions():
            started = _regionlog.start()
            try:
                client = runtime.client_factory(region)
                scanned = selected = 0
                for decision in cleaner.iter_region(client, region, now):
                    scanned += 1
                    if not isinstance(decision, Candidate):
                        continue
                    selected += 1
                    failure = cleaner.delete_one(
                        client, decision.id, dry_run=self.dry_run, region=region
                    )
                    if failure is None:
                        self.deleted_snapshots.append(decision.id)
                _regionlog.region_done(region, scanned, selected, started)
            except CONNECTIVITY_ERRORS as e:
                skip_region(region, SKIP_CONTEXT, e)
            except Exception as e:
                skip_failed_region(region, e)
