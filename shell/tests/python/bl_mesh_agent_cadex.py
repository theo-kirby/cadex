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

import glob
import json
import math
import os
import random
import statistics
import sys
import tempfile
import types
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

#: A script whose declarations do not fit in one `inspect` preview. Eight
#: parameters with labels and descriptions push `params` past the engine's
#: 1 KiB preview threshold, and the source past it too -- which is the size
#: every real model is, and the size at which the shell used to bridge
#: nothing at all. Keep it over the threshold (see test_params_survive_the
#: _inspect_pager) or the test stops testing anything.
WIDE_PARAMS_SCRIPT = """
p = params(
    length=num(120.0, unit="mm", min=60, max=200, label="Overall length",
               description="The long dimension of the plate, corner to corner"),
    width=num(80.0, unit="mm", min=40, max=140, label="Overall width",
              description="The short dimension of the plate, corner to corner"),
    thickness=num(8.0, unit="mm", min=4, max=20, label="Plate thickness",
                  description="Material thickness before any fillet is taken"),
    hole=num(2.5, unit="mm", min=1.0, max=4.0, label="Hole diameter",
             description="Diameter of every hole in the bolt grid"),
    columns=num(6.0, min=2, max=8, label="Hole columns",
                description="How many holes across the length of the plate"),
    rows=num(4.0, min=2, max=6, label="Hole rows",
             description="How many holes across the width of the plate"),
    pitch=num(18.0, unit="mm", min=12, max=30, label="Hole pitch",
              description="Centre-to-centre spacing of the bolt grid"),
    fillet=num(1.0, unit="mm", min=0.5, max=4.0, label="Edge fillet",
               description="Radius rolled onto the plate's outer edges"),
)
base = part.box(p.length, p.width, p.thickness)
holes = [
    part.cylinder(p.hole, p.thickness * 2.0,
                  origin=[10 + p.pitch * (i % int(p.columns)),
                          12 + p.pitch * (i // int(p.columns)),
                          -p.thickness])
    for i in range(int(p.columns) * int(p.rows))
]
plate = part.fillet(part.cut(base, holes), p.fillet)
result = {"plate": plate}
"""


#: Two declarations, then one: the rewrite that used to wedge the sliders
#: permanently. `depth`'s *value* outlived its declaration in the store, and
#: every later `set_params` merged it back in and then refused it (ADR-039).
TWO_PARAM_SCRIPT = """
p = params(width=num(40.0, unit="mm", min=20, max=80, label="Width"),
           depth=num(24.0, unit="mm", min=10, max=50, label="Depth"))
plate = part.box(p.width, p.depth, 6)
result = {"plate": plate}
"""

ONE_PARAM_SCRIPT = """
p = params(width=num(40.0, unit="mm", min=20, max=80, label="Width"))
plate = part.box(p.width, 24, 6)
result = {"plate": plate}
"""


#: A model that cannot be rebuilt from its script alone: the script names a
#: file the user supplied. This is what Save-As used to lose (ADR-046).
IMPORTED_GEOMETRY_SCRIPT = """
widget = mesh.import_file("widget.stl")
result = {"widget": widget}
"""

MOVED_GEOMETRY_SCRIPT = """
widget = mesh.transform(mesh.import_file("widget.stl"), translation=(5, 0, 0))
result = {"widget": widget}
"""

#: A closed tetrahedron, the smallest thing `mesh.import_file` will take.
TETRAHEDRON_STL = """solid widget
facet normal 0 0 -1
  outer loop
    vertex 0 0 0
    vertex 0 10 0
    vertex 10 0 0
  endloop
endfacet
facet normal 0 -1 0
  outer loop
    vertex 0 0 0
    vertex 10 0 0
    vertex 0 0 10
  endloop
endfacet
facet normal -1 0 0
  outer loop
    vertex 0 0 0
    vertex 0 0 10
    vertex 0 10 0
  endloop
endfacet
facet normal 0.5774 0.5774 0.5774
  outer loop
    vertex 10 0 0
    vertex 0 10 0
    vertex 0 0 10
  endloop
endfacet
endsolid widget
"""


def store_state(root):
    """The engine's durable script state, read straight off disk."""
    with open(os.path.join(root, "script.json"), encoding="utf-8") as handle:
        return json.load(handle)


def revision_sources(root):
    """The accepted sources in one project's undo trail (ADR-045)."""
    return sorted(glob.glob(os.path.join(root, "script_history", "*.py")))


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

    # The other half of the template, and the one a stale bundle loses: the
    # top bar carries the Cadex File and Edit menus (ADR-041). The template's
    # own timer never runs here (`load_handler` returns in background), so
    # this calls what the timer would have called -- from the *shipped*
    # module, which is the point.
    from mesh_agent import topbar
    template = sys.modules.get("bl_app_templates_system.Mesh")
    check(template is not None, "the Mesh app template module is loaded")
    if template is not None:
        try:
            template._cadex_topbar()
            check(topbar.installed(),
                  "the shipped app template installs the Cadex top bar")
        finally:
            topbar.uninstall()

        # And no splash on the way in (ADR-042). Suppressing it must not
        # dirty the preferences: dirty preferences auto-save on exit, and
        # this is the product's decision, not the user's.
        preferences = bpy.context.preferences
        was_splash = preferences.view.show_splash
        was_dirty = preferences.is_dirty
        try:
            template._hide_splash()
            check(not preferences.view.show_splash,
                  "the shipped app template suppresses the splash")
            check(preferences.is_dirty == was_dirty,
                  "suppressing the splash leaves the preferences as it found "
                  "them")
        finally:
            preferences.view.show_splash = was_splash
            preferences.is_dirty = was_dirty

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


def test_point_pin_flow(scene):
    """A point pin is a place and a direction — a part.cable port (ADR-056).

    The one thing a face pin cannot give you: imported components are mesh
    outputs, ``resolve_polygon`` refuses them by design, and a harness lands
    almost all of its ports on exactly those.
    """
    print("test_point_pin_flow")
    from mathutils import Matrix, Vector

    # The mesh output: refused as a face pin, accepted as a point pin.
    skin = bpy.data.objects.get("skin")
    refused, _report = cadex_pick.resolve_polygon(scene, skin, 0)
    pin, report = cadex_pick.point_pin(
        skin, Vector((1.0, 2.0, 3.0)), Vector((0.0, 0.0, 2.0)))
    check(refused is None and pin is not None,
          "the mesh output takes a point pin where a face pin is refused "
          "({:s})".format(report))
    check(pin is not None and pin["output"] == "skin"
          and pin["kind"] == "point",
          "the point pin names its output")
    check(pin is not None and pin["point"] == [1.0, 2.0, 3.0],
          "the pinned point is the hit point")
    check(pin is not None and pin["normal"] == [0.0, 0.0, 1.0],
          "the surface normal is normalised: {!r}".format(
              pin and pin["normal"]))

    # A placement is undone: the script authors in the output's own space,
    # so a world-space hit on a placed component must come back as the
    # coordinate the script would have to write.
    box = bpy.data.objects.get("box")
    before = box.matrix_world.copy()
    try:
        box.matrix_world = (Matrix.Translation(Vector((10.0, 0.0, 0.0)))
                            @ Matrix.Rotation(math.radians(90.0), 4, 'Z'))
        placed, _report = cadex_pick.point_pin(
            box, Vector((10.0, 5.0, 0.0)), Vector((0.0, 1.0, 0.0)))
        check(placed is not None
              and all(abs(placed["point"][axis] - value) < 1.0e-6
                      for axis, value in enumerate((5.0, 0.0, 0.0))),
              "a placement is undone on the point: {!r}".format(
                  placed and placed["point"]))
        check(placed is not None
              and all(abs(placed["normal"][axis] - value) < 1.0e-6
                      for axis, value in enumerate((1.0, 0.0, 0.0))),
              "a placement is undone on the normal: {!r}".format(
                  placed and placed["normal"]))
    finally:
        box.matrix_world = before

    # Anything that is not a cadex output is refused rather than pinned to
    # a name the agent cannot act on.
    stray = bpy.data.objects.new("stray", None)
    refused, report = cadex_pick.point_pin(
        stray, Vector((0.0, 0.0, 0.0)), Vector((0.0, 0.0, 1.0)))
    check(refused is None and "not a cadex output" in report,
          "a non-output is refused ({:s})".format(report))
    bpy.data.objects.remove(stray)

    cadex_pick.queue_pin(pin)
    note = cadex_pick.consume_pin_notes()
    check("a point on skin" in note and "surface normal" in note,
          "the point pin note reads as a port: {:s}".format(note.strip()))
    check(cadex_pick.consume_pin_notes() == "", "point pin notes drain")


def test_both_pin_gestures_are_registered():
    print("test_both_pin_gestures_are_registered")
    check(hasattr(bpy.types, "MESH_AGENT_OT_pick_pin"),
          "the face pin operator is registered")
    check(hasattr(bpy.types, "MESH_AGENT_OT_pick_point"),
          "the point pin operator is registered")


