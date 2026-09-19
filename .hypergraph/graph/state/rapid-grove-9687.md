---
node_id: 6eaf1262-e730-5dc4-93ff-9851660b5796
slug: rapid-grove-9687
title: F7. The biped is designed unassisted
created_at: '2026-09-14T17:28:05+00:00'
parents:
- mild-ledge-7157
summary: ''
---
Status: open

## Current

**F7 has now been dispatched three times on `claude-opus-5` and has no design result: two interrupted, one void. No slot has been spent and all four are still held [rec: strong-hollow-7483] [rec: cool-grotto-2512] [rec: weathered-fountain-7838].** The retry is the same frozen create text in a fresh `ot7-plover-e`.

**The third dispatch, `ot7-plover-d`, is the first F7 call to end on its own — and it is void as a design result (ADR-390 amendment, commit `07386514`) [rec: pale-wolf-9928] [rec: weathered-fountain-7838].** The create turn ran on Opus with the probe at 33 % against the unchanged 45 % gate and `turn_bound_seconds: 3600` on the receipt at both levels: exit 0, `success`, 25 provider turns, **1,310.0 s** of the 3,600 s bound, 1,034 frames, 23 tool calls, **0 actor design edits**. It built no biped. The accepted revision is a **three-solid probe script**, and static, swept and attachment fit all read `unavailable`, which is not a passing design and is not a measurement of the agent either. The cause was proved rather than guessed: **this repository's own iteration-158 source edit (ADR-389) poisoned the project-worker bundle underneath the live turn** — 58 ms between the bundle's publication and the first `DOMAIN_WORKER_NO_RESULT` frame — so every build the agent attempted failed for a reason outside its design. Receipt `docs/probes/ot7/attempts/plover-d-engine-mutated.json`; measured window cost of an Opus create turn 33 % → 54 % [rec: pale-wolf-9928].

*Correction, folded here.* The record that collected this turn booked it as a **spent** slot, on the reading that the charter voids only a provider usage, session or credit limit, and said so while flagging the reading as the critic's or owner's call [rec: pale-wolf-9928]. That call was made against it: ADR-390's amendment rules the call **void** — it consumes no slot and is not a measurement of the agent — so **F7 holds its create prompt and all three continuations**, and the earlier "F7's create prompt is SPENT" and the still-earlier "live right now on `ot7-plover-d`" readings are both withdrawn [rec: weathered-fountain-7838]. The engine-side fix that keeps a self-inconsistent bundle from ever being published again is ADR-390 proper, on `forest-wind-0342`.

**The first Opus dispatch produced geometry and ran out of clock [rec: strong-hollow-7483].** A window probe read `allowed` at 14 % of the five-hour window and 2 % of the seven-day, so the frozen `plover.create.prompt.txt` went into a fresh `ot7-plover-c`. The call **reached the model** and ran the full **1,800.0 s** bound — 124 frames, 49 tool calls (4 `describe_api`, 30 `inspect`, 10 `write_script`, 4 `edit_script`, 1 `rebuild`), 1.29 MB of transcript, **zero actor design edits** — and was killed at the bound while reading its own measured fit back through `inspect scope=clearance`. Under ADR-356 that is an **interruption**: no slot spent, retry in a fresh project. Two deviations from the runner default are recorded as deliberate: `--turns 1` (a kill part-way through a four-turn schedule discards every completed turn with it) and launching under `setsid` so the turn outlives the dispatching actor. Receipt `plover-c-interrupted.json`, commit `afd3b773`.

*What it measured is F1–F3 evidence, not an F7 result.* The last revision built (`15be5515…`, **never accepted**) is a 30-component biped, 24 components catalogued and 6 printed, at **13 failing of 435 static pairs** (12 intersections and 1 world-geometry failure, worst a centre screw 12.566 mm³ inside its own hip servo) and **52 failing swept pairs over 4 of 4 joints, coverage complete**. It describes a candidate the agent was mid-way through repairing — the measured-fit surface working on the largest design ot7 has put through it. F7's bar remains an accepted design at zero failing checks [rec: strong-hollow-7483].

*The clock was the binding constraint, and it was raised.* Create turns cost more the larger the design — Heron **1,530.4 s** at 120 static pairs, Robin **1,676.4 s** at 276, Plover **1,800.0 s** at 435 — so the biped is the first design whose create turn does not fit in the old `TURN_BOUND_SECONDS = 1800`. ADR-388 doubled the bound to 3,600 s (collector detail on `chilly-union-8972`). The bound was not what stopped `plover-d`, which used 36 % of it [rec: strong-hollow-7483] [rec: cool-grotto-2512] [rec: pale-wolf-9928].

