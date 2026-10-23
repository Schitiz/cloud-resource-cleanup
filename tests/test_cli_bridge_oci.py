"""Parity: the engine bridge with the real OCI cleaners against the legacy adapters.

The oracle `CRC` (`tests/legacy/crc_main.txt`) runs the real `Disk`, `VM` and `SpotVM` adapters,
the bridge runs `DiskCleaner`, `VmCleaner` and `SpotVmCleaner` built by their registered
factories; both read the same fake SDK API, Slack and Influx clients. For `disk`, `vm` (delete and
stop) and `spot_instances`, in a dry run and a real run, the run-log lines (RUN START, ACTION,
SKIPPED, ERRORS, RESULT, REGION), the other log records, Slack, Influx, stdout and the raised
error must be equal, and so must the mutating SDK calls. The only allowed difference: a listing
error in a later region now stops the pair before any mutation (BUG-408).
"""

import logging
import re
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager, redirect_stdout
from dataclasses import dataclass
from io import StringIO
from types import ModuleType
from typing import Any

import oci
import pytest

from crc.cli import bridge, dispatch
from crc.cli.inputs import Targets, read_options
from crc.cli.routes import Route
from crc.cli.routes import oci as oci_routes
from crc.cli.runner import CRC as NewCRC
from crc.core import logger
from crc.oci.disk import Disk, DiskRuntime
from crc.oci.spot_vm import SpotVM, SpotVmRuntime
from crc.oci.spot_vm.client import RegionClients
from crc.oci.vm import VM, VmRuntime
from tests.helpers_cli_routes import provide_legacy_keypairs
from tests.test_cli_crc_parity import Case, Logs, Scenario, build, oracle
from tests.test_oci_disk import NOW as DISK_NOW
from tests.test_oci_disk import FakeApi as DiskApi
from tests.test_oci_disk import att, vol
from tests.test_oci_spot_instances import FakeClient as SpotApi
from tests.test_oci_spot_instances import inst as spot_inst
from tests.test_oci_spot_instances import paginate
from tests.test_oci_vm import FakeApi as VmApi
from tests.test_oci_vm import inst

provide_legacy_keypairs()

__all__ = ["oracle"]

TAGS = {"env": ["ci"]}
FLAGS: dict[str, Any] = {
    "cloud": "oci",
    "filter_tags": TAGS,
    "exception_tags": {},
    "notags": {"owner": ["x"]},
    "age": {"hours": 5},
    "custom_age_tag_key": "age_tag",
}
MODES = [
    ("both", "on", "on"),
    ("off", "off", "off"),
    ("slack", "on", "off"),
    ("sfx", "off", "on_suffix"),
]
MUTATING = ("delete_volume", "delete_boot_volume", "terminate_instance", "stop_instance")


class Down(DiskApi, VmApi):
    """An API whose listing raises `error`."""

    def __init__(self, error: Exception) -> None:
        DiskApi.__init__(self)
        self.error = error

    def list_volumes(self) -> Sequence[Any]:
        raise self.error

    def list_instances(self, *args: Any, **kwargs: Any) -> Sequence[Any]:
        raise self.error


@dataclass(frozen=True)
class Kind:
    name: str
    operation: str
    act: Callable[[Any], Any]
    apis: Callable[[str | None], dict[str, Any]]


def _disk_apis(second: str | None) -> dict[str, Any]:
    first = DiskApi(
        [vol("a"), vol("young", hours=1), vol("att")],
        [vol("b"), vol("c")],
        [att("att")],
        failing={"c": RuntimeError("boom")},
    )
    return {"r1": first, "r2": _second(second, DiskApi([vol("d")], [vol("e")]))}


def _vm_apis(second: str | None) -> dict[str, Any]:
    first = VmApi(
        [inst("a"), inst("young", hours=1), inst("st", state="STOPPED"), inst("f")],
        failing={"f": RuntimeError("boom")},
    )
    return {"r1": first, "r2": _second(second, VmApi([inst("d")]))}


def _spot_apis(second: str | None) -> dict[str, Any]:
    od = spot_inst("od")
    od.preemptible_instance_config = None
    first = SpotApi(
        [spot_inst("a"), spot_inst("young", hours=1), od],
        {"a": ["vol-a", "vol-keep"]},
        {"vol-keep": {"owner": "x"}},
    )
    return {"r1": first, "r2": _second(second, SpotApi([spot_inst("d")], {"d": ["vol-d"]}))}


def _second(error: str | None, normal: Any) -> Any:
    if error == "connect":
        return Down(oci.exceptions.ConnectTimeout("t"))
    if error == "boom":
        return Down(RuntimeError("list down"))
    return normal


