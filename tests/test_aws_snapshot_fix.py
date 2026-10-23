"""FIX-AWS-SNAP: BUG-144 (tolerant exception-tag reading) and BUG-149 (a non-connectivity
error while listing a region skips only that region).

The diverging parity cases (`DIVERGES` in `tests/test_aws_snapshot_parity.py`) are run through
the oracle and through both new paths: the outcome differs from `main` and equals the table.
"""

import datetime
import logging
from collections.abc import Iterator, Sequence
from typing import Any

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from crc.aws.snapshot import Snapshot, SnapshotCleaner, SnapshotClient, SnapshotRuntime
from crc.core import logger
from crc.core.cleaner import Operation, RunContext
from tests.test_aws_snapshot_parity import (
    CASES,
    DIVERGES,
    NOW,
    _legacy,
    _new,
    _run,
    _run_cleaner,
)

ADAPTER = "adapter"
CLEANER = "cleaner"
OLD_ENOUGH = 100

# case id -> (deleted by the adapter path, deleted by the Cleaner path). The adapter deletes as
# it goes, so snapshots listed before a failing one in the same region are already deleted; the
# Cleaner decides the whole region before it deletes, so a failing region deletes nothing.
EXPECTED: dict[str, tuple[list[str], list[str]]] = {
    "tag-missing-value-raises": (["a"], ["a"]),
    "tag-missing-key-raises": (["a"], ["a"]),
    "tag-malformed-after-deleted-snapshot": (["a", "b", "c"], ["a", "b", "c"]),
    "missing-start-time": (["a"], []),
    "missing-snapshot-id": (["a"], []),
    "missing-snapshots-key": ([], []),
    "naive-start-time": ([], []),
    "start-time-string": ([], []),
    "tags-is-dict": ([], []),
    "exception-tags-not-a-dict": ([], []),
    "ami-ebs-none-raises": ([], []),
    "ami-missing-images-key": ([], []),
    "describe-unexpected-error": ([], []),
    "describe-snapshots-client-error-propagates": (["a"], ["a"]),
    "describe-images-client-error-propagates": (["a", "c"], ["a", "c"]),
}
BUG_144_CASES = {k for k, v in DIVERGES.items() if v == "BUG-144"}


def test_every_diverging_case_has_an_expected_outcome() -> None:
    assert set(EXPECTED) == set(DIVERGES)
    assert {c.id for c in CASES} >= set(DIVERGES)


@pytest.fixture
def debug_logs(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)