*A window measurement the next dispatch should use.* An Opus create turn costs far less window than the Fable turns the 45 % gate was calibrated on: `ot7-plover-c` started at 14–15 %, ran the full 1,800 s, and the window read 31 % after — about 17 points per half hour, against 49 for one Fable turn; `plover-d` then measured 33 % → 54 % over 1,310 s, consistent with it. The gate was left at 45 % on that evidence rather than lowered for the doubled bound; a turn genuinely cut off by the session limit is void under ADR-355 and costs no slot [rec: cool-grotto-2512] [rec: pale-wolf-9928].

**History: the two earlier dispatch failures, neither an attempt.** The first was a pre-restart void call — refused by the provider session limit in 3.273 seconds, zero completed design turns, no accepted revision, no actor design edit [rec: red-hawk-4600] — which ADR-355 makes **void, not an attempt** [rec: keen-wing-6569], classified so by the runner's own code from the retained transcript (`docs/probes/ot7/attempts/void-calls.json`), with the portable receipt `plover-refusal.json` retained in the closing-report accounting [rec: narrow-wave-7452]. The second was `ot7-plover-b` (iteration 154), whose *runner* died mid-turn, leaving a receipt stale at `status: running` with an empty envelope and 16 frames. ADR-388's `reclassify` finalised it: `interrupted`, `kind: runner_died`, silent 2,769.2 s against a 2,700 s budget, 10 model messages before the kill, **0 slots spent**; the stale copy is kept as `attempt.superseded.json` [rec: cool-grotto-2512].

**History: the provider block that preceded all of this.** Through 2026-09-16, `claude-fable-5` was refused on this account at the organisation level — twenty-one window probes, each exit 1 with `seven_day_overage_included` at 100 % and `overage.disabled_reason: org_level_disabled`, while the five-hour window moved freely (0–26 %) underneath, proof that no five-hour reset could reach F7 either [rec: idle-crow-9434] [rec: mellow-sky-2112] [rec: sunny-brook-2439] [rec: still-rock-6891]. The exit taken was the one on no clock: the owner's account-level restore [rec: modest-banner-8771]. F6's create turn then completed on Fable, confirming it [rec: modest-dune-5265]; the owner's 2026-09-17 resume directive named F6 then F7 on the frozen prompts and existing slot accounting, with a fresh 48-hour limit and the two accepted done verdicts as the completion stop [rec: gentle-sand-0141]. The run has since moved to `claude-opus-5` for every role and product call. F4 and F5 stay exhausted with their measured outcomes and are not retried [rec: gentle-sand-0141] [rec: modest-banner-8771]. The window gate that authorised all three Opus dispatches is the one ADR-364, ADR-369 and ADR-376 hardened — a refused probe reads the frame that rejected, an answered probe the frame that allowed [rec: mellow-marsh-0749] [rec: clear-spark-8613].

**The product F7 runs on is thirteen live changes newer than F5's, frozen prompts unchanged [rec: lawful-grotto-1291] [rec: still-rock-6891] [rec: terse-chart-0277].** Fourteen landed and one was withdrawn: ADR-362 (advisory `inventory` block in every build reply), 366 (`fit.sweep` beside `fit`), 367 and 368 (swept-coverage naming), 370 (attachment rows for welded pairs — a biped's legs weld horns, bearings and fasteners to links), 371, 372 (welded pairs exempt from the 0.1 mm undeclared-pair minimum, which reaches Plover hardest: 16 of Finch's 32 below-clearance rows were `fix_*` welds at 0.0 mm on exactly this kind of leg), 373 (declare a narrow gap rather than widen a correct seat), 374 (the sweep reads the pairs the joint actually moves), 375 (an unbounded joint declared beside the limited hips and knees is named instead of silently unchecked), 377 (`cadex smoke`'s support check reads the base's attitude against its accepted keyframe — a biped's failure mode is the same fall the retained balancer measured), 378 (a swept pair fails `below clearance` against its own minimum) and 381 (`catalog_derived_from` — the count F5 failed and the one Plover will be judged on), corrected by ADR-382; ADR-379 was withdrawn by ADR-380 within the day. `docs/probes/ot7/REPORT.md` tracks the count [rec: glad-wing-9845] [rec: terse-chart-0277] [rec: restless-slope-6471] [rec: humble-harvest-9420] [rec: vast-water-9886]. The thinking-bound and stream-capture gate F4's first turn named was met in code before F5 ran [rec: rare-birch-0755] [rec: sunny-chart-5873].

