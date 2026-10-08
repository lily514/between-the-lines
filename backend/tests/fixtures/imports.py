"""What a package's modules import, for tests that keep packages apart."""

import ast
from pathlib import Path
from types import ModuleType


def imports_by_module(package: ModuleType) -> dict[str, list[str]]:
    """Every module a package's files import, by file name."""
    found: dict[str, list[str]] = {}
    for module in Path(str(package.__file__)).parent.glob("*.py"):
        tree = ast.parse(module.read_text())
        found[module.name] = [
            name
            for node in ast.walk(tree)
            for name in (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else []
            )
        ]
    return found