KINDS = [
    Kind(
        "disk",
        "delete",
        lambda c: c.delete_disks(TAGS, {}, {"hours": 5}, "age_tag", {}, [], [], False, None),
        _disk_apis,
    ),
    Kind("vm", "delete", lambda c: c.delete_vm(TAGS, {}, {"hours": 5}, "age_tag", None), _vm_apis),
    Kind("vm", "stop", lambda c: c.stop_vm(TAGS, {}, {"hours": 5}, "age_tag"), _vm_apis),
    Kind(
        "spot_instances",
        "delete",
        lambda c: c.delete_spot_instances(TAGS, {}, {"hours": 5}, "age_tag"),
        _spot_apis,
    ),
]


class Collector(logging.Handler):
    def __init__(self) -> None:
        super().__init__(0)
        self.lines: list[tuple[str, str]] = []

    def emit(self, record: logging.LogRecord) -> None:
        text = re.sub(r"seconds=\d+", "seconds=0", record.getMessage())
        text = re.sub(r"duration=\S+", "duration=0", text)
        self.lines.append((record.name, f"{record.levelname} {text}"))


def _patch_sdk(mp: pytest.MonkeyPatch, apis: dict[str, Any], oracle_module: ModuleType) -> None:
    mp.setattr("crc.service.Service.__init__", lambda self: None)
    mp.setattr("crc.oci._base.Base.__init__", lambda self: None)
    mp.setattr("crc.oci.disk.cleaner.Base", lambda: object())
    mp.setattr("crc.oci.vm.cleaner.Base", lambda: object())
    mp.setattr("crc.oci.spot_vm.cleaner.Base", lambda: object())

    def factory(base: Any) -> Callable[[str], Any]:
        return lambda region: apis[region]

    def spot_factory(region: str) -> RegionClients:
        return RegionClients(apis[region], apis[region], "cmp")

    def regions(base: Any) -> Callable[[], list[str]]:
        return lambda: list(apis)

    for name in ("crc.oci.disk.cleaner", "crc.oci.vm.cleaner", "crc.oci.spot_vm.cleaner"):
        mp.setattr(f"{name}.regions_of", regions)
    mp.setattr("crc.oci.disk.cleaner.api_for", factory)
    mp.setattr("crc.oci.vm.cleaner.compute_api_for", factory)
    mp.setattr("crc.oci.spot_vm.cleaner.clients_for", lambda base: spot_factory)
    mp.setattr("crc.oci.spot_vm.client.oci.pagination.list_call_get_all_results", paginate)
    api_factory, lister = factory(None), regions(None)

    def clock() -> Any:
        return DISK_NOW

    def make_disk(*args: Any) -> Disk:
        return Disk(*args, runtime=DiskRuntime(api_factory, lister, clock))  # type: ignore[misc]

    def make_vm(*args: Any) -> VM:
        return VM(*args, runtime=VmRuntime(api_factory, lister, clock))  # type: ignore[misc]

    def make_spot(*args: Any) -> SpotVM:
        spot = SpotVM(*args, runtime=SpotVmRuntime(spot_factory, lister, paginate, clock))  # type: ignore[misc]
        spot.compartment_id = "cmp"
        return spot

    mp.setattr(oracle_module, "OCI_Disk", make_disk)
    mp.setattr(oracle_module, "OCI_VM", make_vm)
    mp.setattr(oracle_module, "OCI_SpotVM", make_spot)
    mp.setattr(bridge, "init_run_logging", lambda: None)
    mp.setattr(bridge, "datetime", type("D", (), {"now": staticmethod(lambda tz=None: DISK_NOW)}))


@dataclass(frozen=True)
class Run:
    """One side of a comparison: the kind, dry run, Slack and Influx mode, the second region's
    listing error (`connect`, `boom` or none) and whether the bridge or the legacy adapter runs."""

    kind: Kind
    dry: bool
    mode: tuple[str, str, str]
    second: str | None
    routed: bool


@contextmanager
def _capture() -> Iterator[Collector]:
    collector = Collector()
    root, run_log = logging.getLogger(), logging.getLogger("crc.run")
    saved = (root.level, run_log.level)
    root.addHandler(collector)
    root.setLevel(logging.DEBUG)
    run_log.setLevel(logging.DEBUG)
    try:
        yield collector
    finally:
        root.removeHandler(collector)
        root.setLevel(saved[0])
        run_log.setLevel(saved[1])


