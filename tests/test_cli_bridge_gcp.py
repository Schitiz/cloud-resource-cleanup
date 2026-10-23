"""Parity: the engine bridge against the legacy handlers for the GCP kinds routed in ENG-GCP.

Each case builds the same fake GCP client data twice, runs `dispatch._run_handler` once on the
legacy handler (the adapter classes behind `CRC`) and once through the route, with the same fake
Slack and Influx clients, and requires equal run-log lines (RUN START, REGION, ACTION, SKIPPED,
ERRORS, RESULT), Slack calls (text and recipients), Influx points, console output, error and the
GCP calls made. `ENG-1` round 1 found two differences its tests missed (names versus ids in a
dry run, missing per-region ACTION lines): the dry run cases here compare both.
"""

from collections.abc import Callable
from typing import Any

import pytest

from crc.cli import bridge
from tests.helpers_gcp_bridge import (
    FakeGcp,
    Outcome,
    address,
    disk,
    instance,
    run_pair,
)

TAGS = {"k": ["v"]}
AGE = {"days": 1}
BASE: dict[str, Any] = {"slack_channel": "chan", "influxdb": {"bucket": "b"}}


def ips() -> FakeGcp:
    return FakeGcp(
        {
            "r1": [address("a-1"), address("a-2"), address("b-1"), address("a-used", "IN_USE")],
            "r2": [address("a-3"), address("x-a-4")],
        }
    )


def disks() -> FakeGcp:
    return FakeGcp(
        {
            "z1": [
                disk("d1", labels={"owner": "alice@yugabyte.com"}),
                disk("d2", users=["vm"]),
                disk("d3"),
            ],
            "z2": [disk("d4", labels={"owner": "alice@yugabyte.com"}), disk("e5")],
        }
    )


def vms() -> FakeGcp:
    return FakeGcp(
        {
            "z1": [instance("vm1"), instance("vm2", created="2999-01-01T00:00:00.000000+00:00")],
            "z2": [instance("vm3"), instance("vm4", status="TERMINATED")],
        }
    )


CASES: dict[str, tuple[str, dict[str, Any], Callable[[], FakeGcp]]] = {
    "ip": ("ip", {"name_regex": ["a-"], "exception_regex": ["x-"]}, ips),
    "ip-match-all": ("ip", {}, ips),
    "disk": ("disk", {"name_regex": ["d"], "detach_age": AGE}, disks),
    "disk-owners": (
        "disk",
        {"detach_age": AGE, "slack_notify_users": True, "slack_user_label": "owner"},
        disks,
    ),
    "disk-excluded": ("disk", {"detach_age": AGE, "exception_regex": ["d"]}, disks),
    "vm-delete": ("vm", {"age": AGE, "filter_tags": TAGS, "operation_type": "delete"}, vms),
    "vm-delete-states": (
        "vm",
        {"age": AGE, "operation_type": "delete", "resource_states": ["TERMINATED", "RUNNING"]},
        vms,
    ),
    "vm-stop": ("vm", {"age": AGE, "filter_tags": TAGS, "operation_type": "stop"}, vms),
    "vm-nothing": (
        "vm",
        {"age": AGE, "filter_tags": {"other": ["v"]}, "operation_type": "delete"},
        vms,
    ),
}


def run_both(  # noqa: PLR0913 - the case, the three switches and the data hook
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    case: str,
    *,
    dry_run: bool,
    slack: bool,
    influx: bool,
    prepare: Callable[[FakeGcp], None] = lambda client: None,
) -> tuple[Outcome, Outcome]:
    kind, flags, make = CASES[case]
    outcomes = []
    for routed in (False, True):
        client = make()
        prepare(client)
        outcomes.append(
            run_pair(
                monkeypatch,
                caplog,
                kind,
                {**BASE, **flags, "dry_run": dry_run},
                client,
                routed=routed,
                slack=slack,
                influx=influx,
            )
        )
    return outcomes[0], outcomes[1]


def by_kind(lines: list[str]) -> dict[str, list[str]]:
    kinds: dict[str, list[str]] = {}
    for line in lines:
        kinds.setdefault(line.split(" ")[0], []).append(line)
    return kinds


def assert_equal(old: Outcome, new: Outcome) -> None:
    """The routed run lists every region before it logs ACTION lines (BUG-400, and `plan()` of
    the Cleaners logs a dry run's ACTION lines after its REGION lines), so the REGION and ACTION
    lines are compared per kind, each in order; every other line keeps its place."""
    assert by_kind(new.run_log) == by_kind(old.run_log)
    assert (new.run_log[0], new.run_log[-1]) == (old.run_log[0], old.run_log[-1])
    assert new.slack == old.slack
    assert new.influx == old.influx
    assert new.stdout == old.stdout
    assert new.error == old.error


