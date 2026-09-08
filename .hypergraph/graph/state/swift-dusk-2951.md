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

Charter criterion: **The walk holds on a second mechanism.** The same entry point, with no code change specific to the mechanism, takes a second mechanism through the whole loop, and both projects' `PROGRESS.md` carry comparable numbers. Declared target `gap-walk-holds-second-mechanism-same` [rec: empty-wolf-3962]. Re-seeded unticked by the nt3 directive — "finish and evidence it rather than restarting it" [rec: modest-summit-8554] — and again by the ot4 directive, on machine grounds: ot4 moved to `sb1x` (Ubuntu 24.04, RTX 5090, 32 cores), where no mechanism had yet completed the walk at all [rec: humble-forest-6896] [rec: open-hollow-2140].

**Met on this machine, 2026-09-08.** The unchanged `cadex walk --prompt`, with **no code change of any kind** (clean tree at `526d43fb`), took a vertical linear carriage rig — **prismatic** joint, **force motor** — from one sentence to a verified policy: exit 0, **5:59.8**, 1,721 MB peak RSS, into `~/cadex-projects/ot4-carriage`, a second durable project outside this repository. Legs all exit 0 (design 340.7 s, train 15.8 s, declare 0.9 s, rollout 1.0 s; `walk_seconds` 359.7 through review), reward/step 0.02347, witness error 2.8e-09 against 1e-4, verified rollout `total_reward` 3.2963 over 4 legs, all four headless review eyes, `cli/tests` 217 passed 0 skipped. The project landed as a codebase unaided: five commits, five `PROGRESS.md` rows, five project ADRs and `docs/{actuators,clearance,inventory,sensors}.md` [rec: rare-cliff-9595].

Both halves of the criterion hold on this machine, side by side [rec: wandering-jasper-6102] [rec: rare-cliff-9595]:

| project | mechanism, joint, actuator | design | train | declare | rollout | wall | peak RSS | `total_reward` | witness err |
|---|---|---|---|---|---|---|---|---|---|
| `ot4-swing2` [rec: wandering-jasper-6102] | swing arm, revolute, MG90S position servo | 1,014.2 s | 38.3 s | 2.2 s | 2.4 s | 17:43 | 2,640 MB | -0.1765 | 7.2e-09 |
| `ot4-carriage` [rec: rare-cliff-9595] | vertical carriage, prismatic, force motor | 340.7 s | 15.8 s | 0.9 s | 1.0 s | 5:59.8 | 1,721 MB | 3.2963 | 2.8e-09 |

Both at 5 iterations × 16 envs, seed 0, `--timeout 600`, same columns and same metric definitions [rec: rare-cliff-9595]. The second mechanism differs from the first in joint type (prismatic, not revolute) and actuator type (bounded force `motor`, not a position servo) — a different path through the walk's digest edit, taken with no refusal. The inventory eye distinguishes them too: 2 components 0 catalogued for the printed carriage against 10/7 for the swing arm.

Reconcile judgement: `open` → `working`. Neither record declares the flip; both leave it here. The gate the reopening set — "it cannot be re-evidenced until one mechanism completes on this machine" — was opened by `crisp-reef-5607` going `working`, and the carriage is the second mechanism the criterion names, on the same entry point, with the tree clean throughout [rec: rare-cliff-9595] [rec: humble-forest-6896].

**Prior evidence, from the nt3 machine, not withdrawn.** Five mechanisms went through the same unchanged entry point there — pendulum rig (revolute, position servo) [rec: cool-fountain-2483], vertical carriage (prismatic, force motor) [rec: placid-sky-7374], pan-tilt head (two revolute in series, two catalog MG90S) [rec: empty-banner-7438], the same pan-tilt prompt redesigned with fused servo bodies [rec: morning-summit-7848], and a hip-and-knee leg with separately placed catalog servos and M3 hardware [rec: proud-beacon-8002] — all at 1 × 4, `--timeout 600`, all witness-verified between 2.9e-09 and 4.5e-09, all with comparable `PROGRESS.md` rows. Two installed-recipe walks (ADR-203) preceded them with the same shape from a script rather than a prompt [rec: sage-peak-2689] [rec: quiet-vine-3426]. That evidence is from a different machine and is why the criterion was reopened rather than restarted; the entry point was never the thing in doubt. One record adds no mechanism evidence at all: the two-servo design leg refused on provider quota before authoring [rec: silent-mist-5233].

## Negative knowledge

- [scope: comparing the prompt-walk projects' `total_reward` | confidence: high | evidence: placid-sky-7374, empty-banner-7438, proud-beacon-8002, rare-cliff-9595] The columns and their definitions are the same, but the reward expressions are different objectives in different units over different episode lengths, so the totals compare runs of one project and never rank designs against each other — `-0.1765` against `3.2963` on this machine says nothing about which rig is better. The caveat `examples/lifecycle/README.md` and both `PROGRESS.md` headers already carry. One PPO iteration, or five, is a smoke test of the loop, not a claim about learned control.
- [scope: one-iteration linear-carriage qualification | confidence: high | evidence: sage-peak-2689] Working-level evidence denotes pipeline qualification, not control quality or hardware validation: the carriage falls to z=-4699.378313 mm at 1 s on an ideal unlimited guide. Only source, docs and numbers are versioned in the parent repository; policy assets, checkpoints, traces and accepted caches stay untracked.
- [scope: two walks from one prompt | confidence: high | evidence: empty-banner-7438, morning-summit-7848] The same pan-tilt prompt yielded two different assemblies (placed catalog servos, then fused solids) and two different reward expressions. Same prompt is not same design, so even same-prompt totals do not compare across runs; only reruns of one accepted project do.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- sage-peak-2689 — second mechanism qualifies through the unchanged walk with baseline metrics and real CLI tests; control quality remains poor
- modest-summit-8554 — nt3 operator directive re-seeds the criterion unticked: finish and evidence it rather than restarting it
- cool-fountain-2483 — the first prompt-designed mechanism (pendulum rig) through the walk, the baseline the second is compared against
- placid-sky-7374 — a second prompt-designed mechanism (vertical carriage, prismatic, force motor) through the unchanged entry point on the nt3 machine, both PROGRESS.md files comparable
- quiet-vine-3426 — fresh carriage and arm complete-review comparison through the unchanged public walk; committed measurements and 195 passing CLI tests
- empty-banner-7438 — a third prompt-designed mechanism (pan-tilt head, serial two-revolute chain, two catalog MG90S) through the unchanged entry point; comparable PROGRESS rows, no code change
- morning-summit-7848 — a fourth variant (the pan-tilt prompt redesigned with fused servos) through the unchanged entry point on the refreshed bundle; comparable PROGRESS rows, no code change
- silent-mist-5233 — quota-blocked two-servo rehearsal supplies no comparable mechanism numbers
- proud-beacon-8002 — a fifth prompt-designed mechanism (two-servo hip-and-knee leg, separately placed catalog servos, M3 hardware) through the unchanged entry point on the qualified payload
- humble-forest-6896 — the ot4 operator directive re-seeds the criterion unticked on a new machine
- open-hollow-2140 — no mechanism had yet completed the walk on that machine; the first attempt exits 3 at the train leg
- wandering-jasper-6102 — the first mechanism on this machine: the swing-arm rig, exit 0 in 17:43, the baseline the second is compared against
- rare-cliff-9595 — the second mechanism on this machine: a prismatic/force-motor carriage through the unchanged entry point with no code change, exit 0 in 5:59.8, comparable PROGRESS rows, cli/tests 217 passed 0 skipped
