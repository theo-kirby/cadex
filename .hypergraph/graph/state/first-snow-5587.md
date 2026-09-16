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

**The closing report at `docs/probes/ot7/REPORT.md` carries F4 and F5 through exhaustion; critic acceptance of done remains unmet [rec: sunny-chart-5873] [rec: lawful-grotto-1291].** The summary, the per-design attempts row (F5 at 4, all on `ot7-heron-c`), the F5 checks row marked exhausted with catalog hardware its one failing count, and the F10 section naming F4 and F5 exhausted with F6/F7 next in `ot7-robin-b` and `ot7-plover-b` are all current [rec: sunny-chart-5873].

**The product-version comparison now lists three changes since F5, not one [rec: tidy-nest-3309].** The F10 section's "Product version" paragraph opens with ADR-362 (the advisory inventory block), ADR-366 (`fit.sweep` in the build reply) and ADR-367 (sweep coverage published whether or not a step is declared), each with what it publishes that F5's four turns did not, plus ADR-368's wording follow-up; F5 is not re-run, no frozen prompt changed, and any difference from F5 is a difference across those three changes [rec: lawful-grotto-1291] [rec: pale-garden-4669] [rec: tidy-nest-3309]. The report also now carries the dated F6 gate reading as a measurement rather than only a records fact: on 2026-09-16 at 16:39 UTC the window probe was refused in 2.3 s on the organisation-level Fable limit (five-hour 12 %, seven-day 52 %, reset 2026-09-18 14:00 UTC), and no prompt was spent [rec: tidy-nest-3309].

**The report has been written forward, never edited away, once per iteration that produced evidence** — iterations 46, 48, 49, 51, 52, 53, 55, 56, 57, 59, 60, 61, 66, 67 and 72, then the ADR-362 unit (commit `fd3b3643`) and the ADR-368 unit (commit `3cd8905e`). Each contributed its section, its slot-table and evidence rows, and its indexed receipt; the per-iteration detail lives in the record nodes named in `## Provenance` below rather than being restated here. The arc through F4 and F5: F4's repair prompt and three continuations all reached the model on `ot7-heron-repair-d` (receipts `repair-completed-d.json` and `repair-continue-{1,2,3}-d.json`), exhausting it at iteration 53; F5's create was interrupted once on `ot7-heron-b` (receipt `heron-interrupted-b.json`, with an `interruption_analysis` block) and then ran create plus three continuations on `ot7-heron-c` (receipts `heron-create-c.json`, `heron-continue-{1,2,3}-c.json`), exhausting it at iteration 72 with every count met but catalog hardware [rec: stormy-snow-5452] [rec: terse-mesa-7963] [rec: light-river-7871] [rec: plain-dusk-2906] [rec: damp-cedar-5823] [rec: mellow-summit-9733] [rec: crimson-wind-8698] [rec: flat-cove-2253] [rec: easy-otter-0439] [rec: forest-bell-5161] [rec: sunny-chart-5873]. Two corrections were made forward at the critic's direction rather than by edit: the F5 attempts cell reading "2, both" against three completed turns [rec: neat-reef-5625], and ADR-360's refusal wording in `docs/CLI.md` and DECISIONS.md [rec: icy-ivy-3606] [rec: slender-union-6486]. Every receipt is indexed in the retained README, and the runner README records the ADR-358 gate's live dispatches, the dispatch and resume commands per iteration, and the window readings [rec: plain-dusk-2906] [rec: damp-cedar-5823] [rec: mellow-summit-9733] [rec: flat-cove-2253] [rec: easy-otter-0439] [rec: slender-union-6486] [rec: forest-bell-5161].

**Test evidence.** The five ot7 test files pass (215 after iteration 55); `test_review_design.py`'s receipt-cap and private-path selection reads 121 passed after iterations 66 and 72; the three doc-reading files read 79 passed after iterations 57, 66, 67 and 72; and the full CLI suite reads 760/1 after ADR-359, 763/1 after ADR-360, 768/1 after ADR-362 and **783 passed, 1 skipped** after ADR-367 and ADR-368 [rec: mellow-summit-9733] [rec: crimson-wind-8698] [rec: flat-cove-2253] [rec: slender-union-6486] [rec: forest-bell-5161] [rec: neat-reef-5625] [rec: sunny-chart-5873] [rec: lawful-grotto-1291] [rec: pale-garden-4669] [rec: tidy-nest-3309].

Reconcile judgement: the document half of F10 is current and self-consistent — the product-version count is the one thing that had drifted, and it is corrected. Done acceptance is not claimable while F6 and F7 have every slot unspent, and F10 is the run's last unit and cannot be written while they are unattempted [rec: soft-creek-6253]. Retain `open`.

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
- mellow-summit-9733 — iteration 55 section; the F5 create call interrupted at the bound, receipt indexed, F5 rows written forward
- crimson-wind-8698 — iteration 56: the F5 and F4 rows corrected as the critic asked; the F5 row names the retry's effort
- flat-cove-2253 — iteration 57 section; F5's first completed turn, the three counts it fails on, receipt indexed
- easy-otter-0439 — iteration 59 section; F5's first continuation, the two counts it still fails on, the smoke, receipt linked; runner README iteration 59
- slender-union-6486 — iteration 60: two ADR-360 forward notes, runner README page sizes, DECISIONS.md and docs/CLI.md; no design turn
- icy-ivy-3606 — iteration 61: ADR-360's refusal wording corrected forward in docs/CLI.md and DECISIONS.md; no design turn
- forest-bell-5161 — iteration 66 section; F5's second continuation, the one count it still fails on, the smoke, receipt indexed; runner README iteration 66
- neat-reef-5625 — iteration 67: the F5 attempts cell corrected to 3, all; no design turn at 73 %
- sunny-chart-5873 — iteration 72 section; F5 exhausted with one count failing, the F5 rows and the F10 section written forward, receipt indexed; runner README section
- lawful-grotto-1291 — the F10 section's product-version paragraph: F6 and F7 run one product change newer than F5 (ADR-362), F5 not re-run, frozen prompts unchanged
- pale-garden-4669 — ADR-367 lands as a third product change F6/F7 will run on, and the refused window probe is dated to a 2026-09-18 14:00 UTC reset
- tidy-nest-3309 — the product-version comparison corrected forward to three changes since F5, each with what it publishes; the dated refused probe written into the report
- soft-creek-6253 — the hold that keeps F10 open: no probe, no prompt, all eight F6/F7 slots unspent
