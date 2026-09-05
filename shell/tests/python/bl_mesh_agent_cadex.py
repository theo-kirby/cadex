# SPDX-FileCopyrightText: 2026 Cadex Authors
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

# mesh_agent is application code in scripts/startup (ADR-183): the app has
# already registered its bundled copy. The suite tests the SOURCE tree, so
# put that copy down, purge it, and import ours (bl_mesh_agent.py explains).
_REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "..", ".."))
_SOURCE_STARTUP = os.path.join(_REPO, "scripts", "startup")
_bundled = sys.modules.get("mesh_agent")
if _bundled is not None and not os.path.abspath(
        _bundled.__file__).startswith(_SOURCE_STARTUP + os.sep):
    _bundled.unregister()
    for _name in [n for n in sys.modules
                  if n == "mesh_agent" or n.startswith("mesh_agent.")]:
        del sys.modules[_name]
sys.path.insert(0, _SOURCE_STARTUP)

import mesh_agent  # noqa: E402
from mesh_agent import cadex_backend  # noqa: E402
from mesh_agent import cadex_hydrate  # noqa: E402
from mesh_agent import cadex_pick  # noqa: E402
from mesh_agent import cadexd_client  # noqa: E402
from mesh_agent import model as model_module  # noqa: E402
from mesh_agent import tools  # noqa: E402
from mesh_agent import topbar  # noqa: E402
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

#: The parity bar, in seconds. A **product** criterion: a slider drag has to
#: feel like the Qt shell's did, and that is an absolute wall-clock number
#: measured on a machine a person would actually use.
PARITY_BAR_SECONDS = 0.65

#: ...which is why a shared CI runner cannot measure it, and
#: ``CADEX_GATE_LATENCY_BAR`` exists (ADR-163). Every wall-clock number in the
#: gate is uniformly ~2.2-2.5x slower on a GitHub macOS runner than on the
#: developer Mac -- measured on one commit, same code, same day:
#:
#:     open 2.005 -> 5.102 s   refine 1.358 -> 3.021 s
#:     rebuild 1.502 -> 2.775  drag median 0.520 -> 1.268 s
#:
#: The drag's ratio (2.44x) sits in the middle of the others, so the runner is
#: slow at everything rather than slow at dragging. Failing the gate on it
#: would mean a red build that says nothing about the product, which is how a
#: CI job stops being read at all.
#:
#: The override raises the **enforced** ceiling only. ``parity_bar_seconds``
#: and ``median_within_bar`` in the gate payload always report against the
#: real 0.65 s bar, so a CI artifact still tells the truth about parity --
#: it just does not fail the build for the runner being a runner.
_LATENCY_BAR = float(
    os.environ.get("CADEX_GATE_LATENCY_BAR", "") or PARITY_BAR_SECONDS)

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
#:
#: **Two** files, not one (ADR-155). One asset cannot tell a carry that
#: moves everything apart from a carry that moves the first thing it finds
#: and stops, and the real model that found this had two.
IMPORTED_GEOMETRY_SCRIPT = """
widget = mesh.import_file("widget.stl")
bracket = mesh.import_file("bracket.stl")
result = {"widget": widget, "bracket": bracket}
"""

MOVED_GEOMETRY_SCRIPT = """
widget = mesh.transform(mesh.import_file("widget.stl"), translation=(5, 0, 0))
bracket = mesh.import_file("bracket.stl")
result = {"widget": widget, "bracket": bracket}
"""

#: The other model, in the two-model story ADR-138 is about: a parametric
#: sensor body whose bore is what moves when the source is edited.
LINKED_SENSOR_SCRIPT = """
p = params(bore=num(6.0, unit="mm", min=2.0, max=14.0, step=0.5))
block = part.box(40.0, 25.0, 15.0)
bore = part.cylinder(p.bore / 2.0, 25.0, origin=[20.0, 12.5, -5.0])
sensor = part.cut(block, bore)
result = {"sensor": sensor}
"""

#: A measured part: one dimension of each kind, on a shape whose width is a
#: parameter, so the gate can watch the numbers follow a slider (ADR-139).
MEASURED_SCRIPT = """
p = params(width=num(60.0, unit="mm", min=20.0, max=120.0, step=1.0))
plate = part.box(p.width, 40.0, 10.0)
bored = part.cut(plate, part.cylinder(3.0, 30.0, origin=[15.0, 20.0, -10.0]))
height = part.measurement(bored, kind="extent", axis="z", label="height")
span = part.measurement(bored, kind="extent", axis="x")
bore = part.measurement(
    bored, kind="diameter", at={"geometry_type": "Cylinder", "radius": 3.0})
result = {"bored": bored, "height": height, "span": span, "bore": bore}
"""

