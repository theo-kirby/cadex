---
node_id: 23e34076-7542-5354-aff4-675889e4bd64
slug: stormy-snow-5452
title: 'F4: the frozen repair prompt completed on ot7-heron-repair-d — zero failing product checks static and swept, two of three defects resolved, the horn gap declared as clearance; repair-c void'
created_at: '2026-09-15T10:54:11+00:00'
parents:
- sunny-chart-3499
summary: ''
---
## What

F4's frozen repair prompt (`5d846901…`, 830 bytes, unchanged) reached the model twice more this iteration, on fresh validated copies of the seed, through `docs/probes/ot7/runner/run.py repair` under the ADR-356 collector, with no actor edit to any design.

- **`ot7-heron-repair-c`, void** (`docs/probes/ot7/retained/repair-void-c.json`). Dispatched at 06:07 UTC by this iteration's first attempt into a five-hour window already at 95 % (the stream's first `rate_limit_event` frame), the model made six reads in 79.9 s and was cut off mid-turn by the session limit at 101 %. Void under ADR-355, no slot spent, seed unchanged at 15 failures before and after. The first void call whose full stream (216,946 bytes, `facd8200…`) the runner retained itself.
- **`ot7-heron-repair-d`, completed** (`docs/probes/ot7/retained/repair-completed-d.json`). Dispatched at 10:24:40 UTC, four minutes after the reset, at 8 % utilization. The turn ended on its own after **1,461.9 s**: 39 model messages, 46 tool calls (35 inspect, 9 edit_script, 1 describe_api, 1 rebuild), six accepted revisions and three rejected edits (two malformed replacement calls, one MuJoCo refusal of a plane on a non-static body), final revision `252e73b5…`, script `27680dc0…`, transcript 1,384,115 bytes (`43d63ef8…`). Failing count by accepted revision: 15 → 2 → 1 → 2 → 1 → 0 → 0.

Committed: both receipts (10.3 KB and 10.1 KB), the closing report's headline, F4 row, a new iteration 48 section and the F4 evidence row, the retained index and the runner README, all written forward. The critic's fix-first (the missing record for `d516011c` with full CLI evidence) landed first as `sunny-chart-3499` (commit `fd547e8b`).

## Why

The critic's message: finish iteration 46's verification and record, then resume F4 on a fresh seed copy only when Claude is available. Claude was available (the window reset at 10:20 UTC; a one-word probe answered in 4 s), so the design turn was dispatched. The c dispatch was made by this iteration's first attempt, which the session limit then killed along with it; that call is void by the runner's own classification and is reported apart from the design's attempt. The critic named `ot7-heron-repair-c` as the retry project; since c was already spent as a void call, the same frozen prompt went to the next letter, `ot7-heron-repair-d`, as the charter's retry rule says. Advances F4 (`polished-forest-0215`): it now has a completed turn and a measured result.

## Method

1. Read the c project's `attempt.json` and captured stream; classified void by the collector (`usage_limit`, `cut_off_mid_turn: true`).
2. `rsync` the seed to `ot7-heron-repair-d` excluding `evidence/`, `agent.json` and the CLI lock; ran `seed_identity` + `validate_seed`: script `3339a178…`, revision `7e9eff5c…`, valid.
3. Probed Claude; dispatched the runner at 10:24:40 UTC in the background; watched its tool-call log and the frame-by-frame transcript; the runner exited 0 at 10:49:04 UTC.
4. Read the after-read the collector took from the published measurements (`clearance.json`, `fit.json`, `inventory.json`, `repair-assessment.json`), the accepted script diff against the seed (93 lines, 521 → 578), and the project's five new decision entries.
5. Built both compact receipts from `attempt.json` plus the captured stream with a throwaway script (result text truncated to 1,200 characters, per-message list dropped, to stay under 16 KB); ran `test_ot7_prompts.py`, `test_ot7_runner.py`, `test_retained_fit.py`: 59 passed.

## Result