The tested bounded collector (`docs/probes/ot7/runner/`, ADR-354) retains per-turn fit, swept coverage, inventory, transcript hashes and a final bounded smoke, stops on provider errors, voids usage-limit calls without spending a slot, and reads the window before a slot is persisted so an accidental dispatch while refused cannot spend one [rec: peaceful-hill-3013] [rec: narrow-wave-7452] [rec: soft-creek-6253].

Charter criterion: **F7. The biped is designed unassisted.** The same bar as F5 on a biped prompt written and committed in this run's first unit, before any design turn: four MG90S servos from `lib.servo`, hip and knee pitch per leg, catalog horns, bearings and fasteners, modelled printable mounts, no world geometry. ot6 has no biped baseline, because Finch (`cool-hill-9617`) was written by the actor with no model turn. Declared target `gap-f7-biped-designed-unassisted-same`; the human owns the checkbox edit [rec: kind-dusk-1609].

Reconcile judgement: **`open`**, and the obstruction is now entirely internal. The org-level provider block is gone, the turn bound is raised past the largest measured create turn, and what cost F7 its third dispatch was this repository mutating the engine under a live turn — fixed by ADR-390 and ruled void rather than counted against the agent. Done may not be claimed while F7 is unattempted, by the resume directive's own closing rule [rec: gentle-sand-0141], and neither an interrupted turn nor a void one is an attempt [rec: strong-hollow-7483] [rec: weathered-fountain-7838].

## Negative knowledge