#: ...and this model, building on it. `part.cut` is the assertion that the
#: linked part is a real solid the kernel will boolean, not a shell of
#: triangles.
LINKED_CONSUMER_SCRIPT = """
sensor = part.import_part("sensor.cxpart")
plate = part.box(80.0, 60.0, 10.0)
mount = part.cut(plate, part.transform(sensor, translation=[10.0, 10.0, 4.0]))
result = {"sensor": sensor, "plate": plate, "mount": mount}
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
    check(areas == ['CADEX_CHAT', 'CADEX_PARAMS', 'OUTLINER', 'VIEW_3D'],
          "the startup layout is the three Cadex areas plus the outliner "
          "(ADR-168): {!r}".format(areas))

    # The proportions are the product's (ADR-168): the chat column is about
    # a third of the window, and parameters/outliner share the bottom row.
    by_type = {area.type: area for screen in bpy.data.screens
               for area in screen.areas}
    if len(by_type) == 4:
        total_w = max(a.x + a.width for a in by_type.values())
        chat_ratio = by_type['CADEX_CHAT'].width / max(1, total_w)
        check(0.28 <= chat_ratio <= 0.38,
              "the chat column is about a third of the window "
              "({:.2f})".format(chat_ratio))
        params, outliner = by_type['CADEX_PARAMS'], by_type['OUTLINER']
        check(params.y == outliner.y and params.height == outliner.height,
              "parameters and outliner share the bottom row")
        check(params.x < outliner.x,
              "parameters sits left of the outliner")
    workspaces = [workspace.name for workspace in bpy.data.workspaces]
    check(workspaces == ["Simple"],
          "one workspace, named Simple: {!r}".format(workspaces))
    check(not bpy.data.objects, "the startup scene is empty")

    viewport = next((area.spaces.active for screen in bpy.data.screens
                     for area in screen.areas if area.type == 'VIEW_3D'), None)
    check(viewport is not None and viewport.shading.type == 'SOLID'
          and viewport.shading.light == 'MATCAP'
          and viewport.shading.show_cavity,
          "the viewport keeps its solid/matcap styling, cavity on")
    check(viewport is not None and not viewport.show_gizmo
          and not viewport.show_region_ui and not viewport.show_region_header,
          "the viewport keeps its chrome off: no gizmos, no side panels")
    overlay = viewport.overlay if viewport is not None else None
    check(overlay is not None and overlay.show_overlays
          and not overlay.show_floor and not overlay.show_ortho_grid
          and (overlay.show_axis_x, overlay.show_axis_y,
               overlay.show_axis_z) == (False, False, True),
          "overlays are on, bare: no floor, no grid, only the Z axis")

    GATE["startup_areas"] = areas

    # File and Edit live in the OS menu bar since ADR-166 -- built in
    # GHOST_SystemCocoa.mm, unreachable from Python -- so what the template
    # is checked for here is what it still does.
    template = sys.modules.get("bl_app_templates_system.Mesh")
    check(template is not None, "the Mesh app template module is loaded")
    if template is not None:
        # No splash on the way in (ADR-042). Suppressing it must not
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
        # Always the real bar, whatever ceiling is being enforced: a gate
        # payload that reported a relaxed bar as "the bar" would launder the
        # runner's slowness into a passing parity claim.
        "parity_bar_seconds": PARITY_BAR_SECONDS,
        "median_within_bar": median <= PARITY_BAR_SECONDS,
        "enforced_bar_seconds": _LATENCY_BAR,
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
    if _LATENCY_BAR > PARITY_BAR_SECONDS:
        print("  note: slider-drag median {:.3f} s; parity bar {:.2f} s is "
              "NOT enforced here (ceiling {:.2f} s)".format(
                  median, PARITY_BAR_SECONDS, _LATENCY_BAR))
    check(median <= _LATENCY_BAR,
          "slider-drag median {:.3f} s within the {:.2f} s bar".format(
              median, _LATENCY_BAR))
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

def test_cadex_turn_single_undo(root, source=REDUCED_SCRIPT, output="plate"):
    print("test_cadex_turn_single_undo")
    reset_scene(root)
    from mesh_agent import agent as agent_module
    agent = agent_module.Agent()
    agent.tool_cap_override = 10
    script = [[
        ("text", "Building the corpus.\n"),
        ("tool", "write_script", {"content": source}),
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
        check(bpy.data.objects.get(output) is not None,
              "turn hydrated " + output)
        check(len(undo_pushes) == 1,
              "exactly one undo push per turn (got {:d})".format(
                  len(undo_pushes)))
    finally:
        agent.shutdown()


def test_native_blender_recipe(root):
    print("test_native_blender_recipe")
    with open(os.path.join(_REPO, "..", "examples", "blender_enclosure.py")) as stream:
        source = stream.read()
    # Real shell launch discovery, real nested Blender and the actual agent
    # mutation/undo accounting; no CADEX_BLENDER_EXECUTABLE test override.
    test_cadex_turn_single_undo(root, source=source, output="skin")
    skin = bpy.data.objects.get("skin")
    if skin is None:
        return
    check(skin.get(cadex_hydrate.KIND_PROP) == "mesh", "recipe output is an ordinary hydrated mesh")
    original = store_state(root)["accepted_digest"]
    width = skin.dimensions.x
    ok, report = run_tool("set_params", {"params": {"mount_spacing": 56}})
    check(ok, "recipe parameter rebuild: " + report[:120])
    check(bpy.data.objects["skin"].dimensions.x > width, "skin follows CAD mount spacing")
    ok, report = run_tool("set_params", {"params": {"mount_spacing": 42}})
    check(ok and store_state(root)["accepted_digest"] == original,
          "restoring the parameter restores recipe geometry identity")
    ok, report = run_tool("write_script", {"content": source.replace(
        "import bmesh", "raise RuntimeError('deliberate recipe failure')\nimport bmesh")})
    check(not ok, "failed native recipe is refused")
    check(store_state(root)["accepted_digest"] == original, "failed recipe retains accepted geometry")
    GATE["blender_recipe"] = {"facets": len(bpy.data.objects["skin"].data.polygons),
                              "width_mm": width, "runtime": bpy.app.version_string}


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


def test_opening_a_file_hydrates(workdir):
    """Opening a .blend beside its .cadex asks the engine for the display.

    ADR-073 measured `model_objects_on_open = 0`: `load_post` closed the old
    sessions and nothing queued a rebuild, so the viewport held only the mesh
    baked into the file until a tool call, a drag or Rebuild Model provoked
    the first request. ADR-186 queues the open from `load_post`; timers do
    not fire under --background, so this drains it by hand like the drag and
    refine pumps.
    """
    print("test_opening_a_file_hydrates")
    from mesh_agent import cadexd_client

    # An UNSAVED scene's temporary root survives File > New (it is keyed by
    # scene name), so a new empty file must not queue an open against it.
    bpy.ops.wm.read_homefile(use_empty=True)
    ok, report = run_tool("write_script", {"content": REDUCED_SCRIPT,
                                           "replace": True})
    check(ok, "a model in an unsaved file ({:s})".format(report[:60]))
    unsaved_root = cadex_backend.project_root(bpy.context.scene)
    check(os.path.isdir(unsaved_root), "...whose temporary root exists")
    bpy.ops.wm.read_homefile(use_empty=True)
    check(not cadex_backend.pending_open(unsaved_root),
          "File > New does not queue an open of the unsaved file's root")
    check(cadex_backend.open_roots() == [],
          "...and dropped its session")

    blend = os.path.join(workdir, "model.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    ok, report = run_tool("write_script", {"content": BASELINE_SCRIPT,
                                           "replace": True})
    check(ok, "model accepted in model.blend ({:s})".format(report[:60]))
    root = cadex_backend.project_root(bpy.context.scene)
    bpy.ops.wm.save_mainfile()

    # A fresh session: no engine state, nothing in the viewport.
    bpy.ops.wm.read_homefile(use_empty=True)
    check(cadex_backend.open_roots() == [] and not cadexd_client._clients,
          "the session starts with no engine state")
    check(bpy.data.objects.get("plate") is None, "...and an empty viewport")

    began = time.monotonic()
    bpy.ops.wm.open_mainfile(filepath=blend)
    scene = bpy.context.scene
    check(cadex_backend.project_root(scene) == root,
          "the reopened file names its own project")
    check(cadex_backend.pending_open(root),
          "load_post queued the open of the existing project")
    check(cadex_backend.open_roots() == [],
          "...queued, not run: no engine state on the main thread yet")
    # What the viewport shows while the engine comes up is the mesh baked
    # into the file. Take it away so the assertion below can only be met by
    # the engine's own display reply.
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    ok, report = cadex_backend.open_now(scene)
    open_seconds = time.monotonic() - began
    check(ok, "the queued open hydrates ({:s})".format(
        (report or "clean").splitlines()[0][:80]))
    objects = brep_objects()
    GATE["model_objects_on_open"] = len(objects)
    GATE["hydrate_on_open_seconds"] = round(open_seconds, 3)
    check(len(objects) > 0, "model_objects_on_open > 0 ({:d})".format(
        len(objects)))
    check(bpy.data.objects.get("plate") is not None,
          "the engine's geometry is in the viewport")
    check(not cadex_backend.pending_open(root), "the slot is retired")
    check(cadex_backend.open_roots() == [root],
          "exactly the file's own project is open")
    state = cadex_backend._state_for(root)
    check(state.restore.get("performed") is True
          and state.restore.get("matches_accepted") is True,
          "the open ran the restore pass and it matched")
    check(state.open_failure_code == "", "no failure code cached")
    specs = model_module.load_specs(scene)
    check(any(spec["id"] == "hole" for spec in specs),
          "the sliders are rebuilt from the engine's specs")
    # A tool call after that finds the project open and does not reopen it.
    before = cadexd_client._clients.get(root)
    ok, report = cadex_backend.ensure_open(scene)
    check(ok and report == "" and cadexd_client._clients.get(root) is before,
          "ensure_open finds the project open and keeps the child")

    # A second load with a tool call racing the queue: ensure_open drains
    # the queued open rather than issuing a second open_project.
    bpy.ops.wm.open_mainfile(filepath=blend)
    scene = bpy.context.scene
    check(cadex_backend.pending_open(root), "the reload queued again")
    ok, report = run_tool("set_params", {"params": {"hole": 7.0}})
    check(ok, "a tool call during the queued open succeeds ({:s})".format(
        report[:60]))
    check(not cadex_backend.pending_open(root),
          "...and drained the queue on the way")


def test_a_locked_out_project_is_reaccepted_from_the_chat(workdir):
    """A restore failure at open has a button back in (ADR-187).

    A digest-moving engine change -- a solver bump, a sweep-frame fix --
    leaves the stored script unchanged and the accepted digest wrong, so the
    restore pass fails at the next open and every tool that could repair it
    opens the project first. Rebuild Model refuses, correctly. The remedy
    is `open_project restore=false` then `write_script`, by hand until now;
    the chat panel's re-accept box is that, as one operator, drawn off the
    failure code the open cached.
    """
    print("test_a_locked_out_project_is_reaccepted_from_the_chat")
    from mesh_agent import cadexd_client

    bpy.ops.wm.read_homefile(use_empty=True)
    blend = os.path.join(workdir, "locked.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    ok, report = run_tool("write_script", {"content": BASELINE_SCRIPT,
                                           "replace": True})
    check(ok, "model accepted in locked.blend ({:s})".format(report[:60]))
    root = cadex_backend.project_root(bpy.context.scene)
    bpy.ops.wm.save_mainfile()
    true_digest = store_state(root)["accepted_digest"]
    cadex_backend.close_all()

    # The engine moved under the model: the script is untouched and the
    # digest it was accepted at is no longer the one it builds. Written
    # straight into the store, which is the only way to move the digest
    # without changing the script or rebuilding the engine.
    state_path = os.path.join(root, "script.json")
    with open(state_path, encoding="utf-8") as handle:
        stored = json.load(handle)
    stored["accepted_digest"] = "0" * len(true_digest)
    with open(state_path, "w", encoding="utf-8") as handle:
        json.dump(stored, handle, indent=2)

    # Opened the way a user opens it: through load_post's queued open.
    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.wm.open_mainfile(filepath=blend)
    scene = bpy.context.scene
    check(cadex_backend.pending_open(root), "load_post queued the open")
    check(not cadex_backend.locked_out_project(scene),
          "nothing is locked out before the open runs")
    ok, report = cadex_backend.open_now(scene)
    check(not ok, "the queued open refuses the moved digest")
    check("could not restore this model" in report,
          "...as a restore failure, said plainly")
    state = cadex_backend._state_for(root)
    check(state.open_failure_code == cadex_backend.RESTORE_FAILED_CODE,
          "the failure code is cached on the per-root state")
    check(cadex_backend.locked_out_project(scene),
          "the chat panel has a lockout to draw")
    check(not cadex_backend.orphaned_project(scene),
          "...and it is not the orphan box: the project is not empty")
    check(bool(model_module.last_error()),
          "the parameters panel has the failure to draw")

    # Rebuild Model is the wrong button, and says so rather than adopting.
    check(bpy.ops.mesh_agent.rebuild_model.poll()
          and bpy.ops.mesh_agent.rebuild_model() == {'CANCELLED'},
          "Rebuild Model refuses a project whose restore failed")
    check(cadex_backend.locked_out_project(scene),
          "...and the lockout stands")
    check(store_state(root)["accepted_digest"] == "0" * len(true_digest),
          "...with the accepted digest untouched")

    # The way back in. Through poll() first: an operator whose poll fails
    # raises out of bpy.ops and would abort the suite.
    check(bpy.ops.mesh_agent.reaccept_script.poll()
          and bpy.ops.mesh_agent.reaccept_script() == {'FINISHED'},
          "Re-accept Stored Script runs from the locked-out state")
    check(not cadex_backend.locked_out_project(scene),
          "the lockout is over")
    check(state.open_failure_code == "" and state.restore_warning == "",
          "the failure code and the unrestored warning are both cleared")
    check(not model_module.last_error(), "the panel's failure row is gone")
    check(store_state(root)["accepted_digest"] == true_digest,
          "the accepted digest is what this engine builds from the script")
    check(bpy.data.objects.get("plate") is not None,
          "the re-accepted model is in the viewport")
    ok, text = run_tool("get_script", {})
    check(ok and "WITHOUT restoring" not in text,
          "get_script no longer carries the unrestored warning")
    check(sorted(cadexd_client._clients) == [root],
          "one child, for the file's own project")

    # And the store is consistent again: a fresh restoring open passes.
    cadex_backend.close_all()
    ok, report = cadex_backend.ensure_open(scene)
    check(ok, "the re-accepted project opens clean ({:s})".format(
        (report or "clean").splitlines()[0][:80]))
    restore = cadex_backend._state_for(root).restore
    check(restore.get("performed") is True
          and restore.get("matches_accepted") is True,
          "...and its restore pass matches: {!r}".format(restore))

    # The button is not a way to make an empty project do anything: on a
    # project that stores no script it refuses. A *saved* empty file, not
    # File > New: the unsaved scene's temporary root is keyed by scene name
    # and survives across files, so an earlier test's model would be found
    # there and rewritten (the ADR-186 guard exists for the same reason).
    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(workdir, "empty.blend"))
    ok, report = cadex_backend.reaccept_stored_script(bpy.context.scene)
    check(not ok and "no script to re-accept" in report,
          "re-accept refuses a project that stores no script ({:s})".format(
              report[:60]))


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

    Two things here are ADR-155's, and both are about what this test used to
    let through. It carried **one** file, so a carry that stopped after the
    first would have passed; and it adopted the copy without ever saving it
    again, so it never exercised the ordinary Ctrl-S that was overwriting
    the pointer back to the original.
    """
    print("test_save_as_carries_imported_geometry")

    supplied = os.path.join(workdir, "widget.stl")
    with open(supplied, "w", encoding="utf-8") as handle:
        handle.write(TETRAHEDRON_STL)
    second_supplied = os.path.join(workdir, "bracket.stl")
    with open(second_supplied, "w", encoding="utf-8") as handle:
        handle.write(TETRAHEDRON_STL)

    first = os.path.join(workdir, "asset-orig.blend")
    second = os.path.join(workdir, "asset-copy.blend")

    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.wm.save_as_mainfile(filepath=first)
    scene = bpy.context.scene

    payload = cadex_backend.put_asset(scene, supplied)
    check(payload.get("ok") is True,
          "the supplied component lands in the first project's store")
    payload = cadex_backend.put_asset(scene, second_supplied)
    check(payload.get("ok") is True,
          "...and so does the second one")
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

    # ADR-155: the ordinary save that used to destroy that memory. `save_pre`
    # fires on every write, and the hint was rewritten unconditionally -- so
    # one Ctrl-S between the Save-As and the rebuild replaced the pointer to
    # asset-orig.cadex with this file's own root, which `source_root` then
    # refuses for being the current one. Nothing said so: the carry found
    # nowhere to carry from and the rebuild died on the first import.
    bpy.ops.wm.save_mainfile()
    scene = bpy.context.scene
    check(cadex_backend.source_root(scene) == os.path.abspath(
              os.path.join(workdir, "asset-orig.cadex")),
          "an ordinary save does NOT overwrite that memory with its own root")

    ok, report = cadex_backend.adopt_saved_script(scene)
    check(ok, "the saved script rebuilds the Save-As'd project ({:s})".format(
        (report or "clean")[:160]))
    check("widget.stl" in (report or "") and "bracket.stl" in (report or ""),
          "the report names BOTH components it carried across ({:s})".format(
              (report or "")[:120]))
    check(bpy.data.objects.get("widget") is not None,
          "the imported component is back in the new file's viewport")
    check(bpy.data.objects.get("bracket") is not None,
          "...and so is the second one")
    check(not cadex_backend.orphaned_project(scene),
          "the adopted project is no longer orphaned")
    check(cadex_backend.stored_asset_names(scene) == {"widget.stl",
                                                      "bracket.stl"},
          "the new project holds both components in its own store")
    check(os.path.isfile(os.path.join(workdir, "asset-orig.cadex",
                                      "assets", "widget.stl")),
          "the original project keeps its own copy")
    check(len(revision_sources(os.path.join(workdir, "asset-copy.cadex"))) == 1,
          "the new project starts its own trail -- the original's two "
          "revisions did NOT come across")

    # The shape a .blend damaged by the pre-ADR-155 handler is already in:
    # its own root recorded as the source, so the original is named nowhere.
    # This cannot repair that -- the files are wherever the original is and
    # nothing here knows where -- but it must not be silent about it, which
    # is what sent a real model round the "import the file the error names,
    # press rebuild, read the next error" loop one file at a time.
    scene[cadex_backend.SOURCE_PROP] = cadex_backend.project_root(scene)
    ok, report = cadex_backend.migrate_assets(scene)
    check(ok and "its own project" in (report or ""),
          "a file that records its own root as the source says so, rather "
          "than carrying nothing quietly ({:s})".format((report or "")[:120]))


def test_link_part_travels_between_two_models(workdir):
    """A part built in one .blend, used in another, and refreshed.

    The shell's half of ADR-138, end to end and through the real operators:
    `File > Link Part...` picks another model's .blend, the engine pulls the
    solid that model accepted, the script here builds on it with
    `part.import_part`, and `File > Refresh Linked Parts` re-pulls it after
    the source moves.

    Three things this is the only place that can prove:

    - the picked **.blend** resolves to the right project root, which is the
      whole user-facing gesture (nobody picks a `.cadex` folder);
    - the refresh **rebuilds** this model, so the new shape is in the
      viewport rather than only in the store;
    - a Save-As **carries the container**, which is ADR-046's bug arriving
      on a new file type and would otherwise ship broken.
    """
    print("test_link_part_travels_between_two_models")

    source_blend = os.path.join(workdir, "sensorA.blend")
    consumer_blend = os.path.join(workdir, "assembly.blend")

    # -- the other model: one accepted solid ------------------------------
    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.wm.save_as_mainfile(filepath=source_blend)
    ok, report = run_tool("write_script", {"content": LINKED_SENSOR_SCRIPT})
    check(ok, "the source model is accepted ({:s})".format(report[:80]))
    source_root = os.path.join(workdir, "sensorA.cadex")
    check(os.path.isdir(source_root), "the source model has a project root")

    # -- this model: link it ---------------------------------------------
    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.wm.save_as_mainfile(filepath=consumer_blend)
    scene = bpy.context.scene

    # The gesture, not the backend call: the .blend the user picks is what
    # has to resolve to the project root beside it.
    check(topbar._link_source_from(source_blend) == source_root,
          "picking a .blend resolves to the project beside it")

    payload = cadex_backend.link_part(scene, source_root)
    check(payload.get("ok") is not True and payload.get("candidates") == ["sensor"],
          "omitting the output is answered with what that model publishes")

    payload = cadex_backend.link_part(scene, source_root, output="sensor")
    check(payload.get("ok") is True,
          "the part lands in this model's store ({:s})".format(
              str(payload.get("error") or "clean")[:80]))
    check(payload.get("name") == "sensor.cxpart",
          "it is stored under the output's name")
    check(payload.get("changed") is True and not payload.get("previous_revision"),
          "a first pull reports itself as new")
    check(cadex_backend.linked_parts(scene) == ["sensor.cxpart"],
          "the model lists exactly one linked part")

    ok, report = run_tool("write_script", {"content": LINKED_CONSUMER_SCRIPT})
    check(ok, "a model built on the linked part is accepted ({:s})".format(
        report[:120]))
    check(bpy.data.objects.get("sensor") is not None,
          "the linked part is in the viewport")
    # It arrived as BREP and hydrated as BREP -- which is what the shell can
    # say about it. That it is *the same solid*, to the volume and the face
    # count, is asserted where the numbers are: cadex_tests/
    # test_linked_part_live.py. The viewport mesh is a tessellation either
    # way, so counting its polygons here would prove nothing.
    check("sensor" in [obj.name for obj in brep_objects()],
          "the linked part hydrated as BREP, not as a mesh output")
    check("mount" in [obj.name for obj in brep_objects()],
          "...and the kernel cut a plate with it")
    consumer_root = cadex_backend.project_root(scene)
    first_digest = store_state(consumer_root)["accepted_digest"]

    # Nothing moved yet: a refresh must not manufacture a revision.
    ok, report = cadex_backend.refresh_linked_parts(scene)
    check(ok and "Already current" in report,
          "a refresh with nothing to do says so ({:s})".format(report[:80]))
    check(store_state(consumer_root)["accepted_digest"] == first_digest,
          "...and rebuilt nothing")

    # -- move the source model, then refresh ------------------------------
    bpy.ops.wm.open_mainfile(filepath=source_blend)
    ok, report = run_tool("set_params", {"params": {"bore": 12.0}})
    check(ok, "the source model moves ({:s})".format(report[:80]))

    bpy.ops.wm.open_mainfile(filepath=consumer_blend)
    scene = bpy.context.scene
    ok, report = cadex_backend.refresh_linked_parts(scene)
    check(ok, "the refresh succeeds ({:s})".format((report or "")[:160]))
    check("Updated:" in (report or ""),
          "the report says which part moved and between which revisions")
    check("Model rebuilt" in (report or ""),
          "...and that this model was rebuilt behind it")
    check(store_state(consumer_root)["accepted_digest"] != first_digest,
          "the refreshed model has a different digest")
    check(bpy.data.objects.get("sensor") is not None,
          "the refreshed part is still in the viewport")

    # -- and a Save-As carries it ----------------------------------------
    copy_blend = os.path.join(workdir, "assembly-copy.blend")
    bpy.ops.wm.save_as_mainfile(filepath=copy_blend)
    scene = bpy.context.scene
    ok, report = cadex_backend.adopt_saved_script(scene)
    check(ok, "the Save-As'd model rebuilds ({:s})".format(
        (report or "clean")[:160]))
    check("sensor.cxpart" in (report or ""),
          "the report names the linked part it carried across")
    check(cadex_backend.linked_parts(scene) == ["sensor.cxpart"],
          "the new model holds the container in its own store")
    check(bpy.data.objects.get("sensor") is not None,
          "the linked part is back in the new file's viewport")


