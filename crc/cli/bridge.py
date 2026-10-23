"""The bridge from `dispatch` to `crc.core.engine` for the pairs a route table marks as routed.

`route_for(cloud, kind)` reads the route tables in `crc/cli/routes/`. `run_routed` builds the
`RunContext` and `Selection` of one pair and calls `crc.core.engine.run`; the Slack then Influx
notifiers are the ones `crc.py` called after each adapter. `build_registry` and `build_notifiers`
are looked up in this module at call time, the seam the CLI parity tests patch.
"""

from datetime import UTC, datetime
from typing import Any

from crc.cli.inputs import Options, Targets
from crc.cli.routes import Route
from crc.cli.routes import aws as aws_routes
from crc.cli.routes import azu as azu_routes
from crc.cli.routes import gcp as gcp_routes
from crc.cli.routes import oci as oci_routes
from crc.core import engine, registry
from crc.core.cleaner import Operation, RunContext
from crc.core.selection import Selection
from crc.notify.influx import InfluxNotifier
from crc.notify.slack import SlackNotifier

TABLES: dict[str, dict[str, Route]] = {
    "aws": aws_routes.ROUTES,
    "azure": azu_routes.ROUTES,
    "gcp": gcp_routes.ROUTES,
    "oci": oci_routes.ROUTES,
}


def route_for(cloud: Any, kind: Any) -> Route | None:
    """The route of a pair, or None when the pair still runs the legacy handler."""
    return TABLES.get(cloud, {}).get(kind)


def is_routed_kind(kind: Any) -> bool:
    """True when at least one cloud routes `kind`."""
    return any(kind in table for table in TABLES.values())


def build_registry() -> registry.Registry:
    """The registry the cleaners come from (the default one; the route modules registered them)."""
    return registry.DEFAULT_REGISTRY


def build_notifiers(crc: Any, route: Route) -> list[engine.Notifier]:
    """Slack when a client is set, then Influx when a client is set; none for `notify=False`."""
    notifiers: list[engine.Notifier] = []
    if route.notify and crc.slack_client:
        notifiers.append(SlackNotifier(crc.slack_client, crc.slack_channel))
    if route.notify and crc.influxdb_client:
        notifiers.append(InfluxNotifier(crc.influxdb_client, crc))
    return notifiers


def run_routed(
    crc: Any, cloud: Any, kind: Any, options: Options, targets: Targets, route: Route
) -> None:
    """Run one routed pair through the engine: precheck, plan, apply unless dry run, notify."""
    if route.precheck is not None:
        route.precheck(crc, options, targets)
    context = RunContext(
        dry_run=bool(options.dry_run),
        operation=Operation(options.operation_type or "delete"),
        options=route.options(options),
        now=datetime.now(UTC),
    )
    selection = Selection(items=((str(cloud), str(kind)),))
    engine.run(selection, context, build_registry(), build_notifiers(crc, route))
