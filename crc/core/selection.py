"""Selection model of the engine: the `(cloud, kind)` pairs a run executes and the CLI order.

Pure and typed. `Selection` is the ordered pairs the engine runs; `crc/cli/bridge.py` builds a
one-pair `Selection` per run. `CLOUDS`, `RESOURCES` and `EXTRA_RESOURCES` record the `--cloud all`
and `--resource all` expansion order; the pair and opt-in checks live in `crc/cli/inputs.py` and
`crc/cli/dispatch.py`. Nothing here reads the environment or logs.
"""

from dataclasses import dataclass

CLOUDS: tuple[str, ...] = ("aws", "azure", "gcp", "oci")
RESOURCES: tuple[str, ...] = ("disk", "ip", "keypair", "vm", "kms", "nic", "snapshot")
EXTRA_RESOURCES: tuple[str, ...] = ("vpc", "spot_instance_requests", "spot_instances")


@dataclass(frozen=True, slots=True)
class Selection:
    """Ordered `(cloud, kind)` pairs to run and the warnings of the pairs that were skipped."""

    items: tuple[tuple[str, str], ...]
    warnings: tuple[str, ...] = ()
