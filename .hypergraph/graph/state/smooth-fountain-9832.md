---
node_id: a42d8504-4b29-5497-8c42-2d9874704b88
slug: smooth-fountain-9832
title: R1. A quadruped walks with real steps
created_at: '2026-09-30T07:04:57+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run ot11: **R1. A quadruped walks with real steps.** - The final pre-registered confirmation evaluation passes the frozen walk spec on every evaluation seed, and meets the video judge's bar. - The policy is installed, verified and reopened through the supported path, on an accepted design. That design may be one of ot10's, copied into a new `ot11-*` project. - Every earlier training run and evaluation is published, including the failures. [rec: kind-spire-3578]

Declared target: `gap-r1-quadruped-walks-real-steps`. This node tracks the criterion as a gap; it becomes working only with causally parented, measured evidence that the criterion is met. The human owns the charter checkbox; roles report results and do not tick it. The directive's impact line is truncated; its wording is resolved from the full charter carried verbatim in the same record [rec: kind-spire-3578].

**R1 is not met: twelve walk rounds over four sessions, every one 0/10 or void (rows 13–25)** [rec: autumn-current-6021]. Session 1 (rounds 1–4, 8,357 GPU-s) [rec: northern-eagle-1465]; session 2 (rounds 5–7, 5,978 GPU-s) [rec: happy-cliff-3687]; session 3 (rounds 8–10, 6,284.29 GPU-s) [rec: terse-bramble-7437]; **session 4 is live** (rounds 11–12 published, `r14-margin15-lift` training) [rec: autumn-current-6021]. No passing evaluation exists; these are loop rounds, not confirmations.

