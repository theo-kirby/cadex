# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Native Blender recipes: contracts, sandbox and actual geometry execution."""

import json
import os
from pathlib import Path
import sys
import socket
from types import SimpleNamespace

import pytest

import CadexScriptedDomains as domains
from cadex_domain_api import create_domain_api
from cadex_mesh_api import contains_blender_recipe, payload_tree_is_deterministic
from cadex_blender_runner import run_recipe, sandbox_command, validate_geometry


def api(domain="mesh"):
    pack = next(p for p in domains.XSCRIPT_WORKBENCH_PACKS.values() if p.domain == domain)
    return create_domain_api(domain, pack.api_exports, pack.output_types)


CUBE = '''
import bmesh
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=values.get("size", 10))
data = bpy.data.meshes.new("cube")
bm.to_mesh(data)
bm.free()
result = bpy.data.objects.new("cube", data)
bpy.context.scene.collection.objects.link(result)
'''


def test_recipe_declaration_composes_and_is_described():
    mesh, part = api(), api("part")
    value = mesh.blender(CUBE, version="5.3.0", inputs={"mount": mesh.from_shape(part.box(2, 3, 4))},
                         values={"size": 12, "frame": [1, 2, 3]})
    placed = mesh.transform(value, translation=[0, 0, 10])
    assert contains_blender_recipe(placed.to_payload())
    assert not payload_tree_is_deterministic(placed.to_payload())
    with pytest.raises(ValueError, match="Blender"):
        part.shape_from_mesh(placed)
    source = "skin = mesh.blender(" + repr(CUBE) + ", version='5.3.0')\nresult = {'skin': skin}"
    domains.validate_program_source(source)  # Recipe imports are not outer imports.


@pytest.mark.parametrize("kwargs", [
    {"version": "latest"}, {"source": "if"}, {"source": ""},
    {"seed": True}, {"seed": -1}, {"values": {"x": float("nan")}},
    {"values": []}, {"inputs": {"bad-name": 1}}, {"inputs": {"part": 1}},
])
def test_recipe_refuses_invalid_declarations(kwargs):
    arguments = {"source": CUBE, "version": "5.3.0", **kwargs}
    with pytest.raises(ValueError):
        api().blender(**arguments)


@pytest.mark.parametrize("data", [
    {}, {"vertices": [[0, 0, 0]] * 3, "triangles": [[0, 1, 2]]},
    {"vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0]], "triangles": [[0, 1, 3]]},
    {"vertices": [[0, 0, 0], [1, 0, 0], [0, float("inf"), 0]], "triangles": [[0, 1, 2]]},
])
def test_child_geometry_is_untrusted(data):
    with pytest.raises(ValueError):
        validate_geometry(data)


def test_no_unsandboxed_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "win32")
    with pytest.raises(ValueError, match="no OS sandbox"):
        sandbox_command(tmp_path / "blender", tmp_path / "worker.py", tmp_path / "request.json", tmp_path)


def test_recipe_digest_tracks_connectivity_source_and_runtime(monkeypatch, tmp_path):
    import cadex_blender_runner
    import cadex_mesh_worker

    points = [SimpleNamespace(x=x, y=y, z=z) for x, y, z in
              [(0, 0, 0), (1, 0, 0), (0, 1, 0)]]
    mesh = SimpleNamespace(Topology=(points, [(0, 1, 2)]),
                           write=lambda path: Path(path).write_bytes(b"mesh"))
    (tmp_path / "outputs").mkdir()
    monkeypatch.setattr(cadex_mesh_worker, "build_mesh", lambda *args: mesh)
    monkeypatch.setattr(cadex_mesh_worker, "canonical_mesh", lambda value: value)
    monkeypatch.setattr(cadex_mesh_worker, "mesh_facts", lambda value: {"points": 3, "facets": 1})
    monkeypatch.setattr(cadex_blender_runner, "runtime_identity", lambda: "runtime-a")

    def digest(source=CUBE):
        value = api().blender(source, version="5.3.0")
        return cadex_mesh_worker.serialize_mesh_output(
            tmp_path, 0, {"name": "skin", "type": "mesh"}, value)["geometry_sha256"]

    original = digest()
    assert digest() == original
    mesh.Topology = (points, [(0, 2, 1)])
    assert digest() != original  # Same vertex set, different winding.
    mesh.Topology = (points, [(0, 1, 2)])
    assert digest("# changed recipe\n" + CUBE) != original
    monkeypatch.setattr(cadex_blender_runner, "runtime_identity", lambda: "runtime-b")
    assert digest() != original


@pytest.fixture
def blender(monkeypatch):
    value = os.environ.get("CADEX_BLENDER_EXECUTABLE")
    if not value:
        pytest.skip("Set CADEX_BLENDER_EXECUTABLE to exercise the real OS-sandboxed worker")
    assert Path(value).is_file(), value
    return value


