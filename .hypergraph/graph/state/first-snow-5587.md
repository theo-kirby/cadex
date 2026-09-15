---
node_id: 5ec2905b-5ee7-54e2-b0bc-2bdba67648ce
slug: first-snow-5587
title: F10. A closing report exists and the critic accepted done
created_at: '2026-09-14T17:28:06+00:00'
parents:
- mild-ledge-7157
summary: ''
---
Status: open

## Current

**The closing report at `docs/probes/ot7/REPORT.md` carries F4 through exhaustion, with its slot totals consistent and what remains reduced to F5–F7; critic acceptance of done remains unmet.** Sections were written forward on 2026-09-15 for iteration 46 (ADR-356: the F4 row reads zero attempts, one interrupted call apart from three void ones, retry named) [rec: sunny-chart-3499]; iteration 48 (the frozen repair prompt completed on `ot7-heron-repair-d`, the three ot6 defects read against the collector's after-read, receipts `repair-void-c.json` and `repair-completed-d.json`) [rec: stormy-snow-5452]; iteration 49 (ADR-357: headline, slot table, F4 evidence row and remaining-work order say the repair prompt is spent and three continuations unspent; the d receipt carries a `ruling` field) [rec: terse-mesa-7963]; iteration 51 (continue-1 completed, F4 at 2 attempts reached the model and 2 of 3 continuations unspent, receipt `repair-continue-1-d.json` at 8.7 KB) [rec: light-river-7871]; iteration 52 (both attempts: the ADR-358 gate written by the cut-off first attempt and then continue-2 completed, F4 at 3 attempts and 1 continuation unspent, receipt `repair-continue-2-d.json` at 7.9 KB) [rec: plain-dusk-2906]; and iteration 53 (continue-3 completed, F4 exhausted at 4 attempts with 0 of 3 continuations unspent and no retry, the bar read as final, receipt `repair-continue-3-d.json` at 7.8 KB) [rec: damp-cedar-5823]. Each receipt is indexed in the retained README, and the runner README records the ADR-358 gate's two live dispatches [rec: plain-dusk-2906] [rec: damp-cedar-5823]. The five ot7 test files pass (215) and the full CLI suite reads 755 passed, 1 skipped after each of the last two sections [rec: plain-dusk-2906] [rec: damp-cedar-5823]. Reconcile judgement: the document half of F10 is current and self-consistent; done acceptance is not claimable while F5–F7 have every slot unspent. Retain `open`.

**How the report got here.** It was rewritten forward under ADR-355 with the amendment section, a per-design table of void calls, attempts, unspent slots and retry project, and the 2026-09-14 "exhausted" and "terminal incomplete" wording kept and marked superseded, not deleted; the six pre-restart calls are listed apart from design attempts as void by code (`docs/probes/ot7/attempts/void-calls.json`) [rec: narrow-wave-7452]. The F4 timeout on `ot7-heron-repair-b` was written in with its receipt (`repair-timeout-b.json`, 11,180 bytes), then ruled interrupted under ADR-356 with a `ruling` field added and the historical values kept [rec: rare-birch-0755] [rec: sunny-chart-3499]. Iteration 48's "F4 exhausted" claim was rejected by the critic against the charter's exhaustion policy and corrected forward rather than edited away [rec: terse-mesa-7963]; F4's exhaustion in iteration 53 is the real one, all four prompts having reached the model [rec: damp-cedar-5823].

**What the report carries [rec: windy-otter-5423] [rec: blue-slope-0916] [rec: slender-spring-1027].** It links F1–F9 evidence, frozen prompts and transcript digests, fit availability, smoke outcomes and ot6 comparisons. Validation checked its links, seven frozen prompt hashes and transcript digests, and held it under the 16 KB cap after the iteration-40 rewrite condensed prose. The three creates have no accepted geometry or simulation; the seed's 21-to-15 failure correction is threshold slack, not agent repair. Iteration 40's "terminal incomplete" outcome is the wording the amendment superseded: the six refused calls are void, no model saw a prompt, nothing was exhausted then [rec: keen-wing-6569].

Charter criterion: **F10. A closing report exists and the critic accepted done.** One row per design: prompts, turns, continuation prompts used, fit failures per turn, final static and swept checks, smoke result, and the ot6 comparison; it links the evidence for F1–F9 and names what remains open, claiming nothing a record does not carry. This is the run's last unit; declared target `gap-f10-closing-report-exists-critic`, and the human owns the checkbox edit [rec: kind-dusk-1609] [rec: keen-wing-6569]. The ot6 precedent (`chilly-road-8573`) test-pinned the report in `cli/tests/test_review_design.py` and needed one more unit for the critic's acceptance. Exhaustion policy is `report_done`: a design is exhausted only after its create or repair prompt and all three continuations reached the model, void calls never exhaust a design, and "no authorized experiment remaining" may not be claimed while any design has an unspent slot [rec: keen-wing-6569] [rec: terse-mesa-7963].

## Negative knowledge

- [scope: a receipt's `status: exhausted` written by the collector before ADR-357 | confidence: high | evidence: terse-mesa-7963] It is not evidence of exhaustion: the collector of that day counted the repair prompt as the design's only prompt. Read the `ruling` field and the row count against the four-prompt schedule.

## Provenance

- kind-dusk-1609 — the ot7 directive (ADR-341) declared this criterion as gap `gap-f10-closing-report-exists-critic`
- windy-otter-5423 — closing evidence report exists; agent outcomes and critic done acceptance remain unproven
- blue-slope-0916 — report updated with the iteration-39 collector outcome, the sixth provider refusal
- slender-spring-1027 — report rewritten to a terminal incomplete outcome, condensed under 16 KB; reconcile forbidden in that dispatch
- keen-wing-6569 — the ot7 restart directive (ADR-355): the six calls are void, the exhausted handoff is superseded and is fixed forward
- narrow-wave-7452 — REPORT.md, runner README and attempts README rewritten forward with void calls tabled apart from attempts; superseded wording kept
- rare-birch-0755 — report, retained index and runner README written forward with the F4 timeout receipt
- sunny-chart-3499 — iteration 46 section; the F4 row reads one interrupted call apart from three void ones
- stormy-snow-5452 — iteration 48 section and F4 rows written forward with the completed repair turn and both receipts
- terse-mesa-7963 — iteration 49 section; contradictory F4 slot totals corrected forward, d receipt given a ruling field
- light-river-7871 — iteration 51 section; continue-1 completed, receipt indexed
- plain-dusk-2906 — iteration 52 section for both attempts; ADR-358 gate and continue-2, receipt indexed
- damp-cedar-5823 — iteration 53 section; F4 exhausted, the bar read as final, what remains is F5–F7