def _act(run: Run, crc: Any, options: Any, targets: Targets) -> None:
    kind = run.kind
    if run.routed:
        if kind.name == "spot_instances":
            logger.begin("oci", kind.name, kind.operation, run.dry, dispatch._run_options(options))
            try:
                bridge.run_routed(
                    crc, "oci", kind.name, options, targets, Route(oci_routes._spot_instances)
                )
            finally:
                logger.finish()
            return
        assert bridge.route_for("oci", kind.name) is not None
        handler = dispatch.HANDLERS.get(kind.name)
        dispatch._run_handler(handler, crc, "oci", kind.name, options, targets)
        return
    logger.begin("oci", kind.name, kind.operation, run.dry, dispatch._run_options(options))
    try:
        kind.act(crc)
    finally:
        logger.finish()


def _run(run: Run, oracle_module: ModuleType, mp: pytest.MonkeyPatch) -> dict[str, Any]:
    kind, dry, mode = run.kind, run.dry, run.mode
    apis = kind.apis(run.second)
    _patch_sdk(mp, apis, oracle_module)
    case = Case(mode[0], "oci", lambda c: None, Scenario({}, dry, mode[1], mode[2]))
    logs = Logs()
    flags = {**FLAGS, "resource": kind.name, "operation_type": kind.operation, "dry_run": dry}
    options = read_options(flags)
    targets = Targets("oci", False, ["oci"], [kind.name])
    out = StringIO()
    result: Any = ("ok",)
    with _capture() as collector, redirect_stdout(out):
        try:
            crc = build(NewCRC if run.routed else oracle_module.CRC, case, logs)
            _act(run, crc, options, targets)
        except Exception as exc:
            result = ("error", type(exc).__name__, str(exc))
    run_lines = [t for n, t in collector.lines if n == "crc.run"]
    return {
        "result": result,
        "slack": logs.slack,
        "influx": logs.influx,
        "stdout": out.getvalue(),
        "run": run_lines,
        "other": sorted(t for n, t in collector.lines if n != "crc.run"),
        "calls": {r: [c for c in a.calls if c[0] in MUTATING] for r, a in apis.items()},
        "all_calls": sorted(c for a in apis.values() for c in a.calls),
    }


def _by_kind(lines: list[str], prefix: str) -> list[str]:
    return [line for line in lines if prefix in line]


PARAMS = [
    pytest.param(
        kind, dry, mode, second, id=f"{kind.name}-{kind.operation}-dry={dry}-{mode[0]}-{second}"
    )
    for kind in KINDS
    for dry in (True, False)
    for mode in MODES
    for second in (None, "connect", "boom")
]


@pytest.mark.parametrize(("kind", "dry", "mode", "second"), PARAMS)
def test_routed_pair_matches_the_legacy_adapter(
    kind: Kind,
    dry: bool,
    mode: tuple[str, str, str],
    second: str | None,
    oracle: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old = _run(Run(kind, dry, mode, second, False), oracle, monkeypatch)
    new = _run(Run(kind, dry, mode, second, True), oracle, monkeypatch)
    assert new["result"] == old["result"]
    assert new["stdout"] == old["stdout"]
    assert new["run"][0] == old["run"][0]
    if second == "boom" and not dry and kind.name != "spot_instances":
        assert new["calls"] == {"r1": [], "r2": []}
        assert old["calls"]["r1"], "the legacy path deleted region r1 before the listing error"
        assert not _by_kind(new["run"], "ACTION")
        return
    assert new["run"][-1] == old["run"][-1]
    for tag in ("ACTION", "SKIPPED", "ERRORS", "FAILED"):
        assert _by_kind(new["run"], tag) == _by_kind(old["run"], tag)
    assert new["slack"] == old["slack"]
    assert new["influx"] == old["influx"]
    assert new["calls"] == old["calls"]
    assert new["all_calls"] == old["all_calls"]
    assert sorted(new["run"]) == sorted(old["run"])
    assert new["other"] == old["other"]


@pytest.mark.parametrize("kind", KINDS, ids=lambda k: f"{k.name}-{k.operation}")
@pytest.mark.parametrize("dry", [True, False])
def test_the_comparison_is_not_vacuous(
    kind: Kind, dry: bool, oracle: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both paths log ACTION lines, send Slack and Influx with display names, and mutate."""
    new = _run(Run(kind, dry, MODES[0], None, True), oracle, monkeypatch)
    old = _run(Run(kind, dry, MODES[0], None, False), oracle, monkeypatch)
    assert new["result"] == old["result"] == ("ok",)
    assert _by_kind(new["run"], "ACTION") and len(new["slack"]) >= 1 and len(new["influx"]) >= 1
    assert any("name-" in str(call) for call in new["slack"] + new["influx"])
    assert not any("ocid" in str(call) for call in new["slack"] + new["influx"])
    assert bool(new["calls"]["r1"]) is (not dry)
