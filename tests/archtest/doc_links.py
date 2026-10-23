"""ARCH-011: every relative markdown link in the agent-facing documents resolves."""

import re
from pathlib import Path

from tests.archtest._common import relpath, violation

RULE = "ARCH-011"
ROOT_DOCS = ("AGENTS.md", "ARCHITECTURE.md", "CLEANUP_SAFETY.md")
_FENCE = re.compile(r"^(```|~~~).*?^\1[^\n]*$", re.MULTILINE | re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`\n]*`")
_LINK = re.compile(r"\[[^\]\n]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_EXTERNAL = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|#)", re.IGNORECASE)
_REMEDIATION = (
    "Fix the link target, or update the link after a file move or rename. Linked documents are "
    "how an agent finds detail one hop away, so a dead link sends it to guess. Do not delete "
    "the link if the document still needs the reference."
)


def _documents(root: Path) -> list[Path]:
    files = [root / name for name in ROOT_DOCS]
    files += sorted((root / "docs").glob("*.md"))
    cursor = root / ".cursor"
    if cursor.is_dir():
        files += sorted(
            path for path in cursor.rglob("*") if path.suffix in {".md", ".mdc"} and path.is_file()
        )
    return [path for path in files if path.is_file()]


def _links(text: str) -> list[tuple[int, str]]:
    """`(line number, target)` of each link, ignoring fenced and inline code."""
    blanked = _FENCE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    found: list[tuple[int, str]] = []
    for number, line in enumerate(blanked.splitlines(), start=1):
        plain = _INLINE_CODE.sub("", line)
        found += [(number, match.group(1)) for match in _LINK.finditer(plain)]
    return found


def _resolves(root: Path, document: Path, target: str) -> bool:
    path_part = target.split("#", 1)[0].split("?", 1)[0]
    if not path_part:
        return True
    base = root if path_part.startswith("/") else document.parent
    return (base / path_part.lstrip("/")).exists()


def check_doc_links(root: Path) -> list[str]:
    """Violations for relative links that point at a missing file or directory."""
    problems: list[str] = []
    for document in _documents(root):
        for number, target in _links(document.read_text(encoding="utf-8")):
            if _EXTERNAL.match(target) or _resolves(root, document, target):
                continue
            problems.append(
                violation(
                    RULE,
                    f"{relpath(root, document)}:{number} links to {target}, which does not exist",
                    _REMEDIATION,
                )
            )
    return problems
