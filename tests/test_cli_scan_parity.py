"""Parity: `CRC.scan_instances_with_tag` against the CRC class of main (`crc_main.txt`).

Lane WA-2. Moved out of `tests/test_cli_crc_parity.py` with the same oracle
(`load_legacy_crc()`), the same scenario grid and the same compared fields. The oracle runs
`main`'s `CRC` on fake adapters patched in the oracle module; the side under test runs
`crc.cli.runner.CRC` with the SDK-facing VM classes patched through their own modules
(`tests/helpers_wa2_scan.py`), so these cases do not care which module defines the method.
"""

from types import ModuleType

import pytest

from crc.cli.runner import CRC as NewCRC
from tests.helpers_cl2_crc import MIN_SEEN, Case, execute
from tests.helpers_oracle import load_legacy_crc
from tests.helpers_wa2_scan import execute_scan, scan_cases

SCAN_CASES = scan_cases("scan", lambda c: c.scan_instances_with_tag("auto_clean", "false"))
SCAN_UNSUPPORTED_CASES = scan_cases(
    "scan_unsupported", lambda c: c.scan_instances_with_tag("k", "v"), scan_supported=False
)


@pytest.fixture(scope="module")
def oracle() -> ModuleType:
    return load_legacy_crc("legacy_crc_main_scan")


def compare_scan(oracle_module: ModuleType, case: Case) -> None:
    old = execute(oracle_module.CRC, [oracle_module], case)
    new = execute_scan(NewCRC, case)
    for key in old:
        assert new[key] == old[key], f"{case.name}: {key} differs"


@pytest.mark.parametrize("case", SCAN_CASES)
def test_scan_matches_main(oracle: ModuleType, case: Case) -> None:
    compare_scan(oracle, case)


@pytest.mark.parametrize("case", SCAN_UNSUPPORTED_CASES)
def test_scan_unsupported_matches_main(oracle: ModuleType, case: Case) -> None:
    compare_scan(oracle, case)


def test_scan_cases_are_not_vacuous(oracle: ModuleType) -> None:
    seen = {"hit": 0, "unsupported": 0, "invalid_cloud": 0}
    for param in SCAN_CASES[::7] + SCAN_UNSUPPORTED_CASES[::7]:
        outcome = execute_scan(NewCRC, param.values[0])
        result = outcome["result"]
        if result[0] == "ok":
            assert any(call[1] == "find_instances_with_tag" for call in outcome["adapters"][1:])
            seen["hit"] += 1
        elif "does not implement" in result[2]:
            seen["unsupported"] += 1
        else:
            seen["invalid_cloud"] += 1
    assert all(count > MIN_SEEN for count in seen.values()), seen
