---
node_id: f2d3bc57-743b-5295-8114-e65854ed2df7
slug: eager-summit-3153
title: F9. Nothing regressed
created_at: '2026-09-14T17:28:05+00:00'
parents:
- mild-ledge-7157
summary: ''
---
Status: working

## Current

**F9's evidence document now says what the checker actually does, and claims only what it computes [rec: pale-jasper-8166] [rec: loyal-flame-8896].** `docs/probes/ot7/REGRESSION.md` read "The checker reports every overlap and has no implicit seating exceptions", which ADR-372 made false — a pair welded by an unsuppressed `fixed` joint is exactly one implicit exception. That sentence is replaced with the exception stated and the reason the retained numbers did not move anyway: a retained row is the measurement the accepting engine published, it carries no intent, and reading it back recomputes none. Beside it is a table of what those same measurements say under ADR-372's weld exemption, computed through `fit_summary` with each script's own welds supplied as the `attached` intent — Finch 44 failing → 16 cleared → 28 remain, Robin 39 → 11 → 28, Heron 20 → 8 → 12. No overlap is silenced (the 12 / 8 / 6 intersections stand) and a pair merely sharing a host is not cleared, because ADR-372 infers no transitivity. `cli/tests/test_retained_fit.py::test_weld_exemption_would_clear_exactly_these` pins both columns and fails if intent handling is removed from `pair_status` [rec: pale-jasper-8166].

The claim was then narrowed to what it models [rec: loyal-flame-8896]. The heading reads "under ADR-372's weld exemption"; the sentence attributing the gap between the columns to "the four checker changes (ADR-370 – ADR-373)", and the reading of the third column as what a new design would be told, are removed; and three exclusions are named. ADR-370's attachment report is not modelled — the retained receipts carry no `attachments` key and `attachment_summary` reads `unavailable` with `pairs_checked: 0`. ADR-371's sweep coverage is not modelled — every retained `clearance_sweep` reads `unavailable`, "No published sweep for this accepted revision". ADR-373 governs a clearance declaration these three scripts never make. Measured while narrowing it: of the welded pairs in the retained receipts (Finch 24, Robin 21, Heron 12), Finch's and Heron's all meet within ADR-370's 0.001 mm tolerance and **ten of Robin's do not** — its chassis stands 0.3 mm from each of two motors and 0.6 mm from each of eight board and clamp screws. A rebuild would report that; the retained receipts cannot. `test_welded_pairs_that_do_not_meet` pins the counts, the distances and the absent key [rec: loyal-flame-8896].

Neither unit changed product code, and no retained design was rebuilt or re-accepted: the retained measurements, the accepted revisions and the 44 / 39 / 20 comparison are untouched. `cli/tests` 802 then 805 passed, 1 skipped [rec: pale-jasper-8166] [rec: loyal-flame-8896].

**F9 evidence is complete, pending the owner's checkbox.** `docs/probes/ot7/REGRESSION.md` consolidates green engine results (2,142 passed/53 skipped), CLI results (693 passed/1 skipped), successful build/stage, and the packaged lifecycle gate (18 passed), with their distinct verification scopes. The closure unit reused these receipts rather than rerunning gates [rec: narrow-valley-3317].

Six preserved restore/reopen checks for Finch, Robin and Heron preserve accepted identity and all 787 published/rebuilt pairs (406/276/105). Their 44/39/20 static failures are explained by ot6 screw exceptions, undeclared seatings/gaps and exactly two corrected Heron numerical threshold flags. These retained final revisions have no unknowns or world geometry; unavailable sweeps remain unavailable. F4's first seed is distinct [rec: narrow-valley-3317].

Reconcile judgement: mark `working`, correcting the prior closure interpretation. F9 requires passing regression gates, retained compatibility and explained checker differences; the retained designs' explained fit failures do not prevent closure. This does not close F4–F7 or claim whole-goal completion [rec: narrow-valley-3317].

Reconcile judgement, this pass: `pale-jasper-8166` declared its REGRESSION.md delta against `civic-lily-1239`, which is ot6's **D9** and whose evidence is `docs/probes/ot6/regression/`. Its content is ot7's `docs/probes/ot7/REGRESSION.md` — F9's evidence, and the same document its own child record `loyal-flame-8896` correctly targets here — so it is folded into this node and D9's is left untouched [rec: pale-jasper-8166] [rec: loyal-flame-8896]. Status is unchanged: both units corrected what the document *says* about receipts that did not move [rec: pale-jasper-8166] [rec: loyal-flame-8896].

## Negative knowledge

- [scope: reading a retained ot7 fit receipt as what today's checker would say | confidence: high | evidence: pale-jasper-8166, loyal-flame-8896] A retained row is the measurement the accepting engine published. It carries no intent and reading it back recomputes none, so a later checker rule cannot move a retained number — the 44 / 39 / 20 comparison is stable by construction rather than by luck. The counterfactual beside it models ADR-372's weld exemption **alone**, on one retained measurement set, and is not a fresh-build verdict for Finch, Robin or Heron: ADR-370's attachment report, ADR-371's sweep coverage and ADR-373's clearance rule are outside it, and the sharpest of those exclusions has its own measurement (ten of Robin's twenty-one welds hold nothing, at 0.3 and 0.6 mm).

## Provenance

- kind-dusk-1609 — the ot7 directive (ADR-341) declared this criterion as gap `gap-f9-nothing-regressed-both-suites`
- happy-dawn-1960 — initial F1 suite results, focused licensing repair and packaged-gate scope
- steady-quartz-9854 — corrected CLI suite 636 passed/1 skipped; explicitly no fresh engine or F9 claim
- crisp-ember-0302 — F2 engine/packaged success, retained full-CLI telemetry failure and passing isolated retry
- misty-spark-6372 — fresh green engine/CLI/packaged producer runs; retained-design comparisons remain open
- green-river-3790 — ADR-350 consumer unit: engine 2,124/53, CLI 641/1, packaged 17 after one build and stage
- curious-cedar-4881 — ADR-351 backfill with iteration-13 gates: engine 2,127/53, CLI 641/1 to completion, packaged 18
- kind-flint-2780 — same green gates reaffirmed; Finch copy rebuilt under the product checker; retained-design comparison still open

- lean-fountain-9707 — green F8 engine/CLI and staged smoke verification without engine or payload changes
- lucky-willow-8039 — retained read-only ot6 comparison, exact pair-table equality and explained verdict differences
- hidden-lodge-4550 — corrected retained counts 44/39/20; latest green suites, fresh build/stage and packaged gate; F9 explicitly remains open

- keen-quill-2265 — portable regression pins all 787 measurements and 44/39/20 failures; CLI 684/1
- still-raven-7629 — six packaged restores/reopens preserve identity and rebuilt measurements; lifecycle 18 passed
- tidy-journey-9462 — paged build-reply regression and negative control; CLI 686 passed/1 skipped
- narrow-valley-3317 — consolidated regression closure receipt; explicitly corrects F9 to working despite explained retained fit failures

- pale-jasper-8166 — the receipt made true against ADR-372's weld exemption, with the counterfactual table computed from the retained rows through `fit_summary` and test-pinned; declared against `civic-lily-1239` and folded here
- loyal-flame-8896 — that counterfactual narrowed to ADR-372 alone, the ADR-370/371/373 exclusions named, and Robin's ten non-meeting welds measured at 0.3 / 0.6 mm and pinned
