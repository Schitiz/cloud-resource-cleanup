"""build_selection: every branch, compared with what `crc.py main()` runs and raises."""

import importlib.util
import logging
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from crc.core.cleaner import Operation
from crc.core.selection import CLOUDS, RESOURCES, Selection, SelectionOptions, build_selection

ROOT = Path(__file__).resolve().parent.parent
KMS_OPTIONS = SelectionOptions(kms_key_description="desc", kms_user="arn:user")
EBS_MESSAGE = "AWS EBS volume cleanup requires '--cloud aws --resource disk'"

METHOD_KINDS = {
    "delete_disks": "disk",
    "delete_ip": "ip",
    "delete_keypairs": "keypair",
    "delete_nic": "nic",
    "delete_vm": "vm",
    "stop_vm": "vm",
    "delete_vpc": "vpc",
    "delete_kms": "kms",
    "delete_spot_instance_requests": "spot_instance_requests",
    "delete_spot_instances": "spot_instances",
}


@pytest.fixture
def crc_cli() -> Iterator[ModuleType]:
    spec = importlib.util.spec_from_file_location("crc_cli_selection", ROOT / "crc.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["crc_cli_selection"] = module
    spec.loader.exec_module(module)
    yield module
    del sys.modules["crc_cli_selection"]


def run_crc_main(
    crc_cli: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    cloud: str,
    resource: str,
    operation: str,
    options: dict[str, Any],
) -> list[tuple[str, str]]:
    """Run crc.py main() with a recording CRC; return the (cloud, kind) pairs it reached."""
    calls: list[tuple[str, str]] = []

    class FakeCRC:
        def __init__(self, cloud: str, *args: Any, **kwargs: Any) -> None:
            self.cloud = cloud

        def __getattr__(self, name: str) -> Any:
            kind = METHOD_KINDS[name]

            def record(*args: Any, **kwargs: Any) -> None:
                calls.append((self.cloud, kind))

            return record

    class FakeSnapshot:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.age_days = 90
            self.delete_count = 0
            self.get_deleted: list[str] = []

        def delete(self) -> None:
            calls.append((calls[-1][0] if calls else "?", "snapshot"))

    args = dict.fromkeys(
        ["project_id", "resource_states", "filter_tags", "exception_tags", "name_regex",
         "exception_regex", "age", "custom_age_tag_key", "max_age", "detach_age", "notags",
         "slack_channel", "slack_notify_users", "slack_user_label", "influxdb",
         "kms_pending_window", "kms_key_description", "kms_user", "resource_group", "scan_tag"]
    )
    args.update(cloud=cloud, resource=resource, operation_type=operation, dry_run=True)
    args.update(options)
    monkeypatch.setattr(crc_cli, "get_argparser", lambda: args)
    monkeypatch.setattr(crc_cli, "CRC", FakeCRC)
    monkeypatch.setattr(crc_cli, "Snapshot", FakeSnapshot)
    crc_cli.main()
    return calls


# (cloud, resource, operation, options, expected items, expected warning substrings)
OK_CASES: list[tuple[str, str, Operation, SelectionOptions | None, list[tuple[str, str]], int]] = [
    ("aws", "disk", Operation.DELETE, None, [("aws", "disk")], 0),
    ("azure", "disk", Operation.DELETE, None, [("azure", "disk")], 0),
    ("gcp", "disk", Operation.DELETE, None, [("gcp", "disk")], 0),
    ("oci", "disk", Operation.DELETE, None, [("oci", "disk")], 0),
    ("aws", "ip", Operation.DELETE, None, [("aws", "ip")], 0),
    ("azure", "keypair", Operation.DELETE, None, [("azure", "keypair")], 0),
    ("aws", "nic", Operation.DELETE, None, [("aws", "nic")], 0),
    ("aws", "vpc", Operation.DELETE, None, [("aws", "vpc")], 0),
    ("aws", "snapshot", Operation.DELETE, None, [("aws", "snapshot")], 0),
    ("azure", "snapshot", Operation.DELETE, None, [("azure", "snapshot")], 0),
    ("aws", "vm", Operation.DELETE, None, [("aws", "vm")], 0),
    ("gcp", "vm", Operation.STOP, None, [("gcp", "vm")], 0),
    ("aws", "kms", Operation.DELETE, KMS_OPTIONS, [("aws", "kms")], 0),
    ("azure", "kms", Operation.DELETE, KMS_OPTIONS, [("azure", "kms")], 0),
    ("aws", "spot_instance_requests", Operation.DELETE, None,
     [("aws", "spot_instance_requests")], 0),
    ("azure", "spot_instance_requests", Operation.DELETE, None, [], 1),
    ("gcp", "spot_instance_requests", Operation.DELETE, None, [], 1),
    ("oci", "spot_instance_requests", Operation.DELETE, None, [], 1),
    ("aws", "spot_instances", Operation.DELETE, None, [], 1),
    ("azure", "spot_instances", Operation.DELETE, None, [("azure", "spot_instances")], 0),
    ("gcp", "spot_instances", Operation.DELETE, None, [("gcp", "spot_instances")], 0),
    ("oci", "spot_instances", Operation.DELETE, None, [("oci", "spot_instances")], 0),
    ("all", "vm", Operation.DELETE, None, [(c, "vm") for c in CLOUDS], 0),
    ("all", "vm", Operation.STOP, None, [(c, "vm") for c in CLOUDS], 0),
    ("all", "ip", Operation.DELETE, None, [(c, "ip") for c in CLOUDS], 0),
    ("all", "snapshot", Operation.DELETE, None, [(c, "snapshot") for c in CLOUDS], 0),
    ("all", "keypair", Operation.DELETE, None, [(c, "keypair") for c in CLOUDS], 0),
    ("all", "kms", Operation.DELETE, KMS_OPTIONS, [(c, "kms") for c in CLOUDS], 0),
    ("all", "spot_instance_requests", Operation.DELETE, None,
     [("aws", "spot_instance_requests")], 3),
    ("all", "spot_instances", Operation.DELETE, None, [("azure", "spot_instances")], 3),
    ("aws", "vm", Operation.DELETE, SelectionOptions(slack_notify_users=True,
                                                     slack_user_label="owner"),
     [("aws", "vm")], 0),
]


@pytest.mark.parametrize("case", OK_CASES)
def test_build_selection_matches_crc_main(
    crc_cli: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    case: tuple[str, str, Operation, SelectionOptions | None, list[tuple[str, str]], int],
    caplog: pytest.LogCaptureFixture,
) -> None:
    cloud, resource, operation, options, expected, warns = case
    selection = build_selection(cloud, resource, operation, options)
    assert list(selection.items) == expected
    assert len(selection.warnings) == warns
    extra: dict[str, Any] = {}
    if options is not None:
        extra = {
            "kms_key_description": options.kms_key_description,
            "kms_user": options.kms_user,
            "slack_notify_users": options.slack_notify_users,
            "slack_user_label": options.slack_user_label,
        }
    with caplog.at_level(logging.WARNING):
        reached = run_crc_main(crc_cli, monkeypatch, cloud, resource, operation.value, extra)
    if resource == "snapshot":
        # crc.py runs the AWS-only Snapshot class for every cloud; the fake cannot tell the cloud
        assert [kind for _, kind in reached] == [kind for _, kind in expected]
    else:
        assert reached == expected
    logged = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert logged == list(selection.warnings)


ERROR_CASES: list[tuple[str, str, Operation, SelectionOptions | None, str]] = [
    ("aws", "all", Operation.DELETE, KMS_OPTIONS,
     "All Resources cleanup is supported only with all Clouds. "
     "Format: --cloud all --resources all"),
    ("azure", "all", Operation.DELETE, KMS_OPTIONS, "All Resources cleanup is supported only"),
    ("aws", "disk", Operation.STOP, None, "Stop is supported only for vm resource"),
    ("all", "all", Operation.STOP, KMS_OPTIONS, "Stop is supported only for vm resource"),
    ("aws", "ip", Operation.STOP, None, "Stop is supported only for vm resource"),
    ("aws", "vm", Operation.DELETE,
     SelectionOptions(slack_notify_users=True), "--slack_user_label is mandatory"),
    ("aws", "kms", Operation.DELETE, None, "Key description string is required"),
    ("aws", "kms", Operation.DELETE, SelectionOptions(kms_user="u"),
     "Key description string is required"),
    ("aws", "kms", Operation.DELETE, SelectionOptions(kms_key_description="d"),
     "Jenkins user ARN is reuired"),
    ("all", "all", Operation.DELETE, None, "Key description string is required"),
    ("all", "all", Operation.DELETE, SelectionOptions(kms_key_description="d"),
     "Jenkins user ARN is reuired"),
    ("all", "all", Operation.DELETE, KMS_OPTIONS, EBS_MESSAGE),
    ("all", "disk", Operation.DELETE, None, EBS_MESSAGE),
]


@pytest.mark.parametrize("case", ERROR_CASES)
def test_build_selection_errors_match_crc_main(
    crc_cli: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    case: tuple[str, str, Operation, SelectionOptions | None, str],
) -> None:
    cloud, resource, operation, options, message = case
    with pytest.raises(ValueError) as ours:
        build_selection(cloud, resource, operation, options)
    extra: dict[str, Any] = {}
    if options is not None:
        extra = {
            "kms_key_description": options.kms_key_description,
            "kms_user": options.kms_user,
            "slack_notify_users": options.slack_notify_users,
            "slack_user_label": options.slack_user_label,
        }
    with pytest.raises(ValueError) as theirs:
        run_crc_main(crc_cli, monkeypatch, cloud, resource, operation.value, extra)
    assert str(ours.value) == str(theirs.value)
    assert message in str(ours.value)


def test_ebs_breaker_selects_nothing_before_raising(
    crc_cli: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, str]] = []
    with pytest.raises(ValueError, match="AWS EBS volume cleanup requires"):
        calls = run_crc_main(crc_cli, monkeypatch, "all", "all", "delete",
                             {"kms_key_description": "d", "kms_user": "u"})
    assert calls == []


