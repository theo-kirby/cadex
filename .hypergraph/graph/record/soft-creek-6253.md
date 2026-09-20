---
node_id: 43dc4f2e-4cd7-5b2b-aad3-7ac053193ffa
slug: soft-creek-6253
title: 'A deliberate hold: the Fable gate stays shut, no probe spent and all eight F6/F7 slots unspent'
created_at: '2026-09-16T16:37:17+00:00'
parents:
- tidy-nest-3309
summary: ''
---
## What

Nothing changed. This iteration is a deliberate hold: no code, no docs, no
receipt, no probe, and no frozen prompt. F6 (`narrow-dune-9454`) and F7
(`rapid-grove-9687`) remain blocked on the organisation-level Fable refusal
measured one minute before this dispatch opened, and all eight of their
create/continuation slots remain unspent.

## Why

The critic's message for this iteration was explicit on all three points and
this unit follows it exactly:

- **F6 is the next design unit, but do not re-probe before the recorded
  2026-09-18 14:00 UTC reset.** `tidy-nest-3309` took that reading at 16:39 UTC
  today — probe refused in 2.3 s, HTTP 429 "You've reached your Fable limit",
  five-hour window at 12 %, seven-day at 52 % — and this dispatch opened at
  16:36 UTC, inside the same minute. A second probe would measure the same
  refusal and tell the run nothing it does not already carry.
- **Preserve all F6/F7 slots.** None was touched; nothing was dispatched.
- **Otherwise make no change, and do not manufacture additional wording work
  or follow the stale plan into out-of-scope work.** The charter's question
  policy reaches the same place from the other direction: when the harness is
  limited, take an unblocked tooling, test or reconcile unit, and "when none
  is left, make no change and let the loop wait for the reset." The last three
  iterations each took a real but small CLI-wording unit (ADR-366, ADR-367,
  ADR-368); the critic has now judged that seam worked out, and the remaining
  open frontier under this charter is F6, F7 and F10, all of which are gated
  on capacity or on F6/F7 finishing. The plan's short-term ranks 1 and 2
  (swept clearance over rollout poses, the section eye's plane choice) are
  pre-ot7 bets outside this charter's frontier, so taking one would be the
  out-of-scope move the critic named.

The reconcile thresholds are not met and reconcile is forbidden in a work
iteration in any case: the tail stood at two records
(`pale-garden-4669`, `tidy-nest-3309`) when this dispatch opened.

## Method

Read-only, five commands:

- `git status --porcelain` — working tree clean at `4fd29536`, nothing
  uncommitted from the previous iteration.
- Read `tidy-nest-3309` in full for the gate reading, its timestamp and the
  slot accounting.
- `date -u` — 2026-09-16 16:36 UTC, one minute after that reading, and
  roughly 45 hours before the recorded reset.
- Confirmed the gate is self-enforcing rather than resting on this hold:
  `docs/probes/ot7/runner/run.py:509-530` reads the window *before* the slot
  is persisted and the turn directory is created, and on `dispatched: false`
  marks the receipt `paused` with an ADR-355/ADR-358 `deferred` block and
  breaks — the prompt is never sent and no slot moves. So even an accidental
  dispatch while refused could not spend an F6 or F7 slot.
- No probe was run, no test suite was run (nothing changed to test), and no
  file was written outside this record.

## Result

The run is holding, not stalled, and the hold is deliberate and recorded
rather than silent. True now:

- F6 and F7 are blocked solely on provider capacity. The binding limit is the
  organisation-level Fable one, not the five-hour window, which read 12 %.
  Every create and continuation slot for both designs is unspent — eight in
  total — so neither design is exhausted and no verdict or record may say the
  run has no authorised experiment remaining.
- F1–F5, F8 and F9 have their evidence; F10 is the run's last unit and cannot
  be written while F6 and F7 are unattempted.
- Nothing is broken. The tree is clean, no suite was left red, and the
  previous iteration's `cli/tests` run (783 passed, 1 skipped) stands as the
  last measurement.

For the next iteration:

- The tail is now **three** unreconciled records (`pale-garden-4669`,
  `tidy-nest-3309`, this one), so the charter's three-record threshold is
  met and the critic's stated condition for a reconcile pass is reached.
  Reconcile is the next unit unless the critic names another.
- Do not probe before 2026-09-18 14:00 UTC. The reset is roughly 45 hours out
  and past this run's likely horizon; if the loop is still running then, one
  probe decides F6, and a refusal means another hold, not an exhaustion claim.
- Assumption carried: the recorded reset time is the provider's own
  `resetsAt`, taken from the refused probe's frame, and is treated as
  authoritative without re-measurement. If capacity returns earlier by some
  other signal — the operator says so, or an unrelated Fable call succeeds —
  that is grounds to probe sooner; a guess is not.

No new dependency. No deviation from the critic's message.

Dispatch closed: 1 unit — a deliberate no-change hold while the Fable gate is shut; no probe, no prompt, all eight F6/F7 slots unspent, and the reconcile threshold now reached.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 4fd29536a6d4e387f8811cc4852f90d4ebc1a6ca

## State Impact

none: Nothing changed: no code, docs, receipt, probe or prompt. The gate reading, slot accounting and frontier are exactly as tidy-nest-3309 left them one minute earlier; re-declaring them would be bookkeeping without a new measurement.
