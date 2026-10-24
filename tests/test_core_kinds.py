"""The kind table `crc/core/kinds.py` and everything derived from it stays what it was."""

import argparse
import sys
from typing import Any

import pytest

from crc.cli import bridge, constants, pairs
from crc.cli.args import get_argparser
from crc.core import engine, selection
from crc.core.kinds import KINDS, KINDS_BY_NAME, Kind
from crc.core.report import DISK, IP, KEYPAIR, KMS, NIC, SNAPSHOT, SPOT_INSTANCE_REQUEST, VM

CLOUDS = ("aws", "azure", "gcp", "oci")


def _resource_action(monkeypatch: pytest.MonkeyPatch) -> argparse.Action:
    captured: list[argparse.ArgumentParser] = []
    original = argparse.ArgumentParser.parse_args

    def spy(self: argparse.ArgumentParser, *a: Any, **k: Any) -> argparse.Namespace:
        captured.append(self)
        result: argparse.Namespace = original(self, *a, **k)
        return result

    monkeypatch.setattr(sys, "argv", ["crc.py", "--cloud", "aws"])
    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", spy)
    get_argparser()
    return next(a for a in captured[0]._actions if "--resource" in a.option_strings)


def test_names_are_unique() -> None:
    names = [k.name for k in KINDS]
    assert len(names) == len(set(names))
    assert set(KINDS_BY_NAME) == set(names)


def test_parser_choices_keep_their_order(monkeypatch: pytest.MonkeyPatch) -> None:
    assert list(_resource_action(monkeypatch).choices or ()) == [
        "disk",
        "ip",
        "keypair",
        "vm",
        "vpc",
        "kms",
        "nic",
        "spot_instance_requests",
        "spot_instances",
        "snapshot",
        "all",
    ]


def test_expansion_constants_keep_their_order() -> None:
    assert constants.RESOURCES == ["disk", "ip", "keypair", "vm", "kms", "nic", "snapshot"]
    assert selection.RESOURCES == ("disk", "ip", "keypair", "vm", "kms", "nic", "snapshot")
    assert selection.EXTRA_RESOURCES == ("vpc", "spot_instance_requests", "spot_instances")


def test_pair_rules_keep_their_content() -> None:
    assert pairs.SUPPORTED_CLOUDS == {
        "keypair": ("aws",),
        "nic": ("azure",),
        "kms": ("aws",),
        "ip": ("aws", "azure", "gcp"),
        "snapshot": ("aws",),
        "vpc": ("aws",),
    }
    assert set(pairs.AWS_ONLY_RESOURCES) == {"snapshot", "vpc"}


@pytest.mark.parametrize(
    ("cloud", "resource", "message"),
    [
        ("azure", "keypair", "Keypair operation is only supported on AWS."),
        ("gcp", "nic", "NICs operation is only supported on Azure."),
        ("oci", "kms", "KMS operation is only supported on AWS."),
        (
            "oci",
            "ip",
            "Invalid cloud provided: oci. Supported clouds are ['aws', 'azure', 'gcp', 'oci']",
        ),
        ("gcp", "snapshot", "--resource snapshot is AWS-only; use --cloud aws (got --cloud gcp)"),
        ("azure", "vpc", "--resource vpc is AWS-only; use --cloud aws (got --cloud azure)"),
    ],
)
def test_unsupported_pair_messages_are_unchanged(cloud: str, resource: str, message: str) -> None:
    assert not pairs.is_supported_pair(cloud, resource)
    assert pairs._unsupported_message(cloud, resource) == message


def test_report_labels_are_unchanged() -> None:
    assert engine.KIND_LABELS == {
        "disk": DISK,
        "ip": IP,
        "keypair": KEYPAIR,
        "vm": VM,
        "kms": KMS,
        "nic": NIC,
        "snapshot": SNAPSHOT,
        "spot_instance_requests": SPOT_INSTANCE_REQUEST,
        "spot_instances": VM,
        "vpc": "VPC",
    }


def test_explicit_only_is_the_complement_of_all() -> None:
    assert {k.name for k in KINDS if k.explicit_only} == set(selection.EXTRA_RESOURCES)
    assert {k.name for k in KINDS if k.in_all} == set(selection.RESOURCES)


def test_clouds_and_message_are_set_together() -> None:
    with pytest.raises(ValueError, match="set together"):
        Kind("bad", "Bad", clouds=("aws",))
    with pytest.raises(ValueError, match="set together"):
        Kind("bad", "Bad", unsupported="nope")
    with pytest.raises(ValueError, match="every cloud"):
        KINDS_BY_NAME["disk"].unsupported_message("aws", CLOUDS)


def test_every_supported_pair_has_a_route_and_every_route_a_supported_pair() -> None:
    expected = {(c, k.name) for k in KINDS for c in (k.clouds if k.clouds is not None else CLOUDS)}
    routed = {(c, kind) for c, table in bridge.TABLES.items() for kind in table}
    assert set(bridge.TABLES) == set(CLOUDS)
    assert sorted(expected - routed) == [], "supported pair without a route"
    assert sorted(routed - expected) == [], "route of a pair the kind table does not support"


def test_every_routed_kind_is_in_the_table() -> None:
    assert {kind for table in bridge.TABLES.values() for kind in table} <= set(KINDS_BY_NAME)


def test_kind_is_frozen() -> None:
    with pytest.raises(AttributeError):
        KINDS[0].name = "other"  # type: ignore[misc]
