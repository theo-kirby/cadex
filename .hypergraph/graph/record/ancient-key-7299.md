---
node_id: 2446d585-a836-5327-bf4f-0c0a21b2323a
slug: ancient-key-7299
title: 'Bet: bisect the dynamics declarations that burn the worker CPU cap, then re-run the walk'
created_at: '2026-09-08T13:08:16+00:00'
parents:
- open-hollow-2140
summary: ''
---
## What

This run's plan resets to one thing: **finish the walk on this machine.**

The short horizon becomes three ranked units, each one iteration:

1. **Bisect the dynamics declarations that burn the worker CPU cap.** Take the
   accepted `script.py` from the failed walk, which rebuilds geometry-only in
   1 s and then burns exactly 300 s at `params --set policy_on=1`, and add its
   dynamics declarations back one class at a time — bodies with per-component
   collisions, the servo actuator with limits, observations, sensors, the two
   ranged `assembly.disturbance` values, the reward list — timing each at
   `policy_on=1` against the dev-tree engine. The unit names the class that
   crosses the cap and either fixes it or records why it cannot be fixed
   cheaply. Gate: `pixi run python -m pytest src/Mod/cadex/cadex_tests` for an
   engine change, `cli/tests` for a CLI one.
2. **Make the CPU-cap kill legible.** `RLIMIT_CPU` is set to
   `timeout_seconds` in *CPU*-seconds while the parent's timeout is the same
   number in *wall-clock* seconds, so a threaded pass on a 32-core box dies by
   SIGXCPU (returncode -24) and surfaces as `The isolated domain worker exited
   without a result` rather than a budget refusal. Map that signal to an
   explicit refusal that names the cap, and state the asymmetry where the
   setting is documented. Small engine diff plus a regression; engine suite.
3. **Re-run `cadex walk --prompt` end to end.** The charter's standing short
   unit: a clean run is the evidence that closes the walk gap, a failed run
   names the next one.

The medium horizon becomes the open gaps in the order they should fall: the
walk, then the eyes it reviews itself with, then the second mechanism, then
the two cheap legs of three-modes, with the RL gait scale and the parts
library left parked. The long horizon keeps the standing work and the parked
Later criteria, and drops nt3's provider-credit parking, which ADR-249 ended.

No new direction is proposed. At most one is allowed and none is needed: the
frontier is not empty and the next unit is named by evidence.

## Why

The charter is unambiguous about what leads this run: *"One thing leads this
run: the lifecycle walk, run end to end on this machine."* Its short rung says
to run the documented headless entry point end to end, record which leg still
needs a person, and *"do this before anything else, every time the short rung
is empty."* The short rung is empty in exactly that sense — the plan it
inherited from nt3 holds two conditional slots that are explicitly *"not
dispatchable now"* and a paragraph telling the controller to stop dispatching
[rec: curious-badger-0797]. That plan was true for the machine and the credit
state it was written on; it is not true here.

The run happened. `open-hollow-2140` ran `cadex walk --prompt` on this machine
for the first time and it exited 3 at the train leg after 1:06:25. Two legs
needed a person. The first is fixed: the default model had no usage credit, and
ADR-249 at `bc203d28` makes `--model` read `$CADEX_MODEL` before
`DEFAULT_MODEL`, with the CLI suite at 217 passed and no skips. The second is
not: the design agent built the rig — MG90S from the catalog, ten components,
three joints, one project commit, `docs/actuators.md`, `docs/sensors.md` and
`docs/rejected.md` — and then gated the whole training layer behind
`policy_on=0`, because `assembly.mjcf` and `assembly.dynamics` never return
[rec: open-hollow-2140].

That is the trigger the inherited plan demanded and did not have: a new
concrete failure, on a named charter criterion, with a bounded repair. The
criterion is **The walk exists and is tested headlessly**
(`crisp-reef-5607`), and the leg the criterion names — toy-scale local CPU
training from a prompt-designed mechanism — was never reached.

Unit 1 is ranked first because the same record already did the bounding work
and left the bisect as the named next unit. Four controls establish that the
fault is in this rig's declarations rather than in the export: a grounded
one-body model with a box collision accepts in 0 s, the reference
`linear-carriage` accepts in 0.55 s with a box, 1 s with a mesh and 0 s with a
hull, and the walk's own script rebuilds geometry-only in 1 s before burning
exactly 300 s at `policy_on=1`. The design agent's own `docs/rejected.md`
claims a single grounded box exhausts the cap; that claim is measured false,
which is why the bisect is a real experiment and not a re-run of a settled one
[rec: open-hollow-2140].

Unit 2 is second, not first, because the bisect does not need it: script-level
`print(..., flush=True)` is lost on the kill, so the bisect proceeds by timing
whole runs from outside, which works today. It is ranked at all because the
defect is small, certain, and costs every future stall an hour of guessing —
and because it is the reversible option the question policy asks for, a
message and a document before a change to the cap itself.

Unit 3 is the charter's standing unit, restored to the rung it belongs on.

Two things this pass deliberately does not do. It proposes no new direction:
the allowance is one, the frontier has five open criterion gaps, and inventing
a sixth would be the failure mode the charter names — nt3 wrote 22,437 lines
over 201 iterations and moved one node. And it retires no charter-derived gap:
none is blocked. `late-pond-2851`'s gait scale and `brave-stone-9609`'s
breadth stay parked under Later criteria, where only a human edit promotes
them.

Budget supports the ranking. One iteration has run, 46.5h remain, and the
walk itself costs about an hour of wall-clock, so three units and a re-run fit
without crowding out the maintainer passes.

## Method

Read the charter's ladder and question policy, the frontier's seven open
nodes, the three plan horizons, and `open-hollow-2140` in full. Verified the
two mechanical facts the bet rests on against source rather than the record:
`_resource_limits` in `cadex_domain_worker.py:102` applies `RLIMIT_CPU` from
`cpu_limit_seconds`, and `CadexEngineSettings.py:28` carries
`DEFAULT_SCRIPTED_TIMEOUT_SECONDS = 300.0` and
`DEFAULT_SCRIPTED_MEMORY_LIMIT_MB = 6144`. Confirmed `walk` is a real
subcommand of the documented entry point (`cli/cadex_cli/__main__.py:365`,
`command_walk` at 1241).

Then rewrote all three horizons: `short` replaced outright, `medium` reordered
around the open gaps, `long` compressed with the nt3 provider parking retired.
Carried forward the negative knowledge that still constrains work and dropped
the entries whose whole content was nt3's dispatch bookkeeping.

## Result

One planning pass. `short` (`young-crane-9546`), `medium`
(`strong-birch-7412`) and `long` (`late-valley-7350`) rewritten; no new plan
node; no charter-derived gap retired; no new direction proposed. No code, no
state node, no record but this one.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 1ebf1d14167b838bd1c447068da09e74e0345b98

## State Impact

- target: plan/young-crane-9546 — short replaced: bisect the policy_on=1 stall, make the SIGXCPU kill legible, then re-run the walk
- target: plan/strong-birch-7412 — medium reordered around the five open criterion gaps, walk first, eyes second
- target: plan/late-valley-7350 — long compressed; nt3's provider-credit parking retired by ADR-249
