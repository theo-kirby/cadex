# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Headless integration for the cadex backend (cadex Phase 6) — and the
measured evidence for the cadex decision gate's two shell-side criteria
(cadex docs/INTEGRATION.md):

1. Tessellation & picking fidelity: ID maps survive into Blender face
   attributes; a viewport pick (ray-cast → polygon → ``cadex_face`` →
   ``resolve_pin``) resolves to the geometrically correct BREP face
   >= 99% of the time on the test-part corpus.
2. Slider-drag latency: param change → updated tessellation in the scene,
   through the full Blender → cadexd → worker → hydrate path, on the
   24-hole/fillet/mesh-skin baseline part (Qt parity bar: median <= 0.65 s).

Run:
    blender --background --factory-startup \
        --python tests/python/bl_mesh_agent_cadex.py

Requires the cadex engine: FreeCADCmd from a cadex build, found via the
MESH_FREECADCMD environment variable or PATH. Prints one JSON gate report
line ("CADEX-BLENDER-GATE {...}") and exits non-zero on any failure.
"""

import json
import os
import random
import statistics
import sys
import tempfile
import time

import bpy
from mathutils import Vector

_REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "..", ".."))
sys.path.insert(0, os.path.join(_REPO, "scripts", "addons_core"))

import mesh_agent  # noqa: E402
from mesh_agent import cadex_backend  # noqa: E402
from mesh_agent import cadex_hydrate  # noqa: E402
from mesh_agent import cadex_pick  # noqa: E402
from mesh_agent import cadexd_client  # noqa: E402
from mesh_agent import model as model_module  # noqa: E402
from mesh_agent import tools  # noqa: E402
from mesh_agent.mock_backend import MockBackend  # noqa: E402

FAILURES = []
GATE = {}

#: Picking corpus (parts spatially separated so rays are unambiguous):
#: box, cone, torus, drilled+filleted plate — the cadex tessellation
#: corpus — plus one mesh output (not pickable, must be refused).
CORPUS_SCRIPT = """
box = part.box(30, 20, 10, origin=[0, 0, 0])
cone = part.cone(8, 3, 12, origin=[80, 0, 0])
donut = part.torus(10, 3, center=[160, 0, 0])
drilled = part.cut(
    part.fillet(part.box(60, 40, 6, origin=[240, 0, 0]), 1.5),
    [
        part.cylinder(3, 12, origin=[252, 10, -3]),
        part.cylinder(3, 12, origin=[288, 10, -3]),
        part.cylinder(3, 12, origin=[252, 30, -3]),
        part.cylinder(3, 12, origin=[288, 30, -3]),
    ],
)
skin = mesh.from_shape(box)
result = {"box": box, "cone": cone, "donut": donut, "drilled": drilled,
          "skin": skin}
"""

#: Latency baseline: the same 24-hole/fillet/mesh-skin part the Qt
#: switchover integration measured (median 0.479 s, bar 0.65 s).
BASELINE_SCRIPT = """
p = params(hole=num(2.5, unit="mm", min=1.0, max=4.0, step=0.1,
                    label="Hole Diameter"))
