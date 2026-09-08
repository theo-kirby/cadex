---
node_id: 24826620-6f53-5360-b0b7-30343eab8444
slug: chilly-crest-2100
title: 'The walk holds on a third mechanism: a cylindrical joint, driven on its linear coordinate'
created_at: '2026-09-08T18:57:17+00:00'
parents:
- northern-comet-5917
summary: ''
---
## What

**A third mechanism through the unchanged `cadex walk --prompt`, on this
machine.** A *quill lift* rig — **one cylindrical joint** (a slide and a hinge
on the same axis) driven by a **position servo on the linear coordinate** —
went from one sentence to a verified policy with no human step past documented
flags: **exit 0, 10:52.99 wall clock, 1,946 MB peak RSS**, into
`~/cadex-projects/ot4-quill`, a third durable project outside this repository.
No code change of any kind; the whole repo diff is two documents.

Legs, all exit 0: **design 629.6 s** (one turn), **train 19.6 s**, **declare
0.9 s**, **rollout 1.0 s**; `walk_seconds` 652.9 through review. Local CPU
training at the same toy scale and seed the two earlier walks used — 5
iterations × 16 envs, seed 0 — 3.7 s, 4,801 parameters, reward/step
**-0.5796**, witness error **2.9e-08** against 1e-4. The verified rollout
scored **total_reward -74.79** over 200 steps and four terms
(`hold_at_target` +28.18, `tracking_error` -98.23, `actuator_effort` -1.46,
`quiet_slide` -3.28).

The three things the plan asked this walk to report:

- **Both travel channels: `travel_mm 20.28`, `travel_deg 0`, on the same
  component** (`quill_component`, 201 solved frames). The joint offers both
  and the rollout used one — gravity exerts no torque about a vertical axis,
  so an axially offset head mass does not spin the quill. A zero in a channel
  is a fact about that rollout, not a missing measurement.
- **The delta did not render, and could not.** `ot4-quill`'s baseline is its
  first walk, so no previous row carries `travel_mm`, `travel_deg` or
  `total_reward`. ADR-260's threading is exercised by the offline regressions
  the previous unit landed, not by this run.
- **The documentation eye read a real design turn's own notes back**:
  `expected [actuators, sensors]`, `notes [docs/actuators.md,
  docs/sensors.md]`, `missing []` — the row says `docs notes 2, none
  missing`. Both notes were written **unprompted**, and both are substantive:
  `docs/actuators.md` gives the servo's 5 N/mm stiffness, its near-critical
  0.03 N·s/mm damping with the arithmetic, the 20 N limit against a 0.27 N
  static weight, and why the rotation coordinate is deliberately unactuated;
  `docs/sensors.md` names all six channels with units and says which one
  drives the termination rule. This is the first walk where that check had a
  design turn's notes to read — the two documented example walks are recipe
  walks and run no design turn.

One finding nobody asked for: **the clearance eye returned its first
offending pair on an agent-authored design** — `housing`/`quill`, verdict
`intersection`, 960 mm³ common volume, 0.0 mm distance. It is **deliberate**,
and the project says so itself in its own ADR-005: the shaft is modelled
inside a solid bore cylinder, the joint rather than contact constrains the
quill, and the two collision groups are disjoint. So the eye read a known
modelling choice back rather than catching a defect, and exit 0 is right —
the report was written, not "all pairs are clear".

## Why

The charter criterion **The walk holds on a second mechanism**
(`swift-dusk-2951`) and **The walk exists and is tested headlessly**
(`crisp-reef-5607`), mission item 2, through the plan's short-rung unit 1 and
the overseer's instruction in the same words: one fresh prompt walk, third
mechanism, joint and actuator both different from the swing arm (revolute,
position servo) and the carriage (prismatic, force motor), into a durable
project outside this repository.

**Why a cylindrical joint and a linear position servo, and not a velocity
actuator.** The obvious reading of "a different actuator" is the third
MuJoCo kind, and it is not available: `_action_bound` in `CadexDynamics.py`
refuses a **velocity** actuator at `action_range_underivable`, because a
joint states position limits and nothing in an assembly states a speed. The
engine's action-source table has exactly four pairs, and the two earlier
walks drove `(position, angular)` and `(motor, linear)`. `(position,
linear)` is the fourth and last, and hanging it on a **cylindrical** joint
makes the joint differ too — and, because a cylindrical joint has a slide
*and* a hinge, it is the mechanism the plan wanted for the travel channels:
one where nobody knows in advance which channel holds the motion. The answer
turned out to be the linear one, for a reason the physics fixes rather than
the design.

Decisions taken without a person, per the question policy. **Same 5 × 16 ×
seed 0 and `--timeout 600`** as both earlier walks, so the three rows share a
scale. **`CADEX_MODEL=claude-opus-5`** again — the ADR-249 mechanism;
`claude-fable-5` is still out of usage credit on this login, and it answered
`ok` on a one-word probe before the walk. **`--trainer-python` dropped**; the
documented fallback resolved `~/cadex-train-venv` on its own. **No ranking
claim**: three reward expressions in three unit systems are three objectives,
so -74.79 against 3.2963 against -0.1765 says nothing about which rig is
better, and `PROGRESS.md`'s own header carries that rule.

## Method

Prerequisites checked, not assumed: `git status --porcelain` empty on
`ouroboros/ot4` at `ec729d8b`; the installed engine's top-level Python
matched the checkout (the walk's own `engine_source_comparison` reported
`status: match`, 56 files, 0 changed), so **no build was run**; the trainer
venv and the model both answered.

