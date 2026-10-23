"""Parity: the Azure kinds routed through `crc.core.engine` against the legacy `CRC` handlers.

Both sides run the real Azure code on the same fake Azure SDK, through `dispatch._run_pair`
(RUN START and RESULT around the pass): the legacy side with the route lookup switched off (the
`HANDLERS` entry, `CRC` method and adapter), the routed side through `bridge.run_routed` and the
registered cleaner. For every kind, a dry run and a real run, and every Slack and Influx mode, the
run-log lines (RUN START, ACTION, SKIPPED, ERRORS, FAILED, RESULT), the Slack calls and recipients,
the Influx points, the console output and the raised error are equal. The REGION lines are equal as
a set: the cleaner logs them from `plan()` (before the deletes), the adapter after each region.
"""

import logging
import re
from contextlib import redirect_stdout
from datetime import UTC, datetime
from io import StringIO
from typing import Any

import pytest

from crc.cli import bridge
from crc.cli import dispatch as cli_dispatch
from crc.cli.inputs import Targets, read_options
from crc.cli.routes import NotifyMode, skips
from crc.cli.runner import CRC
from crc.core import logger
from tests.helpers_cli_azu import KINDS, Kind
from tests.helpers_legacy_handlers import run_legacy_handler
from tests.test_cli_crc_parity import FULL, Case, Logs, Scenario, build

PREFIXES = ("RUN START", "REGION", "ACTION", "SKIPPED", "ERRORS", "FAILED", "RESULT")
NOW = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
MODES = [
    ("off", "off"),
    ("on", "on"),
    ("post_fail", "write_error"),
    ("on", "api_error"),
    ("no_channel", "on_suffix"),
]


def _flags(kind: Kind, dry_run: bool) -> dict[str, Any]:
    return {
        "cloud": "azure",
        "resource": kind.resource,
        "operation_type": kind.operation,
        "dry_run": dry_run,
        "resource_group": "rg",
        **kind.flags,
    }


ROUTED_RUNS: list[str] = []


def _crc(scenario: Scenario, logs: Logs, options: Any) -> Any:
    """The legacy `CRC` with `notags` and `resource_group` from the flags, as in `cli/main.py`."""
    crc = build(CRC, Case("c", "azure", lambda c: None, scenario), logs)
    crc.notags, crc.resource_group = options.notags, options.resource_group
    return crc


def _run(
    kind: Kind, variant: str, scenario: Scenario, routed: bool, mp: pytest.MonkeyPatch
) -> dict[str, Any]:
    azure = kind.make(variant)
    azure.install(mp)
    logger.finish()
    mp.setattr(bridge, "datetime", type("D", (), {"now": staticmethod(lambda tz=None: NOW)}))
    real_run_routed = bridge.run_routed

    def counting(*args: Any) -> None:
        ROUTED_RUNS.append(kind.resource)
        real_run_routed(*args)

    mp.setattr(cli_dispatch, "run_routed", counting, raising=True)
    logs, out = Logs(), StringIO()
    result: Any = ("ok",)
    records: list[logging.LogRecord] = []

    class Collect(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = Collect()
    root = logging.getLogger()
    root.addHandler(handler)
    old_level = root.level
    root.setLevel(logging.DEBUG)
    flags = _flags(kind, bool(scenario.dry_run))
    options = read_options(flags)
    targets = Targets("azure", False, ["azure"], [kind.resource])
    try:
        with redirect_stdout(out):
            try:
                crc = _crc(scenario, logs, options)
                if routed:
                    cli_dispatch._run_pair(crc, "azure", kind.resource, options, targets)
                else:
                    run_legacy_handler(crc, "azure", kind.resource, options, targets)
            except Exception as exc:
                result = ("error", type(exc).__name__, str(exc))
    finally:
        root.removeHandler(handler)
        root.setLevel(old_level)
        logger.finish()
    lines = [r.getMessage() for r in records if r.getMessage().startswith(PREFIXES)]
    lines = [re.sub(r"(seconds|duration_s)=\d+", r"\1=S", line) for line in lines]
    console_logs = [
        (r.levelno, r.getMessage())
        for r in records
        if r.levelno >= logging.INFO and not r.getMessage().startswith(PREFIXES)
    ]
    mutating = [c for c in azure.calls if any(w in str(c[0]) for w in ("delete", "dealloc"))]
    return {
        "result": result,
        "slack": logs.slack,
        "influx": logs.influx,
        "stdout": out.getvalue(),
        "logs": console_logs,
        "ordered": [x for x in lines if not x.startswith("REGION")],
        "regions": sorted(x for x in lines if x.startswith("REGION")),
        "mutations": mutating,
    }


PARAMS = [
    pytest.param(
        kind,
        variant,
        dry,
        slack,
        influx,
        id=f"{kind.resource}-{kind.operation}-{variant}-dry{int(dry)}-{slack}-{influx}",
    )
    for kind in KINDS
    for variant in kind.variants
    for dry in (False, True)
    for slack, influx in MODES
]


@pytest.mark.parametrize(("kind", "variant", "dry", "slack", "influx"), PARAMS)
def test_routed_azure_pair_matches_the_legacy_handler(
    kind: Kind, variant: str, dry: bool, slack: str, influx: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = Scenario(dict(FULL), dry_run=dry, slack=slack, influx=influx)
    ROUTED_RUNS.clear()
    with monkeypatch.context() as legacy_patch:
        old = _run(kind, variant, scenario, False, legacy_patch)
    assert ROUTED_RUNS == []
    with monkeypatch.context() as routed_patch:
        new = _run(kind, variant, scenario, True, routed_patch)
    assert [kind.resource] == ROUTED_RUNS
    assert new == old
    assert old["ordered"][0].startswith("RUN START")
    assert old["ordered"][-1].startswith("RESULT")
    if variant == "plain":
        assert any(x.startswith("ACTION") for x in old["ordered"])
    if variant == "plain" and slack == "on":
        assert old["slack"]
    if variant == "plain" and influx == "on":
        assert old["influx"]


def test_every_azure_route_is_covered_and_notifies_as_the_legacy_handler() -> None:
    table = {k: r for k, r in bridge.TABLES["azure"].items() if r.options is not skips.no_options}
    assert {k.resource for k in KINDS} == set(table)
    assert set(bridge.TABLES["azure"]) - set(table) == {"spot_instance_requests"}
    modes = {kind: route.notify for kind, route in table.items()}
    assert modes.pop("disk") is NotifyMode.REPORT_THEN_RERAISE
    assert set(modes.values()) == {NotifyMode.REPORT}


def test_spot_without_a_resource_group_raises_before_the_cleaner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kind = next(k for k in KINDS if k.resource == "spot_instances")
    flags = {**_flags(kind, True), "resource_group": None}
    route = bridge.route_for("azure", "spot_instances")
    assert route is not None and route.precheck is not None
    crc = build(CRC, Case("c", "azure", lambda c: None, Scenario(dict(FULL), True)), Logs())
    options = read_options(flags)
    targets = Targets("azure", False, ["azure"], ["spot_instances"])
    with pytest.raises(ValueError, match="resource_group is required for Azure Spot VM cleanup"):
        route.precheck(crc, options, targets)
