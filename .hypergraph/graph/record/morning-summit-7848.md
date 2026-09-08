---
node_id: 0123185d-1dd8-53f8-bb71-0e8199ab093b
slug: morning-summit-7848
title: The refreshed bundle's clearance is right on a catalog-placed assembly
created_at: '2026-09-08T02:54:46+00:00'
parents:
- southern-otter-5999
summary: ''
---
## What

Refreshed the ordinary installed Cadex application so it carries both clearance
frame fixes (ADR-241's static pair check and ADR-242's swept check), then ran the
documented headless lifecycle entry point once from the pan-tilt prompt against
that bundle, and checked the review leg's clearance numbers structurally against
independent surfaces.

**The bundle refresh and the walk are both clean. All four legs exit 0, no leg
needed a person and no leg needed a guess.** No repository source changed; the
tree is clean and nothing was committed to it.

| leg | exit | seconds |
|---|---|---|
| design (1 prompt turn) | 0 | 374.52 |
| train (1 it x 4 envs, CPU) | 0 | 24.65 |
| declare (the digest edit) | 0 | 1.52 |
| rollout | 0 | 1.72 |

Whole walk **406.33 s wall, 1.750 GB peak process-tree RSS**, inside the charter's
850 s and 2.9 GB guards, no cutoff.

**But this walk could not test the conditional it was selected for, and a second
measurement was needed to get that evidence.** The design turn is nondeterministic:
this time it called `lib.servo("mg90s", ...)` twice but **fused** both servo bodies
into its three hand-authored solids instead of adding them as assembly components.
Inventory: 3 components, **0 catalogued**. So **zero clearance rows involved a
`lib.*`-placed component**, and the structural check on this walk passed only
because there was nothing catalog-shaped to bite on. I therefore drove the four
review calls through the same installed bundle against the earlier pan-tilt
project, whose assembly does carry two placed `lib.servo` components, and checked
those numbers instead. They pass, and a negative control proves the check has
power.

## Why

The plan's short rung, rank 1 (`young-crane-9546`), and the overseer's message for
this dispatch, both unchanged: refresh the bundle, confirm the installed worker
carries the fix, run the packaged lifecycle gate against that root, then one walk
on the pan-tilt prompt, checked structurally. It serves missions 1, 2 and 6 and
sits on `damp-moon-9297` (the agent can see its work without a screen), with
incidental evidence for `crisp-reef-5607` and `swift-dusk-2951`.

**Assumption written down, nobody to ask.** The plan's structural check is stated
as a conditional over `lib.*`-placed rows: "every clearance row involving a
`lib.*`-placed component must agree with the exported STL vertex bounds and the
section contours". A conditional with an empty antecedent is vacuously true, and
reporting that as a pass would be the same class of lie the ADR-241 defect was —
a number that reads as a verdict. The reversible option is to spend one more cheap
measurement rather than re-roll the nondeterministic design turn hoping for a
catalog component: the four review calls are token-free, run against the same
installed bundle, and the earlier pan-tilt project is an assembly that already has
the placed catalog parts. That is what I did. Re-rolling the walk would have cost
another ~400 s of tokens for a coin flip on the same question.

## Method

**Refresh.** `pixi run build-shell` (its dependency runs `stage-engine`) then
`bash package/app/build_app.sh install`, both exit 0. Neither `pixi run app` nor
`pixi run install-app` was invoked and no GUI was launched; the install script has
no build dependency and does not open the application.

**Identity.** `cadex_assembly_worker.py` is byte-identical across source, staged
payload and installed bundle: sha256 `6a0e9ff8b16eb240...` for all three. The
installed copy defines `_clearance_prepare` (line 2959), `_component_world_shape`
(5363) and `_linked_source_shape` (5387); the pre-refresh installed copy contained
none of the three. Manifest `c23a9d1826ca8816...` and binary `ef31342ea2803e4c...`
are unchanged from `strong-raven-3067`, so only Python moved. The documented
development-prefix dynamic linking limit still holds: this is the local
unrelocated payload, not a portable release.

**Gate.** `CADEX_ENGINE_ROOT=<bundle> pixi run python -m pytest
src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py -q -ra` — 15 passed in 14.83 s.

**Walk.** `CADEX_ENGINE_ROOT`, `MESH_CADEX_ENGINE`, `MESH_FREECADCMD`,
`MESH_CADEXD_MODULE` and `PYTHONPATH` unset; engine chosen by explicit `--engine`
at the installed manifest directory; fresh scratch project outside the parent
checkout so the CLI owns its own git repository. One command, the same prompt
text as `empty-banner-7438` verbatim: `cadex walk --engine <bundle> --project
<scratch> --out <scratch>/runs/baseline --prompt "<pan-tilt head, two MG90S,
position servos with MG90S torque and speed limits, a joint-angle sensor per axis,
a task driving both joints to pan 0.4 rad / tilt -0.3 rad with a small effort
cost>" --trainer-python <repo>/.venv/bin/python --iterations 1 --envs 4 --seed 0
--timeout 600 --json`, with `JAX_PLATFORMS=cpu`, wrapped in the existing
process-tree monitor (0.2 s RSS sampling, SIGTERM at 2.9 GB or 850 s, five-second
SIGKILL fallback). Model `claude-fable-5`; the design turn is the only leg that
spends tokens.

**The structural check.** A written checker reads the clearance markdown rows and
the per-object world `bounds_mm` from three surfaces independent of the clearance
path and of each other — the section summary, the render summary, and the vertex
bounds of the exported STL, parsed from the binary triangles. For each pair it
computes the largest axis gap and the AABB overlap volume, then asserts: a pair
whose bounds are provably disjoint may not carry a common volume, and its reported
distance may not be smaller than the gap; an overlapping pair's common volume may
not exceed the AABB overlap. Float tolerance 1e-4 mm / mm3.

