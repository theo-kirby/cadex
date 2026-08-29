# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""End-to-end lifecycle integration for the ONE project script (Phase 2).

Runs under FreeCADCmd:

    FreeCADCmd -c "import sys; sys.path.insert(0, '<cadex_tests>'); \\
        sys.path.insert(0, '<cadex>'); \\
        import project_xscript_api_integration as m; raise SystemExit(m.main())"

Covers: write_script through prepare -> staged worker execution ->
validation (multi-domain script: params + part + partdesign + assembly of
same-script solids), edit_script unique-match replacement, set_params
value patch with revision guard, digest stability, the script store's
persisted state transitions, and the publication path: one transaction
publishing every domain into the live document, orphan GC when outputs
leave the contract, the untagged-object ownership lint with transaction
rollback, and the document-side diagnostic digest.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

MODULE_ROOT = Path(__file__).resolve().parent.parent
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

import CadexDigest  # noqa: E402
from CadexProject import CadexProjectScriptStore  # noqa: E402
from CadexScriptedDomainPublication import publish_project_candidate  # noqa: E402
from CadexScriptedDomains import (  # noqa: E402
    PROP_PROGRAM_DOMAIN,
    PROP_PROGRAM_ID,
)
from CadexScriptedRuntime import (  # noqa: E402
    DomainRuntimeFailure,
    accept_project_candidate,
    capture_project_state,
    execute_candidate,
    prepare_project_candidate,
    record_project_candidate_failure,
    validate_project_result,
)


PROJECT_SCRIPT = """
p = params(
    width=num(40, unit="mm", min=10, max=120, step=1, label="Plate Width"),
    thickness=num(6, unit="mm", min=2, max=20),
)
plate = part.box(p.width, 24, p.thickness)
profile = sketcher.sketch(
    [
        sketcher.line([0, 0], [20, 0]),
        sketcher.line([20, 0], [20, 12]),
        sketcher.line([20, 12], [0, 12]),
        sketcher.line([0, 12], [0, 0]),
    ],
    [],
)
block_profile = partdesign.sketch(
    [
        partdesign.line([0, 0], [16, 0]),
        partdesign.line([16, 0], [16, 10]),
        partdesign.line([16, 10], [0, 10]),
        partdesign.line([0, 10], [0, 0]),
    ],
    [],
)
block = partdesign.body(partdesign.pad(block_profile, p.thickness))
base = assembly.component(plate, grounded=True)
lid = assembly.component(plate, placement=[0, 0, p.thickness])
asm = assembly.assembly([base, lid])
diag = assembly.solve(asm)
result = {
    "plate": plate,
    "profile": profile,
    "block": block,
    "base": base,
    "lid": lid,
    "main_assembly": asm,
    "diagnostics": diag,
}
"""


#: The same project without the sketcher profile and the partdesign block:
#: publishing it must garbage-collect the dropped domains' live objects.
DROPPED_SCRIPT = """
p = params(
    width=num(40, unit="mm", min=10, max=120, step=1, label="Plate Width"),
    thickness=num(6, unit="mm", min=2, max=20),
)
plate = part.box(p.width, 30, p.thickness)
base = assembly.component(plate, grounded=True)
lid = assembly.component(plate, placement=[0, 0, p.thickness])
asm = assembly.assembly([base, lid])
diag = assembly.solve(asm)
result = {
    "plate": plate,
    "base": base,
    "lid": lid,
    "main_assembly": asm,
    "diagnostics": diag,
}
"""


