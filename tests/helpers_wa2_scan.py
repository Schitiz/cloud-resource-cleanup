"""Drive `CRC` of the routed code on the oracle's scan scenarios, without legacy modules.

The oracle side is `execute(oracle.CRC, [oracle], case)`: `main`'s `CRC` on fakes bound in the
oracle module. The side under test must not depend on which module defines
`CRC.scan_instances_with_tag`, so `execute_scan` never patches a name in a `crc.cli` module. It
patches the SDK-facing VM classes through their own modules (`crc.aws.vm`, `crc.azu.vm`,
`crc.gcp.vm`, `crc.oci.vm`): the module attribute (a seam looked up at call time) and, in place on
the class object, its constructor and `find_instances_with_tag` (reaching code that already holds
the class), then drives `CRC` as `execute` does.
"""

import importlib
import io
import itertools
from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager, redirect_stdout
from typing import Any

import pytest

from tests.helpers_cl2_crc import (
    DATA,
    INFLUX_MODES,
    SLACK_MODES,
    Case,
    Logs,
    Recorded,
    Scenario,
    build,
    make_fake,
)

VM_CLASSES: dict[str, tuple[str, str]] = {
    "aws": ("crc.aws.vm", "AWS_VM"),
    "azure": ("crc.azu.vm", "AZU_VM"),
    "gcp": ("crc.gcp.vm", "GCP_VM"),
    "oci": ("crc.oci.vm", "OCI_VM"),
}
CLOUDS = ["aws", "azure", "gcp", "oci", "other"]


def scenario_grid(values: dict[str, Any], **overrides: Any) -> Iterator[tuple[str, Scenario]]:
    for dry, slack, influx in itertools.product([False, True], SLACK_MODES, INFLUX_MODES):
        yield (
            f"dry={dry}-slack={slack}-influx={influx}",
            Scenario(dict(values), dry_run=dry, slack=slack, influx=influx, **overrides),
        )


def scan_cases(
    name: str, act: Callable[[Any], Any], clouds: list[str] = CLOUDS, **overrides: Any
) -> list[Any]:
    cases = []
    for cloud, data in itertools.product(clouds, DATA):
        for label, scenario in scenario_grid(DATA[data], **overrides):
            case = Case(f"{name}-{cloud}-{data}-{label}", cloud, act, scenario, routed=name)
            cases.append(pytest.param(case, id=case.name))
    return cases


@contextmanager
def patched_vm_classes(scenario: Scenario, logs: Logs) -> Iterator[None]:
    """Replace the SDK-facing VM class of every cloud by the recording fake of the oracle."""
    with pytest.MonkeyPatch.context() as patch, ExitStack() as restore:
        for module_name, adapter in VM_CLASSES.values():
            _patch_vm_class(patch, restore, module_name, adapter, scenario, logs)
        yield


def _patch_vm_class(
    patch: pytest.MonkeyPatch,
    restore: ExitStack,
    module_name: str,
    adapter: str,
    scenario: Scenario,
    logs: Logs,
) -> None:
    module = importlib.import_module(module_name)
    real = module.VM
    fake = make_fake(adapter, scenario, logs)
    patch.setattr(real, "__init__", fake.__dict__["__init__"])
    if "find_instances_with_tag" in fake.__dict__:
        find = fake.__dict__["find_instances_with_tag"]
        patch.setattr(real, "find_instances_with_tag", find, raising=False)
    elif hasattr(real, "find_instances_with_tag"):
        patch.delattr(real, "find_instances_with_tag")
    # `NotImplementedError` names `type(vm)`: make the real class print like the oracle's fake.
    patch.setattr(real, "__module__", fake.__module__)
    restore.callback(setattr, real, "__qualname__", real.__qualname__)
    real.__qualname__ = fake.__qualname__
    patch.setattr(module, "VM", fake)


def execute_scan(crc_class: Any, case: Case) -> Recorded:
    """`execute` for `crc_class` with the VM classes patched through their own modules."""
    logs = Logs()
    out = io.StringIO()
    result: Any = None
    attributes: Any = None
    with patched_vm_classes(case.scenario, logs), redirect_stdout(out):
        try:
            crc = build(crc_class, case, logs)
            attributes = sorted((k, repr(v)) for k, v in vars(crc).items() if "client" not in k)
            result = ("ok", repr(case.act(crc)))
        except Exception as exc:
            result = ("error", type(exc).__name__, str(exc))
    return {
        "result": result,
        "attributes": attributes,
        "adapters": logs.adapters,
        "reads": logs.reads,
        "slack": logs.slack,
        "influx": logs.influx,
        "stdout": out.getvalue(),
    }