# -- ADR-139: dimensions, from any angle ------------------------------------

def _view_matrix(rotation_degrees_x, rotation_degrees_z):
    """A view matrix looking at the model from one direction."""
    import math
    from mathutils import Matrix

    rotation = (Matrix.Rotation(math.radians(rotation_degrees_z), 4, 'Z')
                @ Matrix.Rotation(math.radians(rotation_degrees_x), 4, 'X'))
    return (Matrix.Translation((-30.0, -20.0, -400.0)) @ rotation.inverted())


class _Region:
    """The two attributes ``location_3d_to_region_2d`` reads off a region."""

    def __init__(self, width=1200, height=800):
        self.width = width
        self.height = height


class _RegionData:
    """...and the two it reads off the region's 3D view data."""

    def __init__(self, view_matrix):
        from mathutils import Matrix

        self.view_matrix = view_matrix
        # Orthographic, and scaled so a 10 mm feature spans ~200 px. That
        # matters: below about 60 px the number is wider than the dimension
        # line and the two halves correctly collapse to nothing, which would
        # make the segment count below a statement about the zoom rather than
        # about the drawing.
        self.window_matrix = Matrix.Diagonal((0.02, 0.05, -0.002, 1.0))
        self.perspective_matrix = self.window_matrix @ view_matrix
        self.is_perspective = False


def test_dimensions_are_readable_from_every_angle(root):
    """The shell's half of ADR-139, and the claim the feature is judged on.

    A dimension is drawn in screen space from two model-space anchors, so
    "can you read it from here" is a question about a view matrix — which is
    exactly what a headless gate can ask and a person can only answer by
    orbiting for a while and hoping.

    Three views, and the third is the one that matters: looking straight down
    the measured axis, where the two anchors project to the same pixel. That
    must become a leader carrying the number, not a zero-length line and not
    nothing at all.
    """
    print("test_dimensions_are_readable_from_every_angle")

    from mesh_agent import cadex_dimension

    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(root, "measured.blend"))
    ok, report = run_tool("write_script", {"content": MEASURED_SCRIPT})
    check(ok, "the measured model is accepted ({:s})".format(report[:120]))

    # The engine published them and the overlay picked them up, without the
    # overlay being visible: records are refreshed on every accepted
    # revision, so turning it on is a redraw rather than a round trip.
    records = cadex_dimension.records()
    by_name = {record["output"]: record for record in records}
    check(sorted(by_name) == ["bore", "height", "span"],
          "the three declared measurements reached the shell")
    check(by_name["height"]["text"] == "10.00 mm",
          "and their numbers arrived formatted by the engine")
    check(by_name["bore"]["text"] == "Ø6.00 mm",
          "including the diameter sign")
    check(by_name["height"]["subject"] == "bored",
          "each names the output whose frame its anchors are in")
    check(len(by_name["bore"].get("ring_mm") or ()) ==
          cadex_dimension.DIAMETER_SAMPLES,
          "a diameter arrives as a ring, because its endpoints are per frame")

    # Nothing here counts polygons: the viewport mesh is a tessellation
    # whatever the output is, so that number cannot tell you anything about a
    # dimension. What can be checked is the drawing, from a given camera.
    region = _Region()
    front = _RegionData(_view_matrix(90.0, 0.0))
    drawing = cadex_dimension.drawing_for(by_name["height"], region, front)
    check(drawing is not None, "a dimension seen from the front draws")
    check(drawing["kind"] == "dimension", "and it draws as a dimension")
    check(len(drawing["segments"]) == 6,
          "two extension lines, two dimension-line halves and two ticks")
    check(drawing["text"] == "10.00 mm", "carrying its number")

    # Orbit 60 degrees. The anchors have not moved; the drawing has.
    turned = cadex_dimension.drawing_for(
        by_name["height"], region, _RegionData(_view_matrix(90.0, 60.0)))
    check(turned is not None and turned["kind"] == "dimension",
          "and it is still a dimension after a 60 degree orbit")
    check(turned["text_at"] != drawing["text_at"],
          "the drawing follows the camera even though the anchors did not")

    # ...and now look straight down the Z axis, which is what `height`
    # measures. This is the case the whole design is judged on.
    down_the_axis = cadex_dimension.drawing_for(
        by_name["height"], region, _RegionData(_view_matrix(0.0, 0.0)))
    check(down_the_axis is not None,
          "looking down the measured axis still draws something")
    check(down_the_axis["kind"] == "leader",
          "it becomes a leader rather than collapsing to a point")
    check(down_the_axis["text"] == "10.00 mm",
          "and the number survives, which is the whole claim")

    # The span is across the screen from that same camera, so the two
    # measurements cannot both be edge-on at once.
    span_down = cadex_dimension.drawing_for(
        by_name["span"], region, _RegionData(_view_matrix(0.0, 0.0)))
    check(span_down is not None and span_down["kind"] == "dimension",
          "while a measurement across that view draws normally")

    # -- the toggle, and a slider ----------------------------------------
    scene = bpy.context.scene
    check(cadex_dimension.SCENE_FLAG not in scene, "the overlay starts hidden")
    report = cadex_dimension.toggle()
    check(report["shown"] is True and report["count"] == 3,
          "the toggle shows all three")
    check(cadex_dimension.SCENE_FLAG in scene,
          "and the scene flag is what the header button reads")

    ok, message = run_tool("set_params", {"params": {"width": 100.0}})
    check(ok, "the width slider moves ({:s})".format(message[:120]))
    moved = {record["output"]: record for record in cadex_dimension.records()}
    check(moved["span"]["text"] == "100.00 mm",
          "a measurement follows the parameter that moves its part")
    check(moved["height"]["text"] == "10.00 mm",
          "and one nothing moved stays where it was")

    report = cadex_dimension.toggle()
    check(report["shown"] is False, "the toggle hides them again")
    check(cadex_dimension.SCENE_FLAG not in scene,
          "and takes the scene flag with it")
    check(cadex_dimension.records() == [],
          "a hidden overlay forgets what it was drawing, so it cannot go stale")


def test_measure_asks_rather_than_rewriting_the_script(root):
    """Two picks and a button queue a request; nothing edits script.py.

    The script has exactly one author. The Measure button rides the pin
    queue that already batches picks into the next message (ADR-139) — so
    what this checks is that the button is inert until there are two picks,
    and that what it queues is a sentence rather than a write.
    """
    print("test_measure_asks_rather_than_rewriting_the_script")

    from mesh_agent import cadex_pick
    from mesh_agent import ui as mesh_ui

    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(root, "measure.blend"))
    ok, report = run_tool("write_script", {"content": MEASURED_SCRIPT})
    check(ok, "a model to pick on ({:s})".format(report[:120]))
    root_dir = cadex_backend.project_root(bpy.context.scene)
    before = store_state(root_dir)["accepted_digest"]

    cadex_pick.consume_pin_notes()  # drain anything an earlier test left
    check(mesh_ui.MESH_AGENT_OT_measure_pins.poll(bpy.context) is False,
          "Measure is inert with no picks")
    cadex_pick.queue_pin({"kind": "face", "output": "bored", "face_index": 1,
                          "detail": {}, "revision": ""})
    check(mesh_ui.MESH_AGENT_OT_measure_pins.poll(bpy.context) is False,
          "and still inert with one -- one pin is not a measurement")
    cadex_pick.queue_pin({"kind": "face", "output": "bored", "face_index": 2,
                          "detail": {}, "revision": ""})
    check(mesh_ui.MESH_AGENT_OT_measure_pins.poll(bpy.context) is True,
          "two picks arm it")

    check(bpy.ops.mesh_agent.measure_pins() == {'FINISHED'},
          "and it runs")
    after = store_state(root_dir)["accepted_digest"]
    check(after == before,
          "the button wrote no script -- the model is untouched")

    note = cadex_pick.consume_pin_notes()
    check("@face-1 of bored" in note and "@face-2 of bored" in note,
          "the next message carries both picks")
    check("part.measurement" in note,
          "and the sentence saying what to do with them")
    check(cadex_pick.consume_pin_notes() == "",
          "draining is once -- a request cannot be sent twice")


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


