---
node_id: 83d43a47-4866-570a-af2a-579a4c4cb9d3
slug: amber-flame-4976
title: 'ot10: ADR-424 P2 leaves out the floor; seven probes re-scored, hex3 P2 0.332→0.189, no A5 verdict changes'
created_at: '2026-09-28T05:05:07+00:00'
parents:
- lucid-glacier-4889
summary: ''
---
## What

Settled the P2 `c_floor`/`floor` exclusion as a recorded decision (ADR-424) and re-scored every earlier probe, hex3 included. P2 `sharp_outside_edge_share` now counts printed parts only: the components the fit reports as world geometry (the floor) are left out, the same set P1 and `look` already leave out. `cli/cadex_cli/inventory.py` `printed_edges` keeps per-placement figures under `by_component`. `render.edge_proxy(inventory, environment)` leaves the environment out and names it under `left_out_as_environment`. `render.write_render` and the bridge's `look` pass the set. The P2 definition in `docs/probes/ot10/README.md` changed, with a new "Decision: P2 leaves out world geometry" subsection and re-score table. Every probe's P2 row was updated, and so were `docs/CLI.md` and ADR-424 in `docs/DECISIONS.md`. The threshold, rubric, bar, procedure and `contract.json` are unchanged.

## Why

The critic ordered this first: "Before that probe, settle the P2 `c_floor` exclusion as a recorded decision in `docs/probes/ot10/README.md` and an ADR. Re-score the earlier probes, hex3 included, if it changes anything." It gates the next A5 probe (loyal-fountain-8709), because a frozen proxy cannot change quietly. I took this as the iteration's one unit. The quadruped rerun the critic named next was **not** started (see Result for why that matters: a completed but unrecorded quadruped attempt already exists).

## Method

- A regression test `test_sharp_outside_edge_share_leaves_out_the_floor` (cli/tests/test_look.py) failed on the previous source (`git stash` of cli/cadex_cli: 1 failed, 3 passed) and passes now.
- Re-measurement: a notes script (`~/cadex-projects/ot10-notes/p2-rescore/measure.py`, outside git) opened each project with restore, read `read_fit` and `read_inventory`, and took each printed component's `source_facts.sharp_edges`. hex3's stored revision predates the edge fact, so it needed a `rebuild` first (`measure_rebuilt.py`). Its totals reproduced ADR-415's 6,793 / 20,468 mm exactly. Every other project reproduced its README P2 exactly with the floor included.
- Results, with the floor → without (ADR-424):
  - hex3: 0.332 → **0.189**. The floor box is 500×400×3, 3,612 mm, all sharp. **The verdict flips from no to yes.**
  - hexapod-1: 0.655 → 0.508 (no).
  - hexapod-2: 0.088 → 0.134 (yes).
  - quadruped-2: 0.238 → 0.040 (yes).
  - biped-1: 0.068 → 0.103 (yes).
  - hexapod-3: 0.240 → 0.048 (yes).
  - hexapod-4: 0.114 → 0.220 (yes). Its filleted floor was 24,019 mm of smooth edge, nearly half its total.
- Suites: see Result.

## Result

- P2 is now defined, implemented and documented as printed parts only.
- **No A5 verdict changed.** No judged score can change, because the judge never sees P2.
- One proxy verdict changed: hex3's P2 now passes (0.189). hex3 remains the baseline. It still fails P1 (0.373) and the judged bar (2/21). The README now says plainly that P2 does not see hex3's T4 0, because its thin plates' long faces dominate the edge length. That makes the necessary-not-sufficient point.
- hexapod-4 is now the design closest to the P2 bar (0.220): its filleted floor had hidden its link edges.
- The quadruped's P2, which the critic worried about (0.238 against 0.25), is 0.040.
- Suites at this revision: `pixi run python -m pytest cli/tests` 1005 passed, 1 skipped; `pixi run test-engine` 2237 passed, 53 skipped. No engine or payload change, so no packaged gate was needed.

Concerns the next iteration must know:
- **An unrecorded, unscored quadruped attempt exists: `ot10-quadruped-3`.** It started 2026-09-28T02:52:54Z at `b20bb7a0`, with receipts in `~/cadex-projects/ot10-notes/quadruped-3/` (`started`, `pipeline.sh`, `turn.json`). The turn ended at about 03:41Z with ok=true, accepted revision `7de6eea6…` and digest `d929e47d…`. It ran concurrently with hexapod-4 (started 03:07Z), and no record mentions it. The charter says "publish every attempt", so this is an A5 attempt to score and publish, not ignore. Scoring it with its existing `pipeline.sh` is probably the next unit before (or instead of) a new `ot10-quadruped-4`. Its prompt and flags should be checked against the frozen ones in `turn.json`/`turn.stderr` first. Its CPU contention with hexapod-4 may also bear on hexapod-4's CPU-limit refusals (lucid-glacier-4889).
- **The restore opens were not strictly read-only.**
  - hex3's `script.json` was changed by my rebuild (a new attempt id for the same revision and digest). I restored it with `git checkout` and removed the three staging directories my opens created. hex3 is as committed. Its committed staging dir `attempt-1790461507510…` was already absent before this run.
  - In the six ot10 projects, the opens bumped `updated_at` and in places `latest_candidate.attempt_id` for the same revision. Those `script.json` files already carried uncommitted attempt changes from their scoring renders. Design content is unchanged everywhere.
  - Future re-measures should use a `/tmp` copy, as ADR-415 did.
- The unreconciled tail is 1 record after this one. Not fat yet.

Dispatch closed: 1 unit — P2 leaves out world geometry (ADR-424); all seven earlier probes re-scored, only hex3's P2 verdict flips (0.332→0.189), no A5 verdict changes; unscored ot10-quadruped-3 found

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 7ad19e78cd2efd8fc41aceec2aea992ddad85a29

## State Impact

- target: loyal-fountain-8709 — P2 exclusion settled (ADR-424): world geometry left out, all earlier probes re-scored (hex3 0.189, hexapod-1 0.508, hexapod-2 0.134, quadruped-2 0.040, biped-1 0.103, hexapod-3 0.048, hexapod-4 0.220); no A5 verdict changed; unscored completed attempt ot10-quadruped-3 (7de6eea6) found and must be published
- target: warm-basin-7003 — P2 now leaves out the fit's world geometry and reports left_out_as_environment (ADR-424); hex3's P2 re-measured 0.189 (within bar; 0.332 counted its floor), so hex3 fails P1 and not P2
