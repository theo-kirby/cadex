---
node_id: aea7b9a7-f0e2-5224-ae21-fe54d0a4ec03
slug: narrow-dune-9454
title: F6. The balancer is designed unassisted
created_at: '2026-09-14T17:28:05+00:00'
parents:
- mild-ledge-7157
summary: ''
---
Status: open

## Current

**F6 has had no design turn: its one dispatch is a void call, and the create prompt and all three continuations are unspent.** The frozen Robin create attempt was dispatched once and refused by the provider session limit in 1.868 seconds (CLI exit 1): zero completed design turns, zero continuations, no accepted revision, no actor design edits; static fit, swept fit and inventory unavailable; smoke exited 1 because `script.json` does not exist [rec: keen-chart-9070]. Under ADR-355 that call is **void, not an attempt** [rec: keen-wing-6569]; the runner now classifies it so by code from its retained transcript (`docs/probes/ot7/attempts/void-calls.json`), listed apart from the design's attempts, with the retry named `ot7-robin-b`, a fresh project, same frozen prompt, only while Claude is available [rec: narrow-wave-7452]. The portable receipt at `docs/probes/ot7/attempts/robin-refusal.json` retains transcript and artifact hashes and stays in the closing-report accounting [rec: keen-chart-9070].

**Before the retry is dispatched, the F4 result names a gate that applies here too [rec: rare-birch-0755].** The first design turn that reached a model (F4's repair) read the measured fit and then spent one 64,000-token message almost entirely on thinking, hitting the output cap without a tool call, and was killed at the runner's 30-minute bound with no submission. The CLI passes no thinking or output bound and the collector loses the stream on a kill; both are to be decided or fixed before any further design turn, F6 included.

**The evidence collector [rec: peaceful-hill-3013] [rec: narrow-wave-7452].** `docs/probes/ot7/runner/` (ADR-354) validates frozen prompt hashes, permits one create and at most three ordered continuations, refuses restart and unfrozen follow-ups, retains per-turn measured static fit, raw swept coverage, inventory, transcript hashes and one final bounded smoke, and voids usage-limit calls without spending a slot. It refuses an existing project, so a retry is never a resume.

**Robin's create prompt is frozen** at `docs/probes/ot7/prompts/robin.create.prompt.txt` (sha256 `e20ee7ab…`), byte-identical to its ot6 prompt, with the same three ordered continuations [rec: silent-union-5108].

Charter criterion: **F6. The balancer is designed unassisted.** The same bar as F5 on Robin's ot6 create prompt (`docs/probes/ot6/robin/create.prompt.txt`). Declared target `gap-f6-balancer-designed-unassisted-same`; the human owns the checkbox edit [rec: kind-dusk-1609]. The ot6 comparison point is Robin (`ready-sand-2621`): the agent's candidate was accepted only after the actor edited its script twice (the reset-lift literal, then the D-bore replaced by an analytic prism after `part.offset` proved non-reproducible). Under this charter the actor never edits a design [rec: kind-dusk-1609].

Reconcile judgement: retain `open`; a void call is neither a pass nor an attempt [rec: keen-wing-6569] [rec: narrow-wave-7452].

## Negative knowledge

None yet.

## Provenance

- kind-dusk-1609 — the ot7 directive (ADR-341) declared this criterion as gap `gap-f6-balancer-designed-unassisted-same`
- silent-union-5108 — ADR-345 prompt freeze recovered with digest pins; no design or repair evidence
- peaceful-hill-3013 — tested bounded frozen-design collector; no design attempt or fit/smoke success
- keen-chart-9070 — single frozen Robin create refused; no accepted design or simulation, portable evidence retained
- keen-wing-6569 — the ot7 restart directive (ADR-355): the refused call is void and consumes no slot
- narrow-wave-7452 — the F6 call classified void by the runner's code; retry named `ot7-robin-b`
- rare-birch-0755 — F4's first model turn timed out thinking; the thinking-bound and stream-capture gate applies before any F6 dispatch
