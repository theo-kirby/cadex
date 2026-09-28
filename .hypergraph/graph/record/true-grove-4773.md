---
node_id: b91cf9d3-3af4-5af6-9d03-ec8eaf869e21
slug: true-grove-4773
title: 'ot10: A4 refusal census over all 14 ot10 transcripts — 0 of 183 in the four classes, pinned and published'
created_at: '2026-09-28T17:29:53+00:00'
parents:
- mild-lily-4405
summary: ''
---
## What

A mechanical census of A4's four refusal classes across **every** ot10 product-agent transcript, with a contract test that pins it. New `docs/probes/ot10/runner/refusals.py` (stdlib only) classifies each `is_error` tool result from the engine's own refusal sentence or `failure_code`. `docs/probes/ot10/refusals.json` holds the census, and a new README section "A4: the refusal census, every ot10 transcript" publishes the table. Six new tests in `cli/tests/test_ot10_contract.py` cover it.

## Why

The critic named this unit. `odd-tree-6681` had counts only for hexapods 1–4 and one quadruped. The critic asked for all four classes counted across every counted A5 transcript (biped-1, quadruped-3, hexapod-10) plus the failed attempts, done mechanically, pinned by a contract test and published. The critic also asked for C1 (full suites at head and REPORT.md). That is a second unit, so under the one-unit rule it is left for the next iteration. I did not do it here.

## Method

- Found every transcript through each project's `agent.json` `session_id`. The two aborted turns (hexapod-9, quadruped-1) have no `agent.json`, so their transcripts were taken from their per-project session directory. Each has exactly one `.jsonl`.
- Status per project follows the README. The **counted** designs are biped-1, hexapod-10 and quadruped-3. The **failed attempts** are hexapods 1–8 and quadruped-2. The **not attempts** are hexapod-9 and quadruped-1, both harness stops.
- Each class is anchored on the engine's exact sentence, in the old hex2/hex3 wording and the ADR-416 wording, instead of the notes counter's `horn|style` keyword. That keyword had false-matched the output name `horn` on hexapod-2.
- The joint class also counts its component twin ("Every component listed in api.assembly…"), since hex2 met that variant. This makes the check stricter.
- Some long refusals reach the transcript with their middle truncated, which leaves invalid JSON. For those, `error` and `failure_code` are read by pattern.
- Every refusal left in `other` was read by hand. None is an A4 class.
- The committed file keeps each transcript's sha256, its counts and a 200-character error excerpt per refusal. It holds no machine paths (tested), and no transcript was committed.
- The tests:
  - classify ten real refusal texts, including two look-alikes that must not match;
  - pin per-project status, refused count and CPU-limit count;
  - re-derive the counts from the committed calls;
  - hold the README table equal to `table(refusals.json)`;
  - parse a synthetic truncated body;
  - re-run the census against the local transcripts when their sha256 matches. On this machine it ran on all 14; it skips elsewhere.

## Result

- **0 of the 4 A4 classes in all 14 ot10 transcripts: 0 of 183 refused calls.** That includes the three counted A5 designs (7, 15 and 10 refusals) and all nine failed attempts.
- What remains outside A4: CPU limit 44, sandbox 32, kernel 29, JSON pointer 22, `Cannot retire` a linked output 15, edit replacement 10, reset variation 7, outputs dropped 3, other 21.
- `pytest cli/tests/test_ot10_contract.py`: 35 passed, and the local-transcript test ran rather than skipping.
- `pytest cli/tests` at this change: 1055 passed, 1 skipped (735 s). The engine suite was not re-run: no engine file changed. C1 still owes both suites at the final revision.
- A4's evidence is now complete for the charter's "A5's transcripts show none of these refusals recurring". The owner holds the checkbox.
- The next unit is C1: both full suites at head, then `docs/probes/ot10/REPORT.md`.
- No new dependency. The tail is 1 unreconciled node after this one.

Dispatch closed: 1 unit — A4 refusal census over all 14 ot10 transcripts, 0/183 in the four classes, pinned by contract tests and published in docs/probes/ot10

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 4284a560d98d15187682544348c3da2f67f2d1b6

## State Impact

- target: odd-tree-6681 — mechanical census (docs/probes/ot10/runner/refusals.py, refusals.json, commit 4284a560) over all 14 ot10 transcripts incl. counted biped-1, hexapod-10, quadruped-3, nine failed attempts and two aborted turns: 0 of 183 refused calls in the four A4 classes; contract tests pin counts and README table; A4 evidence complete pending owner tick
