# Named-plane section evidence

Verified against source: 2026-09-08. [Cadex-new]. ADR-240.

`section.svg` and `summary.json` are actual outputs of the real-engine regression
`test_real_cavity_pose_offsets_and_tracked_artifacts` in
`cli/tests/test_section.py`. Its literal script builds a 20×20×10 mm block with
a radius-4 through hole, rotates it 90 degrees around Z and translates it by
(30,40,5). It runs the public `script` and `section --plane XY --offset-mm 8`
commands against a fresh project; the regression checks accepted revision and
digest, placed bounds (10,40,5)..(30,60,15), two closed contours, approximately
400 and 50.265 mm² enclosed areas, even-odd SVG filling and two tracked output
files plus the PROGRESS row. Offset 18 is empty; offset 5 is unsupported because
it coincides with a face. Invalid NaN input is a command error.

The copied output's acquisition took 0.327 s and contour generation 0.000697 s
(single observations, not benchmarks; generation excludes SVG serialization and
file writing). Full command wall time and process memory were not measured.
The accepted snapshot has the same bounded inputs as `render`.

The actual SVG was rasterized headlessly with CairoSVG in a temporary uv tool
environment, using the existing pixi libcairo, and visually inspected: filled
square, clear circular cavity, outer and inner boundary strokes, legible named
plane/offset/status and tessellation qualification. CairoSVG is inspection-only,
not a product dependency. Initial import lacked a discoverable libcairo; setting
DYLD_FALLBACK_LIBRARY_PATH to the existing pixi library directory resolved it.

`cli-gate.log` retains the full built-engine CLI gate; `targeted-gate.log`
includes the final section tests (including sloped tetrahedron cuts that change
area with offset). No build, GUI or remote execution was needed; the full CLI suite includes
its existing toy local CPU training and walk regressions.
Walk wiring and separate two-mechanism lifecycle evidence remain outstanding.
