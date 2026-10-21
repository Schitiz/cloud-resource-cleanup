# Copyright (c) Yugabyte, Inc.

"""OCI compute instance cleaner.

`VmCleaner` implements the `crc.core.cleaner.Cleaner` contract: `plan()` lists the instances of
every region and decides on them, `apply()` terminates (delete) or stops them. `VM` is the legacy
class `crc.py` uses; it keeps its constructor and attributes and runs the cleaner region by
region, instance by instance, in the exact call order of the original implementation.
"""

import datetime
import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import ClassVar, cast

from crc.core import age as core_age
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
from crc.oci._base import Base
from crc.oci.connectivity import CONNECTIVITY_ERRORS, log_skipped_region
from crc.oci.disk_api import RegionLister, regions_of
from crc.oci.vm_api import ApiFactory, ComputeApi, SdkInstance, compute_api_for
from crc.service import Service

DEFAULT_INSTANCE_STATES = ("RUNNING",)

TagSpec = Mapping[str, Sequence[str]]
Clock = Callable[[], datetime.datetime]


@dataclass(frozen=True, slots=True)
class VmRuntime:
    """Injected collaborators of `VM`: any of them left as `None` is built from the OCI SDK
    (through `Base`), and the clock supplies `now` (the cleaner itself never reads the clock)."""

    api_factory: ApiFactory | None = None
    list_regions: RegionLister | None = None
    clock: Clock = datetime.datetime.now


@dataclass(frozen=True, slots=True)
class VmSettings:
    """Filters and thresholds of one run."""

    filter_tags: TagSpec = field(default_factory=dict)
    exception_tags: TagSpec = field(default_factory=dict)
    notags: TagSpec = field(default_factory=dict)
    age: core_age.AgeSpec = field(default_factory=dict)
    custom_age_tag_key: str = ""
    instance_states: Sequence[str] = DEFAULT_INSTANCE_STATES


def _log_summary(
    operation: Operation,
    deleted: Sequence[str],
    stopped: Sequence[str],
    *,
    dry_run: bool,
) -> None:
    """The closing lines of main. Both name lists are passed because main's "nothing to do"
    warning looks at the two of them, whichever operation runs."""
    if not deleted and not stopped:
        logging.warning(f"No OCI instances to {operation}.")

    if operation is Operation.DELETE:
        if not dry_run:
            logging.info(f"number of OCI instances deleted: {len(deleted)}")
            logging.warning(f"List of OCI instances deleted: {list(deleted)}")
        else:
            logging.warning(
                f"List of OCI instances (Total: {len(deleted)}) "
                f"which will be deleted: {list(deleted)}"
            )

    if operation is Operation.STOP:
        if not dry_run:
            logging.info(f"number of OCI instances stopped: {len(stopped)}")
            logging.warning(f"List of OCI instances stopped: {list(stopped)}")
        else:
            logging.warning(
                f"List of OCI instances (Total: {len(stopped)}) "
                f"which will be stopped: {list(stopped)}"
            )


def _log_for(operation: Operation, names: Sequence[str], *, dry_run: bool) -> None:
    """`_log_summary` for a run that only ever fills one of the two lists."""
    other: list[str] = []
    if operation is Operation.DELETE:
        _log_summary(operation, names, other, dry_run=dry_run)
    else:
        _log_summary(operation, other, names, dry_run=dry_run)


