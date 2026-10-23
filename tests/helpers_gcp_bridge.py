"""Fakes and a runner for `tests/test_cli_bridge_gcp.py`: the same GCP data run through the legacy
handler (adapter classes, `crc.cli.runner.CRC`) and through the engine bridge (the Cleaners)."""

import io
import itertools
import logging
import types
from collections.abc import Mapping, Sequence
from contextlib import redirect_stdout
from dataclasses import dataclass, field
from typing import Any

import pytest
from google.api_core.exceptions import GoogleAPIError

from crc.cli import dispatch
from crc.cli.context import RunContext as CliContext
from crc.cli.context import make_crc
from crc.cli.inputs import Targets, read_options
from crc.gcp import _scan
from tests.helpers_legacy_handlers import run_legacy_handler

RUN_PREFIXES = ("RUN START", "ACTION ", "SKIPPED ", "ERRORS ", "FAILED ", "RESULT ", "REGION ")
OLD = "2020-01-01T00:00:00.000000+00:00"
YOUNG = "2999-01-01T00:00:00.000000+00:00"


def disk(name: str, *, users: Sequence[str] = (), labels: Mapping[str, str] | None = None) -> Any:
    return types.SimpleNamespace(
        name=name, users=list(users), labels=dict(labels or {}), last_detach_timestamp=OLD
    )


def instance(
    name: str,
    *,
    status: str = "RUNNING",
    created: str = OLD,
    labels: Mapping[str, str] | None = None,
    spot: bool = False,
    disks: Sequence[Any] = (),
) -> Any:
    return types.SimpleNamespace(
        name=name,
        status=status,
        labels={"k": "v"} if labels is None else dict(labels),
        creation_timestamp=created,
        scheduling=types.SimpleNamespace(preemptible=spot, provisioning_model=None),
        disks=list(disks),
        metadata=None,
    )


def attached_disk(name: str, zone: str = "z1", auto_delete: bool = False) -> Any:
    return types.SimpleNamespace(
        source=f"projects/proj/zones/{zone}/disks/{name}", auto_delete=auto_delete
    )


def address(name: str, status: str = "RESERVED") -> Any:
    return types.SimpleNamespace(name=name, status=status)


@dataclass
class FakeGcp:
    """One fake client of every GCP kind: `data` maps a zone or region to its resources."""

    data: dict[str, list[Any]]
    fail_delete: str | None = None
    fail_list: str | None = None
    fail_zones: bool = False
    fail_close: bool = False
    fail_close_after_delete: bool = False
    calls: list[tuple[str, ...]] = field(default_factory=list)

    def list_zones(self, project_id: str) -> list[dict[str, str]]:
        if self.fail_zones:
            raise PermissionError("zones denied")
        return [{"name": zone} for zone in self.data]

    def list_regions(self, project_id: str) -> list[str]:
        if self.fail_zones:
            raise PermissionError("regions denied")
        return list(self.data)

    def _list(self, kind: str, zone: str) -> list[Any]:
        self.calls.append((kind, zone))
        if zone == self.fail_list:
            raise RuntimeError("listing denied")
        return self.data[zone]

    def list_disks(self, project_id: str, zone: str) -> list[Any]:
        return self._list("list_disks", zone)

    def list_instances(self, project_id: str, zone: str) -> list[Any]:
        return self._list("list_instances", zone)

    def list_addresses(self, project_id: str, region: str) -> list[Any]:
        return self._list("list_addresses", region)

    def _delete(self, kind: str, where: str, name: str) -> dict[str, str]:
        self.calls.append((kind, where, name))
        if name == self.fail_delete:
            raise GoogleAPIError("denied")
        return {"name": f"op-{name}"}

    def delete_disk(self, project_id: str, zone: str, disk: str) -> object:
        return self._delete("delete_disk", zone, disk)

    def delete_instance(self, project_id: str, zone: str, instance: str) -> object:
        return self._delete("delete_instance", zone, instance)

    def stop_instance(self, project_id: str, zone: str, instance: str) -> object:
        return self._delete("stop_instance", zone, instance)

    def delete_address(self, project_id: str, region: str, address: str) -> object:
        self._delete("delete_address", region, address)
        return types.SimpleNamespace(result=lambda: None)

    def get_zone_operation(self, project_id: str, zone: str, operation: str) -> dict[str, str]:
        return {"status": "DONE"}

    def get_operation(self, project_id: str, scope: str, zone: str, name: str) -> dict[str, str]:
        return {"status": "DONE"}

    def get_disk(self, project: str, scope: str, location: str, disk: str) -> dict[str, Any]:
        return {"labels": {}}

    def close(self) -> None:
        if self.fail_close or (
            self.fail_close_after_delete and any(c[0] == "delete_disk" for c in self.calls)
        ):
            raise RuntimeError("close failed")


