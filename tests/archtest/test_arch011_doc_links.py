"""ARCH-011 check and self-tests."""

from pathlib import Path

from tests.archtest._common import REPO_ROOT
from tests.archtest.doc_links import check_doc_links


def _write(root: Path, name: str, text: str = "x\n") -> None:
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def test_arch011_every_relative_link_resolves() -> None:
    problems = check_doc_links(REPO_ROOT)
    assert not problems, "\n\n".join(problems)


def test_arch011_selftest_fires_on_missing_target(tmp_path: Path) -> None:
    _write(tmp_path, "AGENTS.md", "intro\nsee [plan](docs/PLAN.md)\n")
    messages = check_doc_links(tmp_path)
    assert len(messages) == 1
    assert messages[0].startswith("ARCH-011: AGENTS.md:2 links to docs/PLAN.md")
    assert "\n\nREMEDIATION: " in messages[0]


def test_arch011_selftest_resolves_relative_to_the_document(tmp_path: Path) -> None:
    _write(tmp_path, "docs/a.md", "[b](b.md) [up](../AGENTS.md) [no](c.md)\n")
    _write(tmp_path, "docs/b.md")
    _write(tmp_path, "AGENTS.md")
    messages = check_doc_links(tmp_path)
    assert [m.split("\n")[0] for m in messages] == [
        "ARCH-011: docs/a.md:1 links to c.md, which does not exist"
    ]


def test_arch011_selftest_checks_cursor_files_and_directories(tmp_path: Path) -> None:
    _write(tmp_path, ".cursor/skills/s/SKILL.md", "[ok](review.md) [dir](../s) [bad](gone.md)\n")
    _write(tmp_path, ".cursor/skills/s/review.md")
    _write(tmp_path, ".cursor/rules/00.mdc", "[bad](../../nope.md)\n")
    messages = check_doc_links(tmp_path)
    assert [m.split("\n")[0].split(",")[0] for m in messages] == [
        "ARCH-011: .cursor/rules/00.mdc:1 links to ../../nope.md",
        "ARCH-011: .cursor/skills/s/SKILL.md:1 links to gone.md",
    ]


def test_arch011_selftest_ignores_anchors_external_code_and_other_files(tmp_path: Path) -> None:
    text = (
        "[a](ARCHITECTURE.md#section) [web](https://example.com/x) [mail](mailto:a@b.c) "
        "[here](#top) `[code](missing.md)`\n```\n[fenced](missing.md)\n```\n"
    )
    _write(tmp_path, "AGENTS.md", text)
    _write(tmp_path, "ARCHITECTURE.md")
    _write(tmp_path, "docs/archive/old.md", "[dead](missing.md)\n")
    _write(tmp_path, "docs/sub/old.md", "[dead](missing.md)\n")
    _write(tmp_path, "README.md", "[dead](missing.md)\n")
    assert check_doc_links(tmp_path) == []


def test_arch011_selftest_anchor_on_missing_file_fires(tmp_path: Path) -> None:
    _write(tmp_path, "AGENTS.md", "[x](NOPE.md#part)\n")
    assert len(check_doc_links(tmp_path)) == 1


def test_arch011_selftest_root_relative_links(tmp_path: Path) -> None:
    _write(tmp_path, "docs/a.md", "[ok](/AGENTS.md) [bad](/gone.md)\n")
    _write(tmp_path, "AGENTS.md")
    messages = check_doc_links(tmp_path)
    assert len(messages) == 1
    assert "links to /gone.md" in messages[0]
