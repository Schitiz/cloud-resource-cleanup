"""Expected log lists of the LOG rungs: the oracle logs rewritten one bug rule at a time.

Oracles in ``tests/legacy/*.txt`` stay frozen. A parity test compares the new code with
``expected_logs(oracle_logs, {<bug IDs of the lane>})``. A rule may only change the level of a
line or insert documented new lines; it never drops an oracle line or changes its text.
Contract: ``docs/refactor/LOGGING.md``.
"""

import logging
import re
from collections.abc import Callable, Sequence
from typing import Any

LogRecordKey = tuple[Any, ...]

_AGE_CHECK_PATTERNS = (
    re.compile(r"^Validating resource age with threshold: "),
    re.compile(r"^The resource is .+ old and older than the threshold of .+\.$"),
    re.compile(r"^The resource is not older than the threshold specified in the age argument$"),
    re.compile(r"^No tags provided to search for custom_age_tag_key\.$"),
    re.compile(r"^Searching for custom_age_tag_key: "),
)


def _is_age_check(message: str) -> bool:
    return any(pattern.search(message) for pattern in _AGE_CHECK_PATTERNS)


def _with_level(record: LogRecordKey, level: int) -> LogRecordKey:
    """Return the record with its level replaced, keeping the level's type (int or name)."""
    current = record[-2]
    new_level: Any = logging.getLevelName(level) if isinstance(current, str) else level
    return (*record[:-2], new_level, record[-1])


def _bug_356(records: list[LogRecordKey]) -> list[LogRecordKey]:
    """BUG-356: the per-resource age-check lines become DEBUG, text unchanged."""
    return [
        _with_level(record, logging.DEBUG) if _is_age_check(str(record[-1])) else record
        for record in records
    ]


RULES: dict[str, Callable[[list[LogRecordKey]], list[LogRecordKey]]] = {
    "BUG-356": _bug_356,
}


def _is_tag_dump(message: str) -> bool:
    """OCI dumps `str(freeform_tags)`: a bare dict repr with no other text."""
    return message.startswith("{") and message.endswith("}")


_LEFTOVER_SKIP = re.compile(r"^Skipping leftover volume .+: exception_tags/notags$")


def _bug_353(records: list[LogRecordKey]) -> list[LogRecordKey]:
    """BUG-353: the OCI age-check freeform tag dict becomes DEBUG, text unchanged."""
    return [
        _with_level(record, logging.DEBUG) if _is_tag_dump(str(record[-1])) else record
        for record in records
    ]


def _bug_358(records: list[LogRecordKey]) -> list[LogRecordKey]:
    """BUG-358: raw tag dumps and the OCI per-resource "Skipping leftover volume" line become
    DEBUG, text unchanged."""
    return [
        _with_level(record, logging.DEBUG)
        if _is_tag_dump(str(record[-1])) or _LEFTOVER_SKIP.search(str(record[-1]))
        else record
        for record in _bug_353(records)
    ]


def _inserted_lines_only(records: list[LogRecordKey]) -> list[LogRecordKey]:
    """BUG-361 and BUG-362 only add RUN START/REGION/ACTION/SKIPPED/ERRORS/FAILED/RESULT lines
    in an attached run (`runlog.begin`). A parity run is unattached, so the oracle list is
    unchanged; the new lines are asserted exactly in the runlog unit tests, never dropped here."""
    return list(records)


RULES.update(
    {
        "BUG-353": _bug_353,
        "BUG-358": _bug_358,
        "BUG-361": _inserted_lines_only,
        "BUG-362": _inserted_lines_only,
    }
)


def expected_logs(oracle_logs: Sequence[LogRecordKey], bugs: set[str]) -> list[LogRecordKey]:
    """Rewrite the oracle log records with the rule of each bug ID.

    A record is a tuple whose last item is the message and whose second to last is the level
    (``levelno`` or ``levelname``); any items before them (for example the logger name) are kept.
    Rules apply in sorted bug-ID order. An unknown bug ID raises ``KeyError``.
    """
    records = [tuple(record) for record in oracle_logs]
    for bug in sorted(bugs):
        records = RULES[bug](records)
    return records


def expected_outcome(oracle: tuple[Any, Any, Sequence[LogRecordKey]], bugs: set[str]) -> Any:
    """Rewrite the log list (third item) of a ``(kind, result, logs)`` parity outcome."""
    kind, result, logs = oracle
    return kind, result, expected_logs(logs, bugs)
