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

**The second mechanism now has a comparable baseline/iterate pair.** Width 70 → 80 mm through the unchanged public walk, without a model turn, completed in 20.89 s at CPU 5 × 16, training seed 0, cold initialization. Only model differs between task bundles; rollout seed 7, 200 steps, 4 seconds and randomisation agree. Total reward **3.296298 → 2.760187**, with the decrease automatically recorded in project history and all 21 baseline files preserved. All four review eyes were inspected at the accepted revision; CLI gate: 223 passed, no skips. Retain `working` at toy scale: this measures one seed on one objective, not general design or control quality. [rec: mellow-quartz-8093]

**The repository's own documented example path also takes both mechanisms here (2026-09-08).** Not the prompt walk but the commands `examples/lifecycle/README.md` tells a reader to run — `cadex script --set` then `cadex walk` — unchanged and with no mechanism-specific option, on the hinged arm (revolute, torque motor) and the linear carriage (prismatic, force motor). Both exit 0; no code change of any kind was needed for either mechanism, and the diff was documentation and example-project files only [rec: western-gate-9567]:

| example walk | `total_reward` | trainer reward/step | `walk_seconds` | peak tree RSS | witness err |
|---|---:|---:|---:|---:|---:|
| hinged-arm [rec: western-gate-9567] | -27.109384220904474 | -0.3801981508731842 | 14.40 | 1,539,432,448 | 2.07e-09 |
| linear-carriage [rec: western-gate-9567] | -24159.195371510654 | -82.31990814208984 | 13.10 | 1,467,621,376 | 3.74e-09 |

Legs all exit 0 (arm train 11.38 s / declare 0.75 / rollout 0.93; carriage 10.08 / 0.75 / 0.88). Clearance: arm 1 offending pair of 1 checked, carriage 0 of 1. Both `PROGRESS.md` files gained a two-column comparison against the 2026-09-06 rows from the first machine, which are not withdrawn. `JAX_PLATFORMS=cpu pixi run python -m pytest cli/tests` recorded 227 passed, 0 skipped [rec: western-gate-9567].

**Reproduction is exact where the seed fixes it and not where it does not.** Trainer reward/step is bit-identical to the first machine's rows; the rollout totals agree to 1e-11 (arm) and 1.5e-05 (carriage); the stored policy digests differ (`186faa6e7aad`, `bcf9617aba52`) because the two JAX builds sum the gradient update in a different order. Task sha256 is unchanged on both (`c4315071`, `d71677f3`), so the same objective was scored [rec: western-gate-9567].

**What that evidence claims, corrected.** The two measured rows above were produced with the trainer interpreter named explicitly (`--trainer-python`); the flagless command block the README documents is evidenced by exactly one further carriage walk, which returned the same `total_reward` -24159.195371510654 in 13.19 s through the CLI's documented venv discovery order. The numbers are unaffected — the same interpreter binary ran either way — but before that correction a reader could have taken all three walks as evidence for the flagless form [rec: blue-quill-9477].

Reconcile judgement: retain `working`. This is new evidence for the criterion's *entry point as documented*, on the machine of record, rather than a re-roll of the already-recorded prompt-walk pair; what the criterion's qualification still names is control quality, not pipeline coverage [rec: western-gate-9567].

**The "no mechanism-specific code change" half is now a behavioural regression rather than a narrative claim (ADR-260, commit `9e888610`, 2026-09-08).** Everything above supported that half by recorded *absence* — walk after walk needing no workaround — which is a statement about the past, not a property of the tree; one `if` on the joint kind would have decayed it and nothing would have noticed. Two offline tests in `cli/tests/test_walk.py` now pin it. `test_the_two_example_mechanisms_dispatch_the_identical_legs` walks both repository-owned recipes through `command_walk` with identical flags against the existing fake `cadex` and requires the child argv to be **equal** once the project path is substituted out, asserting the four legs (`train`, `script`, `script`, `params`) really ran so equality is not two empty lists agreeing. `test_the_digest_edit_treats_both_example_mechanisms_alike` covers `declare_policy`, the one leg that opens a script the walk did not write, requiring the same two literals rewritten on both recipes and every other byte left alone. A mutation check proves the first test can fail: one `if "slider" in script` adding a `--label` before the train leg made it fail with both argv lists printed, and the file was restored from a pre-mutation copy with `git diff --stat cli/cadex_cli/` confirmed empty before continuing. `examples/lifecycle/README.md` §"One entry point, and no branch that knows which mechanism" names the entry point (`cadex walk` → `command_walk`, legs spawned as child commands by `run_leg`), both regressions, and puts both projects' comparable `PROGRESS.md` numbers side by side with the joint and actuator each uses. `cli/` and `docs/` only, no implementation changed; CLI gate **233 passed, 0 skipped**, including the real CPU walk and iterate legs [rec: falling-willow-7995].

Rejected on the way, and worth keeping: a lexical net over the dispatch's identifiers for mechanism nouns. It would have had to exempt `swing` — the motion block's own word for the rotation channel (`crisp-reef-5607`) — and a guard whose first act is an arbitrary exemption is worse than no guard. The two behavioural tests replaced it [rec: falling-willow-7995].

Reconcile judgement: retain `working`, and the judgement the record explicitly left to this pass is taken as follows. Both halves the criterion *literally* names now hold and are checkable rather than remembered: one entry point with no mechanism-specific branch (test-pinned, not recalled), and both projects carrying comparable `PROGRESS.md` numbers. What holds the tick back is the qualification this node has recorded since `sage-peak-2689` and restated in its negative knowledge — control quality. The carriage's policy still lets it fall to -4699 mm in one second on an ideal unlimited guide, one PPO iteration is a smoke test of the loop, and the two `total_reward` columns are different objectives in different units. Read as *pipeline coverage* the criterion is met; read as *learned control* it is not, and no record in this fold claims the latter — the README section says exactly this so a reader cannot take the new evidence for more than it is. The tick therefore stays a charter decision, not a maintainer one [rec: falling-willow-7995].

## Negative knowledge

- [scope: reproducing a walk's numbers on a second machine | confidence: high | evidence: western-gate-9567] A fixed seed reproduces the trainer's reward/step bit-for-bit and the rollout total only to ~1e-5, and it does not reproduce the stored policy digest at all: two JAX builds sum the gradient update in a different order. Compare task sha256 to prove the same objective was scored; a policy-digest comparison is not a reproduction check and will read as a failure when nothing failed. Peak RSS is not portable either — ~1.5x the first machine's at the same wall time.
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
- mellow-quartz-8093 — The second mechanism now has a comparable baseline/iterate pair
- western-gate-9567 — both documented lifecycle example walks reproduce on this machine through the README's own commands, no code change, comparable two-column PROGRESS rows; cli/tests 227 passed, 0 skipped
- blue-quill-9477 — corrects that evidence: the two measured rows named the trainer interpreter explicitly, and one further carriage walk is what evidences the flagless documented form
- falling-willow-7995 — ADR-260: the 'no mechanism-specific code' half becomes two offline regressions (both example recipes dispatch byte-identical child argv; the digest edit treats both alike, mutation-checked) plus a README section naming the entry point and both projects' numbers side by side; CLI gate 233 passed, 0 skipped
