"""ARCH-002 check and self-tests."""

from pathlib import Path

from tests.archtest._common import REPO_ROOT, load_legacy
from tests.archtest.readmes import check_readmes, documented_names, sections

GOOD_README = """# pkg

## Purpose
Does things.

## Public API
- `Thing`: a class.
- `do_work()`: a function.

## Safety Invariants
None.

## Extension Rules
Be careful.
"""
MODULE = '__all__ = ["Thing"]\n\n\nclass Thing:\n    pass\n\n\ndef do_work() -> None:\n    pass\n'


def _package(root: Path, readme: str | None, module: str = MODULE) -> None:
    pkg = root / "crc" / "core"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text(module, encoding="utf-8")
    if readme is not None:
        (pkg / "README.md").write_text(readme, encoding="utf-8")


def _assert_formatted(messages: list[str]) -> None:
    assert messages
    for message in messages:
        assert message.startswith("ARCH-002: ")
        assert "\n\nREMEDIATION: " in message


def test_arch002_package_readmes() -> None:
    problems = check_readmes(REPO_ROOT, load_legacy(REPO_ROOT))
    assert not problems, "\n\n".join(problems)


def test_arch002_helpers_parse_sections_and_names() -> None:
    parsed = sections(GOOD_README)
    assert list(parsed) == ["Purpose", "Public API", "Safety Invariants", "Extension Rules"]
    assert documented_names(parsed["Public API"]) == ({"Thing", "do_work"}, [])


def test_arch002_selftest_passes_on_good_package(tmp_path: Path) -> None:
    _package(tmp_path, GOOD_README)
    assert check_readmes(tmp_path, frozenset()) == []


def test_arch002_selftest_ignores_legacy_only_packages(tmp_path: Path) -> None:
    _package(tmp_path, None)
    assert check_readmes(tmp_path, frozenset({"crc/core/__init__.py"})) == []


def test_arch002_selftest_fires_without_readme(tmp_path: Path) -> None:
    _package(tmp_path, None)
    messages = check_readmes(tmp_path, frozenset())
    _assert_formatted(messages)
    assert "no README.md" in messages[0]


def test_arch002_selftest_fires_on_missing_section(tmp_path: Path) -> None:
    _package(tmp_path, GOOD_README.replace("## Extension Rules", "## Other"))
    messages = check_readmes(tmp_path, frozenset())
    _assert_formatted(messages)
    assert "Extension Rules" in messages[0]


def test_arch002_selftest_fires_on_undocumented_public_name(tmp_path: Path) -> None:
    extra = MODULE + "\n\ndef another() -> None:\n    pass\n"
    _package(tmp_path, GOOD_README, extra)
    messages = check_readmes(tmp_path, frozenset())
    _assert_formatted(messages)
    assert "another" in messages[0]


def test_arch002_selftest_fires_on_nonexistent_documented_name(tmp_path: Path) -> None:
    _package(tmp_path, GOOD_README.replace("`do_work()`", "`do_work()`, `ghost`"))
    messages = check_readmes(tmp_path, frozenset())
    _assert_formatted(messages)
    assert "ghost" in messages[0]


def test_arch002_selftest_fires_on_non_name_backticks(tmp_path: Path) -> None:
    _package(tmp_path, GOOD_README.replace("a class.", "see `crc.core.thing`."))
    messages = check_readmes(tmp_path, frozenset())
    _assert_formatted(messages)
    assert "not bare" in messages[0]