**What is true now (measured by the collector, not by the agent's text).**

- Static fit on `252e73b5…`: **pass, 120 pairs, 0 failing** (seed: 105 pairs, 15 failing). Swept fit: **complete** at 5°, shoulder [−90°, +65°] in 32 samples (20.9 s), elbow [−100°, +25°] in 26 samples (10.5 s), solved-pose agreement true, maximum common volume 0 on every pair at every sample; the 19 pairs at 0 mm are all declared contacts.
- **Attachment assessment: fail.** `comp_horn_shoulder`/`comp_upper_arm` 0.19999999999999732 mm and `comp_horn_elbow`/`comp_forearm` 0.19999999999993 mm, the seed's exact values. The agent declared both pairs *clearance, minimum 0.05 mm*, so the product's checker passes them. The third ot6 defect is declared away, not closed.
- The floor plane is gone; a grounded 400 × 400 × 8 mm `bench` slab component with a declared base contact replaced it after MuJoCo refused the plane on a non-static body. The buried tab (248.2 mm³ per joint) is resolved by cheek pockets; screw overlaps by holes cut at shank diameter. `servo_shoulder` and `servo_elbow` are now `uncatalogued_sources` (spline bores cut into the catalog bodies); the other catalog counts are unchanged. Joint ranges narrowed from ±90°/±100° to the swept first contacts less 5°, mirrored into command limits; `sweep_step_degrees=5.0` declared.
- **Against F4's bar:** "accepts with zero failing fit checks" is met on the product's static and swept checks; "resolves all three defects" is not, two of three. The repair mode's single slot is spent (`status: exhausted`, `slots_spent: 1`); F4 has its measured result and no further frozen prompt.
- Turn economics: 80,451 output tokens (65,887 thinking), 5.45 M cache-read input tokens, longest silent gap 254 s, no message hit the 32,000-token cap; the five-hour window went from 8 % to 57 % in this one turn.

**Concerns and assumptions the next iteration must know.**

1. **Product finding.** The horn gap was never a failing row in anything the agent read: 0.2 mm clears the 0.1 mm default, and the seed declared no contact for it. F2's intent mechanism cannot flag an attachment nobody declared; only the collector's ot6-informed attachment assessment sees it. Whether that is a checker gap (a horn on a spline should imply contact with what it drives) is a product decision, not taken here.
2. **The design now carries a bench slab** as a component. F7's prompt says "no world geometry"; the F5–F7 assessment should read the inventory for environment solids, not only the world-geometry row.
3. **Window budget.** One completed repair turn used about half a five-hour window. A create prompt plus three continuations for F5, F6 or F7 will not fit in one window alongside the actor; expect to dispatch one design turn per window and to read the first `rate_limit_event` frame before dispatching, since an answering probe proved nothing on c.
4. **Assumption:** the retry rule sends the same prompt to the next letter after a void call; c was void, so d was used even though the critic named c. Both receipts are committed.
5. No smoke rollout ran on d: the repair mode does not request one, and F4's evidence list does not require it. `cadex smoke` on `ot7-heron-repair-d` is available as a small follow-on.
6. The unreconciled tail is now two records (`sunny-chart-3499`, this one).

Dispatch closed: 1 unit — F4's frozen repair prompt completed once on `ot7-heron-repair-d`: 1,461.9 s, 46 tool calls, six accepted revisions, zero failing product checks static and swept, two of three ot6 defects resolved and the horn gap declared as clearance rather than closed; `ot7-heron-repair-c` void; receipts and report written forward.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 676a99da1a9a89d3168b7b34785302c0255f9591

## State Impact

- target: polished-forest-0215 — F4 has its measured result: one completed turn on ot7-heron-repair-d (1,461.9 s, 46 tool calls, six accepted revisions, final revision 252e73b5) reached zero failing product checks static (0 of 120) and swept (complete at 5°, zero common volume), resolving the plane (replaced by a grounded bench slab) and the buried servo tab (cheek pockets) but declaring the 0.2 mm horn-to-link gap as clearance rather than closing it, so the collector's attachment assessment still fails; servo bodies uncatalogued after spline bores were cut; joint ranges narrowed to the sweep; the repair slot is spent; ot7-heron-repair-c was a fourth void call (session limit after six reads) with its stream retained
- target: mild-ledge-7157 — the agent half has its first completed design turn: from measurements alone the product agent repaired everything the fit report named and nothing it did not; F5–F7 remain untried; one repair turn consumed about half a five-hour window, so design turns are one per window and the first rate_limit_event frame, not a probe, says whether there is room
- target: first-snow-5587 — REPORT.md carries an iteration 48 section reading the three ot6 defects against the after-read, the F4 table and evidence rows are written forward, and the open list no longer includes the seeded repair
- target: wild-horizon-5461 — field evidence for F1: in a real turn the agent read the clearance summary and pairs first and after every accepted edit, and drove six accepted revisions from the published failing rows; a pair the report never flags (an undeclared attachment at 0.2 mm) is not acted on
