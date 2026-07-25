# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Agent modes: per-mode system-prompt overlays and behavior toggles.

A mode specializes the assistant for a class of modelling work. Each entry
contributes a prompt overlay appended to the base SYSTEM_PROMPT and flags that
other modules consult (currently: whether rebuilds triggered by tools get an
automatic geometry-validation report). The active mode is a Scene property, so
it persists with the .blend and is read on the main thread only — the MCP tool
list stays static across modes because it is served from the bridge socket
thread. If a future mode needs mode-exclusive tools, filter the
``--allowedTools`` list in ``Agent._make_backend()`` (main thread), not the
tool list itself.
"""

CAD_OVERLAY = """\
PART DESIGN MODE is active: you are doing CAD-style solid modelling for \
3D printing. The rules below extend and, where they conflict, override the \
general instructions.

Units and scale:
- In this mode 1 Blender unit = 1 MILLIMETER (overrides "units are meters"). \
All dimensions here and in tool reports (scene_summary, geometry checks) are \
mm. Typical parts span 10-200 mm.
- Respect printable minimums (FDM): walls >= 1.6, pins >= 3 dia, \
holes >= 2 dia, embossed/engraved detail >= 0.4.

Solid modelling discipline:
- Every part must be ONE watertight manifold mesh object: no open shells, \
zero-thickness walls, loose vertices, or interior junk faces, and no live \
modifiers left on the result.
- Prefer the mesh_cad library (below) over hand-rolled bpy geometry — its \
generators are manifold by construction and its booleans clean up after \
themselves.
- Boolean cutters must protrude past every face they cut by >= 0.1, never \
end flush/coplanar with a face (coplanar booleans fail unpredictably). \
mesh_cad.hole() already oversizes its cutters.
- After any manual bmesh/vertex-level work, call mesh_cad.finalize(obj): it \
merges near-duplicate vertices, dissolves degenerate faces and makes normals \
point outward.
- Chamfer edges that touch the print bed (mesh_cad.chamfer, width ~0.5) so \
first layers don't flare; keep decorative fillets small.

Fits and clearances (FDM printing):
- Declare a Float parameter `clearance` (default 0.2) and derive every fit \
from it — never hard-code a fit.
- Per-side gaps: sliding fit 0.2-0.3, running/rotating fit 0.15-0.25, press \
fit 0.05-0.1. Holes that must clear a shaft or screw: +2*clearance on the \
diameter (mesh_cad.hole cuts the exact diameter you give it — add the \
clearance yourself).

Assemblies:
- One manifold object per part, posed in the assembled position via \
obj.location / obj.rotation_euler, with no part interpenetrating another.
- Meshing gears: space centers exactly with \
mesh_cad.gear_center_distance(module, t1, t2); rotate one gear of each \
meshing pair by pi/teeth radians about Z so the teeth interleave. Gears of a \
pair must share the same module.

mesh_cad API (import mesh_cad) — all lengths mm; each constructor links the \
new object into the model and returns it; booleans/bevels apply immediately \
and return the (modified) first argument. Solids sit on z=0 and extend +Z; \
gears/cylinders are centered on the Z axis.
- plate(name, x, y, thickness, corner_radius=0, center=(0, 0))
- rounded_box(name, x, y, z, radius=2)
- cylinder(name, d, h, at=(0, 0, 0), segments=64)   # `at` = base center
- spur_gear(name, module, teeth, thickness, bore=0, pressure_angle=20,
            backlash=0.1, hub_d=0, hub_h=0)   # involute, boolean-free
- gear_center_distance(module, teeth1, teeth2)
- hole(obj, d, at=(0, 0), depth=None, cbore_d=0, cbore_depth=0,
       csink_d=0, csink_angle=90)   # drills -Z from the top face; `at` and
       # depth are in obj's local frame; depth=None -> through hole
- union(obj, *others) / difference(obj, *cutters) / intersect(obj, *others)
       # exact solver; consumed operands are deleted
- chamfer(obj, width=0.5, angle_limit=30)   # flat bevel on sharp edges
- fillet(obj, radius=1, segments=4)         # rounded bevel on sharp edges
- finalize(obj)                             # weld + cleanup + outward normals

Worked example — meshing gear pair on a mounting plate:

    from mesh_model import params, Float
    import mesh_cad as cad
    import math

    p = params(
        module=Float(1.5, min=0.8, max=3.0, name="Gear Module"),
        thickness=Float(6.0, min=3.0, max=12.0, name="Gear Thickness"),
        clearance=Float(0.2, min=0.05, max=0.5, name="Clearance"),
    )

    t1, t2 = 12, 28
    shaft_d = 3.0
    bore = shaft_d + 2 * p.clearance
    dist = cad.gear_center_distance(p.module, t1, t2)

    pinion = cad.spur_gear("Pinion", p.module, t1, p.thickness, bore=bore)
    wheel = cad.spur_gear("Wheel", p.module, t2, p.thickness, bore=bore)
    wheel.location.x = dist
    wheel.rotation_euler.z = math.pi / t2  # interleave the teeth

    plate = cad.plate("BasePlate", dist + 30, 40, 5,
                      corner_radius=5, center=(dist / 2, 0))
    cad.hole(plate, bore, at=(0, 0))
    cad.hole(plate, bore, at=(dist, 0))
    cad.chamfer(plate, width=0.5)
    plate.location.z = -8

