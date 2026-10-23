# Copyright (c) Yugabyte, Inc.

"""Settings, skip vocabulary and summary logging of the OCI VM cleaner."""

import datetime
import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from crc.core import age as core_age
from crc.core.cleaner import Operation

DEFAULT_INSTANCE_STATES = ("RUNNING",)

TagSpec = Mapping[str, Sequence[str]]
SKIP_KEYS = {
    "state is not allowed": "state",
    "OKE or instance pool member": "managed",
    "matches exception_tags or notags": "exception_tag",
    "does not match filter_tags": "filter_mismatch",
    "not older than age": "too_young",
}
EVALUATION_FAILED = "evaluation failed"
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


def log_summary(
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


def log_for(operation: Operation, names: Sequence[str], *, dry_run: bool) -> None:
    """`log_summary` for a run that only ever fills one of the two lists."""
    other: list[str] = []
    if operation is Operation.DELETE:
        log_summary(operation, names, other, dry_run=dry_run)
    else:
        log_summary(operation, other, names, dry_run=dry_run)
