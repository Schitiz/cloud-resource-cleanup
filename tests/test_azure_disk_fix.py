"""FIX-AZU-DISK: BUG-172 (only the configured resource group is listed) and BUG-174 (each delete
is isolated and its poller is awaited)."""

import logging
from typing import Any

import pytest

from crc.azu.disk import AzureDiskCleaner, Disk, DiskSettings
from crc.core import logger
from crc.core.cleaner import Operation, RunContext
from tests.helpers_azure_disk import NOW, FakeAzure, disk


@pytest.fixture(autouse=True)
def _reset_run_log() -> Any:
    logger.finish()
    yield
    logger.finish()


def _context(*, dry_run: bool = False) -> RunContext:
    return RunContext(dry_run=dry_run, operation=Operation.DELETE, options={}, now=NOW)


def _cleaner(azure: FakeAzure, group: str = "rg") -> AzureDiskCleaner:
    return AzureDiskCleaner(lambda: azure.client(None, "sub-1"), group, DiskSettings())


def _calls(azure: FakeAzure, name: str) -> list[tuple[Any, ...]]:
    return [c for c in azure.calls if c[0] == name]


def test_bug_172_lists_only_the_configured_group_never_the_subscription() -> None:
    azure = FakeAzure([disk("a")])
    _cleaner(azure, "configured-rg").plan(_context(dry_run=True))
    assert _calls(azure, "list") == []
    assert _calls(azure, "list_by_resource_group") == [("list_by_resource_group", "configured-rg")]


def test_bug_172_delete_targets_the_group_that_was_listed() -> None:
    azure = FakeAzure([disk("a")])
    cleaner = _cleaner(azure, "configured-rg")
    cleaner.apply(cleaner.plan(_context()), _context())
    assert [c[1] for c in _calls(azure, "list_by_resource_group")] == ["configured-rg"]
    assert _calls(azure, "begin_delete") == [("begin_delete", "configured-rg", "a")]


def test_bug_172_listing_error_still_propagates() -> None:
    azure = FakeAzure([], list_error=ValueError("list failed"))
    with pytest.raises(ValueError, match="list failed"):
        _cleaner(azure).plan(_context(dry_run=True))


def test_bug_174_error_on_one_disk_does_not_stop_the_next(
    caplog: pytest.LogCaptureFixture,
) -> None:
    azure = FakeAzure([disk("a"), disk("b"), disk("c")], begin_script={"b": [RuntimeError("nope")]})
    cleaner = _cleaner(azure)
    result = cleaner.apply(cleaner.plan(_context()), _context())
    assert result.succeeded == ("a", "c")
    assert [(f.id, f.error) for f in result.failed] == [("b", "nope")]
    assert [c[2] for c in _calls(azure, "begin_delete")] == ["a", "b", "c"]
    assert azure.waited == ["a", "c"]
    assert "Error occurred while deleting disk b: nope" in caplog.text


def test_bug_174_poller_is_awaited_before_the_disk_counts_as_deleted() -> None:
    azure = FakeAzure([disk("a"), disk("b")], result_script={"a": [RuntimeError("quota")]})
    cleaner = _cleaner(azure)
    result = cleaner.apply(cleaner.plan(_context()), _context())
    assert azure.waited == ["a", "b"]
    assert result.succeeded == ("b",)
    assert [f.id for f in result.failed] == ["a"]


def test_bug_174_failure_is_recorded_in_the_run_log(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    azure = FakeAzure([disk("a")], begin_script={"a": [RuntimeError("nope")]})
    logger.begin("azure", "disk", "delete", False, {})
    cleaner = _cleaner(azure)
    cleaner.apply(cleaner.plan(_context()), _context())
    logger.finish()
    lines = [r.getMessage() for r in caplog.records]
    result_line = next(line for line in lines if line.startswith("RESULT"))
    assert "failed=1" in result_line
    assert any("id=a" in line and "nope" in line for line in lines)


def test_bug_174_dry_run_never_deletes_or_waits() -> None:
    azure = FakeAzure([disk("a")], begin_script={"a": [RuntimeError("nope")]})
    cleaner = _cleaner(azure)
    result = cleaner.apply(cleaner.plan(_context(dry_run=True)), _context(dry_run=True))
    assert result.succeeded == ("a",)
    assert _calls(azure, "begin_delete") == []
    assert azure.waited == []


def test_bug_174_adapter_continues_and_lists_only_deleted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    azure = FakeAzure([disk("a"), disk("b"), disk("c")], begin_script={"a": [RuntimeError("nope")]})
    azure.install(monkeypatch)
    adapter = Disk("rg", False, {}, {}, {}, "", {})
    adapter.clock = lambda: NOW
    adapter.delete()
    assert adapter.get_deleted == ["b", "c"]
    assert adapter.count == len(adapter.get_deleted)
    assert azure.waited == ["b", "c"]


def test_bug_174_selection_errors_still_propagate() -> None:
    azure = FakeAzure([disk("a"), disk("b", created=None)])
    cleaner = _cleaner(azure)
    with pytest.raises(AttributeError):
        cleaner.plan(_context())
    assert _calls(azure, "begin_delete") == []
