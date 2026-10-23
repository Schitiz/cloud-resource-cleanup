# Copyright (c) Yugabyte, Inc.

"""AWS VPC cleaner.

`VpcCleaner` implements the `crc.core.cleaner.Cleaner` contract: `plan()` lists the VPCs of
every region (server side `tag:key` filter) and decides which are protected, `apply()` tears
the VPCs down and deletes them. `VPC` (`adapter.py`) is the legacy class `crc.py` uses.
"""

import logging
import time
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from crc.aws import _regionlog
from crc.aws.connectivity import CONNECTIVITY_ERRORS
from crc.aws.vpc.client import Ec2Client, Ec2Resource, Vpc
from crc.aws.vpc.delete import Sleeper, delete_vpc_with_retries
from crc.aws.vpc.runtime import (
    PROTECTED,
    ClientFactory,
    RegionLister,
    ResourceFactory,
    TagSpec,
    VpcRuntime,
    all_regions,
    boto3_client,
    boto3_resource,
    log_summary,
    skip_region,
)
from crc.aws.vpc.teardown import has_instances, tear_down
from crc.core import logger, policy
from crc.core.cleaner import Candidate, Cleaner, Operation, Plan, Result, RunContext, Skipped
from crc.core.registry import register

__all__ = [
    "ClientFactory",
    "RegionLister",
    "ResourceFactory",
    "TagSpec",
    "VpcCleaner",
    "VpcRuntime",
    "build_vpc_cleaner",
]


