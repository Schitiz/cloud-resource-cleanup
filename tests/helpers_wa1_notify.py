"""Current-side driver of the notify parity tests (lane WA-1).

`execute_current` runs an action on the objects production reaches the notifications through:
`crc.core.report.get_msg`, `SlackNotifier` (with `crc.notify.slack_owners`) and `InfluxNotifier`.
The legacy side is `tests.helpers_cl2_crc.execute` on `load_legacy_crc()`. Neither side uses the
current `crc.cli.runner.CRC`.
"""

import io
import itertools
from collections.abc import Callable, Iterator, Sized
from contextlib import redirect_stdout
from typing import Any

import pytest

from crc.core.cleaner import Operation
from crc.core.report import Report, Section, get_msg
from crc.notify.influx import InfluxNotifier
from crc.notify.slack import SlackNotifier
from tests.helpers_cl2_crc import (
    INFLUX_MODES,
    SLACK_MODES,
    Case,
    FakeInflux,
    FakeSlack,
    Logs,
    Recorded,
    Scenario,
)

OPERATION_OF_WORD = {"Deleted": Operation.DELETE, "Stopped": Operation.STOP}


class CRC:
    """The settings `bridge` hands to the notifiers: clients, channel and the Influx bucket.

    Named `CRC` on purpose: when `influxdb_conn` is absent the stdout of `InfluxNotifier.write`
    carries "'CRC' object has no attribute 'influxdb_bucket'" (BUG-030), as it does in production.
    """

    def __init__(self, case: Case, logs: Logs) -> None:
        scenario = case.scenario
        self.cloud = case.cloud
        self.dry_run = scenario.dry_run
        self.slack_client = FakeSlack(scenario, logs) if scenario.slack != "off" else None
        self.influxdb_client = FakeInflux(scenario, logs) if scenario.influx != "off" else None
        self.slack_channel = None if scenario.slack == "no_channel" else "chan"
        self.influxdb_bucket: str | None
        self.resource_suffix: str | None
        if scenario.influx == "on_suffix":
            self.influxdb_bucket, self.resource_suffix = "bkt", "sfx"
        elif scenario.influx != "no_conn":
            self.influxdb_bucket = "bkt"
            self.resource_suffix = None

    def slack(self) -> SlackNotifier:
        return SlackNotifier(self.slack_client, self.slack_channel)  # type: ignore[arg-type]

    def influx(self) -> InfluxNotifier:
        return InfluxNotifier(self.influxdb_client, self)


def execute_current(case: Case, act: Callable[[CRC], Any]) -> Recorded:
    """Same record as `helpers_cl2_crc.execute`, with `act` run on the notifier context."""
    logs, out = Logs(), io.StringIO()
    result: Any = None
    with pytest.MonkeyPatch.context(), redirect_stdout(out):
        try:
            result = ("ok", repr(act(CRC(case, logs))))
        except Exception as exc:
            result = ("error", type(exc).__name__, str(exc))
    return {
        "result": result,
        "slack": logs.slack,
        "influx": logs.influx,
        "stdout": out.getvalue(),
    }


def current_get_msg(crc: CRC, resource: str, word: str, ids: Sized) -> str:
    """`crc.core.report.get_msg` for the label and the past-tense word of the legacy call."""
    return get_msg(crc.cloud, resource, OPERATION_OF_WORD[word], ids, crc.dry_run)  # type: ignore[arg-type]


def current_ping(crc: CRC, resource: str, word: str, operated: Any) -> None:
    """`ping_on_slack` through `SlackNotifier.ping_owners`, with the BUG-033 pre-loop of `main`.

    Groups are fetched first and `len()` of every value is taken before the first ping, which
    keeps the call order and the error text for a non-dict or a value without `len()`.
    """
    notifier = crc.slack()
    user_groups = notifier.user_groups()
    for key in operated.keys():  # noqa: SIM118 - AttributeError text of a non-dict
        len(operated[key])
    report = Report(
        crc.cloud,
        OPERATION_OF_WORD[word],
        crc.dry_run,
        (Section(resource, ()),),
        by_owner=operated,
    )
    notifier.ping_owners(report, resource, get_groups=lambda: user_groups)


def scenario_grid(values: dict[str, Any], **overrides: Any) -> Iterator[tuple[str, Scenario]]:
    """Dry run x Slack mode x Influx mode, as the CLI parity grid."""
    for dry, slack, influx in itertools.product([False, True], SLACK_MODES, INFLUX_MODES):
        yield (
            f"dry={dry}-slack={slack}-influx={influx}",
            Scenario(dict(values), dry_run=dry, slack=slack, influx=influx, **overrides),
        )
