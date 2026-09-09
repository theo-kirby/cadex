---
node_id: 3efce8ef-2548-5fd0-bea2-08003f5f639b
slug: rare-cliff-9595
title: 'The walk holds on a second mechanism on this machine: prismatic carriage, exit 0 in 5:59.8'
created_at: '2026-09-08T14:28:06+00:00'
parents:
- glad-mesa-6299
summary: ''
---
## What

**A second mechanism through the unchanged `cadex walk --prompt`, on this run's
machine.** A *vertical linear carriage* rig — **prismatic** joint, **force
motor** — went from one sentence to a verified policy with no human step past
documented flags: **exit 0, 5:59.8 wall clock, 1,721 MB peak RSS**, into
`~/cadex-projects/ot4-carriage`, a second durable project outside this
repository. The tree was clean throughout: **no code change of any kind**, and
the whole repo diff is two documentation edits.

Legs, all exit 0: **design 340.7 s** (one turn), **train 15.8 s**, **declare
0.9 s**, **rollout 1.0 s**; `walk_seconds` 359.7 through review. Training was
local CPU at the same toy scale and seed the swing arm used — 5 iterations × 16
envs, seed 0, 2.8 s, 4,673 parameters, reward/step **0.02347** (best iteration
0.16748), witness error 2.8e-09 against a 1e-4 tolerance. The verified rollout
scored **total_reward 3.2963** over 4 legs (`height` +3.3085, `effort`
-0.0122).

