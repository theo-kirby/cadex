---
node_id: 9d4737b1-6325-5ed6-bd64-24d0b3df707b
slug: golden-dune-8756
title: Fresh crank-slider walk reaches geometry and stops at an MJX geom pair
created_at: '2026-09-09T03:19:57+00:00'
parents:
- salty-wolf-2393
summary: ''
---
## What

Dispatched the fresh mixed-joint crank-slider walk as the iteration's first action, into a new empty project (`ot4-mix52`), with no `--resume` and no supplied script. **The design leg succeeded** — the first fresh mixed-joint geometry this run has evidenced — and the train leg failed on an MJX limitation. Then fixed the defect that run exposed: a failed training leg did not name its cause in the machine-readable envelope (ADR-280).

## Why

Advances charter criterion **The walk exists and is tested headlessly** (`crisp-reef-5607`), per the overseer's explicit instruction to dispatch first and take whatever it returned as the result, and the short plan's unit 1. Iteration 48's attempt was refused by the provider before geometry; this one reached and passed design, so the crank-slider linkage question is now answered: the engine, the solver and the MJCF export all accept it.

The train failure was the leg that needed a guess, and it needed one for a reason worth fixing rather than working around: `walk.json` named the wrong cause. Choosing the tee over capture-and-replay is the reversible option — live progress on stderr is a documented contract (`docs/CLI.md` §2, ADR-093) and the tee preserves it byte for byte, where capturing would have held a 10-minute training run's progress until it ended.

Assumption written down rather than asked: the MJX cylinder-box gap is a real constraint on what a design turn may author, not a bug to fix in this repo. It is recorded in `docs/CLI.md` §2 as guidance for the next design turn (prefer capsule or box collision geometry for a rail, or mark it contact-free); the engine is not changed to work around a trainer limitation.

## Method

Rebuilt and installed the engine first (`pixi run build-engine`, exit 0) because the checkout carried one differing top-level Python file against the install; the walk's own comparison then reported `match` across 56 files.

Ran, from `/home/theo/cadex`, into `~/cadex-projects/ot4-mix52` (created empty):

`JAX_PLATFORMS=cpu CADEX_MODEL=claude-opus-5 ./cadex walk --project "$P" --prompt "$PROMPT" --out "$P/runs/fresh52" --name fresh52.cxpolicy --iterations 5 --envs 16 --seed 0 --timeout 600 --leg-timeout 1800 --json`

The prompt asked for a grounded frame, a position-servo revolute crank, a coupler, a prismatic slider on a rail, real masses, one small CPU task using the `policy_on` convention, and the project docs; it explicitly prohibited substituting disconnected parts. A local Python monitor sampled process-tree RSS every 0.2 s under a 2.9 GiB guard.

The fix: `run_trainer` in `cli/cadex_cli/train.py` replaces `subprocess.run(stderr=None)` with a `Popen` whose stderr is drained by a thread that writes each line through to `sys.stderr` and keeps the last four in a bounded deque; a second thread drains stdout so neither pipe can deadlock. A nonzero exit now appends the stdout tail (the remote dispatcher's `FAIL:` lines) and then the stderr tail. The regression drives a real subprocess printing the two benign lines on stdout and a traceback on stderr, and asserts both that the error names the cause and that stderr still passed through live.

## Result

**Walk: exit 1 in 1138.30 s; peak process-tree RSS 729,931,776 bytes; the watchdog did not intervene.** Model actually passed to the child: `claude-opus-5`.

Per leg:

- **design — exit 0, 1135.85 s.** Accepted revision `3892e8cdb5ab…`, digest `df4ee45fb590…`. A four-body closed-loop planar slider-crank: grounded frame (base plate, crank post, round guide rail on two posts, 389.6 g), an 11.3 g crank on a revolute driven by a 250 N·mm position servo, a 25.7 g coupler, a 38.3 g slider block bored onto the rail on a prismatic joint. Mobility 1, four tree coordinates, one MuJoCo `connect` closure, worst closure residual 0.0015 mm over a 2 s driven run, peak servo effort 17.3 N·mm unsaturated, zero initial contacts. The agent refused the all-revolute version (Ondsel reported it redundant by three in 3D) and spent those constraints on a cylindrical crank pin and a ball wrist pin rather than disconnect anything, which is exactly what the prompt forbade it from faking. Task `slider_tracking`: 100 steps, 50 Hz, one action, eight observation channels, four reward terms. Four `DECISION:` lines and three notes (`linkage-geometry`, `actuators`, `sensors`) landed. One recoverable in-leg refusal: an early `write_script` violated the no-imports policy and the agent corrected it.
- **train — exit 1, 2.27 s.** `mjx.put_model` raised `NotImplementedError: (mjtGeom.mjGEOM_CYLINDER, mjtGeom.mjGEOM_BOX) collisions not implemented`. The guide rail is a cylinder against box bodies; the MJCF is valid MuJoCo and untrainable under MJX. No policy, no weights.
- **declare, rollout — not reached.**
- **render, section, inventory, clearance — not reached; review block empty.** Total reward and witness error unavailable.

**The leg that needed a guess was `train`, and it needed one because the envelope lied.** `walk.json`'s `error` quoted only `Failed to import warp: No module named 'warp'` twice — harmless startup noise on stdout — while saying "its stderr is above", which is nothing a `--json` caller has. That is now fixed.

Validation: `JAX_PLATFORMS=cpu pixi run python -m pytest cli/tests` exited 0 — **289 passed in 222.98s**. The new test was run against `git show HEAD:cli/cadex_cli/train.py` and **fails on the previous source** (1 failed), passes on the new. `git diff --check` clean. No engine or shell code changed, so no engine suite or shell gate was required for the zone; the engine build that preceded the walk was for freshness, not for this diff.

Local evidence stays out of Git in `~/cadex-projects/ot4-mix52/runs/fresh52/{walk.json,walk.stderr,monitor.json}`; the commit carries only source, tests and docs.

What is still missing before **The walk exists and is tested headlessly** can be ticked: a fresh mixed-joint run that gets past `train` — which now means a design turn whose collision geometry MJX supports — and then through declare, rollout and all four review calls. The geometry half of that criterion is evidenced; the training half is not. The tail is now four unreconciled records; the contributor did not reconcile.

Dispatch closed: 1 unit — fresh crank-slider walk reached geometry and stopped at an MJX geom-pair limit; the failed leg now names its cause.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: a8287b22f239f464ca8a8ebfd7a8795c1bec9117

## State Impact

- target: crisp-reef-5607 — Fresh from-nothing mixed-joint walk (ot4-mix52, claude-opus-5) passed design: exit 0 in 1135.85 s, accepted revision 3892e8cd, a closed-loop four-body slider-crank with mobility 1 and 0.0015 mm worst closure residual, DECISION lines and linkage-geometry/actuators/sensors notes landed. Train failed in 2.27 s on mjx.put_model NotImplementedError for the cylinder-box geom pair; declare, rollout and all four eyes not reached, review block empty. 1138.30 s total, 729,931,776 bytes peak tree RSS, no watchdog intervention. The train leg's --json error now carries the trainer's stderr tail rather than two benign stdout warnings (ADR-280); 289 CLI tests pass and the regression fails on the previous source.
