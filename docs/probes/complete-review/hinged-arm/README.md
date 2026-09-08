# Fresh hinged-arm complete-review rehearsal

Verified against source: 2026-09-08. [Cadex-new].

The unchanged public entry point completed design/assembly acceptance,
MJCF/task export, toy CPU training, policy witness verification, rollout and
all four review outputs on a fresh project. No model call, GUI or remote host.
This is the first of the two separately planned mechanism rehearsals; the
fresh carriage comparison remains required for the headless-review criterion.

Reproduce from the repo root with a built engine and the training venv from
`training/SETUP.md`. Choose a fresh project outside the checkout (so automatic
project commits do not enter the product repository):

```bash
project=$(mktemp -d)/hinged-arm
./cadex script --project "$project" --set examples/lifecycle/hinged-arm/script.py --json
JAX_PLATFORMS=cpu .venv/bin/python docs/probes/named-angle/fresh-walk/monitor.py \
  ./cadex walk --project "$project" --out "$project/runs/baseline" \
  --trainer-python "$PWD/.venv/bin/python" --iterations 1 --envs 4 --seed 0 \
  --timeout 600 --json
```

Both commands exited 0. The existing monitor samples the command's process
tree every 0.2 s, stopping above 2.9 GB or 850 s. The trainer also has a 600 s
timeout. Whole-command time was 16.61 s; peak sampled RSS 1,059,241,984 bytes.
Sampling is not an instantaneous memory maximum. The gate ran concurrently
with the latter part of this walk; timings are observations, not benchmarks.

Exact reward/witness/timing numbers are in retained `PROGRESS.md` and
`runs/baseline/review.json`. Training seed is 0; the recipe's rollout seed is 3.
Rollout reward -27.109384220927513 over 50 steps is -0.5421876844185503 per
step. Training-batch reward/step is -0.3801981508731842, a different measure.
Witness error is 1.3841167412209642e-09. CPU training is a pipeline rehearsal,
not a useful learned robot policy. Acquisition is shared and counted once;
contour time excludes SVG serialization/writes, and walk_seconds excludes the
last project commit. The external monitor includes command startup and exit.

All four actual SVGs were rasterized with inspection-only CairoSVG using the
existing pixi libcairo and visually inspected. Front shows the orange arm
resting on the blue base and extending beyond it; top shows the narrow arm
along the base edge; right shows their heights; iso shows the solved placement
and flat lighting. Captions are legible. XZ at Y=3.125 mm has two closed filled
contours, base 360 mm² and swing 640 mm², in contact at Z=6 mm. Actual contour
coordinates and SVG paths were inspected; this model has no cavity.

Inventory truthfully lists two uncatalogued synthetic components. Clearance
names base–swing: distance 0 mm, common volume 0 mm³, below the 0.1 mm clearance
threshold; one checked/offending pair, zero unknowns. Zero common volume is
not a clearance pass. Render and section revision/digest agree with rollout;
clearance revision agrees. All geometry findings concern the initial solved
pose, not swept motion. Section remains qualified tessellation, not exact BREP.

`audit.json` retains the project commit, SHA-256 hashes of all copied source,
document and review artifacts, contour areas and the policy metadata extracted
from the trace. Every listed artifact matched `git show HEAD:<path>` byte for
byte, and project status was clean. No checkpoint, policy bytes or rollout
trace is retained here. The source script references the runtime-only policy.
The reviewing agent copied the existing sensor notes after the run (script
import only imports code), and committed those with exact measurements and
ADR-002. The final PROGRESS row uses `<project>` to avoid retaining a machine
path; the source project's final committed file has that same normalization.

The full built-engine gate uses the same process-tree monitor:
`pixi run python -m pytest cli/tests -q --basetemp <fresh-temp-directory>`.
See `cli-gate.log` and `cli-monitor.log` for its final result. No product code,
payload or shell changed, so no full build or bundle qualification is claimed.
GUI remains documented-only; remote handoff remains scripted-only, with prior
CPU stand-in parity evidence in `copper-timber-8947`.

Gate result: **195 passed, zero skipped, 217.22 s**; monitor exited 0 in
217.87 s with sampled peak process-tree RSS 1,172,209,664 bytes.
