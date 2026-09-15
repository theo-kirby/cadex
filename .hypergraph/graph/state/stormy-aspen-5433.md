---
node_id: 02f9a989-8616-549c-95e7-c9d943b99a0b
slug: stormy-aspen-5433
title: F5. The arm is designed unassisted
created_at: '2026-09-14T17:28:05+00:00'
parents:
- mild-ledge-7157
summary: ''
---
Status: open

## Current

**F5 has had no design turn: its one dispatch is a void call, and the create prompt and all three continuations are unspent.** The frozen Heron create attempt was dispatched once and refused by the provider session limit in 1.917 seconds (CLI exit 1): zero completed design turns, zero continuations, no accepted revision, no actor design edits; static fit, swept fit and inventory unavailable; smoke exited 1 because `script.json` does not exist [rec: quiet-dew-5243]. Under ADR-355 that call is **void, not an attempt** [rec: keen-wing-6569]; the runner now classifies it so by code from its retained transcript (`docs/probes/ot7/attempts/void-calls.json`), listed apart from the design's attempts, with the retry named `ot7-heron-b`, a fresh project, same frozen prompt, only while Claude is available [rec: narrow-wave-7452]. The portable receipt at `docs/probes/ot7/attempts/heron-refusal.json` retains transcript and artifact hashes and stays in the closing-report accounting [rec: quiet-dew-5243].

**Before the retry is dispatched, the F4 result names a gate that applies here too [rec: rare-birch-0755].** The first design turn that reached a model (F4's repair) read the measured fit and then spent one 64,000-token message almost entirely on thinking, hitting the output cap without a tool call, and was killed at the runner's 30-minute bound with no submission. The CLI passes no thinking or output bound and the collector loses the stream on a kill; both are to be decided or fixed before any further design turn, F5 included. Reconcile judgement: derivable from that record's charter-level impact, folded here so the F5 dispatch is not taken blind.

**The evidence collector [rec: peaceful-hill-3013] [rec: narrow-wave-7452].** `docs/probes/ot7/runner/` (ADR-354) validates frozen prompt hashes, permits one create and at most three ordered continuations, refuses restart and unfrozen follow-ups, retains per-turn measured static fit, raw swept coverage, inventory, transcript hashes and one final bounded smoke, and voids usage-limit calls without spending a slot. It refuses an existing project, so a retry is never a resume.

**Heron's create prompt is frozen** at `docs/probes/ot7/prompts/heron.create.prompt.txt` (sha256 `bcda5af5…`), byte-identical to its ot6 prompt, with three ordered continuation prompts [rec: silent-union-5108].

Charter criterion: **F5. The arm is designed unassisted.** Heron's ot6 create prompt, in a fresh project, reaches an accepted design with zero failing static and swept fit checks, zero actor edits, at most three frozen continuation prompts, catalog hardware for every purchased part, and a passing smoke rollout. Evidence: prompts and continuation count, per-turn fit failure counts, final fit report, inventory, smoke result, and the comparison with ot6. Declared target `gap-f5-arm-designed-unassisted-heron`; the human owns the checkbox edit [rec: kind-dusk-1609]. The ot6 comparison point is Heron (`civic-creek-8215`): one 9,648-byte prompt, a 24-minute turn, three measured corrections fed back by hand before acceptance. No policy training this run — smoke rollouts only, bounded to five minutes (F8) [rec: kind-dusk-1609].

Reconcile judgement: retain `open`; a void call is neither a pass nor an attempt [rec: keen-wing-6569] [rec: narrow-wave-7452].

## Negative knowledge

None yet.

## Provenance

- kind-dusk-1609 — the ot7 directive (ADR-341) declared this criterion as gap `gap-f5-arm-designed-unassisted-heron`
- silent-union-5108 — ADR-345 prompt freeze recovered with digest pins; no design or repair evidence
- peaceful-hill-3013 — tested bounded frozen-design collector; no design attempt or fit/smoke success
- quiet-dew-5243 — single frozen Heron create refused; no accepted design or simulation, portable evidence retained
- keen-wing-6569 — the ot7 restart directive (ADR-355): the refused call is void and consumes no slot
- narrow-wave-7452 — the F5 call classified void by the runner's code; retry named `ot7-heron-b`
- rare-birch-0755 — F4's first model turn timed out thinking; the thinking-bound and stream-capture gate applies before any F5 dispatch
