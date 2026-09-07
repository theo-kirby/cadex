---
node_id: 07285db2-b997-5129-9a6c-181697a82113
slug: swift-dusk-2951
title: The walk holds on a second mechanism
created_at: '2026-09-06T19:18:34+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion: **The walk holds on a second mechanism.** The same entry point, with no code change specific to the mechanism, takes a second mechanism through the whole loop, and both projects' `PROGRESS.md` carry comparable numbers. Declared target `gap-walk-holds-second-mechanism-same` [rec: empty-wolf-3962]. The nt3 operator directive re-seeded it unticked: "finish and evidence it rather than restarting it" [rec: modest-summit-8554].

**Met, 2026-09-07: the same `cadex walk --prompt` entry point took a second prompt-designed mechanism through the whole loop — design included — with no code change of any kind** [rec: placid-sky-7374]. The tree was unchanged at `dfeccc9f` with `git status` clean, and both prompt-walk projects' `PROGRESS.md` files carry the same rows with the same metric definitions:

| project | mechanism, joint, actuator | design | train | declare | rollout | wall | peak RSS | `total_reward` |
|---|---|---|---|---|---|---|---|---|
| `prompt-walk-nt3b` [rec: cool-fountain-2483] | pendulum rig, revolute, position servo | 262.03 s | 14.50 s | 1.43 s | 1.76 s | 280.7 s | 1.23 GB | 425.997 (`lift_height` +427.193, `effort_cost` -1.194, `speed_cost` -0.001) |
| `prompt-walk-nt3c` [rec: placid-sky-7374] | vertical carriage, prismatic, force motor | 172.59 s | 13.06 s | 1.25 s | 1.50 s | 189.4 s | 1.115 GB | 0.0035556 (`lift` +0.0035706, `effort_cost` -1.4984e-05) |

Both at 1 iteration × 4 environments (seeds 0 and 1), both `--timeout 600`, both verified against the engine witness (4.48e-09 and 3.679e-09). The second mechanism differed in prompt, joint type (prismatic, not revolute) and actuator type (bounded force `motor`, not a position servo), and the walk's digest edit rewrote its `assembly.policy(...)` call with no refusal [rec: placid-sky-7374].

**Earlier evidence, from installed recipes (nt2, ADR-203)** [rec: sage-peak-2689]: the unchanged `cadex walk` trained, declared and verified an ideal vertical slider/force-motor carriage beside a fresh revolute/torque-motor hinged-arm baseline, both repository-owned projects carrying source, architecture/decision/sensor docs and comparable `PROGRESS.md` definitions; rollout totals -27.1093842209 / -24159.1953563, walks 15.22 / 13.52 s, RSS below 1 GB, CLI suite 138 with no skips. What that left open — the loop starting at design, from `--prompt`, on a mechanism that is not an installed recipe — is what the nt3c run supplies.

Reconcile judgement: flipped `open` → `working` on the declared MET impact [rec: placid-sky-7374]; the node had been held open only because the walk did not yet complete from `--prompt` on any mechanism, and it now completes on two (`crisp-reef-5607`). The honest caveat is carried as negative knowledge: comparable columns, incomparable objectives.

## Negative knowledge

- [scope: one-iteration linear-carriage qualification | confidence: high | evidence: sage-peak-2689] Working-level evidence denotes pipeline qualification, not control quality or hardware validation: the carriage falls to origin z=-4699.378313 mm at 1 s on an ideal unlimited guide. Torque and force costs use different units, so these rewards do not rank designs. Only source, docs and numbers are versioned in the parent repository; policy assets, checkpoints, traces and accepted caches remain untracked.
- [scope: comparing the two prompt-walk projects' `total_reward` | confidence: high | evidence: placid-sky-7374] The columns and their definitions are the same, but the two reward expressions are different objectives in different units, so the totals compare runs of the same project and never rank designs against each other — the caveat `examples/lifecycle/README.md` already records for the example mechanisms, unchanged here. One PPO iteration is a smoke test of the loop, not a claim about learned control.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- sage-peak-2689 — second mechanism qualifies through the unchanged walk with baseline metrics and real CLI tests; control quality remains poor
- modest-summit-8554 — nt3 operator directive re-seeds the criterion unticked: finish and evidence it rather than restarting it
- cool-fountain-2483 — the first prompt-designed mechanism (pendulum rig) through the walk, the baseline the second is compared against
- placid-sky-7374 — a second prompt-designed mechanism (vertical carriage, prismatic, force motor) through the unchanged entry point, both PROGRESS.md files comparable; the criterion declared met with the objectives-differ caveat
