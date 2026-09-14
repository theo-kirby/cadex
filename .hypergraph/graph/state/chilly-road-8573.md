---
node_id: 1e4ec655-8284-594d-9bbc-22118f01a4f2
slug: chilly-road-8573
title: D10. A closing report exists and the critic accepted done
created_at: '2026-09-13T21:25:10+00:00'
parents:
- round-sun-8398
summary: ''
---
Status: working

## Current

**The closing report exists and is test-pinned, the critic accepted done, and the owner ticked D10 on 2026-09-14** (commits `45e6618b`, `1ba64fd5`, `9a203c24`). As first written [rec: frosty-path-5235]: `docs/probes/ot6/REPORT.md` (14.5 KB, under the 16 KB receipt cap) carries one section per criterion D1–D9 with **Evidence** (relative links to the committed receipts, screenshots and scripts under `docs/probes/ot6/` and `docs/review-design/`, the ADR numbers, and the record slugs that carry each claim), **Measured** (the numbers the records report) and **Caveat** (what the evidence is not), a D10 section naming the page and its test, and a **What remains open** list. `test_closing_report_links_every_criterion_to_committed_evidence` in `cli/tests/test_review_design.py` holds it: a section per D1–D10 and the open-items section, every relative link resolving to a committed file, every `[rec: …]` slug existing in `.hypergraph/graph/record/`, every ADR it names (ADR-328 through ADR-340 required) present in `docs/DECISIONS.md`, no private address or hostname, and the existing caps parametrisation under 16 KB; the receipt and caps tests ran 111 passed. No product code, protocol, payload, engine or dependency changed [rec: frosty-path-5235].

What the report preserves rather than smooths over: Robin's diverged `robin1` kept as a failed run and its unrecoverable first accepted revision; D9's restart evidence resting on the fixture test and ot5's Lark restart, with no real restart during ot6 training; Heron's checkpoint-20 policy reaching on 0/10; Finch's shuffle being stand-task behaviour; phone evidence being emulated touch. One identity that looked contradictory was checked, not copied: Heron's design receipt names accepted revision `9c1f2fe7ea19…`, the training receipt `5971903121bf…`, and the page serves `0c8c64c92252…` — all three carry the same script digest `f9be3985bc55…`, the revision identity carrying the playback parameter values, and the report says so. The `part.offset` nondeterminism has no ADR of its own (it lives in `kind-reef-3852` and Robin's `RESTORE.md`), so the report cites the receipt. Its open list: reward terms on Robin and Heron (open design decisions in their projects), fit at moving poses, `part.offset` non-reproducibility on the D-shaft, no physical device, and the north-star legs the charter excludes [rec: frosty-path-5235].

**Closed out.** The report's §D10 now states the critic **accepted done** (iteration 30, verdict `done_accepted`, source `critic:codex`) rather than "claimed for review", names [rec: frosty-path-5235] (claimed; `done_rejected` for unreconciled impacts) and [rec: sharp-cedar-0014] (reconciled and claimed again; accepted) around the verdict, and carries the run's final operator-dashboard check: the user unit serving `ot6-heron`, accepted revision `0c8c64c92252…`, three runs `ok`, `heron1-final` named on the page — the same state D9 measured. Commit `1ba64fd5` (one file, 15.3 KB, under the 16 KB cap); report, receipt and caps tests 111 passed; no product code changed. Done was claimed a second time under `report_done` [rec: hollow-slope-2048]. The critic rejected that iteration for one defect: the record's Method section carried the operator's absolute project directory, which the charter forbids committing. Fixed by naming the project portably as `ot6-heron` (commit `9a203c24`, one line; the record's identity, parents, Repo and State Impact untouched); receipt checks 121 passed, `hypergraph check` 0 violations, the dashboard verified again unchanged; done claimed again, and with one acceptance already standing under `on_done_accepted: 2` that acceptance ended the run [rec: rising-bloom-3478]. **The owner ticked D10 in the charter on 2026-09-14 with the evidence unchanged**; the ot6 charter is superseded by ADR-341 [rec: nimble-wing-3050].

Charter criterion: **D10. A closing report exists and the critic accepted done.** `docs/probes/ot6/REPORT.md` links the evidence for D1-D9, states what each measured, and names what remains open, with nothing claimed that a record does not carry. This is the run's last unit, not a repeat of any earlier one. Declared target `gap-d10-closing-report-exists-critic`; the human owns the checkbox edit [rec: brisk-ledge-9638]. Reconcile judgement: `working`, held the way ot5's ticked criteria were — both halves of the criterion now have evidence (the report, and the critic's acceptance recorded in it) and the owner's tick is in the charter [rec: hollow-slope-2048] [rec: nimble-wing-3050].

## Negative knowledge

- [scope: the ot6 closing report | confidence: high | evidence: frosty-path-5235] The report claims nothing a record does not carry, which means it also carries every measured failure the records do; a reader who wants a cleaner story must go to the records, not to a rewritten report. If the critic rejects, the next unit fixes the report forward — never a repeat lifecycle, a fourth mechanism or a long-term rung.
- [scope: absolute paths in the record graph | confidence: high | evidence: rising-bloom-3478] Nine older records from ot4 and earlier (`dry-falcon-5463`, `chilly-basin-7378`, `candid-fern-3092`, `golden-dune-8756`, `steady-chart-0544`, `blue-quill-9477`, `lone-haven-0640`, `terse-crane-6585`) carry home-directory absolute paths committed before the no-absolute-paths rule. They are merged history, deliberately not swept; cleaning them is an owner decision.

## Provenance

- brisk-ledge-9638 — the ot6 directive (ADR-328) declared this criterion as gap `gap-d10-closing-report-exists-critic`
- frosty-path-5235 — the closing report written and test-pinned (commit `45e6618b`), D10 evidenced, done claimed for the critic's review
- hollow-slope-2048 — the report's §D10 records the critic's `done_accepted` (iteration 30) and the run's final dashboard check on Heron (commit `1ba64fd5`); done claimed a second time under report_done
- rising-bloom-3478 — critic fix: the machine-specific project path in hollow-slope-2048 replaced by `ot6-heron` (commit `9a203c24`); checks green; done claimed again, ending the run
- nimble-wing-3050 — the owner ticked D10 on 2026-09-14; evidence unchanged; the ot6 charter superseded by ADR-341
