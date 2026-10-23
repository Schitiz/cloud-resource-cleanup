# Copyright (c) Yugabyte, Inc.

"""OCI block volume and boot volume cleaner (`DiskCleaner`).

`plan()` lists the volumes, boot volumes and attachments of every region and decides on them;
`apply()` calls `delete_volume` / `delete_boot_volume`. The legacy class `Disk` is in `adapter.py`.
"""

import datetime
import logging
from collections.abc import Sequence

from crc.core import policy
from crc.core.cleaner import (
    Candidate,
    Cleaner,
    Failure,
    Operation,
    Plan,
    Result,
    RunContext,
    Skipped,
)
from crc.core.registry import register
from crc.oci import _logger
from crc.oci._base import Base
from crc.oci._common import group_by_region
from crc.oci.connectivity import CONNECTIVITY_ERRORS, log_skipped_region
from crc.oci.disk.api import ApiFactory, RegionLister, SdkVolume, VolumeApi, api_for, regions_of
from crc.oci.disk.decide import in_use, skip_reason, sort_decisions
from crc.oci.disk.settings import (
    ATTACHMENTS_CONTEXT,
    BOOT_ATTACHMENTS_CONTEXT,
    IN_USE_ATTACHMENT_STATES,
    KIND_BOOT_DISK,
    KIND_DISK,
    KIND_KEY,
    LIST_CONTEXT,
    SKIP_KEYS,
    UNKNOWN_REASONS,
    Clock,
    DiskRuntime,
    DiskSettings,
    TagSpec,
    log_summary,
)

_LIST_CONTEXT = LIST_CONTEXT
_log_summary = log_summary

__all__ = [
    "IN_USE_ATTACHMENT_STATES",
    "KIND_BOOT_DISK",
    "KIND_DISK",
    "SKIP_KEYS",
    "_LIST_CONTEXT",
    "Clock",
    "DiskCleaner",
    "DiskRuntime",
    "DiskSettings",
    "TagSpec",
    "_log_summary",
    "build_disk_cleaner",
]


