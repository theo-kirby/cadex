"""ADR-827: every engine module the project worker bundle imports is staged in it.

usage: pixi run python docs/probes/lurcher/worker_bundle_closure.py

`_unstaged_member_imports` (the bundle's own guard) reads module-scope imports
only. This probe walks every import a member makes, at any depth, follows them
through the engine tree, and lists the engine modules (and the data files they
read beside themselves) that the closure reaches but the bundle does not stage.
Such a module is found on FreeCAD's own Mod path inside the worker: in a dev
tree that is the copy the environment last installed, not this tree.

Exits non-zero, naming them, when any is missing.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"
sys.path.insert(0, str(ROOT))

import CadexScriptedRuntime as runtime  # noqa: E402


def imports(path: Path) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            out.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            out.add(node.module.split(".")[0])
    return out


def data_files(path: Path) -> set[str]:
    # files a module reads beside itself: Path(__file__).with_name("X")
    text = path.read_text(encoding="utf-8")
    return set(re.findall(r'with_name\(\s*"([^"]+)"\s*\)', text))


def main() -> int:
    entry, members = runtime._bundle_members("project")
    staged = {entry, *members}
    engine = {p.stem for p in ROOT.glob("*.py")}
    seen = {Path(n).stem for n in staged if n.endswith(".py")}
    todo = sorted(seen)
    reached: dict[str, str] = {}
    files: dict[str, str] = {}
    while todo:
        module = todo.pop()
        path = ROOT / f"{module}.py"
        for name in data_files(path):
            files.setdefault(name, module)
        for name in sorted(imports(path)):
            if name in engine and name not in seen:
                seen.add(name)
                reached[name] = module
                todo.append(name)
    missing = [f"{name}.py (imported by {by})" for name, by in sorted(reached.items())]
    missing += [f"{name} (read by {by})" for name, by in sorted(files.items()) if name not in staged]
    print(f"project bundle: {len(staged)} files staged, {len(seen)} engine modules in its import closure")
    if missing:
        print("FAIL  reached but not staged:\n  " + "\n  ".join(missing))
        return 1
    print("ok    every engine module and data file the closure reaches is staged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