base = part.box(120, 80, 8)
holes = [
    part.cylinder(p.hole, 16, origin=[10 + 18 * (i % 6), 12 + 18 * (i // 6), -4])
    for i in range(24)
]
plate = part.fillet(part.cut(base, holes), 1.0)
skin = mesh.from_shape(plate, linear_deflection=0.5)
result = {"plate": plate, "skin": skin}
"""

REDUCED_SCRIPT = """
plate = part.box(60, 40, 8)
result = {"plate": plate}
"""


def check(condition, label):
    status = "ok" if condition else "FAIL"
    print("  {:s}: {:s}".format(status, label))
    if not condition:
        FAILURES.append(label)


def reset_scene(root):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene[cadex_backend.ROOT_PROP] = root


def run_tool(name, tool_input):
    # The cadex modeling tools are deferred (they run off the main thread);
    # execute_blocking resolves the Pending through the same code path the
    # agent's drain loop uses.
    content, is_error = tools.execute_blocking(name, tool_input)
    text = "\n".join(block.get("text", "") for block in content
                     if block.get("type") == "text")
    return not is_error, text


def brep_objects():
    return sorted(
        (obj for obj in bpy.data.objects
         if str(obj.get(cadex_hydrate.KIND_PROP, "")) == "brep"),
        key=lambda obj: obj.name)


# -- write_script + ID-map transport ----------------------------------------

def test_startup_layout_is_the_shipped_file():
    """The Mesh template's layout is a saved screen, not a timer.

    This is the only thing that catches `Mesh/startup.blend` silently failing
    to load: the app-template stub no longer rebuilds the layout, so a broken
    or missing startup file degrades to Blender's factory screen rather than
    raising. See ADR-037.
    """
    print("test_startup_layout_is_the_shipped_file")
    bpy.ops.wm.read_homefile(app_template="Mesh", use_factory_startup=True)

    areas = sorted(area.type for screen in bpy.data.screens
                   for area in screen.areas)
    check(areas == ['CADEX_CHAT', 'CADEX_PARAMS', 'VIEW_3D'],
          "the startup layout is the three Cadex areas: {!r}".format(areas))
    workspaces = [workspace.name for workspace in bpy.data.workspaces]
    check(workspaces == ["Simple"],
          "one workspace, named Simple: {!r}".format(workspaces))
    check(not bpy.data.objects, "the startup scene is empty")

    viewport = next((area.spaces.active for screen in bpy.data.screens
                     for area in screen.areas if area.type == 'VIEW_3D'), None)
    check(viewport is not None and viewport.shading.type == 'SOLID'
          and viewport.shading.light == 'MATCAP',
          "the viewport keeps its solid/matcap styling")
    check(viewport is not None and not viewport.overlay.show_overlays
          and not viewport.show_region_ui and not viewport.show_region_header,
          "the viewport keeps its chrome off")

    GATE["startup_areas"] = areas

    # Leave the factory startup loaded: everything after this builds its own
    # scene from it.
    bpy.ops.wm.read_factory_settings(use_empty=True)


def test_write_script_hydrates(root):
    print("test_write_script_hydrates")
    reset_scene(root)
    ok, report = run_tool("write_script", {"content": CORPUS_SCRIPT})
    check(ok, "corpus write_script accepted ({:s})".format(
        report.splitlines()[0] if report else ""))

    names = {obj.name for obj in bpy.data.objects}
    for expected in ("box", "cone", "donut", "drilled", "skin"):
        check(expected in names, "output {:s} hydrated".format(expected))
    for obj in brep_objects():
        check(obj.data.attributes.get(cadex_hydrate.FACE_ATTRIBUTE) is not None,
              "{:s} carries the {:s} attribute".format(
                  obj.name, cadex_hydrate.FACE_ATTRIBUTE))
        collection_names = {c.name for c in obj.users_collection}
        check(model_module.COLLECTION_NAME in collection_names,
              "{:s} lives in the Model collection".format(obj.name))

    skin = bpy.data.objects.get("skin")
    check(skin is not None
          and str(skin.get(cadex_hydrate.KIND_PROP, "")) == "mesh",
          "mesh output tagged as kind=mesh")

    # ID-map transport integrity: the face attribute must equal the sidecar
    # face_ranges exactly, and every BREP face must own >= 1 triangle.
    transported = 0
    for obj in brep_objects():
        sidecar = str(obj.get(cadex_hydrate.SIDECAR_PROP, ""))
        tess = cadex_hydrate.read_tessellation(sidecar)
        expected = cadex_hydrate.face_ids_per_triangle(
            tess["face_ranges"], len(tess["triangles"]))
        attribute = obj.data.attributes[cadex_hydrate.FACE_ATTRIBUTE]
        actual = [0] * len(attribute.data)
        attribute.data.foreach_get("value", actual)
        check(list(expected) == actual,
              "{:s}: attribute equals sidecar ranges".format(obj.name))
        face_count = len(tess["face_ranges"])
        covered = len(set(actual))
        check(covered == face_count,
              "{:s}: 100% face coverage ({:d}/{:d})".format(
                  obj.name, covered, face_count))
        transported += face_count
    GATE["corpus_faces"] = transported


# -- picking fidelity --------------------------------------------------------

def _face_truth(obj, scene):
    """Engine-side truth per BREP face: resolve_pin detail for every index,
    verified against the tessellation aggregate (area + centroid + normal).

    Returns (details, agreement) where agreement[face_index] is True when
    the tessellated triangles claimed by the ID map geometrically match the
    engine's description of that face."""
    output = str(obj.get(cadex_hydrate.OUTPUT_PROP, ""))
    sidecar = str(obj.get(cadex_hydrate.SIDECAR_PROP, ""))
    tess = cadex_hydrate.read_tessellation(sidecar)
    deflection = max(tess["deflection"], 0.05)
    vertices = tess["vertices"]
    triangles = tess["triangles"]
    details = {}
    agreement = {}
    for index, (start, count) in enumerate(tess["face_ranges"], start=1):
        payload = cadex_backend.resolve_pin(
            scene, output, {"element_type": "face", "index": index})
        if payload.get("ok") is not True:
            agreement[index] = False
            continue
        detail = (payload.get("details") or [{}])[0]
        details[index] = detail
        # Aggregate the face's triangles.
        area = 0.0
        centroid = Vector((0.0, 0.0, 0.0))
        for tri in triangles[start:start + count]:
            a = Vector(vertices[tri[0]])
            b = Vector(vertices[tri[1]])
            c = Vector(vertices[tri[2]])
            tri_area = ((b - a).cross(c - a)).length * 0.5
            area += tri_area
            centroid += (a + b + c) / 3.0 * tri_area
        if area <= 0.0:
            agreement[index] = False
            continue
        centroid /= area
        engine_area = float(detail.get("area_mm2") or 0.0)
        engine_center = detail.get("center_mm")
        area_ok = (abs(area - engine_area)
                   <= max(0.08 * engine_area, deflection ** 2 * 10.0))
        center_ok = True
        if isinstance(engine_center, (list, tuple)) and len(engine_center) == 3:
            center_ok = ((centroid - Vector(engine_center)).length
                         <= max(6.0 * deflection, 0.5))
        agreement[index] = bool(area_ok and center_ok)
    return details, agreement


def test_picking_fidelity(scene):
    print("test_picking_fidelity")
    rng = random.Random(20260725)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    picks = 0
    correct = 0
    per_object = {}
    for obj in brep_objects():
        details, agreement = _face_truth(obj, scene)
        attribute = obj.data.attributes[cadex_hydrate.FACE_ATTRIBUTE]
        polygons = obj.data.polygons
        sample = min(len(polygons), 120)
        indices = rng.sample(range(len(polygons)), sample)
        matrix = obj.matrix_world
        object_picks = object_correct = 0
        for polygon_index in indices:
            polygon = polygons[polygon_index]
            center = matrix @ polygon.center
            normal = (matrix.to_3x3() @ polygon.normal).normalized()
            if normal.length == 0.0:
                continue
            origin = center + normal * 0.5
            hit, location, _n, hit_index, hit_obj, _m = scene.ray_cast(
                depsgraph, origin, -normal)
            if not hit or hit_obj is None:
                continue
            if str(hit_obj.get(cadex_hydrate.KIND_PROP, "")) != "brep":
                continue  # ray landed on the mesh-domain skin; not pickable
            picks += 1
            object_picks += 1
            try:
                face_index = cadex_pick.face_index_of_polygon(
                    hit_obj, hit_index)
            except ValueError:
                continue
            if hit_obj is not obj:
                # Landed on a neighbor: judge against that object's truth.
                neighbor_details, neighbor_agreement = per_object.get(
                    hit_obj.name, (None, None))
                if neighbor_details is None:
                    neighbor_details, neighbor_agreement = _face_truth(
                        hit_obj, scene)
                    per_object[hit_obj.name] = (neighbor_details,
                                                neighbor_agreement)
                face_agreement = neighbor_agreement
                face_details = neighbor_details
            else:
                face_agreement = agreement
                face_details = details
            if not face_agreement.get(face_index, False):
                continue
            detail = face_details.get(face_index) or {}
            # Planar faces additionally verify the exact pick point.
            if str(detail.get("geometry_type") or "") == "Plane":
                engine_center = detail.get("center_mm")
                engine_normal = detail.get("normal")
                if engine_center and engine_normal:
                    residual = abs((Vector(location) - Vector(engine_center))
                                   .dot(Vector(engine_normal).normalized()))
                    if residual > 0.25:
                        continue
            correct += 1
            object_correct += 1
        per_object[obj.name] = (details, agreement)
        print("  {:s}: {:d}/{:d} picks correct".format(
            obj.name, object_correct, object_picks))
        # Every face of every corpus part must match engine truth.
        mismatched = [i for i, good in agreement.items() if not good]
        check(not mismatched,
              "{:s}: all {:d} faces match engine truth (mismatched: {!s})"
              .format(obj.name, len(agreement), mismatched[:8]))
    fidelity = (correct / picks) if picks else 0.0
    GATE["picking"] = {
        "picks": picks,
        "correct": correct,
        "fidelity": round(fidelity, 4),
        "bar": 0.99,
    }
    check(picks >= 300, "enough ray-cast picks sampled ({:d})".format(picks))
    check(fidelity >= 0.99,
          "picking fidelity {:.4f} >= 0.99".format(fidelity))

    # A pick on the mesh-domain output must be refused, not misresolved.
    skin = bpy.data.objects.get("skin")
    pin, report = cadex_pick.resolve_polygon(scene, skin, 0)
    check(pin is None and "BREP" in report,
          "mesh-domain output pick refused ({:s})".format(report))


def test_pin_flow(scene):
    print("test_pin_flow")
    box = bpy.data.objects.get("box")
    pin, report = cadex_pick.resolve_polygon(scene, box, 0)
    check(pin is not None, "pin resolved ({:s})".format(report))
    check(pin is not None and pin["output"] == "box"
          and pin["subelement"].startswith("Face"),
          "pin names a BREP face of the box")
    cadex_pick.queue_pin(pin)
    note = cadex_pick.consume_pin_notes()
    check("@face-" in note and "box" in note, "pin note formatted")
    check(cadex_pick.consume_pin_notes() == "", "pin notes drain")


# -- params bridge + slider latency ------------------------------------------

def test_params_and_latency(root):
    print("test_params_and_latency")
    reset_scene(root)
    scene = bpy.context.scene
    ok, report = run_tool("write_script", {"content": BASELINE_SCRIPT})
    check(ok, "baseline write_script accepted")

    specs = model_module.load_specs(scene)
    check(len(specs) == 1 and specs[0]["id"] == "hole"
          and specs[0]["type"] == 'FLOAT'
          and abs(specs[0]["min"] - 1.0) < 1e-9
          and abs(specs[0]["max"] - 4.0) < 1e-9,
          "engine param bridged into a scene spec")
    check(specs and "mm" in specs[0]["name"],
          "bridged spec label carries the unit")
    group = getattr(scene, "mesh_params", None)
    check(group is not None and hasattr(group, "hole"),
          "slider property group registered")

    plate = bpy.data.objects.get("plate")
    check(plate is not None, "plate hydrated")
    check(bpy.data.objects.get("plate" + cadex_hydrate.EDGE_SUFFIX) is not None,
          "standard display carries the edge wire object")
    revision_before = str(plate.get(cadex_hydrate.REVISION_PROP, ""))

    durations = []
    for index in range(10):
        value = 1.5 + 0.2 * index
        started = time.perf_counter()
        ok, drag_report = model_module.set_values({"hole": value})
        durations.append(time.perf_counter() - started)
        check(ok, "drag {:d} accepted".format(index))
    median = statistics.median(durations)
    plate = bpy.data.objects.get("plate")
    check(plate is not None
          and str(plate.get(cadex_hydrate.REVISION_PROP, "")) != revision_before,
          "drags advanced the hydrated revision")
    GATE["slider_latency"] = {
        "seconds": [round(value, 3) for value in durations],
        "median_seconds": round(median, 3),
        "parity_bar_seconds": 0.65,
        "median_within_bar": median <= 0.65,
    }
    check(median <= 0.65,
          "slider-drag median {:.3f} s within the 0.65 s parity bar".format(
              median))
    check(bpy.data.objects.get("plate" + cadex_hydrate.EDGE_SUFFIX) is None,
          "coarse drag display drops the edge wire object")

    # Post-drag refinement: the settled rebuild restores the standard
    # tessellation with edges (progressive display).
    refine_revision = str(plate.get(cadex_hydrate.REVISION_PROP, ""))
    started = time.perf_counter()
    ok, refine_report = cadex_backend.refine_now(scene)
    refine_seconds = time.perf_counter() - started
    check(ok, "refine accepted ({:s})".format(
        refine_report.splitlines()[0] if refine_report else ""))
    plate = bpy.data.objects.get("plate")
    check(bpy.data.objects.get("plate" + cadex_hydrate.EDGE_SUFFIX) is not None,
          "refine restored the edge wire object")
    # Revisions are content-derived; a display-only refine of the same
    # source and values must keep the accepted revision.
    check(plate is not None
          and str(plate.get(cadex_hydrate.REVISION_PROP, "")) == refine_revision,
          "refine kept the content-identical revision")
    GATE["refine_seconds"] = round(refine_seconds, 3)

    # Out-of-range values clamp to the bridged range before the engine runs.
    ok, _report = model_module.set_values({"hole": 99.0})
    check(ok, "clamped value accepted")

    # Contract-driven GC through the shell: dropping outputs removes them.
    ok, _report = run_tool("write_script", {"content": REDUCED_SCRIPT})
    check(ok, "reduced write_script accepted")
    check(bpy.data.objects.get("skin") is None, "dropped output GCed")
    check(bpy.data.objects.get("plate") is not None, "kept output survives")
    check(not model_module.load_specs(scene),
          "param specs empty after params left the script")


# -- agent turn: one undo per turn through the real bridge -------------------

def test_cadex_turn_single_undo(root):
    print("test_cadex_turn_single_undo")
    reset_scene(root)
    from mesh_agent import agent as agent_module
    agent = agent_module.Agent()
    agent.tool_cap_override = 10
    script = [[
        ("text", "Building the corpus.\n"),
        ("tool", "write_script", {"content": REDUCED_SCRIPT}),
        ("text", "Done."),
        ("result", False, "Done."),
    ]]

    def factory(bridge):
        return MockBackend(script=script, bridge_port=bridge.port,
                           bridge_token=bridge.token)

    agent.backend_factory = factory
    undo_pushes = []
    agent._undo_push = undo_pushes.append
    try:
        started = agent.start_turn("build a plate")
        deadline = time.monotonic() + 120.0
        while agent.busy and time.monotonic() < deadline:
            agent.drain()
            time.sleep(0.01)
        check(started and not agent.busy, "cadex turn completes")
        check(bpy.data.objects.get("plate") is not None,
              "turn hydrated the plate")
        check(len(undo_pushes) == 1,
              "exactly one undo push per turn (got {:d})".format(
                  len(undo_pushes)))
    finally:
        agent.shutdown()


# -- restart: reattach to the engine store ----------------------------------

def test_reopen_restores(root):
    print("test_reopen_restores")
    reset_scene(root)
    ok, _report = run_tool("write_script", {"content": BASELINE_SCRIPT})
    check(ok, "baseline accepted before restart")
    cadex_backend.close_all()
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    ok, report = cadex_backend.ensure_open(bpy.context.scene)
    check(ok, "reopen succeeds ({:s})".format(report or "clean"))
    check(bpy.data.objects.get("plate") is not None,
          "geometry rehydrated after engine restart")
    specs = model_module.load_specs(bpy.context.scene)
    check(any(spec["id"] == "hole" for spec in specs),
          "params restored after engine restart")
    check(model_module.get_script().strip() != "",
          "script text mirrored after engine restart")



# -- M2: the main thread stays live, and cancel reaches the engine ----------

SLOW_SCRIPT = """
blobs = [part.sphere(5.0, center=[i * 3.0, 0.0, 0.0]) for i in range(60)]
result = {"blob": part.fuse(blobs)}
"""


def test_main_thread_free_during_rebuild(root):
    """A modeling request must not block Blender's main thread.

    Proof by timestamps: while the engine runs the script, this loop is the
    main thread, and it ticks. Before M2 the request ran *on* this thread,
    so there would be exactly one tick.
    """
    print("test_main_thread_free_during_rebuild")
    reset_scene(root)
    scene = bpy.context.scene

    started = cadex_backend.begin_write_script(scene, BASELINE_SCRIPT)
    check(isinstance(started, cadex_backend.Lifecycle),
          "write_script begins off-thread")
    if not isinstance(started, cadex_backend.Lifecycle):
        return

    ticks = []
    began = time.monotonic()
    outcome = None
    while outcome is None and time.monotonic() - began < 300.0:
        ticks.append(time.monotonic())
        outcome = started.poll()
        time.sleep(0.01)
    elapsed = time.monotonic() - began

    check(outcome is not None and outcome[0],
          "deferred write_script accepted ({:s})".format(
              "ok" if outcome else "timeout"))
    check(len(ticks) > 10,
          "main thread ticked {:d} times during a {:.2f} s rebuild".format(
              len(ticks), elapsed))
    # The ticks must span the rebuild, not bunch up at one end.
    spread = ticks[-1] - ticks[0]
    check(spread > 0.5 * elapsed,
          "ticks span the rebuild ({:.2f} s of {:.2f} s)".format(
              spread, elapsed))
    check(bpy.data.objects.get("plate") is not None,
          "deferred write_script hydrated")
    GATE["main_thread_ticks"] = len(ticks)
    GATE["main_thread_rebuild_seconds"] = round(elapsed, 3)


def test_cancel_reaches_the_engine(root):
    """Escape during a long rebuild must cancel it, not orphan it."""
    print("test_cancel_reaches_the_engine")
    reset_scene(root)
    scene = bpy.context.scene

    ok, _report = run_tool("write_script", {"content": BASELINE_SCRIPT})
    check(ok, "baseline accepted before the cancel attempt")
    before = brep_objects()

    # Cancel once the engine's worker is demonstrably running.
    began = time.monotonic()
    started = cadex_backend.begin_write_script(
        scene, SLOW_SCRIPT, cancelled=lambda: time.monotonic() - began > 1.5)
    check(isinstance(started, cadex_backend.Lifecycle),
          "slow write_script begins off-thread")
    if not isinstance(started, cadex_backend.Lifecycle):
        return
    outcome = None
    while outcome is None and time.monotonic() - began < 300.0:
        outcome = started.poll()
        time.sleep(0.01)

    check(outcome is not None and not outcome[0],
          "cancelled write_script is refused")
    report = outcome[1] if outcome else ""
    check("RUN_CANCELLED" in report,
          "engine reports RUN_CANCELLED (got: {:s})".format(report[:120]))
    check(bpy.data.objects.get("blob") is None,
          "cancelled run hydrated nothing")
    check(brep_objects() == before,
          "cancelled run left the accepted geometry alone")

    # The engine stays serviceable after a cancel.
    ok, report = run_tool("write_script", {"content": REDUCED_SCRIPT})
    check(ok, "engine still serviceable after cancel ({:s})".format(
        report[:120]))
    GATE["cancel_seconds"] = round(time.monotonic() - began, 3)



# -- M4: Save-As and the second .blend --------------------------------------

def test_save_as_and_multi_file_lifecycle(workdir):
    """Save-As must repoint the engine project; a second file must not leak.

    Phase 6 cached the derived root in scene["mesh_cadex_root"], which made
    it indistinguishable from a user override — so after Save-As the new
    file kept driving the old file's engine project.
    """
    print("test_save_as_and_multi_file_lifecycle")
    from mesh_agent import cadexd_client

    first = os.path.join(workdir, "a.blend")
    second = os.path.join(workdir, "b.blend")

    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.wm.save_as_mainfile(filepath=first)
    scene = bpy.context.scene

    root_a = cadex_backend.project_root(scene)
    check(root_a == os.path.join(workdir, "a.cadex"),
          "root derived from the file name: {:s}".format(root_a))
    check(scene.get(cadex_backend.ROOT_PROP) is None,
          "the derived root is NOT cached as a user override")

    ok, report = run_tool("write_script", {"content": REDUCED_SCRIPT})
    check(ok, "model accepted in a.blend ({:s})".format(report[:80]))
    check(os.path.isdir(root_a), "a.cadex created on disk")
    check(cadex_backend.open_roots() == [root_a],
          "exactly one engine session open")

    # Save-As: the handler fires for real.
    bpy.ops.wm.save_as_mainfile(filepath=second)
    scene = bpy.context.scene
    root_b = cadex_backend.project_root(scene)
    check(root_b == os.path.join(workdir, "b.cadex"),
          "Save-As repoints the root: {:s}".format(root_b))
    check(cadex_backend.open_roots() == [],
          "Save-As dropped the old engine session")
    check(not cadexd_client._clients, "no cadexd child left for the old root")

    # The new file starts a fresh project with a fresh child.
    ok, report = run_tool("write_script", {"content": BASELINE_SCRIPT})
    check(ok, "model accepted in b.blend ({:s})".format(report[:80]))
    check(cadex_backend.open_roots() == [root_b],
          "the new file opened its own project")
    check(os.path.isdir(root_b), "b.cadex created on disk")
    check(os.path.isdir(root_a), "a.cadex left intact, not moved or copied")

    # Opening the first file again must not leak the second file's child.
    bpy.ops.wm.open_mainfile(filepath=first)
    check(cadex_backend.open_roots() == [],
          "opening another .blend dropped the previous session")
    check(not cadexd_client._clients, "no leaked cadexd child after load")
    scene = bpy.context.scene
    check(cadex_backend.project_root(scene) == root_a,
          "reopened file resolves back to its own project")
    ok, report = cadex_backend.ensure_open(scene)
    check(ok, "reopened file's project opens ({:s})".format(report or "clean"))
    check(bpy.data.objects.get("plate") is not None,
          "reopened file rehydrates its own geometry")


def test_duplicated_file_keeps_its_parameters(workdir):
    """A copy names an empty project; that must not erase what the file holds.

    ``open_project`` mkdirs the root it is handed, so a duplicated or
    Save-As'd .blend opens a project with no script in it. Adopting that
    emptiness used to overwrite scene["mesh_model_specs"] with "[]" and
    unregister the slider group -- destroying the only surviving copy of the
    parameter declarations, while the baked mesh stayed in the viewport and
    made the file look fine.
    """
    print("test_duplicated_file_keeps_its_parameters")

    first = os.path.join(workdir, "orig.blend")
    copy = os.path.join(workdir, "orig-copy.blend")

    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.wm.save_as_mainfile(filepath=first)
    scene = bpy.context.scene
    ok, report = run_tool("write_script", {"content": BASELINE_SCRIPT})
    check(ok, "parametric model accepted in orig.blend ({:s})".format(
        report[:60]))
    specs_before = model_module.load_specs(scene)
    check(len(specs_before) == 1 and specs_before[0]["id"] == "hole",
          "the original file has its spec")

    bpy.ops.wm.save_as_mainfile(filepath=copy)
    scene = bpy.context.scene
    root_copy = cadex_backend.project_root(scene)
    check(not os.path.isdir(root_copy),
          "the copy names a project that does not exist yet")
    check(cadex_backend.scene_remembers_a_model(scene),
          "the .blend still carries the model (specs and script mirror)")

    # The open that used to do the damage.
    ok, report = cadex_backend.ensure_open(scene)
    check(ok, "the empty project opens ({:s})".format(report or "clean"))
    specs_after = model_module.load_specs(scene)
    check(len(specs_after) == 1 and specs_after[0]["id"] == "hole",
          "opening an empty project did NOT wipe the saved specs")
    check(getattr(scene, "mesh_params", None) is not None,
          "the slider group survived the open")
    check(cadex_backend.orphaned_project(scene),
          "the empty project is reported as orphaned")

    # Recovery: re-run the script the .blend carries.
    ok, report = cadex_backend.adopt_saved_script(scene)
    check(ok, "the saved script rebuilds the project ({:s})".format(
        report[:60] if report else "clean"))
    check(not cadex_backend.orphaned_project(scene),
          "the project is no longer orphaned once adopted")
    check(bpy.data.objects.get("plate") is not None,
          "adopting the saved script hydrated the geometry")
    specs_final = model_module.load_specs(scene)
    check(len(specs_final) == 1 and specs_final[0]["id"] == "hole",
          "the adopted project declares the same parameter")
    check(os.path.isdir(os.path.join(workdir, "orig.cadex")),
          "the original project is left intact, not moved or copied")


# -- M5: the restore pass runs on every open --------------------------------

def test_open_runs_the_restore_pass(root):
    """Every open re-proves that the script still reproduces the model.

    cadex docs/ARCHITECTURE.md promises this for every open; Phase 6 was
    passing restore: False to save a script run, so the promise was not
    being kept in the Blender shell.
    """
    print("test_open_runs_the_restore_pass")
    reset_scene(root)
    scene = bpy.context.scene
    ok, _report = run_tool("write_script", {"content": BASELINE_SCRIPT})
    check(ok, "baseline accepted before the restore check")

    cadex_backend.close_all()
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)

    began = time.monotonic()
    ok, report = cadex_backend.ensure_open(scene)
    open_seconds = time.monotonic() - began
    check(ok, "reopen with restore succeeds ({:s})".format(report or "clean"))

    restore = cadex_backend._state_for(
        cadex_backend.project_root(scene)).restore
    check(restore.get("performed") is True,
          "the engine ran a restore pass: {!r}".format(restore))
    check(restore.get("matches_accepted") is True,
          "the restored digest matches the accepted digest")
    check(bool(restore.get("digest")), "the restore reported a digest")
    check(bpy.data.objects.get("plate") is not None,
          "the reopened project hydrated")
    GATE["open_seconds"] = round(open_seconds, 3)
    GATE["restore"] = {"performed": bool(restore.get("performed")),
                       "matches_accepted": bool(restore.get("matches_accepted"))}


def test_restore_failure_is_first_class(root):
    """A store whose script no longer reproduces its digest must say so."""
    print("test_restore_failure_is_first_class")
    reset_scene(root)
    scene = bpy.context.scene
    ok, _report = run_tool("write_script", {"content": BASELINE_SCRIPT})
    check(ok, "baseline accepted before corrupting the store")

    project = cadex_backend.project_root(scene)
    cadex_backend.close_all()

    # Edit the stored script behind the engine's back, exactly as a user
    # with a text editor would: the accepted digest no longer matches.
    script_path = os.path.join(project, "script.py")
    with open(script_path, "r", encoding="utf-8") as handle:
        source = handle.read()
    with open(script_path, "w", encoding="utf-8") as handle:
        handle.write(source.replace("part.box(120, 80, 8)",
                                    "part.box(60, 40, 8)"))

    ok, report = cadex_backend.ensure_open(scene)
    check(not ok, "an inconsistent store refuses to open")
    check("could not restore this model" in report,
          "the failure is reported as a restore failure, not a traceback")
    check("will not help" in report,
          "the report says retrying will not help")



# -- M6: the engine describes its own API -----------------------------------

def test_describe_cad_api(root):
    """The model reads the API from the engine, not from the prompt."""
    print("test_describe_cad_api")
    reset_scene(root)

    ok, text = run_tool("describe_cad_api", {})
    check(ok, "describe_cad_api overview succeeds")
    overview = json.loads(text)
    domains = overview.get("domains") or {}
    check(sorted(domains) == ["assembly", "mesh", "part", "partdesign",
                              "sketcher"],
          "overview lists the engine's real domains: {!r}".format(
              sorted(domains)))
    check("instructions" in overview and "result_contract" in overview,
          "overview carries the authoring contract")
    functions = domains.get("part", {}).get("functions") or []
    check("box" in functions and "fillet" in functions,
          "part's function names are listed ({:d} functions)".format(
              len(functions)))
    check(all(isinstance(name, str) for name in functions),
          "function lists are plain names")
    check(len(text) < 8000,
          "the overview is prompt-sized: {:d} chars".format(len(text)))

    ok, text = run_tool("describe_cad_api", {"domain": "mesh"})
    check(ok, "describe_cad_api for one domain succeeds")
    block = json.loads(text)
    exports = {item["name"]: item for item in block.get("exports") or []}
    check("from_shape" in exports, "the mesh domain's exports are served")
    check("signature" in exports.get("from_shape", {}),
          "exports carry full signatures")

    ok, text = run_tool("describe_cad_api", {"domain": "nope"})
    check(not ok, "an unknown domain is refused")
    check("part" in text and "mesh" in text,
          "the refusal names the real domains")

    GATE["describe_api"] = {
        "overview_chars": len(json.dumps(overview)),
        "domains": sorted(domains),
    }



# -- M7: edit_script, inspect_model, and scene_summary telling the truth ----

def test_edit_script_and_inspection(root):
    print("test_edit_script_and_inspection")
    reset_scene(root)
    scene = bpy.context.scene

    ok, _report = run_tool("write_script", {"content": BASELINE_SCRIPT})
    check(ok, "baseline accepted before editing")
    before = model_module.get_script()
    check("part.box(120, 80, 8)" in before, "the literal to edit is present")

    # One literal changes; the rest of the script must survive untouched.
    ok, report = run_tool("edit_script", {"replacements": [
        {"old": "part.box(120, 80, 8)", "new": "part.box(140, 80, 8)"}]})
    check(ok, "edit_script accepted ({:s})".format(report[:100]))
    after = model_module.get_script()
    check("part.box(140, 80, 8)" in after, "the edit landed")
    check("mesh.from_shape" in after and "part.fillet" in after,
          "the rest of the script survived")
    check(len(after.splitlines()) == len(before.splitlines()),
          "no lines gained or lost")

    # An ambiguous `old` is refused whole, not applied partially.
    ok, report = run_tool("edit_script", {"replacements": [
        {"old": "part.", "new": "PART."}]})
    check(not ok, "an ambiguous replacement is refused")
    check(model_module.get_script() == after,
          "the refused edit changed nothing")

    # The revision guard still holds after an edit.
    ok, report = run_tool("set_params", {"params": {"hole": 3.0}})
    check(ok, "set_params still works after an edit ({:s})".format(
        report[:80]))

    # inspect_model reads engine truth.
    ok, text = run_tool("inspect_model", {"scope": "script",
                                          "path": "/revisions"})
    check(ok, "inspect_model script scope succeeds")
    revisions = json.loads(text)
    check(bool(revisions.get("accepted_revision")),
          "the engine reports an accepted revision")

    ok, text = run_tool("inspect_model", {"scope": "document"})
    check(ok, "inspect_model document scope succeeds")
    check(json.loads(text).get("object_count", 0) > 0,
          "the engine's document holds objects")

    ok, _text = run_tool("inspect_model", {"scope": "selection"})
    check(not ok, "shell-only scopes are refused")

    # scene_summary reports the engine, and labels the mirror as a mirror.
    ok, text = run_tool("scene_summary", {})
    check(ok, "scene_summary succeeds in cadex mode")
    summary = json.loads(text)
    check("cadex engine" in str(summary.get("source", "")),
          "scene_summary says it is reporting the engine")
    check("document" in summary and "revision" in summary,
          "scene_summary carries engine state")
    mirror = summary.get("viewport_mirror") or {}
    check("plate" in (mirror.get("objects") or []),
          "the Blender objects are reported as the mirror they are")
    check("approximation" in mirror.get("note", ""),
          "the mirror is labelled as approximate")


def main():
    registered = False
    # Resolve the engine exactly as the add-on does -- explicit preference,
    # MESH_FREECADCMD, the bundled payload's manifest, then PATH. With the
    # engine bundled inside the application (cadex ADR-023) this succeeds
    # with no environment set at all, which is the Phase 7 exit criterion.
    mesh_agent.register()
    registered = True
    ok, reason, remedy = cadex_backend.preflight()
    if not ok:
        print("FAIL:", reason, remedy)
        return 1
    freecadcmd, module_dir = cadex_backend.resolved_engine()
    print("engine:", freecadcmd)
    print("engine module dir:", module_dir)
    GATE["engine_from_bundle"] = bool(
        cadexd_client.find_bundled_engine(cadex_backend.bundle_roots()))

    corpus_root = tempfile.mkdtemp(prefix="mesh-cadex-corpus-")
    baseline_root = tempfile.mkdtemp(prefix="mesh-cadex-baseline-")
    turn_root = tempfile.mkdtemp(prefix="mesh-cadex-turn-")
    reopen_root = tempfile.mkdtemp(prefix="mesh-cadex-reopen-")
    threading_root = tempfile.mkdtemp(prefix="mesh-cadex-thread-")
    cancel_root = tempfile.mkdtemp(prefix="mesh-cadex-cancel-")
    saveas_root = tempfile.mkdtemp(prefix="mesh-cadex-saveas-")
    duplicate_root = tempfile.mkdtemp(prefix="mesh-cadex-duplicate-")
    restore_root = tempfile.mkdtemp(prefix="mesh-cadex-restore-")
    corrupt_root = tempfile.mkdtemp(prefix="mesh-cadex-corrupt-")
    describe_root = tempfile.mkdtemp(prefix="mesh-cadex-describe-")
    edit_root = tempfile.mkdtemp(prefix="mesh-cadex-edit-")
    try:
        test_startup_layout_is_the_shipped_file()
        test_write_script_hydrates(corpus_root)
        scene = bpy.context.scene
        test_picking_fidelity(scene)
        test_pin_flow(scene)
        test_describe_cad_api(describe_root)
        test_edit_script_and_inspection(edit_root)
        test_params_and_latency(baseline_root)
        test_main_thread_free_during_rebuild(threading_root)
        test_cancel_reaches_the_engine(cancel_root)
        test_cadex_turn_single_undo(turn_root)
        test_save_as_and_multi_file_lifecycle(saveas_root)
        test_duplicated_file_keeps_its_parameters(duplicate_root)
        test_reopen_restores(reopen_root)
        test_open_runs_the_restore_pass(restore_root)
        test_restore_failure_is_first_class(corrupt_root)
    finally:
        try:
            cadex_backend.close_all()
        except Exception:
            pass
        try:
            if registered:
                mesh_agent.unregister()
        except Exception:
            pass
        import shutil
        for root in (corpus_root, baseline_root, turn_root, reopen_root,
                     threading_root, cancel_root, saveas_root,
                     duplicate_root,
                     restore_root, corrupt_root, describe_root, edit_root):
            shutil.rmtree(root, ignore_errors=True)

    GATE["ok"] = not FAILURES
    print("CADEX-BLENDER-GATE " + json.dumps(GATE, sort_keys=True))
    if FAILURES:
        print("FAILED ({:d}):".format(len(FAILURES)))
        for failure in FAILURES:
            print("  -", failure)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
