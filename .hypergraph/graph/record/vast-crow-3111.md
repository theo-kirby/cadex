---
node_id: 61715432-ad89-59a7-b283-07a55f81e585
slug: vast-crow-3111
title: 'A total hold: the Fable gate is shut for ~45 more hours and the loop is firing every few minutes'
created_at: '2026-09-16T16:43:52+00:00'
parents:
- soft-creek-6253
summary: ''
---
## What

Nothing in the repository changed. No code, no docs, no receipt, no window
probe, no frozen prompt. F6 (`narrow-dune-9454`) and F7 (`rapid-grove-9687`)
stay blocked on the organisation-level Fable refusal, and all eight of their
create/continuation slots stay unspent.

The one thing this record adds that `soft-creek-6253` does not is a measured
statement about the loop's own cadence against the gate — see `## Result`.

## Why

The critic's message selected the unit for this iteration and left no
ambiguity: "F6 is next: after the recorded 2026-09-18 14:00 UTC reset, or
concrete evidence of earlier restored capacity, run one window probe and
dispatch the frozen balancer create prompt only if available. Until then,
make no change: no waiting record, repeated audit, wording cleanup or
additional reconcile without new impacts. Preserve all eight F6/F7 slots,
leave the stale out-of-scope plan alone, and do not stop or restart the run."

This dispatch opened at 2026-09-16 16:41 UTC, four minutes after the previous
one closed and about **45 hours** before the recorded reset. No signal of
earlier restored capacity exists: the only channel that could carry one is a
probe, and probing is what the critic gated. So the answer to "is there an
unblocked unit" is the same as it was four minutes ago, and the charter's
question policy lands in the same place: "when none is left, make no change
and let the loop wait for the reset."

**Deviation, stated plainly.** The critic asked for *no waiting record*. This
record exists anyway, because the dispatch contract above it is explicit that
recording is mandatory and that an iteration with no record node is counted as
lost work. The compromise is the smallest footprint that satisfies both: the
hold is total — the working tree is untouched — and the only commit this
iteration produces is the record itself, declared with no state impact so the
reconcile pass has nothing to fold. If the critic wants the record suppressed
too, that is a change to the loop's dispatch contract, not something an actor
can decide by omission.

I did not take any of the four things the critic named as churn, and I did
not take the plan's short-term ranks 1 and 2 (swept clearance over rollout
poses; the section eye's plane choice), which are pre-ot7 bets outside this
charter's frontier.

## Method

Read-only, six commands, no writes outside this record:

- `date -u` — 2026-09-16 16:41 UTC.
- `git status --porcelain` — clean at `5ef69db0`, the reconcile commit.
- `git log --oneline -20` — confirmed the last three units were the ADR-366 /
  ADR-367 / ADR-368 wording seam the critic has now closed, followed by the
  hold and the reconcile.
- Read `docs/probes/ot7/attempts/f6-window-refusal.json` in full. The binding
  limit is `seven_day_overage_included` at 100 % with
  `overageDisabledReason: org_level_disabled`; `five_hour` read 1 % and
  `seven_day` 51 %. Its `second_probe` block is the reason ADR-364 exists: an
  `allowed` frame at 2 % that the provider refused anyway.
- `grep -rn "2026-09-18" docs/ .hypergraph/graph/record` — the reset time is
  provenanced, not assumed: `pale-garden-4669` records it as the rejected
  window's own `resets_at` (1789740000 → 2026-09-18 14:00 UTC), so no
  re-measurement is needed to trust it.
- Read `soft-creek-6253` in full, to avoid restating it.

No probe, no suite (nothing changed to test), no dispatch.

## Result

True now, unchanged from `soft-creek-6253`: F6 and F7 are blocked solely on
provider capacity; all eight slots are unspent, so neither design is exhausted
and no verdict or record may claim the run has no authorised experiment
remaining; F1–F5, F8 and F9 have their evidence; F10 cannot be written while
F6 and F7 are unattempted; nothing is broken and the tree is clean. The tail
is one record deep after this one — well under the reconcile threshold.

**The new fact, and the one thing the next iteration and the owner should
weigh.** The last three dispatches opened at 16:36, 16:39-ish and 16:41 UTC:
this loop is firing roughly every four to five minutes. The gate is about 45
hours out. At that cadence the run faces on the order of **five hundred**
dispatches before a probe is even permitted, and under the critic's ruling the
only compliant action in each of them is this same hold. That is not a reason
to manufacture work — the critic is right that the wording seam was worked out
and that every further product change widens the gap between F5's conditions
and F6/F7's, which is exactly what REPORT.md's product-version comparison has
to account for. It is a reason to say out loud that the *loop*, not the run,
is now the thing spending: the run is correctly parked, and only the owner or
the runner's configured stop rules can change that. No role here may stop or
restart the run, and this record does not.

Carried assumptions, both inherited and neither re-measured this iteration:
the provider's own `resets_at` is authoritative, and a probe before it would
return the same refusal. Grounds to probe earlier are an operator statement or
an unrelated Fable call succeeding — not a guess and not elapsed time.

No new dependency.

Dispatch closed: 1 unit — a total hold with the Fable gate shut, recorded against the critic's "no waiting record" because the dispatch contract makes a record mandatory; no probe, no prompt, all eight F6/F7 slots unspent, and the loop's ~5-minute cadence against a ~45-hour gate named for the owner.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 5ef69db095c414f1ea2cedcb10b97aa71ed63f0e

## State Impact

none: Nothing changed: no code, docs, receipt, probe or prompt. The gate reading, slot accounting and frontier are exactly as tidy-nest-3309 measured them and soft-creek-6253 restated them; the only new observation is about the loop's dispatch cadence, which is not a fact about the project's state.
