# Copyright (c) Yugabyte, Inc.

"""Helpers shared by the Azure ip, nic and disk cleaners (log text and skip bookkeeping only)."""

import logging
from collections.abc import Iterable, Sequence

from crc.azu import _logger
from crc.core.cleaner import Candidate


def kept(reason: str) -> tuple[None, str]:
    """Count a kept resource under `reason` and return the "not selected" decision."""
    _logger.skip(reason)
    return None, reason


def log_would_delete(resource_group: str, candidates: Iterable[Candidate]) -> None:
    """One dry-run ACTION line per planned resource."""
    for candidate in candidates:
        _logger.acted("would_delete", resource_group, candidate.id)


def log_delete_summary(
    noun: str, deleted: Sequence[str], *, dry_run: bool, number_word: str = "number"
) -> None:
    """The closing warning lines main logs for a resource kind (`noun` is e.g. `IPs`)."""
    items = list(deleted)
    if dry_run:
        logging.warning(
            "List of Azure %s (Total: %s) which will be deleted: %s", noun, len(items), items
        )
    else:
        logging.warning("%s of Azure %s deleted: %s", number_word, noun, len(items))
        logging.warning("List of Azure %s deleted: %s", noun, items)
