---
node_id: fa126afd-6bd8-51d7-896f-0c1aaa676854
slug: polished-forest-0215
title: F4. The agent repairs from measurements alone
created_at: '2026-09-14T17:28:05+00:00'
parents:
- mild-ledge-7157
summary: ''
---
Status: open

## Current

**The single frozen repair invocation was refused at the provider's session limit: F4 remains open.** The fresh Heron seed was extracted from its first accepted ot6 revision `7e9eff5c…`; one `claude-fable-5` invocation with the frozen prompt, without `--resume`, exited 1 after 4.09 seconds with zero completed design turns. No retry or actor design edit occurred. `docs/probes/ot7/retained/repair-refusal.json` retains identity, timings and transcript/artifact digests [rec: lucky-willow-8039].

Historical seed artifacts were missing, so both before-fit reads failed. The normal product-call restore recreated them and changed the attempt pointer while preserving accepted revision, accepted digest and script bytes. The newly restored report has 105 pairs and 21 failures: 8 intersections, 12 below-clearance pairs and one plane. Both servo/cheek overlaps are 248.20162986795 mm³; the 0.2 mm child/horn gaps do not fail without contact declarations. Sweep unavailable. This is newly restored evidence, not a historical before-fit report or a repair result [rec: lucky-willow-8039].

The design-agnostic prompt remains frozen at `docs/probes/ot7/prompts/repair.prompt.txt` (sha256 `5d846901…`), with wording test-pinned [rec: silent-union-5108]. Charter criterion: an unassisted session on the first Heron revision resolves all three defects from tools and one frozen continuation prompt, accepting zero failing fit checks, with before/after reports and turn/transcript evidence [rec: kind-dusk-1609]. Reconcile judgement: retain `open`; a provider refusal is not a completed repair attempt [rec: lucky-willow-8039].

## Negative knowledge

None yet.

## Provenance

- kind-dusk-1609 — the ot7 directive (ADR-341) declared this criterion as gap `gap-f4-agent-repairs-from-measurements`
- silent-union-5108 — ADR-345 prompt freeze recovered with digest pins; no design or repair evidence

- lucky-willow-8039 — one frozen invocation refused, zero completed design turns; restored seed identity and 21-failure report retained
