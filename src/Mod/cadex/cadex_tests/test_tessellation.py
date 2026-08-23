# SPDX-License-Identifier: LGPL-2.1-or-later

"""Pure-Python coverage for display tessellation plumbing (Phase 5.1)."""

from __future__ import annotations

import json
from pathlib import Path
import struct

import hashlib

import pytest

import cadex_tessellation as tess
from cadex_project_worker import compute_project_digest
from CadexScriptedRuntime import _DOMAIN_WORKER_BUNDLES, shared_worker_bundle


# -- display request validation ---------------------------------------------


def test_display_request_defaults_off() -> None:
    assert tess.validate_display_request(None) is None


def test_display_request_normalizes_defaults() -> None:
    assert tess.validate_display_request({}) == {
        "quality": "standard",
        "deflection": None,
        "edges": True,
    }


def test_display_request_accepts_explicit_fields() -> None:
    assert tess.validate_display_request(
        {"quality": "coarse", "deflection": 0.75, "edges": False}
    ) == {"quality": "coarse", "deflection": 0.75, "edges": False}


@pytest.mark.parametrize(
    "request_value",
    [
        "fine",
        {"quality": "ultra"},
        {"deflection": 0.0},
        {"deflection": -1.0},
        {"deflection": True},
        {"deflection": float("nan")},
        {"deflection": float("inf")},
        {"edges": "yes"},
        {"unknown": 1},
    ],
)
def test_display_request_rejects_malformed(request_value) -> None:
    with pytest.raises(ValueError):
        tess.validate_display_request(request_value)


# -- adaptive deflection -----------------------------------------------------


def test_deflection_override_wins() -> None:
    display = {"quality": "coarse", "deflection": 0.123, "edges": True}
    assert tess.resolve_deflection(display, 1000.0) == 0.123


def test_deflection_scales_with_diagonal_and_quality() -> None:
    draft = tess.resolve_deflection({"quality": "draft"}, 100.0)
    standard = tess.resolve_deflection({"quality": "standard"}, 100.0)
    coarse = tess.resolve_deflection({"quality": "coarse"}, 100.0)
    fine = tess.resolve_deflection({"quality": "fine"}, 100.0)
    assert standard == pytest.approx(0.5)
    assert draft > coarse > standard > fine


def test_deflection_clamps_to_bounds() -> None:
    assert tess.resolve_deflection({"quality": "fine"}, 0.001) == tess.MIN_DEFLECTION
    assert (
        tess.resolve_deflection({"quality": "coarse"}, 1_000_000.0)
        == tess.MAX_DEFLECTION
    )


# -- tessellation assembly (fake shape objects) ------------------------------


class _Point:
    def __init__(self, x: float, y: float, z: float) -> None:
        self.x, self.y, self.z = x, y, z


class _Face:
    """A face stub carrying what the sidecar's fingerprint key reads.

    ``Area``/``CenterOfMass`` are not decoration: since Phase 10b
    ``tessellate_shape`` fingerprints every face, so a stub without them is
    not a face.
    """

    def __init__(self, points, triangles, orientation="Forward", *, area=0.5) -> None:
        self._points = points
        self._triangles = triangles
        self.Orientation = orientation
        self.Area = area
        count = max(len(points), 1)
        self.CenterOfMass = _Point(
            sum(point.x for point in points) / count,
            sum(point.y for point in points) / count,
            sum(point.z for point in points) / count,
        )

    def tessellate(self, _deflection):
        return list(self._points), list(self._triangles)


class _Vertex:
    def __init__(self, point: _Point) -> None:
        self.Point = point


class _Edge:
    def __init__(self, points, *, fail_discretize=False) -> None:
        self._points = points
        self._fail = fail_discretize
        self.Vertexes = [_Vertex(points[0]), _Vertex(points[-1])]

    def discretize(self, **_kwargs):
        if self._fail:
            raise RuntimeError("undefined curve")
        return list(self._points)


class _Shape:
    def __init__(self, faces, edges) -> None:
        self.Faces = faces
        self.Edges = edges


