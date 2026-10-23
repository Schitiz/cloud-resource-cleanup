"""Route tables: which (cloud, kind) pairs the CLI runs through `crc.core.engine`.

One module per cloud (`aws`, `azu`, `gcp`, `oci`) holds `ROUTES`, a dict from resource kind to a
`Route`. A kind that is not in its cloud's table keeps the legacy `CRC` handler of
`crc/cli/dispatch.py`. The dispatcher asks `route_for` before it looks up the legacy handler.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from crc.cli.inputs import Options, Targets

__all__ = ["OptionsBuilder", "Precheck", "Route"]

OptionsBuilder = Callable[[Options], dict[str, Any]]
Precheck = Callable[[Any, Options, Targets], None]


@dataclass(frozen=True, slots=True)
class Route:
    """How one engine-routed kind is run.

    `options` maps the parsed flags to the `RunContext.options` of the registered cleaner (raw
    flag values, as the legacy handler passed them). `notify` False sends no Slack and no Influx
    (`vpc`, BUG-084). `precheck` runs between RUN START and the cleaner, for gates that
    the legacy handler raised itself (the AWS disk opt-in).
    """

    options: OptionsBuilder
    notify: bool = True
    precheck: Precheck | None = None
