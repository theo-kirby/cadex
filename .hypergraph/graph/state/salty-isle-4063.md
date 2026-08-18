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

**These are the newest and least settled surfaces in the product.** The author rates the training and demonstration panels as "not fully fleshed out — most of what you need, but not quite" [rec: western-badger-3023].

## Negative knowledge

- [scope: CadexDynamics imports | confidence: high | evidence: sage-wood-0687] mujoco and scipy.spatial must stay deferred imports inside functions. A service whose job is reading NDJSON off a pipe does not need 53.5 MB of physics engine resident, and test_engine_purity_guardrails asserts cadexd's import closure exactly.
- [scope: MuJoCo defaults | confidence: high | evidence: sage-wood-0687] A default is a promise, not a decision. Every MuJoCo option the translator depends on is set explicitly and re-asserted on the compiled model; moving one is a measurement, not an edit.
- [scope: reading a wrench out of MuJoCo | confidence: high | evidence: fair-beacon-5964] `cfrc_int` and `cfrc_ext` are **com-based**: the torque is about `subtree_com[body_rootid[body]]`, not about the body. Read without moving it onto the body (`t_p = t_c + (c - p) x F`), the forces still check out and the moments are wrong by `r x F` — which on a leg is the whole number. The failure is silent in exactly the way that survives a review.
- [scope: replaying a trace to measure anything | confidence: high | evidence: fair-beacon-5964] A replay is only the rollout if it **tracked** the rollout, so check it frame by frame against the trace's own recorded poses rather than assuming. Author a rollout at `frames_per_second` equal to the control rate when you intend to read loads off it: a trace sampled more coarsely holds only some of the actions, and measured on a two-link leg the same motion recorded half as often replayed **142 mm** away from itself where an exact one replays to 0.0 mm. The trace's frame convention is the other trap — an untimed `input` frame, then an **unstepped** `solver_output` at t=0 carrying no commands, then one frame per action.
- [scope: trajectory comparison on a contacting biped | confidence: high | evidence: humble-path-4466] Trajectory-level agreement between MJX and stock MuJoCo can never be had — a 1e-7 nudge inside stock MuJoCo alone separates the trajectory just as fast. The two are comparable statistically and in no other way.

## Provenance

- sage-wood-0687 — the whole M0-M8 arc, the dependency and the three invariants
- open-key-6334 — why it is product surface on one branch rather than a vertical on a fork
- mellow-hawk-8610 — live mode and its measured numbers
- humble-path-4466 — the two observation kinds and the MJX/MuJoCo comparison
- western-badger-3023 — the author's own rating of how settled these surfaces are
- fair-beacon-5964 — a rollout trace read offboard as a structural load case, and the two ways that is silently wrong