class FakeSlack:
    def __init__(self, calls: list[Any]) -> None:
        self.calls = calls

    def chat_postMessage(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("chat_postMessage", kwargs))
        return {"ok": True}

    def users_lookupByEmail(self, email: str) -> dict[str, Any]:
        self.calls.append(("users_lookupByEmail", email))
        return {"user": {"id": "U1"}}

    def usergroups_list(self) -> dict[str, Any]:
        self.calls.append(("usergroups_list",))
        return {"usergroups": [{"handle": "team", "id": "G1"}]}

    def conversations_open(self, users: list[str]) -> dict[str, Any]:
        self.calls.append(("conversations_open", users))
        return {"channel": {"id": "D1"}}


class FakeInflux:
    def __init__(self, calls: list[Any]) -> None:
        self.calls = calls

    def write_api(self, write_options: Any = None) -> Any:
        def write(bucket: Any, record: Any) -> None:
            self.calls.append((bucket, record._name, dict(record._tags), dict(record._fields)))

        return types.SimpleNamespace(write=write)


@dataclass(frozen=True)
class Outcome:
    run_log: list[str]
    slack: list[Any]
    influx: list[Any]
    stdout: str
    error: str | None
    gcp_calls: list[tuple[str, ...]]


def _lines(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.getMessage().startswith(RUN_PREFIXES)]


def install(monkeypatch: pytest.MonkeyPatch, client: FakeGcp) -> None:
    """Every GCP client constructor, the scan clock and the logging setup, as fakes."""
    for module in ("ip_adapter", "ip_cleaner"):
        monkeypatch.setattr(f"crc.gcp.{module}.ComputeIpClient", lambda: client)
    for module in ("disk_adapter", "disk_cleaner"):
        monkeypatch.setattr(f"crc.gcp.{module}.ComputeDiskClient", lambda: client)
    for module in ("vm_adapter", "vm_cleaner"):
        monkeypatch.setattr(f"crc.gcp.{module}.ComputeVmClient", lambda: client)
    for module in ("adapter", "cleaner"):
        monkeypatch.setattr(f"crc.gcp.spot_vm.{module}.ComputeSpotClient", lambda: client)
    ticks = itertools.cycle([0.0, 7.0])
    monkeypatch.setattr(_scan, "time", types.SimpleNamespace(monotonic=lambda: next(ticks)))
    monkeypatch.setattr("crc.service.init_logging", lambda *a, **k: None)


def run_pair(  # noqa: PLR0913 - the case, the data and the three switches
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    kind: str,
    flags: dict[str, Any],
    client: FakeGcp,
    *,
    routed: bool,
    slack: bool,
    influx: bool,
) -> Outcome:
    """Run `kind` on gcp through `dispatch._run_pair`, routed or on the legacy handler."""
    install(monkeypatch, client)
    slack_calls: list[Any] = []
    influx_calls: list[Any] = []
    args = {"cloud": "gcp", "project_id": "proj", "resource": kind, **flags}
    options = read_options(args)
    crc = make_crc(
        CliContext(
            options.dry_run,
            options.notags,
            FakeSlack(slack_calls) if slack else None,
            FakeInflux(influx_calls) if influx else None,
            "proj",
            None,
            "chan",
            {"bucket": "b"},
        ),
        "gcp",
    )
    targets = Targets("gcp", False, ["gcp"], [kind])
    caplog.clear()
    caplog.set_level(logging.INFO)
    out = io.StringIO()
    error = None
    try:
        with redirect_stdout(out):
            if routed:
                dispatch._run_pair(crc, "gcp", kind, options, targets)
            else:
                run_legacy_handler(crc, "gcp", kind, options, targets)
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
    stdout = "\n".join(line for line in out.getvalue().splitlines() if "loglevel" not in line)
    return Outcome(_lines(caplog), slack_calls, influx_calls, stdout, error, client.calls)
