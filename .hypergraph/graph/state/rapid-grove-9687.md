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

**F7 is no longer blocked on provider capacity: the owner restored Fable access (ADR-383), both launch-time availability checks succeeded, and F6's create turn has since completed on `claude-fable-5` — a 28-minute answered turn being the strongest evidence of restored access. F7 is queued behind F6's continuations with every slot unspent [rec: modest-banner-8771] [rec: modest-dune-5265].** The owner's versioned directive names it explicitly: the next substantive unit is F6 (Robin), followed by F7 (Plover), on the frozen prompts and existing slot accounting, every runner role and product-agent call on `claude-fable-5` with no Opus or Codex fallback, the window checked before each design turn, void calls and unspent slots preserved, and the no-actor-design-edits rule retained; after the experiments come regression verification and the F10 closing report, and a design that fails after its allowed turns is valid evidence. The restart has a fresh 48-hour limit and keeps the two accepted done verdicts as its completion stop; if access is lost again, the previous directive's waiting rules apply [rec: gentle-sand-0141]. F4 and F5 stay exhausted with their measured outcomes and are not retried [rec: gentle-sand-0141] [rec: modest-banner-8771].

**F7 has had no design turn: its one dispatch is a pre-restart void call, and the create prompt and all three continuations are unspent.** The frozen Plover create attempt was dispatched once, before the restart, and refused by the provider session limit in 3.273 seconds: zero completed design turns, no accepted revision, no actor design edit [rec: red-hawk-4600]. Under ADR-355 that call is **void, not an attempt** [rec: keen-wing-6569]; the runner classifies it so by code from its retained transcript (`docs/probes/ot7/attempts/void-calls.json`), with the retry named `ot7-plover-b`, a fresh project, same frozen prompt [rec: narrow-wave-7452]. The portable receipt at `docs/probes/ot7/attempts/plover-refusal.json` retains transcript and artifact hashes and stays in the closing-report accounting [rec: red-hawk-4600]. The dispatch, after F6's continuations finish, is the unchanged frozen `plover.create.prompt.txt` (sha256 `b95f98b7…`) into a fresh `ot7-plover-b` on `claude-fable-5`, under the runner's under-45 % window gate; each create-plus-three-continuations schedule spans several five-hour windows [rec: silent-union-5108] [rec: sunny-chart-5873] [rec: crimson-nest-6583].

**History: the block that preceded this.** Through 2026-09-16, `claude-fable-5` was refused on this account at the organisation level — twenty-one window probes, each exit 1 with `seven_day_overage_included` at 100 % and `overage.disabled_reason: org_level_disabled`, while the five-hour window moved freely (0–26 %) underneath, proof that no five-hour reset could reach F7 either [rec: idle-crow-9434] [rec: mellow-sky-2112] [rec: sunny-brook-2439] [rec: still-rock-6891]. The exit taken was the one on no clock: the owner's account-level restore, not the 2026-09-18T14:00Z window reset [rec: sunny-brook-2439] [rec: modest-banner-8771]. The window gate that will authorize Plover's dispatch is the one ADR-364, ADR-369 and ADR-376 hardened — a refused probe reads the frame that rejected, an answered probe the frame that allowed, so provider frame order can neither send a prompt into a refusal nor defer one on an account with room — and it worked live on F6's dispatch [rec: mellow-marsh-0749] [rec: clear-spark-8613] [rec: modest-dune-5265]. F6's other launch lesson applies to Plover unchanged: a dead parent kills the collector mid-stream (`ot7-robin-b`, burned as an interrupted execution at zero slots), so the dispatching session is held alive until the runner exits [rec: modest-dune-5265].