def test_all_expansion_order_follows_crc_py(crc_cli: ModuleType) -> None:
    assert list(CLOUDS) == crc_cli.CLOUDS
    assert list(RESOURCES) == crc_cli.RESOURCES


@pytest.mark.parametrize("cloud", ["aws", "azure", "gcp", "oci"])
@pytest.mark.parametrize("resource", ["ip", "vm", "nic", "keypair"])
def test_single_pair(cloud: str, resource: str) -> None:
    assert build_selection(cloud, resource) == Selection(((cloud, resource),))


@pytest.mark.parametrize(
    ("cloud", "resource"), [("bogus", "vm"), ("aws", "bogus"), ("", "vm"), ("aws", "")]
)
def test_unknown_values_raise(cloud: str, resource: str) -> None:
    with pytest.raises(ValueError, match="unknown"):
        build_selection(cloud, resource)


def test_warning_texts_match_crc_py() -> None:
    requests = build_selection("gcp", "spot_instance_requests").warnings
    assert requests == (
        "spot_instance_requests is AWS-only; skipped for gcp (use --resource spot_instances)",
    )
    aws = build_selection("aws", "spot_instances").warnings
    assert aws == (
        "For AWS use --resource spot_instance_requests "
        "(cancel request before terminate). Skipping spot_instances.",
    )
    everything = build_selection("all", "spot_instances").warnings
    assert everything[0] == aws[0]
    assert everything[1].startswith("GCP/OCI spot_instances require explicit --cloud gcp (not")
    assert everything[2].startswith("GCP/OCI spot_instances require explicit --cloud oci (not")
    assert everything[1].endswith("under --cloud all for backward compatibility.")