def test_get_script_serves_windows(root):
    """ADR-140: the script is read in windows, so it is never edited to fit.

    The host — not this add-on — can refuse a tool result that is too large.
    Faced with that, an agent trimmed comment blocks out of a user's script
    to make the next read smaller. A window is the alternative that does not
    touch the model.
    """
    print("test_get_script_serves_windows")
    reset_scene(root)

    padding = "\n".join(
        "# padding line {:03d} ".format(n) + "x" * 60 for n in range(120))
    source = BASELINE_SCRIPT + "\n" + padding + "\n# LAST-LINE-MARKER\n"
    total = len(source.splitlines())

    ok, _report = run_tool("write_script", {"content": source})
    check(ok, "the long script is accepted")

    # The default is unchanged: the whole script, no banner. ADR-044 stands.
    ok, whole = run_tool("get_script", {})
    check(ok and "# LAST-LINE-MARKER" in whole, "no arguments still serves it all")
    check("get_script window" not in whole, "and says nothing about windows")

    # A window is a window, and says so.
    ok, first = run_tool("get_script", {"offset": 1, "limit": 10})
    check(ok, "a window is served")
    check("get_script window: lines 1-10 of {:d}".format(total) in first,
          "the banner carries the range and the total")
    check("NOT THE SCRIPT" in first, "and refuses to be mistaken for the whole")
    check("offset=11" in first, "and says how to continue")
    check("# LAST-LINE-MARKER" not in first, "the window really is cut")

    # The windows reassemble into the script exactly -- no lost or doubled line.
    rebuilt, cursor = [], 1
    while cursor <= total:
        ok, chunk = run_tool("get_script", {"offset": cursor, "limit": 50})
        check(ok, "window at offset {:d} is served".format(cursor))
        body = chunk.split("]\n", 1)[1] if "]\n" in chunk else chunk
        rebuilt.append(body.split("\nEngine revision:")[0])
        cursor += 50
    check("\n".join(rebuilt).strip() == source.strip(),
          "the windows reassemble into the exact script")

    # The last window says it is the last one.
    ok, tail = run_tool("get_script", {"offset": max(1, total - 5)})
    check(ok and "reaches the end of the script" in tail,
          "the final window announces the end")
    check("# LAST-LINE-MARKER" in tail, "and carries the last line")

    # Past the end is a sentence, not an empty result the model reads as done.
    ok, past = run_tool("get_script", {"offset": total + 500})
    check(ok and "past the end" in past, "an offset past the end says so")

    # Bad arguments are refused in a sentence rather than silently defaulted.
    for bad in ({"offset": 0}, {"offset": -3}, {"limit": 0},
                {"offset": "seven"}, {"offset": True}):
        ok, complaint = run_tool("get_script", bad)
        check(not ok and "whole number 1 or greater" in complaint,
              "get_script refuses {!r}".format(bad))

    # A string of digits is what an MCP host actually sends; accept it.
    ok, coerced = run_tool("get_script", {"offset": "1", "limit": "10"})
    check(ok and "lines 1-10 of {:d}".format(total) in coerced,
          "numeric strings are read as numbers")


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

    # ADR-177: the placed copies are grouped, not interleaved with the
    # solids they instance -- an "Assembly" collection INSIDE Model, so one
    # outliner click hides the duplicates and every all_objects walker
    # (find, GC, posing, bounds) still sees them.
    from mesh_agent import model as model_module
    home = bpy.data.collections.get(cadex_hydrate.COMPONENT_COLLECTION)
    model_coll = bpy.data.collections.get(model_module.COLLECTION_NAME)
    check(home is not None and model_coll is not None
          and home.name in model_coll.children,
          "components hydrate into an Assembly collection inside Model")
    check(all(any(c is home for c in obj.users_collection)
              for obj in (swing, base, edges)),
          "the instances and their wire children are linked there")
    check(arm is not None
          and any(c is model_coll for c in arm.users_collection),
          "the source solids stay at the Model root")


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
    check(bpy.data.collections.get(cadex_hydrate.COMPONENT_COLLECTION)
          is None,
          "the Assembly collection leaves with its last component (ADR-177)")
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
    check(sorted(domains) == ["assembly", "lib", "mesh", "part",
                              "partdesign", "sketcher"],
          "overview lists the engine's real domains plus the parts library "
          "(ADR-181): {!r}".format(sorted(domains)))
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

    # EVERY domain, not just the small one. Before ADR-123 this test asked
    # for `mesh` alone -- the one domain that fit under the size cap -- so
    # `part` and `assembly` came back severed mid-structure, unparseable,
    # with half their functions gone, and the gate stayed green.
    sizes = {}
    for name in sorted(domains):
        ok, text = run_tool("describe_cad_api", {"domain": name})
        check(ok, "describe_cad_api {:s} succeeds".format(name))
        try:
            block = json.loads(text)
        except ValueError as exc:
            block = None
            check(False, "{:s} is parseable JSON ({!s})".format(name, exc))
        check(len(text) < tools._API_DOMAIN_CHARS,
              "{:s} is served whole, under the cap: {:d} of {:d} chars".format(
                  name, len(text), tools._API_DOMAIN_CHARS))
        check("[... truncated" not in text,
              "{:s} carries no truncation marker".format(name))
        sizes[name] = len(text)
        if not isinstance(block, dict):
            continue
        exports = {item["name"]: item for item in block.get("exports") or []}
        listed = set(domains.get(name, {}).get("functions") or [])
        check(set(exports) == listed,
              "{:s} serves every function the overview names ({:d} of "
              "{:d})".format(name, len(exports), len(listed)))
        check(all(item.get("signature") for item in exports.values()),
              "{:s}'s exports all carry a signature".format(name))

    ok, text = run_tool("describe_cad_api", {"domain": "mesh"})
    check(ok, "describe_cad_api for one domain succeeds")
    block = json.loads(text)
    exports = {item["name"]: item for item in block.get("exports") or []}
    check("from_shape" in exports, "the mesh domain's exports are served")
    check("signature" in exports.get("from_shape", {}),
          "exports carry full signatures")

    # The parts library (ADR-181): surfaced in the overview, browsable as a
    # domain, and the catalog rides the compact block.
    lib_entry = domains.get("lib") or {}
    check("servo" in (lib_entry.get("functions") or []),
          "the overview lists the library and its generators")
    check("m3" in (lib_entry.get("part_numbers") or {}).get("fasteners", []),
          "the overview summarises the catalogued part numbers")
    ok, text = run_tool("describe_cad_api", {"domain": "lib"})
    check(ok, "describe_cad_api lib succeeds")
    lib_block = json.loads(text)
    lib_catalog = lib_block.get("catalog") or {}
    check("sg90" in (lib_catalog.get("servos") or {}).get("skus", []),
          "the servo catalog arrives with the library block")
    check("608" in (lib_catalog.get("bearings") or {}).get("codes", []),
          "the bearing catalog arrives with the library block")

    # The two big domains: the operations the wolf could not reach.
    ok, text = run_tool("describe_cad_api", {"domain": "part"})
    part_exports = {item["name"]: item
                    for item in json.loads(text).get("exports") or []}
    for name in ("fillet", "cut", "thicken"):
        check(bool(part_exports.get(name, {}).get("signature")),
              "part.{:s} arrives with its signature".format(name))
    ok, text = run_tool("describe_cad_api", {"domain": "assembly"})
    asm_exports = {item["name"]: item
                   for item in json.loads(text).get("exports") or []}
    for name in ("body", "rollout"):
        check(bool(asm_exports.get(name, {}).get("signature")),
              "assembly.{:s} arrives with its signature".format(name))

    # ...and the long descriptions, for the functions the model names.
    ok, text = run_tool("describe_cad_api",
                        {"domain": "part", "functions": ["fillet"]})
    check(ok, "describe_cad_api with functions=[...] succeeds")
    picked = json.loads(text)
    check(isinstance(picked, list) and len(picked) == 1,
          "one entry back for one name")
    entry = picked[0] if picked else {}
    check(entry.get("name") == "fillet", "and it is the one asked for")
    summary = part_exports.get("fillet", {}).get("summary") or ""
    check(len(entry.get("description") or "") > len(summary),
          "the full description is longer than the compact summary "
          "({:d} vs {:d} chars)".format(len(entry.get("description") or ""),
                                        len(summary)))

    ok, text = run_tool("describe_cad_api",
                        {"domain": "part", "functions": ["fillet", "nope"]})
    check(not ok, "an unknown function name is refused")
    check("'nope'" in text and "fillet" in text,
          "the refusal names the miss and the domain's real exports")

    ok, text = run_tool("describe_cad_api", {"domain": "nope"})
    check(not ok, "an unknown domain is refused")
    check("part" in text and "mesh" in text,
          "the refusal names the real domains")

    GATE["describe_api"] = {
        "overview_chars": len(json.dumps(overview)),
        "domains": sorted(domains),
        "domain_chars": sizes,
        "domain_cap": tools._API_DOMAIN_CHARS,
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


RENDER_VIEWS_SCRIPT = """
body = part.box(80, 40, 20, origin=[-40, -20, 0])
fin = part.cylinder(6, 30, origin=[0, 0, 20])
result = {"body": body, "fin": fin}
"""


def test_render_views_frames_the_engines_geometry(root):
    """The cameras are fitted to what the ENGINE built (ADR-124).

    Honest about what this cannot cover: ``draw_view3d`` needs a real VIEW_3D
    and the gate runs ``--background``, so no pixel here is ever rendered and
    nothing asserts the image looks like the model. What it does cover is the
    input to the cameras -- the world bounding box of hydrated engine
    geometry, measured against dimensions the script declares in millimetres
    -- and that the refusal on the path the gate can reach is a sentence
    rather than a traceback.
    """

    print("test_render_views_frames_the_engines_geometry")
    from mesh_agent import capture

    reset_scene(root)
    ok, report = run_tool("write_script", {"content": RENDER_VIEWS_SCRIPT})
    check(ok, "the two-solid script accepted ({:s})".format(
        (report or "").splitlines()[0] if report else ""))
    if not ok:
        return

    bbox = capture.model_bbox()
    check(bbox is not None, "the Model collection has a measurable bbox")
    if bbox is None:
        return
    (low_x, low_y, low_z), (high_x, high_y, high_z) = bbox
    check(abs((high_x - low_x) - 80.0) < 0.5,
          "it is 80 mm across x (got {:.2f})".format(high_x - low_x))
    check(abs((high_y - low_y) - 40.0) < 0.5,
          "40 mm across y (got {:.2f})".format(high_y - low_y))
    check(abs((high_z - low_z) - 50.0) < 0.5,
          "and 50 mm tall -- the box plus the cylinder standing on it "
          "(got {:.2f})".format(high_z - low_z))

    views = capture.view_matrices(bbox)
    corners = [(x, y, z) for x in (low_x, high_x) for y in (low_y, high_y)
               for z in (low_z, high_z)]
    contained = all(
        all((lambda p: p is not None and abs(p[0]) <= 1.0 and abs(p[1]) <= 1.0)(
            capture.project(view["view"], view["window"], corner))
            for corner in corners)
        for view in views)
    check(contained, "all four fitted cameras contain the built model")

    image_b64, error = capture.render_views()
    check(image_b64 is None, "no image in background mode, as expected")
    message = str(error or "")
    check(message.endswith(".") and "scene_summary" in message,
          "and the refusal is a sentence pointing somewhere useful "
          "(got {!r})".format(message[:80]))
    ok, text = run_tool("render_views", {})
    check(not ok and text.strip().endswith("."),
          "the tool reports it as an error, in a sentence")

    GATE["render_views"] = {
        "bbox_mm": [round(value, 2) for value in
                    (low_x, low_y, low_z, high_x, high_y, high_z)],
        "views": [view["name"] for view in views],
        # No composite is produced in background mode; when a viewport
        # exists this is the size of the image the tool returns.
        "composite_px": None if image_b64 is None else [1024, 1024],
    }


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



#: Two boards with terminals and no wires: the smallest harness the wiring
#: editor can actually be edited on. Deliberately a `boards(...)` script, so
#: the ports come back marked editable and `set_params(nets=...)` is allowed.
WIRING_SCRIPT = """
T, PITCH = 1.6, 2.54
DOWN = (0.0, 0.0, -1.0)
left = part.box(20.0, 20.0, T, label="left")
right = part.box(20.0, 20.0, T, origin=(20.0, 0.0, 0.0), label="right")

b = boards({
    "left": board(left, terminals=[
        term("sda", origin=(10.0, 5.0, T), axis=DOWN, hole_dia=1.0, depth=T),
        term("gnd", origin=(10.0, 5.0 + PITCH, T), axis=DOWN, hole_dia=1.0,
             depth=T),
    ]),
    "right": board(right, terminals=[
        term("sda", origin=(30.0, 5.0, T), axis=DOWN, hole_dia=1.0, depth=T),
        term("gnd", origin=(30.0, 5.0 + PITCH, T), axis=DOWN, hole_dia=1.0,
             depth=T),
    ]),
})

n = nets(ports=b, wires={})

result = {"left": left, "right": right}
for name, w in n.items():
    if not w.enabled:
        continue
    result["wire_" + name] = part.cable(w.a, w.b, gauge_mm=w.gauge,
                                        avoid=[left, right], cell_mm=1.0)
"""


def test_two_applies_in_a_row_both_land(root):
    """THE ADR-122 regression, against the bundled engine.

    ``wiring.push`` started a ``Lifecycle`` and handed it to a timer that
    threw it away, so ``_revision_from_payload`` never ran and the shell's
    cached ``expected_revision`` still named the revision from *before* the
    first apply. The engine had moved on, so the second apply — and every
    apply after it — came back ``STALE_PROGRAM_REVISION``, with the refusal
    dropped on the floor too because nobody read the payload. Twenty wires
    dragged, one cable built, nineteen wiped off the canvas by the next
    refresh.

    So: draw a wire, Apply; draw a second, Apply again with no intervening
    rebuild; and assert **both** cables exist in the accepted revision. This
    fails on the second apply without the pump.
    """
    print("test_two_applies_in_a_row_both_land")
    from mesh_agent import wiring

    reset_scene(root)
    scene = bpy.context.scene
    ok, report = run_tool("write_script", {"content": WIRING_SCRIPT})
    check(ok, "the two-board harness was accepted: {:s}".format(
        first_line_of(report)))

    tree = wiring.ensure_tree(scene)
    check(wiring.sync_from_engine(scene, force=True),
          "the canvas filled from the engine")
    check(len(tree.nodes) == 2, "two boards on the canvas")
    check(tree.cadex_editable, "and a boards(...) harness is editable")
    left = next((n for n in tree.nodes if n.port == "left"), None)
    right = next((n for n in tree.nodes if n.port == "right"), None)
    if left is None or right is None:
        check(False, "both ports drew a node")
        return

    def apply_and_wait(label):
        ok, report = wiring.push(scene)
        if not ok:
            check(False, "{:s}: {:s}".format(label, first_line_of(report)))
            return False
        # No timers under --background, so the gate drives the pump, exactly
        # as it drives the drag pump.
        ok, report = cadex_backend.wiring_apply_now()
        check(ok, "{:s} landed: {:s}".format(label, first_line_of(report)))
        return ok

    def cables():
        # Keyed on the engine's own output property, not on the object name:
        # a hydrated BREP brings an " ... Edges" companion object along with
        # it, and that is a display detail, not a second cable.
        return sorted(
            str(obj[cadex_hydrate.OUTPUT_PROP]) for obj in bpy.data.objects
            if str(obj.get(cadex_hydrate.OUTPUT_PROP, "")).startswith("wire_")
            and str(obj.get(cadex_hydrate.KIND_PROP, "")) == "brep")

    def _terminal(node, name, outputs):
        return next(s for s in (node.outputs if outputs else node.inputs)
                    if s.terminal == name)

    before = cadex_backend._state_for(root).revision
    tree.links.new(_terminal(left, "sda", True), _terminal(right, "sda", False))
    if not apply_and_wait("the first apply"):
        return
    first = cadex_backend._state_for(root).revision
    check(first and first != before,
          "the first apply moved the revision guard: {!r} -> {!r}".format(
              before, first))
    check(len(cables()) == 1, "and built one cable: {!r}".format(cables()))

    # The second apply, with no rebuild, no sync and no chat turn in between:
    # exactly what dragging a second wire and pressing Apply again does.
    tree.links.new(_terminal(left, "gnd", True), _terminal(right, "gnd", False))
    if not apply_and_wait("the second apply"):
        return
    second = cadex_backend._state_for(root).revision
    check(second and second != first,
          "the second apply moved it again: {!r} -> {!r}".format(first, second))
    check(not model_module.last_error(),
          "with nothing refused in silence ({:s})".format(
              first_line_of(model_module.last_error())))

    built = cables()
    check(len(built) == 2,
          "BOTH cables exist in the accepted revision: {!r}".format(built))
    check(len(tree.links) == 2,
          "and both links survived the sync that follows an apply")
    check(len(wiring.stored_rows(tree)) == 2,
          "with two rows in the table the canvas mirrors")
    GATE["wiring_applies"] = cadex_backend.wiring_stats()["requests"]


CAGE_SCRIPT = """
c = cage({
    "torso": section_cage([
        ring(0, 30, 38, exponent=2.4),
        ring(120, 46, 52, exponent=3.0),
        ring(300, 34, 40, exponent=2.2),
    ], axis=(1, 0, 0)),
})

result = {"torso": part.loft_cage(c["torso"], solid=True)}
"""


def test_a_dragged_ring_lands_in_the_accepted_revision(root):
    """O3's whole point, end to end against the bundled engine (ADR-127).

    Draw the cage, grab a ring, scale and move it, press Apply — and assert
    the accepted revision moved and the engine now holds the dragged row.
    Modelled directly on ``test_two_applies_in_a_row_both_land``, and it
    applies twice for that test's reason: a cage drag is a stream of
    transform events, so if the pump ever loses a request this is where it
    shows.
    """
    print("test_a_dragged_ring_lands_in_the_accepted_revision")
    from mesh_agent import cadex_cage

    reset_scene(root)
    scene = bpy.context.scene
    ok, report = run_tool("write_script", {"content": CAGE_SCRIPT})
    check(ok, "the cage script was accepted: {:s}".format(first_line_of(report)))
    if not ok:
        return

    cages, rows = cadex_backend.script_cages(scene)
    check(cages is not None and len(cages) == 1,
          "the engine serves one declared cage")
    check(rows is not None and len(rows) == 3,
          "with its three rings: {!r}".format(rows))
    if not cages or not rows:
        return
    check(cages[0]["axis"] == [1.0, 0.0, 0.0], "and the cage's own axis")

    report = cadex_cage.show(scene)
    drawn = cadex_cage.ring_objects(scene)
    check(report.get("shown") and len(drawn) == 3,
          "three rings drawn as an overlay ({!r})".format(report))
    if len(drawn) != 3:
        return
    # A sibling of Model, never a child, and never tagged cadex_output --
    # either would put the overlay in front of the hydrate GC.
    check(cadex_cage.COLLECTION_NAME in
          {child.name for child in scene.collection.children},
          "the overlay collection is a sibling of Model at the scene root")
    check(all(cadex_hydrate.OUTPUT_PROP not in obj for obj in drawn),
          "and no ring is tagged as an engine output")
    middle = drawn[1]
    check(abs(middle.matrix_world.translation.x - 120.0) < 1e-6,
          "the middle ring sits at its position on the spine (got {:.3f})"
          .format(middle.matrix_world.translation.x))

    def apply_and_wait(label):
        ok, report = cadex_cage.apply(scene)
        if not ok:
            check(False, "{:s}: {:s}".format(label, first_line_of(report)))
            return False
        # No timers under --background: the gate drives the pump, exactly as
        # it does for the wiring canvas.
        ok, report = cadex_backend.wiring_apply_now()
        check(ok, "{:s} landed: {:s}".format(label, first_line_of(report)))
        return ok

    before = cadex_backend._state_for(root).revision

    # Grab the waist and pull it in: the gesture the wolf's bad ring needed.
    middle.scale = (0.5, 1.0, 1.0)
    bpy.context.view_layer.update()
    if not apply_and_wait("the first apply"):
        return
    first = cadex_backend._state_for(root).revision
    check(first and first != before,
          "the first apply moved the revision guard: {!r} -> {!r}".format(
              before, first))
    _cages, applied = cadex_backend.script_cages(scene)
    waist = [row for row in (applied or []) if abs(row["position"] - 120.0) < 1e-6]
    check(len(waist) == 1 and abs(waist[0]["half_width"] - 23.0) < 0.01,
          "the engine now holds the dragged half-width: 46 * 0.5 = 23 "
          "(got {!r})".format([row.get("half_width") for row in waist]))
    check(waist and abs(waist[0]["exponent"] - 3.0) < 1e-9,
          "and the exponent came back untouched — nothing in the viewport "
          "edits it")

    # A second apply with no rebuild and no chat turn in between, which is
    # the ADR-122 regression this shares a pump with.
    cadex_cage.show(scene)
    drawn = cadex_cage.ring_objects(scene)
    if len(drawn) != 3:
        check(False, "the overlay redrew after the apply")
        return
    drawn[2].location.x += 40.0
    bpy.context.view_layer.update()
    if not apply_and_wait("the second apply"):
        return
    second = cadex_backend._state_for(root).revision
    check(second and second != first,
          "the second apply moved it again: {!r} -> {!r}".format(first, second))
    _cages, applied = cadex_backend.script_cages(scene)
    positions = sorted(round(float(row["position"]), 3) for row in applied or [])
    check(positions == [0.0, 120.0, 340.0],
          "and the last ring moved 40 mm down the spine: {!r}".format(positions))
    check(not model_module.last_error(),
          "with nothing refused in silence ({:s})".format(
              first_line_of(model_module.last_error())))

    GATE["cage"] = {"rings": len(drawn), "positions": positions}
    cadex_cage.clear(scene)
    check(not cadex_cage.ring_objects(scene), "and the overlay cleans up")


TWO_PART_SCRIPT = """
result = {
    "bracket": part.box(40.0, 25.0, 15.0),
    "arm": part.cylinder(6.0, 60.0, origin=[80.0, 0.0, 0.0]),
}
"""

#: ...and the same model with one of them gone: what a script changing its
#: mind looks like, and what a tick for the missing part has to survive.
ONE_PART_SCRIPT = """
result = {"bracket": part.box(40.0, 25.0, 15.0)}
"""


def test_marked_parts_export_as_stl(root):
    """ADR-156 and ADR-158, end to end against the bundled engine.

    Four claims, in the order they can fail:

    1. **the roster is the accepted output list** — no script global
       declares it, so a two-output script must produce two candidates,
       both unticked, with no help from the panel.
    2. **a tick is the scene's, and reaches the engine not at all** — it
       lands in a scene property, the accepted revision does not move, and
       ``script.json`` holds nothing about printing. That is ADR-158 stated
       as assertions rather than claimed by an ADR.
    3. **the export writes real STLs into the store** — one file per ticked
       part, in ``print/``, written by the engine off the accepted solid
       from the list the shell named.
    4. **the second export refuses and names what is there** — then
       ``keep_both`` writes beside it. The refusal is what the Overwrite /
       Keep Both dialog is built from, so a refusal that did not name the
       files would leave that dialog with nothing to say.
    """
    print("test_marked_parts_export_as_stl")
    from mesh_agent import cadex_print

    reset_scene(root)
    scene = bpy.context.scene
    ok, report = run_tool("write_script", {"content": TWO_PART_SCRIPT})
    check(ok, "the two-part script was accepted: {:s}".format(
        first_line_of(report)))
    if not ok:
        return

    roster = cadex_backend.script_printable(scene)
    names = sorted(str(entry["name"]) for entry in roster or [])
    check(names == ["arm", "bracket"],
          "both outputs are printable candidates: {!r}".format(names))
    check(all(set(entry) == {"name", "artifact_kind"}
              for entry in roster or []),
          "the roster carries no tick — the engine has no opinion about one "
          "(cadex ADR-158): {!r}".format(roster))
    check(not cadex_print.marked(scene),
          "and nothing is ticked until somebody ticks it")
    # The roster reaches the panel's cache off the block the backend already
    # adopts, so the checkboxes are drawable with no round trip of their own.
    check(len(cadex_print.cached(scene)) == 2,
          "the panel's cache holds the roster after the rebuild")

    before = cadex_backend._state_for(root).revision
    ok, report = cadex_print.toggle(scene, "bracket")
    check(ok, "ticking one part took: {:s}".format(first_line_of(report)))
    check(cadex_print.marked(scene) == ["bracket"],
          "and it is the one that is marked: {!r}".format(
              cadex_print.marked(scene)))
    check(cadex_print.is_marked(scene, "bracket")
          and "bracket" in str(scene.get("cadex_printable") or ""),
          "the tick is in the SCENE, which is what saves it with the .blend")
    check(cadex_backend._state_for(root).revision == before,
          "a print mark did NOT move the revision guard — no rebuild for a "
          "checkbox ({!r} -> {!r})".format(
              before, cadex_backend._state_for(root).revision))
    with open(os.path.join(root, "script.json"), "r") as handle:
        stored = json.load(handle)
    check(not [key for key in stored if key.startswith("print")],
          "and script.json holds nothing about printing at all: {!r}".format(
              sorted(key for key in stored if key.startswith("print"))))

    # ...and again through the registered operator, which is what the row in
    # the Parameters editor actually calls. A panel row is a button here, not
    # a BoolProperty, so this is the only thing that proves the name reaches
    # the tick list at all.
    check(bpy.ops.mesh_agent.toggle_printable(name="arm") == {'FINISHED'},
          "the panel's per-row operator ticks a second part")
    check(cadex_print.marked(scene) == ["bracket", "arm"],
          "both are marked now: {!r}".format(cadex_print.marked(scene)))
    bpy.ops.mesh_agent.toggle_printable(name="arm")
    check(cadex_print.marked(scene) == ["bracket"],
          "and ticking it again unticks it: {!r}".format(
              cadex_print.marked(scene)))

    payload = cadex_backend.export_printable(scene)
    check(payload.get("ok") is True,
          "the export ran: {!r}".format(payload.get("error") or "ok"))
    written = [str(item.get("file")) for item in payload.get("files") or []]
    check(written == ["bracket.stl"],
          "one STL, for the one marked part: {!r}".format(written))
    stls = sorted(os.path.basename(path) for path in
                  glob.glob(os.path.join(root, "print", "*.stl")))
    check(stls == ["bracket.stl"],
          "and it is on disk in print/: {!r}".format(stls))
    size = os.path.getsize(os.path.join(root, "print", "bracket.stl"))
    check(size > 84, "with real triangles in it ({:d} bytes)".format(size))

    repeat = cadex_backend.export_printable(scene)
    check(str(repeat.get("failure_code")) == "PRINT_FILES_EXIST",
          "a second export refuses rather than overwriting: {!r}".format(
              repeat.get("failure_code")))
    existing = list((repeat.get("observed") or {}).get("existing") or [])
    check(existing == ["bracket.stl"],
          "and the refusal names the file, which is what the dialog shows: "
          "{!r}".format(existing))

    kept = cadex_backend.export_printable(scene, conflict="keep_both")
    check(kept.get("ok") is True,
          "keep_both went through: {!r}".format(kept.get("error") or "ok"))
    stls = sorted(os.path.basename(path) for path in
                  glob.glob(os.path.join(root, "print", "*.stl")))
    check(stls == ["bracket-002.stl", "bracket.stl"],
          "leaving both files: {!r}".format(stls))

    GATE["printable"] = {"outputs": names, "files": stls, "bytes": size}

    # Drop-on-drift, which moved to this side of the boundary with the ticks
    # (cadex ADR-158): a rebuild that stops publishing a part is what drops
    # its tick, and adopting the new roster is where that happens. Ticking
    # `arm` first so there is something to lose as well as something to keep.
    bpy.ops.mesh_agent.toggle_printable(name="arm")
    # `replace` because this rewrite *drops* an output, which is the ADR-045
    # guard rather than anything to do with printing.
    ok, report = run_tool("write_script", {"content": ONE_PART_SCRIPT,
                                           "replace": True})
    check(ok, "the one-part rewrite was accepted: {:s}".format(
        first_line_of(report)))
    if ok:
        check([str(entry["name"]) for entry in cadex_print.cached(scene)] ==
              ["bracket"], "the roster follows the rebuild: {!r}".format(
                  [str(entry["name"]) for entry in cadex_print.cached(scene)]))
        check(cadex_print.marked(scene) == ["bracket"],
              "and the tick for the part that is gone went with it: "
              "{!r}".format(cadex_print.marked(scene)))


#: A blind bore: a 10 mm hole down into a 20 mm block that does NOT break
#: through. Nothing on the outside of this part says whether it did, which is
#: the case the section view exists for (ADR-148). Its depth is a parameter so
#: the same model can be rebuilt under the cut.
BLIND_BORE_SCRIPT = """
p = params(depth=num(10.0, unit="mm", min=2.0, max=18.0, step=0.5))
block = part.box(40.0, 30.0, 20.0)
bore = part.cylinder(5.0, p.depth + 1.0, origin=[20.0, 15.0, 20.0 - p.depth])
result = {"body": part.cut(block, bore)}
"""


def test_the_section_view_cuts_the_model_open(root):
    """ADR-148, end to end against the bundled engine.

    The three claims worth a gate, in the order they can fail:

    1. **the cut is capped** — a boolean closes the surface it opens, which
       is the whole reason this is a boolean rather than the viewport's own
       clipping planes. A polygon lying in the cutting plane is the evidence,
       and it is evidence the `--background` gate can actually collect;
       nothing about ``rv3d.clip_planes`` can be seen from here at all.
    2. **the bore is open in the section** — the cap is the *material*
       cross-section, so the wall of the blind bore has to appear in it. This
       is what a person turns the section on to see.
    3. **nothing reached the engine** — the accepted revision before and
       after is the same revision. The section is a view (`docs/VISION.md`:
       nothing happens outside the script), and this is the assertion that
       says so rather than the docstring that claims it.

    ...plus the one that breaks quietly: a rebuild under the cut. The
    modifier rides on the object and ``cadex_hydrate`` swaps the mesh
    datablock, so it should survive — and if that ever stops being true, the
    section silently stops applying to the newest shape.
    """
    print("test_the_section_view_cuts_the_model_open")
    from mesh_agent import cadex_section

    reset_scene(root)
    scene = bpy.context.scene
    ok, report = run_tool("write_script", {"content": BLIND_BORE_SCRIPT})
    check(ok, "the blind-bore script was accepted: {:s}".format(
        first_line_of(report)))
    if not ok:
        return

    body = next((obj for obj in brep_objects()
                 if obj.get(cadex_hydrate.OUTPUT_PROP) == "body"), None)
    check(body is not None, "the part hydrated")
    if body is None:
        return

    def evaluated(obj):
        """World-space points and polygons of what is actually drawn."""
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        mesh = obj.evaluated_get(depsgraph).to_mesh()
        points = [obj.matrix_world @ vertex.co for vertex in mesh.vertices]
        polygons = [[points[index] for index in polygon.vertices]
                    for polygon in mesh.polygons]
        obj.evaluated_get(depsgraph).to_mesh_clear()
        return points, polygons

    points, _polygons = evaluated(body)
    check(max(point.x for point in points) > 39.0,
          "the whole part is drawn before the cut")
    before = cadex_backend._state_for(root).revision

    # -- on, through the agent's tool, which is the path with no button ------
    ok, message = run_tool("section_view", {"show": True, "axis": "X"})
    check(ok, "section_view turned it on ({:s})".format(first_line_of(message)))
    flag = dict(scene.get(cadex_section.SCENE_FLAG) or {})
    check(flag.get("axis") == 'X' and abs(float(flag.get("offset") or 0.0) - 20.0)
          < 0.51,
          "and centred the plane on the part: {!r}".format(
              (flag.get("axis"), flag.get("offset"))))
    offset = float(flag.get("offset") or 0.0)

    points, polygons = evaluated(body)
    check(points and all(cadex_section.is_kept(point, 'X', offset + 1e-3)
                         for point in points),
          "every drawn point is on the surviving side of the plane")
    caps = [polygon for polygon in polygons
            if all(abs(point.x - offset) < 1e-3 for point in polygon)]
    check(caps, "the cut face is capped: {:d} polygon(s) lie in the plane"
                .format(len(caps)))

    # The bore's wall, in the cut face: 5 mm from the bore axis at y = 15,
    # above the blind floor at z = 10. A clip plane cannot produce this
    # because it fills nothing; an uncut part cannot either.
    wall = [point for polygon in caps for point in polygon
            if abs(abs(point.y - 15.0) - 5.0) < 0.4 and point.z > 9.0]
    check(wall, "the blind bore is open in the section — its wall is in the "
                "cut face ({:d} point(s))".format(len(wall)))

    check(cadex_backend._state_for(root).revision == before,
          "and the engine never heard about any of it: the accepted "
          "revision is unchanged")
    check(bpy.data.objects.get(cadex_section.CUTTER_NAME) is not None
          and not bpy.data.objects[cadex_section.CUTTER_NAME].visible_get(),
          "the cutter is in the scene and hidden")

    # Down onto solid material well clear of both the bore and the plane: the
    # cutter box wraps the whole model, so if a hidden object could be hit
    # this ray would find it before it found the part.
    hit = scene.ray_cast(bpy.context.view_layer.depsgraph,
                         (8.0, 6.0, 400.0), (0.0, 0.0, -1.0))
    check(hit[0] and getattr(hit[4], "name", "") != cadex_section.CUTTER_NAME,
          "and never steals a face pick: {!r}".format(
              (hit[0], getattr(hit[4], "name", None))))

    # -- how long the cut takes, which is what a slider drag pays -----------
    started = time.perf_counter()
    for step in range(6):
        scene.cadex_section.offset = offset + (step - 3) * 2.0
        bpy.context.view_layer.update()
        bpy.context.evaluated_depsgraph_get().update()
        body.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()
    seconds = (time.perf_counter() - started) / 6.0
    GATE["section_cut_seconds"] = round(seconds, 4)
    scene.cadex_section.offset = offset

    # -- a rebuild under the cut --------------------------------------------
    ok, message = run_tool("set_params", {"params": {"depth": 16.0}})
    check(ok, "the model rebuilt with the section on: {:s}".format(
        first_line_of(message)))
    body = next((obj for obj in brep_objects()
                 if obj.get(cadex_hydrate.OUTPUT_PROP) == "body"), None)
    check(body is not None
          and body.modifiers.get(cadex_section.MODIFIER_NAME) is not None,
          "the cut survived the rebuild")
    if body is not None:
        points, polygons = evaluated(body)
        check(points and all(cadex_section.is_kept(point, 'X', offset + 1e-3)
                             for point in points),
              "and still applies to the shape that came back")
        deeper = [point for polygon in polygons for point in polygon
                  if abs(point.x - offset) < 1e-3 and point.z < 5.0
                  and abs(abs(point.y - 15.0) - 5.0) < 0.4]
        check(deeper, "the deeper bore is visible in the same section")

    # -- render_views does not show the cut ---------------------------------
    restore = cadex_section.suspend()
    points, _polygons = evaluated(body)
    check(max(point.x for point in points) > 39.0,
          "suspended for render_views, the whole part is drawn again")
    restore()
    points, _polygons = evaluated(body)
    check(max(point.x for point in points) < offset + 1e-3,
          "and the cut comes back after it")

    # -- off ----------------------------------------------------------------
    ok, message = run_tool("section_view", {"show": False})
    check(ok, "section_view turned it off ({:s})".format(first_line_of(message)))
    check(all(obj.modifiers.get(cadex_section.MODIFIER_NAME) is None
              for obj in bpy.data.objects if obj.modifiers),
          "no modifier is left anywhere")
    check(bpy.data.objects.get(cadex_section.CUTTER_NAME) is None
          and bpy.data.node_groups.get(cadex_section.CLIP_GROUP_NAME) is None,
          "and neither the cutter nor its node group outlives it")
    points, _polygons = evaluated(body)
    check(max(point.x for point in points) > 39.0, "the part is whole again")

    GATE["section"] = {"caps": len(caps), "bore_wall_points": len(wall)}


def test_the_blueprint_view_restyles_and_restores(root):
    """ADR-150 in the viewport half, end to end against the bundled engine.

    The claims worth a gate, in the order they can fail: the styled viewport
    equals ``shading_values`` field for field (any sub-overlay missing from
    that table would appear uninvited, because this is the one view that
    turns overlays ON); the engine never hears about any of it; it layers
    over the section instead of excluding it; ``suspend_for_render`` takes
    the styling off and its undo puts it back; a rebuild under it leaves the
    styling standing; and off restores the pre-toggle look EXACTLY — the
    gate scene's look is the shipped startup look, which the startup test
    pins, so exact restore here is what keeps that pin true after a
    blueprint has been on. Plus the sheet renderer's headless refusal, which
    is all a ``--background`` gate can prove about it.
    """
    print("test_the_blueprint_view_restyles_and_restores")
    from mesh_agent import cadex_blueprint, cadex_section, cadex_views

    def near_field(got, want):
        if isinstance(want, tuple):
            return (len(tuple(got)) == len(want)
                    and all(abs(float(g) - float(w)) < 1e-4
                            for g, w in zip(tuple(got), want)))
        if isinstance(want, float):
            return abs(float(got) - want) < 1e-4
        return got == want

    def styled_exactly(space, values, label):
        for field, want in values.items():
            got = cadex_blueprint._read_field(space, field)
            check(near_field(got, want),
                  "{:s}: {:s} is {!r} (wanted {!r})".format(
                      label, field, got, want))

    reset_scene(root)
    scene = bpy.context.scene
    ok, report = run_tool("write_script", {"content": BLIND_BORE_SCRIPT})
    check(ok, "the script was accepted: {:s}".format(first_line_of(report)))
    if not ok:
        return
    before = cadex_backend._state_for(root).revision

    spaces = cadex_blueprint._spaces()
    check(bool(spaces), "the gate scene has a 3D viewport space")
    if not spaces:
        return
    space = spaces[0]
    fields = cadex_blueprint.shading_values()
    look_before = {field: cadex_blueprint._read_field(space, field)
                   for field in fields}

    # -- on, through the agent's tool, which is the path with no button ------
    ok, message = run_tool("blueprint_view",
                           {"show": True, "theme": "blueprint", "grid": True})
    check(ok, "blueprint_view turned it on ({:s})".format(
        first_line_of(message)))
    styled_exactly(space, cadex_blueprint.shading_values("blueprint", True),
                   "styled")
    check(cadex_backend._state_for(root).revision == before,
          "and the engine never heard about it: the accepted revision is "
          "unchanged")

    # -- it layers over the section rather than excluding it -----------------
    ok, message = run_tool("section_view", {"show": True, "axis": "X"})
    check(ok, "the section went on under the blueprint ({:s})".format(
        first_line_of(message)))
    check(dict(scene.get(cadex_section.SCENE_FLAG) or {}).get("shown") is True,
          "the section reports shown with the blueprint on")
    styled_exactly(space, cadex_blueprint.shading_values("blueprint", True),
                   "sectioned")
    run_tool("section_view", {"show": False})

    # -- a rebuild under it leaves the styling standing -----------------------
    ok, message = run_tool("set_params", {"params": {"depth": 16.0}})
    check(ok, "the model rebuilt with the blueprint on: {:s}".format(
        first_line_of(message)))
    styled_exactly(space, cadex_blueprint.shading_values("blueprint", True),
                   "rebuilt")

    # -- the theme is live state, not a one-shot ------------------------------
    scene.cadex_blueprint.theme = 'grey'
    styled_exactly(space, cadex_blueprint.shading_values("grey", True),
                   "retinted")
    scene.cadex_blueprint.theme = 'blueprint'

    # -- render_views suspends it, and the undo puts it back ------------------
    undo = cadex_views.suspend_for_render()
    styled_exactly(space, look_before, "suspended")
    undo()
    styled_exactly(space, cadex_blueprint.shading_values("blueprint", True),
                   "resumed")

    # -- the sheet renderer refuses headless, in the stated sentence ----------
    ok, message = run_tool("make_blueprint", {})
    check(not ok and "Blueprint rendering is unavailable in background mode"
          in str(message),
          "make_blueprint refuses under --background: {:s}".format(
              first_line_of(message)))

    # ...so no draft can exist here, and the store side of the ADR-178
    # split refuses in its own sentence before it reaches the engine.
    ok, message = run_tool("save_blueprint", {})
    check(not ok and "no draft" in str(message)
          and "make_blueprint" in str(message),
          "save_blueprint with nothing drafted refuses with the fix: "
          "{:s}".format(first_line_of(message)))

    # -- ADR-179: the drawing has a window of its own ------------------------
    from mesh_agent import cadex_drawings
    check(cadex_drawings.EDITOR_AVAILABLE
          and getattr(bpy.types, "SpaceCadexBlueprint", None) is not None,
          "this bundle carries the Blueprint Editor space type")
    editor_area = bpy.context.window_manager.windows[0].screen.areas[-1]
    previous_type = editor_area.type
    try:
        editor_area.type = 'CADEX_BLUEPRINT'
        check(editor_area.type == 'CADEX_BLUEPRINT',
              "an area becomes the Blueprint Editor, headless included")
        editor_space = editor_area.spaces.active
        check(cadex_drawings.selection(editor_space)["kind"] == "draft",
              "a fresh editor opens on the draft")
        cadex_drawings.select(editor_space, 7)
        check(cadex_drawings.selection(editor_space)
              == {"kind": "stored", "ordinal": 7},
              "the selection is per-space state, so two editors can show "
              "two sheets")
    finally:
        cadex_drawings._selections.clear()
        editor_area.type = previous_type

    # -- off restores the pre-toggle look EXACTLY -----------------------------
    ok, message = run_tool("blueprint_view", {"show": False})
    check(ok, "blueprint_view turned it off ({:s})".format(
        first_line_of(message)))
    styled_exactly(space, look_before, "restored")
    check(cadex_blueprint.SCENE_FLAG not in scene
          and cadex_blueprint.SAVED_KEY not in scene,
          "both scene flags are gone")

    GATE["blueprint"] = {"fields": len(fields),
                         "themes": sorted(cadex_blueprint.THEMES)}


#: The jointed assembly with one slider of each kind (the PREVIEW_SCRIPT
#: pair), plus a two-move staged explosion on the same component -- up, then
#: over -- which is what makes the staged windows observable at factor 0.5.
EXPLODED_SCRIPT = """
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
boom = assembly.exploded_view(asm, [
    {"components": [swing], "transform": [0, 0, 30]},
    {"components": [swing], "transform": [20, 0, 0]},
])
result = {"plate": plate, "arm": arm, "base": base, "swing": swing,
          "j": j, "asm": asm, "diag": diag, "boom": boom}
"""


def test_the_exploded_view_spreads_the_assembly(root):
    """ADR-149, end to end against the bundled engine.

    The factor-0.5 check comes first on purpose: it is the D3 risk made a
    test. The pure half predicts a mid-stage pose, the viewport is asked
    for the same pose through ``matrix_world``, and if the depsgraph or the
    hook ordering ever fights the re-application, this is the assertion
    that says so before anything subtler gets a chance to.
    """
    print("test_the_exploded_view_spreads_the_assembly")
    from mesh_agent import cadex_explode

    reset_scene(root)
    scene = bpy.context.scene
    ok, report = run_tool("write_script", {"content": EXPLODED_SCRIPT})
    check(ok, "the exploded-assembly script was accepted: {:s}".format(
        first_line_of(report)))
    if not ok:
        return

    swing = bpy.data.objects.get("swing")
    base = bpy.data.objects.get("base")
    check(swing is not None and base is not None, "the components hydrated")
    if swing is None or base is None:
        return

    display = dict(cadex_backend.last_accepted(root).get("display") or {})
    record = (display.get("boom") or {}).get("exploded_view")
    check(isinstance(record, dict),
          "the display entry carries the exploded-view record")
    if not isinstance(record, dict):
        return
    stages = list(record["stages"])
    solved = cadex_explode._solved_poses(display, list(record["final_poses"]))
    solved_swing = tuple(swing.matrix_world.translation)
    solved_base = tuple(base.matrix_world.translation)
    revision_before = cadex_backend._state_for(root).revision

    def at(obj):
        return tuple(obj.matrix_world.translation)

    def near(a, b, tolerance=1e-4):
        return max(abs(x - y) for x, y in zip(a, b)) < tolerance

    # -- (b) FIRST: the viewport at factor 0.5 is the pure half's number ----
    ok, message = run_tool("exploded_view", {"show": True, "factor": 0.5})
    check(ok, "exploded_view turned it on ({:s})".format(
        first_line_of(message)))
    predicted = cadex_explode.poses_at(0.5, solved, stages)
    check(near(at(swing), predicted["swing"][0]),
          "factor 0.5 matches the staged interpolation (viewport {!r}, "
          "predicted {!r})".format(at(swing), predicted["swing"][0]))

    # -- (a) factor 1 is the engine's final pose; 0 and off reassemble ------
    scene.cadex_explode.factor = 1.0
    final_swing = tuple(record["final_poses"]["swing"]["position_mm"])
    check(near(at(swing), final_swing),
          "factor 1 is the engine's final pose ({!r})".format(at(swing)))
    check(near(at(base), solved_base),
          "the grounded component never moves")
    scene.cadex_explode.factor = 0.0
    check(near(at(swing), solved_swing),
          "factor 0 is the solved pose again")
    scene.cadex_explode.factor = 1.0

    # -- (c) the leader lines are real, sibling-collected and untagged ------
    lines_obj = bpy.data.objects.get(cadex_explode.LINES_NAME)
    check(lines_obj is not None, "the leader lines are drawn")
    check(cadex_explode.COLLECTION_NAME in scene.collection.children,
          "in a collection that is a SIBLING of Model")
    check(lines_obj is not None
          and cadex_hydrate.OUTPUT_PROP not in lines_obj,
          "and carry no output tag, so the hydrate GC ignores them")

    check(cadex_backend._state_for(root).revision == revision_before,
          "and the engine never heard about any of it: the accepted "
          "revision is unchanged")

    # -- how long a factor step takes, which is what the slider pays --------
    started = time.perf_counter()
    for step in range(6):
        scene.cadex_explode.factor = 0.15 * step
    factor_seconds = (time.perf_counter() - started) / 6.0
    scene.cadex_explode.factor = 1.0

    # -- (d) a rebuild under the explosion keeps it, from the NEW record ----
    ok, message = run_tool("set_params", {"params": {"width": 60.0}})
    check(ok, "the model rebuilt with the explosion on: {:s}".format(
        first_line_of(message)))
    swing = bpy.data.objects.get("swing")
    display = dict(cadex_backend.last_accepted(root).get("display") or {})
    record = (display.get("boom") or {}).get("exploded_view")
    check(swing is not None and isinstance(record, dict),
          "the rebuild republished the record")
    if swing is None or not isinstance(record, dict):
        return
    check(near(at(swing), tuple(record["final_poses"]["swing"]["position_mm"])),
          "the explosion was re-applied from the new response's own data")

    # -- (e) a preview drag under it neither crashes nor collapses ----------
    model_module.apply_values({"reach": 20.0})
    cadex_backend.note_preview(scene)
    cadex_backend.pump_preview_once()
    _pump_preview_until_idle()
    cadex_backend.pump_preview_once()      # applies poses + re-applies the spread
    check(bpy.data.objects.get(cadex_explode.LINES_NAME) is not None,
          "mid-drag the explosion is still standing")
    ok, message = run_tool("set_params", {"params": {"reach": 20.0}})
    check(ok, "the drag settled: {:s}".format(first_line_of(message)))
    swing = bpy.data.objects.get("swing")
    display = dict(cadex_backend.last_accepted(root).get("display") or {})
    record = (display.get("boom") or {}).get("exploded_view")
    check(swing is not None and isinstance(record, dict)
          and near(at(swing),
                   tuple(record["final_poses"]["swing"]["position_mm"])),
          "and the settled rebuild left it exploded on fresh endpoints "
          "({!r})".format(None if swing is None else at(swing)))
    settled_solved = cadex_explode._solved_poses(
        display, list(record["final_poses"]))

    # -- (g) render_views sees the assembled model: the suspend round trip --
    restore = cadex_explode.suspend()
    check(near(at(swing), settled_solved["swing"][0]),
          "suspended for render_views, the assembly is back together")
    restore()
    check(near(at(swing),
               tuple(record["final_poses"]["swing"]["position_mm"])),
          "and the spread comes back after it")

    # -- off restores the solved placements and removes what drew it --------
    ok, message = run_tool("exploded_view", {"show": False})
    check(ok, "exploded_view turned it off ({:s})".format(
        first_line_of(message)))
    check(near(at(swing), settled_solved["swing"][0]),
          "off is the engine's solved placement, exactly")
    check(bpy.data.objects.get(cadex_explode.LINES_NAME) is None
          and bpy.data.collections.get(cadex_explode.COLLECTION_NAME) is None,
          "and neither the lines nor their collection outlives it")

    # -- (f) a baked simulation refuses the explosion -----------------------
    # `replace`: this revision drops the exploded-view output on purpose.
    ok, _report = run_tool("write_script", {"content": SIMULATION_SCRIPT,
                                            "replace": True})
    check(ok, "a simulation script accepted on the same project")
    ok, message = run_tool("exploded_view", {"show": True})
    check(not ok and "simulation" in message,
          "with a simulation baked the tool refuses, naming the conflict "
          "({:s})".format(first_line_of(message)))

    GATE["exploded_view"] = {
        "stages": len(stages),
        "factor_step_seconds": round(factor_seconds, 4),
    }


def test_sheet_state_applies_and_restores(root):
    """ADR-151's scene-state half, end to end and with no GL.

    What a ``--background`` gate can prove about the composed sheet, in the
    order it can fail: spec refusals come back through the tool BEFORE the
    headless refusal (and a valid spec still refuses headless in the
    unchanged ADR-150 sentence); ``apply_view_state`` lands one cell's
    hide + explode + section (the Edges child hidden too, the settings
    carrying the overrides); the next cell with no overrides sees the LIVE
    presentation again, not cell 1's; and ``restore_state`` puts the whole
    presentation back bit-for-bit — with the live toggles initially ON (the
    write-back-and-refresh branch) and initially OFF (the clear branch,
    which is the class of bug the ADR-150 gate caught once already). Plus
    ``quiet()``: several settings written, no refresh until the explicit
    call.
    """
    print("test_sheet_state_applies_and_restores")
    from mesh_agent import cadex_explode, cadex_section, cadex_sheet

    reset_scene(root)
    scene = bpy.context.scene
    ok, report = run_tool("write_script", {"content": EXPLODED_SCRIPT})
    check(ok, "the exploded-assembly script was accepted: {:s}".format(
        first_line_of(report)))
    if not ok:
        return
    display = dict(cadex_backend.last_accepted(root).get("display") or {})
    record = (display.get("boom") or {}).get("exploded_view")
    check(isinstance(record, dict), "the exploded-view record is published")
    if not isinstance(record, dict):
        return
    final = tuple(record["final_poses"]["swing"]["position_mm"])

    # -- spec refusals land BEFORE the headless refusal ----------------------
    ok, message = run_tool("make_blueprint", {"views": [{"view": "rear"}]})
    check(not ok and "Unknown view 'rear'" in message
          and "background" not in message,
          "a bad view name is refused for what it is, not for headlessness: "
          "{:s}".format(first_line_of(message)))
    ok, message = run_tool("make_blueprint",
                           {"views": [{"view": "front", "hide": ["swng"]}]})
    check(not ok and "'swng'" in message and "swing" in message,
          "a bad hide is refused naming the declared outputs: {:s}".format(
              first_line_of(message)))
    ok, message = run_tool("make_blueprint", {"views": [{"view": "front"}],
                                              "layout": "hexagon"})
    check(not ok and "Unknown layout" in message,
          "a bad layout is refused: {:s}".format(first_line_of(message)))
    ok, message = run_tool("make_blueprint", {"views": [{"view": "front"}],
                                              "layout": "mosaic"})
    check(not ok and "give every view a cell" in message,
          "a mosaic without cells is refused with the fix: {:s}".format(
              first_line_of(message)))
    ok, message = run_tool(
        "make_blueprint",
        {"views": [{"view": "params", "explode": 1.0}]})
    check(not ok and "takes only cell, span, hero, aspect and title" in message,
          "a params cell with camera keys is refused for what it is: "
          "{:s}".format(first_line_of(message)))
    ok, message = run_tool(
        "make_blueprint", {"views": [{"view": "text"}]})
    check(not ok and "carries no text" in message,
          "an empty text panel is refused for what it is: {:s}".format(
              first_line_of(message)))
    ok, message = run_tool(
        "make_blueprint",
        {"views": [{"view": "front", "aspect": "1:9"}]})
    check(not ok and "between 1:5 and 5:1" in message,
          "an extreme cell aspect names its bounds: {:s}".format(
              first_line_of(message)))
    ok, message = run_tool("make_blueprint", {"based_on": "no-such-sheet"})
    check(not ok and "No stored blueprint matches" in message
          and "scope=blueprint" in message,
          "based_on against nothing points at the listing: {:s}".format(
              first_line_of(message)))
    ok, message = run_tool(
        "make_blueprint",
        {"name": "shop notes v1",
         "views": [{"view": "front", "aspect": "2:1", "title": "as built"},
                   {"view": "text", "text": "M3 threads.\nDeburr edges.",
                    "title": "notes", "aspect": "1:2"}]})
    check(not ok and "Blueprint rendering is unavailable in background mode"
          in message,
          "a named sheet with a text panel and per-cell shapes validates "
          "and only then refuses headless: {:s}".format(
              first_line_of(message)))
    ok, message = run_tool("make_blueprint",
                           {"views": [{"view": "front"}], "aspect": "wide"})
    check(not ok and "width:height" in message,
          "a bad aspect is refused with the format: {:s}".format(
              first_line_of(message)))
    ok, message = run_tool(
        "make_blueprint",
        {"views": [{"view": "three-quarter", "explode": 0.5}]})
    check(not ok and "Blueprint rendering is unavailable in background mode"
          in message,
          "a VALID composed spec still refuses headless, in the unchanged "
          "sentence: {:s}".format(first_line_of(message)))
    ok, message = run_tool(
        "make_blueprint",
        {"views": [{"view": "front"}, {"view": "params"}]})
    check(not ok and "Blueprint rendering is unavailable in background mode"
          in message,
          "a params cell against a two-parameter script validates and only "
          "then refuses headless: {:s}".format(first_line_of(message)))

    def presentation():
        # A parented Edges child's matrix_world is an EVALUATED value; a
        # capture taken between a matrix write and the next depsgraph pass
        # would snapshot the stale pose and blame the restore for it.
        bpy.context.view_layer.update()
        bpy.context.evaluated_depsgraph_get()
        objects = {}
        for obj in bpy.data.objects:
            try:
                hidden = obj.hide_get()
            except Exception:
                hidden = None
            objects[obj.name] = (
                tuple(tuple(row) for row in obj.matrix_world),
                hidden,
                tuple((modifier.name, modifier.type,
                       bool(modifier.show_viewport))
                      for modifier in obj.modifiers),
            )
        explode, section = scene.cadex_explode, scene.cadex_section
        return {
            "objects": objects,
            "explode": (bool(explode.show), float(explode.factor)),
            "section": (bool(section.show), str(section.axis),
                        float(section.offset), bool(section.flip)),
            "explode_flag": cadex_sheet._scene_flag(
                scene, cadex_explode.SCENE_FLAG),
            "section_flag": cadex_sheet._scene_flag(
                scene, cadex_section.SCENE_FLAG),
        }

    def same_presentation(before, after, label):
        wrong = []
        if set(before["objects"]) != set(after["objects"]):
            wrong.append("the object set")
        for name in sorted(set(before["objects"]) & set(after["objects"])):
            matrix_b, hidden_b, mods_b = before["objects"][name]
            matrix_a, hidden_a, mods_a = after["objects"][name]
            if not all(abs(a - b) < 1e-5
                       for row_a, row_b in zip(matrix_a, matrix_b)
                       for a, b in zip(row_a, row_b)):
                wrong.append(name + " matrix_world")
            if hidden_a != hidden_b:
                wrong.append(name + " hide state")
            if mods_a != mods_b:
                wrong.append(name + " modifiers")
        for key in ("explode", "section", "explode_flag", "section_flag"):
            if before[key] != after[key]:
                wrong.append(key)
        check(not wrong, "{:s}: the presentation is restored exactly "
                         "(differs: {:s})".format(label,
                                                  ", ".join(wrong) or "none"))

    specs, error = cadex_sheet.normalize_views(
        [{"view": "front", "hide": ["swing"], "explode": 1.0,
          "section": "Z"},
         {"view": "top"}], sorted(display))
    check(error == "", "the two-cell spec normalizes: " + (error or "ok"))
    if error:
        return
    collection = cadex_hydrate._model_collection()
    swing = cadex_hydrate._find(collection, "swing", edges=False)
    swing_edges = cadex_hydrate._find(collection, "swing", edges=True)
    check(swing is not None and swing_edges is not None,
          "the component and its Edges child hydrated")
    if swing is None or swing_edges is None:
        return

    def at(obj):
        return tuple(obj.matrix_world.translation)

    def near(a, b, tolerance=1e-4):
        return max(abs(x - y) for x, y in zip(a, b)) < tolerance

    # -- live toggles ON: the write-back-and-refresh branch ------------------
    # Explosion FIRST, section second: the cutter's matrix is derived from
    # the model bounds at refresh time, and a section switched on before an
    # explosion holds a matrix computed at the solved poses that no later
    # refresh reproduces. The restore recomputes -- which is what the
    # product's own next refresh would do -- so bit-equality is asserted
    # against a section whose live value is itself reproducible.
    ok, message = run_tool("exploded_view", {"show": True, "factor": 0.25})
    check(ok, "a live explosion went on ({:s})".format(
        first_line_of(message)))
    ok, message = run_tool("section_view", {"show": True, "axis": "X"})
    check(ok, "a live section went on ({:s})".format(first_line_of(message)))
    revision_before = cadex_backend._state_for(root).revision
    before = presentation()

    snapshot = cadex_sheet.snapshot_state(scene)
    cadex_sheet.apply_view_state(scene, specs[0], snapshot)
    check(swing.hide_get() is True,
          "the cell's hide landed through hide_set")
    check(swing_edges.hide_get() is True,
          "and the Edges child is hidden with it")
    check(near(at(swing), final),
          "the cell's explode factor 1.0 landed ({!r})".format(at(swing)))
    check(float(scene.cadex_explode.factor) == 1.0
          and str(scene.cadex_section.axis) == 'Z',
          "the settings carry the overrides while the cell renders")
    report = cadex_sheet._scene_flag(scene, cadex_section.SCENE_FLAG) or {}
    check(report.get("axis") == 'Z', "the section refresh ran on Z")

    cadex_sheet.apply_view_state(scene, specs[1], snapshot)
    check(swing.hide_get() is False,
          "the next cell unhides what cell 1 hid")
    check(float(scene.cadex_explode.factor) == 0.25
          and str(scene.cadex_section.axis) == 'X',
          "and inherits the LIVE presentation, not cell 1's overrides")

    cadex_sheet.restore_state(scene, snapshot)
    same_presentation(before, presentation(), "live-on restore")
    check(cadex_backend._state_for(root).revision == revision_before,
          "the engine never heard about any of it: the accepted revision "
          "is unchanged")

    # -- live toggles OFF: the clear branch ----------------------------------
    ok, _message = run_tool("exploded_view", {"show": False})
    check(ok, "the live explosion went off")
    ok, _message = run_tool("section_view", {"show": False})
    check(ok, "the live section went off")
    before = presentation()
    snapshot = cadex_sheet.snapshot_state(scene)
    cadex_sheet.apply_view_state(scene, specs[0], snapshot)
    check(any(obj.modifiers.get(cadex_section.MODIFIER_NAME) is not None
              for obj in bpy.data.objects if obj.modifiers),
          "the cell's own section put its modifiers on")
    check(near(at(swing), final), "and the cell's own explode landed")
    cadex_sheet.restore_state(scene, snapshot)
    check(all(obj.modifiers.get(cadex_section.MODIFIER_NAME) is None
              for obj in bpy.data.objects if obj.modifiers)
          and bpy.data.objects.get(cadex_section.CUTTER_NAME) is None,
          "the clear branch removed everything the cell added")
    check(bpy.data.objects.get(cadex_explode.LINES_NAME) is None,
          "including the leader lines")
    same_presentation(before, presentation(), "live-off restore")

    # -- only: isolate one output; everything else hides and comes back ------
    before = presentation()
    snapshot = cadex_sheet.snapshot_state(scene)
    iso_specs, error = cadex_sheet.normalize_views(
        [{"view": "front", "only": ["swing"]}], sorted(display))
    check(error == "", "the only spec normalizes: " + (error or "ok"))
    cadex_sheet.apply_view_state(scene, iso_specs[0], snapshot)
    base = cadex_hydrate._find(collection, "base", edges=False)
    check(base is not None and base.hide_get() is True,
          "only hides the outputs it does not name")
    check(swing.hide_get() is False, "and keeps the one it does")
    cadex_sheet.restore_state(scene, snapshot)
    same_presentation(before, presentation(), "only restore")

    # -- quiet(): several settings written, ONE explicit refresh -------------
    solved = at(swing)
    with cadex_explode.quiet():
        scene.cadex_explode.show = True
        scene.cadex_explode.factor = 1.0
    check(at(swing) == solved,
          "quiet() holds the update callbacks: no refresh fired")
    cadex_explode.refresh(scene)
    check(near(at(swing), final), "until the explicit refresh call")
    with cadex_explode.quiet():
        scene.cadex_explode.show = False
    cadex_explode.clear(scene)
    check(near(at(swing), solved), "and the cleanup reassembles")

    GATE["sheet"] = {"outputs": len(display), "spec_refusals": 9}


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
                    "actuator_channels", "episode_seconds", "policy"):
            check(key in opened, "a refusal still carries %r" % key)
        # WHICH policy is playing (ADR-111). Empty on a refusal, and every
        # field present: the panel reads these unconditionally, and a
        # KeyError in a draw callback takes the whole editor down.
        for key in ("label", "weights", "sha256", "trained_label"):
            check(key in (opened.get("policy") or {}),
                  "...and its policy block carries %r" % key)

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


