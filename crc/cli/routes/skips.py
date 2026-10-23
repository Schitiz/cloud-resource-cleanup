"""Skips of the routes that warn and run nothing, as the legacy spot handlers did."""

import logging

from crc.cli.inputs import Options, Targets

_LOG = logging.getLogger("crc.cli.dispatch")


def explicit_cloud_spot(cloud: str, options: Options, targets: Targets) -> bool:
    """SAF-037: GCP and OCI `spot_instances` need an explicit `--cloud`; skip under `all`."""
    if targets.cloud_arg != "all":
        return False
    _LOG.warning(
        "GCP/OCI spot_instances require explicit --cloud %s "
        "(not --cloud all); skipped. Azure spot_instances still runs "
        "under --cloud all for backward compatibility.",
        cloud,
    )
    return True
