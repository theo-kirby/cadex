---
node_id: cfe2ac06-1c45-52c3-91bd-2f51b7aa7ae0
slug: chilly-willow-8488
title: 'ot10: A5 confirmation turn 3 — ot10-biped-2 misses at 2/21 on a publication leak; round closes 2 of 3'
created_at: '2026-09-28T20:49:36+00:00'
parents:
- tidy-pebble-6206
summary: ''
---
## What

A5's confirmation-round turn 3, the last pre-registered turn: the frozen biped prompt run once on the new project `ot10-biped-2` (`claude-opus-5-5`, `CADEX_EFFORT=medium`, no continuation). It was launched detached at 2026-09-28T20:13:42Z at `15f2bf9e`. It ended by itself at exit 0, but **it did not publish a design**. Its accepted revision is the agent's servo-orientation probe. Blind scoring gave **2 of 21**, equal to hex3, so **it misses the bar**. I diagnosed the miss to a measured engine defect and published it with scores, renders, sheet, census row and tests. The round is now complete at 2 of 3.

## Why

The critic's message asked for the last pre-registered turn, `ot10-biped-2`, with nothing changed. It said to check `ot10-notes/biped-2/exit` and live pids first. There was no `biped-2` notes directory, no `ot10-biped-2` project and no cadex turn process, so I launched once. Then: wait in-session, score blind, publish, census, test, commit, and update REPORT.md's A5 verdict honestly. I did all of that. **One deviation:** the critic also said "reconcile". This dispatch's rules forbid the hypergraph-reconcile skill in a work iteration, so I did not reconcile. The tail is now 2 unreconciled records (`tidy-pebble-6206` and this one), and the next reconcile pass should fold both. Target: A5 (`loyal-fountain-8709`), the highest-ranked open criterion.

## Method

- **Turn.** `~/cadex-projects/ot10-notes/biped-2/turn.sh` is a copy of quadruped-4's with the plan name swapped. It reads its prompt from `contract.json` `a5.prompts.biped`, and the argv is the same. It ran from 20:13:42Z to 20:32:22Z (19 min), `exit 0`, `ok: true`, accepted revision `6447da4ae63e…`, digest `2a6fb6856355…`, session `ec4f9873…`.
- **Scoring.** `cp -a` to `/tmp/ot10-biped-2`, then the same `pipeline.sh`: `cadex render` (6 s wall), `look_views.py`, and `runner/judge.py`, which makes three blind `claude-opus-5-5` calls under the frozen rubric (sha `1c81caa2…`).
- **Census.** `runner/refusals.census(transcript, "failed_attempt")`, inserted after the last failed attempt, and the README table regenerated with `refusals.table()`.
- **Diagnosis.** From the transcript, plus a direct measurement under `FreeCADCmd`: `App.newDocument()` has `UndoMode 0`. Running `openTransaction`, `addObject`, `abortTransaction` leaves the object in the document. `cadexd.py:500` creates the live document that way, and nothing sets `UndoMode`.
- **Published** under `docs/probes/ot10/`: the hero, five look views, the sheet (all ≤ 81 KB) and `ot10-biped-2-score.json` (no machine paths). The README gets a new section, "A5 attempt 2: the biped (`ot10-biped-2`), confirmation round", and an updated census paragraph. REPORT.md gets a row, the result paragraph, the A5 verdict, the failure list, the census numbers and remaining defect 9.
- **Tests.** A new `test_a5_biped_attempt_2_the_confirmation_round_misses_and_is_diagnosed`, plus the census and report counts. The report test's gate parser now accepts `**unmeasured**` proxies and number-less fit cells, and treats an unmeasured P1 or P2 as a miss.

## Result

**`ot10-biped-2` misses the A5 bar on every item that could be measured.**
- **Judged medians.** T1–T7 = 0/1/0/0/0/0/1, total **2** (the three calls gave 2, 3 and 1). That equals hex3 and is not above it.
- **Proxies.** P1 and P2 are unmeasured, because the probe has no inventory. P3 is 4, because no roles were declared and every part got an index colour.
- **Fit.** Static and swept fit are both unavailable: the probe has no assembly.
- **Electronics.** None published.

**Diagnosis: a product defect, not a design verdict. It is still a counted miss under the pre-registration.**
- The agent named a concept first: a hood-seam torso, a flush visor, bone over graphite.
- It had a full build that passed geometry, assembly, MJCF export and the reset check. That build then stored the servo actuators as result outputs.
- The assembly pass had already created its components when `_native_type` raised `No native publisher exists for output type 'actuator'`. The refusal claimed `accepted_live_state_preserved: true`, which was false.
- 43 objects leaked into the live document. Every later write and rebuild was then refused, with `PUBLICATION_UNTAGGED_OBJECT` or with `Cannot retire XScript output 'floor'`.
- ADR-429 had recorded exactly this `UndoMode 0` gap as known and unfixed, and recorded the retire-linked refusal as "found, not fixed". hexapod-8 wedged on the rename path. biped-2 wedged on the general path.
- A second, smaller cause sits upstream: validation accepts an output type that no publisher can write.

**Census.** 7 refusals, and **none of A4's four classes: 0 of 208 across 17 transcripts.**

**The confirmation round is complete at 2 of 3:** hexapod-11 at 14, quadruped-4 at 16, biped-2 at 2. REPORT.md now says **A5 is not met**, with ten misses. The highest bar reached is unchanged: one design per body plan meets it.

**Tests.** `test_ot10_contract.py` + `test_ot10_report.py`: 44 passed. Full `pixi run python -m pytest cli/tests`: 1064 passed, 1 skipped (12 min 15 s). The engine suite was not re-run: no engine or product code changed, only probe docs, images, census JSON and tests.

**Next unit, as the round requires (diagnose, then fix before any prompt change):**
- Reproduce the leak under the real kernel with a regression test that fails on the current source: a project publish that raises in the assembly pass after creating components must leave the document as accepted, and a later publish must succeed.
- Then fix it. Either roll back the objects the failed publish created, or turn on `UndoMode` for the daemon's document; ADR-429 flagged that one as wider.
- Consider refusing unpublishable output types (such as `actuator`) at validation.
- Any further biped turn is a new registered decision, not part of this round.

Dispatch closed: 1 unit — ot10-biped-2 ran as pre-registered and misses at 2/21 on a measured publication leak (UndoMode 0); published, census'd, tested; confirmation round closes 2 of 3; A5 stays not met

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: e7dcfc229317a17ec818b635126a7375541f4915

## State Impact

- target: loyal-fountain-8709 — Confirmation round turn 3: ot10-biped-2 (frozen biped prompt, 15f2bf9e, opus-5-5, effort medium, no continuation) exit 0 at a servo-orientation probe; misses at 2/21 (0/1/0/0/0/0/1), P1/P2 unmeasured, P3 4, no fit, no electronics. Diagnosed: a publish refused mid assembly pass (actuator stored as an output) leaked 43 objects because the cadexd document runs UndoMode 0 (ADR-429's recorded gap), wedging every later write. Round closes 2 of 3; REPORT.md says A5 not met with ten misses; A4 census 0 of 208 across 17 transcripts; next unit is a regression + fix for the leak (commit e7dcfc22)
- target: forest-wind-0342 — Measured defect: a project publish that raises after creating objects leaks them into the live document (UndoMode 0, abortTransaction restores nothing) while reporting accepted_live_state_preserved: true; validation also accepts an unpublishable output type ('actuator'). Found on ot10-biped-2, not yet fixed