- **Project.** `ot11-quad-1`, a `cp -a` copy of `ot10-quadruped-3-w2` at accepted revision `84ff4c98…`. Fixed mechanism for sessions 1–2 [rec: lively-ledge-7354]; since session 3 the agent may revise it within bounds (four legs, same feet, floor and global physics fixed, catalog actuators only), and **HIP_MM and WEIGHT_N must equal the revised model's rig, or the evaluation is void** [rec: red-mountain-4965].
- **Spec.** The frozen walk spec as a thirteen-predicate xscript block with a commanded-speed goal in [0.6, 1.0] hip heights/s (`retained/walk-spec-block.txt`, sha256 `487416af…`); W3 as `speed_ratio` in [0.75, 1.25], W4 as `lateral_ratio` ≤ 0.25 plus `max_heading_deg` ≤ 45; 10 s, tilt 0–3°, one 0.05–0.20 × weight shove for 0.15 s between 3 s and 7 s. An evaluation whose spec block differs from the retained one is void [rec: lively-ledge-7354]. Each published round checks: registered and evaluated revisions differ only in the `assembly.policy` line; the block tokenizes (379 tokens) as the frozen one but for WEIGHT_N's value; HIP_MM/WEIGHT_N equal the rig; all checkpoints record trainer `97bc1d9a…` [rec: rapid-peak-4236] [rec: autumn-current-6021]. W10 is read after the 1.0 s settle since ADR-467 (detail on `rough-shore-6557`) [rec: pale-ember-2389]. Since ADR-468 a spec can state `scale=`; the frozen block does not, and adopting it is a contract change [rec: keen-walrus-1609].
- **Sessions 1–2 (rounds 1–7), in one line each** (detail in REPORT.md and the record graph). r1-clearance collapsed, best checkpoint 0/10 backwards [rec: empty-bay-8350]; r2-bounded 0/10 backwards, dragged rear feet [rec: copper-sun-7929]; r3-nochatter 0/10 backwards [rec: windy-nest-5080]. **Rounds 1–3 trained on MJX physics that disagreed with the engine through saturated servos (ADR-465)**: their evaluations stand but say nothing about their reward designs (mechanism on `late-pond-2851`) [rec: long-badger-5117]. r4-anglesonly, first on the fixed trainer, stands still (W10 failure is its FL stance, −7.0 mm) [rec: northern-eagle-1465] [rec: square-crane-0130]. r5-swing walks forward and fails 0/10 (W3 9/10; FL paddles, RL dragged; W10 −0.209..−0.138 HH) [rec: pale-ember-2389]; r6-trot 0/10, both rear feet drag [rec: gilded-ridge-5195]; r7-relswing collapsed (ending an episode paid), iter-200 checkpoint 0/10 [rec: happy-cliff-3687].
- **Session 3 (rounds 8–10, closed)**, pre-registered at `fa8e61bc` [rec: red-mountain-4965]. r8-stance stands on one diagonal and is **void** on the HIP_MM digit [rec: rough-bell-4381]; r9-steelfoot a refused start (`attempt: false`) [rec: keen-walrus-1609] [rec: shady-pond-5657]; r10-steelfoot-fresh (steel-ball feet, 10.47 g) valid 0/10, **W10 passes every seed for the first time**, stands on three feet [rec: shady-pond-5657]; r11-speedpay valid 0/10, **the concave speed Gaussian was farmed by rocking in place** [rec: terse-bramble-7437]. Every session-3 reward found a different stationary optimum [rec: terse-bramble-7437].
- **Session 4 (live).** Pre-registered at 06:12:49Z (`retained/p4-quad-1-s4-preregistration.json`, prompts `walk.s4.loop` `ca1d1b99…` / `walk.s4.continue` `3a6e6f17…`); **no rule changed from session 3**: same mechanism bounds, spec block, seeds, trainer, driver; at most 3 runs of ≤ 2,400 s this session, `--stop-on-collapse`, 2 turns. Launched under `setsid` at 06:13:10Z. The actor did not instruct the agent to keep the steel feet; the mechanism is the agent's [rec: forest-stone-4700].
  - **Round 11 `r12-convex-sym`** (fresh, 800 it, 2,105.98 s; convex speed cost, signed swing pay, hover cost 0.15, `diag_sym`/`hip_antiphase` encoders, alive 5) **valid, 0/10**. First steel-foot policy to travel: W3 0.65–0.81 (5 of 10), both front feet step (6–11), but RL is held up on every seed (W8-low 0.00), RR drags (slip 0.85–0.98), tilt 23–28°. **W10 under a gait on steel feet is measured and fails** (−0.154..−0.074 HH; worst foot always a stepping front foot). Holding RL up cost 0.14/step against 0.49/step of slip for dragging RR. Receipt `retained/p4-quad-1-r12-evaluation.json` [rec: rapid-peak-4236].
  - **Round 12 `r13-hovercost-margin`** (fresh, seed 137, 800 it, 2,239.22 s; hover cost 0.6, tilt −40, alive 6, and **one mechanism change: `margin="0.003"` on the four foot collision geoms**) **valid, 0/10**: W3 0.28–0.64, W6 0.032–0.038 HH, W8-low 0.02–0.09 fail on all ten. **First ot11 walk policy with every foot stepping on every seed** (W5-steps 10/10), level body (tilt 3.6–6.8°), heading within 9° [rec: autumn-current-6021].
  - **Round 12's W10 pass is the margin, not a fix.** New reader `runner/rest_height.py` (recomputes foot heights from stored traces; refuses unless every settled minimum equals the stored one; agreed on all 30 seeds of rounds 10–12) shows the 3 mm margin holds every foot's median settled height at +1.5..+3.5 mm, against −3.1..+0.4 mm for a loaded foot in rounds 10–11; 48–96 % of settled frames sit between the 1.0 mm stance threshold and 4 mm, so W8 and W7 under-read stance and slip and W5 can count a forward-moving hover as a step. The verdict is a fail either way. Receipt `retained/p4-quad-1-r13-evaluation.json` [rec: autumn-current-6021].
  - **`r14-margin15-lift`** (fresh, seed 139, 2,400 s, registered 08:36:27Z) cuts the margin to 1.5 mm and is training. Publishing it must rerun `rest_height.py`: a 1.5 mm margin passes only if a loaded foot reads at or under 1.0 mm [rec: autumn-current-6021].
- **While a session is alive** (`pgrep -f "rounds.py --project ot11-quad-1"`), no other GPU job is started, and its registered prompt is not changed or the job killed mid-session [rec: lively-ledge-7354] [rec: windy-nest-5080]. A full `cli/tests` run puts JAX on the GPU (`test_walk.py::test_the_same_walk_handles_a_linear_carriage`); it failed with cuSolver errors while r12 held 24.7 GB [rec: forest-stone-4700], and passed while r14 trained [rec: autumn-current-6021]. Either way it breaks the one-GPU-job rule for its duration [rec: forest-stone-4700].

