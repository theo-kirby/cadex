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

**F7 is blocked behind F6 and by the same cause, with every slot unspent: `claude-fable-5` is refused on this account at the organisation level [rec: idle-crow-9434] [rec: mellow-sky-2112].** The window probes of 2026-09-16 were refused in 2.2–2.4 s — `seven_day` 51 %, `seven_day_overage_included` 100 %, overage `org_level_disabled` — while the five-hour window read 1–4 %, so no five-hour reset reaches F7 either. It waits on Fable capacity returning to the account or on an owner decision; the product agent's model stays `claude-fable-5` because ADR-363 preserved the experiment's settings on purpose, and changing it is a charter question for the owner [rec: idle-crow-9434] [rec: mellow-sky-2112]. F7 follows F6 in any case: the frozen Plover create on fresh `ot7-plover-b`, dispatched only when the runner's window probe reads under 45 %, on the same product version as F6 [rec: sunny-chart-5873].

**F7 has had no design turn: its one dispatch is a void call, and the create prompt and all three continuations are unspent.** The frozen Plover create attempt was dispatched once and refused by the provider session limit in 3.273 seconds (CLI exit 1): zero completed design turns, zero continuations, no accepted revision, no actor design edit; static fit, swept fit and inventory unavailable; smoke exited before simulation because `script.json` does not exist [rec: red-hawk-4600]. Under ADR-355 that call is **void, not an attempt** [rec: keen-wing-6569]; the runner now classifies it so by code from its retained transcript (`docs/probes/ot7/attempts/void-calls.json`), listed apart from the design's attempts, with the retry named `ot7-plover-b`, a fresh project, same frozen prompt [rec: narrow-wave-7452]. The portable receipt at `docs/probes/ot7/attempts/plover-refusal.json` retains transcript and artifact hashes and stays in the closing-report accounting [rec: red-hawk-4600].

**When it runs, it runs on the same product as F6 — two changes newer than F5's, frozen prompts unchanged** [rec: lawful-grotto-1291] [rec: mellow-sky-2112]. ADR-362 (commit `fd3b3643`) put an advisory `inventory` block beside `fit` on every build reply, envelope and prose report — counts, catalog roll-up and every uncatalogued source name, refusing nothing, with a system-prompt bullet that catalog identity is measured too — which is the one count F5 failed [rec: sunny-chart-5873] [rec: lawful-grotto-1291]. ADR-366 then added `fit.sweep` beside `fit`, so measured motion fit reaches the agent in the build reply itself (detail on `chilly-union-8972`) [rec: mellow-sky-2112]. Any difference from F5 is therefore a difference across those two product changes, and the swept-coverage column in F7's REPORT row is measured on the newer product [rec: lawful-grotto-1291] [rec: mellow-sky-2112]. Each create-plus-three-continuations schedule spans several five-hour windows [rec: sunny-chart-5873]. The thinking-bound and stream-capture gate F4's first turn named (`rare-birch-0755`) was met in code before F5 ran — the per-message cap, the runner's recorded `medium` effort, streams captured as they arrive — and F5's four turns completed on their own with their streams retained [rec: sunny-chart-5873].

Plover's create prompt is frozen at `docs/probes/ot7/prompts/plover.create.prompt.txt` (sha256 `b95f98b7…`) [rec: silent-union-5108]. The tested bounded collector (`docs/probes/ot7/runner/`, ADR-354) retains per-turn fit, swept coverage, inventory, transcript hashes and a final bounded smoke, stops on provider errors, voids usage-limit calls without spending a slot, and refuses an existing project, so a retry is never a resume [rec: peaceful-hill-3013] [rec: narrow-wave-7452].

Charter criterion: **F7. The biped is designed unassisted.** The same bar as F5 on a biped prompt written and committed in this run's first unit, before any design turn: four MG90S servos from `lib.servo`, hip and knee pitch per leg, catalog horns, bearings and fasteners, modelled printable mounts, no world geometry. ot6 has no biped baseline, because Finch (`cool-hill-9617`) was written by the actor with no model turn. Declared target `gap-f7-biped-designed-unassisted-same`; the human owns the checkbox edit [rec: kind-dusk-1609].

Reconcile judgement: `open` → `blocked`, for the same reason as F6 (`narrow-dune-9454`) — the obstruction is an external organisation-level limit on the experiment's model, not a queue position or a five-hour window. A void call remains neither a pass nor an attempt, and no design turn has yet been dispatched for F7 [rec: idle-crow-9434] [rec: mellow-sky-2112] [rec: keen-wing-6569].

## Negative knowledge

None yet; the blocking evidence is `narrow-dune-9454`'s entry, which applies to F7 unchanged [rec: idle-crow-9434] [rec: mellow-sky-2112].

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
