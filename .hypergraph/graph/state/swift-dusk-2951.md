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
| pan-tilt scratch project [rec: empty-banner-7438] | pan-tilt head, two revolute in series, two catalog MG90S position servos | 347.25 s | 17.49 s | 1.54 s | 1.74 s | 371.70 s | 1.419 GB | -2380.357 (closeness +2.826, tracking cost -2383.181, effort cost -0.0014) |
| pan-tilt scratch project, refreshed bundle [rec: morning-summit-7848] | pan-tilt head, same prompt, servo bodies fused into hand-authored solids | 374.52 s | 24.65 s | 1.52 s | 1.72 s | 406.33 s | 1.750 GB | -237.568 (`pan_error` -151.349, `tilt_error` -86.218, `effort` -1.686e-06) |

All at 1 iteration × 4 environments (seeds 0, 1, 0 and 0), all `--timeout 600`, all verified against the engine witness (4.48e-09, 3.679e-09, 4.028e-09 and 2.882e-09). The second mechanism differed in prompt, joint type (prismatic, not revolute) and actuator type (bounded force `motor`, not a position servo), and the walk's digest edit rewrote its `assembly.policy(...)` call with no refusal [rec: placid-sky-7374].

**Earlier evidence, from installed recipes (nt2, ADR-203)** [rec: sage-peak-2689]: the unchanged `cadex walk` trained, declared and verified an ideal vertical slider/force-motor carriage beside a fresh revolute/torque-motor hinged-arm baseline, both repository-owned projects carrying source, architecture/decision/sensor docs and comparable `PROGRESS.md` definitions; rollout totals -27.1093842209 / -24159.1953563, walks 15.22 / 13.52 s, RSS below 1 GB, CLI suite 138 with no skips. What that left open — the loop starting at design, from `--prompt`, on a mechanism that is not an installed recipe — is what the nt3c run supplies.

Reconcile judgement: flipped `open` → `working` on the declared MET impact [rec: placid-sky-7374]; the node had been held open only because the walk did not yet complete from `--prompt` on any mechanism, and it now completes on two (`crisp-reef-5607`). The honest caveat is carried as negative knowledge: comparable columns, incomparable objectives.

**Fresh complete-review corroboration (2026-09-08).** The carriage again passes the unchanged public script/walk route with the arm's bounded CPU settings (one iteration, four environments, seed 0, timeout 600). Both projects commit comparable reward, witness and review measurements and inspected named views/sections, truthful inventory and named-pair results. Carriage/arm witness errors are 5.4189e-09/1.3841e-09; rollout totals are -24159.1953563/-27.1093842 over 50 steps. Both source projects are clean and retained artifacts match committed bytes. The carriage's full built-engine CLI gate records 195 passed, zero skipped. This corroborates the existing working status at toy pipeline scale: carriage still falls under gravity, force and torque costs use different units, and GUI/SSH were not exercised [rec: quiet-vine-3426].

**A third mechanism through the unchanged entry point (2026-09-08).** The same `cadex walk --prompt`, against the refreshed installed bundle with the tree unchanged and clean at `a31cb828`, designed and carried a two-axis pan-tilt head — the first serial two-DOF chain and the first walked mechanism built from catalog parts (two `servo/mg90s`). Four legs exit 0, no mechanism-specific code, and the project's `PROGRESS.md` carries the same rows and metric definitions as the two earlier prompt-walk projects. Reconcile judgement: retain `working`; this corroborates the criterion on a third topology and adds nothing it needs. The clearance numbers its review leg reported for the catalog servos were false, a review-surface defect owned by `damp-moon-9297`, not a walk defect [rec: empty-banner-7438].

**A fourth variant through the unchanged entry point, on the refreshed installed bundle (2026-09-08).** The same `cadex walk --prompt`, with no repository source changed and the tree clean, took the pan-tilt prompt through design, train, declare, rollout and review again against the `.app` refreshed with ADR-241 and ADR-242: four legs exit 0, six project commits, clean status, and `PROGRESS.md` rows with the same definitions as the three earlier prompt-walk projects. The design turn produced a different mechanism from the same prompt — the servo bodies fused into three hand-authored solids rather than placed as catalog components — which is a fourth variant through one entry point with no mechanism-specific code, and also the reason this walk says nothing about catalog-part review. Reconcile judgement: retain `working`; corroboration only, nothing the criterion still needs [rec: morning-summit-7848].

**The selected two-servo leg adds no mechanism evidence.** Its design leg was refused by provider session quota before authoring, so there is no accepted design, comparable `PROGRESS.md` row, inventory classification or review artifact. Reconcile judgement: retain `working` on the existing mechanisms; the planned leg rehearsal still requires a retry after quota availability, which this record does not establish [rec: silent-mist-5233].

## Negative knowledge

- [scope: one-iteration linear-carriage qualification | confidence: high | evidence: sage-peak-2689] Working-level evidence denotes pipeline qualification, not control quality or hardware validation: the carriage falls to origin z=-4699.378313 mm at 1 s on an ideal unlimited guide. Torque and force costs use different units, so these rewards do not rank designs. Only source, docs and numbers are versioned in the parent repository; policy assets, checkpoints, traces and accepted caches remain untracked.
- [scope: two walks from one prompt | confidence: high | evidence: empty-banner-7438, morning-summit-7848] The same pan-tilt prompt yielded two different assemblies (placed catalog servos, then fused servo bodies) and two different reward expressions (-2380.357 and -237.568). Same prompt is not same design, so even same-prompt totals do not compare across runs; only reruns of one accepted project do.
- [scope: comparing the prompt-walk projects' `total_reward` | confidence: high | evidence: placid-sky-7374, empty-banner-7438] The columns and their definitions are the same, but the reward expressions are different objectives in different units, so the totals compare runs of the same project and never rank designs against each other — the caveat `examples/lifecycle/README.md` already records for the example mechanisms, unchanged here. One PPO iteration is a smoke test of the loop, not a claim about learned control.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- sage-peak-2689 — second mechanism qualifies through the unchanged walk with baseline metrics and real CLI tests; control quality remains poor
- modest-summit-8554 — nt3 operator directive re-seeds the criterion unticked: finish and evidence it rather than restarting it
- cool-fountain-2483 — the first prompt-designed mechanism (pendulum rig) through the walk, the baseline the second is compared against
- placid-sky-7374 — a second prompt-designed mechanism (vertical carriage, prismatic, force motor) through the unchanged entry point, both PROGRESS.md files comparable; the criterion declared met with the objectives-differ caveat

- quiet-vine-3426 — fresh carriage and arm complete-review comparison through the unchanged public walk; committed measurements and 195 passing CLI tests
- empty-banner-7438 — a third prompt-designed mechanism (pan-tilt head, two catalog MG90S, serial two-revolute chain) through the unchanged entry point on the installed bundle; comparable PROGRESS rows, no code change
- morning-summit-7848 — a fourth variant (the pan-tilt prompt redesigned with fused servos) through the unchanged entry point on the refreshed installed bundle; six project commits, comparable PROGRESS rows, no code change
- silent-mist-5233 — quota-blocked two-servo rehearsal supplies no comparable mechanism numbers; working status retained
