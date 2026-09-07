"""ADR-235: qualify the proposed planetary mesh using the committed spur generator.

Run from the repo root (no planetary API or uncommitted patch required):
  build/release/bin/FreeCADCmd -c 'exec(open("docs/experiments/planetary_mesh_probe.py").read())'

A failed mesh is an expected experiment result, printed as qualified=false.
This is a geometric probe, not a public mechanism or a strength qualification.
"""
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path("src/Mod/cadex").resolve()))
import FreeCAD as App
from CadexCatalog import gear_spec
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from cadex_domain_api import create_domain_api
from cadex_library_api import create_library_api, _spur_gear_outline
from cadex_part_worker import build_part_shape

pack = XSCRIPT_WORKBENCH_PACKS["PartWorkbench"]
part = create_domain_api(pack.domain, pack.api_exports, pack.output_types)
lib = create_library_api(part)

# m1, z_s=18, z_p=18, z_r=54; three equally spaced planets satisfy
# (sun+ring) % planets == 0. Test the first pair at sun phase zero.
# A virtual external gear cuts the internal tooth spaces. Its root is the
# ring tip (26 mm), its tip the ring root (28.25 mm), on the same base circle.
virtual = gear_spec(1, 54)
virtual.update(root_diameter_mm=52.0, tip_diameter_mm=56.5)
outline = [(x, y, -1.0) for x, y, _ in _spur_gear_outline(virtual)]
spaces = part.extrude(part.face(part.wire(outline, closed=True)), (0, 0, 8))
ring_recipe = part.cut(part.cylinder(30.25, 6), spaces)
ring = build_part_shape(ring_recipe.to_payload())
ring.rotate(App.Vector(), App.Vector(0, 0, 1), 180 * 17 / 54)
sun = build_part_shape(lib.spur_gear(1, 18, 6).body.to_payload())
planet = build_part_shape(lib.spur_gear(1, 18, 6, origin=(18, 0, 0),
                                      roll_degrees=170).body.to_payload())
assert all(s.isValid() and len(s.Solids) == 1 for s in (sun, planet, ring))

# Circle clearances measured from the generated solids, not API metadata.
sun_r = [math.hypot(v.X, v.Y) for v in sun.Vertexes]
planet_r = [math.hypot(v.X - 18, v.Y) for v in planet.Vertexes]
ring_r = [math.hypot(v.X, v.Y) for v in ring.Vertexes
          if math.hypot(v.X, v.Y) < 30]
clearances = [18 - max(sun_r) - min(planet_r),
              18 - min(sun_r) - max(planet_r),
              max(ring_r) - 18 - max(planet_r),
              min(ring_r) - 18 - min(planet_r)]
assert all(abs(c - 0.25) < 1e-7 for c in clearances), clearances
commons = [sun.common(planet).Volume, planet.common(ring).Volume]
gaps = [sun.distToShape(planet)[0], planet.distToShape(ring)[0]]
# A half-tooth-pitch error must register as a collision in both meshes.
bad = planet.copy()
bad.rotate(App.Vector(18, 0, 0), App.Vector(0, 0, 1), 10)
controls = [sun.common(bad).Volume, bad.common(ring).Volume]
assert min(controls) > 1, controls
print("PLANETARY-PROBE " + json.dumps({
    "sun_phase_degrees": 0, "sun_planet_and_planet_ring_common_mm3": commons,
    "flank_gap_mm": gaps, "root_circle_clearances_mm": clearances,
    "half_pitch_control_common_mm3": controls,
    "tolerance_mm3": 1e-6, "qualified": max(commons) < 1e-6,
}), flush=True)