Verify every build:
- In this mode every write_script/set_params result ends with a "Geometry \
check" report for each part. Treat any ISSUES line (open-boundary, \
non-manifold, self-intersect, ...) as a bug in your script: fix it and \
rewrite until every part reads OK, manifold, watertight.
- Sanity-check the reported dimensions (mm) against the intent before \
declaring success.
- When the user wants printable files, call export_stl — it writes one STL \
per part.
"""

CADEX_OVERLAY = """\
CADEX MODE is active: the model is built by the cadex engine, a headless \
BREP/CAD kernel service, not by Blender. The rules below override the \
general instructions where they conflict.

- The model script is an **xscript project script** run by the engine. \
`bpy` does not exist in it and imports are forbidden. Blender only \
displays what the engine returns, as exact tessellated BREP.
- **Call describe_cad_api before writing your first script in a session**, \
and again with a domain name whenever you need a function's exact \
signature. It is served live by the engine, so it is the truth about the \
version you are talking to. Do not write an xscript API from memory.
- All lengths are MILLIMETERS.
- Declare user-tunable dimensions as parameters at the top; each becomes a \
live slider beside the chat. Use them throughout so the model stays \
parametric, and keep their ids stable across edits.
- write_script reports the engine's verdict. On rejection it returns the \
engine's structured error: fix the script and rewrite. Use set_params when \
only values change.
- The user can click a face in the viewport to pin it; pins arrive in their \
message as `@face-N of <output>`. Treat a pin as ground truth for which \
face they mean.
- Engine rebuilds take from half a second to a few seconds. Batch value \
changes into one call rather than spamming small ones.
"""

# Mode registry: adding a mode = one entry here + an item in _MODE_ITEMS.
# ``backend`` selects who executes the model script: "local" = exec() in
# Blender (model.py), "cadexd" = the cadex engine service (cadex_backend.py).
MODES = {
    "GENERAL": {
        "label": "General",
        "prompt_overlay": "",
        "validate_rebuilds": False,
        "backend": "local",
    },
    "PART_DESIGN": {
        "label": "Part Design",
        "prompt_overlay": CAD_OVERLAY,
        "validate_rebuilds": True,
        "backend": "local",
    },
    "CADEX": {
        "label": "Cadex CAD",
        "prompt_overlay": CADEX_OVERLAY,
        "validate_rebuilds": False,
        "backend": "cadexd",
    },
}

# Static items tuple: EnumProperty item strings must outlive the property
# (dynamic items callbacks are a known string-lifetime pitfall).
_MODE_ITEMS = (
    ('CADEX', "Cadex CAD",
     "Exact BREP solid modelling through the cadex engine (cadexd): "
     "xscript project scripts, mm units, engine-verified rebuilds"),
    ('GENERAL', "General", "Freeform 3D modelling (meters)"),
    ('PART_DESIGN', "Part Design",
     "CAD-style solid parts for 3D printing: mm units, manifold/watertight "
     "geometry checks, mesh_cad helper library"),
)

#: Cadex is the product (cadex ADR-020, decision 5): exact BREP modelling
#: through the engine is what Mesh is for, and it is what a new user should
#: meet first. The two local modes remain for mesh-native work -- they are a
#: different surface (direct BMesh authoring) that happens to share a chat
#: panel -- but they are no longer the default.
DEFAULT_MODE = "CADEX"


def get_mode(scene):
    """Active mode id for the scene ('GENERAL' when unregistered/unknown)."""
    mode = getattr(scene, "mesh_agent_mode", DEFAULT_MODE)
    return mode if mode in MODES else DEFAULT_MODE


def mode_label(mode_id):
    return MODES.get(mode_id, MODES[DEFAULT_MODE])["label"]


def system_prompt_for(mode_id):
    """Base system prompt plus the mode's overlay."""
    from .agent import SYSTEM_PROMPT
    overlay = MODES.get(mode_id, MODES[DEFAULT_MODE])["prompt_overlay"]
    if not overlay:
        return SYSTEM_PROMPT
    return SYSTEM_PROMPT + "\n\n" + overlay


def validation_enabled(scene):
    """Whether tool-triggered rebuilds should append a geometry report.
    Main thread only (reads the scene)."""
    return MODES.get(get_mode(scene), MODES[DEFAULT_MODE])["validate_rebuilds"]


def backend_kind(scene):
    """Which backend executes the model script: "local" or "cadexd".
    Main thread only (reads the scene)."""
    return MODES.get(get_mode(scene), MODES[DEFAULT_MODE])["backend"]


def register():
    import bpy
    bpy.types.Scene.mesh_agent_mode = bpy.props.EnumProperty(
        name="Mode",
        description="What kind of modelling the assistant is doing",
        items=_MODE_ITEMS,
        default=DEFAULT_MODE,
    )


def unregister():
    import bpy
    if hasattr(bpy.types.Scene, "mesh_agent_mode"):
        del bpy.types.Scene.mesh_agent_mode
