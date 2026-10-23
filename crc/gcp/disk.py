# Copyright (c) Yugabyte, Inc.

"""GCP disk cleaner.

`DiskCleaner` implements the `crc.core.cleaner.Cleaner` contract: `plan()` lists the zones of
the project and their disks and filters them, `apply()` deletes the planned disks.
`Disk` is the legacy class `crc.py` uses; it keeps its constructor, attributes and result
shapes and runs the cleaner disk by disk, in the exact call order of the original implementation.
"""

import datetime
import logging
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import ClassVar, cast

from crc.core import age as core_age
from crc.core import logger, policy
from crc.core.cleaner import Candidate, Cleaner, Operation, Plan, Result, RunContext
from crc.core.registry import register
from crc.gcp._scan import ZoneScan, log_action
from crc.gcp.disk_client import ComputeDiskClient as ComputeDiskClient
from crc.gcp.disk_client import DiskView as DiskView
from crc.gcp.disk_client import GcpDiskClient as GcpDiskClient
from crc.gcp.spot_vm.client import GcpSpotClient
from crc.gcp.spot_vm.operations import wait_operation
from crc.gcp.spot_vm.settings import DEFAULT_POLL_INTERVAL_SEC, DEFAULT_WAIT_SEC, SpotSettings
from crc.service import Service

_SERVICE_NAME = "compute"
_SERVICE_VERSION = "v1"
_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f%z"
_NOT_TAGGED = "not_tagged"

Clock = Callable[[], datetime.datetime]
Deleted = list[str] | dict[str, list[str]]


@dataclass(frozen=True, slots=True)
class DiskSettings:
    """Filters and options of one run: only the fields `main` reads."""

    project_id: str
    filter_labels: Mapping[str, Sequence[str]] | None
    exception_labels: Mapping[str, Sequence[str]] | None
    exception_regex: Sequence[str] | None
    custom_age_tag_key: str
    detach_age: core_age.AgeSpec | int
    slack_notify_users: bool = False
    slack_user_label: str = ""
    notags: Mapping[str, Sequence[str]] | None = None
    name_regex: Sequence[str] | None = None
    wait_sec: float = DEFAULT_WAIT_SEC
    poll_sec: float = DEFAULT_POLL_INTERVAL_SEC


def _name_patterns(name_regex: Sequence[str] | None) -> tuple[str, ...]:
    """The `name_regex` patterns; a bad value raises `ValueError` before any call is made."""
    if name_regex is None:
        return ()
    if not isinstance(name_regex, list | tuple) or not all(isinstance(p, str) for p in name_regex):
        raise ValueError(f"Invalid name_regex {name_regex!r}: expected a list of patterns")
    if not name_regex:
        return ()
    patterns = tuple(name_regex)
    policy.compile_patterns(patterns, "name_regex")
    return patterns


def _frozen_groups(groups: dict[str, list[str]] | None) -> dict[str, tuple[str, ...]] | None:
    if groups is None:
        return None
    return {owner: tuple(names) for owner, names in groups.items()}


def _record(deleted: Deleted, settings: DiskSettings, name: str, labels: Mapping[str, str]) -> None:
    """Record a deleted (or listed) disk by name, or by `slack_user_label` (`not_tagged`)."""
    if not settings.slack_notify_users:
        cast(list[str], deleted).append(name)
        return
    groups = cast(dict[str, list[str]], deleted)
    label = settings.slack_user_label
    owner = labels.get(label, _NOT_TAGGED)
    groups.setdefault(owner, []).append(name)


def _log_summary(deleted: Deleted, *, dry_run: bool) -> None:
    if not deleted:
        logging.warning("No GCP disk to delete.")
    if not dry_run:
        logging.warning(f"number of GCP disks deleted: {len(deleted)}")
        logging.warning(f"List of GCP disk deleted: {deleted}")
    else:
        logging.warning(
            f"List of GCP disk (Total: {len(deleted)}) which will be deleted: {deleted}"
        )