All four headless eyes ran again: render (front/top/right/iso, 60 triangles,
0.32 s), section (XZ at 3.125 mm), inventory (**2 components, 0 catalogued** —
this rig is printed, not purchased, where the swing arm's was 10/7), and the
clearance bounds check (**pass**, 2 comparisons over 1 pair, 0 offending). The
project landed as a codebase without help: five commits, five `PROGRESS.md`
rows, five project ADRs (ADR-002..005 are the design leg's own `DECISION:`
lines about the fused base/column, the mid-stroke slider, the absent collision
shapes and the clamped parameter ranges), and
`docs/{actuators,clearance,inventory,sensors}.md`.

## Why

The charter criterion **The walk holds on a second mechanism**
(`swift-dusk-2951`), mission item 2, and the short rung's unit 1 — the
overseer's item 2 in the same words. The gate that held the criterion open was
"it cannot be re-evidenced until one mechanism completes on this machine";
`wandering-jasper-6102` opened it, and the swing-arm rig is mechanism one.

The plan asked for a mechanism differing from the swing arm in **joint type and
actuator type**, which is why the carriage prompt was reused verbatim from
nt3's `prompt-walk-nt3c`: revolute + position servo against prismatic + force
motor, a different path through the digest edit. What a contributor can say is
that both halves of the criterion held — same entry point with no
mechanism-specific code, and both `PROGRESS.md` files carrying comparable rows.
The tick is the maintainer's.

Three decisions taken without a person, per the question policy. **The same 5 ×
16 × seed 0 as the swing arm**, not nt3's 1 × 4, so the two rows on this machine
share a scale and the comparison is about the mechanism rather than the budget.
**`CADEX_MODEL=claude-opus-5`** again — the ADR-249 mechanism; `claude-fable-5`
is still out of usage credit on this login. **`--trainer-python` dropped**, as
`wandering-jasper-6102` recommended: the documented fallback resolved
`~/cadex-train-venv` on its own, and the train leg's flags in the envelope show
it was never passed.

The **caveat is stated rather than a ranking**, because it is true and the
alternative is a lie: the two reward expressions are different objectives in
different units and different episode lengths, so `total_reward 3.2963` against
`-0.1765` says nothing about which rig is better. `PROGRESS.md`'s own header
carries that rule; this record does not weaken it.

## Method

Prerequisites checked first, not assumed: `git status --porcelain` empty; the
installed runtime already carried ADR-250's OpenBLAS pin (`grep -c
OPENBLAS_NUM_THREADS build/release/Mod/cadex/CadexScriptedRuntime.py` → 1), so
**no build was needed and none was run**; `claude -p "reply with the single
word ok" --model claude-opus-5` answered `ok`.

One command, with `PYTHONPATH` / `CADEX_ENGINE_ROOT` / `CADEX_MODULE_DIR`
unset and `/usr/bin/time -v` around the whole process tree:

```sh
CADEX_MODEL=claude-opus-5 JAX_PLATFORMS=cpu ./cadex walk \
  --project ~/cadex-projects/ot4-carriage \
  --out ~/cadex-projects/ot4-carriage/runs/baseline \
  --prompt "A vertical linear carriage test rig: … prismatic joint … force
  motor … rewards lifting the carriage while penalising actuator effort …" \
  --iterations 5 --envs 16 --seed 0 --timeout 600 --json
```

Numbers read back from the `--json` envelope, from
`runs/baseline/review.json`, and from the project's own git log and
`PROGRESS.md`. **No generated artifact entered the run branch:** the project is
its own repository at `~/cadex-projects/ot4-carriage`, and this unit's whole
diff here is `docs/ROADMAP.md` (one entry) and `docs/CLI.md` (one paragraph).

Gate for the zone touched: `JAX_PLATFORMS=cpu pixi run python -m pytest
cli/tests` — **217 passed, 0 skipped, 181.60 s**, including `test_walk.py`'s two
real walks with the real engine and trainer, which skip without a training venv
and did not skip.

No GUI, no `pixi run app`, no remote dispatch, no retry, no hand edit of the
project's script or documents.

## Result

The second mechanism is through, and the two projects on this machine now read
side by side:

| project | mechanism, joint, actuator | design | train | declare | rollout | wall | peak RSS | `total_reward` |
|---|---|---|---|---|---|---|---|---|
| `ot4-swing2` | swing arm, revolute, MG90S position servo | 1,014.2 s | 38.3 s | 2.2 s | 2.4 s | 17:43 | 2,640 MB | -0.1765 |
| `ot4-carriage` | vertical carriage, prismatic, force motor | 340.7 s | 15.8 s | 0.9 s | 1.0 s | 5:59.8 | 1,721 MB | 3.2963 |

Both at 5 iterations × 16 envs, seed 0, `--timeout 600`, both witness-verified
(7.2e-09 and 2.8e-09 against 1e-4). Same columns, same definitions; the totals
compare runs within one project and never rank the two designs.

Also landed, as the overseer asked and no larger: **one paragraph in
`docs/CLI.md`** saying the walk resolves the installed engine and never checks
it against the tree, so an unbuilt Python change under `src/Mod/cadex/` runs the
previous runtime and the walk still exits 0. That is the plan's unit 2 reported
as a doc prerequisite rather than built as a `--json` field — the reversible
option, and it leaves the field free for whoever takes that unit.

What is still missing on the frontier: **Three modes, one shape**
(`witty-spark-2613`) wants a currency audit of the ADR-200 remote handoff and
the ADR-201 GUI-attached document against `$CADEX_MODEL` and the ADR-250 pin —
a documentation unit, not a re-scripting. The unreconciled tail is now three
nodes and the maintainer pass is due; the overseer asked for it before this
unit, and a work dispatch may not run it.

Dispatch closed: 1 unit — a second mechanism (prismatic joint, force motor) through the unchanged `cadex walk --prompt` on this machine, exit 0 in 5:59.8, four legs and four review eyes, PROGRESS rows comparable with the swing arm's, `cli/tests` 217 passed / 0 skipped.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 5eb24941212b4099f5a03780bc076ee056a7882b

## State Impact

- target: swift-dusk-2951 — the same cadex walk --prompt entry point, with no code change of any kind (clean tree at 526d43fb), took a vertical linear carriage rig (prismatic joint, force motor) from a prompt to a verified policy on this machine: exit 0, 5:59.8, 1,721 MB peak, design 340.7 s / train 15.8 s / declare 0.9 s / rollout 1.0 s, walk_seconds 359.7, reward/step 0.02347, witness error 2.8e-09, total_reward 3.2963 over 4 legs, all four review eyes; both projects' PROGRESS.md rows are comparable line for line at 5x16 seed 0, with the standing different-objectives caveat, and cli/tests 217 passed 0 skipped
- target: crisp-reef-5607 — the documented headless entry point completed unattended a second time on this machine, on a mechanism it had not seen, with no build and no retry
