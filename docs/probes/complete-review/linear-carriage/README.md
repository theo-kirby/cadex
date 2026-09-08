# Fresh linear-carriage complete-review rehearsal

Verified against source: 2026-09-08. [Cadex-new].

The same public entry point used by the fresh hinged-arm rehearsal completed
on the existing linear-carriage example with no runner or model code change.
Both projects' committed PROGRESS.md now carry the same comparison table.
This is the second separate evidence run planned by sage-crow-3224.

Reproduce from the repository root with the built engine and the existing
training venv from training/SETUP.md; choose a fresh directory outside the
product checkout so the project's automatic commits remain independent:

```bash
project=$(mktemp -d)/linear-carriage
./cadex script --project "$project" --set examples/lifecycle/linear-carriage/script.py --json
JAX_PLATFORMS=cpu .venv/bin/python docs/probes/named-angle/fresh-walk/monitor.py \
  ./cadex walk --project "$project" --out "$project/runs/baseline" \
  --trainer-python "$PWD/.venv/bin/python" --iterations 1 --envs 4 --seed 0 \
  --timeout 600 --json
```

Design and walk exited 0. The monitor sampled the process tree every 0.2 s,
with 2.9 GB / 850 s cutoffs; trainer timeout was 600 s. The whole command took
16.39 s with peak sampled RSS 987,168,768 bytes. This is a sampled maximum,
not an instantaneous bound. Gate and walk overlapped, as in the arm run;
timings are observations rather than performance benchmarks.

Training was CPU, one iteration, four environments, seed 0. Training reward
per step was -82.31990814208984, witness error 5.41889473917867e-09. The
verified rollout (seed 3, 50 steps) scored -24159.19535630446, averaging
-483.1839071260892 per step. The carriage falls with this toy policy. A
verified policy is not a useful controller or a safe mechanism. The common
lift term uses millimetres, but effort is N here and N·mm in the arm; the
comparison table does not rank unlike mechanisms as policy improvements.

Shared display acquisition took 0.6857212079921737 s; four-view rasterization
0.6373496250016615 s; section contours 0.00007579103112220764 s. Acquisition
counts once for both outputs. Contour time excludes serialization/writes;
walk_seconds 16.048740583006293 ends before the final project commit. External
whole-command time includes startup, that commit and exit. All boundaries
match the fresh arm table rather than older timing evidence.

All actual SVG artifacts were rasterized using inspection-only CairoSVG and
the existing pixi libcairo, then visually inspected. Front and right show the
orange cube above the blue base; top shows the cube footprint over the base;
iso shows the two volumes and their placement. Captions identify the view and
revision. The XZ cut at Y=3.125 mm contains closed filled contours for base
(X=0..60, Z=0..6 mm, area 360 mm²) and slide (X=12..32, Z=40..60 mm,
area 400 mm²). Actual contour coordinates, shoelace areas and SVG contents
were checked. Neither example has a cavity; cavity/rotation coverage comes
from the real-kernel CLI suite, not this rectangular example.

Inventory names base/slide, sources plate/carriage and catalogue fields;
both parts are truthfully uncatalogued synthetic boxes. Clearance names
base–slide at 34 mm distance and 0 mm³ common volume: one pair checked,
zero offending, zero unknown, using 0.1 mm / 1e-6 mm³ thresholds. The arm
keeps its base–swing zero-distance contact as one offending pair. This is
initial solved pose only; falling rollout geometry is not certified clear.
Sections are qualified tessellation cuts, not exact BREP or swept safety.

The accepted project revision/digest equals the rollout leg, render and
section identity; inventory and clearance identify that revision. Trace
policy/task hashes, reward, seed and steps match the review. audit.json
retains extracted trace metadata, contour areas, committed artifact hashes
and the source project's final commit. Every copied project file matches
`git show HEAD:<path>` bytes, and source project status was clean. The existing
arm project was audited again after its comparison commit; see its new
comparison-audit.json. Prior arm audit.json remains evidence of the earlier
commit. No checkpoints, policy bytes, rollout traces or machine paths are
retained in this evidence directory. The retained script references its
runtime-only policy, so this directory is evidence, not a portable project.

The reviewing agent copied the example's existing docs/sensors.md after
script import, normalized project paths in PROGRESS.md, and committed the
comparison/rationale in both projects. No lifecycle implementation or scaffold
convention changed. No new dependency, build, payload or protocol change.

Together with first-branch-9614, this supplies fresh inspected evidence for
all headless-review clauses: named-angle rendering, named-plane sections,
assembly inventory with catalogue fields, and named clearance/intersection
pairs, all used in the public walk and committed to each project. The full
CLI gate also exercises the standalone commands and local CPU remote-flag
stand-in parity. GUI mode remains documented-only; remote handoff remains
scripted-only, as the charter requires (existing parity: copper-timber-8947).
Combined evidence is ready for maintainer judgement; no charter or state node
was changed, and no later criterion was promoted.

Gate command (the same monitor, fresh temporary test directory):

```bash
.venv/bin/python docs/probes/named-angle/fresh-walk/monitor.py \
  pixi run python -m pytest cli/tests -q --basetemp <fresh-temp-directory>
```

Gate result: **195 passed, zero skipped, 219.10 s**. Monitor exit 0,
219.85 s whole command, peak sampled process-tree RSS 1,173,487,616 bytes.
See cli-gate.log and cli-monitor.log. No build or packaged gate is claimed;
this unit changes evidence/docs only. git diff --check and hypergraph checks
passed. Reconciliation and re-planning are reserved for the next maintainer
and planner passes under the contributor-only dispatch rules.