@pytest.mark.parametrize("influx", [False, True], ids=["no-influx", "influx"])
@pytest.mark.parametrize("slack", [False, True], ids=["no-slack", "slack"])
@pytest.mark.parametrize("dry_run", [False, True], ids=["real", "dry"])
@pytest.mark.parametrize("case", list(CASES))
def test_routed_run_equals_legacy_handler(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    case: str,
    dry_run: bool,
    slack: bool,
    influx: bool,
) -> None:
    old, new = run_both(monkeypatch, caplog, case, dry_run=dry_run, slack=slack, influx=influx)
    assert_equal(old, new)
    assert old.run_log and old.run_log[0].startswith("RUN START")
    assert old.run_log[-1].startswith("RESULT")
    if slack:
        assert old.slack
    if influx:
        assert old.influx
    if dry_run:
        assert not [c for c in new.gcp_calls if c[0].startswith(("delete", "stop"))]
        assert any(line.startswith("ACTION") for line in old.run_log) == (
            case != "vm-nothing"
        )
        assert new.gcp_calls == old.gcp_calls
    else:
        assert sorted(new.gcp_calls) == sorted(old.gcp_calls)


@pytest.mark.parametrize("dry_run", [False, True], ids=["real", "dry"])
@pytest.mark.parametrize("case", ["ip", "disk", "vm-delete", "vm-stop"])
def test_one_failed_delete_is_recorded_and_the_run_goes_on(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    case: str,
    dry_run: bool,
) -> None:
    fail = {"ip": "a-2", "disk": "d1", "vm-delete": "vm1", "vm-stop": "vm1"}[case]

    def prepare(client: FakeGcp) -> None:
        client.fail_delete = fail

    old, new = run_both(
        monkeypatch, caplog, case, dry_run=dry_run, slack=True, influx=True, prepare=prepare
    )
    assert_equal(old, new)
    assert old.error is None
    assert dry_run or any(line.startswith("ERRORS") for line in old.run_log)


@pytest.mark.parametrize("dry_run", [False, True], ids=["real", "dry"])
@pytest.mark.parametrize("case", ["ip", "disk", "vm-delete"])
def test_first_zone_listing_error_gives_the_same_run(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    case: str,
    dry_run: bool,
) -> None:
    def prepare(client: FakeGcp) -> None:
        client.fail_list = next(iter(client.data))

    old, new = run_both(
        monkeypatch, caplog, case, dry_run=dry_run, slack=True, influx=True, prepare=prepare
    )
    assert_equal(old, new)


@pytest.mark.parametrize("dry_run", [False, True], ids=["real", "dry"])
@pytest.mark.parametrize("case", ["ip", "disk", "vm-delete", "vm-stop"])
def test_project_listing_error_raises_the_same_error_after_the_same_report(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    case: str,
    dry_run: bool,
) -> None:
    """`disk` reports (an empty list) before it raises, as `delete_disks` did; the others raise
    without a Slack or Influx message."""

    def prepare(client: FakeGcp) -> None:
        client.fail_zones = True

    old, new = run_both(
        monkeypatch, caplog, case, dry_run=dry_run, slack=True, influx=True, prepare=prepare
    )
    assert_equal(old, new)
    assert old.error is not None
    assert bool(old.slack) == (case == "disk")


@pytest.mark.parametrize("case", ["ip", "disk", "vm-delete"])
def test_later_listing_error_deletes_fewer_never_more(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, case: str
) -> None:
    """The one allowed difference (BUG-400): `plan()` lists every region before any delete."""

    def prepare(client: FakeGcp) -> None:
        client.fail_list = list(client.data)[-1]

    old, new = run_both(
        monkeypatch, caplog, case, dry_run=False, slack=False, influx=False, prepare=prepare
    )
    deletes = ("delete_address", "delete_disk", "delete_instance")
    old_deleted = [c for c in old.gcp_calls if c[0] in deletes]
    new_deleted = [c for c in new.gcp_calls if c[0] in deletes]
    assert set(new_deleted) <= set(old_deleted)
    assert len(new_deleted) <= len(old_deleted)


def test_route_table_routes_the_kinds_and_leaves_spot_instances_legacy() -> None:
    assert sorted(bridge.TABLES["gcp"]) == ["disk", "ip", "vm"]
    assert bridge.route_for("gcp", "spot_instances") is None
