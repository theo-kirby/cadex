# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Headless tests for the Mesh agent's Part Design mode: mode plumbing, the
geometry-validation feedback loop, the mesh_cad library and the export_stl
tool. Mock backend only — no network, no `claude` needed.

Run:
    blender --background --factory-startup --python tests/python/bl_mesh_agent_cad.py
"""

import os
import sys
import tempfile
import textwrap

import bpy

# Make the repo's add-on importable regardless of which Blender runs this.
_REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "..", ".."))
sys.path.insert(0, os.path.join(_REPO, "scripts", "addons_core"))

import mesh_agent  # noqa: E402
from mesh_agent import agent as agent_module  # noqa: E402
from mesh_agent import model as model_module  # noqa: E402
from mesh_agent import modes as modes_module  # noqa: E402
from mesh_agent import tools as tools_module  # noqa: E402
from mesh_agent import validation as validation_module  # noqa: E402
from mesh_agent.mock_backend import MockBackend  # noqa: E402

FAILURES = []

GEAR_MODEL = """\
from mesh_model import params, Float
import mesh_cad as cad

p = params(
    module=Float(1.5, min=0.8, max=3.0, name="Module"),
)

cad.spur_gear("TestGear", p.module, 16, 6.0, bore=4.0)
"""

OPEN_BOX_MODEL = """\
import bpy
import bmesh