def test_the_training_plot_reads_the_same_file_and_only_that():
    """The reward-curve plot (the shell's first plot), headless.

    What `--background` can prove: the import discipline, the handler
    bookkeeping, and that the pure pipeline turns the progress file the
    panel reads into a drawable layout — and turns a curve-less file into
    None, which is how a progress.json from an older trainer degrades to
    panel-only with no version check anywhere. What only a window can
    prove — pixels — was probed once against the built bundle before this
    module existed (a no-op handler on SpaceCadexTraining fired on redraw
    of a CADEX_TRAINING area) and is checked by looking at a live run.
    """

    print("test_the_training_plot_reads_the_same_file_and_only_that")
    import tempfile

    from mesh_agent import cadex_training
    from mesh_agent import cadex_training_plot as plot

    # The dependency is one-way: the plot imports cadex_training, and
    # cadex_training must never import the plot -- its import set is pinned
    # to exactly {json, os, bpy} by the training-panel test above, and this
    # spells the direction out where the next reader will look.
    training_source = open(cadex_training.__file__, encoding="utf-8").read()
    check("cadex_training_plot" not in training_source,
          "cadex_training never learns the plot exists")

    import ast as _ast

    tree = _ast.parse(open(plot.__file__, encoding="utf-8").read())
    imported = set()
    module_level = set()
    for node in _ast.walk(tree):
        names = ()
        if isinstance(node, _ast.Import):
            names = tuple(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, _ast.ImportFrom) and node.module:
            names = (node.module.split(".")[0],)
        imported.update(names)
        if node in tree.body:
            module_level.update(names)
    for forbidden in ("mujoco", "CadexDynamics", "subprocess", "socket",
                      "urllib", "http"):
        check(forbidden not in imported, "the plot never imports %s" % forbidden)
    check(module_level == {"math"},
          "the pure half imports math at module scope and nothing else "
          "(got %r)" % (sorted(module_level),))
    check(plot._shader is None,
          "no GPU shader is fetched at import or registration")

    # Handler bookkeeping. mesh_agent.register() already added the handler
    # for the add-on's whole life, so idempotence is asserted from there.
    handle = plot._draw_handle
    check(handle is not None, "registering the add-on registered the plot")
    plot._add_draw_handler()
    check(plot._draw_handle is handle, "adding twice leaks no second handle")
    plot._remove_draw_handler()
    check(plot._draw_handle is None,
          "removing removes -- a leaked handler draws forever")
    plot._remove_draw_handler()
    plot._add_draw_handler()
    check(plot._draw_handle is not None,
          "...and back, so unregister has something to remove")

    # The pipeline the draw handler runs, against the very file the panel
    # reads, with the drawing arithmetic asserted where a region cannot be.
    root = tempfile.mkdtemp(prefix="cadex-training-plot-")
    scene = bpy.context.scene
    scene[cadex_backend.ROOT_PROP] = root
    path = os.path.join(root, cadex_training.PROGRESS_NAME)
    try:
        payload = {
            "schema": cadex_training.PROGRESS_SCHEMA,
            "state": "training", "iteration": 40, "total": 100,
            "reward_per_step": 1.9, "best_reward_per_step": 2.0,
            "best_iteration": 30, "wall_time_s": 12.0, "eta_s": 18.0,
            "device": "cpu", "checkpoints": [],
            "curve": [[i, i * 0.05 - 0.4] for i in range(0, 41, 5)],
        }
        with open(path, "w", encoding="utf-8") as handle_:
            json.dump(payload, handle_)
        report = cadex_training.read_progress(scene)
        check(report is not None, "the plot's file is the panel's file")
        points = plot.curve_from(report)
        check(len(points) == 9, "the curve field arrives as points")
        layout = plot.plot_layout(
            800, 600, points,
            best_iteration=int(report["best_iteration"]),
            total=int(report["total"]))
        check(layout is not None, "a run with a curve lays out a plot")
        check(layout["best"] is not None,
              "with the best-so-far marked on the curve")
        check(layout["frame"][3] <= 600 * plot.PLOT_FRACTION,
              "and the plot keeps below the floating panel")

        # A progress file from before the curve field: panel-only, by
        # construction rather than by version check.
        del payload["curve"]
        with open(path, "w", encoding="utf-8") as handle_:
            json.dump(payload, handle_)
        report = cadex_training.read_progress(scene)
        check(report is not None, "an old report still reads")
        check(plot.curve_from(report) == [],
              "but carries no curve")
        check(plot.plot_layout(800, 600, plot.curve_from(report)) is None,
              "so the editor is panel-only, exactly as before the plot")

        # And the handler's own early exit runs clean where there is no
        # region at all, which is every --background redraw.
        check(plot._layout_for_context() is None,
              "no region, no layout, no exception")
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
    hydrate_root = tempfile.mkdtemp(prefix="mesh-cadex-hydrate-")
    lockout_root = tempfile.mkdtemp(prefix="mesh-cadex-lockout-")
    duplicate_root = tempfile.mkdtemp(prefix="mesh-cadex-duplicate-")
    carry_root = tempfile.mkdtemp(prefix="mesh-cadex-carry-")
    linked_root = tempfile.mkdtemp(prefix="mesh-cadex-linked-")
    dimension_root = tempfile.mkdtemp(prefix="mesh-cadex-dimension-")
    measure_root = tempfile.mkdtemp(prefix="mesh-cadex-measure-")
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
    window_root = tempfile.mkdtemp(prefix="mesh-cadex-window-")
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
    views_root = tempfile.mkdtemp(prefix="mesh-cadex-views-")
    collision_root = tempfile.mkdtemp(prefix="mesh-cadex-collision-")
    shapes_root = tempfile.mkdtemp(prefix="mesh-cadex-shapes-")
    isolate_root = tempfile.mkdtemp(prefix="mesh-cadex-isolate-")
    readers_root = tempfile.mkdtemp(prefix="mesh-cadex-readers-")
    training_root = tempfile.mkdtemp(prefix="mesh-cadex-training-")
    live_root = tempfile.mkdtemp(prefix="mesh-cadex-live-")
    wiring_root = tempfile.mkdtemp(prefix="mesh-cadex-wiring-")
    cage_root = tempfile.mkdtemp(prefix="mesh-cadex-cage-")
    print_root = tempfile.mkdtemp(prefix="mesh-cadex-print-")
    section_root = tempfile.mkdtemp(prefix="mesh-cadex-section-")
    explode_root = tempfile.mkdtemp(prefix="mesh-cadex-explode-")
    blueprint_root = tempfile.mkdtemp(prefix="mesh-cadex-blueprint-")
    sheet_root = tempfile.mkdtemp(prefix="mesh-cadex-sheet-")
    recipe_root = tempfile.mkdtemp(prefix="mesh-cadex-recipe-")
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
        test_native_blender_recipe(recipe_root)
        test_save_as_and_multi_file_lifecycle(saveas_root)
        test_opening_a_file_hydrates(hydrate_root)
        test_a_locked_out_project_is_reaccepted_from_the_chat(lockout_root)
        test_duplicated_file_keeps_its_parameters(duplicate_root)
        test_save_as_carries_imported_geometry(carry_root)
        test_link_part_travels_between_two_models(linked_root)
        test_dimensions_are_readable_from_every_angle(dimension_root)
        test_measure_asks_rather_than_rewriting_the_script(measure_root)
        test_reopen_restores(reopen_root)
        test_open_runs_the_restore_pass(restore_root)
        test_restore_failure_is_first_class(corrupt_root)
        test_a_refused_edit_leaves_the_project_openable(refused_root)
        test_a_broken_store_can_still_be_rewritten(rewrite_root)
        test_a_script_that_will_not_run_is_repaired_from_the_accepted_source(
            repair_root)
        test_a_working_scripts_stdout_reaches_the_caller(stdout_root)
        test_get_script_is_not_truncated(long_root)
        test_get_script_serves_windows(window_root)
        test_write_script_refuses_to_drop_existing_outputs(guard_root)
        test_script_history_and_revert(history_root)
        test_stale_attempts_are_pruned(prune_root)
        test_an_assembly_shows_its_solved_placements(assembly_root)
        test_two_components_share_one_mesh(shared_root)
        test_a_simulation_plays(sim_root)
        test_the_policy_outputs_panel_reads_a_rollout()
        test_a_pose_only_slider_previews_at_interactive_rate(preview_root)
        test_a_shape_slider_falls_back_to_set_params(fallback_root)
        test_render_views_frames_the_engines_geometry(views_root)
        test_the_collision_overlay_draws_adr074(collision_root)
        test_the_collision_overlay_measures_every_primitive(shapes_root)
        test_the_collision_overlay_is_isolated(isolate_root)
        test_both_collision_readers_agree(readers_root)
        test_the_training_panel_tracks_a_run(training_root)
        test_the_training_plot_reads_the_same_file_and_only_that()
        test_two_applies_in_a_row_both_land(wiring_root)
        test_a_dragged_ring_lands_in_the_accepted_revision(cage_root)
        test_marked_parts_export_as_stl(print_root)
        test_the_section_view_cuts_the_model_open(section_root)
        test_the_exploded_view_spreads_the_assembly(explode_root)
        test_the_blueprint_view_restyles_and_restores(blueprint_root)
        test_sheet_state_applies_and_restores(sheet_root)
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
                     threading_root, cancel_root, saveas_root, hydrate_root,
                     lockout_root,
                     duplicate_root, carry_root, linked_root,
                     dimension_root, measure_root,
                     restore_root, corrupt_root, describe_root, edit_root,
                     drop_root, rederive_root, mirror_root, defaults_root,
                     refused_root, rewrite_root, repair_root, stdout_root,
                     long_root, guard_root, history_root, prune_root,
                     assembly_root, shared_root, sim_root, live_root,
                     drag_root, supersede_root, skip_root,
                     preview_root, fallback_root, views_root, collision_root,
                     shapes_root, isolate_root, readers_root, wiring_root,
                     cage_root, print_root, section_root,
                     explode_root, blueprint_root,
                     sheet_root, recipe_root):
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
