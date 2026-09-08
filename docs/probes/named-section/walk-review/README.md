# Sections integrated into walk review

Verified against source: 2026-09-08. [Cadex-new]. ADR-240 follow-up.

The SVG and JSON pairs are actual outputs from the built-engine regression
`test_remote_walk_has_local_artifact_paths_with_a_cpu_dispatcher`, parameterized
for the documented hinged-arm and linear-carriage scripts. Each mechanism runs
through the same `script --set` and `walk --iterations 1 --envs 4 --seed 0
--timeout 600` entry points in local mode and with `--remote --allow-cpu`.
The remote dispatcher is replaced by a local CPU trainer subprocess: no SSH,
remote machine, GUI or provisioning. The existing training venv supplies JAX
and MuJoCo; training remains offboard.

The tests assert verified policy witnesses, matching contour geometry and
image pixels between modes, section status/metadata and accepted revision/digest,
actual SVG paths, positive contour areas, git-tracked SVG/JSON and clean project
worktrees. Both cuts are world XZ at Y = 3.125 mm, using exactly the preview's
accepted snapshot (no second display rebuild). Both objects have closed,
nonempty cuts. These are qualified initial-pose tessellation sections: the
arm retains its known base contact; the carriage is separated. Neither is
swept clearance, and neither example exercises a cavity; the separate section
CLI cavity fixture remains the evidence for even-odd hole preservation.

`measurements.json` retains timings, reward, witness and artifact assertions
from the initial targeted gate. Whole walks took 14.35–15.75 s, shared display
acquisition 0.645–0.668 s and contour generation 0.000064–0.000069 s. Acquisition
must be counted once across render and section. Contour timings exclude SVG
serialization/writes; whole-walk timings end before the final project commit.
These are observations, not benchmarks. Mode pairs have identical rewards:
arm -27.1093842209, carriage -24159.1953563045 (see measurements for exact values).
They are comparable task measurements, not useful learned robot policies.

The initial targeted gate passed 24 tests in 116.19 s (zero skipped), before
adding four explicit section outcome regressions and the scaffold contract
assertions. `cli-gate.log` is the subsequent full built-engine CLI gate, including
those tests: **195 passed, zero skipped, 216.88 s**. The monitored command
exited 0 in 217.42 s with peak process-tree RSS **1,175,715,840 bytes**.
`monitor.log` samples its entire process tree every 0.2 s and stops
it above 2.9 GB or 850 s. Each toy training run is contained within that bound.
The initial targeted gate was not continuously memory-sampled; one active
trainer sample was 989,200 KiB RSS. No full build was needed for CLI-only edits.

Both local SVGs were rasterized headlessly with inspection-only CairoSVG and
visually inspected: blue rectangular bases, orange arm/carriage cuts, readable
XZ/offset/status qualification. Direct uv executable invocation initially lost
the libcairo search path; setting it inside the inspection Python process
resolved that. No rasterizer dependency was added to the product.

This is integration evidence. The separate fresh two-mechanism complete-review
rehearsal remains the next unit, and the headless-review frontier remains open.
No training checkpoint or rollout trace is retained here.