@pytest.mark.parametrize("case_id", sorted(DIVERGES))
@pytest.mark.parametrize("path", [ADAPTER, CLEANER])
def test_diverging_case_has_the_fixed_outcome(
    case_id: str,
    path: str,
    debug_logs: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    case = next(c for c in CASES if c.id == case_id)
    old = _run(_legacy, case, monkeypatch, caplog, capsys)
    new = (
        _run(_new, case, monkeypatch, caplog, capsys)
        if path == ADAPTER
        else _run_cleaner(case, monkeypatch, caplog, capsys)
    )
    assert old.error is not None, "oracle no longer shows the bug"
    assert new.error is None
    assert new.deleted == EXPECTED[case_id][0 if path == ADAPTER else 1]
    assert new.count == len(new.deleted)
    if case_id not in BUG_144_CASES:
        assert any("skipped snapshot cleanup — error while listing" in r[2] for r in new.logs)


def _ctx(dry_run: bool = False) -> RunContext:
    return RunContext(dry_run=dry_run, operation=Operation.DELETE, options={}, now=NOW)


def snap(snap_id: str, days: float = OLD_ENOUGH, **extra: Any) -> dict[str, Any]:
    return {"SnapshotId": snap_id, "StartTime": NOW - datetime.timedelta(days=days), **extra}


class Ec2:
    def __init__(self, snaps: Any, images: Any = ()) -> None:
        self.snaps = snaps
        self.images = images
        self.calls: list[tuple[str, Any]] = []

    def describe_snapshots(self, *, OwnerIds: Sequence[str]) -> Any:
        self.calls.append(("describe_snapshots", tuple(OwnerIds)))
        if isinstance(self.snaps, Exception):
            raise self.snaps
        return {"Snapshots": self.snaps}

    def describe_images(self, *, Owners: Sequence[str]) -> Any:
        self.calls.append(("describe_images", tuple(Owners)))
        return {"Images": self.images}

    def delete_snapshot(self, *, SnapshotId: str) -> Any:
        self.calls.append(("delete_snapshot", SnapshotId))
        return {}


def cleaner_for(clients: dict[str, Ec2], exception_tags: Any = None) -> SnapshotCleaner:
    def factory(region: str) -> SnapshotClient:
        client: SnapshotClient = clients[region]
        return client

    return SnapshotCleaner(factory, lambda: list(clients), 90, exception_tags)


@pytest.fixture
def run_log() -> Iterator[logger.RunLog]:
    run = logger.begin("aws", "snapshot", "delete", False, {})
    yield run
    logger.finish()


def _failed_regions(run: logger.RunLog) -> list[tuple[str | None, str]]:
    return [(f.region, f.resource_id) for f in run._failures]


def auth_error() -> Exception:
    error: Exception = ClientError({"Error": {"Code": "AuthFailure", "Message": "x"}}, "Op")
    return error


def test_listing_error_is_recorded_and_other_regions_continue(run_log: logger.RunLog) -> None:
    clients = {"r1": Ec2(auth_error()), "r2": Ec2([snap("b")])}
    cleaner = cleaner_for(clients)
    plan = cleaner.plan(_ctx())
    assert [c.id for c in plan.candidates] == ["b"]
    assert _failed_regions(run_log) == [("r1", "-")]
    assert run_log._regions_skipped == 1
    assert run_log._regions == 1
    assert [c for c in clients["r1"].calls if c[0] == "delete_snapshot"] == []


def test_listing_error_in_adapter_keeps_earlier_deletes_and_continues(
    monkeypatch: pytest.MonkeyPatch, run_log: logger.RunLog
) -> None:
    monkeypatch.setattr("crc.service.init_logging", lambda *args, **kwargs: None)
    clients = {"r1": Ec2([snap("a")]), "r2": Ec2(auth_error()), "r3": Ec2([snap("c")])}
    runtime = SnapshotRuntime(
        client_factory=lambda region: clients[region],
        list_regions=lambda: list(clients),
        clock=lambda: NOW,
    )
    adapter = Snapshot(False, 90, None, runtime)
    adapter.delete()
    assert adapter.get_deleted == ["a", "c"]
    assert _failed_regions(run_log) == [("r2", "-")]
    assert run_log._regions_skipped == 1


def test_connectivity_error_is_still_skipped_without_a_failure(run_log: logger.RunLog) -> None:
    error: Exception = EndpointConnectionError(endpoint_url="https://ec2.example")
    cleaner = cleaner_for({"r1": Ec2(error), "r2": Ec2([snap("b")])})
    plan = cleaner.plan(_ctx())
    assert [c.id for c in plan.candidates] == ["b"]
    assert _failed_regions(run_log) == []
    assert run_log._regions_skipped == 1


def test_failed_region_snapshot_is_kept_in_a_dry_run() -> None:
    clients = {"r1": Ec2([snap("a"), {"SnapshotId": "b"}]), "r2": Ec2([snap("c")])}
    plan = cleaner_for(clients).plan(_ctx(dry_run=True))
    assert [c.id for c in plan.candidates] == ["c"]


@pytest.mark.parametrize(
    "tags",
    [
        [{"Key": "k"}],
        [{"Value": "v"}],
        [{}],
        [{"Key": "k"}, {"Value": "v"}, {"Key": "keep2", "Value": "x"}],
    ],
)
def test_malformed_tag_entries_are_tolerated(tags: list[dict[str, str]]) -> None:
    clients = {"r1": Ec2([snap("a", Tags=tags), snap("b")])}
    plan = cleaner_for(clients, {"keep": []}).plan(_ctx())
    assert [c.id for c in plan.candidates] == ["a", "b"]


def test_missing_value_reads_as_empty_string() -> None:
    tags = [{"Key": "env"}]
    clients = {"r1": Ec2([snap("a", Tags=tags), snap("b", Tags=[{"Key": "env", "Value": "x"}])])}
    plan = cleaner_for(clients, {"env": [""]}).plan(_ctx())
    assert [c.id for c in plan.candidates] == ["b"]


def test_key_only_tag_still_protects_when_any_value_is_listed() -> None:
    clients = {"r1": Ec2([snap("a", Tags=[{"Key": "keep"}, {"Value": "junk"}])])}
    assert cleaner_for(clients, {"keep": []}).plan(_ctx()).candidates == ()


def test_malformed_tags_on_a_young_snapshot_are_read_and_kept() -> None:
    clients = {"r1": Ec2([snap("y", 1, Tags=[{"Key": "k"}]), snap("a")])}
    plan = cleaner_for(clients, {"keep": []}).plan(_ctx())
    assert [c.id for c in plan.candidates] == ["a"]


def test_protected_snapshot_with_a_malformed_sibling_tag_is_kept() -> None:
    tags = [{"Key": "autoclean"}, {"Value": "x"}, {"Key": "autoclean2", "Value": "false"}]
    clients = {"r1": Ec2([snap("a", Tags=tags)])}
    spec = {"autoclean": ["false", "False", "FALSE"], "autoclean2": ["false"]}
    assert cleaner_for(clients, spec).plan(_ctx()).candidates == ()


@pytest.mark.parametrize("case_id", sorted(DIVERGES))
def test_oracle_still_shows_the_bug(
    case_id: str,
    debug_logs: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    case = next(c for c in CASES if c.id == case_id)
    old = _run(_legacy, case, monkeypatch, caplog, capsys)
    assert old.error is not None


@pytest.mark.parametrize(
    ("tags", "exception_tags", "expected"),
    [
        ([{"Key": "k"}], {"keep": []}, False),
        ([{"Value": "v"}], {"keep": []}, False),
        ([{"Value": "v"}, {"Key": "keep"}], {"keep": []}, True),
        ([{"Key": "env"}], {"env": [""]}, True),
        ([{"Key": "env"}], {"env": ["prod"]}, False),
    ],
)
def test_is_protected_tolerates_malformed_entries(
    tags: Any,
    exception_tags: Any,
    expected: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("crc.service.init_logging", lambda *args, **kwargs: None)
    assert Snapshot(False, 90, exception_tags)._is_protected(tags, "snap-1") is expected
