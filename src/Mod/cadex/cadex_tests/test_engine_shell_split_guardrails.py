# SPDX-License-Identifier: LGPL-2.1-or-later

"""Engine/shell split guardrails (Phase 5.5, ADR-018).

The split is process-level: the pipeline modules stay in-tree because
cadexd and cadex_rebuild run them, but the Qt shell must never reach them
in-process again. These tests pin that boundary — loosening it is a
direction change that needs an ADR and owner sign-off.
"""

from __future__ import annotations

import ast
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent.parent

#: Shell-side modules that must stay protocol clients. The Qt UI layer left
#: this list in C3 (ADR-021); the rest of the file goes in C5, when the
#: last shell module in this repo does.
SHELL_MODULES = (
    "CadexSession.py",
    "CadexShellHydration.py",
    "CadexdClient.py",
)

#: Engine internals the shell may not import: the publication applier, the
#: worker process runner, and the pipeline entry points around them.
FORBIDDEN_MODULES = {
    "CadexScriptedDomainPublication",
    "CadexScriptedProcess",
}
FORBIDDEN_NAMES = {
    "execute_candidate",
    "publish_project_candidate",
    "prepare_project_candidate",
    "validate_project_result",
    "accept_project_candidate",
    "capture_project_state",
    "run_project_lifecycle",
}


def _imports(path: Path) -> list[tuple[str, tuple[str, ...]]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[tuple[str, tuple[str, ...]]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append((alias.name, ()))
        elif isinstance(node, ast.ImportFrom):
            found.append(
                (str(node.module or ""), tuple(alias.name for alias in node.names))
            )
    return found


def test_shell_modules_do_not_import_engine_internals() -> None:
    for module_name in SHELL_MODULES:
        for module, names in _imports(MODULE_DIR / module_name):
            assert module not in FORBIDDEN_MODULES, (
                f"{module_name} imports engine-internal module {module}; "
                "the shell drives modeling through cadexd only (ADR-018)."
            )
            leaked = FORBIDDEN_NAMES.intersection(names)
            assert not leaked, (
                f"{module_name} imports engine pipeline entry {sorted(leaked)} "
                f"from {module}; the shell drives modeling through cadexd "
                "only (ADR-018)."
            )


def test_engine_side_users_of_the_pipeline_are_the_known_ones() -> None:
    users = set()
    for path in MODULE_DIR.glob("*.py"):
        for module, names in _imports(path):
            if module in FORBIDDEN_MODULES or FORBIDDEN_NAMES.intersection(names):
                users.add(path.name)
    # The pipeline stays in-tree for exactly these engine-side drivers.
    assert users <= {
        "cadexd.py",
        "cadex_rebuild.py",
        "CadexScriptedRuntime.py",
        "CadexScriptedDomainPublication.py",
        "CadexDigest.py",
        "CadexScriptedOwnership.py",
    }, users


def test_session_project_tools_route_through_the_cadexd_client() -> None:
    source = (MODULE_DIR / "CadexSession.py").read_text(encoding="utf-8")
    assert "CadexdClient" in source
    assert "client_for_project" in source