## Negative knowledge

- [scope: checking an xscript edit on a project copy | confidence: high | evidence: lively-ledge-7354] `cadex params` rewrites `script.py` from the accepted revision, so a hand edit followed by `params` is silently lost; the spec check was redone with `cadex script --set`.
- [scope: the frozen ot11 walk spec on ot11-quad-1 | confidence: high | evidence: autumn-current-6021] A foot contact margin of 3 mm lifts every resting foot above the 1.0 mm stance threshold, so W10 passes and W5/W7/W8 misread stance; nothing in the product refuses such a margin. Whether to close the hole is an unrecorded contract decision.
- [scope: ot11-quad-1 sessions 3–4 | confidence: medium | evidence: terse-bramble-7437, rapid-peak-4236] A concave speed Gaussian is farmed by rocking in place; a hover cost below the slip cost leaves holding a foot up as the cheapest answer.

## Provenance

- kind-spire-3578 — ot11 operator-declared charter gap
- lively-ledge-7354 — R1 started: ot11-quad-1 copied, full walk spec with speed goal pre-registered (626141c8), round 1 r1-clearance training
- empty-bay-8350 — walk round 1 r1-clearance collapsed at it 568; best checkpoint fails 10/10 (backwards, slip, sinking, idle rear legs); round 2 cites it (74debd53)
- copper-sun-7929 — walk round 2 r2-bounded finished without collapse, 0/10, still backwards with dragging rear feet; round 3 cites it; train/eval gap flagged (150988d9)
- long-badger-5117 — ADR-465: rounds 1–3 trained on MJX physics that diverged from the engine through saturated servos; evaluations stand, reward designs unevidenced
- windy-nest-5080 — walk round 3 r3-nochatter 0/10 still backwards on the pre-ADR-465 trainer (2a21210c); round 4 the first on the fixed trainer; save-time trainer_sha256 flagged
- northern-eagle-1465 — walk round 4 r4-anglesonly 0/10 standing still, train/eval gap closed; session 1 closed at 4 runs; session 2 pre-registered with ADR-465 in its prompt and launched (e4500356)
- square-crane-0130 — round 4's W10 failure is the policy's FL stance (−7.0 mm), not only the reset drop; any R1 policy must cushion its landing to pass W10 as frozen
- pale-ember-2389 — W10 settled re-read (ADR-467) moves no walk verdict; round 5 r5-swing walks forward and fails 0/10
- gilded-ridge-5195 — round 6 r6-trot published, 0/10: RL unchanged, rear pair dragged, slip 0.28–0.32
- happy-cliff-3687 — round 7 r7-relswing collapsed, iter-200 checkpoint 0/10; session 2 closed at seven rounds; session 3 may revise the mechanism
- red-mountain-4965 — session 3 diagnosed, pre-registered with a bounded mechanism revision (fa8e61bc) and launched
- rough-bell-4381 — round 8 r8-stance stands on one diagonal; evaluation void on the HIP_MM digit
- keen-walrus-1609 — r9 refused at start (warm start across a channel change), r10-steelfoot-fresh training; ADR-468 scale guard opt-in
- shady-pond-5657 — round 9 r10-steelfoot-fresh valid, 0/10: W10 passes every seed, stands on three feet; r9 published as a refused start
- terse-bramble-7437 — round 10 r11-speedpay valid, 0/10: rocks in place to farm speed pay, W10 holds; session 3 closed, no session 4 registered
- forest-stone-4700 — session 4 pre-registered with no rule changed and launched under setsid; r12-convex-sym training
- rapid-peak-4236 — round 11 r12-convex-sym valid, 0/10: travels on three legs; W10 under a gait on steel feet measured failing; r13 training
- autumn-current-6021 — round 12 r13-hovercost-margin valid, 0/10: every foot steps, but W10 pass and stance readings are a 3 mm margin artefact (rest_height.py); r14-margin15-lift training
