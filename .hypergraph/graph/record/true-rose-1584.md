---
node_id: ae38dc15-e08c-5870-945f-2a7df8f713fe
slug: true-rose-1584
title: 'ot10: hexapod attempt 6 judged 15/21, misses A5 on the sweep pair budget (0/12 at 87 components); ADR-425 held at 12/12 with 63'
created_at: '2026-09-28T08:57:11+00:00'
parents:
- swift-trail-3183
summary: ''
---
## What

Ran and published A5 hexapod attempt 6 (`ot10-hexapod-6`): the frozen cold hexapod prompt, one design-only turn on the ADR-425 engine. Judged blind **15/21** (calls 14, 15, 15; medians T1 2, T2 3, T3 2, T4 2, T5 2, T6 2, T7 2). P1 0.009, P2 0.198, P3 3, and the electronics are carried. It **misses the A5 bar**: the accepted revision's swept fit is **incomplete, 0 of 12 joints, all `pair budget exceeded`**. The static pass also reports six feet resting on `c_floor` as `below clearance`. Committed: the README section, six candidate PNGs (≤158 KB each), the score file and a contract test (`4f7390c3`).

## Why

The critic named this unit: hexapod attempt 6 on a new `ot10-hexapod-6`, with the frozen prompt, the frozen flags, `claude-opus-5-5` and `CADEX_EFFORT=medium`, on the rebuilt engine. Then the A2 render and the blind score under the frozen procedure, published pass or miss. If the sweep fell short again, the critic said to diagnose it before any change, and not to raise the budget. It serves A5 (`loyal-fountain-8709`), because the hexapod is the one body plan with no passing design. Done as asked, with no deviation. The sweep did fall short again, but on its pair budget rather than its time budget. It is diagnosed below, and nothing was changed.

## Method

1. **Launch.**
   - Command: `CADEX_EFFORT=medium ./cadex --project ~/cadex-projects/ot10-hexapod-6 --model claude-opus-5-5 -p <contract.json a5.prompts.hexapod> --json`, detached with `setsid`.
   - Timing: started 08:07:15Z at `feb2190b` (engine `source: dev-tree`, which carries `_boundary_distance`). It ended on its own at 08:39:33Z with `ok: true`.
   - `agent.json`: model `claude-opus-5-5`, one session `eb4ad1fd…`, no continuation.
   - Receipts are in `~/cadex-projects/ot10-notes/hexapod-6/`: `argv`, `started`, `ended`, `revision`, `turn.json` and `turn.stderr`.
2. **Measurement.**
   - Copied the project with `cp -a` to `/tmp/ot10-hexapod-6`. Removed a stale lock whose PID had exited.
   - Ran the notes' `pipeline.sh`, which is attempt 5's with the name changed: `cadex render --json`, then `look_views.py`, then `judge.py` (3 calls, `claude-opus-5-5`, effort high, rubric sha `1c81caa2…`).
   - Read the proxies from `review/render/summary.json`, and the fit from the turn's `--json` envelope.
3. **Refusals.** `refusals.py` on the session jsonl.
4. **Diagnosis.**
   - Read the one-line fit summaries in `turn.stderr` for every build.
   - Read the budget check in `cadex_assembly_worker.py`: `_SWEEP_MAX_PAIRS = 2000`, and `if len(baseline) > _SWEEP_MAX_PAIRS: raise ValueError("pair budget exceeded")` before any pose.
5. **Contract test.** `test_a5_hexapod_attempt_6_is_published_with_its_score` pins:
   - the score file: rubric sha, model, total 15 and 3 calls;
   - each candidate's sha256 and the 300 KB cap;
   - the median row and the README verdict line.
   It fails with the score file removed and passes with it: 18 passed.

## Result

