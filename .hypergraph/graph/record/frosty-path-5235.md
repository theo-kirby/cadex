---
node_id: ea1b3c7f-975b-5633-a104-b10392d580c1
slug: frosty-path-5235
title: 'ot6 closing report: docs/probes/ot6/REPORT.md links D1–D9 to their records and receipts, preserves the measured failures; D10 evidenced, done claimed for review'
created_at: '2026-09-14T05:24:44+00:00'
parents:
- bold-arbor-2078
summary: ''
---
## What

The ot6 closing report, `docs/probes/ot6/REPORT.md` (14.5 KB, under the 16 KB receipt cap): one section per criterion D1–D9 with **Evidence** (relative links to the committed receipts, screenshots and scripts under `docs/probes/ot6/` and `docs/review-design/`, the ADR numbers, and the record slugs that carry each claim), **Measured** (the numbers the records report) and **Caveat** (what the evidence is not), a D10 section naming this page and its test, and a **What remains open** list. Pinned by `test_closing_report_links_every_criterion_to_committed_evidence` in `cli/tests/test_review_design.py`: a section per D1–D10 and the open-items section, every relative link resolving to a committed file, every `[rec: …]` slug existing in `.hypergraph/graph/record/`, every ADR it names (ADR-328 through ADR-340 required) present in `docs/DECISIONS.md`, and no private address or hostname; the existing caps parametrisation holds it under 16 KB. Commit `45e6618b` (the report and the test), one logical change. No product code, protocol, payload, engine or dependency change.

## Why

D10 is the only criterion without evidence (STATE.md after `da12657b`); the critic named it as this iteration's unit and the charter's exhaustion policy is `report_done`: when D1–D9 each have evidence, the next unit is the closing report, and done is claimed for the critic's review.

The critic also asked, "through reconciliation", to correct D7–D9's owner-checkbox-only `open` statuses and to qualify `ready-sand-2621`'s dashboard claim as historical. **Not done by reconciling**: a work iteration may not run the reconcile skill or edit state nodes, and this is a work iteration. Done instead the contributor's way — this record declares those exact impacts on `ready-sand-2621`, `civic-creek-8215` and `civic-lily-1239` (open → working, evidenced pending the owner's tick, the same reading D1–D6 already carry; D7's dashboard claim historical, the service serving Heron), and the report says the same in D7's caveats, so the next reconcile pass folds them with nothing to infer. Reward tuning, memory compaction and the obsolete plan's clearance unit were not pursued, as asked.

## Method

1. Read the ten ot6 state nodes and their provenance, the probe READMEs and receipts under `docs/probes/ot6/`, the branch's commit list, the receipt tests and the caps test, and the live service (`systemctl --user` unit serving `ot6-heron`, `/api/project` current run `heron1-final`, accepted revision `0c8c64c92252…`, unchanged by this unit).
2. One identity looked contradictory and was checked rather than copied: Heron's design receipt names accepted revision `9c1f2fe7ea19…` and the training receipt `5971903121bf…`, while the page serves `0c8c64c92252…`. All three carry the same script digest `f9be3985bc55…`; the revision identity carries the playback parameter values. The report says so.
3. One citation was wrong on first draft and fixed: the `part.offset` nondeterminism has no ADR of its own (it lives in `kind-reef-3852` and `robin/RESTORE.md`), so the report cites the receipt, and the test now holds every ADR the report names to the log.
4. Wrote the report, then the test; ran the receipt and caps tests of `cli/tests/test_review_design.py` (`-k "closing_report or ot6_evidence or spec_itself"`): 111 passed, 0 failed, 0.14 s; the new test alone: 1 passed. The browser tests were not re-run — no page, script or product code changed.

## Result

`docs/probes/ot6/REPORT.md` exists and is test-pinned; D10's evidence is present. **D1–D10 each now have evidence in a record, and this record claims done for the critic's review** under the charter's exhaustion policy. The persistent operator dashboard still serves the active project `ot6-heron` with `heron1-final` current (checked at the unit's start; nothing in this unit touched it).

What the report preserves, deliberately: Robin's diverged `robin1` kept as a failed run and its unrecoverable first accepted revision; D9's restart evidence resting on the fixture test and ot5's Lark restart, with no real restart during ot6 training; Heron's checkpoint-20 policy reaching on 0/10; Finch's shuffle being stand-task behaviour; phone evidence being emulated touch. What remains open is listed in the report: reward terms on Robin and Heron (open design decisions in their projects), fit at moving poses, `part.offset` non-reproducibility on the D-shaft, no physical device, and the north-star legs the charter excludes.

Assumptions: the roadmap carries no ot6 line (no earlier ot6 unit added one), so none was added; the report cites commits by short hash because the run's memory already does. No new dependency. If the critic rejects, the next unit fixes the report forward; it is not a repeat lifecycle, a fourth mechanism or a long-term rung.

Dispatch closed: 1 unit — the ot6 closing report written and test-pinned; D10 evidenced, done claimed for review.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot6
- commit: 45e6618b3744872914c6dc8cc4d9dff6b990306c

## State Impact

- target: chilly-road-8573 — open → working: the closing report exists at docs/probes/ot6/REPORT.md (14.5 KB), a section per D1–D10 with evidence links, measurements and caveats and a what-remains-open list, pinned by test_closing_report_links_every_criterion_to_committed_evidence (links, record slugs, ADRs, no private address, the 16 KB cap); done claimed for the critic's review, the owner's checkbox outstanding
- target: ready-sand-2621 — open → working on the same reading as D1–D6: every clause of D7 has committed evidence and only the owner's checkbox is outstanding; the dashboard claim is historical — the operator service now serves ot6-heron, Robin's runs retrievable by pointing it back; the stationary-balance reward term stays an open design decision in the project
- target: civic-creek-8215 — open → working on the same reading: every clause of D8 has committed evidence, only the owner's checkbox is outstanding; the 3 mm-low hold stays an open design decision in the project
- target: civic-lily-1239 — open → working on the same reading: D9's final assessment is committed and test-pinned, only the owner's checkbox is outstanding; restart during real training rests on the fixture test and ot5's Lark restart
- target: round-sun-8398 — D1–D10 each have evidence in a record; done is claimed for the critic's review under the report_done exhaustion policy; if rejected the next unit fixes the report forward, never a repeat lifecycle or a fourth mechanism
