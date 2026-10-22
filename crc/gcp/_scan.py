# Copyright (c) Yugabyte, Inc.

"""Run-log helpers shared by the GCP cleaners (rung LOG-GCP): the REGION line of one zone or
region pass and the ACTION kind of one resource. Log text only; nothing here selects or acts."""

import time

from crc.core import runlog
from crc.core.cleaner import Candidate


class ZoneScan:
    """Counts the resources listed and selected in one zone or region and reports the pass as
    one `REGION` line to the current run when `finish()` is called."""

    def __init__(self, region: str) -> None:
        self._region = region
        self._started = time.monotonic()
        self.scanned = 0
        self.selected = 0

    def finish(self) -> None:
        """Report the pass: the REGION line of the current run (nothing when none began)."""
        seconds = time.monotonic() - self._started
        runlog.current().region(self._region, self.scanned, self.selected, seconds)


def log_action(verb: str, candidate: Candidate, *, dry_run: bool) -> None:
    """Log the ACTION line of one resource a `delete` or `stop` was done to, or would be in a
    dry run (`would_<verb>`; else `deleted` or `stopped`)."""
    kind = f"would_{verb}" if dry_run else ("deleted" if verb == "delete" else "stopped")
    runlog.current().action(kind, candidate.region, candidate.id, candidate.name)