class DiskCleaner:
    """Deletes unattached disks with a `last_detach_timestamp` that are at least `detach_age`
    (or the custom age label) old, match `filter_labels` (any key; empty matches all) and
    `name_regex` (`re.search` any; empty matches all) and are not excluded by `exception_regex`
    (`re.match` on the name), `exception_labels` (any key) or `notags` (all keys, as the GCP VM
    cleaner). Applies to every zone of the project. An error on one disk or one zone listing is
    recorded and the run goes on."""

    cloud = "gcp"
    kind = "disk"

    def __init__(self, client: GcpDiskClient, settings: DiskSettings) -> None:
        self._client = client
        self._settings = settings
        self._name_patterns = _name_patterns(settings.name_regex)

    def supports(self, operation: Operation) -> bool:
        return operation is Operation.DELETE

    def zones(self) -> Sequence[Mapping[str, str]]:
        """Zones of the project (read-only call)."""
        return self._client.list_zones(self._settings.project_id)

    def plan(self, context: RunContext) -> Plan:
        """List every zone and filter. Makes no mutating call."""
        settings = self._settings
        candidates: list[Candidate] = []
        try:
            for zone_obj in self.zones():
                zone = zone_obj["name"]
                candidates.extend(self.plan_zone(zone, lambda: context.now))
        finally:
            self._client.close()
        by_owner: dict[str, list[str]] | None = {} if settings.slack_notify_users else None
        deleted: Deleted = by_owner if by_owner is not None else []
        for candidate in candidates:
            _record(deleted, settings, candidate.id, candidate.tags)
        if context.dry_run:
            for candidate in candidates:
                log_action("delete", candidate, dry_run=True)
            _log_summary(deleted, dry_run=True)
        return Plan(candidates=tuple(candidates), by_owner=_frozen_groups(by_owner))

    def apply(self, plan: Plan, context: RunContext) -> Result:
        """Delete the planned disks one by one; a failed delete is logged and skipped."""
        settings = self._settings
        by_owner: dict[str, list[str]] | None = {} if settings.slack_notify_users else None
        deleted: Deleted = by_owner if by_owner is not None else []
        succeeded: list[str] = []
        try:
            succeeded.extend(
                candidate.id
                for candidate in plan.candidates
                if self.apply_disk(candidate.region, candidate, deleted, dry_run=context.dry_run)
            )
            _log_summary(deleted, dry_run=context.dry_run)
        finally:
            self._client.close()
        return Result(succeeded=tuple(succeeded), by_owner=_frozen_groups(by_owner))

    def plan_zone(self, zone: str, clock: Clock) -> Iterator[Candidate]:
        """List one zone lazily and yield the disks to delete, in the order of `main`: attached,
        exception regex and labels, filter labels, detach timestamp, age; then the REGION line."""
        scan = ZoneScan(zone)
        try:
            for disk in self._client.list_disks(self._settings.project_id, zone):
                scan.scanned += 1
                candidate = self._evaluate(disk, zone, clock)
                if candidate is None:
                    continue
                scan.selected += 1
                yield candidate
        except Exception as e:
            logging.error(f"Error occurred while listing disks of zone {zone}: {e}")
            logger.current().fail(zone, f"zone {zone}", e)
        scan.finish()

    def _evaluate(self, disk: DiskView, zone: str, clock: Clock) -> Candidate | None:
        """The candidate for a disk to delete; `None` when it is kept, skipped, or an error
        while evaluating it was recorded (the disk is kept)."""
        try:
            reason = self._reject(disk, clock)
            if reason is not None:
                logger.current().skip(reason)
                return None
            return Candidate(
                id=disk.name, name=disk.name, region=zone, tags=policy.normalize_tags(disk.labels)
            )
        except Exception as e:
            name = str(getattr(disk, "name", ""))
            logging.error(f"Error occurred while evaluating disk {name}: {e}")
            logger.current().fail(zone, name, e)
            return None

    def _reject(self, disk: DiskView, clock: Clock) -> str | None:
        if disk.users:
            return "attached"
        if reason := self._exception_reason(disk):
            return reason
        if self._name_patterns and not policy.name_regex_search_matches(
            self._name_patterns, disk.name
        ):
            return "name_regex_mismatch"
        if not self._has_matching_filter_label(disk):
            return "filter_mismatch"
        if not disk.last_detach_timestamp:
            return "never_detached"
        return None if self._older_than_detach_age(disk, clock) else "too_young"

    def apply_disk(
        self, zone: str, candidate: Candidate, deleted: Deleted, *, dry_run: bool
    ) -> bool:
        """Delete one disk (nothing in a dry run) and record it; an error is logged and the
        disk is not recorded. Returns whether it was recorded."""
        try:
            if not dry_run:
                operation = self._client.delete_disk(self._settings.project_id, zone, candidate.id)
                logging.info(f"Deleting disk {candidate.id}")
                if not self._delete_completed(zone, candidate, operation):
                    return False
            _record(deleted, self._settings, candidate.id, candidate.tags)
        except Exception as e:
            logging.error(f"Error occurred while deleting disk {candidate.id}: {e}")
            logger.current().fail(zone, candidate.id, e)
            return False
        log_action("delete", candidate, dry_run=dry_run)
        return True

    def _delete_completed(self, zone: str, candidate: Candidate, operation: object) -> bool:
        """Wait for the zone operation of a disk delete to be DONE without an error, as the GCP
        spot cleaner does; a missing operation name, an operation error or a timeout is logged
        and recorded as a failure."""
        settings = self._settings
        name = operation.get("name") if isinstance(operation, Mapping) else None
        spot = SpotSettings(
            project_id=settings.project_id,
            filter_labels={},
            exception_labels={},
            notags={},
            age={},
            custom_age_tag_key=None,
            wait_sec=settings.wait_sec,
            poll_sec=settings.poll_sec,
        )
        if name and wait_operation(cast(GcpSpotClient, self._client), spot, "zone", zone, name):
            return True
        logging.error(f"Disk delete failed or incomplete for {candidate.id}")
        logger.current().fail(zone, candidate.id, "disk delete failed or incomplete")
        return False

    def _exception_reason(self, disk: DiskView) -> str | None:
        settings = self._settings
        if settings.exception_regex:
            patterns = [f"{p}" for p in settings.exception_regex]
            if policy.exception_regex_match_matches(patterns, disk.name):
                return "exception_regex"
        if settings.exception_labels or settings.notags:
            tags = policy.normalize_tags(disk.labels)
            if policy.should_skip_by_tags(
                tags, settings.exception_labels or {}, settings.notags or {}
            ):
                return "exception_tag"
        return None

    def _has_matching_filter_label(self, disk: DiskView) -> bool:
        if not self._settings.filter_labels:
            return True
        tags = policy.normalize_tags(disk.labels)
        return policy.filter_tags_any_key(tags, self._settings.filter_labels)

    def _older_than_detach_age(self, disk: DiskView, clock: Clock) -> bool:
        detached = datetime.datetime.strptime(disk.last_detach_timestamp, _TIME_FORMAT)
        now = clock().astimezone(detached.tzinfo)
        logging.debug(disk.labels)
        settings = self._settings
        retention_age = core_age.get_retention_age(
            cast(dict[str, str], disk.labels), settings.custom_age_tag_key
        )
        if retention_age:
            logging.info(f"Updating age for disk: {disk.name}")
        # An int is a number of days, which `is_old` accepts.
        default_age = cast(core_age.AgeSpec, settings.detach_age)
        return core_age.is_old(policy.effective_age(retention_age, default_age), now, detached)


@register("gcp", "disk")
def build_disk_cleaner(context: RunContext) -> Cleaner:
    """Registry factory. Options: `project_id`, `filter_tags` (labels), `exception_tags`
    (labels), `exception_regex`, `notags`, `name_regex`, `custom_age_tag_key`, `detach_age`,
    `slack_notify_users` and `slack_user_label`."""
    options = context.options
    project_id = options.get("project_id")
    if not project_id:
        raise ValueError("project_id is required for GCP disk cleanup")
    settings = DiskSettings(
        project_id=project_id,
        filter_labels=options.get("filter_tags"),
        exception_labels=options.get("exception_tags"),
        exception_regex=options.get("exception_regex"),
        custom_age_tag_key=options.get("custom_age_tag_key") or "",
        detach_age=options.get("detach_age") or {},
        slack_notify_users=bool(options.get("slack_notify_users")),
        slack_user_label=options.get("slack_user_label") or "",
        notags=options.get("notags"),
        name_regex=options.get("name_regex"),
    )
    return DiskCleaner(ComputeDiskClient(), settings)


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
    time_format = _TIME_FORMAT
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
