"""The BUG-358 rule of `tests/helpers_log_fix.py` (raw dump lines become DEBUG, nothing else)."""

import logging

import pytest

from tests.helpers_log_fix import expected_logs

DUMPS = ["{}", "{'owner': 'me'}", "namespace(name='a', status='RESERVED')"]
SKIP = "Skipping leftover Spot disk p/z/d: exception_labels/notags"
OTHER = [
    "Deleting disk a",
    "List of GCP disk deleted: [{'a': 1}]",
    "Updating age for disk: a",
    "RESULT cloud=gcp resource=disk operation=delete dry_run=false selected=0",
]


@pytest.mark.parametrize("message", [*DUMPS, SKIP])
def test_bug_358_dump_becomes_debug_in_every_record_shape(message: str) -> None:
    assert expected_logs([(logging.INFO, message)], {"BUG-358"}) == [(logging.DEBUG, message)]
    assert expected_logs([("INFO", message)], {"BUG-358"}) == [("DEBUG", message)]
    assert expected_logs([("root", logging.INFO, message)], {"BUG-358"}) == [
        ("root", logging.DEBUG, message)
    ]


@pytest.mark.parametrize("message", OTHER)
def test_bug_358_leaves_other_lines_alone(message: str) -> None:
    records = [("root", logging.INFO, message), ("root", logging.WARNING, message)]
    assert expected_logs(records, {"BUG-358"}) == records


def test_bug_358_only_touches_info_dumps() -> None:
    records = [("root", logging.WARNING, "{}"), ("root", logging.ERROR, SKIP)]
    assert expected_logs(records, {"BUG-358"}) == records
