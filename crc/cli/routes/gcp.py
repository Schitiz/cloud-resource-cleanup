"""GCP route table: the kinds run through `crc.core.engine`.

`spot_instances` is not routed: the legacy handler warns and skips the pair under `--cloud all`
(GCP and OCI spot VMs need an explicit cloud), and a `Route` can neither skip a pair nor run
between the pair check and the cleaner, so a route would delete under `--cloud all`.
"""

from typing import Any

import crc.gcp.disk_cleaner
import crc.gcp.ip_cleaner
import crc.gcp.vm_cleaner  # noqa: F401
from crc.cli.inputs import Options
from crc.cli.routes import NotifyMode, Route


def _ip(options: Options) -> dict[str, Any]:
    return {
        "project_id": options.project_id,
        "name_regex": options.name_regex,
        "exception_regex": options.exception_regex,
    }


def _disk(options: Options) -> dict[str, Any]:
    return {
        "project_id": options.project_id,
        "filter_tags": options.filter_tags,
        "exception_tags": options.exception_tags,
        "notags": options.notags,
        "name_regex": options.name_regex,
        "exception_regex": options.exception_regex,
        "custom_age_tag_key": options.custom_age_tag_key,
        "age": options.age,
        "detach_age": options.detach_age,
        "slack_notify_users": options.slack_notify_users,
        "slack_user_label": options.slack_user_label,
    }


def _vm(options: Options) -> dict[str, Any]:
    """The legacy handler passed the states to delete only (stop used the cleaner default)."""
    values: dict[str, Any] = {
        "project_id": options.project_id,
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
    "ip": Route(_ip),
    "disk": Route(_disk, notify=NotifyMode.REPORT_THEN_RERAISE),
    "vm": Route(_vm),
}
