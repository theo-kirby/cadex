---
node_id: 6eaf1262-e730-5dc4-93ff-9851660b5796
slug: rapid-grove-9687
title: F7. The biped is designed unassisted
created_at: '2026-09-14T17:28:05+00:00'
parents:
- mild-ledge-7157
summary: ''
---
Status: blocked

## Current

**F7 is blocked behind F6 and by the same cause, with every slot unspent: `claude-fable-5` is refused on this account at the organisation level [rec: idle-crow-9434] [rec: mellow-sky-2112].** The window probes of 2026-09-16 were refused in 2.2–2.4 s — `seven_day` 51 %, `seven_day_overage_included` 100 %, overage `org_level_disabled` — while the five-hour window read 1–12 %, so no five-hour reset reaches F7 either [rec: pale-garden-4669] [rec: tidy-nest-3309].

**The gate cannot open before this run's own stop, and is not promised to open then [rec: crimson-nest-6583] [rec: sage-isle-3511].** The full reading is on `narrow-dune-9454` and applies to F7 unchanged: the rejected overage window's `resets_at` of **2026-09-18T14:00:00Z** is the *earliest* the refusal could lift rather than a dated opening — the binding field is `overage.disabled_reason: "org_level_disabled"`, which no window reset is evidence about — and ot7's binding stop rule puts its last possible iteration at **2026-09-17T04:25:13Z**, 33 h 34 m 47 s earlier, with `stop.max_stuck: 25` able to end it sooner. F7 is therefore **expected to end this run unattempted, with all four create/continuation slots unspent — incomplete, never exhausted** under the charter's exhaustion policy [rec: crimson-nest-6583] [rec: sage-isle-3511]. Finishing it needs no new decision and no new prompt: after an unrefused `run.py window --model claude-fable-5`, the unchanged frozen `plover.create.prompt.txt` (`b95f98b7…`) into a fresh `ot7-plover-b` on `claude-fable-5`, through its three continuations; only the owner can decide whether that happens in a new run [rec: crimson-nest-6583]. The product agent's model stays `claude-fable-5` because ADR-363 preserved the experiment's settings on purpose, and changing it is a charter question for the owner [rec: idle-crow-9434] [rec: mellow-sky-2112]. F7 follows F6 in any case: the frozen Plover create on fresh `ot7-plover-b`, dispatched only when the runner's window probe reads under 45 %, on the same product version as F6 [rec: sunny-chart-5873].

**F7 has had no design turn: its one dispatch is a void call, and the create prompt and all three continuations are unspent** — still true through six further iterations, none of which dispatched anything [rec: pale-garden-4669] [rec: tidy-nest-3309] [rec: soft-creek-6253] [rec: vast-crow-3111] [rec: crimson-nest-6583] [rec: sage-isle-3511]. The hold is gated by code as well: `run.py` reads the window before a slot is persisted or a turn directory created, and on `dispatched: false` marks the receipt `paused`, so an accidental dispatch while refused cannot spend a slot [rec: soft-creek-6253]. The frozen Plover create attempt was dispatched once and refused by the provider session limit in 3.273 seconds (CLI exit 1): zero completed design turns, zero continuations, no accepted revision, no actor design edit; static fit, swept fit and inventory unavailable; smoke exited before simulation because `script.json` does not exist [rec: red-hawk-4600]. Under ADR-355 that call is **void, not an attempt** [rec: keen-wing-6569]; the runner now classifies it so by code from its retained transcript (`docs/probes/ot7/attempts/void-calls.json`), listed apart from the design's attempts, with the retry named `ot7-plover-b`, a fresh project, same frozen prompt [rec: narrow-wave-7452]. The portable receipt at `docs/probes/ot7/attempts/plover-refusal.json` retains transcript and artifact hashes and stays in the closing-report accounting [rec: red-hawk-4600].