class VmCleaner:
    """Terminates (delete) or stops instances that are in an allowed lifecycle state, match
    the filter tags (all keys), are not excluded by exception tags or notags, and are old
    enough. Applies to every region the injected lister returns."""

    cloud = "oci"
    kind = "vm"

    def __init__(
        self,
        api_factory: ApiFactory,
        list_regions: RegionLister,
        settings: VmSettings,
    ) -> None:
        self._api_factory = api_factory
        self._list_regions = list_regions
        self._settings = settings

    def supports(self, operation: Operation) -> bool:
        return operation in (Operation.DELETE, Operation.STOP)

    def plan(self, context: RunContext) -> Plan:
        """List every region and decide on each instance. Makes no mutating call."""
        candidates: list[Candidate] = []
        skipped: list[Skipped] = []
        for region in self._list_regions():
            try:
                api = self._api_factory(region)
                instances = api.list_instances()
            except CONNECTIVITY_ERRORS as e:
                log_skipped_region(region, f"list_instances vm {context.operation}", e)
                continue
            for instance in instances:
                decision = self.decide(instance, region, lambda: context.now)
                if isinstance(decision, Candidate):
                    candidates.append(decision)
                else:
                    skipped.append(decision)
        if context.dry_run:
            _log_for(context.operation, [c.name for c in candidates], dry_run=True)
        return Plan(candidates=tuple(candidates), skipped=tuple(skipped))

    def apply(self, plan: Plan, context: RunContext) -> Result:
        """Act on the planned instances region by region (nothing in a dry run). A failed call
        is logged and left out of the result, as on main."""
        if context.dry_run:
            return Result(succeeded=tuple(c.name for c in plan.candidates))
        by_region: dict[str, list[Candidate]] = {}
        for candidate in plan.candidates:
            by_region.setdefault(candidate.region, []).append(candidate)
        done: list[str] = []
        failed: list[Failure] = []
        for region, items in by_region.items():
            api = self._api_factory(region)
            for candidate in items:
                error = self.act(api, candidate, context.operation, done, dry_run=False)
                if error is not None:
                    failed.append(error)
        _log_for(context.operation, done, dry_run=False)
        return Result(succeeded=tuple(done), failed=tuple(failed))

    def decide(self, instance: SdkInstance, region: str, clock: Clock) -> Candidate | Skipped:
        """State, tag and age checks, in the order of main. `clock` is only read by the age
        check, as `datetime.now()` is on main."""
        reason = self._skip_reason(instance, clock)
        if reason is not None:
            return Skipped(id=instance.id, reason=reason, name=instance.display_name)
        return Candidate(
            id=instance.id,
            name=instance.display_name,
            region=region,
            state=instance.lifecycle_state,
            launch_time=instance.time_created,
            tags=policy.normalize_tags(instance.freeform_tags),
        )

    def act(
        self,
        api: ComputeApi,
        candidate: Candidate,
        operation: Operation,
        done: list[str],
        *,
        dry_run: bool,
    ) -> Failure | None:
        """Terminate or stop one planned instance and record its name in `done` (also in a dry
        run, where nothing is called). Any error is logged and returned, not raised."""
        try:
            if not dry_run:
                if operation is Operation.DELETE:
                    api.terminate_instance(candidate.id)
                    logging.info(f"Deleting instance {candidate.name}")
                else:
                    api.stop_instance(candidate.id)
                    logging.info(f"Stopping instance {candidate.name}")
            done.append(candidate.name)
        except Exception as e:
            logging.error(f"Error occurred while {operation} instance {candidate.name}: {e}")
            return Failure(id=candidate.name, error=str(e))
        return None

    def _skip_reason(self, instance: SdkInstance, clock: Clock) -> str | None:
        settings = self._settings
        if not policy.state_in(instance.lifecycle_state, settings.instance_states):
            return "state is not allowed"
        tags = policy.normalize_tags(instance.freeform_tags)
        if policy.should_skip_by_tags(tags, settings.exception_tags, settings.notags):
            return "matches exception_tags or notags"
        if not policy.filter_tags_all_keys(tags, settings.filter_tags):
            return "does not match filter_tags"
        if not self._is_old(instance, clock):
            return "not older than age"
        return None

    def _is_old(self, instance: SdkInstance, clock: Clock) -> bool:
        """Older than `age`, or than the instance's own custom age tag (capped by MAX_AGE)."""
        created_time = instance.time_created
        now = clock().astimezone(created_time.tzinfo)
        tags = instance.freeform_tags or {}
        logging.info(tags)
        retention_age = core_age.get_retention_age(
            cast(dict[str, str], tags), self._settings.custom_age_tag_key
        )
        if retention_age:
            logging.info(f"Updating age for instance: {instance.display_name}")
        return core_age.is_old(
            policy.effective_age(retention_age, self._settings.age), now, created_time
        )


@register("oci", "vm")
def build_vm_cleaner(context: RunContext) -> Cleaner:
    """Registry factory. Options: `filter_tags`, `exception_tags`, `notags` (dicts), `age`
    (dict), `custom_age_tag_key` and `instance_state` (list, default `["RUNNING"]`)."""
    options = context.options
    base = Base()
    states = options.get("instance_state") if context.operation is Operation.DELETE else None
    settings = VmSettings(
        filter_tags=options.get("filter_tags") or {},
        exception_tags=options.get("exception_tags") or {},
        notags=options.get("notags") or {},
        age=options.get("age") or {},
        custom_age_tag_key=options.get("custom_age_tag_key") or "",
        instance_states=DEFAULT_INSTANCE_STATES if states is None else states,
    )
    return VmCleaner(compute_api_for(base), regions_of(base), settings)