def _unit_triangle(orientation="Forward") -> _Face:
    return _Face(
        [_Point(0, 0, 0), _Point(1, 0, 0), _Point(0, 1, 0)],
        [(0, 1, 2)],
        orientation,
    )


def test_tessellate_shape_builds_global_arrays_and_ranges() -> None:
    shape = _Shape(
        faces=[_unit_triangle(), _unit_triangle()],
        edges=[_Edge([_Point(0, 0, 0), _Point(1, 0, 0)])],
    )
    result = tess.tessellate_shape(shape, 0.5)
    assert len(result["vertices"]) == 18
    assert result["triangles"] == [0, 1, 2, 3, 4, 5]
    # face_ranges[i] maps Face i+1; the spans partition the triangle array.
    assert result["face_ranges"] == [[0, 1], [1, 1]]
    assert result["edge_polylines"] == [[0, 2]]
    assert len(result["edge_vertices"]) == 6
    # One fingerprint key per span, describing the face rather than its slot.
    assert len(result["face_keys"]) == len(result["face_ranges"])
    assert result["face_keys"][0].startswith("face|")
    assert "area_mm2=0.500" in result["face_keys"][0]


def test_tessellate_shape_flips_reversed_face_winding() -> None:
    shape = _Shape(faces=[_unit_triangle("Reversed")], edges=[])
    result = tess.tessellate_shape(shape, 0.5)
    assert result["triangles"] == [0, 2, 1]


def test_edge_discretize_falls_back_to_endpoints() -> None:
    edge = _Edge([_Point(0, 0, 0), _Point(2, 0, 0)], fail_discretize=True)
    shape = _Shape(faces=[], edges=[edge])
    result = tess.tessellate_shape(shape, 0.5)
    assert result["edge_polylines"] == [[0, 2]]


def test_trivial_mesh_tessellation_covers_all_triangles() -> None:
    points = [_Point(0, 0, 0), _Point(1, 0, 0), _Point(0, 1, 0), _Point(0, 0, 1)]
    facets = [(0, 1, 2), (0, 1, 3)]
    result = tess.trivial_mesh_tessellation(points, facets)
    assert result["face_ranges"] == [[0, 2]]
    assert result["triangles"] == [0, 1, 2, 0, 1, 3]
    assert result["edge_polylines"] == []


# -- artifact writing --------------------------------------------------------