class DiskCleaner:
    """Deletes `AVAILABLE` block volumes and boot volumes that are not attached, match the
    filter tags (any key), are not excluded by exception tags or notags, and are old enough.
    Applies to every region the injected lister returns."""

    cloud = "oci"
    kind = "disk"

    def __init__(
        self,
        api_factory: ApiFactory,
        list_regions: RegionLister,
        settings: DiskSettings,
    ) -> None:
        self._api_factory = api_factory
        self._list_regions = list_regions
        self._settings = settings
        self._unknown_regions: set[str] = set()

    def supports(self, operation: Operation) -> bool:
        return operation is Operation.DELETE

    def plan(self, context: RunContext) -> Plan:
        """List every region and decide on each volume. Makes no mutating call."""
        candidates: list[Candidate] = []
        skipped: list[Skipped] = []
        self._unknown_regions = set()
        for region in self._list_regions():
            started = _logger.region_started()
            before = len(candidates)
            try:
                api = self._api_factory(region)
                volumes, boot_volumes = self.list_region(api)
            except CONNECTIVITY_ERRORS as e:
                log_skipped_region(region, LIST_CONTEXT, e)
                _logger.region_skipped(region, e)
                continue
            attached = self.attached_volume_ids(api, region)
            sort_decisions(
                (self.decide(v, attached, KIND_DISK, region, context.now) for v in volumes),
                candidates,
                skipped,
            )
            attached_boot = self.attached_boot_volume_ids(api, region)
            sort_decisions(
                (
                    self.decide(v, attached_boot, KIND_BOOT_DISK, region, context.now)
                    for v in boot_volumes
                ),
                candidates,
                skipped,
            )
            _logger.region_done(
                region, len(volumes) + len(boot_volumes), len(candidates) - before, started
            )
        if context.dry_run:
            log_summary([c.name for c in candidates], dry_run=True)
        return Plan(candidates=tuple(candidates), skipped=tuple(skipped))

    def apply(self, plan: Plan, context: RunContext) -> Result:
        """Delete the planned volumes region by region (nothing in a dry run). A failed delete
        is logged and left out of the result, as on main."""
        deleted: list[str] = []
        failed: list[Failure] = []
        for region, items in group_by_region(plan.candidates).items():
            api = self._api_factory(region)
            for candidate in items:
                error = self.remove(api, candidate, deleted, dry_run=context.dry_run)
                if error is not None:
                    failed.append(error)
        log_summary(deleted, dry_run=context.dry_run)
        return Result(succeeded=tuple(deleted), failed=tuple(failed))

    def list_region(self, api: VolumeApi) -> tuple[Sequence[SdkVolume], Sequence[SdkVolume]]:
        """Block volumes then boot volumes of one region."""
        return api.list_volumes(), api.list_boot_volumes()

    def attached_volume_ids(self, api: VolumeApi, region: str) -> set[str] | None:
        """Ids of block volumes in use, or `None` when the attachments cannot be listed (a
        connectivity error). OCI has no "unattached" lifecycle state: a volume stays `AVAILABLE`
        whether or not it is attached, so attachments are listed separately. `None` means every
        block volume of the region is kept (fail closed, BUG-096)."""
        try:
            return {a.volume_id for a in in_use(api.list_volume_attachments())}
        except CONNECTIVITY_ERRORS as e:
            log_skipped_region(region, ATTACHMENTS_CONTEXT, e)
            self._keep_all(region, KIND_DISK, e)
            return None

    def attached_boot_volume_ids(self, api: VolumeApi, region: str) -> set[str] | None:
        """Ids of boot volumes in use, or `None` when they cannot be known: a connectivity
        error while listing availability domains or any domain's attachments (BUG-097), or a
        region without availability domains (BUG-098). `None` means every boot volume of the
        region is kept (fail closed). Boot volume attachments are scoped per availability
        domain, unlike regular volume attachments."""
        attached_ids: set[str] = set()
        try:
            domains = api.list_availability_domains()
            if not domains:
                self._keep_all(region, KIND_BOOT_DISK, ValueError("no availability domains"))
                return None
            for domain in domains:
                attached_ids.update(
                    a.boot_volume_id for a in in_use(api.list_boot_volume_attachments(domain))
                )
        except CONNECTIVITY_ERRORS as e:
            log_skipped_region(region, BOOT_ATTACHMENTS_CONTEXT, e)
            self._keep_all(region, KIND_BOOT_DISK, e)
            return None
        return attached_ids

    def _keep_all(self, region: str, kind: str, error: BaseException) -> None:
        logging.warning(f"Region {region}: keeping every {kind}: {UNKNOWN_REASONS[kind]}")
        if region not in self._unknown_regions:
            self._unknown_regions.add(region)
            _logger.region_skipped(region, error)

    def decide(
        self,
        volume: SdkVolume,
        attached_ids: set[str] | None,
        kind: str,
        region: str,
        now: datetime.datetime,
    ) -> Candidate | Skipped:
        """State, attachment, tag and age checks common to block and boot volumes.
        `attached_ids` is `None` when the attachments are unknown: the volume is kept."""
        reason = skip_reason(self._settings, volume, attached_ids, kind, now)
        if reason is not None:
            _logger.record_skip(SKIP_KEYS[reason])
            return Skipped(id=volume.id, reason=reason, name=volume.display_name)
        return Candidate(
            id=volume.id,
            name=volume.display_name,
            region=region,
            state=volume.lifecycle_state,
            launch_time=volume.time_created,
            tags=policy.normalize_tags(volume.freeform_tags),
            extra={KIND_KEY: kind},
        )

    def remove(
        self, api: VolumeApi, candidate: Candidate, deleted: list[str], *, dry_run: bool
    ) -> Failure | None:
        """Delete one planned volume and record its name in `deleted` (also in a dry run, where
        nothing is deleted). Any error is logged and returned, not raised."""
        kind = candidate.extra[KIND_KEY]
        try:
            if not dry_run:
                if kind == KIND_BOOT_DISK:
                    api.delete_boot_volume(candidate.id)
                else:
                    api.delete_volume(candidate.id)
                logging.info(f"Deleting {kind} {candidate.name}")
            deleted.append(candidate.name)
        except Exception as e:
            logging.error(f"Error occurred while deleting {kind} {candidate.name}: {e}")
            _logger.record_failure(candidate.region, candidate.id, e)
            return Failure(id=candidate.name, error=str(e))
        _logger.record_action(
            Operation.DELETE,
            dry_run=dry_run,
            region=candidate.region,
            resource_id=candidate.id,
            name=candidate.name,
        )
        return None


@register("oci", "disk")
def build_disk_cleaner(context: RunContext) -> Cleaner:
    """Registry factory. Options: `filter_tags`, `exception_tags`, `notags` (dicts), `age`
    (dict) and `custom_age_tag_key`."""
    options = context.options
    base = Base()
    settings = DiskSettings(
        filter_tags=options.get("filter_tags") or {},
        exception_tags=options.get("exception_tags") or {},
        notags=options.get("notags") or {},
        age=options.get("age") or {},
        custom_age_tag_key=options.get("custom_age_tag_key") or "",
    )
    return DiskCleaner(api_for(base), regions_of(base), settings)