- **What is true now.** The hexapod still has no passing design: 6 attempts, judged 13, 14, 13, 12, 16 and 15. Attempt 6 clears every judged and proxy item. It fails only on fit coverage.
- **ADR-425 held on a fresh turn.** With the design at 63 components and 1,953 pairs, the sweep came back complete and passing, **12/12 at 5° steps**. No runtime-budget row appears anywhere in the turn; attempt 5 needed 80° steps and still stopped at 10/12.
- **What bound this time.** The agent added 24 M2×8 servo-tab screws, taking the design to 87 components and 3,741 pairs, over the 2,000-pair budget. It put them behind a `fasteners` parameter and checked the sweep with `fasteners=0`. Then it published `fasteners=1` as the default, and said in its reply that the default's motion check is incomplete. The bar counts the accepted revision, so the `fasteners=0` sweep does not stand in for it.
- **Diagnosis, from names and code, not measured.**
  - The budget counts every pair in the assembly. A rigid pair's row is copied from the solved pose unchanged, and only pairs with one side in the moving subtree are measured.
  - A hip moves at most 10 of 87 components, so at most 770 moving pairs. A knee moves about 4, so about 332. Both are far under 2,000.
  - **Next unit:** measure each joint's moving-pair count on the accepted request, read-only on `/tmp/ot10-hexapod-6`. If the count confirms this, make the budget count what the sweep measures, with a regression test that fails on the old source and an ADR. Do not raise 2,000.
- **Second finding.** The six ball feet rest exactly on `c_floor` (0.0 mm, no common volume). The static pass reports each as `below clearance`, while the sweep treats contacts with world geometry as advisory (ADR-420). This is the first design that stands on the floor at the solved pose. I record it as a static-fit failure as the engine reports it. Whether the static pass should also apply ADR-420 is a decision for its own unit, not taken here.
- **Judged gaps against attempt 5:**
  - T3 fell from 3 to 2: the hip rings and the knee caps differ, and bare shaft stubs show.
  - T4, T5 and T6 are unchanged at 2.
  - For T7, all three calls named a high camera and a faint contact shadow. That is a renderer property shared by every design, a renderer unit of its own, alongside attempt 4's hero-camera concern.
- **Refusals.** 8 refused calls: 0 CPU-limit, and none of the four A4 classes. The build reply was again too large for the agent to read; this is the third time in the run.
- **Render timing.** 1 min 25 s: 38.5 s acquisition, 7.6 s drawing, 2.4 s hero, 141,438 drawn triangles.
- **Suites.** `pytest cli/tests`: 1,008 passed, 1 skipped (11 min 29 s); `test_ot10_contract.py`: 18 passed. No engine code changed, so `test-engine` was not rerun.
- **Tail.** 2 unreconciled records once this one lands.
- **No new dependency.**

Dispatch closed: 1 unit — published ot10-hexapod-6 (frozen prompt, flags, model, effort, on the ADR-425 engine): judged 15/21, P1 0.009, P2 0.198, P3 3. It misses A5 because the accepted fasteners=1 revision's sweep is 0/12 at the 2,000-pair budget (87 components, 3,741 pairs; 12/12 at 5° with 63 components). The six floor-contact feet also read below clearance in the static pass. Diagnosed, and nothing changed.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 4f7390c3020a77034d7f08c478dea6e2cbae4ed9

## State Impact

- target: loyal-fountain-8709 — ot10-hexapod-6 (frozen prompt/argv/model/effort, started feb2190b, rev 3cb2b1d0) judged 15/21 (no trait 0), P1 0.009, P2 0.198, P3 3, electronics carried, but the accepted fasteners=1 revision's swept fit is incomplete 0/12 (pair budget exceeded: 87 components, 3,741 pairs > _SWEEP_MAX_PAIRS 2,000, which counts rigid pairs the sweep never moves) and six feet resting on c_floor read below clearance in the static pass; with 63 components the sweep passed 12/12 at 5 deg (ADR-425 confirmed). Hexapod still has no passing design (6 attempts); next is measuring per-joint moving pairs before any budget-accounting change
