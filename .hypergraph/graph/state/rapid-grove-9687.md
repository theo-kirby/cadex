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

**F7 follows F6: the frozen Plover create prompt on fresh `ot7-plover-b`, after F6's create on `ot7-robin-b` and only when the runner's window probe reads under 45 %, on the same product version as F6, one change newer than F5's, whose build replies carry an advisory `inventory` block beside `fit` (ADR-362, commit `fd3b3643`) [rec: sunny-chart-5873] [rec: lawful-grotto-1291].** F5 exhausted on 2026-09-16 with every count met except catalog hardware, the agent having claimed catalog parts against a published inventory listing both servos and both horns uncatalogued because nothing in its reply carried catalog identity; the block now carries the counts, the catalog roll-up and every uncatalogued source name on every build reply, the envelope and the prose report, advisory and refusing nothing, with a system-prompt bullet that catalog identity is measured too (detail on `chilly-union-8972`) [rec: sunny-chart-5873] [rec: lawful-grotto-1291]. Plover's frozen prompts are unchanged, so a catalog-count difference from F5 is a difference across that one product change [rec: lawful-grotto-1291]. Each create-plus-three-continuations schedule spans several five-hour windows [rec: sunny-chart-5873]. The gate F4's first turn named below was met in code before F5 ran (the per-message cap, the runner's recorded `medium` effort, streams captured as they arrive): F5's four turns completed on their own with their streams retained [rec: sunny-chart-5873].

**F7 has had no design turn: its one dispatch is a void call, and the create prompt and all three continuations are unspent.** The frozen Plover create attempt was dispatched once and refused by the provider session limit in 3.273 seconds (CLI exit 1): zero completed design turns, zero continuations, no accepted revision, no actor design edit; static fit, swept fit and inventory unavailable; smoke exited before simulation because `script.json` does not exist [rec: red-hawk-4600]. Under ADR-355 that call is **void, not an attempt** [rec: keen-wing-6569]; the runner now classifies it so by code from its retained transcript (`docs/probes/ot7/attempts/void-calls.json`), listed apart from the design's attempts, with the retry named `ot7-plover-b`, a fresh project, same frozen prompt, only while Claude is available [rec: narrow-wave-7452]. The portable receipt at `docs/probes/ot7/attempts/plover-refusal.json` retains transcript and artifact hashes and stays in the closing-report accounting [rec: red-hawk-4600].

**Before the retry is dispatched, the F4 result names a gate that applies here too [rec: rare-birch-0755].** The first design turn that reached a model (F4's repair) read the measured fit and then spent one 64,000-token message almost entirely on thinking, hitting the output cap without a tool call, and was killed at the runner's 30-minute bound with no submission. The CLI passes no thinking or output bound and the collector loses the stream on a kill; both are to be decided or fixed before any further design turn, F7 included.

Plover's create prompt is frozen at `docs/probes/ot7/prompts/plover.create.prompt.txt` (sha256 `b95f98b7…`) [rec: silent-union-5108]. The tested bounded collector (`docs/probes/ot7/runner/`, ADR-354) retains per-turn fit, swept coverage, inventory, transcript hashes and a final bounded smoke, stops on provider errors, voids usage-limit calls without spending a slot, and refuses an existing project, so a retry is never a resume [rec: peaceful-hill-3013] [rec: narrow-wave-7452].

Charter criterion: **F7. The biped is designed unassisted.** The same bar as F5 on a biped prompt written and committed in this run's first unit, before any design turn: four MG90S servos from `lib.servo`, hip and knee pitch per leg, catalog horns, bearings and fasteners, modelled printable mounts, no world geometry. ot6 has no biped baseline, because Finch (`cool-hill-9617`) was written by the actor with no model turn. Declared target `gap-f7-biped-designed-unassisted-same`; the human owns the checkbox edit [rec: kind-dusk-1609].

Reconcile judgement: retain `open`; a void call is neither a pass nor an attempt, and no design turn has yet been dispatched for F7 [rec: keen-wing-6569] [rec: narrow-wave-7452] [rec: sunny-chart-5873].

## Negative knowledge

None yet.

## Provenance

- kind-dusk-1609 — the ot7 directive (ADR-341) declared this criterion as gap `gap-f7-biped-designed-unassisted-same`
- silent-union-5108 — ADR-345 prompt freeze recovered with digest pins; no design or repair evidence
- peaceful-hill-3013 — tested bounded frozen-design collector; no design attempt or fit/smoke success
- red-hawk-4600 — single frozen biped dispatch refused; no accepted geometry or simulation; F7 remains open
- keen-wing-6569 — the ot7 restart directive (ADR-355): the refused call is void and consumes no slot
- narrow-wave-7452 — the F7 call classified void by the runner's code; retry named `ot7-plover-b`
- rare-birch-0755 — F4's first model turn timed out thinking; the thinking-bound and stream-capture gate applies before any F7 dispatch
- sunny-chart-5873 — F5 exhausted with catalog hardware its one failing count; F7 on `ot7-plover-b` named after F6
- lawful-grotto-1291 — ADR-362: F7 runs on the same product version as F6, build replies carrying the advisory inventory block; frozen prompts unchanged
