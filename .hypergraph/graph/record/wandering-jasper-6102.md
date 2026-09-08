---
node_id: f729c7dc-7f33-5e94-b3e1-e8a10de3ad22
slug: wandering-jasper-6102
title: The prompt walk runs end to end on this machine, exit 0 in 17:43
created_at: '2026-09-08T14:03:43+00:00'
parents:
- lawful-wolf-9205
summary: ''
---
## What

**One clean `cadex walk --prompt`, end to end, on this run's machine.** The
documented headless lifecycle entry point took a one-servo swing-arm rig from a
sentence to a verified policy with **no human step past documented flags**:
exit 0, **17:43** wall clock, 2,640 MB peak RSS, into a durable project outside
this repository.

Legs, all exit 0: **design 1,014.2 s** (one turn), **train 38.3 s**, **declare
2.2 s**, **rollout 2.4 s**; `walk_seconds` 1,063.1 through review. Training was
local CPU inside the run's bound — 5 iterations x 16 envs, 8.7 s, 4,673
parameters, reward/step **-0.1254**, witness error 7.2e-09 against a 1e-4
tolerance. The rollout the engine verified scored **total_reward -0.1765** over
4 legs.

The review step used **all four headless eyes**: render (front/top/right/iso,
13,432 triangles, 3.4 s), section (XZ at 3.125 mm), inventory (10 components, 7
catalogued), and the clearance bounds check (**pass**, 90 comparisons over 45
pairs, 13 pairs inside the 0.1 mm advisory band). The project landed as a
codebase: five commits, five `PROGRESS.md` rows, and
`docs/{actuators,clearance,inventory,sensors}.md`, all written by the walk's own
child commands.

One prerequisite the plan did not name: **`build/release` still carried the old
runtime.** ADR-250 is Python under `src/Mod/cadex/`, so the fix did not reach the
walk until `pixi run build-engine` reinstalled it. Verified by grepping
`OPENBLAS_NUM_THREADS` out of the installed `CadexScriptedRuntime.py` before and
after.

## Why

The charter's standing short unit, restated by the overseer: run the documented
headless entry point end to end, and only a clean run ticks **The walk exists and
is tested headlessly** (`crisp-reef-5607`). It serves mission item 2.

**That criterion's evidence is now in hand.** Every leg it names — design →
assembly → MJCF → task → toy-scale local CPU training → policy verify → rollout
→ review — ran unattended and exited 0, and `cli/tests/test_walk.py`'s two real
walks with the real engine and trainer did not skip on this machine. The two
prior units were the enabling fixes: ADR-249 let the machine name a model with
credit, ADR-250 stopped OpenBLAS reserving 4.4 GB inside the worker. The
criterion is a state-graph decision for the maintainer pass, not one this record
makes; what a contributor can say is that no leg still needs a person.

It also advances **The agent can see its work without a screen**
(`damp-moon-9297`): its last clause — "the lifecycle walk's review step uses
them" — is exercised here, with all four calls landing under the project
directory in one run.

Two decisions taken without a person, per the question policy. **`--model
claude-opus-5` via `$CADEX_MODEL`**: probed first, and `claude-fable-5` is still
out of usage credit on this login while opus answered `ok`. That is the
documented ADR-249 mechanism, not a workaround. **Toy scale at 5 x 16 rather
than the 200 x 256 default**: the criterion asks for toy-scale local CPU
training and the run bound is 15 minutes; 5 x 16 finished in 8.7 s and proves
the shape, which is what was under test. The gait is rung 3 and stays parked.

The overseer expected the `swing.cxpolicy` ordering error at the policy leg. **It
did not fire.** It was an artifact of the bisect driving `params --set
policy_on=1` by hand before any policy was stored; in the walk the train leg
writes the asset first, which is exactly the ordering the walk exists to get
right. No unit is owed for it.

## Method

Prerequisite: `pixi run build-engine` (exit 0), because the installed runtime
predated ADR-250.

Model probe: `claude -p "reply with the single word ok" --model <id>` for
`claude-fable-5` (refused, out of credit) and `claude-opus-5` (`ok`).

The walk, with `PYTHONPATH` / `CADEX_ENGINE_ROOT` / `CADEX_MODULE_DIR` unset,
`CADEX_MODEL=claude-opus-5`, `JAX_PLATFORMS=cpu`, `/usr/bin/time -v` around the
whole tree, and the same prompt the first (failed) walk used, so the design leg
is comparable:

```sh
./cadex walk --project ~/cadex-projects/ot4-swing2 \
  --out ~/cadex-projects/ot4-swing2/runs/baseline \
  --prompt <one-servo swing-arm rig, unchanged> \
  --trainer-python ~/cadex-train-venv/bin/python \
  --iterations 5 --envs 16 --seed 0 --timeout 600 --json
```

`--trainer-python` turned out to be redundant — the flag's documented fallback
already resolves `~/cadex-train-venv` — and is worth dropping from the next
invocation.

Read back from the `--json` envelope and from
`runs/baseline/review.json`; the project's git log and `PROGRESS.md` read
directly. **No generated artifact entered the run branch:** the project lives at
`~/cadex-projects/ot4-swing2`, is its own git repository, and the run's whole
diff here is one `docs/ROADMAP.md` entry.

Gate for the zone touched: `pixi run python -m pytest cli/tests` — **217 passed,
0 skipped, 181.85 s**. `test_walk.py`'s two real walks with the real engine and
trainer skip without a training venv and did not skip here.

## Result

The walk is green end to end on this machine, and the numbers are in
`docs/ROADMAP.md` beside the ADR-249 and ADR-250 entries they close out
(`1d2964c6`).

What is still missing before the *other* open walk criteria can be ticked, none
of it blocking: **Three modes, one shape** (`witty-spark-2613`) wants the
GUI-attached and remote-training legs documented against this run's shape, both
of which are documentation units under the headless-only constraint; **The walk
holds on a second mechanism** (`swift-dusk-2951`) wants the linear carriage taken
through this same entry point on this machine and its `PROGRESS.md` numbers put
beside these, which nt2 left close to done. Neither needs a code change that this
run has found.

Two smaller things for whoever takes the next unit. The unreconciled tail is
three nodes and the maintainer pass is due. And a walk on a fresh checkout must
`pixi run build-engine` first or it silently runs the previous runtime — the walk
does not check that the installed engine matches the tree, and it cost this unit
a full rebuild to notice.

Dispatch closed: 1 unit — one clean `cadex walk --prompt` end to end on this machine, exit 0 in 17:43, all four legs and all four review eyes, recorded in ROADMAP with `cli/tests` 217/217 green.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 1d2964c697c6abd12334fba7165d5fdf050877fc

## State Impact

- target: crisp-reef-5607 — the documented headless entry point ran end to end on this machine with no human step past documented flags: exit 0, 17:43, design/train/declare/rollout all exit 0, local CPU training 5x16 at reward/step -0.1254, verified rollout total_reward -0.1765, and cli/tests 217 passed 0 skipped including test_walk.py's real-engine walks
- target: damp-moon-9297 — the walk's review step exercised all four headless eyes in one run, landing under the project directory: render front/top/right/iso (13,432 triangles), section XZ at 3.125 mm, inventory 10 components / 7 catalogued, clearance bounds check pass over 45 pairs
