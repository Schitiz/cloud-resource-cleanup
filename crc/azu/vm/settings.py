# Copyright (c) Yugabyte, Inc.

"""Settings, name tally and summary logging of the Azure VM cleaner."""

import datetime
import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from crc.core import age as core_age
from crc.core.cleaner import Operation

DEFAULT_INSTANCE_STATES = ("running",)

TagSpec = Mapping[str, Sequence[str]]
Clock = Callable[[], datetime.datetime]


@dataclass(frozen=True, slots=True)
class VmSettings:
    """Filters and thresholds of one run."""

    filter_tags: TagSpec = field(default_factory=dict)
    exception_tags: TagSpec = field(default_factory=dict)
    notags: TagSpec = field(default_factory=dict)
    age: core_age.AgeSpec = field(default_factory=dict)
    custom_age_tag_key: str = ""
    instance_states: Sequence[str] = DEFAULT_INSTANCE_STATES


@dataclass(slots=True)
class Tally:
    """Names recorded so far: VMs deleted, VMs stopped and NICs deleted (also in a dry run)."""

    deleted: list[str] = field(default_factory=list)
    stopped: list[str] = field(default_factory=list)
    nics: list[str] = field(default_factory=list)


def _log_deleted(tally: Tally, *, dry_run: bool) -> None:
    if not dry_run:
        logging.warning(f"number of Azure instances deleted: {len(tally.deleted)}")
        logging.warning(f"List of Azure instances deleted: {tally.deleted}")
        logging.warning(f"number of Azure nics deleted: {len(tally.nics)}")
        logging.warning(f"List of Azure nics deleted: {tally.nics}")
    else:
        logging.warning(
            f"List of Azure instances (Total: {len(tally.deleted)}) "
            f"which will be deleted: {tally.deleted}"
        )
        logging.warning(
            f"List of Azure nics (Total: {len(tally.nics)}) which will be deleted: {tally.nics}"
        )


def _log_stopped(tally: Tally, *, dry_run: bool) -> None:
    if not dry_run:
        logging.warning(f"number of Azure instances stopped: {len(tally.stopped)}")
        logging.warning(f"List of Azure instances stopped: {tally.stopped}")
    else:
        logging.warning(
            f"List of Azure instances (Total: {len(tally.stopped)}) "
            f"which will be stopped: {tally.stopped}"
        )


def log_summary(operation: Operation, tally: Tally, *, dry_run: bool) -> None:
    """The closing lines of main. The "nothing to do" warning looks at both name lists,
    whichever operation runs."""
    if not tally.deleted and not tally.stopped:
        logging.warning(f"No Azure instances to {operation}.")
    if operation is Operation.DELETE:
        _log_deleted(tally, dry_run=dry_run)
    if operation is Operation.STOP:
        _log_stopped(tally, dry_run=dry_run)