class _Service:
    """Minimal document-affine service protocol for the project lifecycle."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root

    def _active_document(self):
        import FreeCAD as App

        return App.ActiveDocument

    def project_scope_snapshot(self):
        return {"root": str(self._root), "project_id": "test-project"}

    @staticmethod
    def provider_document_revision() -> str:
        return "fixture-document-revision"

    @staticmethod
    def active_workbench_name() -> str:
        return "CadexProject"

    @staticmethod
    def modeling_engine() -> str:
        return "xscript"

    @staticmethod
    def _partdesign_body_for_feature(_obj):
        return None


def _run_lifecycle(service, tool: str, arguments: dict) -> tuple[dict, dict]:
    captured = capture_project_state(service, tool, arguments)
    prepared = prepare_project_candidate(captured)
    execution = execute_candidate(prepared, cancellation_check=None)
    if execution.get("ok") is not True:
        record_project_candidate_failure(prepared, execution)
        raise AssertionError(f"{tool} execution failed: {execution}")
    validated = validate_project_result(prepared, execution)
    return prepared, validated


def main() -> int:
    import FreeCAD as App

    root = Path(tempfile.mkdtemp(prefix="cadex-project-lifecycle-"))
    document = App.newDocument("ProjectLifecycle")
    try:
        service = _Service(root)
        store = CadexProjectScriptStore(root)

        # 1. write_script: fresh script executes and validates
        prepared, validated = _run_lifecycle(
            service,
            "xscript.project.write_script",
            {"source": PROJECT_SCRIPT, "expected_revision": ""},
        )
        contract = validated["contract"]
        assert sorted(item["name"] for item in contract) == [
            "base",
            "block",
            "diagnostics",
            "lid",
            "main_assembly",
            "plate",
            "profile",
        ], contract
        domains = {item["name"]: item["domain"] for item in contract}
        assert domains["plate"] == "part"
        assert domains["profile"] == "sketcher"
        assert domains["block"] == "partdesign"
        assert domains["main_assembly"] == "assembly"
        assert validated["validations"]["assembly"]["status"] == "solved"
        first_digest = validated["digest"]
        assert len(first_digest) == 64

        state = store.read_state()
        assert state["working_revision"] == prepared["revision"]
        assert [spec["name"] for spec in state["param_specs"]] == [
            "width",
            "thickness",
        ]
        assert state["param_specs"][0]["label"] == "Plate Width"
        assert state["latest_candidate"]["status"] == "validated"
        assert store.read_source() == PROJECT_SCRIPT

        # 2. stale revision guard
        try:
            capture = capture_project_state(
                service,
                "xscript.project.set_params",
                {"values": {"width": 60}, "expected_revision": "wrong"},
            )
            prepare_project_candidate(capture)
        except DomainRuntimeFailure as exc:
            assert exc.payload["failure_code"] == "STALE_PROGRAM_REVISION"
        else:
            raise AssertionError("Stale revision was not rejected.")

        # 3. set_params: value-only patch, source untouched, digest changes
        working = state["working_revision"]
        prepared2, validated2 = _run_lifecycle(
            service,
            "xscript.project.set_params",
            {"values": {"width": 60}, "expected_revision": working},
        )
        assert store.read_source() == PROJECT_SCRIPT
        assert store.read_state()["param_values"] == {"width": 60.0}
        assert validated2["digest"] != first_digest

        # 4. unknown parameter rejected
        try:
            capture = capture_project_state(
                service,
                "xscript.project.set_params",
                {
                    "values": {"bogus": 1},
                    "expected_revision": store.read_state()["working_revision"],
                },
            )
            prepare_project_candidate(capture)
        except DomainRuntimeFailure as exc:
            assert exc.payload["failure_code"] == "UNKNOWN_PROJECT_PARAMETER"
        else:
            raise AssertionError("Unknown parameter was not rejected.")

        # 5. edit_script: unique-match targeted edit re-runs the whole script
        working = store.read_state()["working_revision"]
        prepared3, validated3 = _run_lifecycle(
            service,
            "xscript.project.edit_script",
            {
                "replacements": [{"old": "part.box(p.width, 24,", "new": "part.box(p.width, 30,"}],
                "expected_revision": working,
            },
        )
        assert "part.box(p.width, 30," in store.read_source()
        assert validated3["digest"] != validated2["digest"]

        # 6. ambiguous replacement rejected
        try:
            capture = capture_project_state(
                service,
                "xscript.project.edit_script",
                {
                    "replacements": [{"old": "assembly", "new": "asm"}],
                    "expected_revision": store.read_state()["working_revision"],
                },
            )
            prepare_project_candidate(capture)
        except DomainRuntimeFailure as exc:
            assert exc.payload["failure_code"] == "REPLACEMENT_NOT_UNIQUE"
        else:
            raise AssertionError("Ambiguous replacement was not rejected.")

        # 7. determinism: identical rerun of the same revision -> same digest
        working = store.read_state()["working_revision"]
        source_now = store.read_source()
        prepared4, validated4 = _run_lifecycle(
            service,
            "xscript.project.write_script",
            {"source": source_now, "expected_revision": working},
        )
        assert validated4["digest"] == validated3["digest"], (
            validated4["digest"],
            validated3["digest"],
        )

        # 8. publication: ONE transaction publishes every domain live
        publication = publish_project_candidate(service, prepared4, validated4)
        accepted = accept_project_candidate(prepared4, publication, validated4)
        assert accepted["ok"] is True, accepted
        expected_domains = {
            "plate": "part",
            "profile": "sketcher",
            "block": "partdesign",
            "main_assembly": "assembly",
        }
        for output_name, domain in expected_domains.items():
            live_name = publication["outputs"][output_name]
            obj = document.getObject(live_name)
            assert obj is not None, (output_name, live_name)
            assert str(getattr(obj, PROP_PROGRAM_ID)) == "project", output_name
            assert str(getattr(obj, PROP_PROGRAM_DOMAIN)) == domain, output_name
        state = store.read_state()
        assert state["accepted_revision"] == state["working_revision"]
        assert state["accepted_revision"] == prepared4["revision"]
        assert state["accepted_digest"] == validated4["digest"]
        assert state["latest_candidate"]["status"] == "accepted"
        digest_first = CadexDigest.document_digest(document)
        assert re.fullmatch(r"[0-9a-f]{64}", digest_first), digest_first

        # 9. republishing the same revision leaves the document digest stable
        working = store.read_state()["working_revision"]
        prepared5, validated5 = _run_lifecycle(
            service,
            "xscript.project.write_script",
            {"source": store.read_source(), "expected_revision": working},
        )
        assert validated5["digest"] == validated4["digest"]
        publication5 = publish_project_candidate(service, prepared5, validated5)
        accept_project_candidate(prepared5, publication5, validated5)
        assert publication5["outputs"] == publication["outputs"]
        digest_second = CadexDigest.document_digest(document)
        assert digest_second == digest_first, (digest_first, digest_second)

        # 10. dropping outputs (whole partdesign + sketcher domains) GCs them
        block_live = publication["outputs"]["block"]
        profile_live = publication["outputs"]["profile"]
        working = store.read_state()["working_revision"]
        prepared6, validated6 = _run_lifecycle(
            service,
            "xscript.project.write_script",
            {"source": DROPPED_SCRIPT, "expected_revision": working},
        )
        assert sorted(item["name"] for item in validated6["contract"]) == [
            "base",
            "diagnostics",
            "lid",
            "main_assembly",
            "plate",
        ], validated6["contract"]
        publication6 = publish_project_candidate(service, prepared6, validated6)
        accepted6 = accept_project_candidate(prepared6, publication6, validated6)
        assert block_live in publication6["removed"], publication6["removed"]
        assert profile_live in publication6["removed"], publication6["removed"]
        assert block_live in accepted6["removed"]
        assert document.getObject(block_live) is None
        assert document.getObject(profile_live) is None
        plate_live = publication6["outputs"]["plate"]
        assembly_live = publication6["outputs"]["main_assembly"]
        assert document.getObject(plate_live) is not None
        assert document.getObject(assembly_live) is not None
        assert store.read_state()["accepted_digest"] == validated6["digest"]

        # 11. an untagged object fails the ownership lint and aborts cleanly
        rogue = document.addObject("Part::Feature", "Rogue")
        rogue_name = str(rogue.Name)
        working = store.read_state()["working_revision"]
        prepared7, validated7 = _run_lifecycle(
            service,
            "xscript.project.write_script",
            {"source": DROPPED_SCRIPT, "expected_revision": working},
        )
        try:
            publish_project_candidate(service, prepared7, validated7)
        except RuntimeError as exc:
            assert "PUBLICATION_UNTAGGED_OBJECT" in str(exc), exc
            assert rogue_name in str(exc), exc
        else:
            raise AssertionError("The untagged object lint did not fire.")
        # transaction aborted: previous outputs stay intact, the rogue object
        # (created before the transaction) survives
        assert document.getObject(plate_live) is not None
        assert document.getObject(assembly_live) is not None
        assert document.getObject(rogue_name) is not None
        assert store.read_state()["accepted_digest"] == validated6["digest"]

        # 12. removing the rogue object lets the same candidate publish again
        document.removeObject(rogue_name)
        publication8 = publish_project_candidate(service, prepared7, validated7)
        accept_project_candidate(prepared7, publication8, validated7)
        assert publication8["outputs"]["plate"] == plate_live
        assert document.getObject(plate_live) is not None

        print(
            json.dumps(
                {
                    "ok": True,
                    "outputs": len(validated7["contract"]),
                    "digest": validated7["digest"],
                    "document_digest": CadexDigest.document_digest(document),
                    "removed_on_drop": sorted(publication6["removed"]),
                },
                sort_keys=True,
            )
        )
    finally:
        App.closeDocument(document.Name)
        shutil.rmtree(root, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
