# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Headless project rebuild: re-run THE script, verify the content digest.

The FreeCAD document is a rebuildable artifact (docs/VISION.md): this driver
re-executes a project's ``script.py`` from scratch into a fresh document and
compares the resulting content digest with the accepted digest recorded in
``script.json``. Run it under FreeCADCmd::

    FreeCADCmd -c "import sys; sys.path.insert(0, '<cadex>'); \\
        import cadex_rebuild; raise SystemExit(cadex_rebuild.main(['<project_root>']))"

or via ``pixi run rebuild <project_root>``.

Exit codes: 0 digest matches (or no accepted digest recorded yet — printed
as such), 2 digest mismatch, 1 rebuild failure. Re-accepting the identical
revision leaves the content-addressed store state unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


class _RebuildService:
    """Document-affine service shim for one headless rebuild."""

    def __init__(self, project_root: Path, document: Any) -> None:
        self._root = project_root
        self._document = document

    def _active_document(self):
        return self._document

    def project_scope_snapshot(self):
        return {"root": str(self._root), "project_id": "rebuild"}

    def provider_document_revision(self) -> str:
        return f"rebuild-{getattr(self._document, 'Uid', '')}"

    @staticmethod
    def active_workbench_name() -> str:
        return "CadexProject"

    @staticmethod
    def modeling_engine() -> str:
        return "xscript"

    @staticmethod
    def _partdesign_body_for_feature(_obj):
        return None


def rebuild_project(project_root: str | Path) -> dict[str, Any]:
    """Re-run the project script into a fresh document; return the report."""

    import FreeCAD as App

    module_root = Path(__file__).resolve().parent
    if str(module_root) not in sys.path:
        sys.path.insert(0, str(module_root))

    from CadexScriptStore import CadexProjectScriptStore
    from CadexScriptedRuntime import run_project_lifecycle

    root = Path(str(project_root)).expanduser().resolve()
    store = CadexProjectScriptStore(root)
    source = store.read_source()
    if not source.strip():
        raise RuntimeError(f"No project script found at {store.script_path}.")
    state = store.read_state()
    accepted_digest_before = str(state.get("accepted_digest") or "")

    document = App.newDocument("CadexRebuild")
    try:
        service = _RebuildService(root, document)
        payload = run_project_lifecycle(
            service,
            "xscript.project.write_script",
            {
                "source": source,
                "expected_revision": str(state.get("working_revision") or ""),
            },
        )
        if payload.get("ok") is not True:
            raise RuntimeError(
                f"Rebuild execution failed: {payload.get('error')!r} "
                f"({payload.get('failure_code')})"
            )

        import CadexDigest

        return {
            "ok": True,
            "project_root": str(root),
            "outputs": len(payload["outputs"]),
            "digest": str(payload["digest"]),
            "accepted_digest_before": accepted_digest_before,
            "digest_matches_accepted": (
                str(payload["digest"]) == accepted_digest_before
                if accepted_digest_before
                else None
            ),
            "document_digest": CadexDigest.document_digest(document),
        }
    finally:
        App.closeDocument(document.Name)


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 1 or not str(arguments[0]).strip():
        print("usage: cadex_rebuild <project_root>", file=sys.stderr, flush=True)
        return 1
    # flush=True: the pixi task exits via SystemExit straight from
    # FreeCADCmd -c, which skips the interpreter teardown that would flush a
    # block-buffered (piped) stdout — without it the report line is lost.
    try:
        report = rebuild_project(arguments[0])
    except Exception as exc:  # structured single-line failure for CI logs
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True), flush=True)
        return 1
    print(json.dumps(report, sort_keys=True), flush=True)
    if report["digest_matches_accepted"] is False:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