mesh = bpy.data.meshes.new("OpenBox")
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=10.0)
bm.faces.ensure_lookup_table()
bm.faces.remove(bm.faces[0])
bm.to_mesh(mesh)
bm.free()
obj = bpy.data.objects.new("OpenBox", mesh)
bpy.context.collection.objects.link(obj)
"""


def check(condition, label):
    status = "ok" if condition else "FAIL"
    print("  {:s}: {:s}".format(status, label))
    if not condition:
        FAILURES.append(label)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # This suite exercises the local (bpy) model path. Cadex is the default
    # mode since cadex ADR-024, so each test states the path it is testing.
    bpy.context.scene.mesh_agent_mode = 'GENERAL'


def analyze_one(obj):
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    return validation_module.analyze_object(obj, depsgraph)


def is_clean(stats):
    return not validation_module._issues(stats)


# -- 1. mode plumbing --------------------------------------------------------

def test_mode_plumbing():
    print("test_mode_plumbing")
    # Deliberately not reset_scene(): that helper pins GENERAL for the
    # local-path tests, and what is under test here is the factory default.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    # Cadex is the default since cadex ADR-024 -- the engine is the product.
    check(modes_module.get_mode(scene) == 'CADEX', "default mode is CADEX")
    check(modes_module.DEFAULT_MODE == 'CADEX',
          "the module agrees with the scene default")
    check(modes_module.backend_kind(scene) == "cadexd",
          "the default mode routes to the engine")
    scene.mesh_agent_mode = 'GENERAL' 
    check(modes_module.system_prompt_for('GENERAL') == agent_module.SYSTEM_PROMPT,
          "GENERAL prompt is the base prompt")
    part_prompt = modes_module.system_prompt_for('PART_DESIGN')
    check(part_prompt.startswith(agent_module.SYSTEM_PROMPT),
          "PART_DESIGN prompt starts with the base prompt")
    check(modes_module.CAD_OVERLAY in part_prompt,
          "PART_DESIGN prompt contains the CAD overlay")
    check(not modes_module.validation_enabled(scene),
          "validation off in GENERAL")

    # A mode switch between turns must update the backend's system prompt in
    # place without touching the session id (so --resume continuity holds).
    class PromptBackend(MockBackend):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.system_prompt = modes_module.system_prompt_for(
                modes_module.get_mode(bpy.context.scene))

    agent = agent_module.Agent()
    holder = {}

    def factory(bridge):
        script = [[("result", False, "ok")], [("result", False, "ok")]]
        backend = PromptBackend(script=script, bridge_port=bridge.port,
                                bridge_token=bridge.token)
        holder["backend"] = backend
        return backend

    agent.backend_factory = factory
    agent._undo_push = lambda message: None
    try:
        import time
        def run_turn(prompt):
            started = agent.start_turn(prompt)
            deadline = time.monotonic() + 30.0
            while agent.busy and time.monotonic() < deadline:
                agent.drain()
                time.sleep(0.01)
            return started and not agent.busy

        check(run_turn("first turn"), "first turn completes")
        backend = holder["backend"]
        check(backend.system_prompt == agent_module.SYSTEM_PROMPT,
              "backend starts with the GENERAL prompt")
        session_before = backend.session_id

        scene.mesh_agent_mode = 'PART_DESIGN'
        check(run_turn("second turn"), "second turn completes")
        check(backend.system_prompt ==
              modes_module.system_prompt_for('PART_DESIGN'),
              "mode switch updated the backend system prompt")
        check(backend.session_id == session_before,
              "session id untouched by the mode switch")
        check(any(message.role == "status" and "Part Design" in message.text
                  for message in agent.history.messages),
              "mode change noted in the transcript")
    finally:
        agent.shutdown()


# -- 2. validation gating ----------------------------------------------------

def test_validation_gating():
    print("test_validation_gating")
    reset_scene()
    scene = bpy.context.scene

    content, is_error = tools_module.execute("write_script",
                                             {"content": GEAR_MODEL})
    check(not is_error, "write_script succeeds in GENERAL")
    check("Geometry check" not in content[0]["text"],
          "no geometry report in GENERAL mode")

    scene.mesh_agent_mode = 'PART_DESIGN'
    content, is_error = tools_module.execute("write_script",
                                             {"content": GEAR_MODEL})
    check(not is_error, "write_script succeeds in PART_DESIGN")
    text = content[0]["text"]
    check("Geometry check" in text, "geometry report in PART_DESIGN mode")
    check("TestGear" in text and "OK" in text,
          "report covers the gear part")

    content, is_error = tools_module.execute(
        "set_params", {"params": {"module": 2.0}})
    check(not is_error and "Geometry check" in content[0]["text"],
          "set_params result carries the geometry report too")

    # A defective build must be called out to the model.
    content, is_error = tools_module.execute("write_script",
                                             {"content": OPEN_BOX_MODEL})
    check(not is_error and "ISSUES" in content[0]["text"]
          and "open-boundary" in content[0]["text"],
          "defective part flagged with ISSUES in the report")


# -- 3. validation on known-bad geometry ------------------------------------

def _new_mesh_object(name, verts, faces, edges=()):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(list(verts), list(edges), list(faces))
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def test_validation_analysis():
    print("test_validation_analysis")
    reset_scene()
    import bmesh

    # Open cube: one face removed -> 4 open boundary edges, not watertight.
    mesh = bpy.data.meshes.new("OpenCube")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bm.faces.ensure_lookup_table()
    bm.faces.remove(bm.faces[0])
    bm.to_mesh(mesh)
    bm.free()
    open_cube = bpy.data.objects.new("OpenCube", mesh)
    bpy.context.collection.objects.link(open_cube)
    stats = analyze_one(open_cube)
    check(stats["boundary_edges"] == 4, "open cube: 4 boundary edges "
          "(got {:d})".format(stats["boundary_edges"]))
    check(not is_clean(stats), "open cube flagged")

    # Two overlapping cube shells joined in one mesh -> self-intersections.
    mesh = bpy.data.meshes.new("Overlap")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    result = bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.translate(bm, verts=result["verts"], vec=(1.0, 0.7, 0.3))
    bm.to_mesh(mesh)
    bm.free()
    overlap = bpy.data.objects.new("Overlap", mesh)
    bpy.context.collection.objects.link(overlap)
    stats = analyze_one(overlap)
    check(stats["self_intersections"] > 0,
          "overlapping shells: self-intersections detected")

    # Three faces sharing one edge -> non-manifold.
    tee = _new_mesh_object(
        "Tee",
        [(0, 0, 0), (0, 1, 0), (1, 0, 0), (-1, 0, 0), (0, 0, 1)],
        [(0, 1, 2), (0, 1, 3), (0, 1, 4)])
    stats = analyze_one(tee)
    check(stats["non_manifold_edges"] >= 1,
          "3-faces-per-edge: non-manifold edge detected")

    # A lone vertex -> loose.
    lone = _new_mesh_object("Lone", [(0, 0, 0)], [])
    stats = analyze_one(lone)
    check(stats["loose_verts"] == 1, "lone vertex flagged as loose")

    # And a clean closed cube passes.
    mesh = bpy.data.meshes.new("Solid")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bm.to_mesh(mesh)
    bm.free()
    solid = bpy.data.objects.new("Solid", mesh)
    bpy.context.collection.objects.link(solid)
    stats = analyze_one(solid)
    check(is_clean(stats), "closed cube reads clean")


# -- 4. mesh_cad -------------------------------------------------------------

def test_mesh_cad():
    print("test_mesh_cad")
    reset_scene()
    import mesh_cad as cad

    # Involute gear: manifold, watertight, correct outside diameter.
    gear = cad.spur_gear("Gear", 1.5, 20, 6.0, bore=4.0)
    stats = analyze_one(gear)
    check(is_clean(stats), "spur_gear is manifold and watertight")
    outside = 1.5 * (20 + 2)
    check(abs(stats["dimensions"][0] - outside) < 0.05
          and abs(stats["dimensions"][1] - outside) < 0.05,
          "spur_gear OD == module*(teeth+2) (got {:.3f})".format(
              stats["dimensions"][0]))
    check(abs(stats["dimensions"][2] - 6.0) < 1e-4, "spur_gear thickness")

    hub_gear = cad.spur_gear("HubGear", 1.5, 20, 6.0, bore=4.0,
                             hub_d=10.0, hub_h=4.0)
    stats = analyze_one(hub_gear)
    check(is_clean(stats), "spur_gear with hub is manifold")
    check(abs(stats["dimensions"][2] - 10.0) < 1e-4,
          "hub adds height (thickness + hub_h)")

    solid_gear = cad.spur_gear("SolidGear", 2.0, 12, 5.0)
    check(is_clean(analyze_one(solid_gear)), "boreless gear is manifold")

    check(abs(cad.gear_center_distance(1.5, 12, 28) - 30.0) < 1e-9,
          "gear_center_distance exact")

    # Boolean difference: one manifold result, cutter consumed.
    box = cad.plate("Box", 20, 20, 10)
    cutter = cad.cylinder("Cutter", 6, 12, at=(0, 0, -1))
    objects_before = len(bpy.data.objects)
    cad.difference(box, cutter)
    check(len(bpy.data.objects) == objects_before - 1,
          "difference consumed the cutter object")
    check(bpy.data.objects.get("Cutter") is None
          and bpy.data.meshes.get("Cutter") is None,
          "cutter object and mesh removed from bpy.data")
    check(is_clean(analyze_one(box)), "difference result is manifold")

    # hole(): plate stays watertight, counterbore included.
    plate = cad.plate("HolePlate", 40, 30, 5, corner_radius=4)
    verts_before = len(plate.data.vertices)
    cad.hole(plate, 3.4, at=(10, 5), cbore_d=6.0, cbore_depth=2.0)
    check(len(plate.data.vertices) > verts_before, "hole cut new geometry")
    check(is_clean(analyze_one(plate)), "plate watertight after hole")

    # Blind hole and countersink variants stay manifold too.
    plate2 = cad.plate("BlindPlate", 30, 30, 8)
    cad.hole(plate2, 4.0, at=(-5, 0), depth=5.0)
    cad.hole(plate2, 3.0, at=(8, 0), csink_d=6.0)
    check(is_clean(analyze_one(plate2)), "blind + countersunk holes manifold")

    # rounded_box and chamfer keep solids clean.
    rbox = cad.rounded_box("RBox", 20, 15, 10, radius=2)
    check(is_clean(analyze_one(rbox)), "rounded_box is manifold")
    chamfered = cad.chamfer(cad.plate("Cham", 20, 20, 5), width=0.5)
    check(is_clean(analyze_one(chamfered)), "chamfer keeps the solid clean")

    # finalize() welds duplicate vertices.
    doubled = _new_mesh_object(
        "Doubled",
        [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 0, 0), (1, 1, 0), (0, 1, 0)],
        [(0, 1, 2), (3, 4, 5)])
    cad.finalize(doubled)
    check(len(doubled.data.vertices) == 4,
          "finalize merged doubled vertices (got {:d})".format(
              len(doubled.data.vertices)))


# -- overlay worked example --------------------------------------------------

def _overlay_example_source():
    """Extract the worked-example code block from the CAD overlay, so the
    documented snippet is exactly what gets tested."""
    lines = modes_module.CAD_OVERLAY.splitlines()
    start = next(i for i, line in enumerate(lines)
                 if line.startswith("Worked example"))
    block = []
    for line in lines[start + 1:]:
        if line and not line.startswith(" "):
            break
        block.append(line)
    return textwrap.dedent("\n".join(block)).strip() + "\n"


def test_overlay_worked_example():
    print("test_overlay_worked_example")
    reset_scene()
    source = _overlay_example_source()
    check("spur_gear" in source and "params(" in source,
          "extracted the worked example from the overlay")
    model_module.set_script(source)
    ok, report = model_module.rebuild()
    check(ok, "overlay worked example rebuilds OK ({:s})".format(
        report.splitlines()[-1] if not ok else "ok"))
    collection = bpy.data.collections.get(model_module.COLLECTION_NAME)
    names = sorted(obj.name for obj in collection.all_objects)
    check(names == ["BasePlate", "Pinion", "Wheel"],
          "worked example builds the three documented parts (got {!s})".format(names))
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in collection.all_objects:
        stats = validation_module.analyze_object(obj, depsgraph)
        check(is_clean(stats),
              "worked example part {:s} is manifold".format(obj.name))
    # The documented parameters must exist so the example is truly parametric.
    specs = {spec["id"] for spec in model_module.load_specs(bpy.context.scene)}
    check({"module", "thickness", "clearance"} <= specs,
          "worked example declares module/thickness/clearance")
    # Rebuild determinism: a second run yields the same parts.
    ok, _report = model_module.rebuild()
    names_again = sorted(obj.name for obj in collection.all_objects)
    check(ok and names_again == names, "worked example rebuild deterministic")


# -- 5. export_stl -----------------------------------------------------------

def test_export_stl():
    print("test_export_stl")
    reset_scene()
    content, is_error = tools_module.execute("write_script",
                                             {"content": GEAR_MODEL})
    check(not is_error, "model built")

    directory = os.path.join(tempfile.gettempdir(), "mesh_cad_stl_test")
    content, is_error = tools_module.execute("export_stl",
                                             {"directory": directory})
    check(not is_error, "export_stl succeeds")
    text = content[0]["text"]
    check("TestGear" in text, "report names the exported part")

    path = os.path.join(directory, "TestGear.stl")
    check(os.path.isfile(path), "STL file written")
    if os.path.isfile(path):
        import re
        match = re.search(r"\((\d+) triangles\)", text)
        check(match is not None, "report includes a triangle count")
        if match:
            triangles = int(match.group(1))
            expected = 84 + 50 * triangles  # binary STL: header + 50 B/tri
            size = os.path.getsize(path)
            check(size == expected,
                  "binary STL size matches triangle count "
                  "({:d} vs {:d})".format(size, expected))
        os.remove(path)

    content, is_error = tools_module.execute(
        "export_stl", {"objects": ["NoSuchObject"]})
    check(is_error, "missing object -> is_error")

    tools_module.execute("write_script", {"content": ""})
    content, is_error = tools_module.execute("export_stl", {})
    check(is_error, "empty model -> is_error")


# -- 6. mode persistence -----------------------------------------------------

def test_mode_persists_through_save_load():
    print("test_mode_persists_through_save_load")
    reset_scene()
    bpy.context.scene.mesh_agent_mode = 'PART_DESIGN'
    path = os.path.join(tempfile.gettempdir(), "mesh_mode_persist.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    check(bpy.context.scene.mesh_agent_mode == modes_module.DEFAULT_MODE,
          "fresh scene back to the default mode ({:s})".format(
              modes_module.DEFAULT_MODE))
    bpy.ops.wm.open_mainfile(filepath=path)
    try:
        check(bpy.context.scene.mesh_agent_mode == 'PART_DESIGN',
              "mode restored from the .blend")
    finally:
        if os.path.exists(path):
            os.remove(path)


def main():
    print("=== bl_mesh_agent_cad tests ===")
    mesh_agent.register()
    try:
        test_mode_plumbing()
        test_validation_gating()
        test_validation_analysis()
        test_mesh_cad()
        test_overlay_worked_example()
        test_export_stl()
        test_mode_persists_through_save_load()
    finally:
        mesh_agent.unregister()

    if FAILURES:
        print("\n{:d} FAILURE(S):".format(len(FAILURES)))
        for label in FAILURES:
            print("  - " + label)
        sys.exit(1)
    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
