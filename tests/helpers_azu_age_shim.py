"""Fixture that keeps the Azure cleaner classes under their historic parity tests.

The registry factories of the Azure disk, IP and NIC cleaners now refuse a real run without a
positive `--age` (BUG-075, BUG-112, BUG-173). The parity tests compare the cleaner logic with
the frozen oracle on cases that carry no age, so they pass the option through unchecked here;
`tests/test_azure_age_required_fix.py` covers the refusal and the creation-time gate without
this shim, which also treats every IP and NIC as old enough.
"""

from collections.abc import Mapping
from typing import Any

import pytest

from crc.azu._created import AgeGate
from crc.core.cleaner import RunContext


def _passthrough(context: RunContext, kind: str) -> Mapping[str, Any] | None:
    age: Mapping[str, Any] | None = context.options.get("age")
    return age


@pytest.fixture(autouse=True)
def legacy_age_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    for module in ("disk", "ip", "nic"):
        monkeypatch.setattr(f"crc.azu.{module}.cleaner.real_run_age", _passthrough)
    monkeypatch.setattr(AgeGate, "load", lambda self, now: None)
    monkeypatch.setattr(AgeGate, "keep_reason", lambda self, resource_id: "")
