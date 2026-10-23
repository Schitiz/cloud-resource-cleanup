"""OCI route table: `disk` and `vm` (delete and stop) run through `crc.core.engine`.

`spot_instances` stays on the legacy handler: under `--cloud all` it only warns and returns
(SAF-037), and `Route.precheck` can raise but cannot skip a pair (see `crc/cli/README.md`).
"""

from typing import Any

import crc.oci.disk
import crc.oci.vm  # noqa: F401
from crc.cli.inputs import Options
from crc.cli.routes import NotifyMode, Route


def _disk(options: Options) -> dict[str, Any]:
    return {
        "filter_tags": options.filter_tags,
        "exception_tags": options.exception_tags,
        "notags": options.notags,
        "age": options.age,
        "custom_age_tag_key": options.custom_age_tag_key,
    }


def _vm(options: Options) -> dict[str, Any]:
    """The legacy handler passed the states to delete only (stop used the cleaner default)."""
    values: dict[str, Any] = {
        "filter_tags": options.filter_tags,
        "exception_tags": options.exception_tags,
        "notags": options.notags,
        "age": options.age,
        "custom_age_tag_key": options.custom_age_tag_key,
    }
    if options.operation_type != "stop" and options.resource_states:
        values["instance_state"] = options.resource_states
    return values


ROUTES: dict[str, Route] = {
    "disk": Route(_disk, notify=NotifyMode.REPORT_THEN_RERAISE),
    "vm": Route(_vm),
}