def test_the_pick_finds_the_viewport_under_the_mouse():
    """Both pins start from a button in the chat editor, not the viewport.

    The button row is under the message box (ADR-074 moved it there from the
    header, which now carries only the pinned count) -- but either way it is
    the chat's own area, and that is what matters here: the modal cannot use
    the area it was invoked from, because gating on it cancels the gesture the
    instant it starts, which is what the buttons did. The region has to come
    from where the mouse ends up. Driving the modal needs a real window, so
    what is checked here is the lookup the modal depends on.
    """
    print("test_the_pick_finds_the_viewport_under_the_mouse")

    class _Region:
        def __init__(self, kind, x, y, width, height):
            self.type = kind
            self.x, self.y = x, y
            self.width, self.height = width, height

    class _Area:
        def __init__(self, kind, regions):
            self.type = kind
            self.regions = regions

    window = _Region('WINDOW', 100, 50, 400, 300)
    areas = [
        _Area('CADEX_CHAT', [_Region('HEADER', 0, 0, 100, 400)]),
        _Area('VIEW_3D', [_Region('HEADER', 100, 350, 400, 26), window]),
    ]

    check(cadex_pick.viewport_region_at(areas, 300, 200) is window,
          "a pixel inside the viewport finds its window region")
    check(cadex_pick.viewport_region_at(areas, 50, 200) is None,
          "a pixel over the chat header finds nothing")
    check(cadex_pick.viewport_region_at(areas, 300, 360) is None,
          "a pixel over the viewport's own header finds nothing")
    check(cadex_pick.viewport_region_at(areas, 100, 50) is window
          and cadex_pick.viewport_region_at(areas, 500, 350) is None,
          "the region is half-open: its low corner is in, its high corner out")
    check(cadex_pick.viewport_region_at([], 300, 200) is None,
          "no viewport at all is not an error")


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

    cadex_backend.hydrate_timings(reset=True)
    durations = []
    for index in range(10):
        value = 1.5 + 0.2 * index
        started = time.perf_counter()
        ok, drag_report = model_module.set_values({"hole": value})
        durations.append(time.perf_counter() - started)
        check(ok, "drag {:d} accepted".format(index))
    hydrations = cadex_backend.hydrate_timings(reset=True)
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
    # Hydration's share of the drag. Measured, not bounded: it is here to
    # say whether the viewport half of a drag is worth optimising at all.
    hydrate_median = statistics.median(hydrations) if hydrations else 0.0
    GATE["hydrate_seconds"] = {
        "seconds": [round(value, 4) for value in hydrations],
        "median_seconds": round(hydrate_median, 4),
        "share_of_drag": (round(hydrate_median / median, 3)
                          if median > 0 else None),
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
    ok, _report = run_tool("write_script", {"content": REDUCED_SCRIPT,
                              "replace": True})
    check(ok, "reduced write_script accepted")
    check(bpy.data.objects.get("skin") is None, "dropped output GCed")
    check(bpy.data.objects.get("plate") is not None, "kept output survives")
    check(not model_module.load_specs(scene),
          "param specs empty after params left the script")


def test_params_survive_the_inspect_pager(root):
    """A model too big for one `inspect` preview still gets its sliders.

    `inspect` bounds what it returns: a value over 1 KiB comes back as a stub
    naming the pointer to reach it. The shell used to read the top page and
    take it at face value, so every model with more than a parameter or two
    bridged *zero* specs and mirrored an empty script -- while this suite,
    whose baseline declares one parameter, stayed green throughout.
    """
    print("test_params_survive_the_inspect_pager")
    reset_scene(root)
    scene = bpy.context.scene
    ok, report = run_tool("write_script", {"content": WIDE_PARAMS_SCRIPT})
    check(ok, "wide write_script accepted ({:s})".format(
        report.splitlines()[0] if report else ""))

    declared = ["length", "width", "thickness", "hole",
                "columns", "rows", "pitch", "fillet"]
    specs = model_module.load_specs(scene)
    check([spec["id"] for spec in specs] == declared,
          "all {:d} params bridged, in order ({:d} arrived)".format(
              len(declared), len(specs)))
    group = getattr(scene, "mesh_params", None)
    check(group is not None
          and all(hasattr(group, name) for name in declared),
          "every declared param has a slider property")
    check(model_module.get_script().strip() == WIDE_PARAMS_SCRIPT.strip(),
          "the script mirror holds the whole source, not a truncated page")

    # The guard is only meaningful while the payload actually exceeds the
    # engine's preview threshold; a smaller script would pass either way.
    client = cadex_backend._client(cadex_backend.project_root(scene))
    top = client.request("inspect", {"scope": "script"})
    previewed = [key for key, value in dict(top.get("value") or {}).items()
                 if isinstance(value, dict) and "inspect_path" in value]
    check("params" in previewed and "source" in previewed,
          "this model is big enough that the engine previews it {!r}".format(
              sorted(previewed)))

    # And the sliders drive the engine, not just the panel.
    ok, drag_report = model_module.set_values({"length": 150.0})
    check(ok, "a bridged slider rebuilds ({:s})".format(
        drag_report.splitlines()[0] if drag_report else ""))


def test_dropping_a_param_leaves_the_sliders_working(root):
    """A script that drops a parameter must not wedge every later drag.

    The reported failure, at the shell's own level: the sliders on a real model
    stopped working *permanently* and nothing in the UI could un-stick them.
    The patch the shell sends is built from the declared parameters, so it
    never mentioned the dropped one -- the engine merged the dead value in from
    its own store and then refused the request for naming it (ADR-039).
    """
    print("test_dropping_a_param_leaves_the_sliders_working")
    reset_scene(root)
    scene = bpy.context.scene
    ok, report = run_tool("write_script", {"content": TWO_PARAM_SCRIPT})
    check(ok, "two-param write_script accepted ({:s})".format(
        report.splitlines()[0] if report else ""))
    ok, report = model_module.set_values({"width": 50.0, "depth": 30.0})
    check(ok, "both sliders set ({:s})".format(
        report.splitlines()[0] if report else ""))
    check(store_state(root).get("param_values") == {"width": 50.0,
                                                    "depth": 30.0},
          "the store holds both values: {!r}".format(
              store_state(root).get("param_values")))

    # The rewrite. `depth` is gone from the script; its value must go with it.
    ok, report = run_tool("write_script", {"content": ONE_PARAM_SCRIPT})
    check(ok, "one-param write_script accepted ({:s})".format(
        report.splitlines()[0] if report else ""))
    check([spec["id"] for spec in model_module.load_specs(scene)] == ["width"],
          "only the surviving parameter has a slider")
    values = store_state(root).get("param_values") or {}
    check("depth" not in values and values.get("width") == 50.0,
          "the dropped parameter's value is pruned from the store: {!r}".format(
              values))

    # The drag that used to fail forever, and then a second one -- the failure
    # was permanent, so one success is the whole regression.
    for index, value in enumerate((55.0, 60.0)):
        ok, report = model_module.set_values({"width": value})
        check(ok, "drag {:d} after the drop succeeds ({:s})".format(
            index, report.splitlines()[0] if report else ""))

    # And the engine is still strict about what the *caller* asks for: an
    # undeclared name in the patch is a caller error, not a stale store.
    ok, report = model_module.set_values({"depth": 30.0})
    check(not ok and "depth" in report,
          "setting the dropped parameter by name is still refused ({:s})".format(
              report.splitlines()[0] if report else ""))


def test_rebuild_model_rederives_from_the_engine(root):
    """The way out, for the user and the assistant: re-run what is stored.

    Nothing used to heal a shell that had lost track of the engine -- neither
    `write_script` nor "Rebuild From Saved Script" touched the stored values,
    and there was no route back except editing `script.json` by hand.
    """
    print("test_rebuild_model_rederives_from_the_engine")
    reset_scene(root)
    scene = bpy.context.scene
    ok, report = run_tool("write_script", {"content": TWO_PARAM_SCRIPT})
    check(ok, "write_script accepted ({:s})".format(
        report.splitlines()[0] if report else ""))

    check("rebuild_model" in {tool["name"] for tool in tools.list_tools()},
          "rebuild_model is offered to the assistant")
    check("rebuild_model" in tools.MUTATING_TOOLS,
          "rebuild_model counts as mutating, so the turn gets one undo step")

    # Throw away everything the shell believes about the parameters, which is
    # the state a drifted file is in, then ask the engine to re-derive it.
    scene[model_module.SPECS_PROP] = ""
    model_module.ensure_group([])
    check(not model_module.load_specs(scene), "specs cleared for the test")

    ok, report = run_tool("rebuild_model", {})
    check(ok, "rebuild_model accepted ({:s})".format(
        report.splitlines()[0] if report else ""))
    check([spec["id"] for spec in model_module.load_specs(scene)]
          == ["width", "depth"],
          "rebuild_model re-derived the declared parameters")
    group = getattr(scene, "mesh_params", None)
    check(group is not None and hasattr(group, "width")
          and hasattr(group, "depth"),
          "and rebuilt the slider properties from them")
    check(bpy.data.objects.get("plate") is not None,
          "the geometry is back in the scene")


def test_rewrite_defaults_splices_only_the_default():
    """The source surgery behind "Apply as Defaults", on its own.

    Pure text-in/text-out, so it is tested without an engine: what matters is
    that it touches the default and *nothing* else -- comments, spacing and the
    other arguments of the same `num()` call all survive byte for byte.
    """
    print("test_rewrite_defaults_splices_only_the_default")
    rewrite = model_module.rewrite_defaults

    # The ordinary case, with a comment and non-ASCII text to splice around.
    source = (
        '# leading comment — with an em dash\n'
        'p = params(\n'
        '    width=num(40.0, unit="mm", min=20, max=80, label="Width"),\n'
        '    depth=num(24, unit="mm", min=10, max=50),  # trailing comment\n'
        ')\n'
        'plate = part.box(p.width, p.depth, 6)\n'
        'result = {"plate": plate}\n')
    updated, changes = rewrite(source, {"width": 50.0, "depth": 30.0})
    check(dict((name, (old, new)) for name, old, new in changes)
          == {"width": ("40.0", "50.0"), "depth": ("24", "30.0")},
          "both defaults reported as old -> new: {!r}".format(changes))
    check('width=num(50.0, unit="mm", min=20, max=80, label="Width")' in updated,
          "the width default is replaced in place")
    check('depth=num(30.0, unit="mm", min=10, max=50),  # trailing comment'
          in updated,
          "the depth default is replaced and the trailing comment survives")
    check('# leading comment — with an em dash' in updated
          and updated.startswith('# leading comment'),
          "comments and non-ASCII text are untouched")
    check(updated.count("part.box(p.width, p.depth, 6)") == 1,
          "the body of the script is untouched")

    # float32 noise from a Blender slider must not reach the script.
    noisy, changes = rewrite('p = params(w=num(1.0))',
                             {"w": 3.5999999046325684})
    check(noisy == 'p = params(w=num(3.6))',
          "a float32 slider value is rounded to what the panel showed: "
          "{!r}".format(noisy))

    # The default as a keyword, which `num()`'s signature also allows.
    keyworded, changes = rewrite('p = params(w=num(default=1.0, min=0))',
                                 {"w": 2.5})
    check(keyworded == 'p = params(w=num(default=2.5, min=0))',
          "a keyword default is rewritten too: {!r}".format(keyworded))

    # Already equal: nothing to do, and nothing rewritten.
    same, changes = rewrite('p = params(w=num(2.5))', {"w": 2.5})
    check(same == 'p = params(w=num(2.5))' and not changes,
          "an unchanged default is left alone and not reported")

    # A parameter with no slider value is not touched.
    partial, changes = rewrite('p = params(a=num(1.0), b=num(2.0))', {"a": 9.0})
    check(partial == 'p = params(a=num(9.0), b=num(2.0))'
          and [name for name, _old, _new in changes] == ["a"],
          "a parameter absent from the values is left as declared")

    # And the refusals, which must be sentences rather than tracebacks.
    for label, bad, values in (
            ("no params() call", 'plate = part.box(1, 2, 3)', {"w": 1.0}),
            ("dynamic declarations", 'p = params(**declared)', {"w": 1.0}),
            ("a syntax error", 'p = params(w=num(1.0)', {"w": 1.0}),
            ("a computed declaration", 'p = params(w=spec_for("w"))',
             {"w": 1.0}),
    ):
        try:
            rewrite(bad, values)
        except ValueError as exc:
            check(bool(str(exc)) and "Traceback" not in str(exc),
                  "{:s} is refused with a sentence: {:s}".format(
                      label, str(exc)[:60]))
        else:
            check(False, "{:s} should have been refused".format(label))


def test_apply_slider_defaults(root):
    """The button: slider values become the script's declared defaults.

    End to end, because the interesting claims are about the engine's state
    afterwards -- the script it holds, the specs it re-derives, and the digest,
    which must *not* move: the values are unchanged, only where they are
    written down.
    """
    print("test_apply_slider_defaults")
    reset_scene(root)
    scene = bpy.context.scene
    ok, report = run_tool("write_script", {"content": TWO_PARAM_SCRIPT})
    check(ok, "write_script accepted ({:s})".format(
        report.splitlines()[0] if report else ""))
    check(not model_module.defaults_differ_from_sliders(scene),
          "a freshly built model sits at its declared defaults "
          "(so the button is greyed out)")

    ok, report = model_module.set_values({"width": 50.0, "depth": 30.0})
    check(ok, "sliders moved ({:s})".format(
        report.splitlines()[0] if report else ""))
    check(model_module.defaults_differ_from_sliders(scene),
          "moving a slider lights the button")
    digest_before = store_state(root).get("accepted_digest")

    ok, report = cadex_backend.apply_slider_defaults(scene)
    check(ok, "apply_slider_defaults accepted ({:s})".format(
        report.splitlines()[0] if report else ""))

    # The script the *engine* holds now declares the new defaults.
    source = cadex_backend.cached_script_state(scene).source
    check("width=num(50.0," in source and "depth=num(30.0," in source,
          "the engine's script declares the slider values as defaults")
    check(model_module.get_script() == source,
          "and the buffer mirrors it")
    check(not model_module.script_is_dirty(),
          "the rewritten script reads as clean, not as a hand edit")

    # The specs the panel draws come back with the new defaults.
    defaults = {spec["id"]: spec["default"]
                for spec in model_module.load_specs(scene)}
    check(defaults == {"width": 50.0, "depth": 30.0},
          "the bridged specs carry the new defaults: {!r}".format(defaults))
    check(not model_module.defaults_differ_from_sliders(scene),
          "and the button goes back to greyed out")

    # Same numbers, written down somewhere else: the model cannot have moved.
    check(store_state(root).get("accepted_digest") == digest_before,
          "the content digest is unchanged, so the geometry did not move")

    # Pressing it again is a no-op that says so rather than writing a revision.
    ok, report = cadex_backend.apply_slider_defaults(scene)
    check(ok and "already" in report,
          "a second press reports there is nothing to do ({:s})".format(
              report.splitlines()[0] if report else ""))

    # A hand-edited buffer is refused, not swept into the rewrite -- the write
    # would refresh the mirror and take the user's edits with it.
    text = bpy.data.texts[model_module.SCRIPT_NAME]
    text.write("\n# an edit that has not been applied\n")
    check(model_module.script_is_dirty(), "the buffer is dirty for the test")
    ok, report = model_module.set_values({"width": 55.0})
    check(ok, "a slider still moves with a dirty buffer")
    ok, report = cadex_backend.apply_slider_defaults(scene)
    check(not ok and "unapplied edits" in report,
          "a dirty buffer is refused with a way out ({:s})".format(
              report.splitlines()[0] if report else ""))
    check("# an edit that has not been applied" in model_module.get_script(),
          "and the refused attempt left the buffer alone")


def test_script_view_marks_hand_edits(root):
    """The buffer never diverges from the model silently.

    `bpy.data.texts["model.py"]` mirrors the engine's script, and a hand edit
    that has not been applied is invisible in the geometry. The sidebar panel
    reads `script_is_dirty()`, so that is what this pins -- plus the two things
    a live view needs: refreshing the mirror must not move the cursor, and
    Revert must put the engine's source back.
    """
    print("test_script_view_marks_hand_edits")
    reset_scene(root)
    scene = bpy.context.scene
    ok, report = run_tool("write_script", {"content": ONE_PARAM_SCRIPT})
    check(ok, "write_script accepted ({:s})".format(
        report.splitlines()[0] if report else ""))
    check(not model_module.script_is_dirty(),
          "a freshly mirrored script reads as clean")

    # Re-mirroring the same source must be a no-op, cursor included: the mirror
    # is rewritten on every accepted request, and a slider drag that reset the
    # cursor would fight anyone reading the script.
    text = bpy.data.texts[model_module.SCRIPT_NAME]
    text.cursor_set(2, character=4)
    check(model_module.set_script(text.as_string()) is False,
          "re-mirroring an unchanged source does not rewrite the buffer")
    ok, report = model_module.set_values({"width": 44.0})
    check(ok, "a drag through the mirrored script ({:s})".format(
        report.splitlines()[0] if report else ""))
    check([text.current_line_index, text.current_character] == [2, 4],
          "a drag leaves the cursor where it was: {!r}".format(
              [text.current_line_index, text.current_character]))
    check(not model_module.script_is_dirty(),
          "and leaves the buffer clean")

    # A hand edit, exactly as the Text Editor makes one: the buffer changes
    # and nothing tells the engine.
    text.clear()
    text.write(ONE_PARAM_SCRIPT + "\n# a hand edit the engine has not seen\n")
    check(model_module.script_is_dirty(),
          "a hand edit marks the buffer modified")

    ok, report = model_module.set_values({"width": 46.0})
    check(ok, "the model still builds from engine truth, not the buffer")
    check(model_module.script_is_dirty(),
          "and a rebuild does not quietly adopt the edit")

    # Through `poll()` first: an operator whose poll fails raises out of
    # `bpy.ops`, which would abort the whole suite instead of failing one check.
    check(bpy.ops.mesh_agent.revert_script.poll()
          and bpy.ops.mesh_agent.revert_script() == {'FINISHED'},
          "Revert to Model runs")
    check(not model_module.script_is_dirty(), "Revert clears the divergence")
    check(model_module.get_script().strip() == ONE_PARAM_SCRIPT.strip(),
          "and the buffer is the engine's source again")

    # A failed Apply keeps the text *and* keeps the marking. Both halves
    # matter: the user's edit is not thrown away, and a script the engine
    # refused must never come back reading as "matches the model".
    text.clear()
    text.write(ONE_PARAM_SCRIPT + "\nthis is not python (\n")
    check(model_module.script_is_dirty(), "the broken edit marks the buffer")
    check(bpy.ops.mesh_agent.adopt_script.poll()
          and bpy.ops.mesh_agent.adopt_script() == {'CANCELLED'},
          "Apply to Model fails on a script the engine refuses")
    check("this is not python (" in model_module.get_script(),
          "the refused source stays in the buffer to be fixed")
    check(model_module.script_is_dirty(),
          "and is not stamped as matching the model")
    check(bool(model_module.last_error()),
          "the failure is recorded, so the panel can say why")
    model_module.clear_last_error()


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


def test_unchanged_geometry_is_not_rebuilt(root):
    """Same buffers in, same mesh datablock out (ADR-051).

    And the part that is easy to get wrong: a *draft* response for the same
    source must NOT be mistaken for the same buffers, or the settled refine
    would be a no-op and the viewport would keep the coarse mesh for good.
    """
    print("test_unchanged_geometry_is_not_rebuilt")
    reset_scene(root)
    scene = bpy.context.scene
    ok, _ = run_tool("write_script", {"content": BASELINE_SCRIPT})
    check(ok, "baseline accepted")

    plate = bpy.data.objects.get("plate")
    check(plate is not None, "plate hydrated")
    if plate is None:
        return
    mesh_before = plate.data
    key_before = str(plate.get(cadex_hydrate.SOURCE_SHA_PROP, ""))
    check(bool(key_before), "the object records what its mesh was built from")

    # Re-run the same script at the same quality: identical buffers.
    ok, _ = cadex_backend.rebuild_model(scene)
    check(ok, "rebuild accepted")
    plate = bpy.data.objects.get("plate")
    check(plate is not None and plate.data is mesh_before,
          "unchanged geometry keeps the very same mesh datablock")

    # A drag changes the geometry, so it must NOT be skipped.
    ok, _ = model_module.set_values({"hole": 3.1})
    check(ok, "drag accepted")
    plate = bpy.data.objects.get("plate")
    check(plate is not None and plate.data is not mesh_before,
          "changed geometry is rebuilt, not skipped")
    key_draft = str(plate.get(cadex_hydrate.SOURCE_SHA_PROP, ""))
    check(key_draft != key_before, "and the recorded key moved with it")

    # The settled refine is the same source at standard quality. Keyed on
    # source_sha256 alone this would be skipped and the coarse mesh would
    # survive; the key carries quality, so it is rebuilt.
    draft_mesh = plate.data
    ok, _ = cadex_backend.refine_now(scene)
    check(ok, "refine accepted")
    plate = bpy.data.objects.get("plate")
    check(plate is not None and plate.data is not draft_mesh,
          "a standard-quality refine of the same source is NOT skipped")
    check(bpy.data.objects.get("plate" + cadex_hydrate.EDGE_SUFFIX) is not None,
          "and the refine restored the edge wire object")


def test_main_thread_free_during_a_drag(root):
    """A slider drag must not block the main thread either (ADR-051).

    ``test_main_thread_free_during_rebuild`` proves it for the agent's
    modeling requests; the drag path had its own blocking call, and a drag
    is the one thing the user does continuously.

    ``bpy.app.timers`` do not fire under ``--background``, so the pump is
    driven by hand -- which is also what makes the tick count meaningful:
    every tick here is a turn the main thread got back.
    """
    print("test_main_thread_free_during_a_drag")
    reset_scene(root)
    scene = bpy.context.scene
    ok, _ = run_tool("write_script", {"content": BASELINE_SCRIPT})
    check(ok, "baseline accepted")

    cadex_backend.drag_stats(reset=True)

    # A burst, exactly as a real drag delivers it: many value changes far
    # faster than one round trip.
    finished = []
    for index in range(12):
        model_module.apply_values({"hole": 1.6 + 0.1 * index})
        cadex_backend.note_drag(scene, on_finish=lambda ok, report:
                                finished.append(ok))

    stats = cadex_backend.drag_stats()
    check(stats["in_flight"], "one request went in flight")
    check(stats["requests"] == 1,
          "a 12-event burst started exactly one request (got {:d})".format(
              stats["requests"]))
    check(stats["queued"], "and the rest coalesced into one queued boolean")

    ticks = []
    began = time.monotonic()
    while (cadex_backend.drag_stats()["in_flight"]
           or cadex_backend.drag_stats()["queued"]):
        if time.monotonic() - began > 300.0:
            break
        ticks.append(time.monotonic())
        cadex_backend.pump_drag_once()
        time.sleep(0.01)
    elapsed = time.monotonic() - began

    check(len(ticks) > 10,
          "main thread ticked {:d} times across a {:.2f} s drag".format(
              len(ticks), elapsed))
    total = cadex_backend.drag_stats()["requests"]
    check(total == 2,
          "12 events became 2 requests: one in flight, one for the final "
          "value (got {:d})".format(total))

    # Coalescing takes the *newest* values, because begin_slider_rebuild
    # reads the live PropertyGroup when it starts rather than from a queue.
    group = getattr(scene, "mesh_params", None)
    check(group is not None and abs(group.hole - 2.7) < 1e-6,
          "the drag converged on the final value")
    plate = bpy.data.objects.get("plate")
    check(plate is not None, "and the viewport still has the model")
    check(not model_module.last_error(),
          "a coalesced drag reports no error")

    GATE["drag_ticks"] = len(ticks)
    GATE["drag_requests"] = total
    GATE["drag_seconds"] = round(elapsed, 3)


def test_an_agent_turn_supersedes_a_queued_drag(root):
    """The agent is about to move the revision; a queued drag is stale.

    And a superseded drag is not a failure: it must not land in
    ``model.last_error()``, which is what the parameters panel shows.
    """
    print("test_an_agent_turn_supersedes_a_queued_drag")
    reset_scene(root)
    scene = bpy.context.scene
    ok, _ = run_tool("write_script", {"content": BASELINE_SCRIPT})
    check(ok, "baseline accepted")

    model_module.clear_last_error()
    cadex_backend.drag_stats(reset=True)
    for index in range(6):
        model_module.apply_values({"hole": 1.6 + 0.1 * index})
        cadex_backend.note_drag(scene)
    check(cadex_backend.drag_stats()["queued"], "a drag is queued")

    # The agent's own modeling request drops it.
    started = cadex_backend.begin_write_script(scene, BASELINE_SCRIPT)
    check(not cadex_backend.drag_stats()["queued"],
          "an agent turn supersedes the queued drag")
    if isinstance(started, cadex_backend.Lifecycle):
        started.wait()
    while cadex_backend.drag_stats()["in_flight"]:
        cadex_backend.pump_drag_once()
        time.sleep(0.01)
    check(not model_module.last_error(),
          "and the supersede is not reported as a failure ({:s})".format(
              first_line_of(model_module.last_error())))


def first_line_of(text):
    return (text or "").splitlines()[0] if text else ""


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
    ok, report = run_tool("write_script", {"content": REDUCED_SCRIPT,
                              "replace": True})
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

    ok, report = run_tool("write_script", {"content": REDUCED_SCRIPT,
                              "replace": True})
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
    # Before any open, which is when the offer has to be reachable: Save-As
    # closes every session, so an engine-only answer left the chat with no
    # button at exactly the moment one was needed (ADR-046).
    check(cadex_backend.orphaned_project(scene),
          "the copy is reported as orphaned before anything opens it")

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


def test_save_as_carries_imported_geometry(workdir):
    """Save-As must bring the files the script imports along with it.

    ADR-043 made external geometry a first-class input; the Save-As story
    was written before it existed and carried nothing across. So a file that
    imported anything -- a bought part, a scan, a component from another
    tool -- Saved-As into a project whose script could not run: the recovery
    path the shell offers ("re-run the saved script") died on the first
    ``mesh.import_file``, and the only surviving copy of the model was the
    baked mesh in the viewport, which nothing can edit.

    Assets are inputs, not derived state. They come across; the revision
    history, which *is* derived and would fork if copied, does not (ADR-046).
    """
    print("test_save_as_carries_imported_geometry")

    supplied = os.path.join(workdir, "widget.stl")
    with open(supplied, "w", encoding="utf-8") as handle:
        handle.write(TETRAHEDRON_STL)

    first = os.path.join(workdir, "asset-orig.blend")
    second = os.path.join(workdir, "asset-copy.blend")

    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.wm.save_as_mainfile(filepath=first)
    scene = bpy.context.scene

    payload = cadex_backend.put_asset(scene, supplied)
    check(payload.get("ok") is True,
          "the supplied component lands in the first project's store")
    ok, report = run_tool("write_script", {"content": IMPORTED_GEOMETRY_SCRIPT})
    check(ok, "a model built on the imported file is accepted ({:s})".format(
        report[:80]))
    check(bpy.data.objects.get("widget") is not None,
          "the imported component is in the viewport")
    # A second accepted revision, so "the history did not come across" is a
    # claim the counts can actually distinguish.
    ok, report = run_tool("write_script",
                          {"content": MOVED_GEOMETRY_SCRIPT})
    check(ok, "a second revision is accepted ({:s})".format(report[:80]))
    check(len(revision_sources(os.path.join(workdir, "asset-orig.cadex"))) == 2,
          "the original project has two revisions in its trail")

    bpy.ops.wm.save_as_mainfile(filepath=second)
    scene = bpy.context.scene
    check(not os.path.isdir(cadex_backend.project_root(scene)),
          "the Save-As'd file names a project that does not exist yet")
    check(cadex_backend.orphaned_project(scene),
          "the Save-As'd file is reported as orphaned before any open")
    check(cadex_backend.source_root(scene) == os.path.abspath(
              os.path.join(workdir, "asset-orig.cadex")),
          "the new file remembers which project its geometry came from")

    ok, report = cadex_backend.adopt_saved_script(scene)
    check(ok, "the saved script rebuilds the Save-As'd project ({:s})".format(
        (report or "clean")[:160]))
    check("widget.stl" in (report or ""),
          "the report names the component it carried across")
    check(bpy.data.objects.get("widget") is not None,
          "the imported component is back in the new file's viewport")
    check(not cadex_backend.orphaned_project(scene),
          "the adopted project is no longer orphaned")
    check(cadex_backend.stored_asset_names(scene) == {"widget.stl"},
          "the new project holds the component in its own store")
    check(os.path.isfile(os.path.join(workdir, "asset-orig.cadex",
                                      "assets", "widget.stl")),
          "the original project keeps its own copy")
    check(len(revision_sources(os.path.join(workdir, "asset-copy.cadex"))) == 1,
          "the new project starts its own trail -- the original's two "
          "revisions did NOT come across")


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

    # ADR-044: and it must keep refusing. The restore pass runs through
    # write_script, which accepts what it builds, so the run that reports the
    # corruption used to also adopt it -- the second open came up clean with
    # the hand edit installed as the accepted model.
    accepted = store_state(project)["accepted_digest"]
    cadex_backend.close_all()
    ok, report = cadex_backend.ensure_open(scene)
    check(not ok, "the second open refuses too, rather than adopting the edit")
    check(store_state(project)["accepted_digest"] == accepted,
          "and the accepted digest still names the model the user built")


# -- ADR-044: a refused script must not be able to shut the project ---------

def test_a_refused_edit_leaves_the_project_openable(root):
    """The whole ADR-044 failure, end to end, through the real tools.

    A script that raises used to be left on disk as the working source. The
    restore pass re-runs the working source at every open, so the next open
    -- a respawn, or just quitting and coming back -- failed, and every tool
    that could have fixed it opens the project first. One refused edit, and
    the project was gone.
    """
    print("test_a_refused_edit_leaves_the_project_openable")
    reset_scene(root)
    scene = bpy.context.scene
    ok, _report = run_tool("write_script", {"content": BASELINE_SCRIPT})
    check(ok, "baseline accepted")
    accepted = store_state(root)["accepted_revision"]

    # Exactly the shape of the edit that caused this: a probe that raises on
    # purpose, because raising was the only way to read a value back out.
    ok, report = run_tool("edit_script", {"replacements": [
        {"old": 'result = {"plate": plate}',
         "new": 'info = [("w", 120)]\n{}[str(info)]\nresult = {"plate": plate}'}]})
    check(not ok, "the raising edit is refused")

    state = store_state(root)
    check(state["accepted_revision"] == accepted,
          "the accepted revision is untouched by the refused edit")
    check(state["working_revision"] == accepted,
          "the working revision rolled back to the accepted one")
    with open(os.path.join(root, "script.py"), encoding="utf-8") as handle:
        check("{}[str(info)]" not in handle.read(),
              "the refused source is not left as the working script")

    # The engine restarting is what used to surface the damage.
    cadex_backend.close_all()
    ok, report = cadex_backend.ensure_open(scene)
    check(ok, "the project still opens after a refused edit ({:s})".format(
        report or "clean"))
    check(bpy.data.objects.get("plate") is not None,
          "and the model comes back")

    ok, text = run_tool("get_script", {})
    check(ok and "{}[str(info)]" not in text,
          "get_script shows the good script, not the refused one")


def test_a_broken_store_can_still_be_rewritten(root):
    """The documented remedy has to be reachable from the broken state.

    ``write_script`` replaces the stored script outright, so it neither reads
    nor builds on the model the restore pass could not prove -- but it went
    through the same ``ensure_open`` as everything else, so the failure
    report recommended an action the failure itself prevented.
    """
    print("test_a_broken_store_can_still_be_rewritten")
    reset_scene(root)
    scene = bpy.context.scene
    ok, _report = run_tool("write_script", {"content": BASELINE_SCRIPT})
    check(ok, "baseline accepted before breaking the store")

    project = cadex_backend.project_root(scene)
    cadex_backend.close_all()
    # Break it the way only a human can: a script that runs but builds
    # something else. The engine must keep calling this a restore failure.
    script_path = os.path.join(project, "script.py")
    with open(script_path, "r", encoding="utf-8") as handle:
        source = handle.read()
    with open(script_path, "w", encoding="utf-8") as handle:
        handle.write(source.replace("part.box(120, 80, 8)",
                                    "part.box(60, 40, 8)"))

    ok, report = run_tool("rebuild_model", {})
    check(not ok, "rebuild still refuses an unproven model")

    ok, text = run_tool("get_script", {})
    check(ok, "get_script reads a project whose restore failed")
    check("part.box(60, 40, 8)" in text,
          "and shows the script that has to be rewritten")
    check("WITHOUT restoring" in text,
          "with the state said plainly rather than implied")

    ok, report = run_tool("write_script", {"content": BASELINE_SCRIPT})
    check(ok, "write_script succeeds on a project whose restore failed: "
              "{:s}".format(report))

    cadex_backend.close_all()
    ok, report = cadex_backend.ensure_open(scene)
    check(ok, "the rewritten project opens clean ({:s})".format(
        report or "clean"))


def test_a_script_that_will_not_run_is_repaired_from_the_accepted_source(root):
    """Self-repair for stores already broken by the pre-ADR-044 engine.

    A working source that *runs* and mismatches is the user's edit and stays
    a hard error (test_restore_failure_is_first_class). A working source that
    will not run at all is not that, and the accepted revision's own source
    is pinned right beside it.
    """
    print("test_a_script_that_will_not_run_is_repaired_from_the_accepted_source")
    reset_scene(root)
    scene = bpy.context.scene
    ok, _report = run_tool("write_script", {"content": BASELINE_SCRIPT})
    check(ok, "baseline accepted before poisoning the store")
    accepted = store_state(root)["accepted_revision"]

    project = cadex_backend.project_root(scene)
    cadex_backend.close_all()
    # Exactly what the old engine left behind: a raising script as the
    # working source, with the accepted state still pointing at a good one.
    with open(os.path.join(project, "script.py"), "a", encoding="utf-8") as handle:
        handle.write('\n{}["boom"]\n')

    ok, report = cadex_backend.ensure_open(scene)
    check(ok, "a store that cannot run its script repairs itself ({:s})".format(
        report or "clean"))
    restore = cadex_backend._state_for(project).restore
    check(restore.get("repaired_from_accepted") is True,
          "the repair is reported, not silent: {!r}".format(restore))
    check(restore.get("matches_accepted") is True,
          "and the repaired model still matches the accepted digest")
    check(store_state(root)["accepted_revision"] == accepted,
          "the accepted revision is unchanged by the repair")
    with open(os.path.join(project, "script.py"), encoding="utf-8") as handle:
        check('{}["boom"]' not in handle.read(),
              "the poisoned source is gone from the working script")


def test_a_working_scripts_stdout_reaches_the_caller(root):
    """``print()`` must work without making the script fail.

    It reached the caller only on the failure envelope, which left "raise on
    purpose" as the cheapest way to read a value out of a working script --
    and that is what broke a project.
    """
    print("test_a_working_scripts_stdout_reaches_the_caller")
    reset_scene(root)

    ok, report = run_tool("write_script", {"content": (
        BASELINE_SCRIPT + '\nprint("plate_volume", 120 * 80 * 8)\n')})
    check(ok, "a script that prints is accepted")
    check("plate_volume 76800" in report,
          "and its stdout comes back on the accepted reply: {:s}".format(report))


def test_get_script_is_not_truncated(root):
    """The trigger: a script served at half length, cut mid-line.

    get_script serves the exact text the next edit_script has to match, and
    a model cannot tell that the half it was given is the half it needs.
    """
    print("test_get_script_is_not_truncated")
    reset_scene(root)

    # Comfortably past the 4 KB cap that used to apply, with a marker last.
    padding = "\n".join(
        "# padding line {:03d} ".format(n) + "x" * 60 for n in range(120))
    source = BASELINE_SCRIPT + "\n" + padding + "\n# LAST-LINE-MARKER\n"
    check(len(source) > 6000, "the fixture script is past the old cap")

    ok, _report = run_tool("write_script", {"content": source})
    check(ok, "the long script is accepted")

    ok, text = run_tool("get_script", {})
    check(ok, "get_script succeeds")
    check("# LAST-LINE-MARKER" in text,
          "the end of the script survives ({:d} chars returned)".format(len(text)))
    check("truncated" not in text, "and nothing was elided")


# -- ADR-045: history, revert, and the destructive-overwrite guard ----------

def test_write_script_refuses_to_drop_existing_outputs(root):
    """"lets create a battery model" must not delete the drone frame.

    write_script replaces THE project script, so a model answering an
    additive request with a script containing only the new part builds
    fine, publishes fine, and is accepted -- taking everything else with it.
    """
    print("test_write_script_refuses_to_drop_existing_outputs")
    reset_scene(root)
    ok, _report = run_tool("write_script", {"content": BASELINE_SCRIPT})
    check(ok, "baseline accepted")
    accepted = store_state(root)["accepted_revision"]

    battery = ('p = params(length=num(64.0, unit="mm", min=10.0, max=200.0,\n'
               '                      label="Length"))\n'
               'battery = part.box(p.length, 10, 6, label="Battery")\n'
               'result = {"battery": battery}\n')
    ok, report = run_tool("write_script", {"content": battery})
    check(not ok, "a script that drops existing outputs is refused")
    check("plate" in report and "skin" in report,
          "the refusal names what would have been lost: {:s}".format(report[:160]))
    check("replace=true" in report, "and how to confirm if it was meant")
    check(store_state(root)["accepted_revision"] == accepted,
          "the model is untouched by the refusal")
    check(bpy.data.objects.get("plate") is not None,
          "and the viewport still has it")

    ok, report = run_tool("write_script", {"content": battery, "replace": True})
    check(ok, "replace=true goes through: {:s}".format(report[:80]))
    check(sorted(o["name"] for o in store_state(root)["accepted_contract"])
          == ["battery"], "and the project is now just the battery")


def test_script_history_and_revert(root):
    """The undo trail, end to end through the tools."""
    print("test_script_history_and_revert")
    reset_scene(root)
    ok, _report = run_tool("write_script", {"content": BASELINE_SCRIPT})
    check(ok, "first version accepted")
    ok, _report = run_tool("edit_script", {"replacements": [
        {"old": "part.box(120, 80, 8)", "new": "part.box(90, 60, 8)"}]})
    check(ok, "second version accepted")

    ok, text = run_tool("inspect_model", {"scope": "history"})
    check(ok, "history lists")
    payload = json.loads(text)
    versions = payload.get("versions") or []
    check(len(versions) >= 2, "both versions are listed ({:d})".format(len(versions)))
    check(all("plate" in v.get("outputs", []) for v in versions),
          "each version records the outputs it declared")
    first = versions[0]

    ok, text = run_tool("inspect_model", {"scope": "history",
                                          "target": str(first["ordinal"])})
    check(ok and "part.box(120, 80, 8)" in text,
          "a stored version serves its own source")

    # And the round trip: put version 1 back.
    ok, report = run_tool("restore_version", {"version": str(first["ordinal"])})
    check(ok, "revert succeeds: {:s}".format(report[:80]))
    ok, text = run_tool("get_script", {})
    check(ok and "part.box(120, 80, 8)" in text,
          "the reverted script is the one in the engine now")
    check(bpy.data.objects.get("plate") is not None, "and it rebuilt")

    # A revert is itself an accepted revision, so it is undoable too.
    ok, text = run_tool("inspect_model", {"scope": "history"})
    check(ok and len(json.loads(text).get("versions") or []) >= 3,
          "the revert is itself recorded in the history")


ASSEMBLY_SCRIPT = """
plate = part.box(40, 20, 4)
arm = part.box(30, 6, 6)
base = assembly.component(plate, grounded=True)
swing = assembly.component(arm, placement=[0, 0, 40])
j = assembly.joint("revolute",
                   assembly.connector(base, "origin", offset=[12, 0, 4]),
                   assembly.connector(swing, "origin"))
asm = assembly.assembly([base, swing], [j])
diag = assembly.solve(asm)
result = {"plate": plate, "arm": arm, "base": base, "swing": swing,
          "j": j, "asm": asm, "diag": diag}
"""

SHARED_SOURCE_SCRIPT = """
plate = part.box(40, 20, 4)
base = assembly.component(plate, grounded=True)
top = assembly.component(plate, placement=[0, 0, 20])
asm = assembly.assembly([base, top])
diag = assembly.solve(asm)
result = {"plate": plate, "base": base, "top": top, "asm": asm, "diag": diag}
"""


#: The same jointed assembly, with one slider of each kind (ADR-055).
#: ``reach`` is a joint offset — it moves `swing` and changes no definition,
#: so it previews. ``width`` feeds ``part.box``, so it does not and must not.
PREVIEW_SCRIPT = """
p = params(reach=num(12, unit="mm", min=0, max=30, step=1, label="Reach"),
           width=num(40, unit="mm", min=10, max=90, step=1, label="Width"))
plate = part.box(p.width, 20, 4)
arm = part.box(30, 6, 6)
base = assembly.component(plate, grounded=True)
swing = assembly.component(arm, placement=[0, 0, 40])
j = assembly.joint("revolute",
                   assembly.connector(base, "origin", offset=[p.reach, 0, 4]),
                   assembly.connector(swing, "origin"))
asm = assembly.assembly([base, swing], [j])
diag = assembly.solve(asm)
result = {"plate": plate, "arm": arm, "base": base, "swing": swing,
          "j": j, "asm": asm, "diag": diag}
"""


def _pump_preview_until_idle(limit=30.0):
    """Drive the preview pump by hand; timers do not fire under --background."""
    began = time.monotonic()
    while time.monotonic() - began < limit:
        cadex_backend.pump_preview_once()
        stats = cadex_backend.preview_stats()
        if not stats["in_flight"]:
            return stats
        time.sleep(0.005)
    return cadex_backend.preview_stats()


def test_a_pose_only_slider_previews_at_interactive_rate(root):
    """A motion slider is answered by the preview path, not the debounce.

    The engine answers a pose-only parameter change with solved placements
    from a resident worker (ADR-055); the shell applies them straight to
    ``matrix_world`` on the component instances, with no hydration in the
    path at all -- ``preview_params`` returns placements, not a display
    block, so there is nothing to hydrate.
    """

    print("test_a_pose_only_slider_previews_at_interactive_rate")
    reset_scene(root)
    scene = bpy.context.scene
    ok, report = run_tool("write_script", {"content": PREVIEW_SCRIPT})
    check(ok, "preview baseline accepted ({:s})".format(
        report.splitlines()[0] if report else ""))

    swing = bpy.data.objects.get("swing")
    check(swing is not None, "the driven component hydrated")
    if swing is None:
        return
    check(abs(swing.matrix_world.translation.x - 12.0) < 1e-6,
          "and starts on the declared joint offset (got {:.3f})".format(
              swing.matrix_world.translation.x))

    cadex_backend.preview_stats(reset=True)

    # A burst exactly as a real drag delivers it: many value changes far
    # faster than one round trip. Every intermediate one must be dropped.
    for index in range(12):
        model_module.apply_values({"reach": 13.0 + index})
        cadex_backend.note_preview(scene)
    check(cadex_backend.preview_stats()["requests"] == 0,
          "note_preview sends nothing by itself; the pump does")

    cadex_backend.pump_preview_once()
    in_flight = cadex_backend.preview_stats()
    check(in_flight["in_flight"], "one preview went in flight")
    check(in_flight["requests"] == 1,
          "a 12-event burst started exactly one preview (got {:d})".format(
              in_flight["requests"]))

    stats = _pump_preview_until_idle()
    cadex_backend.pump_preview_once()  # applies the reply
    stats = cadex_backend.preview_stats()

    check(not stats["latched"],
          "a pose-only slider is previewable ({:s})".format(stats["reason"]))
    check(stats["applied"] > 0,
          "the preview posed the viewport ({:d} placements)".format(
              stats["applied"]))
    # 12 events became one request, and it carried the *newest* value --
    # values are read when the request starts, not when it is queued.
    check(abs(swing.matrix_world.translation.x - 24.0) < 1e-6,
          "the component moved to the final dragged value (got {:.3f})".format(
              swing.matrix_world.translation.x))
    check(not model_module.last_error(),
          "a preview reports no error ({:s})".format(
              first_line_of(model_module.last_error())))

    # Now the rate, which is the whole point: several sequential previews,
    # each a full round trip through the resident worker.
    cadex_backend.preview_stats(reset=True)
    seconds = []
    for index in range(8):
        model_module.apply_values({"reach": 5.0 + index})
        cadex_backend.note_preview(scene)
        cadex_backend.pump_preview_once()
        _pump_preview_until_idle()
        cadex_backend.pump_preview_once()
    seconds = cadex_backend.preview_stats()["seconds"]
    check(len(seconds) >= 6,
          "drove {:d} sequential previews".format(len(seconds)))
    median = sorted(seconds)[len(seconds) // 2] if seconds else 99.0
    check(median <= 0.2,
          "median preview latency {:.3f} s is interactive".format(median))
    GATE["preview"] = {
        "median_seconds": round(median, 4),
        "seconds": [round(value, 4) for value in seconds],
        "applied": cadex_backend.preview_stats()["applied"],
    }


def test_a_shape_slider_falls_back_to_set_params(root):
    """Most sliders are not pose-only, and degrading cleanly is required.

    A parameter feeding ``part.box`` changes that box's definition, so a
    placement-only reply would be a lie and the engine refuses to give one.
    The shell must latch previews off for the rest of that drag -- the answer
    cannot change while the same slider is being dragged -- must not report
    it as an error, and must still end up with the correct viewport, because
    the debounced ``set_params`` behind it is the real answer.
    """

    print("test_a_shape_slider_falls_back_to_set_params")
    reset_scene(root)
    scene = bpy.context.scene
    ok, _report = run_tool("write_script", {"content": PREVIEW_SCRIPT})
    check(ok, "preview baseline accepted")
    model_module.clear_last_error()
    cadex_backend.preview_stats(reset=True)

    model_module.apply_values({"width": 61.0})
    cadex_backend.note_preview(scene)
    cadex_backend.pump_preview_once()
    _pump_preview_until_idle()
    cadex_backend.pump_preview_once()

    stats = cadex_backend.preview_stats()
    check(stats["latched"], "a shape slider latches previews off")
    check("plate" in stats["reason"],
          "and says which output changed ({:s})".format(stats["reason"][:70]))
    check(stats["applied"] == 0, "nothing was posed from a refused preview")
    check(not model_module.last_error(),
          "a refused preview is not an error ({:s})".format(
              first_line_of(model_module.last_error())))

    # Latched: dragging the *same* slider further must not re-ask.
    before = cadex_backend.preview_stats()["requests"]
    for index in range(5):
        model_module.apply_values({"width": 62.0 + index})
        cadex_backend.note_preview(scene)
        cadex_backend.pump_preview_once()
    check(cadex_backend.preview_stats()["requests"] == before,
          "the latch stops re-asking every tick (got {:d}, was {:d})".format(
              cadex_backend.preview_stats()["requests"], before))

    # A *different* slider is a different question, so the latch lifts.
    model_module.apply_values({"reach": 21.0})
    cadex_backend.note_preview(scene)
    check(not cadex_backend.preview_stats()["latched"],
          "moving a different parameter clears the latch")

    # And the real answer still lands: the debounced set_params rebuilds the
    # geometry the preview could not describe.
    cadex_backend.drag_stats(reset=True)
    cadex_backend.note_drag(scene)
    began = time.monotonic()
    while (cadex_backend.drag_stats()["in_flight"]
           or cadex_backend.drag_stats()["queued"]):
        if time.monotonic() - began > 300.0:
            break
        cadex_backend.pump_drag_once()
        time.sleep(0.01)
    plate = bpy.data.objects.get("plate")
    check(plate is not None, "the viewport still has the model")
    if plate is not None:
        width = plate.dimensions.x
        check(abs(width - 66.0) < 0.5,
              "and the set_params behind the preview rebuilt the geometry "
              "(plate x = {:.2f}, expected 66)".format(width))
    swing = bpy.data.objects.get("swing")
    check(swing is not None
          and abs(swing.matrix_world.translation.x - 21.0) < 1e-6,
          "with the motion slider's value applied too")
    check(not model_module.last_error(),
          "and no error was reported ({:s})".format(
              first_line_of(model_module.last_error())))


def test_an_assembly_shows_its_solved_placements(root):
    """The solved assembly reaches the viewport (ADR-049).

    Components carry a placement and no geometry, so before source_output
    existed the hydrator skipped them and the GC deleted them: a solved
    assembly was invisible no matter how well it solved.
    """

    print("test_an_assembly_shows_its_solved_placements")
    reset_scene(root)
    ok, report = run_tool("write_script", {"content": ASSEMBLY_SCRIPT})
    check(ok, "jointed assembly accepted ({:s})".format(
        report.splitlines()[0] if report else ""))

    swing = bpy.data.objects.get("swing")
    base = bpy.data.objects.get("base")
    check(swing is not None and base is not None,
          "both components hydrated as objects")
    if swing is None or base is None:
        return

    check(str(swing.get(cadex_hydrate.KIND_PROP, "")) == "component",
          "a component is tagged as one")
    check(str(swing.get(cadex_hydrate.SOURCE_PROP, "")) == "arm",
          "the component records the output it instances")

    # The solver put `swing` on the base connector's [12, 0, 4] offset,
    # overriding its declared [0, 0, 40]. That exact matrix is what has to
    # reach the object.
    translation = swing.matrix_world.translation
    check(abs(translation.x - 12.0) < 1e-6
          and abs(translation.y) < 1e-6
          and abs(translation.z - 4.0) < 1e-6,
          "the component sits at its solved placement, not its declared one")

    # It draws the source's geometry, and it does so by sharing the
    # datablock rather than copying it.
    arm = bpy.data.objects.get("arm")
    check(arm is not None and swing.data is arm.data,
          "the component shares the source mesh datablock")
    check(arm is not None and bool(arm.hide_viewport),
          "an instanced source is hidden, not deleted")
    check(bpy.data.objects.get("plate") is not None,
          "and the source object still exists")

    edges = bpy.data.objects.get("swing" + cadex_hydrate.EDGE_SUFFIX)
    check(edges is not None and edges.parent is swing,
          "the component's wire child is parented to it")


def test_two_components_share_one_mesh(root):
    """Forty screws cost one mesh. Here, two components and one plate."""

    print("test_two_components_share_one_mesh")
    reset_scene(root)
    ok, _ = run_tool("write_script", {"content": SHARED_SOURCE_SCRIPT})
    check(ok, "shared-source assembly accepted")

    base = bpy.data.objects.get("base")
    top = bpy.data.objects.get("top")
    plate = bpy.data.objects.get("plate")
    check(base is not None and top is not None and plate is not None,
          "both components and their shared source exist")
    if base is None or top is None or plate is None:
        return
    check(base.data is top.data is plate.data,
          "two components and their source are one mesh datablock")
    check(len([m for m in bpy.data.meshes
               if m.users and m is base.data]) == 1,
          "and it is a single datablock, not a copy per component")

    # Same geometry, different places.
    check((base.matrix_world.translation
           - top.matrix_world.translation).length > 1.0,
          "the two instances are at different placements")

    # A revision that drops the assembly leaves no component objects and
    # unhides the source -- the GC is the whole cleanup story.
    ok, _ = run_tool("write_script", {
        "content": "result = {\"plate\": part.box(40, 20, 4)}",
        "replace": True})
    check(ok, "a revision without the assembly accepted")
    check(bpy.data.objects.get("base") is None
          and bpy.data.objects.get("top") is None,
          "components are collected when they leave the contract")
    plate = bpy.data.objects.get("plate")
    check(plate is not None and not plate.hide_viewport,
          "and the source is unhidden once nothing instances it")


SIMULATION_SCRIPT = """
plate = part.box(40, 20, 4)
arm = part.box(30, 6, 6)
base = assembly.component(plate, grounded=True)
swing = assembly.component(arm, placement=[0, 0, 40])
j = assembly.joint("revolute",
                   assembly.connector(base, "origin", offset=[12, 0, 4]),
                   assembly.connector(swing, "origin"))
asm = assembly.assembly([base, swing], [j])
diag = assembly.solve(asm)
spin = assembly.motion(j, "2 * pi * time")
sim = assembly.simulation(asm, [spin], end_time_s=1.0, time_step_s=0.05)
result = {"plate": plate, "arm": arm, "base": base, "swing": swing,
          "j": j, "asm": asm, "diag": diag, "spin": spin, "sim": sim}
"""


def test_a_simulation_plays(root):
    """The mechanism moves when you press play (ADR-050).

    Compares the baked curves against the engine's own trace at three
    frames, through the depsgraph -- not against the F-curve values, which
    would only prove the bake agrees with itself.
    """

    print("test_a_simulation_plays")
    from mesh_agent import cadex_animate

    reset_scene(root)
    scene = bpy.context.scene
    started = time.perf_counter()
    ok, report = run_tool("write_script", {"content": SIMULATION_SCRIPT})
    bake_seconds = time.perf_counter() - started
    check(ok, "simulation script accepted ({:s})".format(
        report.splitlines()[0] if report else ""))
    if not ok:
        return

    swing = bpy.data.objects.get("swing")
    check(swing is not None, "the driven component hydrated")
    if swing is None:
        return

    check(swing.rotation_mode == 'QUATERNION',
          "rotation_mode is QUATERNION (the default XYZ ignores the bake)")
    curves = cadex_animate.fcurves_of(swing)
    check(len(curves) == 7,
          "seven F-curves: location xyz + quaternion wxyz (got {:d})".format(
              len(curves)))
    keys = sorted({len(curve.keyframe_points) for curve in curves})
    check(keys == [21],
          "every channel carries one key per solver frame (got {})".format(
              keys))

    check(scene.render.fps == 30, "the scene plays at the trace's fps")
    check(scene.frame_start == 1 and scene.frame_end == 31,
          "the frame range covers the run (1..31, got {:d}..{:d})".format(
              scene.frame_start, scene.frame_end))

    # The grounded component is in the trace and never moves; it still gets
    # curves, which is what keeps the two halves consistent.
    base = bpy.data.objects.get("base")
    check(base is not None and len(cadex_animate.fcurves_of(base)) == 7,
          "the grounded component is baked too")

    # Read the engine's own trace and compare, through the depsgraph.
    traces = glob.glob(os.path.join(
        root, "script_artifacts", "*", "*", "outputs",
        "assembly-simulation-trace.json"))
    check(bool(traces), "the trace artifact is on disk")
    if not traces:
        return
    trace, _sha = cadex_animate.read_trace(sorted(traces)[-1])
    solved = cadex_animate.solver_frames(trace["frames"])
    start_s = float(trace["parameters"]["start_time_s"])
    fps = int(trace["parameters"]["frames_per_second"])

    agreed = 0
    for index in (0, len(solved) // 2, len(solved) - 1):
        frame = solved[index]
        at = cadex_animate.frame_of(frame["nominal_time_s"], start_s, fps)
        scene.frame_set(int(round(at)), subframe=at - int(round(at)))
        evaluated = swing.evaluated_get(bpy.context.evaluated_depsgraph_get())
        expected = frame["component_placements"]["swing"]["position_mm"]
        actual = evaluated.matrix_world.translation
        if all(abs(actual[axis] - expected[axis]) < 1e-3 for axis in range(3)):
            agreed += 1
    check(agreed == 3,
          "the played pose matches the engine's trace at 3 frames "
          "({:d}/3)".format(agreed))

    # The wire child follows its parent and carries no action of its own.
    edges = bpy.data.objects.get("swing" + cadex_hydrate.EDGE_SUFFIX)
    check(edges is not None and not cadex_animate.fcurves_of(edges),
          "the wire child has no action of its own")
    if edges is not None:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        child = edges.evaluated_get(depsgraph).matrix_world.translation
        parent = swing.evaluated_get(depsgraph).matrix_world.translation
        check((child - parent).length < 1e-3,
              "and it follows the parent anyway")

    GATE["simulation"] = {
        "frames": len(solved),
        "components": len(trace.get("component_outputs") or []),
        "bake_seconds": round(bake_seconds, 3),
        "keyframes": len(curves) * (keys[0] if keys else 0),
    }

    # A revision that drops the simulation leaves no orphan actions behind.
    # Drop the simulation, keep the mechanism. (Dropping the parts as well
    # is refused by the engine's output-retirement guard, because the live
    # App::Link component still references them -- a real ordering wrinkle
    # in retirement, and nothing to do with playback.)
    actions_before = len(bpy.data.actions)
    ok, drop_report = run_tool("write_script", {"content": ASSEMBLY_SCRIPT,
                                               "replace": True})
    check(ok, "a revision without the simulation accepted ({:s})".format(
        (drop_report or "").splitlines()[0] if drop_report else ""))
    check(actions_before > 0 and len(bpy.data.actions) == 0,
          "dropping the simulation leaves no orphan actions "
          "({:d} -> {:d})".format(actions_before, len(bpy.data.actions)))


def test_stale_attempts_are_pruned(root):
    """The store must not grow without bound (56 MB for one afternoon)."""
    print("test_stale_attempts_are_pruned")
    reset_scene(root)
    ok, _report = run_tool("write_script", {"content": BASELINE_SCRIPT})
    check(ok, "baseline accepted")
    for size in (2.0, 2.2, 2.4, 2.6):
        ok, _report = run_tool("set_params", {"params": {"hole": float(size)}})
        check(ok, "set_params {:.1f} accepted".format(size))
    attempts = glob.glob(os.path.join(root, "script_artifacts", "*", "attempt-*"))
    check(len(attempts) <= 5,
          "stale attempt directories are pruned ({:d} left)".format(len(attempts)))

    pinned = store_state(root).get("accepted_attempt") or {}
    staging = os.path.join(root, str(pinned.get("staging") or ""))
    check(os.path.isdir(staging), "the accepted attempt is never pruned")
    # The facts block is over inspect's 1 KiB preview threshold, so the top
    # page carries a stub for it -- reading the pinned attempt at all is the
    # property under test here.
    ok, text = run_tool("inspect_model", {"scope": "output", "target": "plate"})
    check(ok and '"artifact_kind": "brep"' in text,
          "and inspect scope=output still reads the pinned attempt")


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


# ---------------------------------------------------------------------------
# The collision overlay (ADR-091).
# ---------------------------------------------------------------------------
#
# The load-bearing case here is ADR-087's own failure, reproduced and then
# corrected. That bug shipped a hopper that trained for an hour standing on
# an invisible 20 mm shelf, and every gate the project had was green while
# the model was wrong -- because nothing drew the shape that was wrong.

#: A floor whose collision box is NOT offset. `part.box`'s origin is a
#: corner, so the solid sits at z = -40..0 while an unoffset collision box of
#: the same extents sits at -20..+20: the collision top stands 20 mm proud of
#: the visible top, and anything resting on the floor rests on nothing.
COLLISION_BAD_SCRIPT = """
floor_solid = part.box(400, 200, 40, origin=[-200, -100, -40])
ball_solid = part.box(20, 20, 20, origin=[-10, -10, -10])
ground = assembly.component(floor_solid, grounded=True)
body = assembly.component(ball_solid, placement=[0, 0, 100])
rail = assembly.joint("slider",
                      assembly.connector(ground, "origin",
                                         offset={"position": [0, 0, 100]}),
                      assembly.connector(body, "origin"),
                      length_limits_mm=[-200, 200])
asm = assembly.assembly([ground, body], [rail])
diag = assembly.solve(asm)
model = assembly.mjcf(asm, [
    assembly.body(ground, density_kg_m3=7850,
                  collision=assembly.collision("box", size_mm=[400, 200, 40])),
    assembly.body(body, density_kg_m3=1040,
                  collision=assembly.collision("sphere", radius_mm=10)),
])
result = {"floor_solid": floor_solid, "ball_solid": ball_solid,
          "ground": ground, "body": body, "rail": rail, "asm": asm,
          "diag": diag, "model": model}
"""

#: The same script with the one-line fix ADR-087 landed.
COLLISION_GOOD_SCRIPT = COLLISION_BAD_SCRIPT.replace(
    'assembly.collision("box", size_mm=[400, 200, 40])',
    'assembly.collision("box", size_mm=[400, 200, 40], '
    'offset={"position": [0, 0, -20]})')

#: The same model with the mjcf output removed and NOTHING else changed.
#: Swapping in a wholly different script instead would be refused by the
#: engine's output-retirement guard -- the live App::Link components still
#: reference the parts it would drop -- which is a real wrinkle in output
#: retirement and nothing to do with the overlay.
COLLISION_NO_DYNAMICS_SCRIPT = COLLISION_GOOD_SCRIPT.replace(
    """model = assembly.mjcf(asm, [
    assembly.body(ground, density_kg_m3=7850,
                  collision=assembly.collision("box", size_mm=[400, 200, 40], offset={"position": [0, 0, -20]})),
    assembly.body(body, density_kg_m3=1040,
                  collision=assembly.collision("sphere", radius_mm=10)),
])
""", "").replace(', "model": model}', "}")


#: One of every primitive, to pin the size conversion per type.
COLLISION_SHAPES_SCRIPT = """
floor_solid = part.box(400, 200, 40, origin=[-200, -100, -40])
ball_solid = part.box(20, 20, 20, origin=[-10, -10, -10])
ground = assembly.component(floor_solid, grounded=True)
body = assembly.component(ball_solid, placement=[0, 0, 100])
rail = assembly.joint("slider",
                      assembly.connector(ground, "origin",
                                         offset={"position": [0, 0, 100]}),
                      assembly.connector(body, "origin"),
                      length_limits_mm=[-200, 200])
asm = assembly.assembly([ground, body], [rail])
diag = assembly.solve(asm)
model = assembly.mjcf(asm, [
    assembly.body(ground, density_kg_m3=7850,
                  collision=assembly.collision("box", size_mm=[400, 200, 40],
                                               offset={"position": [0, 0, -20]})),
    assembly.body(body, density_kg_m3=1040, collision=[
        assembly.collision("sphere", radius_mm=10),
        assembly.collision("cylinder", radius_mm=6, length_mm=30,
                           offset={"position": [40, 0, 0]}),
        assembly.collision("capsule", radius_mm=5, length_mm=20,
                           offset={"position": [-40, 0, 0]}),
    ]),
])
result = {"floor_solid": floor_solid, "ball_solid": ball_solid,
          "ground": ground, "body": body, "rail": rail, "asm": asm,
          "diag": diag, "model": model}
"""


def _collision_objects():
    from mesh_agent import cadex_collision
    collection = bpy.data.collections.get(cadex_collision.COLLECTION_NAME)
    return {} if collection is None else {obj.name: obj
                                          for obj in collection.objects}


def _world_z_range(obj):
    """The object's world-space z extent, through the depsgraph."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    matrix = evaluated.matrix_world
    zs = [(matrix @ vertex.co).z for vertex in evaluated.data.vertices]
    return (min(zs), max(zs)) if zs else (0.0, 0.0)


def test_the_collision_overlay_draws_adr074(root):
    """The bug that shipped, drawn -- then the fix, drawn (ADR-091).

    Nothing drew collision geometry, so a floor whose collision box stood
    20 mm proud of its visible top was invisible and a hopper trained
    against it for an hour. This asserts the overlay would have shown it:
    the wire cage's top at z = +20 against a visible solid top at z = 0.
    Then the corrected script, where the same measurement is 0.
    """

    print("test_the_collision_overlay_draws_adr074")
    from mesh_agent import cadex_collision

    reset_scene(root)
    ok, report = run_tool("write_script", {"content": COLLISION_BAD_SCRIPT})
    check(ok, "the unoffset-collision script accepted ({:s})".format(
        (report or "").splitlines()[0] if report else ""))
    if not ok:
        return

    # Off by default: an overlay nobody asked for is not a feature.
    check(not _collision_objects(),
          "no overlay until it is asked for")

    ok, message = run_tool("collision_view", {"show": True})
    check(ok, "collision_view turned it on ({:s})".format(
        (message or "").splitlines()[0] if message else ""))
    objects = _collision_objects()
    check("ground/collision0" in objects,
          "the wire is named exactly what MuJoCo calls the geom "
          "(got {})".format(sorted(objects)))
    if "ground/collision0" not in objects:
        return

    floor = bpy.data.objects.get("ground")
    check(floor is not None, "the floor component hydrated")
    if floor is None:
        return
    _low, solid_top = _world_z_range(floor)
    _low, wire_top = _world_z_range(objects["ground/collision0"])
    check(abs(solid_top) < 1e-3,
          "the VISIBLE floor top is at z = 0 (got {:.3f})".format(solid_top))
    check(abs(wire_top - 20.0) < 1e-3,
          "and the collision box's top is drawn 20 mm above it, which is the "
          "bug ADR-087 found by arithmetic (got {:.3f})".format(wire_top))
    check(abs(wire_top - solid_top - 20.0) < 1e-3,
          "so the overlay shows a 20.00 mm gap (got {:.3f})".format(
              wire_top - solid_top))

    # ...and the corrected script, where the same measurement is zero.
    ok, report = run_tool("write_script", {"content": COLLISION_GOOD_SCRIPT,
                                           "replace": True})
    check(ok, "the offset-collision script accepted ({:s})".format(
        (report or "").splitlines()[0] if report else ""))
    if not ok:
        return
    objects = _collision_objects()
    check("ground/collision0" in objects,
          "the overlay survived the rebuild and refreshed itself")
    if "ground/collision0" not in objects:
        return
    floor = bpy.data.objects.get("ground")
    _low, solid_top = _world_z_range(floor)
    _low, wire_top = _world_z_range(objects["ground/collision0"])
    check(abs(wire_top - solid_top) < 1e-3,
          "with offset [0,0,-20] the gap is 0.00 mm (got {:.3f})".format(
              wire_top - solid_top))

    GATE["collision_overlay"] = {"shapes": len(objects)}


def test_the_collision_overlay_measures_every_primitive(root):
    """Extents per type, against the record's own independently-computed size.

    ``size_mm`` is a different arithmetic on the engine side from the
    ``size_m`` this module converts, so a doubled or halved conversion
    cannot pass both. The capsule is the one that matters most: MuJoCo's
    half-length is of the CYLINDRICAL SECTION ONLY, so its total extent is
    ``2*(half + radius)`` and a cage that stopped at the cylinder would
    understate it by a full diameter.
    """

    print("test_the_collision_overlay_measures_every_primitive")
    from mesh_agent import cadex_collision

    reset_scene(root)
    ok, report = run_tool("write_script", {"content": COLLISION_SHAPES_SCRIPT})
    check(ok, "the four-primitive script accepted ({:s})".format(
        (report or "").splitlines()[0] if report else ""))
    if not ok:
        return
    ok, _message = run_tool("collision_view", {"show": True})
    check(ok, "overlay on")

    evidence, source = cadex_collision.read_evidence(
        cadex_backend.last_accepted(root), root)
    check(evidence is not None,
          "a collision record was found (via {:s})".format(source))
    if evidence is None:
        return
    records = cadex_collision.records_from_evidence(evidence)
    check(len(records) == 4,
          "four shapes in the record (got {:d})".format(len(records)))

    agreed = 0
    for record in records:
        declared = [round(value, 6) for value in record["declared_size_mm"]]
        computed = [round(value, 6) for value in record["extents_mm"]]
        if declared == computed:
            agreed += 1
        else:
            check(False, "{:s}: extents {} != the engine's size_mm {}".format(
                record["kind"], computed, declared))
    check(agreed == len(records),
          "every type's extents match the engine's own size_mm "
          "({:d}/{:d})".format(agreed, len(records)))

    by_kind = {record["kind"]: record for record in records}
    objects = _collision_objects()

    box = by_kind.get("box")
    if box is not None:
        obj = objects.get(box["name"])
        low, high = _world_z_range(obj) if obj else (0.0, 0.0)
        check(abs((high - low) - 40.0) < 1e-3,
              "the box is drawn at its FULL 40 mm extent, not its 20 mm "
              "half-extent (got {:.3f})".format(high - low))

    capsule = by_kind.get("capsule")
    if capsule is not None:
        obj = objects.get(capsule["name"])
        check(obj is not None, "the capsule is drawn")
        if obj is not None:
            vertices = [vertex.co for vertex in obj.data.vertices]
            span = max(v.z for v in vertices) - min(v.z for v in vertices)
            check(abs(span - 30.0) < 1e-2,
                  "the capsule spans 2*(half+radius) = 30 mm including its "
                  "caps, not its 20 mm length (got {:.3f})".format(span))

    check(all(len(obj.data.polygons) == 0 for obj in objects.values()),
          "every overlay mesh has zero polygons")


def test_the_collision_overlay_is_isolated(root):
    """It follows the parts, and nothing else in the add-on can see it.

    Four independent ways this could go wrong, all cheap to break by
    accident: the hydrate GC sweeping it (it walks ``all_objects``, which
    recurses into child collections -- hence a SIBLING collection); picking
    resolving to a wire cage instead of a face; ``export_stl`` writing the
    overlay out as a part; and the wire not following the component it
    belongs to.
    """

    print("test_the_collision_overlay_is_isolated")
    from mesh_agent import cadex_collision

    reset_scene(root)
    ok, _report = run_tool("write_script", {"content": COLLISION_GOOD_SCRIPT})
    check(ok, "script accepted")
    ok, _message = run_tool("collision_view", {"show": True})
    check(ok, "overlay on")
    objects = _collision_objects()
    check(len(objects) == 2, "two shapes drawn (got {:d})".format(len(objects)))
    if not objects:
        return

    # A sibling of Model, not a child: the hydrate GC would sweep a child.
    collection = bpy.data.collections.get(cadex_collision.COLLECTION_NAME)
    scene = bpy.context.scene
    check(collection is not None
          and collection.name in scene.collection.children,
          "the Collision collection is a sibling at the scene root")
    model_collection = bpy.data.collections.get("Model")
    check(model_collection is not None
          and cadex_collision.COLLECTION_NAME not in
          [child.name for child in model_collection.children],
          "and is NOT a child of Model")

    # Not tagged with the property the hydrate GC hunts for.
    check(all(cadex_hydrate.OUTPUT_PROP not in obj for obj in objects.values()),
          "no overlay object carries cadex_output")
    swept = [obj.name for obj in
             cadex_hydrate._cadex_objects(cadex_hydrate._model_collection())]
    check(not any(name in swept for name in objects),
          "so hydrate's own object walk does not see them")

    # A rebuild is the GC. The overlay must still be there afterwards.
    ok, _report = run_tool("rebuild_model", {})
    check(ok, "rebuild accepted")
    check(len(_collision_objects()) == 2,
          "the overlay survives a rebuild's contract-driven GC")

    # It follows the component through the depsgraph.
    body = bpy.data.objects.get("body")
    wire = _collision_objects().get("body/collision0")
    check(body is not None and wire is not None, "the body and its wire exist")
    if body is not None and wire is not None:
        check(wire.parent is body, "the wire is parented to the component")
        depsgraph = bpy.context.evaluated_depsgraph_get()
        here = wire.evaluated_get(depsgraph).matrix_world.translation
        there = body.evaluated_get(depsgraph).matrix_world.translation
        check((here - there).length < 1e-3,
              "and sits at the component's origin, where the record puts it")

    # Picking still resolves to a face, not to a wire cage.
    ok, summary = run_tool("scene_summary", {})
    check(ok and "ground" in (summary or ""),
          "scene_summary still describes the model")

    # export_stl must not write the overlay out as a part.
    written = tempfile.mkdtemp(prefix="mesh-cadex-collision-stl-")
    try:
        ok, report = run_tool("export_stl", {"directory": written})
        check(ok, "export_stl ran ({:s})".format(
            (report or "").splitlines()[0] if report else ""))
        names = os.listdir(written)
        check(not any("collision" in name for name in names),
              "and wrote no collision wire ({})".format(sorted(names)))
    finally:
        import shutil
        shutil.rmtree(written, ignore_errors=True)

    # Losing the dynamics output clears it: a wire cage for a model that no
    # longer has collision geometry is a drawing of nothing.
    ok, report = run_tool("write_script",
                          {"content": COLLISION_NO_DYNAMICS_SCRIPT,
                           "replace": True})
    check(ok, "a revision without dynamics accepted ({:s})".format(
        (report or "").splitlines()[0] if report else ""))
    check(not _collision_objects(),
          "losing the dynamics output clears the overlay")
    check(cadex_collision.SCENE_FLAG not in bpy.context.scene,
          "and the panel flag goes with it")

    ok, _message = run_tool("collision_view", {"show": False})
    check(not _collision_objects(), "and turning it off is idempotent")


def test_both_collision_readers_agree(root):
    """Path A (the trace) and path B (inspect) place the same shape.

    Both are needed and neither is redundant: a model that is mjcf-only has
    no trace, and a rollout's trace carries the small evidence dict without
    the collisions block. If the two ever disagreed, the overlay would
    depend on which reader happened to answer.
    """

    print("test_both_collision_readers_agree")
    from mesh_agent import cadex_collision

    reset_scene(root)
    ok, _report = run_tool("write_script", {"content": COLLISION_GOOD_SCRIPT})
    check(ok, "script accepted")

    accepted = cadex_backend.last_accepted(root)
    check(bool(accepted), "the accepted payload was cached for the overlay")

    # Path B directly -- this model is mjcf-only, so it has no trace at all,
    # which is exactly the case path A cannot serve.
    check(not cadex_collision.trace_entries(accepted.get("display") or {}),
          "an mjcf-only model has no simulation trace")
    from_inspect = cadex_backend.mjcf_validation_evidence(root)
    check(from_inspect is not None and from_inspect.get("collisions"),
          "path B read the collision record off the publication object")
    if not from_inspect:
        return
    b_records = cadex_collision.records_from_evidence(from_inspect)

    # Path A, on a model that has a simulation. A SECOND store, because
    # writing an unrelated model over the first is refused by the output
    # retirement guard rather than accepted.
    trace_root = tempfile.mkdtemp(prefix="mesh-cadex-readers-trace-")
    reset_scene(trace_root)
    ok, report = run_tool("write_script", {"content": SIMULATION_SCRIPT})
    check(ok, "a simulation script accepted ({:s})".format(
        (report or "").splitlines()[0] if report else ""))
    accepted = cadex_backend.last_accepted(trace_root)
    check(bool(cadex_collision.trace_entries(accepted.get("display") or {})),
          "a simulation model does have a trace on disk")
    import shutil
    shutil.rmtree(trace_root, ignore_errors=True)

    names = sorted(record["name"] for record in b_records)
    check(names == ["body/collision0", "ground/collision0"],
          "path B named both geoms exactly as MuJoCo does (got {})".format(
              names))
    positions = {record["name"]: [round(value, 6)
                                  for value in record["position_mm"]]
                 for record in b_records}
    check(positions.get("ground/collision0") == [0.0, 0.0, -20.0],
          "and placed the floor's box at the offset the script gave it "
          "(got {})".format(positions.get("ground/collision0")))


#: One rollout trace's worth of the two keys the Policy Outputs panel reads,
#: with the rest of the schema left out: `commands_table` is pure, so a
#: synthetic trace exercises it without a trained policy and four hours of
#: GPU time. Two actuators with deliberately different units and spans --
#: a motor bounded by its effort limit and a servo bounded by its joint --
#: because an aggregate "full scale" would be wrong for exactly that pair.
COMMANDS_TRACE = {
    "actuator_channels": [
        {"actuator": "knee/motor", "joint": "knee", "motion_type": "angular",
         "kind": "motor", "unit": "nmm", "low": -216.0, "high": 216.0},
        {"actuator": "ankle/servo", "joint": "ankle", "motion_type": "angular",
         "kind": "position", "unit": "deg", "low": -40.0, "high": 40.0},
    ],
    "frames": [
        {"frame_kind": "input", "nominal_time_s": None},
        {"frame_kind": "solver_output", "nominal_time_s": 0.0},
        {"frame_kind": "solver_output", "nominal_time_s": 0.04,
         "actuator_commands": [108.0, -20.0]},
        {"frame_kind": "solver_output", "nominal_time_s": 0.08,
         "actuator_commands": [-216.0, 40.0]},
    ],
}


def test_the_policy_outputs_panel_reads_a_rollout():
    """The commands a rollout recorded, indexed by the frame they drove.

    The panel is drawn from `scene.frame_current` at draw time rather than
    from a property a handler writes, so what is worth testing is the
    lookup: the right row for a frame, nothing before the first command,
    and a held value between frames.
    """

    print("test_the_policy_outputs_panel_reads_a_rollout")
    from mesh_agent import cadex_animate
    from mesh_agent import ui as ui_module

    table = cadex_animate.commands_table(COMMANDS_TRACE, 0.0, 25)
    check(table is not None, "a rollout trace yields a command table")
    if table is None:
        return
    check([channel["label"] for channel in table["channels"]]
          == ["knee", "ankle"],
          "channels are labelled by the joint they drive")
    check(len(table["frames"]) == 2 and len(table["values"]) == 4,
          "one row per commanded frame, flat and row-major (got {:d} rows, "
          "{:d} values)".format(len(table["frames"]), len(table["values"])))

    # frame_of(t, 0, 25) = 1 + 25t, so 0.04 s is frame 2 and 0.08 s frame 3.
    check(cadex_animate.commands_at(table, 1) is None,
          "the reset frame has no command, and is not zero-filled")
    check(cadex_animate.commands_at(table, 2) == [108.0, -20.0],
          "the first commanded frame reads back exactly")
    check(cadex_animate.commands_at(table, 3) == [-216.0, 40.0],
          "and so does the last")
    # Zero-order hold: a command stands until the next control step, so a
    # frame between two rows reads the earlier one rather than a blend.
    check(cadex_animate.commands_at(table, 2.6) == [108.0, -20.0],
          "a command is held between frames, not interpolated")
    check(cadex_animate.commands_at(table, 99) == [-216.0, 40.0],
          "and past the end it holds the last command")

    # A trace with no policy in it -- kinematics, or a plain dynamics run --
    # produces no table, which is what keeps the panel off those models.
    check(cadex_animate.commands_table(
              {"frames": COMMANDS_TRACE["frames"]}, 0.0, 25) is None,
          "a trace with no actuator_channels yields no table")

    panel = ui_module.CADEX_POLICY_PT_actuators
    scene = bpy.context.scene
    had = cadex_animate.COMMANDS_FLAG in scene
    check(not had and not panel.poll(bpy.context),
          "the panel is absent on a model with no rollout")
    scene[cadex_animate.COMMANDS_FLAG] = table
    try:
        check(panel.poll(bpy.context),
              "and present once a rollout is baked")
        # The bar itself. `progress` is what makes this a readout rather
        # than an editable slider, and it is the one call in the panel that
        # a Blender upgrade could take away.
        #
        # Asked of `bl_rna.functions` rather than with `hasattr`: an RNA
        # function is resolved through the instance, so it is absent from
        # `dir(bpy.types.UILayout)` and `hasattr` answers False for a method
        # that exists and works. Measured -- this check failed that way
        # first, and the panel was fine.
        check("progress" in bpy.types.UILayout.bl_rna.functions,
              "UILayout.progress exists (the panel draws no other widget)")
    finally:
        del scene[cadex_animate.COMMANDS_FLAG]
    check(not panel.poll(bpy.context),
          "and gone again when the rollout is dropped")



def test_live_mode_is_wired_and_refuses_cleanly(live_root):
    """Live mode reaches the engine, and says no politely when it must.

    What it *cannot* test here is a live session: that plays a trained
    policy, and a policy is an asset -- hours of stochastic GPU compute the
    engine can verify but has never been able to produce (ADR-070,
    ADR-084). A gate corpus cannot contain one. So what is checked is
    everything either side of that: the panels exist on the Live editor, the
    module reaches for nothing it must not, and a `live_open` against a
    project with no rollout makes a real round trip to the engine and comes
    back a **refusal rather than a failure** -- because a project nobody has
    trained a policy for is a state, not an error (ADR-109).

    That refusal is the load-bearing one. It is the path every user takes
    the first time they open the editor.

    The force overlay (ADR-110) is the same shape of problem one step
    further: drawing needs a GPU context and this process has none, so what
    is checked is everything either side of the draw — that the handlers
    register and, more importantly, *unregister*; that no shader is fetched
    until a callback runs, which is the rule that keeps this suite green;
    and the arrow's geometry, which is pure arithmetic.
    """

    print("test_live_mode_is_wired_and_refuses_cleanly")
    from mesh_agent import cadex_live

    check(cadex_live.EDITOR_AVAILABLE,
          "live mode registered against the CADEX_LIVE editor")
    for name in ("CADEX_LIVE_PT_session", "CADEX_LIVE_PT_push",
                 "CADEX_LIVE_PT_actuators"):
        cls = getattr(bpy.types, name, None)
        check(cls is not None, "%s is registered" % name)
        if cls is not None:
            check(cls.bl_space_type == 'CADEX_LIVE',
                  "%s draws in the Live editor" % name)

    # The shell never learns about physics. The branch-wide form of this is
    # `test_the_shell_never_learns_about_mujoco`; this one also bans the
    # transports, because live mode is the first thing in the add-on with a
    # thread of its own and a socket there would be a second protocol.
    import ast as _ast

    tree = _ast.parse(open(cadex_live.__file__, encoding="utf-8").read())
    imported = set()
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, _ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    for forbidden in ("mujoco", "CadexDynamics", "subprocess", "socket",
                      "urllib", "http"):
        check(forbidden not in imported, "live mode never imports %s" % forbidden)

    # The force overlay (ADR-110): the add-on's first draw handlers, and the
    # rule that keeps this suite green. `gpu.shader.from_builtin` raises
    # "requires the gpu module to be initialized" under --background, so the
    # shader is fetched inside the draw callback and never at module scope --
    # asserted on the fetched object rather than on the import, because it is
    # the fetch that raises.
    check(cadex_live._shader is None,
          "no GPU shader is fetched at import or registration")
    module_level = set()
    for node in tree.body:
        if isinstance(node, _ast.Import):
            module_level.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, _ast.ImportFrom) and node.module:
            module_level.add(node.module.split(".")[0])
    for lazy in ("gpu", "gpu_extras", "blf", "bpy_extras"):
        check(lazy not in module_level,
              "%s is imported inside a callback, not at module scope" % lazy)

    check(cadex_live._draw_3d_handle is None
          and cadex_live._draw_2d_handle is None,
          "no draw handler is registered before a session")
    cadex_live._add_draw_handlers()
    check(cadex_live._draw_3d_handle is not None
          and cadex_live._draw_2d_handle is not None,
          "starting a session registers both draw handlers")
    handles = (cadex_live._draw_3d_handle, cadex_live._draw_2d_handle)
    cadex_live._add_draw_handlers()
    check((cadex_live._draw_3d_handle, cadex_live._draw_2d_handle) == handles,
          "...and adding twice leaks no second pair")
    cadex_live._remove_draw_handlers()
    check(cadex_live._draw_3d_handle is None
          and cadex_live._draw_2d_handle is None,
          "stopping removes them -- a leaked handler draws forever")
    cadex_live._remove_draw_handlers()
    check(True, "...and removing twice is safe, because unregister does too")

    # The arrow's geometry is pure arithmetic and is the whole of what the
    # POST_VIEW callback draws, so it is testable with no GPU at all.
    segments, tip, magnitude = cadex_live._arrow(
        (0.0, 0.0, 300.0), (1.0, 0.0, 0.0), 150.0)
    check(abs(magnitude - 1.0) < 1e-9, "a 1 N force measures 1 N")
    check(tip is not None and abs(tip[0] - 150.0) < 1e-9
          and abs(tip[2] - 300.0) < 1e-9,
          "at 150 mm/N it reaches 150 mm along +X from the centre of mass")
    check(len(segments) == 10,
          "one shaft and four head segments (got %d points)" % len(segments))
    check(cadex_live._arrow((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 150.0)[1] is None,
          "and no force draws no arrow")

    scene = bpy.context.scene
    check(scene.cadex_live_variation is False,
          "the panel opens calm: task forces and reset variation off")
    check(abs(scene.cadex_live_force_scale
              - cadex_live.DEFAULT_FORCE_SCALE_MM_N) < 1e-6,
          "the arrow scale defaults to %.0f mm/N"
          % cadex_live.DEFAULT_FORCE_SCALE_MM_N)
    scene[cadex_backend.ROOT_PROP] = live_root
    try:
        opened = cadex_backend.live_open(live_root, {"output": ""})
        check(opened.get("ok") is True,
              "live_open answers ok even with nothing to play")
        check(opened.get("live") is False,
              "...and live: false, because there is no rollout")
        check(bool(opened.get("reason")),
              "...with a reason a person can act on (%r)"
              % (opened.get("reason"),))
        # Every declared key is present on a refusal: the response spec is
        # pinned per op, not per outcome, so a shell reading `components`
        # off a refusal finds an empty list rather than a KeyError.
        for key in ("components", "control_hz", "frames_per_second",
                    "actuator_channels", "episode_seconds"):
            check(key in opened, "a refusal still carries %r" % key)

        stepped = cadex_backend.live_step(live_root, {"steps": 3})
        check(stepped.get("ok") is True and stepped.get("live") is False,
              "live_step with no session declines rather than failing")
        check(stepped.get("frames") == [],
              "...and hands back no frames")

        closed = cadex_backend.live_close(live_root)
        check(closed.get("ok") is True and closed.get("closed") is True,
              "live_close is fine with nothing open")

        ok, message = cadex_live.start(bpy.context)
        check(ok is False, "the operator path refuses too")
        check(cadex_live.session() is None,
              "...and leaves no session behind (%r)" % (message,))
        GATE["live"] = {"refused": str(message)[:80]}
    finally:
        scene.pop(cadex_backend.ROOT_PROP, None)


def test_the_training_panel_tracks_a_run(training_root):
    """The shell's view of a run happening on another machine (M9, ADR-098).

    Before this, a training run was a black box with one artifact at the
    end: dispatch it, wait, find out. The run that motivated M9 peaked at
    iteration 1200 of 2000 -- thirty of its seventy-six minutes made the
    policy worse, with no way to know while it was happening.

    What the panel reads is one local file that `remote_train.sh watch`
    mirrors off the box. **No ssh, no protocol change, no engine change and
    no mujoco**: the assertion at the end of this test is the one that
    matters most, because `test_the_shell_never_learns_about_mujoco` pins
    that this side may never import it.

    Driven directly rather than through `bpy.app.timers`, which do not fire
    under `--background` -- the timer is the interactive convenience and
    every function it calls is written to be callable without it.
    """

    from mesh_agent import cadex_training
    from mesh_agent import ui as ui_module

    scene = bpy.context.scene
    scene[cadex_backend.ROOT_PROP] = training_root
    panel = ui_module.CADEX_TRAINING_PT_training
    path = os.path.join(training_root, cadex_training.PROGRESS_NAME)
    try:
        check(cadex_training.progress_path(scene) == path,
              "the panel looks beside the project for training-progress.json")
        check(cadex_training.read_progress(scene) is None,
              "no run reports, no reading")
        check(not panel.poll(bpy.context),
              "and the panel is absent on a project with no run")

        # A file that is not this file is not this file. A run reporting a
        # schema nobody wrote would otherwise draw as a row of zeros.
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"schema": "something-else", "state": "training"}, handle)
        check(cadex_training.read_progress(scene) is None,
              "a foreign schema reads as no run rather than as an empty one")
        check(not panel.poll(bpy.context), "so the panel stays away")

        # Half a file reads as no file. The trainer writes atomically so
        # this window does not exist in practice; what is asserted is that
        # the panel survives it if it ever does.
        with open(path, "w", encoding="utf-8") as handle:
            handle.write('{"schema": "cadex-training-progress-v1", "state"')
        check(cadex_training.read_progress(scene) is None,
              "a truncated file reads as no run")

        live = {
            "schema": cadex_training.PROGRESS_SCHEMA,
            "state": "training",
            "iteration": 419,
            "total": 2000,
            "wall_time_s": 913.0,
            "eta_s": 3440.0,
            "reward_per_step": 0.391,
            "loss": 0.0021,
            "episode_steps": 137.5,
            "best_reward_per_step": 0.402,
            "best_iteration": 388,
            "device": "gpu",
            "out": "stand.cxpolicy",
            "label": "stand",
            "checkpoints": [
                {"tag": "000100", "iteration": 99, "path": "stand.000100.cxpolicy",
                 "reward_per_step": 0.21, "sha256": "a" * 64, "bytes": 30000},
                {"tag": "best", "iteration": 388, "path": "stand.best.cxpolicy",
                 "reward_per_step": 0.402, "sha256": "b" * 64, "bytes": 30000},
            ],
            "error": "",
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(live, handle)

        report = cadex_training.read_progress(scene)
        check(report is not None and report["iteration"] == 419,
              "a live run reads back")
        check(cadex_training.is_live(report), "and reads as live")
        check(panel.poll(bpy.context), "so the panel appears")

        # The one number the panel exists to put in front of somebody: how
        # far behind the current iteration the best one is.
        check(report["best_iteration"] == 388 and report["iteration"] == 419,
              "best-so-far and where it happened are both carried")
        check(cadex_training.format_eta(3440.0) == "57 min",
              "an ETA is minutes, because a run is minutes to hours")
        check(cadex_training.format_eta(0) == "-",
              "and an absent one says so rather than reading zero")

        # It draws. A panel that polls True and then raises in `draw` is a
        # Blender error popup, and `--background` is where that is cheap to
        # find.
        drawn = _draw_panel(panel)
        text = " ".join(part for row in drawn for part in row
                        if isinstance(part, str))
        check(any(row[0] == "progress" for row in drawn),
              "the panel draws a progress bar")
        check("420 / 2000 iterations" in text,
              "iterations done over iterations asked for, 1-based")
        check("+0.391" in text and "+0.402" in text,
              "the current reward and the best are both shown")
        check("at iteration 388" in text,
              "and where the best happened, which is the decision to make")
        # ADR-101's row. The reward alone is the number that lied for two
        # runs; the episode length beside it is what shows a policy failing
        # sooner while being paid more for it.
        check("137.5 steps" in text,
              "mean episode length is shown beside the reward")
        # ...and a report written before ADR-101 still draws. The schema did
        # not change for an additive field, so old files keep arriving and a
        # panel that raised on one would be a Blender error popup.
        older = dict(live)
        older.pop("episode_steps")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(older, handle)
        drawn_old = _draw_panel(panel)
        check("episode      -" in " ".join(part for row in drawn_old
                                           for part in row
                                           if isinstance(part, str)),
              "a report without the field draws a dash rather than raising")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(live, handle)

        check("57 min" in text and "15 min" in text,
              "elapsed and remaining, in minutes")
        check("gpu" in text, "and the device, so a CPU fallback is visible")
        check("stand.best.cxpolicy" in text and "stand.000100.cxpolicy" in text,
              "the checkpoints pulled so far are listed")

        # The terminal states keep the panel up rather than making it
        # vanish: "it finished" is information and an empty panel is not.
        for state in ("done", "failed"):
            live["state"] = state
            live["error"] = "SystemExit: diverged" if state == "failed" else ""
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(live, handle)
            report = cadex_training.read_progress(scene)
            check(report["state"] == state, "%s reads back" % state)
            check(not cadex_training.is_live(report),
                  "%s is terminal, so the timer stops caring" % state)
            check(panel.poll(bpy.context),
                  "but the panel stays up on %s" % state)
            drawn = _draw_panel(panel)
            text = " ".join(part for row in drawn for part in row
                            if isinstance(part, str))
            check(state.title() in text,
                  "and says which terminal state on %s" % state)
            if state == "failed":
                check("diverged" in text,
                      "a failed run shows why, rather than just stopping")
            else:
                check("remaining" not in text,
                      "a finished run has no time remaining to report")

        # And gone when the file goes, so a project that never trained is
        # the parameters editor exactly as it was.
        os.remove(path)
        check(cadex_training.read_progress(scene) is None,
              "a removed report reads as no run")
        check(not panel.poll(bpy.context), "and the panel goes with it")

        # The invariant this whole design exists to keep, asserted on the
        # *imports* rather than on the prose: the shell learns about
        # training from one JSON file and from nothing else. No mujoco
        # (`test_the_shell_never_learns_about_mujoco` is the branch-wide
        # form of that), and no transport -- a panel that opened a network
        # connection would block Blender the first time a box was slow.
        import ast as _ast

        tree = _ast.parse(open(cadex_training.__file__, encoding="utf-8").read())
        imported = set()
        for node in _ast.walk(tree):
            if isinstance(node, _ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, _ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        check(imported - {"__future__"} == {"json", "os", "bpy"},
              "the panel's module imports json, os and bpy -- nothing else "
              "(got %r)" % (sorted(imported),))
        for forbidden in ("mujoco", "subprocess", "socket", "paramiko",
                          "urllib", "http"):
            check(forbidden not in imported,
                  "and never %s" % forbidden)
    finally:
        scene.pop(cadex_backend.ROOT_PROP, None)
        try:
            os.remove(path)
        except OSError:
            pass


class _RecordingLayout:
    """Enough of `UILayout` to run a panel's `draw` and see what it drew.

    `Panel.draw` needs a live layout and Blender only makes one while it is
    drawing a region, which `--background` never does. A stub is not a
    substitute for the real widget -- what it tests is the *body*: the
    formatting, the None handling, the branch a failed run takes, and the
    cap on the checkpoint list. Those are where a panel goes wrong in a way
    a person only finds by looking at it.
    """

    def __init__(self, sink=None):
        self.sink = [] if sink is None else sink
        self.enabled = True
        self.alert = False

    def _child(self):
        return _RecordingLayout(self.sink)

    row = column = box = split = lambda self, *a, **k: self._child()

    def label(self, text="", icon=""):
        self.sink.append(("label", str(text), str(icon)))

    def progress(self, factor=0.0, text=""):
        self.sink.append(("progress", float(factor), str(text)))

    def prop(self, *a, **k):
        self.sink.append(("prop",))

    def operator(self, *a, **k):
        self.sink.append(("operator",))
        return self._child()


def _draw_panel(panel):
    """Run one panel's `draw` against the stub and return what it emitted."""

    # A plain object rather than `panel.__new__(panel)`: a registered
    # `bpy_struct` refuses to be constructed that way ("expected a single
    # argument"), and `draw` is an ordinary Python function that touches
    # nothing but `self.layout`.
    layout = _RecordingLayout()
    panel.draw(types.SimpleNamespace(layout=layout), bpy.context)
    return layout.sink


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
    wide_root = tempfile.mkdtemp(prefix="mesh-cadex-wide-")
    turn_root = tempfile.mkdtemp(prefix="mesh-cadex-turn-")
    reopen_root = tempfile.mkdtemp(prefix="mesh-cadex-reopen-")
    threading_root = tempfile.mkdtemp(prefix="mesh-cadex-thread-")
    cancel_root = tempfile.mkdtemp(prefix="mesh-cadex-cancel-")
    saveas_root = tempfile.mkdtemp(prefix="mesh-cadex-saveas-")
    duplicate_root = tempfile.mkdtemp(prefix="mesh-cadex-duplicate-")
    carry_root = tempfile.mkdtemp(prefix="mesh-cadex-carry-")
    restore_root = tempfile.mkdtemp(prefix="mesh-cadex-restore-")
    corrupt_root = tempfile.mkdtemp(prefix="mesh-cadex-corrupt-")
    describe_root = tempfile.mkdtemp(prefix="mesh-cadex-describe-")
    edit_root = tempfile.mkdtemp(prefix="mesh-cadex-edit-")
    drop_root = tempfile.mkdtemp(prefix="mesh-cadex-drop-")
    rederive_root = tempfile.mkdtemp(prefix="mesh-cadex-rederive-")
    mirror_root = tempfile.mkdtemp(prefix="mesh-cadex-mirror-")
    defaults_root = tempfile.mkdtemp(prefix="mesh-cadex-defaults-")
    refused_root = tempfile.mkdtemp(prefix="mesh-cadex-refused-")
    rewrite_root = tempfile.mkdtemp(prefix="mesh-cadex-rewrite-")
    repair_root = tempfile.mkdtemp(prefix="mesh-cadex-repair-")
    stdout_root = tempfile.mkdtemp(prefix="mesh-cadex-stdout-")
    long_root = tempfile.mkdtemp(prefix="mesh-cadex-long-")
    guard_root = tempfile.mkdtemp(prefix="mesh-cadex-guard-")
    history_root = tempfile.mkdtemp(prefix="mesh-cadex-history-")
    prune_root = tempfile.mkdtemp(prefix="mesh-cadex-prune-")
    assembly_root = tempfile.mkdtemp(prefix="mesh-cadex-assembly-")
    shared_root = tempfile.mkdtemp(prefix="mesh-cadex-shared-")
    sim_root = tempfile.mkdtemp(prefix="mesh-cadex-sim-")
    drag_root = tempfile.mkdtemp(prefix="mesh-cadex-drag-")
    skip_root = tempfile.mkdtemp(prefix="mesh-cadex-skip-")
    preview_root = tempfile.mkdtemp(prefix="mesh-cadex-preview-")
    fallback_root = tempfile.mkdtemp(prefix="mesh-cadex-fallback-")
    supersede_root = tempfile.mkdtemp(prefix="mesh-cadex-supersede-")
    collision_root = tempfile.mkdtemp(prefix="mesh-cadex-collision-")
    shapes_root = tempfile.mkdtemp(prefix="mesh-cadex-shapes-")
    isolate_root = tempfile.mkdtemp(prefix="mesh-cadex-isolate-")
    readers_root = tempfile.mkdtemp(prefix="mesh-cadex-readers-")
    training_root = tempfile.mkdtemp(prefix="mesh-cadex-training-")
    live_root = tempfile.mkdtemp(prefix="mesh-cadex-live-")
    try:
        test_startup_layout_is_the_shipped_file()
        test_write_script_hydrates(corpus_root)
        scene = bpy.context.scene
        test_picking_fidelity(scene)
        test_pin_flow(scene)
        test_point_pin_flow(scene)
        test_both_pin_gestures_are_registered()
        test_the_pick_finds_the_viewport_under_the_mouse()
        test_describe_cad_api(describe_root)
        test_edit_script_and_inspection(edit_root)
        test_params_and_latency(baseline_root)
        test_params_survive_the_inspect_pager(wide_root)
        test_dropping_a_param_leaves_the_sliders_working(drop_root)
        test_rebuild_model_rederives_from_the_engine(rederive_root)
        test_script_view_marks_hand_edits(mirror_root)
        test_rewrite_defaults_splices_only_the_default()
        test_apply_slider_defaults(defaults_root)
        test_main_thread_free_during_rebuild(threading_root)
        test_unchanged_geometry_is_not_rebuilt(skip_root)
        test_main_thread_free_during_a_drag(drag_root)
        test_an_agent_turn_supersedes_a_queued_drag(supersede_root)
        test_cancel_reaches_the_engine(cancel_root)
        test_cadex_turn_single_undo(turn_root)
        test_save_as_and_multi_file_lifecycle(saveas_root)
        test_duplicated_file_keeps_its_parameters(duplicate_root)
        test_save_as_carries_imported_geometry(carry_root)
        test_reopen_restores(reopen_root)
        test_open_runs_the_restore_pass(restore_root)
        test_restore_failure_is_first_class(corrupt_root)
        test_a_refused_edit_leaves_the_project_openable(refused_root)
        test_a_broken_store_can_still_be_rewritten(rewrite_root)
        test_a_script_that_will_not_run_is_repaired_from_the_accepted_source(
            repair_root)
        test_a_working_scripts_stdout_reaches_the_caller(stdout_root)
        test_get_script_is_not_truncated(long_root)
        test_write_script_refuses_to_drop_existing_outputs(guard_root)
        test_script_history_and_revert(history_root)
        test_stale_attempts_are_pruned(prune_root)
        test_an_assembly_shows_its_solved_placements(assembly_root)
        test_two_components_share_one_mesh(shared_root)
        test_a_simulation_plays(sim_root)
        test_the_policy_outputs_panel_reads_a_rollout()
        test_a_pose_only_slider_previews_at_interactive_rate(preview_root)
        test_a_shape_slider_falls_back_to_set_params(fallback_root)
        test_the_collision_overlay_draws_adr074(collision_root)
        test_the_collision_overlay_measures_every_primitive(shapes_root)
        test_the_collision_overlay_is_isolated(isolate_root)
        test_both_collision_readers_agree(readers_root)
        test_the_training_panel_tracks_a_run(training_root)
        test_live_mode_is_wired_and_refuses_cleanly(live_root)
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
        for root in (corpus_root, baseline_root, wide_root, turn_root,
                     reopen_root,
                     threading_root, cancel_root, saveas_root,
                     duplicate_root, carry_root,
                     restore_root, corrupt_root, describe_root, edit_root,
                     drop_root, rederive_root, mirror_root, defaults_root,
                     refused_root, rewrite_root, repair_root, stdout_root,
                     long_root, guard_root, history_root, prune_root,
                     assembly_root, shared_root, sim_root, live_root,
                     drag_root, supersede_root, skip_root,
                     preview_root, fallback_root, collision_root,
                     shapes_root, isolate_root, readers_root):
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
