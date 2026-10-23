"""The legacy per-resource handlers of `crc/cli/dispatch.py`, kept for the parity tests only.

Production routes every pair through `crc.cli.bridge` (the two warn-only pairs have skip-only
routes). The parity tests still drive the legacy side with the current `CRC` through these
handlers until they are retargeted to the frozen oracle `tests/legacy/crc_main.txt`
(`tests.helpers_oracle.load_legacy_crc`); see docs/archive/reviews/CLEAN-1.md.
"""

import logging
from collections.abc import Callable
from typing import Any

from crc.cli.dispatch import _run_options
from crc.cli.inputs import Options, Targets
from crc.core import logger

_LOG = logging.getLogger("crc.cli.dispatch")

Handler = Callable[[Any, Any, Options, Targets], None]


def _disk(crc: Any, cloud: Any, options: Options, targets: Targets) -> None:
    """Azure, GCP and OCI disks; AWS disks run through the engine (`Route.precheck` is the gate)."""
    crc.delete_disks(
        options.filter_tags,
        options.exception_tags,
        options.age,
        options.custom_age_tag_key,
        options.detach_age,
        options.name_regex,
        options.exception_regex,
        options.slack_notify_users,
        options.slack_user_label,
    )


def _ip(crc: Any, cloud: Any, options: Options, targets: Targets) -> None:
    crc.delete_ip(
        options.filter_tags,
        options.exception_tags,
        options.name_regex,
        options.exception_regex,
    )


def _nic(crc: Any, cloud: Any, options: Options, targets: Targets) -> None:
    crc.delete_nic(options.name_regex, options.exception_regex)


def _vm(crc: Any, cloud: Any, options: Options, targets: Targets) -> None:
    if options.operation_type == "delete":
        crc.delete_vm(
            options.filter_tags,
            options.exception_tags,
            options.age,
            options.custom_age_tag_key,
            options.resource_states,
        )
    elif options.operation_type == "stop":
        crc.stop_vm(
            options.filter_tags,
            options.exception_tags,
            options.age,
            options.custom_age_tag_key,
        )


def _spot_instance_requests(crc: Any, cloud: Any, options: Options, targets: Targets) -> None:
    """Non-AWS clouds only warn; AWS spot instance requests run through the engine."""
    _LOG.warning(
        "spot_instance_requests is AWS-only; skipped for %s (use --resource spot_instances)",
        crc.cloud,
    )


def _spot_instances(crc: Any, cloud: Any, options: Options, targets: Targets) -> None:
    if crc.cloud == "aws":
        _LOG.warning(
            "For AWS use --resource spot_instance_requests "
            "(cancel request before terminate). Skipping spot_instances."
        )
        return
    if crc.cloud in ("gcp", "oci") and targets.cloud_arg == "all":
        _LOG.warning(
            "GCP/OCI spot_instances require explicit --cloud %s "
            "(not --cloud all); skipped. Azure spot_instances still runs "
            "under --cloud all for backward compatibility.",
            crc.cloud,
        )
        return
    # Fail closed: missing --resource_group / --project_id / --age must raise
    # (do not continue into other clouds under --cloud all).
    crc.delete_spot_instances(
        options.filter_tags, options.exception_tags, options.age, options.custom_age_tag_key
    )


HANDLERS: dict[str, Handler] = {
    "disk": _disk,
    "ip": _ip,
    "nic": _nic,
    "vm": _vm,
    "spot_instance_requests": _spot_instance_requests,
    "spot_instances": _spot_instances,
}


def run_legacy_handler(
    crc: Any, cloud: Any, resource: Any, options: Options, targets: Targets
) -> None:
    """One cloud and resource pass on the legacy handler, between RUN START and RESULT."""
    logger.begin(
        str(cloud),
        str(resource),
        str(options.operation_type or "delete"),
        bool(options.dry_run),
        _run_options(options),
    )
    try:
        handler = HANDLERS.get(resource)
        if handler is not None:
            handler(crc, cloud, options, targets)
    finally:
        logger.finish()
