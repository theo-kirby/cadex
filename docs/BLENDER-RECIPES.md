# Native Blender recipes in xscript

Verified against source: 2026-09-05

[Cadex-new] ADR-185. `mesh.blender` is an opt-in mesh operation in the one
project script. It uses native Blender Python without giving the live scene
a second authoring path. Exact CAD stays exact; organic output stays a mesh.

## Authoring

```python
p = params(width=num(40, unit="mm", min=20, max=70, step=1))
mount = part.box(p.width, 20, 4)
skin = mesh.blender('''
result = inputs["mount"]
bevel = result.modifiers.new("round", 'BEVEL')
bevel.width = values["radius"]
bevel.segments = 4
''', version="5.3.0", inputs={"mount": mesh.from_shape(mount)},
    values={"radius": 1.5})
result = {"mount": mount, "skin": skin, "check": mesh.check(skin)}
```

The inner recipe may import `bpy`, `bmesh`, `mathutils` and Python libraries.
The outer xscript import policy is unchanged. `inputs` maps up to 32 public
identifier names to Blender mesh objects; each input comes from an xscript
mesh value. Use `mesh.from_shape` explicitly for CAD tessellation quality.
`values` is a finite JSON dictionary (up to 64 KiB), suitable for dimensions,
named frames and other metadata. The source is limited to 64 KiB.

Assign one mesh Object to `result`. Its evaluated modifiers and world matrix
are baked into triangles; negatively scaled objects have their winding
corrected. One coordinate unit is one millimetre. The worker starts with an
empty object collection at frame 1, independent of the live scene, startup
files, selection and user preferences. Prefer data/BMesh APIs; operators
requiring a window or editor context may fail in background mode. Geometry
Nodes instances must be realized before mesh export.

One call returns one mesh. Chain calls through named inputs when one result
feeds another. Keep quad-cage construction, modifiers and node construction
in the recipe: evaluated triangles do not retain their edit history. UVs,
materials, animation, external file reads and live modifier stacks are not
outputs of this first surface. External geometry enters through project
assets and named mesh inputs.

`examples/blender_enclosure.py` is a complete hybrid project: CAD mounting
rails, a declared CAD clearance tool, and a rounded Blender shell with wall
thickness and an opening. Shared spacing, length, height and wall sliders
rebuild the relevant geometry. This is a mechanism-envelope benchmark, not a
claim that the older wolf benchmark was rebuilt or visually improved.

## Runtime, identity and failure

The shell supplies its own executable to its cadexd child. Headless clients
set `CADEX_BLENDER_EXECUTABLE` to an absolute Blender/Cadex executable path.
Ordinary engine-only projects require no Blender installation. The numeric
`version` argument is mandatory and checked against `bpy.app.version` before
recipe execution; `5.3.0` also identifies the numeric version of this tree's
5.3 development build. Python and NumPy RNGs are seeded by `seed` (default 0).
Stochastic modifiers/nodes need explicit seeds in their own settings too.

The evaluator hashes the executable bytes and its own worker source, and
hashes that identity together with the recipe definition and actual canonical
vertices **and triangles**. This catches winding/connectivity changes that a
vertex-set fingerprint would miss. It does not assert cross-version or
arbitrary-script determinism. Dependency-library changes can change geometry
without changing the executable hash; actual output geometry is hashed too.
Reopening recomputes and compares against the accepted project digest. A
mismatch refuses restoration through the existing project lifecycle.

Identical calls within one attempt reuse a validated result outside the
child's writable workspace. There is no cross-attempt geometry cache: a
rebuild really runs the recipe. Source, values and accepted mesh artifacts
remain in the normal project store, so save/reopen and history restoration
need no `.blend` scene state. Slider changes, failures and undo use the same
revision guard, acceptance transaction and source rollback as every mesh op.

Blender-derived trees are refused by `part.shape_from_mesh` and exact CAD
routing-obstacle consumers. They can feed further mesh operations or checks,
and publish beside CAD parts. Mesh-to-BREP remains faceted conversion of a
fixed asset, not analytic reconstruction. Check final manufacturing geometry
for fit, thickness, clearance and closedness; CAD-derived cutters do not make
the resulting mesh an exact CAD solid.

## Execution boundary

The engine stages `cadex_blender_runner.py` and `cadex_blender_worker.py` by
filename. Neither enters cadexd's import closure; only the Blender process
imports `bpy`. These are newly authored LGPL adapters, with no copied shell
implementation. There is no new protocol operation or output kind.

macOS uses `sandbox-exec`; Linux requires bubblewrap with private namespaces.
Unsupported platforms or unavailable sandboxes refuse execution. No fallback
runs recipe code unsandboxed. The child reads its runtime, system libraries,
the worker and one input file, and writes only its scratch directory. It
receives a closed environment, no user home or credentials, and no network.
The worker has a 90-second wall budget, 80-second CPU budget, 2-GiB monitored
resident-memory budget and a 64-MiB per-file/output limit. The enclosing
project's budget still applies. Output is limited to 250,000 triangles;
finite coordinates, valid indices and nonzero triangle area are independently
checked before the FreeCAD mesh kernel receives the result. Open surfaces
are allowed; `mesh.check` reports manufacturing soundness separately.

The subprocess shares the project worker's process group so cancellation
terminates both; the parent process runner also kills surviving descendants.
The published model remains the last accepted model when the recipe fails.

## Verification

Native execution and application integration are verified on macOS. The Linux
bubblewrap launcher requires validation on a Linux host; Windows currently
refuses this operation. This does not limit ordinary engine-only projects.

Run the engine suite with `CADEX_BLENDER_EXECUTABLE` set to exercise the real
worker tests in `cadex_tests/test_blender_recipe.py`. Without it, native tests
skip explicitly and API/validation tests still run. Native tests cover fresh
rebuild equality, inputs, modifiers, units, version refusal, host-file/network
denial, timeout and the hybrid project's rebuild/rollback/reopen lifecycle.
