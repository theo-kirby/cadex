---
node_id: dbfb76dd-2401-5f9f-8fb7-87cc652c5c19
slug: salty-isle-4063
title: Dynamics and control on MuJoCo
created_at: '2026-08-09T15:22:03+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Dynamics and control is ordinary product surface on the one branch, not a vertical on a fork [rec: open-key-6334]. It is operations on the existing `assembly` domain — **no sixth domain, no protocol op, no output type of its own** — which is why the whole arc cost so little contract [rec: sage-wood-0687].

- The arc runs end to end: `assembly.dynamics` simulates a solved assembly with exact OCCT inertias, `assembly.mjcf` exports one self-contained file that loads in a stock MuJoCo and verifies its own output before returning it, `assembly.task` states a control problem as data, `assembly.policy` verifies returned weights against a recorded witness, and `assembly.rollout` plays it back in the viewport [rec: sage-wood-0687].
- **Live mode**: a running mechanism the user can push with the mouse, at **344 µs a control step (29× real time)** and a 1.72 ms median round trip against a 33 ms bar, identical from the staged payload. `endless` plus `record_steps=False` makes a half-hour session cost +1.6 MB instead of +553 MB [rec: mellow-hawk-8610].
- MuJoCo is a **kernel we keep, not a tree we fork** — upstream, unmodified, and `mujoco == 3.10.0` exactly pinned, arriving as a pypi wheel carried by name because the conda manifest is not re-solvable against the `occt` pin [rec: sage-wood-0687].
- **Three invariants, all test-pinned and all cheap to break by accident**: nothing in `shell/` imports mujoco; `CadexDynamics.py` is reachable from the sandboxed worker and **never** from `cadexd`; and no `jax` or `mjx` anywhere under `src/Mod/cadex` or in a staged payload [rec: sage-wood-0687].
- Two observation kinds were added by the RL work and cost one table row each: `centre_of_mass_velocity` and `centroidal_angular_momentum` [rec: humble-path-4466].
- MJX and stock MuJoCo are the same physics to float64 machine epsilon with collision disabled and with a `plane` floor. They differ **only about box against box** — which is what `export_mjcf` writes for every grounded body [rec: humble-path-4466].
- **A published rollout trace is also a load-case source**, and this needed nothing new from the engine. `analysis/loads_from_rollout.py` replays a `cadex-assembly-simulation-trace-v1` in stock MuJoCo and reads `mj_rnePostConstraint`'s `cfrc_int` (the joint reaction wrench between a body and its parent) and `cfrc_ext` (contact and applied) — so `contact_force` being a deferred *engine* observation does not block structural work on mechanism parts, because this runs offboard [rec: fair-beacon-5964].

**Open defect: `assembly.mjcf` does not return for a ten-component catalog rig on the dev-tree engine.** On the ot4 machine a walk-designed one-servo swing-arm rig (MG90S from the catalog, printed base plate, retainer and swing arm, six M3 bolts and nuts, 10 components, 3 joints) hit four separate 300 s worker kills — returncode −24, SIGXCPU — on `assembly.mjcf` and `assembly.dynamics`, so the design agent gated its whole training layer off behind `policy_on=0` and the walk failed at `train`. **The export as such is not the fault**: in fresh projects on the same engine, a grounded one-body model with a box collision builds in 0 s, the reference `linear-carriage` builds in 0.55 s with `box`, 1 s with `mesh` and 0 s with `hull` (and `plane` is correctly refused by MuJoCo outside a static body), and the rig's own script rebuilds geometry-only in 1 s — then burns **exactly 300 s** at `params --set policy_on=1`. The fault is somewhere in that rig's dynamics declarations (per-component collisions, a servo actuator with real limits, observations, sensors, two ranged `assembly.disturbance` values, a reward list) and a bisect over them is the named next unit. This falsifies the design agent's own narrower claim, written into that project's `docs/rejected.md`, that a single grounded box with one box collision exhausts the cap [rec: open-hollow-2140].

Reconcile judgement: status stays `working`. The stall is real and blocks the lifecycle walk on this machine (`crisp-reef-5607`), but it is bounded to one unbisected rig against controls that all pass in under a second, so it does not establish that the dynamics surface itself is broken [rec: open-hollow-2140].

**These are the newest and least settled surfaces in the product.** The author rates the training and demonstration panels as "not fully fleshed out — most of what you need, but not quite" [rec: western-badger-3023].

## Negative knowledge

- [scope: CadexDynamics imports | confidence: high | evidence: sage-wood-0687] mujoco and scipy.spatial must stay deferred imports inside functions. A service whose job is reading NDJSON off a pipe does not need 53.5 MB of physics engine resident, and test_engine_purity_guardrails asserts cadexd's import closure exactly.
- [scope: MuJoCo defaults | confidence: high | evidence: sage-wood-0687] A default is a promise, not a decision. Every MuJoCo option the translator depends on is set explicitly and re-asserted on the compiled model; moving one is a measurement, not an edit.
- [scope: reading a wrench out of MuJoCo | confidence: high | evidence: fair-beacon-5964] `cfrc_int` and `cfrc_ext` are **com-based**: the torque is about `subtree_com[body_rootid[body]]`, not about the body. Read without moving it onto the body (`t_p = t_c + (c - p) x F`), the forces still check out and the moments are wrong by `r x F` — which on a leg is the whole number. The failure is silent in exactly the way that survives a review.
- [scope: replaying a trace to measure anything | confidence: high | evidence: fair-beacon-5964] A replay is only the rollout if it **tracked** the rollout, so check it frame by frame against the trace's own recorded poses rather than assuming. Author a rollout at `frames_per_second` equal to the control rate when you intend to read loads off it: a trace sampled more coarsely holds only some of the actions, and measured on a two-link leg the same motion recorded half as often replayed **142 mm** away from itself where an exact one replays to 0.0 mm. The trace's frame convention is the other trap — an untimed `input` frame, then an **unstepped** `solver_output` at t=0 carrying no commands, then one frame per action.
- [scope: a worker kill on a long dynamics op | confidence: high | evidence: open-hollow-2140] The sandbox cap is an `RLIMIT_CPU` in **CPU-seconds** (`cadex_domain_worker.py:_resource_limits`, `DEFAULT_SCRIPTED_TIMEOUT_SECONDS = 300.0`) while the parent's timeout is the same number in **wall-clock** seconds. A threaded pass on a many-core box reaches the CPU limit first and dies by SIGXCPU, surfacing as the opaque `The isolated domain worker exited without a result` rather than as a budget refusal. Script-level `print(..., flush=True)` is lost on that kill, so instrumenting from inside the script cannot locate the stall — bisect the declarations from outside instead.
- [scope: trajectory comparison on a contacting biped | confidence: high | evidence: humble-path-4466] Trajectory-level agreement between MJX and stock MuJoCo can never be had — a 1e-7 nudge inside stock MuJoCo alone separates the trajectory just as fast. The two are comparable statistically and in no other way.

## Provenance

- sage-wood-0687 — the whole M0-M8 arc, the dependency and the three invariants
- open-key-6334 — why it is product surface on one branch rather than a vertical on a fork
- mellow-hawk-8610 — live mode and its measured numbers
- humble-path-4466 — the two observation kinds and the MJX/MuJoCo comparison
- western-badger-3023 — the author's own rating of how settled these surfaces are
- fair-beacon-5964 — a rollout trace read offboard as a structural load case, and the two ways that is silently wrong
- open-hollow-2140 — `assembly.mjcf` stalls to SIGXCPU on a ten-component catalog rig while one-body and reference-carriage controls build in under a second; the fault is in that rig's dynamics declarations, not in the export
