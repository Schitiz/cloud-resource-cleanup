"""The Slack then InfluxDB report that every `CRC` operation runs after its adapter."""

from collections.abc import Callable
from typing import Any

from crc.cli.notify import NotifyMixin


def report_result(
    ops: NotifyMixin,
    resource: Any,
    notify: Callable[[Any], None],
    label: str,
    result_attr: str = "get_deleted",
) -> None:
    """Slack (`notify(resource)`) when a Slack client is set, then Influx (`label` points of
    `resource.<result_attr>`) when an InfluxDB client is set; the attribute is read only then.
    """
    if ops.slack_client:
        notify(resource)
    if ops.influxdb_client:
        ops.write_influxdb(label, getattr(resource, result_attr))