**When it runs, it runs on the same product as F6 — thirteen live changes newer than F5's, frozen prompts unchanged [rec: lawful-grotto-1291] [rec: still-rock-6891] [rec: terse-chart-0277].** The running count the records carry is fourteen — ADR-362 (advisory `inventory` block in every build reply), 366 (`fit.sweep` beside `fit`), 367 and 368 (swept-coverage naming), 370 (attachment rows for welded pairs — a biped's legs weld horns, bearings and fasteners to links), 371, 372 (welded pairs exempt from the 0.1 mm undeclared-pair minimum, which reaches Plover hardest: 16 of Finch's 32 below-clearance rows were `fix_*` welds at 0.0 mm on exactly this kind of leg), 373 (declare a narrow gap rather than widen a correct seat, the case Finch's four 0.05 mm bearing seats name), 374 (the sweep reads the pairs the joint actually moves, so a welded horn no longer defines its joint's range), 375 (an unbounded joint declared beside the limited hips and knees is named instead of silently unchecked), 377 (`cadex smoke`'s support check reads the base's attitude against its accepted keyframe — a biped's failure mode is the same fall the retained balancer measured), 378 (a swept pair fails `below clearance` against its own minimum) and 381 (`catalog_derived_from` names the catalog body a modified purchase was cut from — the count F5 failed and the one Plover will be judged on — its prompt clause corrected by ADR-382) — of which the thirteenth, ADR-379's `clearance under weld`, was withdrawn by ADR-380 within the day, leaving thirteen live; `docs/probes/ot7/REPORT.md` tracks the count [rec: glad-wing-9845] [rec: terse-chart-0277] [rec: still-rock-6891] [rec: restless-slope-6471] [rec: humble-harvest-9420] [rec: vast-water-9886]. The thinking-bound and stream-capture gate F4's first turn named was met in code before F5 ran [rec: rare-birch-0755] [rec: sunny-chart-5873].

The tested bounded collector (`docs/probes/ot7/runner/`, ADR-354) retains per-turn fit, swept coverage, inventory, transcript hashes and a final bounded smoke, stops on provider errors, voids usage-limit calls without spending a slot, refuses an existing project so a retry is never a resume, and reads the window before a slot is persisted so an accidental dispatch while refused cannot spend one [rec: peaceful-hill-3013] [rec: narrow-wave-7452] [rec: soft-creek-6253].

Charter criterion: **F7. The biped is designed unassisted.** The same bar as F5 on a biped prompt written and committed in this run's first unit, before any design turn: four MG90S servos from `lib.servo`, hip and knee pitch per leg, catalog horns, bearings and fasteners, modelled printable mounts, no world geometry. ot6 has no biped baseline, because Finch (`cool-hill-9617`) was written by the actor with no model turn. Declared target `gap-f7-biped-designed-unassisted-same`; the human owns the checkbox edit [rec: kind-dusk-1609].

Reconcile judgement: `open` — the obstruction was the same external organisation-level provider limit as F6's, and it is no longer reproduced; what remains between F7 and its create turn is queue position (F6's three continuations) and the ordinary window gate, neither of which is a block in this graph's sense [rec: modest-banner-8771] [rec: modest-dune-5265]. The owner's resume directive supersedes the previous wait-hold, and its no-reprobe rule is retired with it; the waiting rules return only if access is lost again. Done may still not be claimed while F7 is unattempted, now by the resume directive's own closing rule [rec: gentle-sand-0141].

## Negative knowledge

None of its own; `narrow-dune-9454`'s entries apply to F7 unchanged — the five-hour window was not the binding limit during the 2026-09-16 refusal, the 2026-09-18T14:00:00Z epoch was evidence about the org-level refusal in neither direction (the owner's restore lifted it first), a pre-ADR-369 refusal receipt may name the wrong limit, and a collector whose parent session dies loses its turn as an interruption [rec: idle-crow-9434] [rec: mellow-sky-2112] [rec: soft-journey-2954] [rec: mellow-marsh-0749] [rec: modest-banner-8771] [rec: modest-dune-5265].

## Provenance