One command, `PYTHONPATH` / `CADEX_ENGINE_ROOT` / `CADEX_MODULE_DIR` unset,
`/usr/bin/time -v` around the whole process tree:

```sh
CADEX_MODEL=claude-opus-5 JAX_PLATFORMS=cpu ./cadex walk \
  --project ~/cadex-projects/ot4-quill \
  --out ~/cadex-projects/ot4-quill/runs/baseline \
  --prompt "A quill lift test rig … ONE cylindrical joint … POSITION SERVO
  commanding the LINEAR coordinate … rewards extending the quill to about
  30 mm and holding it there while penalising actuator effort …" \
  --iterations 5 --envs 16 --seed 0 --timeout 600 --json
```

Numbers read back from `runs/baseline/review.json`, the exported trace, the
project's `PROGRESS.md` and its git log. The project landed as a codebase
without help: **five commits, five `PROGRESS.md` rows, six project ADRs**
(ADR-002..006 are the design turn's own `DECISION:` lines — one cylindrical
joint over a stacked slider-plus-revolute, the derived bore height, the
derived solver step, the disjoint contact groups, and a randomisation it
tried and dropped because `assembly.randomise` exposes no `motion_type` for a
cylindrical joint) and
`docs/{actuators,sensors,inventory,clearance}.md`.

A mid-unit correction, recorded because it changed the documents: I first
read the 960 mm³ as the head block passing 2 mm through the column, from the
arithmetic alone. The project's ADR-005 gives the real reason and says it was
intended; both documents were corrected before the commit.

**Nothing generated entered this repository.** The unit's whole diff here is
`docs/ROADMAP.md` (one entry) and `docs/CLI.md` (one paragraph).

Gate for the zone touched: `JAX_PLATFORMS=cpu pixi run python -m pytest
cli/tests` — **234 passed, 0 skipped, 202.20 s**, including `test_walk.py`'s
real-engine, real-trainer walks, which skip without a training venv and did
not skip. The doc-sensitive subset was re-run after the corrective prose
edit: 26 passed. No GUI, no `pixi run app`, no remote dispatch, no retry, no
hand edit of the project's script or documents.

## Result

Three mechanisms on this machine now read side by side, same columns, same
definitions, same toy scale:

| project | joint, actuator | design | train | wall | peak RSS | `total_reward` | travel |
|---|---|---|---|---|---|---|---|
| `ot4-swing2` | revolute, position servo | 1,014.2 s | 38.3 s | 17:43 | 2,640 MB | -0.1765 | not measured (pre-ADR-259) |
| `ot4-carriage` | prismatic, force motor | 340.7 s | 15.8 s | 5:59.8 | 1,721 MB | 3.2963 | not measured (pre-ADR-259) |
| `ot4-quill` | **cylindrical, position servo (linear)** | 629.6 s | 19.6 s | **10:53** | 1,946 MB | -74.79 | **20.28 mm / 0°** |

Inside every declared bound: ≤5 × 16, `--timeout 600`, explicit CPU, under 18
minutes, under 3 GB. The provider did not refuse.

What the criterion still wants before it is ticked — the maintainer's call,
not a contributor's: `swift-dusk-2951` reads "no code change specific to the
mechanism", which this run evidences a third time and which two offline
regressions now pin, and "both projects' `PROGRESS.md` carry comparable
numbers", which three projects now do except that the two older ones predate
the travel channels. **`crisp-reef-5607` is untouched by this unit** on its
remaining leg: the walk still spends an unbounded design turn — 629.6 s here,
1,014.2 s on the swing arm — with no `--timeout` of its own on that leg,
which is the one place the entry point can outrun a caller's budget.

Dispatch closed: 1 unit — a third mechanism (cylindrical joint, linear position servo) through the unchanged `cadex walk --prompt`, exit 0 in 10:53, travel 20.28 mm / 0° in the two channels, no delta (first walk of the project), documentation eye `docs notes 2, none missing` on a real design turn's unprompted notes, clearance `intersection` 960 mm³ that the project's own ADR-005 calls deliberate, `cli/tests` 234 passed / 0 skipped.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: c749d838579889e3568545cec9948ae3c0240c41

## State Impact

- target: swift-dusk-2951 — a third mechanism (cylindrical joint, position servo on the linear coordinate) went through the unchanged cadex walk --prompt on this machine with no code change of any kind: exit 0, 10:52.99, 1,946 MB peak, design 629.6 s / train 19.6 s / declare 0.9 s / rollout 1.0 s, walk_seconds 652.9, reward/step -0.5796, witness 2.9e-08, total_reward -74.79 over 200 steps; PROGRESS.md rows comparable with the swing arm's and the carriage's at 5x16 seed 0
- target: crisp-reef-5607 — the walk's third mechanism ran end to end headless with no human step, and named the one remaining unbounded leg: the design turn has no --timeout of its own (629.6 s here, 1,014.2 s on the swing arm)
- target: damp-moon-9297 — all four eyes ran on a third mechanism: render (front/top/right/iso, 1,404 triangles, 0.49 s), section (XZ at 3.125 mm, ok), inventory (2 components, 0 catalogued), clearance (1 offending pair, housing/quill intersection 960 mm3, deliberate per the project's own ADR-005); the ADR-256 documentation eye read a real design turn's unprompted NOTE lines back for the first time -- docs notes 2, none missing