class VM(Service, Base):
    """Legacy entry point used by `crc.py`: terminates (`delete()`) or stops (`stop()`)
    instances that match the filter tags and are older than `age`, excluding exception tags and
    notags. In dry run it only lists them.

    Attributes: `instance_names_to_delete` and `instance_names_to_stop` (display names acted
    on, or listed in a dry run, accumulated over calls), the constructor arguments,
    `get_deleted`, `delete_count`, `get_stopped`, `stopped_count`, `delete()` and `stop()`.
    """

    default_instance_state: ClassVar[list[str]] = ["RUNNING"]
    """The default state of instances that will be deleted."""

    def __init__(  # noqa: PLR0913, PLR0917 - the six parameters are the public signature
        self,
        dry_run: bool,
        filter_tags: TagSpec,
        exception_tags: TagSpec,
        age: core_age.AgeSpec,
        custom_age_tag_key: str,
        notags: TagSpec,
        runtime: VmRuntime | None = None,
    ) -> None:
        """
        :param dry_run: If True, only list matching instances without deleting/stopping them.
        :param filter_tags: Freeform tags and their values used to select instances.
        :param exception_tags: Freeform tags and their values that exclude instances.
        :param age: Age (days/hours) of instances that will be deleted.
        :param custom_age_tag_key: Tag name to overwrite the age condition.
        :param notags: Tags that exclude instances which have all of them.
        :param runtime: Injected SDK access and clock; tests pass fakes.
        """
        Service.__init__(self)
        Base.__init__(self)
        self.instance_names_to_delete: list[str] = []
        self.instance_names_to_stop: list[str] = []
        self.dry_run = dry_run
        self.filter_tags = filter_tags
        self.exception_tags = exception_tags
        self.age = age
        self.custom_age_tag_key = custom_age_tag_key
        self.notags = notags
        self._runtime = runtime or VmRuntime()

    @property
    def get_deleted(self) -> list[str]:
        """Display names of the instances terminated (listed in a dry run)."""
        return self.instance_names_to_delete

    @property
    def delete_count(self) -> int:
        """Number of instances terminated (listed in a dry run); logs the count."""
        count = len(self.instance_names_to_delete)
        logging.info(f"count of items in instance_names_to_delete: {count}")
        return count

    @property
    def get_stopped(self) -> list[str]:
        """Display names of the instances stopped (listed in a dry run)."""
        return self.instance_names_to_stop

    @property
    def stopped_count(self) -> int:
        """Number of instances stopped (listed in a dry run); logs the count."""
        count = len(self.instance_names_to_stop)
        logging.info(f"count of items in instance_names_to_stop: {count}")
        return count

    def delete(self, instance_state: list[str] = default_instance_state) -> None:
        """Terminate (or, in a dry run, only list) the matching instances of every region."""
        self._perform_operation(Operation.DELETE, instance_state)

    def stop(self) -> None:
        """Stop (or, in a dry run, only list) the matching instances of every region."""
        self._perform_operation(Operation.STOP, self.default_instance_state)

    def _perform_operation(self, operation: Operation, instance_state: list[str]) -> None:
        runtime = self._runtime
        api_factory = runtime.api_factory or compute_api_for(self)
        list_regions = runtime.list_regions or regions_of(self)
        cleaner = VmCleaner(
            api_factory,
            list_regions,
            VmSettings(
                self.filter_tags or {},
                self.exception_tags or {},
                self.notags or {},
                self.age,
                self.custom_age_tag_key,
                instance_state,
            ),
        )
        names = (
            self.instance_names_to_delete
            if operation is Operation.DELETE
            else self.instance_names_to_stop
        )
        for region in list_regions():
            try:
                api = api_factory(region)
                instances = api.list_instances()
            except CONNECTIVITY_ERRORS as e:
                log_skipped_region(region, f"list_instances vm {operation}", e)
                continue
            for instance in instances:
                decision = cleaner.decide(instance, region, runtime.clock)
                if isinstance(decision, Candidate):
                    cleaner.act(api, decision, operation, names, dry_run=self.dry_run)
        _log_summary(
            operation,
            self.instance_names_to_delete,
            self.instance_names_to_stop,
            dry_run=self.dry_run,
        )