- [scope: editing engine source in this repository while an ot7 design turn is live | confidence: high | evidence: pale-wolf-9928, weathered-fountain-7838] It can destroy the turn without failing the runner. The iteration-158 ADR-389 edit republished the project-worker bundle 58 ms before the first `DOMAIN_WORKER_NO_RESULT` frame, so `ot7-plover-d` ran to a clean exit 0 / `success` with 25 provider turns and an accepted three-solid probe and no biped at all, its fit `unavailable`. A turn that ends on its own is not thereby a measurement of the agent; check what the repository did under it before reading the result, and rule such a call void.
- [scope: a create turn on a design of Plover's size | confidence: high | evidence: strong-hollow-7483] A 1,800 s bound is **not** enough. The three measured create turns scale with static-pair count — 1,530.4 s at 120, 1,676.4 s at 276, 1,800.0 s at 435 — so a retry at the same bound has no reason to end differently; a raised bound must precede the retry, which is what ADR-388 did.
- [scope: the 13/435 static and 52 swept failures on `ot7-plover-c` | confidence: high | evidence: strong-hollow-7483] These are **not** an F7 result and must not be read as one. They describe an unaccepted candidate mid-repair; they are evidence for F1–F3 and for nothing else.
- [scope: reading F7's provider and collector failures | confidence: high | evidence: idle-crow-9434, mellow-sky-2112, soft-journey-2954, mellow-marsh-0749, modest-dune-5265] `narrow-dune-9454`'s entries apply to F7 unchanged: the five-hour window was not the binding limit during the 2026-09-16 refusal, the 2026-09-18T14:00:00Z epoch was evidence about the org-level refusal in neither direction, a pre-ADR-369 refusal receipt may name the wrong limit, and a collector whose parent session dies loses its turn as an interruption.

## Provenance

- kind-dusk-1609 — the ot7 directive (ADR-341) declared this criterion as gap `gap-f7-biped-designed-unassisted-same`
- silent-union-5108 — ADR-345 prompt freeze recovered with digest pins; no design or repair evidence
- peaceful-hill-3013 — tested bounded frozen-design collector; no design attempt or fit/smoke success
- red-hawk-4600 — single frozen biped dispatch refused; no accepted geometry or simulation; F7 remains open
- keen-wing-6569 — the ot7 restart directive (ADR-355): the refused call is void and consumes no slot
- narrow-wave-7452 — the F7 call classified void by the runner's code; retry named `ot7-plover-b`
- rare-birch-0755 — F4's first model turn timed out thinking; the gate it named applied before any F7 dispatch and is now met
- sunny-chart-5873 — F5 exhausted with catalog hardware its one failing count
- lawful-grotto-1291 — ADR-362: build replies carry the advisory inventory block; frozen prompts unchanged
- idle-crow-9434 — F7 blocked by the same org-level Fable refusal as F6 and follows it; its four slots are unspent
- mellow-sky-2112 — the refusal repeated; ADR-366 lands as the second product change
- pale-garden-4669 — the refusal dated at 2026-09-18 14:00 UTC; ADR-367 lands as the third
- tidy-nest-3309 — re-measured, still refused; ADR-368 wording follow-up
- soft-creek-6253 — a deliberate no-change hold; the runner shown to gate before any slot is persisted
- vast-crow-3111 — a second total hold at the same gate; nothing dispatched, the slots unspent
- crimson-nest-6583 — the arithmetic: the window reset falls after ot7's then-binding stop
- sage-isle-3511 — that epoch is a scheduled window reset rather than a dated opening
- soft-journey-2954 — and not a lower bound either; F7 is unattempted, never exhausted
- mellow-marsh-0749 — the third probe still refused; ADR-369 makes a refusal receipt name the limit that rejected
- honest-sky-8719 — a fourth refused probe; ADR-370 lands as the fourth product change
- golden-lodge-6986 — a fifth refused probe; ADR-371 lands as the fifth
- sharp-glacier-3405 — a sixth refused probe; ADR-372 lands as the sixth, measured on Finch's own welded legs
- fierce-falcon-2378 — a seventh refused probe read before any other work; ADR-373 lands as the seventh
- pale-jasper-8166 — refused again; and the correction that the product is eight changes newer than F5's, not seven
- loyal-flame-8896 — refused again (`slot_consumed: false`), no slot spent
- old-star-3367 — refused again; ADR-374 lands as the ninth, reaching a biped's welded leg hardware directly
- wild-eagle-4128 — refused again; REPORT.md's F10 comparison brought level at nine
- solar-arrow-5671 — refused again; ADR-375 lands as the tenth, naming any unbounded joint
- clear-spark-8613 — refused again; ADR-376 fixes the answered half of the window gate — runner-only, not a product change
- humble-harvest-9420 — refused again; ADR-377 lands as the eleventh, reaching F7's smoke rollout directly
- vast-water-9886 — refused again; ADR-378 lands as the twelfth, making the swept half of F7's fit bar expressible
- sunny-brook-2439 — refused again; the two exits named and ADR-369's frame-order fix confirmed on a live stream
- jolly-current-9257 — the charter's waiting exception taken deliberately: no probe, no change, F7's four slots unspent
- glad-wing-9845 — ADR-379 lands as the thirteenth product change; no probe that iteration
- terse-chart-0277 — ADR-380 withdraws ADR-379: F7's bar is the four fit checks again
- still-rock-6891 — ADR-381 lands as the fourteenth product change, naming the catalog body a modified purchase was cut from
- restless-slope-6471 — ADR-382: an absent catalog-provenance name is unknown, not printed
- fair-badger-6443 — the owner's earlier 2026-09-17 directive: reconcile, then wait; superseded
- modest-banner-8771 — ADR-383: the owner restored Fable access and authorized the resumption
- gentle-sand-0141 — the owner's 2026-09-17 resume directive: F6 then F7 on frozen prompts and existing slots, no done claim while either is unattempted
- modest-dune-5265 — F6's create turn completed on `ot7-robin-c`, confirming restored access on a full design turn
- strong-hollow-7483 — F7's first Opus dispatch: the frozen create prompt reached the model on `ot7-plover-c`, ran the full 1,800 s bound across 49 tool calls and was killed mid-repair; an ADR-356 interruption at 0 slots, with 13/435 static and 52 swept failures on an unaccepted 30-component biped
- cool-grotto-2512 — ADR-388 raised the bound to 3,600 s and finalised `ot7-plover-b` as a `runner_died` interruption at 0 slots; the Opus window cost measured at ~17 points per half hour
- pale-wolf-9928 — `ot7-plover-d` collected: the first F7 call to end on its own, exit 0 in 1,310 s with an accepted three-solid probe and fit `unavailable`, cause proved as this repo's own iteration-158 edit poisoning the worker bundle 58 ms in
- weathered-fountain-7838 — the ADR-390 amendment ruling that call void as a design result: no slot consumed, F7 holds all four prompts, and the retry is the same frozen create text in a fresh `ot7-plover-e`
