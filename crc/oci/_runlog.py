# Copyright (c) Yugabyte, Inc.

"""Thin glue between the OCI cleaners and `crc.core.runlog` (rung LOG-OCI).

Log text only: these helpers report what a cleaner did to the current run and never decide
anything. `monotonic` is bound by name so a test that patches `time.monotonic` (the spot VM
terminate wait does) does not consume its fake clock here.
"""

from time import monotonic

from crc.core import runlog
from crc.core.cleaner import Operation

_ACTION_KINDS = {
    (Operation.DELETE, False): "deleted",
    (Operation.DELETE, True): "would_delete",
    (Operation.STOP, False): "stopped",
    (Operation.STOP, True): "would_stop",
}


def region_started() -> float:
    """Start time of a region walk, for the REGION line's `seconds`."""
    return monotonic()


def region_done(region: str, scanned: int, selected: int, started: float) -> None:
    """Log the REGION line of a region that was walked."""
    runlog.current().region(region, scanned, selected, monotonic() - started)


def region_skipped(region: str, error: BaseException) -> None:
    """Count a region skipped for a connectivity error (its warning is logged separately)."""
    runlog.current().region_skipped(region, error)


def record_action(
    operation: Operation,
    *,
    dry_run: bool,
    region: str | None,
    resource_id: str,
    name: str | None,
) -> None:
    """Log the ACTION line of one resource acted on (or that would be in a dry run)."""
    kind = _ACTION_KINDS[(operation, dry_run)]
    runlog.current().action(kind, region, resource_id, name)


def record_skip(reason: str) -> None:
    """Count one skipped resource under a short snake_case reason."""
    runlog.current().skip(reason)


def record_failure(region: str | None, resource_id: str, error: BaseException | str) -> None:
    """Record one per-resource failure for the end-of-run list."""
    runlog.current().fail(region, resource_id, error)
