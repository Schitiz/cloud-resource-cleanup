"""Parity: the `CRC` constructor against the CRC class of main (`tests/legacy/crc_main.txt`).

Lane WA-2. Moved out of `tests/test_cli_crc_parity.py` with the same oracle
(`load_legacy_crc()`), inputs and compared fields: the constructor attributes (cloud, dry_run,
notags, resource group, project id, Slack and Influx settings), the clients' construction calls,
the printed output and the result. No adapter or VM class is patched on the side under test.
"""

from types import ModuleType
from typing import Any

import pytest

from crc.cli.runner import CRC as NewCRC
from tests.helpers_cl2_crc import FULL, Case, Scenario, execute
from tests.helpers_oracle import load_legacy_crc


@pytest.fixture(scope="module")
def oracle() -> ModuleType:
    return load_legacy_crc("legacy_crc_main_runner")


@pytest.mark.parametrize("cloud", ["aws", "azure", "gcp", "oci", "other"])
@pytest.mark.parametrize("project_id", [None, "", "proj"])
@pytest.mark.parametrize("slack", ["off", "on"])
def test_constructor_matches_main(
    oracle: ModuleType, cloud: str, project_id: Any, slack: str
) -> None:
    scenario = Scenario(dict(FULL), slack=slack, project_id=project_id, influx="no_conn")
    case = Case(f"ctor-{cloud}", cloud, lambda c: None, scenario)
    old = execute(oracle.CRC, [oracle], case)
    new = execute(NewCRC, [], case)
    for key in old:
        assert new[key] == old[key], f"{case.name}: {key} differs"
