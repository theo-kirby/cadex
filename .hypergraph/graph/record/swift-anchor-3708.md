---
node_id: b9706db3-544f-5926-b897-32f448d93f0e
slug: swift-anchor-3708
title: 'The owner-directed hold held: no change, and the handoff for the next model'
created_at: '2026-09-17T02:36:08+00:00'
parents:
- fair-badger-6443
summary: ''
---
## What

No change to the repository. This iteration is the owner-directed hold, taken
deliberately, plus the handoff the critic asked for. No product code, no test,
no doc, no receipt, no provider probe, no run-control action.

F6's four slots and F7's four remain unspent. No frozen prompt was sent.

## Why

The owner directive of 2026-09-17, recorded verbatim in `fair-badger-6443`,
takes precedence over instructions to find more tooling work. Its items 1 and
2 are finished: the in-flight unit landed (ADR-380, `c41191f5`), the corrective
impacts were folded and the views regenerated (`e0446465`, tail now empty), and
the directive itself is recorded with its State Impact. That leaves item 3
verbatim: *"Then wait for product-agent access. Do not start more tooling,
checker, test, documentation or bookkeeping units to fill the wait. Do not write
repeated waiting records or repeatedly probe the same organisation-level
refusal. An unchanged refusal is not new evidence. Return a no-change stuck
result and let the runner back off."*

The critic's message asks two things that pull apart. Its body says to pick a
charter criterion and do the smallest thing that moves it, and that the current
bet is banned; its last paragraph says to maintain the owner-directed hold and
make no changes. I followed the last paragraph, because the hold is the owner's
and the charter says unattended roles do not overrule it. **So I did not do what
the critic's body asked, and this is that deviation stated plainly:** I started
no unit on any criterion, and I wrote no bet, because every remaining criterion
resolves to either "already has its evidence" or "needs a product-agent turn
the hold forbids dispatching".

One line each, as the critic asked:

- **F1** — not blocked; evidence complete pending the owner's checkbox
  (`wild-horizon-5461`, ADR-346). Nothing to move.
- **F2** — not blocked; evidence complete, ADR-379's false fifth check
  withdrawn by ADR-380 (`winter-key-1482`). Nothing to move.
- **F3** — not blocked; bounded exact-solid sweeps published (ADR-349, ADR-351,
  `curious-quill-9036`). Nothing to move.
- **F4** — exhausted, not blocked: repair prompt and all three continuations
  reached the model on `ot7-heron-repair-d` (`polished-forest-0215`). A measured
  outcome; the charter forbids repeating it to fill the run.
- **F5** — exhausted on the same terms on `ot7-heron-c` (`stormy-aspen-5433`).
- **F6** — blocked: `claude-fable-5` refused at the organisation level on this
  account, so the create prompt cannot reach the model (`narrow-dune-9454`).
- **F7** — blocked behind F6 by the identical cause (`rapid-grove-9687`).
- **F8** — not blocked; `cadex smoke` implemented and fixture-verified
  (ADR-352, `honest-ivy-8824`). Nothing to move.
- **F9** — not blocked; the regression assessment is written and says only what
  it computes (`eager-summit-3153`).
- **F10** — open but not startable: the directive's item 4 forbids claiming
  done while F6 and F7 are unattempted, and F10 is defined as the run's last
  unit.

That is the whole frontier, and it is why fifty-two iterations of tooling did
not move a node: the four criteria that need a model turn are the only ones
left, and the model has been unreachable for all of them.

## Method

1. Read the owner directive in `fair-badger-6443` and confirmed items 1 and 2
   are discharged: `git log` shows ADR-380 at `c41191f5` and the reconcile at
   `e0446465`; STATE.md reports zero unreconciled records at
   2026-09-17T00:35:33Z.
2. Read `jolly-current-9257`, the previous hold record, specifically so as not
   to repeat it — this record adds the per-criterion reading and the handoff the
   critic asked for, and takes no probe.
3. Read the frontier lines for F1–F10 out of STATE.md rather than re-deriving
   them.
4. Confirmed the working tree clean at `e0446465` and left it so.

No suite was run: nothing changed for one to cover. No provider call of any
kind was made.

## Result

**The repository is byte-identical to `e0446465` apart from this record.**
F6 and F7 are blocked, all eight of their slots unspent; F4 and F5 hold their
measured exhausted outcomes; F1–F3, F8 and F9 have their evidence and await the
owner's checkboxes; F10 is the last unit and is not startable yet.

What the next iteration — a different model — must know:

- **The hold is the owner's, not the critic's, and it is still on.** Do not
  start tooling, checker, test, doc or bookkeeping units to fill the wait. Do
  not probe the refusal again: it is an organisation-level setting
  (`overageDisabledReason: org_level_disabled`), not a rolling window, so
  re-reading it produces no new evidence. Return a no-change stuck result and
  let the runner back off — `stop.max_stuck` is 25 and backoff is what the
  owner asked the loop to spend.
- **What was tried, across the last fifty-two iterations:** every unblocked
  tooling unit the charter permitted — the fit summary and clearance scope
  (F1), declared fit intent and its checks (F2), the swept check (F3), the
  smoke command (F8), the regression assessment (F9), and then a tail of
  corrective ADRs (376, 377, 378, 379→380, 381, 382) tightening checks nobody
  could run against a new design. None of it could move a node, because the
  only open nodes need a product-agent turn.
- **What to try next, and the only thing worth trying:** when, and only when,
  there is concrete evidence of restored access to `claude-fable-5` — an owner
  account refresh or a provider reset, followed by one successful availability
  check — F6 is the unit, and the command is known and verified:
  `docs/probes/ot7/runner/run.py robin "$PROJECTS/ot7-robin-b" --model
  claude-fable-5`, then `resume` for one continuation per window, then F7 on
  the frozen biped prompt. Actor availability does not establish it; this actor
  is running on Opus while the product agent's model is refused.
- No new dependency, no red tree, nothing broken and left silent.

Dispatch closed: 1 unit — the owner-directed hold held: no change, no probe, the
per-criterion reading of why the frontier cannot move, and the handoff for the
next model.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: e04464653dcb8ed774efa19577a32a47f8668583

## State Impact

none: The owner directive's items 1 and 2 are discharged and item 3 is a no-change hold; nothing in the repository changed, so no state node moves.
