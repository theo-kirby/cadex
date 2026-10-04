---
node_id: 0d1755fd-e113-53fb-9393-31d06b2ce68d
slug: shady-clover-5534
title: W1. Nothing the product could do headlessly was lost (orun2)
created_at: '2026-10-03T10:54:47+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Open charter criterion for run orun2: **W1. Nothing the product could do headlessly was lost.** - On a copy of an existing robot project, the whole walk runs and every step is visible in the dashboard: 1. prompt; 2. accepted design; 3. params sweep; 4. `look` and render; 5. STEP/STL export; 6. MJCF export; 7. a short training run on the 5090; 8. `evaluate`. - Both full suites pass, and so does the packaged lifecycle gate. - The CLI and dashboard have no feature the shell parity ledger below marks "ported" without a test. - **The parity ledger is complete:** `docs/SHELL-PARITY.md` gives each of these one row: - every `mesh_agent` module; - each of its 23 tools; - each of the seven Cadex editors. Each row says one of three things: **ported** (where, and the test), **already covered** (where), or **dropped** (why, and the ADR). No row is blank. [rec: winter-stone-5109]

**Every part of the criterion has evidence; the 5090 leg is closed** [rec: solemn-birch-8260] [rec: rough-bell-4055].

**Walk: all eight steps ran on copies of real robot projects, each seen in the dashboard.** Steps 1–6 ran on `orun2-w1-quad`, a copy of `ot11-quad-1` (`docs/probes/orun2/w1/walk_dashboard.py`, `walk-steps.json`): the prompt was accepted as `a7d487ae`; Accept verdict, 62 components; `shin` sweep 3/3; render on the Concept tab; Export 62 STEP + 62 STL; MJCF with 8 actuators, plus the task JSON [rec: red-loom-2239]. Steps 7–8 ran on `orun2-w1-robin`, a copy of `ot11-robin-1` (`walk_train_dashboard.py`) [rec: dusty-bramble-8099].

- **Step 7 on the RTX 5090** (`a320a489`, run `w1-gpu-1`): `cadex walk` at r3-ppo-1's budget, 300 it × 1024 envs, seed 1001. Exit 0 in 517.5 s wall; trainer 331.1 s; receipt `device: gpu`, policy `dbd3913e` on task `d50e953b`. Reward/step rose 0.167 → 0.950; median episode length 500/500 over iterations 250–299. Accepted as `bf914476`. Seed-0 rollout stayed upright for all 501 frames, max tilt 6.79° [rec: rough-bell-4055].
- **Step 8:** `cadex evaluate` **passed 10/10 seeds**, with B1–B5 each 10/10 (tilt ≤ 6.35° against a 30° bound, recovery ≤ 1.80 s against 2 s). Both runs show in the dashboard: the Curves tab marks `w1-gpu-1` current at iteration 299/300, and the Evaluation tab shows "pass: 10 of 10 seeds", with the earlier CPU run's 0/10 listed as historical. `w1-7-training.png` and `w1-8-evaluate.png` were re-shot [rec: rough-bell-4055].
- The earlier CPU deviation (no `nvidia` module on 7.0.0-34, run `w1-cpu-2`, 0/10) is superseded: the driver is loaded (580.178.04), and JAX sees `CudaDevice(id=0)` [rec: dusty-bramble-8099] [rec: rough-bell-4055]. The policy binary and the rollout trace stay in the project copy and are not committed [rec: rough-bell-4055].

**Parity ledger complete, with no "to port" row.** §1 has 47 module rows, §2 has 23 tool rows and §3 has 7 editor rows. None is blank and none still says "to port" [rec: neat-grove-1406]. The audit found every cited test passing [rec: mellow-fjord-5906]. Six rows were ported after the audit, each with its test:
- `modes.py` (ADR-521) [rec: autumn-rose-7173];
- `cadex_roles.py`, `cadex_print.py` and Parameters (ADR-522) [rec: winter-hill-2339];
- `agent.py` per-turn tokens and cost (ADR-523) [rec: copper-cliff-1990];
- `cadex_dimension.py`'s in-viewer overlay (ADR-524, `cli/tests/test_dashboard_dimensions.py`, including a real-engine headless-Chromium test). The viewer draws the script's declared `part.measurement` records from the accepted `result.json` as an SVG over the canvas, and redraws each frame [rec: neat-grove-1406].