- kind-dusk-1609 — the ot7 directive (ADR-341) declared this criterion as gap `gap-f7-biped-designed-unassisted-same`
- silent-union-5108 — ADR-345 prompt freeze recovered with digest pins; no design or repair evidence
- peaceful-hill-3013 — tested bounded frozen-design collector; no design attempt or fit/smoke success
- red-hawk-4600 — single frozen biped dispatch refused; no accepted geometry or simulation; F7 remains open
- keen-wing-6569 — the ot7 restart directive (ADR-355): the refused call is void and consumes no slot
- narrow-wave-7452 — the F7 call classified void by the runner's code; retry named `ot7-plover-b`
- rare-birch-0755 — F4's first model turn timed out thinking; the gate it named applied before any F7 dispatch and is now met
- sunny-chart-5873 — F5 exhausted with catalog hardware its one failing count; F7 on `ot7-plover-b` named after F6
- lawful-grotto-1291 — ADR-362: F7 runs on the same product version as F6, build replies carrying the advisory inventory block; frozen prompts unchanged
- idle-crow-9434 — F7 blocked by the same org-level Fable refusal as F6 and follows it; its four slots are unspent
- mellow-sky-2112 — the refusal repeated; F7 will also run on the ADR-362 + ADR-366 product
- pale-garden-4669 — the refusal dated at 2026-09-18 14:00 UTC; ADR-367 lands as the third product change
- tidy-nest-3309 — re-measured, still refused; ADR-368 wording follow-up and REPORT.md's comparison at three changes
- soft-creek-6253 — a deliberate no-change hold: no probe, no prompt, all four F7 slots unspent, and the runner shown to gate before any slot is persisted
- vast-crow-3111 — a second total hold at the same gate; nothing dispatched, the slots unspent
- crimson-nest-6583 — the arithmetic: the window reset falls after ot7's then-binding stop
- sage-isle-3511 — that epoch is a scheduled window reset rather than a dated opening; only an unrefused probe is evidence it lifted
- soft-journey-2954 — and not a lower bound either: the lower-bound reading and "dispatch before ot7's stop is impossible" are withdrawn; F7 is unattempted, never exhausted
- mellow-marsh-0749 — the third probe still refused; ADR-369 makes a refusal receipt name the limit that rejected
- honest-sky-8719 — a fourth refused probe, no slot spent; ADR-370 lands as the fourth product change
- golden-lodge-6986 — a fifth refused probe, no slot spent; ADR-371 lands as the fifth product change
- sharp-glacier-3405 — a sixth refused probe; ADR-372 lands as the sixth, measured on Finch's own welded legs
- fierce-falcon-2378 — a seventh refused probe read before any other work; ADR-373 lands as the seventh
- pale-jasper-8166 — refused again (`five_hour` 0 %); and the correction that the product is eight changes newer than F5's, not seven
- loyal-flame-8896 — refused again (`five_hour` 2 %, `slot_consumed: false`), no slot spent
- old-star-3367 — refused again (`five_hour` 3 %); ADR-374 lands as the ninth, reaching a biped's welded leg hardware directly
- wild-eagle-4128 — refused again (`five_hour` 6 %); REPORT.md's F10 comparison brought level at nine
- solar-arrow-5671 — refused again (`five_hour` 7 %); ADR-375 lands as the tenth, naming any unbounded joint a biped declares beside its limited hip and knee
- clear-spark-8613 — refused again (`five_hour` 11 %); ADR-376 fixes the answered half of the window gate, so provider frame order can no longer defer F7's frozen prompt — runner-only, not a product change
- humble-harvest-9420 — refused again (`five_hour` 11 %); ADR-377 lands as the eleventh, reaching F7's smoke rollout directly after the retained balancer toppled and passed the old support check
- vast-water-9886 — refused again (`five_hour` 13 %); ADR-378 lands as the twelfth, making the swept half of F7's fit bar something an overlap-only rule could not express
- sunny-brook-2439 — refused again (`five_hour` 18 %); the two exits named and ADR-369's frame-order fix confirmed on a live stream
- jolly-current-9257 — the charter's waiting exception taken deliberately: no probe, no change, F7's four slots unspent
- glad-wing-9845 — ADR-379 lands as the thirteenth product change; no probe that iteration
- terse-chart-0277 — ADR-380 withdraws ADR-379: F7's bar is the four fit checks again, and a biped's welded legs are no longer failed for being welded and spaced
- still-rock-6891 — ADR-381 lands as the fourteenth product change, naming the catalog body a modified purchase was cut from; F7 unspent and blocked behind F6
- restless-slope-6471 — ADR-382: an absent catalog-provenance name is unknown, not printed
- fair-badger-6443 — the owner's earlier 2026-09-17 directive: reconcile, then wait; superseded by the resume directive after the successful availability check
- modest-banner-8771 — ADR-383: the owner restored Fable access and authorized the resumption; the shared provider block is no longer reproduced, F7 next after F6 with every slot unspent
- gentle-sand-0141 — the owner's 2026-09-17 resume-on-Fable directive: F6 then F7 on frozen prompts and existing slots, fresh 48-hour limit, no done claim while either is unattempted
- modest-dune-5265 — F6's create turn completed on `ot7-robin-c`, confirming restored Fable access on a full design turn; F7 remains queued behind F6's continuations, every slot unspent
