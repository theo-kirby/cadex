# SPDX-License-Identifier: LGPL-2.1-or-later

"""Tessellation + ID-map integration for display artifacts (Phase 5.1).

Runs under FreeCADCmd:

    FreeCADCmd -c "import sys; sys.path.insert(0, '<cadex_tests>'); \\
        import tessellation_id_map_integration as m; raise SystemExit(m.main())"

Corpus: box, cone, torus, drilled+filleted plate (BREP) plus one mesh
output. Verifies for every BREP output: 100% face coverage (each face
contributes at least one triangle), face ranges exactly partition the
triangle array, every edge has a polyline, the binary buffer matches the
sidecar layout; coarse produces fewer triangles than fine on the plate;
and the content digest is identical with display off and on.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import struct
import sys
import tempfile

MODULE_ROOT = Path(__file__).resolve().parent.parent
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from CadexProject import CadexProjectScriptStore  # noqa: E402
from CadexScriptedRuntime import (  # noqa: E402
    capture_project_state,
    execute_candidate,
    prepare_project_candidate,
    record_project_candidate_failure,
    validate_project_result,
)
import cadex_tessellation  # noqa: E402


CORPUS_SCRIPT = """
box = part.box(30, 20, 10)
cone = part.cone(8, 3, 12)
donut = part.torus(10, 3)
drilled = part.cut(
    part.fillet(part.box(60, 40, 6), 1.5),
    [
        part.cylinder(3, 12, origin=[12, 10, -3]),
        part.cylinder(3, 12, origin=[48, 10, -3]),
        part.cylinder(3, 12, origin=[12, 30, -3]),
        part.cylinder(3, 12, origin=[48, 30, -3]),
    ],
)
skin = mesh.from_shape(box, linear_deflection=0.4)
result = {"box": box, "cone": cone, "donut": donut, "drilled": drilled, "skin": skin}
"""


class _Service:
    def __init__(self, project_root: Path) -> None:
        self._root = project_root

    def _active_document(self):
        import FreeCAD as App

        return App.ActiveDocument

    def project_scope_snapshot(self):
        return {"root": str(self._root), "project_id": "tess-integration"}

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


def _run(service, arguments: dict) -> tuple[dict, dict]:
    captured = capture_project_state(
        service, "xscript.project.write_script", arguments
    )
    prepared = prepare_project_candidate(captured)
    execution = execute_candidate(prepared, cancellation_check=None)
    if execution.get("ok") is not True:
        record_project_candidate_failure(prepared, execution)
        raise AssertionError(f"corpus execution failed: {execution}")
    return prepared, validate_project_result(prepared, execution)


def _verify_brep_display(staging: Path, item: dict) -> dict:
    name = item["name"]
    display = item.get("display")
    assert isinstance(display, dict), f"{name}: BREP output has no display record"
    facts = item["facts"]
    sidecar = cadex_tessellation.read_sidecar(staging / display["sidecar_path"])
    counts = sidecar["counts"]
    face_ranges = sidecar["face_ranges"]
    edge_polylines = sidecar["edge_polylines"]

    # ID-map cardinality matches the exact 1-based topology enumeration.
    assert counts["faces"] == facts["faces"], (name, counts, facts["faces"])
    assert counts["edges"] == facts["edges"], (name, counts, facts["edges"])

    # 100% face coverage and an exact partition of the triangle array.
    assert all(count > 0 for _start, count in face_ranges), (name, face_ranges)
    cursor = 0
    for start, count in face_ranges:
        assert start == cursor, (name, face_ranges)
        cursor += count
    assert cursor == counts["triangles"], (name, cursor, counts)

    # Every edge has a polyline of at least two points.
    assert len(edge_polylines) == facts["edges"], name
    assert all(count >= 2 for _start, count in edge_polylines), (
        name,
        edge_polylines,
    )
    edge_cursor = 0
    for start, count in edge_polylines:
        assert start == edge_cursor, (name, edge_polylines)
        edge_cursor += count
    assert edge_cursor == counts["edge_vertices"], name

    # Binary buffer matches the declared layout exactly.
    binary = (staging / display["artifact_path"]).read_bytes()
    layout = sidecar["layout"]
    assert len(binary) == sum(section["bytes"] for section in layout.values()), name
    assert layout["vertices"]["bytes"] == counts["vertices"] * 12, name
    assert layout["triangles"]["bytes"] == counts["triangles"] * 12, name
    assert layout["edge_vertices"]["bytes"] == counts["edge_vertices"] * 12, name
    triangle_values = struct.unpack_from(
        f"<{counts['triangles'] * 3}I", binary, layout["triangles"]["offset"]
    )
    assert all(value < counts["vertices"] for value in triangle_values), name
    return sidecar


def main() -> int:
    import FreeCAD as App

    root = Path(tempfile.mkdtemp(prefix="cadex-tess-integration-"))
    document = App.newDocument("TessIntegration")
    report: dict = {}
    try:
        service = _Service(root)
        store = CadexProjectScriptStore(root)

        # Run 1: display off — the digest baseline.
        prepared_off, validated_off = _run(
            service, {"source": CORPUS_SCRIPT, "expected_revision": ""}
        )
        assert all(
            item.get("display") is None for item in validated_off["outputs"]
        ), "display must be off by default"

        # Run 2: standard display on every output.
        working = str(store.read_state()["working_revision"])
        prepared_std, validated_std = _run(
            service,
            {
                "source": CORPUS_SCRIPT,
                "expected_revision": working,
                "display": {"quality": "standard"},
            },
        )
        assert validated_std["digest"] == validated_off["digest"], (
            "display artifacts changed the content digest"
        )
        staging = Path(prepared_std["staging"])
        by_name = {item["name"]: item for item in validated_std["outputs"]}
        sidecars = {}
        for name in ("box", "cone", "donut", "drilled"):
            sidecars[name] = _verify_brep_display(staging, by_name[name])

        # Mesh output: trivial one-range map over its own triangles.
        skin = by_name["skin"]
        assert isinstance(skin.get("display"), dict), "mesh output has no display"
        skin_sidecar = cadex_tessellation.read_sidecar(
            staging / skin["display"]["sidecar_path"]
        )
        assert skin_sidecar["face_ranges"] == [
            [0, skin_sidecar["counts"]["triangles"]]
        ]
        assert skin_sidecar["counts"]["triangles"] == skin["facts"]["facets"]

        # Run 3: coarse < fine on the filleted plate.
        working = str(store.read_state()["working_revision"])
        _prepared_coarse, validated_coarse = _run(
            service,
            {
                "source": CORPUS_SCRIPT,
                "expected_revision": working,
                "display": {"quality": "coarse"},
            },
        )
        working = str(store.read_state()["working_revision"])
        _prepared_fine, validated_fine = _run(
            service,
            {
                "source": CORPUS_SCRIPT,
                "expected_revision": working,
                "display": {"quality": "fine"},
            },
        )

        def _triangles(validated: dict, name: str) -> int:
            item = next(
                item for item in validated["outputs"] if item["name"] == name
            )
            return int(item["display"]["counts"]["triangles"])

        coarse = _triangles(validated_coarse, "drilled")
        standard = _triangles(validated_std, "drilled")
        fine = _triangles(validated_fine, "drilled")
        assert coarse < fine, (coarse, fine)
        assert coarse <= standard <= fine, (coarse, standard, fine)
        assert validated_fine["digest"] == validated_off["digest"]

        report = {
            "ok": True,
            "digest": validated_off["digest"],
            "plate_triangles": {
                "coarse": coarse,
                "standard": standard,
                "fine": fine,
            },
            "faces": {
                name: sidecars[name]["counts"]["faces"] for name in sidecars
            },
        }
    finally:
        App.closeDocument(document.Name)
        shutil.rmtree(root, ignore_errors=True)

    print("TESSELLATION-INTEGRATION " + json.dumps(report, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
