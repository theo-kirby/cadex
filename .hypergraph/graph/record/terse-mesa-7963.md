---
node_id: 8f9fa5dd-70e5-597c-a67f-4017177bd415
slug: terse-mesa-7963
title: 'ADR-357: the repair prompt is F4''s first prompt, not its only one — runner resumes continuations without replay; REPORT.md slot totals corrected; F4 open with three continuations; no dispatch at 74 % of the window'
created_at: '2026-09-15T11:14:33+00:00'
parents:
- stormy-snow-5452
summary: ''
---
## What

The fix-first the critic asked for, as one tooling unit (ADR-357), with no design turn and no prompt byte changed:

- **The runner's repair schedule is four prompts.** `frozen('repair')` in `docs/probes/ot7/runner/run.py` is `repair.prompt.txt` followed by `continue-1`, `continue-2` and `continue-3`, the same three every design gets; the first prompt of any schedule counts no continuation, so a completed repair row reads `continuations_used: 0`. The prompt digests are unchanged and still verified before every dispatch.
- **One turn per window, and `resume`.** `run.py repair` dispatches the repair prompt alone and pauses (`status: paused`, a `remaining` block naming the next prompt); `run.py resume PROJECT` dispatches exactly the next continuation, with `--resume` into the agent's own session, without replaying anything earlier; `--turns N` bounds either command, a design attempt still dispatches all four by default, and `run.py remaining PROJECT` only reads. Every row now snapshots the design identity after its turn (`accepted_after`); `resume` refuses a project whose design differs from that snapshot, one closed by a void, interrupted or failed call (those still retry on a fresh copy), an exhausted one, and one with no attempt. A receipt written under the old rule (`exhausted` with fewer than four completed rows) resumes from its rows and gains a `ruling` field.
- **The record corrected forward.** `REPORT.md` (headline, slot table, the F4 evidence row, the "what remains" order, a new iteration 49 section), `runner/README.md` (a new resume section and the iteration 48 wording), `prompts/README.md` (the limits table: F4 has 3 continuations after the repair prompt), `retained/README.md`, and `retained/repair-completed-d.json` (a `ruling` field, as the iteration 44 receipt carries decision #44; its historical `status`, `slots_spent` and `continuations_used` kept as written). The completed experiment on `ot7-heron-repair-d` and its receipts are preserved.
- **Fixtures** in `cli/tests/test_ot7_runner.py`: a repair that pauses with three continuations and resumes through all three without replaying the repair prompt; the legacy `exhausted` receipt resuming with its ruling; the three refusals; a create paused per window and resumed to its smoke; a continuation child passing `--resume`. `test_ot7_prompts.py` pins the corrected limits row. On the real project, `run.py remaining ~/cadex-projects/ot7-heron-repair-d` reads: 1 completed, 0 continuations used, 3 unspent, next `continue-1.prompt.txt`, not closed.

## Why

The critic rejected iteration 48's "F4 exhausted" claim: the amended charter's exhaustion policy counts a design exhausted only after its create or repair prompt *and all three continuations* reached the model, and REPORT.md's slot table said "none" for F4 in the same column where every other design has "3 of 3". This unit does what the message asked, in its order: fix the contradictory totals in REPORT.md and the runner README, supersede `stormy-snow-5452`'s exhausted-F4 impact (through this record's impact on `polished-forest-0215`; the record graph is append-only, so the old node is not edited), keep F4 open, preserve the completed experiment, do not repeat the repair prompt, and pin in `run.py` that the slots remain after one completed repair and can resume without replaying it.

**What it did not do, and why.** The message's last step, "then use the frozen continuations only when Claude is available", was not taken this iteration. At 10:59 UTC the probe's first `rate_limit_event` frame showed the five-hour window at 74 % (reset 15:20 UTC); the one completed turn on d moved a window from 8 % to 57 %, so a continuation dispatched now would be cut off mid-turn and void. The charter says never to spend a frozen prompt while the harness is limited, so the next unit, after the reset, is `run.py resume ~/cadex-projects/ot7-heron-repair-d` with `continue-1`. Advances F4 (`polished-forest-0215`) by restoring its three continuations and the tool that spends them.

## Method

1. Read the critic's message, the charter's exhaustion policy, REPORT.md, the runner README, `run.py`, the d project's `attempt.json` and the retained receipts; probed Claude with a one-word turn and read the first `rate_limit_event` frame (74 %).
2. Rewrote `run()` around a shared `dispatch()` loop with `remaining()` computed from the rows, added `resume()`, `design_identity()`, `evidence_dir()`, `--turns`, and the `resume`/`remaining` subcommands; the first prompt of any schedule no longer counts as a continuation.
3. Updated the one assertion the rule change broke (`continuations_used` 1 → 0 on a completed repair) and added the fixtures above; corrected the manifest's limits row and its test.
4. Applied the forward corrections to REPORT.md, both READMEs and the retained receipt (rewritten in its original one-space format so the diff is the added field only); appended ADR-357.
5. Ran `cli/tests/test_ot7_runner.py` and `test_ot7_prompts.py` (63 passed), then the full CLI suite; scanned the diff for machine paths (none).

## Result

**What is true now.** F4 stands at one completed turn: its repair prompt is spent, zero continuations are used and three are unspent, and the next turn is `continue-1.prompt.txt` resumed on `ot7-heron-repair-d`, into the agent's own session, one turn per window. The runner enforces that schedule and refuses to replay, to resume a closed project, or to resume a design something other than a product-agent turn changed. The iteration 48 measured result stands as recorded: zero failing product checks static and swept, two of three ot6 defects resolved, the horn gap declared as clearance. The d receipt's `status: exhausted` is historical output marked by its `ruling`. F5–F7 gain per-window dispatch for free (`--turns 1`, then `resume`), which iteration 48's window measurement said they need.

**Concerns and assumptions.**

1. **The dispatch decision is the operator's, not the runner's.** `resume` does not read the window; the actor must read the first `rate_limit_event` frame before each continuation. One turn of the observed size needs roughly half a window, so dispatch only when the frame shows under about 45 %.
2. **The continuation resumes the agent's session on d** (`agent.json`), so the model carries its own context from the repair turn, which is what a continuation means; the frozen continuation text names nothing.
3. **The prompt manifest README changed**, in its limits table and one description cell, not in any prompt; `frozen()` verifies every digest against the unchanged hash column and passes. If the "changing any byte of any file in this directory starts a new attempt" sentence is read to cover the manifest itself, that reading is wrong for this change and this record says so.
4. `stormy-snow-5452` is superseded by impact, not edited; the reconcile pass should fold this record's `polished-forest-0215` delta over it.
5. The unreconciled tail is three records after this one (`sunny-chart-3499`, `stormy-snow-5452`, this), so a reconcile pass is due by the charter's rule.
6. Full CLI suite: 745 passed, 1 skipped in 524 s (`pixi run python -m pytest cli/tests`); the runner and prompt suites 63 passed.

Dispatch closed: 1 unit — ADR-357: the repair prompt is F4's first prompt, not its only one; the runner carries the four-prompt repair schedule, pauses one turn per window and resumes the next continuation without replay, fixtures pin it, REPORT.md and the receipts are corrected forward, F4 stays open with three continuations, and no continuation was dispatched because the window stood at 74 %.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 78ad33cef33fdf138c404f399f0484258aefe089

## State Impact

- target: polished-forest-0215 — supersedes stormy-snow-5452's 'the repair slot is spent' clause (ADR-357): F4 stands at one completed turn on ot7-heron-repair-d with its repair prompt spent, zero continuations used and three unspent; next is continue-1.prompt.txt resumed on that project into the agent's own session, one turn per window, only when the first rate_limit_event frame shows room (about half a window per turn); the iteration 48 measured result stands unchanged; no continuation was dispatched in iteration 49 because the window stood at 74 % with the reset at 15:20 UTC
- target: mild-ledge-7157 — the ot7 runner carries a four-prompt repair schedule, pauses after one turn (status paused, a remaining block), resumes exactly the next continuation with run.py resume without replaying earlier turns, bounds any invocation with --turns, snapshots the design identity after every turn and refuses to resume a design changed by anything but a product-agent turn; F5–F7 can dispatch their create and each continuation one per window; fixtures pin it (ADR-357)
- target: first-snow-5587 — REPORT.md's contradictory F4 slot totals are corrected forward: the slot table, headline, F4 evidence row and remaining-work order say three continuations unspent, and an iteration 49 section records the correction; the d receipt carries a ruling field with its historical values kept