class VpcCleaner:
    """Deletes the VPCs the server side `tag:key` filter returns, except the protected ones.
    Applies to every region the injected lister returns."""

    cloud = "aws"
    kind = "vpc"

    def __init__(
        self,
        client_factory: ClientFactory,
        resource_factory: ResourceFactory,
        list_regions: RegionLister,
        filter_tags: TagSpec | None,
        exception_tags: TagSpec | None,
        notags: TagSpec | None,
    ) -> None:
        self._client_factory = client_factory
        self._resource_factory = resource_factory
        self._list_regions = list_regions
        self._filter_tags = filter_tags
        self._exception_tags = exception_tags
        self._notags = notags
        self._vpcs: dict[tuple[str, str], list[Vpc]] = {}
        self.sleep: Sleeper = time.sleep

    def supports(self, operation: Operation) -> bool:
        return operation is Operation.DELETE

    def plan(self, context: RunContext) -> Plan:
        """List every region and decide. Makes no mutating call. Default VPCs are skipped and
        never candidates (BUG-083). Every other listed VPC is a candidate (main records them
        all before the skip check); protected ones carry `protected` in `extra` and are listed
        in `skipped` too. Raises `ValueError` before any SDK call when `filter_tags` is empty."""
        self.require_filter_tags()
        self._vpcs.clear()
        vpc_filter = self.build_filter()
        candidates: list[Candidate] = []
        skipped: list[Skipped] = []
        for region in self._list_regions():
            try:
                self._client_factory(region)
                ec2 = self._resource_factory(region)
                region_plan = self.plan_region(ec2, region, vpc_filter, dry_run=context.dry_run)
            except CONNECTIVITY_ERRORS as e:
                skip_region(region, e)
                continue
            candidates.extend(region_plan.candidates)
            skipped.extend(region_plan.skipped)
        if context.dry_run:
            log_summary([c.id for c in candidates], dry_run=True)
        return Plan(candidates=tuple(candidates), skipped=tuple(skipped))

    def apply(self, plan: Plan, context: RunContext) -> Result:
        """Tear down and delete the planned VPCs, region by region (nothing in a dry run)."""
        ids = [candidate.id for candidate in plan.candidates]
        if context.dry_run:
            for candidate in plan.candidates:
                logger.current().action("would_delete", candidate.region, candidate.id)
            return Result(succeeded=tuple(ids))
        by_region: dict[str, list[Candidate]] = {}
        for candidate in plan.candidates:
            by_region.setdefault(candidate.region, []).append(candidate)
        kept: set[int] = set()
        for region, items in by_region.items():
            try:
                client = self._client_factory(region)
                ec2 = self._resource_factory(region)
                kept.update(id(c) for c in self.apply_region(client, ec2, items))
            except CONNECTIVITY_ERRORS as e:
                skip_region(region, e)
        ids = [c.id for c in plan.candidates if id(c) not in kept]
        log_summary(ids, dry_run=False)
        return Result(succeeded=tuple(ids))

    def require_filter_tags(self) -> None:
        """BUG-083: an empty `filter_tags` would select every VPC of every region."""
        if not self._filter_tags:
            raise ValueError(
                "AWS VPC cleanup needs non-empty filter_tags: an empty tag filter would select "
                "every VPC of every region; refusing to list or delete any"
            )

    def build_filter(self) -> list[dict[str, Any]]:
        """EC2 `tag:key` filters of `filter_tags` (the values list is passed unchanged)."""
        filters: list[dict[str, Any]] = []
        if self._filter_tags:
            filters.extend(
                {"Name": f"tag:{key}", "Values": value} for key, value in self._filter_tags.items()
            )
        logging.info(f"Filters created: {filters}")
        return filters

    def list_vpcs(self, ec2: Ec2Resource, vpc_filter: Sequence[Mapping[str, Any]]) -> list[Vpc]:
        """The VPCs of one region that match the server side filter."""
        return list(ec2.vpcs.filter(Filters=vpc_filter))

    def plan_region(
        self,
        ec2: Ec2Resource,
        region: str,
        vpc_filter: Sequence[Mapping[str, Any]],
        *,
        dry_run: bool,
    ) -> Plan:
        """List one region; unless `dry_run`, also decide which VPCs are protected."""
        started = _regionlog.start()
        vpcs = self.list_vpcs(ec2, vpc_filter)
        ids = [vpc.id for vpc in vpcs]
        candidates: list[Candidate] = []
        skipped: list[Skipped] = []
        for vpc_id, vpc in zip(ids, vpcs, strict=True):
            if self.is_default(vpc):
                logger.current().skip("default_vpc")
                skipped.append(Skipped(id=vpc_id, reason="default VPC"))
                continue
            protected = False if dry_run else self.is_protected(vpc)
            self._vpcs.setdefault((region, vpc_id), []).append(vpc)
            candidates.append(
                Candidate(id=vpc_id, name=vpc_id, region=region, extra={PROTECTED: protected})
            )
            if protected:
                logger.current().skip("protected")
                skipped.append(Skipped(id=vpc_id, reason="matches exception_tags or notags"))
        selected = sum(1 for c in candidates if not c.extra[PROTECTED])
        _regionlog.region_done(region, len(ids), selected, started)
        return Plan(candidates=tuple(candidates), skipped=tuple(skipped))

    def apply_region(
        self, client: Ec2Client, ec2: Ec2Resource, candidates: Sequence[Candidate]
    ) -> list[Candidate]:
        """Tear down every unprotected candidate of one region. Returns the unprotected
        candidates that were kept (instances left, or the VPC could not be deleted)."""
        kept: list[Candidate] = []
        for candidate in candidates:
            vpc = self._vpcs[(candidate.region, candidate.id)].pop(0)
            if candidate.extra[PROTECTED]:
                continue
            if not self.delete_vpc(client, ec2, vpc, region=candidate.region):
                kept.append(candidate)
        return kept

    @staticmethod
    def is_default(vpc: Vpc) -> bool:
        """BUG-083: a default VPC is never touched. Anything but an explicit `False` counts
        as default (fail closed)."""
        return vpc.is_default is not False

    def is_protected(self, vpc: Vpc) -> bool:
        """Exception tags / notags decision on the VPC's own tags (BUG-012). An untagged VPC
        (boto3 returns `None`) has no tags."""
        return self.should_skip(vpc.tags or [])

    def should_skip(self, tags: Iterable[Mapping[str, str]]) -> bool:
        """Exception tags (any key) and notags (all keys) decision for one VPC's tags."""
        if not self._exception_tags and not self._notags:
            logging.warning("Tags and notags not present")
            return False
        all_tags: dict[str, str] = {}
        for tag in tags:
            key = tag["Key"]
            value = tag["Value"]
            if self._exception_tags and policy.exception_tags_any(
                {key: value}, self._exception_tags
            ):
                return True
            all_tags[key] = value
        return policy.notags_all(all_tags, self._notags or {})

    def delete_vpc(
        self, client: Ec2Client, ec2: Ec2Resource, vpc: Vpc, *, region: str | None = None
    ) -> bool:
        """Detach and delete everything the VPC owns, in the order of main, then the VPC.
        A VPC with instances in its subnets is kept before anything is touched (BUG-088).
        Returns True when the VPC was deleted."""
        if has_instances(vpc):
            logger.current().skip("has_instances")
            logging.debug(f"Keeping VPC {vpc.id}: instances in its subnets")
            return False
        try:
            tear_down(client, ec2, vpc)
        except Exception as e:
            logger.current().fail(region, vpc.id, e)
            raise
        return delete_vpc_with_retries(client, vpc, region, self.sleep)


@register("aws", "vpc")
def build_vpc_cleaner(context: RunContext) -> Cleaner:
    """Registry factory. Options: `filter_tags`, `exception_tags` and `notags` (dicts)."""
    options = context.options
    return VpcCleaner(
        client_factory=boto3_client,
        resource_factory=boto3_resource,
        list_regions=all_regions,
        filter_tags=options.get("filter_tags"),
        exception_tags=options.get("exception_tags"),
        notags=options.get("notags"),
    )