**When it runs, it runs on the same product as F6 — three changes newer than F5's, frozen prompts unchanged** [rec: lawful-grotto-1291] [rec: mellow-sky-2112]. ADR-362 (commit `fd3b3643`) put an advisory `inventory` block beside `fit` on every build reply, envelope and prose report — counts, catalog roll-up and every uncatalogued source name, refusing nothing, with a system-prompt bullet that catalog identity is measured too — which is the one count F5 failed [rec: sunny-chart-5873] [rec: lawful-grotto-1291]. ADR-366 then added `fit.sweep` beside `fit`, so measured motion fit reaches the agent in the build reply itself (detail on `chilly-union-8972`) [rec: mellow-sky-2112]. ADR-367 then closed the gap ADR-366 left — an assembly declaring no step now names every limited joint it left unswept instead of reading `sweep unavailable` — and ADR-368 made an `unavailable` swept verdict say which of its two causes it is [rec: pale-garden-4669] [rec: tidy-nest-3309]. Any difference from F5 is therefore a difference across those three product changes, and the swept-coverage column in F7's REPORT row is measured on the newer product [rec: lawful-grotto-1291] [rec: tidy-nest-3309]. Each create-plus-three-continuations schedule spans several five-hour windows [rec: sunny-chart-5873]. The thinking-bound and stream-capture gate F4's first turn named (`rare-birch-0755`) was met in code before F5 ran — the per-message cap, the runner's recorded `medium` effort, streams captured as they arrive — and F5's four turns completed on their own with their streams retained [rec: sunny-chart-5873].

Plover's create prompt is frozen at `docs/probes/ot7/prompts/plover.create.prompt.txt` (sha256 `b95f98b7…`) [rec: silent-union-5108]. The tested bounded collector (`docs/probes/ot7/runner/`, ADR-354) retains per-turn fit, swept coverage, inventory, transcript hashes and a final bounded smoke, stops on provider errors, voids usage-limit calls without spending a slot, and refuses an existing project, so a retry is never a resume [rec: peaceful-hill-3013] [rec: narrow-wave-7452].

Charter criterion: **F7. The biped is designed unassisted.** The same bar as F5 on a biped prompt written and committed in this run's first unit, before any design turn: four MG90S servos from `lib.servo`, hip and knee pitch per leg, catalog horns, bearings and fasteners, modelled printable mounts, no world geometry. ot6 has no biped baseline, because Finch (`cool-hill-9617`) was written by the actor with no model turn. Declared target `gap-f7-biped-designed-unassisted-same`; the human owns the checkbox edit [rec: kind-dusk-1609].

Reconcile judgement: `blocked`, unchanged, for the same reason as F6 (`narrow-dune-9454`) — an external organisation-level limit on the experiment's model, not a queue position or a five-hour window. What changed this pass is the shape of the block: its earliest possible end now falls after ot7's own stop, and the earlier fold's wording that the refusal "lifts at 2026-09-18 14:00 UTC" is corrected to a lower bound [rec: crimson-nest-6583] [rec: sage-isle-3511]. A void call remains neither a pass nor an attempt, and no design turn has yet been dispatched [rec: keen-wing-6569].

## Negative knowledge

None of its own; `narrow-dune-9454`'s two entries apply to F7 unchanged — the five-hour window is not the binding limit, and the 2026-09-18T14:00:00Z epoch bounds the org-level refusal from below rather than dating its end [rec: idle-crow-9434] [rec: mellow-sky-2112] [rec: pale-garden-4669] [rec: sage-isle-3511].

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
- pale-garden-4669 — the refusal dated at 2026-09-18 14:00 UTC; ADR-367 lands as the third product change F7 will run on
- tidy-nest-3309 — re-measured at 16:39 UTC, still refused, five-hour window 12 %; ADR-368 wording follow-up and REPORT.md's comparison at three changes
- soft-creek-6253 — a deliberate no-change hold: no probe, no prompt, all four F7 slots unspent, and the runner shown to gate before any slot is persisted
- vast-crow-3111 — a second total hold at the same gate; nothing dispatched, the slots unspent
- crimson-nest-6583 — the arithmetic: the earliest reopening falls after ot7's binding stop, so F7 ends the run unattempted rather than exhausted
- sage-isle-3511 — correction: that epoch is a scheduled window reset bounding an org-level refusal from below; only an unrefused probe is evidence it lifted
