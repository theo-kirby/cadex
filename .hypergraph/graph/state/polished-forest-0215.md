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

**The single repair prompt is frozen** at `docs/probes/ot7/prompts/repair.prompt.txt` (sha256 `5d846901…`), with its design-agnostic wording test-pinned. The seeded copy of ot6 Heron at `7e9eff5c…` has not been made and no repair turn has run; F4 remains open [rec: silent-union-5108].

Charter criterion: **F4. The agent repairs from measurements alone.** A fresh product-agent session is given Heron's first accepted ot6 revision (`7e9eff5c…`, from a copy of the retained project) and one frozen continuation prompt that contains no part name, number or defect. Using only its tools, it resolves all three defects and accepts with zero failing fit checks. Evidence: turn count and timings, transcript digests, and the fit report before and after. Declared target `gap-f4-agent-repairs-from-measurements`; a record may say "ticks F4" when its evidence exists, and the human owns the checkbox edit [rec: kind-dusk-1609].

The baseline is Heron's ot6 design half (`civic-creek-8215`): the three defects were found by a hand-run probe and fed back as three hand-written `--resume` turns quoting the measurement. Here the continuation prompt is frozen and names nothing ("Read the measured fit report and resolve every failing check." is the shape), the actor never edits the design, and a design that does not get there is a measured result, reported as such. [rec: kind-dusk-1609]

Reconcile judgement: the prompt prerequisite is evidenced, but the design or repair result is not; retain `open` [rec: silent-union-5108].

## Negative knowledge

None yet.

## Provenance

- kind-dusk-1609 — the ot7 directive (ADR-341) declared this criterion as gap `gap-f4-agent-repairs-from-measurements`
- silent-union-5108 — ADR-345 prompt freeze recovered with digest pins; no design or repair evidence
