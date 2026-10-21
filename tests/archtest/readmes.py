"""ARCH-002: package READMEs with required sections and symbol sync."""

import ast
import re
from pathlib import Path

from tests.archtest._common import iter_python_files, parse_module, relpath, violation

RULE = "ARCH-002"
REQUIRED_SECTIONS = ("Purpose", "Public API", "Safety Invariants", "Extension Rules")
_HEADING = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_BACKTICKED = re.compile(r"`([^`\n]+)`")


def sections(markdown: str) -> dict[str, str]:
    """Split a README into `## ` sections keyed by heading text."""
    matches = list(_HEADING.finditer(markdown))
    result: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        result[match.group(1)] = markdown[match.end() : end]
    return result


def declared_all(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else []
        if isinstance(node, ast.AnnAssign):
            targets = [node.target]
        if not any(isinstance(t, ast.Name) and t.id == "__all__" for t in targets):
            continue
        value = node.value if isinstance(node, ast.Assign | ast.AnnAssign) else None
        if isinstance(value, ast.List | ast.Tuple):
            names.update(
                el.value
                for el in value.elts
                if isinstance(el, ast.Constant) and isinstance(el.value, str)
            )
    return names


def public_defs(tree: ast.Module) -> set[str]:
    return {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
        and not node.name.startswith("_")
    }


def required_names(modules: list[Path]) -> set[str]:
    """`__all__` of the package `__init__.py` plus public defs of every module."""
    names: set[str] = set()
    for module in modules:
        tree = parse_module(module)
        names |= public_defs(tree)
        if module.name == "__init__.py":
            names |= declared_all(tree)
    return names


def documented_names(api_section: str) -> tuple[set[str], list[str]]:
    """Backticked names in the API section, plus tokens that are not bare names."""
    names: set[str] = set()
    invalid: list[str] = []
    for token in _BACKTICKED.findall(api_section):
        bare = token.removesuffix("()")
        if bare.isidentifier():
            names.add(bare)
        else:
            invalid.append(token)
    return names, invalid


def package_dirs(root: Path, legacy: frozenset[str]) -> dict[Path, list[Path]]:
    """Directories under `crc/` mapped to their direct non-legacy `.py` files."""
    found: dict[Path, list[Path]] = {}
    for path in iter_python_files(root / "crc"):
        if path.parent == root / "crc" or relpath(root, path) in legacy:
            continue
        found.setdefault(path.parent, []).append(path)
    return found


def _check_readme(root: Path, directory: Path, modules: list[Path]) -> list[str]:
    where = relpath(root, directory)
    readme = directory / "README.md"
    if not readme.is_file():
        return [
            violation(
                RULE,
                f"{where}/ has non-legacy modules but no README.md",
                f"Create {where}/README.md with the sections "
                + ", ".join(f"`## {s}`" for s in REQUIRED_SECTIONS)
                + ". List every public name in backticks under `## Public API`.",
            )
        ]
    found = sections(readme.read_text(encoding="utf-8"))
    problems: list[str] = []
    missing = [s for s in REQUIRED_SECTIONS if s not in found]
    if missing:
        problems.append(
            violation(
                RULE,
                f"{where}/README.md is missing sections: {missing}",
                "Add each missing `## <Section>` heading with real content. Required: "
                + ", ".join(REQUIRED_SECTIONS)
                + ".",
            )
        )
    if "Public API" in found:
        problems.extend(_check_symbols(where, found["Public API"], required_names(modules)))
    return problems


def _check_symbols(where: str, api_section: str, required: set[str]) -> list[str]:
    documented, invalid = documented_names(api_section)
    problems: list[str] = []
    if invalid:
        problems.append(
            violation(
                RULE,
                f"{where}/README.md `## Public API` has backticked tokens that are not bare "
                f"names: {sorted(invalid)}",
                "Under `## Public API` use backticks only for exported names such as "
                "`Thing` or `do_work()`. Move paths, flags and code samples to other sections.",
            )
        )
    undocumented = sorted(required - documented)
    if undocumented:
        problems.append(
            violation(
                RULE,
                f"{where}/README.md `## Public API` does not mention: {undocumented}",
                "Add each name in backticks with a one-line description under `## Public API`, "
                "or make it private with a leading underscore if it is not public API.",
            )
        )
    unknown = sorted(documented - required)
    if unknown:
        problems.append(
            violation(
                RULE,
                f"{where}/README.md `## Public API` lists names that do not exist: {unknown}",
                "Remove the stale names from the README, or restore/export them in `__all__` "
                "or as public top-level functions or classes. Do not invent names.",
            )
        )
    return problems


def check_readmes(root: Path, legacy: frozenset[str]) -> list[str]:
    problems: list[str] = []
    for directory, modules in sorted(package_dirs(root, legacy).items()):
        problems.extend(_check_readme(root, directory, modules))
    return problems