## Result

**Bundle refresh: clean.** Build and install exit 0; the installed worker carries
all three helpers; the packaged lifecycle gate passes 15 in 14.83 s against that
root.

**Walk: clean, four legs, no guess and no person.** Accepted revision
`8ad39702c21c...`, digest `ac1c9ca29dd8...`. Training CPU, 1 iteration, 4 envs,
seed 0, 4,738 parameters, **witness error 2.882e-09** against a 1e-4 tolerance.
Rollout `total_reward` -237.568 (pan_error -151.349, tilt_error -86.218, effort
-1.686e-06). Toy execution measurements, not learned-control quality.
Project: **six commits, clean status**, carrying `ARCHITECTURE.md`, `DECISIONS.md`,
`PROGRESS.md`, `docs/inventory.md`, `docs/clearance.md`, `runs/baseline/review.json`,
four view SVGs, the XZ section at Y = 3.125 mm and its summary, `assets/`.

Review outputs: render four views, 3,804 triangles, three objects; section XZ at
3.125 mm, three objects, all `status: ok`; clearance 3 pairs checked, 2
offending, 0 unknown; inventory 3 components, 0 catalogued. **Views inspected, both
read correctly**: blue base plate with the pan MG90S silhouette fused into it, green
yoke with the tilt servo's mounting lugs and horn boss fused into it, orange head
plate and camera cube. The fused-servo geometry in the render is exactly what the
zero-catalogued inventory says, so the two surfaces agree.

**Structural check on the walk: PASS, 0 failures over 6 bound comparisons plus the
STL pass — and it proves nothing about the fix,** because none of the three rows
involves a `lib.*`-placed component. Recorded as a null result, not a pass.

**Structural check on a lib-placed assembly through the same installed bundle:
PASS, 0 failures over 20 pairwise comparisons.** `clearance`, `inventory`,
`section` and `render` all exit 0 against the earlier pan-tilt project at revision
`404caef91b4c`; inventory reports **5 components, 2 catalogued** (`servo/mg90s`
x2). Ten clearance rows, **seven of them touching a catalog-placed part**, every
one agreeing with both the section and the render bounds. The numbers:
base/servo_pan 111.264 mm3 (the true 0.4 mm sink, against an AABB overlap of
158.6 mm3), base/servo_tilt 57.9 mm clear, servo_pan/servo_tilt 25.9 mm clear.

**Negative control: the same checker, fed the three pre-fix rows recorded in
`empty-banner-7438`, reports 10 failures** — servo_pan/servo_tilt "8240.943 mm3"
against bounds disjoint by 25.9 mm, base/servo_tilt "1112.640 mm3" against bounds
disjoint by 57.9 mm, and base/servo_pan "1112.640 mm3" against a 158.6 mm3 AABB
ceiling. The check has real power over exactly the defect it was written for, and
the refreshed bundle passes it.

Not claimed: sections are tessellated cuts and clearance here is initial-pose, not
swept — ADR-242's swept path was not exercised by this unit, only shipped in the
bundle it verified. The design turn's nondeterminism means a future walk may or
may not produce catalog components; nothing here makes that repeatable. No engine
or CLI suite was rerun because no repository source changed; the packaged lifecycle
gate is the only gate this unit owed and it passed. No shell gate: `shell/` is
untouched. No remote dispatch, no GUI launch.

**Charter criterion this advances: `damp-moon-9297` — the agent can see its work
without a screen.** Its four calls all land in the project directory and all four
now measure a catalog-placed component where the assembly puts it, through the
ordinary installed bundle rather than the development tree. What is still missing
before it can be ticked: nothing this unit found. The one defect that blocked it
(`empty-banner-7438`) is closed in source (ADR-241, ADR-242) and now shown correct
through the shipped artifact against three independent surfaces with a working
negative control. `crisp-reef-5607` gains a fourth clean prompt walk and
`swift-dusk-2951` a fourth mechanism through the same entry point with no
mechanism-specific code; neither needs anything more from this unit.

Next: the tail is three unreconciled records, over the charter's threshold of
three, so a maintainer pass is due before more work. After it, the remote-training
handoff script and doc for `witty-spark-2613` ("three modes, one shape") is the
next unit the overseer named — noting that `empty-banner-7438` argues that leg is
already shipped as ADR-200, so the unit may be evidencing it rather than writing it.
Dispatch closed: 1 unit — the refreshed bundle passes the packaged gate and a clean four-leg pan-tilt walk, and its clearance is proved correct on a catalog-placed assembly against three independent surfaces with a negative control.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 870ed8166d4f23387a38e9dc4b181708f087cd5b

## State Impact

- target: damp-moon-9297 — Both clearance frame fixes now ship in the ordinary installed bundle (worker byte-identical to source, packaged lifecycle gate 15 passed); its clearance, inventory, section and render agree on a 5-component assembly with two lib.*-placed MG90S, 20 pairwise bound comparisons and 0 failures, where the same check gives 10 failures on the pre-fix numbers.
- target: crisp-reef-5607 — A fourth clean prompt walk on the refreshed installed bundle: four legs exit 0, 406.33 s, 1.750 GB peak RSS, no cutoff, no leg needed a person or a guess; witness error 2.882e-09.
- target: swift-dusk-2951 — The same entry point took a fourth mechanism variant through design/train/declare/rollout/review with no mechanism-specific code change; six project commits, clean status, PROGRESS numbers comparable.