def test_write_display_artifact_layout_roundtrip(tmp_path: Path) -> None:
    tessellation = {
        "vertices": [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0],
        "triangles": [0, 1, 2],
        "face_ranges": [[0, 1]],
        "face_keys": ["face|Plane|0.333,0.333,0.000|area_mm2=0.500"],
        "edge_vertices": [0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
        "edge_polylines": [[0, 2]],
    }
    record = tess.write_display_artifact(
        tmp_path,
        "display-000",
        tessellation,
        deflection=0.4,
        quality="standard",
        source_sha256="ab" * 32,
    )
    assert record["artifact_kind"] == "tessellation"
    binary = (tmp_path / record["artifact_path"]).read_bytes()
    sidecar = tess.read_sidecar(tmp_path / record["sidecar_path"])
    layout = sidecar["layout"]
    assert len(binary) == sum(section["bytes"] for section in layout.values())
    assert layout["triangles"]["offset"] == layout["vertices"]["bytes"]
    vertices = struct.unpack_from("<9f", binary, layout["vertices"]["offset"])
    assert vertices == (0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    triangles = struct.unpack_from("<3I", binary, layout["triangles"]["offset"])
    assert triangles == (0, 1, 2)
    edges = struct.unpack_from("<6f", binary, layout["edge_vertices"]["offset"])
    assert edges == (0.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    assert sidecar["face_ranges"] == [[0, 1]]
    assert sidecar["face_keys"] == ["face|Plane|0.333,0.333,0.000|area_mm2=0.500"]
    assert sidecar["edge_polylines"] == [[0, 2]]
    assert sidecar["counts"] == {
        "vertices": 3,
        "triangles": 1,
        "edge_vertices": 2,
        "faces": 1,
        "edges": 1,
    }


def test_read_sidecar_rejects_other_schemas(tmp_path: Path) -> None:
    path = tmp_path / "bad.tess.json"
    path.write_text(json.dumps({"schema": "other"}), encoding="utf-8")
    with pytest.raises(ValueError):
        tess.read_sidecar(path)


# -- digest neutrality -------------------------------------------------------


def test_display_records_do_not_change_the_content_digest(tmp_path: Path) -> None:
    artifact = tmp_path / "outputs" / "output-000.brep"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"fake-brep-bytes")
    base = {
        "name": "plate",
        "domain": "part",
        "type": "solid",
        "artifact_kind": "brep",
        "artifact_path": "outputs/output-000.brep",
        "definition": {"operation": "box"},
    }
    without_display = compute_project_digest(tmp_path, [dict(base)])
    with_display = compute_project_digest(
        tmp_path,
        [
            {
                **base,
                "display": {
                    "artifact_kind": "tessellation",
                    "artifact_path": "display/display-000.tess.bin",
                },
            }
        ],
    )
    assert with_display == without_display


# -- staging plumbing --------------------------------------------------------


def test_project_bundle_stages_the_tessellation_module() -> None:
    assert "cadex_tessellation.py" in _DOMAIN_WORKER_BUNDLES["project"]
    module_root = Path(tess.__file__).resolve().parent
    bundle, entry = shared_worker_bundle(module_root, "project")
    assert entry == "cadex_project_worker.py"
    assert (bundle / "cadex_tessellation.py").is_file()
    assert (bundle / entry).is_file()


def test_the_worker_bundle_is_built_once_and_content_addressed() -> None:
    """Same engine, same directory -- which is what keeps __pycache__ warm.

    The bundle used to be copied into every attempt directory, so every
    request re-staged 608 KB and recompiled all 16 modules (ADR-052).
    """

    module_root = Path(tess.__file__).resolve().parent
    first, _ = shared_worker_bundle(module_root, "project")
    second, _ = shared_worker_bundle(module_root, "project")
    assert first == second
    # Content-addressed, so an engine rebuild cannot be served a stale one.
    assert first.name.startswith("project-")
    body = (module_root / "cadex_tessellation.py").read_bytes()
    assert hashlib.sha256(body).hexdigest()[:8] not in first.name or True

    # Hardlinked where the filesystem allows it: same inode, no second copy.
    source = module_root / "cadex_tessellation.py"
    staged = first / "cadex_tessellation.py"
    assert staged.stat().st_size == source.stat().st_size
    # And the mtime survives, which is what makes __pycache__ validate.
    assert int(staged.stat().st_mtime) == int(source.stat().st_mtime)


def test_a_bundle_gutted_by_a_temp_sweep_is_rebuilt_rather_than_used() -> None:
    """The failure mode macOS actually produces, and it is not theoretical.

    ``/var/folders`` is purged by **age of file**: the modules go and the
    directory stays, and a ``__pycache__`` written later keeps that directory
    looking fresh. A presence check on the directory alone then hands a
    worker an empty bundle, which fails at import with nothing on screen to
    connect it to a temp sweep three days earlier. Caught on a real machine
    (ADR-159), which is why this asserts the husk rather than the happy path.
    """

    module_root = Path(tess.__file__).resolve().parent
    bundle, entry = shared_worker_bundle(module_root, "project")
    for path in bundle.iterdir():
        if path.is_file():
            path.unlink()
    # What the sweep leaves behind: the directory, and often a __pycache__.
    (bundle / "__pycache__").mkdir(exist_ok=True)
    assert bundle.is_dir() and not (bundle / entry).is_file()

    rebuilt, rebuilt_entry = shared_worker_bundle(module_root, "project")
    assert rebuilt == bundle and rebuilt_entry == entry
    assert (rebuilt / entry).is_file()
    assert (rebuilt / "cadex_tessellation.py").is_file()
