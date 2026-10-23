"""Parity: the engine bridge (`crc.cli.bridge`) against `CRC.delete_keypairs` of main.

The oracle is `tests/legacy/crc_main.txt`. The oracle CRC runs `delete_keypairs` with a fake
adapter; the bridge runs the engine with a fake cleaner that plans and applies the same ids. Both
use the same fake Slack and Influx clients: the Slack calls, the Influx calls, the printed output
and the raised error must be equal, in every Slack and Influx mode and in a dry run.
"""

from contextlib import redirect_stdout
from io import StringIO
from types import ModuleType
from typing import Any

import pytest

from crc.cli import bridge
from crc.cli.inputs import Options, Targets, read_options
from crc.cli.routes import NotifyMode, Route
from crc.cli.runner import CRC as NewCRC
from crc.core.cleaner import Candidate, Cleaner, Operation, Plan, Result, RunContext
from crc.core.registry import Registry
from tests.helpers_cli_routes import provide_legacy_keypairs
from tests.test_cli_crc_parity import (
    AGE,
    FULL,
    Case,
    Logs,
    Scenario,
    build,
    make_fake,
    oracle,
    scenario_grid,
)

provide_legacy_keypairs()

__all__ = ["oracle"]

IDS = ["a", "b"]
ID_SETS = {"two": ["a", "b"], "none": [], "dashed": ["k-1", "k_2"], "one": ["only"]}
OPTIONS = {"name_regex": ["n"], "exception_regex": ["x"], "age": AGE}


class FakeCleaner:
    cloud = "aws"
    kind = "keypair"

    def __init__(self, scenario: Scenario, seen: list[RunContext], ids: list[str]) -> None:
        self.scenario = scenario
        self.seen = seen
        self.ids = ids

    def supports(self, operation: Operation) -> bool:
        return True

    def plan(self, context: RunContext) -> Plan:
        self.seen.append(context)
        if self.scenario.delete_error is not None:
            raise self.scenario.delete_error
        return Plan(candidates=tuple(Candidate(id=i) for i in self.ids))

    def apply(self, plan: Plan, context: RunContext) -> Result:
        return Result(succeeded=tuple(c.id for c in plan.candidates))


def _options(dry_run: bool) -> Options:
    return read_options(
        {
            "cloud": "aws",
            "resource": "keypair",
            "operation_type": "delete",
            "dry_run": dry_run,
            "name_regex": ["n"],
            "exception_regex": ["x"],
            "age": AGE,
        }
    )


def _run(case: Case, run: Any) -> dict[str, Any]:
    logs = Logs()
    out = StringIO()
    result: Any = ("ok",)
    with redirect_stdout(out):
        try:
            run(case, logs)
        except Exception as exc:
            result = ("error", type(exc).__name__, str(exc))
    return {"result": result, "slack": logs.slack, "influx": logs.influx, "stdout": out.getvalue()}


def _legacy(oracle_module: ModuleType, monkeypatch: pytest.MonkeyPatch) -> Any:
    def run(case: Case, logs: Logs) -> None:
        monkeypatch.setattr(
            oracle_module, "KeyPairs", make_fake("KeyPairs", case.scenario, logs), raising=True
        )
        build(oracle_module.CRC, case, logs).delete_keypairs(["n"], ["x"], AGE)

    return run


def _bridged(monkeypatch: pytest.MonkeyPatch, seen: list[RunContext], ids: list[str]) -> Any:
    def run(case: Case, logs: Logs) -> None:
        registry = Registry()
        registry.register("aws", "keypair")(
            lambda context: _as_cleaner(FakeCleaner(case.scenario, seen, ids))
        )
        monkeypatch.setattr(bridge, "init_run_logging", lambda: None)
        monkeypatch.setattr(bridge, "build_registry", lambda: registry)
        crc = build(NewCRC, case, logs)
        route = bridge.route_for("aws", "keypair")
        assert route is not None
        options = _options(bool(case.scenario.dry_run))
        targets = Targets("aws", False, ["aws"], ["keypair"])
        bridge.run_routed(crc, "aws", "keypair", options, targets, route)

    return run


def _as_cleaner(cleaner: FakeCleaner) -> Cleaner:
    return cleaner


CASES = [
    (name, scenario)
    for name, scenario in scenario_grid(FULL)
    if scenario.slack != "off" or scenario.influx != "off"
]
ERROR_CASES = [
    ("delete-error", Scenario(dict(FULL), delete_error=RuntimeError("keypair boom"))),
    ("dry-delete-error", Scenario(dict(FULL), dry_run=True, delete_error=ValueError("bad"))),
]


@pytest.mark.parametrize("id_set", list(ID_SETS))
@pytest.mark.parametrize(("name", "scenario"), [*CASES, *ERROR_CASES], ids=lambda v: str(v)[:60])
def test_bridge_matches_crc_delete_keypairs(
    id_set: str, name: str, scenario: Scenario, oracle: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = ID_SETS[id_set]
    case = Case(name, "aws", lambda crc: None, scenario)
    scenario.values = {**scenario.values, "get_deleted": list(ids)}
    old = _run(case, _legacy(oracle, monkeypatch))
    seen: list[RunContext] = []
    new = _run(case, _bridged(monkeypatch, seen, ids))
    assert new == old
    assert len(seen) == 1
    assert seen[0].dry_run is bool(scenario.dry_run)
    assert dict(seen[0].options) == OPTIONS


def test_bridge_reaches_the_cleaner_with_the_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[RunContext] = []
    init_calls: list[tuple[Any, ...]] = []
    registry = Registry()
    registry.register("aws", "keypair")(
        lambda context: _as_cleaner(FakeCleaner(Scenario({}), seen, IDS))
    )
    monkeypatch.setattr("crc.service.init_logging", lambda *args: init_calls.append(args))
    monkeypatch.setattr(bridge, "build_registry", lambda: registry)
    crc = NewCRC("aws", False, None, None, None)
    route = bridge.route_for("aws", "keypair")
    assert route is not None
    bridge.run_routed(
        crc,
        "aws",
        "keypair",
        _options(False),
        Targets("aws", False, ["aws"], ["keypair"]),
        route,
    )
    assert [dict(c.options) for c in seen] == [OPTIONS]
    assert init_calls == [("logs/crc.log",)]


def test_route_tables_route_the_aws_kinds() -> None:
    assert {cloud: sorted(table) for cloud, table in bridge.TABLES.items()} == {
        "aws": [
            "disk",
            "ip",
            "keypair",
            "kms",
            "snapshot",
            "spot_instance_requests",
            "vm",
            "vpc",
        ],
        "azure": [],
        "gcp": [],
        "oci": [],
    }
    assert bridge.is_routed_kind("keypair")
    assert bridge.is_routed_kind("disk")
    assert not bridge.is_routed_kind("nic")
    assert bridge.route_for("azure", "keypair") is None


def test_notifiers_follow_the_clients_and_the_notify_flag() -> None:
    route = bridge.route_for("aws", "keypair")
    assert route is not None
    silent = NewCRC("aws", False, None, None, None)
    assert bridge.build_notifiers(silent, route) == []
    both = NewCRC("aws", False, None, object(), object(), slack_channel="c", influxdb_conn={})
    assert [n.name for n in bridge.build_notifiers(both, route)] == ["slack", "influx"]
    quiet = Route(route.options, notify=NotifyMode.NONE)
    assert bridge.build_notifiers(both, quiet) == []


def test_every_routed_pair_has_a_registered_cleaner() -> None:
    for cloud, table in bridge.TABLES.items():
        for kind in table:
            assert bridge.build_registry().get(cloud, kind) is not None