def build(root, source=CUBE, values=None, inputs=None, version="5.3.0"):
    return run_recipe(root, source, {"version": version, "seed": 0, "values": values or {}}, inputs or {})


def test_native_recipe_rebuild_modifiers_inputs_and_units(blender, tmp_path):
    first = build(tmp_path / "a", values={"size": 12})
    assert len(first["triangles"]) == 12
    assert max(p[0] for p in first["vertices"]) == 6
    assert build(tmp_path / "b", values={"size": 12}) == first
    source = '''
result = inputs["mount"]
result.location.x = values["offset"]
mod = result.modifiers.new("round", 'BEVEL')
mod.width = 1
mod.segments = 2
'''
    changed = build(tmp_path / "c", source, {"offset": 20}, {"mount": first})
    assert len(changed["triangles"]) > 12
    assert min(p[0] for p in changed["vertices"]) == pytest.approx(14)
    assert max(p[0] for p in changed["vertices"]) == pytest.approx(26)


def test_native_recipe_refuses_wrong_version_and_missing_result(blender, tmp_path):
    with pytest.raises(ValueError, match="runtime is"):
        build(tmp_path / "version", version="0.0.0")
    with pytest.raises(ValueError, match="Assign one Blender mesh Object"):
        build(tmp_path / "empty", "pass")


def test_native_sandbox_denies_host_files_network_and_writes(blender, tmp_path):
    secret = tmp_path / "private.txt"
    secret.write_text("must not be readable")
    outside = tmp_path / "escaped.txt"
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    probes = '''
import socket
try:
    open(SECRET).read()
except OSError:
    pass
else:
    raise AssertionError("host file readable")
try:
    open(OUTSIDE, "w").write("escaped")
except OSError:
    pass
else:
    raise AssertionError("host file writable")
try:
    s = socket.socket()
    s.settimeout(1)
    s.connect(("127.0.0.1", PORT))
except OSError:
    pass
else:
    raise AssertionError("network available")
'''.replace("SECRET", repr(str(secret))).replace("OUTSIDE", repr(str(outside))).replace("PORT", str(port))
    try:
        assert build(tmp_path / "sandbox", probes + CUBE)["triangles"]
    finally:
        server.close()
    assert not outside.exists()


def test_native_recipe_timeout(blender, tmp_path, monkeypatch):
    import cadex_blender_runner
    monkeypatch.setattr(cadex_blender_runner, "TIMEOUT_SECONDS", 0.75)
    with pytest.raises(ValueError, match="timed out"):
        build(tmp_path, "while True: pass")


def test_hybrid_project_lifecycle(blender, tmp_path):
    """Real CAD → bpy → mesh, accepted rebuild, parameter sweep and rollback."""
    import test_cadexd_lifecycle as lifecycle

    if lifecycle.FREECADCMD is None:
        pytest.skip("No FreeCADCmd")
    source = (Path(__file__).resolve().parents[4] / "examples" / "blender_enclosure.py").read_text()
    client = lifecycle._spawn_cadexd()
    try:
        assert client.request("open_project", {"project_root": str(tmp_path)})["ok"]
        written = client.request("write_script", {"source": source, "expected_revision": "",
                                                  "display": {"quality": "standard"}})
        assert written["ok"], written
        assert written["display"]["mounts"]["artifact_kind"] == "brep"
        assert written["display"]["skin"]["artifact_kind"] == "mesh"
        check = client.request("inspect", {"scope": "output", "target": "skin_check"})
        assert check["ok"], check
        # The declared check must actually find a sound closed shell, not
        # merely return a mesh-shaped artifact from a successful subprocess.
        assert '"sound": true' in json.dumps(check), check
        digest = written["digest"]
        changed = client.request("set_params", {"values": {"mount_spacing": 56},
            "expected_revision": written["model_state"]["next_write_expected_revision"]})
        assert changed["ok"] and changed["digest"] != digest, changed
        restored = client.request("set_params", {"values": {"mount_spacing": 42},
            "expected_revision": changed["model_state"]["next_write_expected_revision"]})
        assert restored["ok"] and restored["digest"] == digest, restored
        bad = client.request("write_script", {
            "source": source.replace("import bmesh", "raise RuntimeError('recipe failure')\nimport bmesh"),
            "expected_revision": restored["model_state"]["next_write_expected_revision"]})
        assert not bad["ok"], bad
        assert (tmp_path / "script.py").read_text() == source
        printed = client.request("export_printable", {"printable": ["skin"]})
        assert printed["ok"], printed
        assert list((tmp_path / "print").glob("*.stl")), printed
    finally:
        lifecycle._stop(client)
    client = lifecycle._spawn_cadexd()
    try:
        reopened = client.request("open_project", {"project_root": str(tmp_path)})
        assert reopened["ok"], reopened
        assert reopened["restore"]["matches_accepted"], reopened
    finally:
        lifecycle._stop(client)