Ported earlier: blueprint (ADR-516) [rec: sweet-arrow-0695], `prefs.py` (ADR-517) [rec: curious-flint-4836], and `model.py`/`history.py`/`ui.py` [rec: mellow-fjord-5906]. Two "owner to confirm" rows remain, face-level pins and the face-ID channel. They stay with the owner [rec: neat-grove-1406].

**Gates, on `9fc13812`** [rec: neat-grove-1406] [rec: solemn-birch-8260]:
- `pixi run test-engine`: 2607 passed, 56 skipped [rec: neat-grove-1406].
- CLI suite with the GPU hidden: 1412 passed, 1 skipped [rec: neat-grove-1406].
- Packaged lifecycle gate: **24 passed** against the payload staged from `ef69dd39`. Since then, the only change under `src/Mod/cadex`, `package`, `src/App` and `src/Base` is one test file, so the payload's engine code is HEAD's [rec: solemn-birch-8260] [rec: icy-tooth-7719]. It was not re-run for the GPU leg, because the payload did not change [rec: rough-bell-4055].
- Later, at `a320a489`: CLI suite with the GPU hidden, run during live training, **1420 passed, 1 skipped**. The engine suite was not re-run, because that commit is docs and probes only [rec: rough-bell-4055].

The rollout-playback timing flake is fixed: the test now waits for `#play-toggle` to be enabled, and it did not recur in a full run [rec: neat-grove-1406]. The pre-ADR-469 lock is resolved (ADR-520) [rec: icy-tooth-7719].

**Residual walk findings. These are polish, not lost capability, and moved to C1's defect list** [rec: solemn-birch-8260]:
- the robot was a speck until **Fit**. Fixed by ADR-525, see `wild-ocean-3878` [rec: clear-current-6218];
- debug colours. ADR-522 may have fixed this, but it is unverified [rec: solemn-birch-8260];
- a CLI turn's transcript and `look` images do not appear on the project page [rec: red-loom-2239].

Reconcile judgement: flipped `open` → `working`. The claim is evidenced end to end. With the 5090 leg closed and evaluate at 10/10, nothing run-side is owed [rec: rough-bell-4055]. Status stays `working` and does not go to `done`, because the human owns the charter checkbox [rec: solemn-birch-8260]. Declared target: `gap-w1-nothing-product-could-do`. Every orun2 gap title carries the run [rec: winter-stone-5109].

## Negative knowledge

None yet.

## Provenance

- winter-stone-5109 — orun2 operator-declared charter gap
- old-arrow-4088 — SHELL-PARITY.md skeleton: 47 module / 23 tool / 7 editor rows, none blank, statuses interim
- sweet-arrow-0695 — blueprint ledger rows ported: draw_blueprint and the Drawings panel, tested (ADR-516)
- curious-flint-4836 — prefs.py ledger row ported: engine budgets belong to the project, tested (ADR-517)
- amber-moon-9415 — both full suites green at 21d130f5; restart flake and viewer-settle race fixed in test logic
- red-loom-2239 — W1 walk steps 1–6 on orun2-w1-quad, each seen in the dashboard; pre-ADR-469 trained projects unopenable
- icy-tooth-7719 — ADR-520 unlocks pre-ADR-469 projects; packaged gate and both suites green
- dusty-bramble-8099 — walk steps 7–8 on orun2-w1-robin seen in the dashboard; CPU because the 5090 driver is not loaded
- mellow-fjord-5906 — parity ledger audited: 77 rows, all cited tests pass, six rows still to port
- autumn-rose-7173 — modes.py row ported: §4 guidance settled in CLI_OVERLAY (ADR-521)
- winter-hill-2339 — cadex_roles.py, cadex_print.py and Parameters rows ported: appearance roles and printable roster in the dashboard (ADR-522)
- copper-cliff-1990 — agent.py row ported: per-turn tokens/cost and text-tool-call warning (ADR-523)
- neat-grove-1406 — cadex_dimension.py viewer overlay ported (ADR-524); ledger has 0 to-port rows; playback flake fixed; suites green on 9fc13812
- solemn-birch-8260 — W1 claimed for critic review: walk 1–8, ledger complete, gates 2607/1412/24; 5090 leg owner-blocked
- clear-current-6218 — walk finding "robot a speck until Fit" fixed by ADR-525
- rough-bell-4055 — step 7 on the RTX 5090 (300 it × 1024 envs, device gpu), evaluate pass 10/10, seen in the dashboard; CPU deviation and REPORT defect 5 closed
