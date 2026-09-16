---
node_id: 8399f2c4-bcdb-508c-abce-a298577ffdd8
slug: clear-spark-8613
title: The frame that bound the call is the reading, in both directions (ADR-376)
created_at: '2026-09-16T21:43:09+00:00'
parents:
- solar-arrow-5671
summary: ''
---
## What

ADR-376. The ot7 collector's window gate read the wrong `rate_limit_event`
frame on a probe the provider **answered**, so the provider's frame order
alone decided whether F6's create prompt was dispatched or deferred. Fixed:
the reading is the frame that bound the call — the one that rejected on a
refused probe (ADR-369, unchanged), the one that allowed on an answered one.
Two known-answer tests, both red on the old code. `docs/DECISIONS.md`,
`docs/probes/ot7/runner/README.md`, `docs/probes/ot7/REPORT.md` and
`attempts/f6-window-refusal.json` carry it. Commits `235ebce4`, `8f44bec3`.

## Why

The critic's message: keep F6 as the next design unit; while availability
remains refused, make no change and write no waiting record **unless a
concrete reproduced tooling defect advances an F criterion**. I did what it
asked, in that order.

Availability first. `run.py window --model claude-fable-5` at 21:37 UTC was
refused outright: `seven_day_overage_included` 100 %, `overageDisabledReason:
org_level_disabled`, five-hour 11 %, exit 1 in 2.37 s, `room: false`. The
probe spends no slot. So no F6 dispatch, and no model switch was considered —
the configured product model stays `claude-fable-5`.

That left reading the gate that will decide F6's dispatch when capacity
returns, and it holds a defect. ADR-369 fixed one direction of a two-sided
problem and the other side was never covered. It advances F6 and F7 directly:
it is the last thing standing between "the refusal lifted" and "the prompt was
sent", and its failure mode is silent and permanent rather than one deferred
probe.

## Method

1. Probed availability (above). Refused; no design turn.
2. Read `window_reading`/`window_has_room`/`dispatch` against ADR-364 and
   ADR-369. ADR-364 makes `refused` ignore the stray rejected
   `seven_day_overage_included` frame this organisation emits on every probe,
   "so a stray rejected frame cannot close the gate on an account that in fact
   has room" — but `info = infos[0]` then took `status` from whichever frame
   came first, which can be that same stray frame. ADR-369's own measurement
   is that both orders occur on this account, twenty minutes apart.
3. Reproduced before changing anything. One answered probe, five-hour at 8 %,
   two `rate_limit_event` frames, nothing else varied:

   | frame order | `refused` | `status` | five-hour | gate |
   |---|---|---|---:|---|
   | allowed, rejected | none | `allowed` | 8 % | dispatch |
   | rejected, allowed | none | `rejected` | 8 % | **defer** |

4. Fixed: `allowed[0]` on an answered probe, `rejected[-1]` on a refused one,
   falling back to `infos[0]` when the stream holds no frame of the kind
   needed — conservative both ways, since an answered probe carrying only
   rejected frames still reads `rejected` and still does not dispatch. Window
   merging is untouched, so the 100 % window that is merely unavailable is
   still named in the receipt by the frame that named it.
5. Two tests: `test_an_answered_probe_reads_the_frame_that_allowed_it_whatever_the_order`
   sends both orders and requires one reading;
   `test_a_stray_rejected_frame_in_front_still_dispatches_the_frozen_prompt`
   pins the schedule-level cost. Confirmed both fail on stashed old code and
   pass on the new.
6. Full CLI suite: **812 passed, 1 skipped, 528.00 s**. No engine change, so
   no engine suite or packaged gate was required or run.

## Result

The gate is correct in both directions and pinned against the order that
failed. The two pre-existing stray-frame tests put the allowed frame in front,
passed throughout, and never covered the failing order — that is why this
survived ADR-364 and ADR-369.

Scope: the runner is evidence-collection machinery under `docs/probes/`. No
engine, CLI, protocol, payload, acceptance or dashboard behaviour changed; no
frozen prompt, slot count or design result moved. ADR-376 is therefore **not**
added to REPORT.md's ten-change "product version" list, which counts only
changes a design's own measured fit reads. It stays ten.

**Availability is unchanged and F6 remains blocked.** Four probes now, at
14:29, 14:50, 17:02 and 21:37 UTC, all refused on the same
`org_level_disabled` setting. F6's four slots and F7's four are unspent; no
`ot7-robin-b` or `ot7-plover-b` exists. F10 cannot close. Nothing here is
evidence the refusal will lift, and the `seven_day_overage_included` reset at
2026-09-18T14:00Z is the schedule of a usage window, not a date for the
organisation setting that refused — it also falls after this run's configured
`stop.until`. No role stopped, started or restarted anything.

For the next iteration: probe before assuming either way; a scheduled reset is
not availability, and a refused probe is not permanent. If the probe comes
back unrefused, dispatch F6's frozen `robin.create.prompt.txt` into a fresh
`ot7-robin-b`, then F7's `plover.create.prompt.txt` into `ot7-plover-b`. No new
dependency. The unreconciled tail is 3 records after this one; a reconcile pass
is the critic's call, not mine.

Dispatch closed: 1 unit — ADR-376 fixes the answered half of the ot7 window gate, where the provider's frame order alone could have withheld F6's and F7's eight unspent prompts from a model with room; F6 stays blocked on a refusal reproduced again at 21:37 UTC.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 8f44bec33534570ebc7d149365e30d6b368f0394

## State Impact

- target: narrow-dune-9454 — F6 stays blocked: a fourth probe at 2026-09-16T21:37Z was refused on the same org_level_disabled setting (seven_day_overage_included 100 %, five-hour 11 %), all four slots unspent and no ot7-robin-b. The gate that will decide its dispatch is now correct in both directions (ADR-376): on an answered probe the reading is the frame that allowed the call, not whichever arrived first, so the stray rejected overage frame this organisation emits can no longer defer the prompt on frame order alone.
- target: rapid-grove-9687 — F7 unchanged and still blocked behind F6 by the same refusal, all four slots unspent and no ot7-plover-b; the same ADR-376 gate correction applies to its dispatch.
- target: mild-ledge-7157 — The ot7 collector's window gate gains ADR-376: the reading is the frame that bound the call in both directions, fixing the answered half ADR-369 left on infos[0]. Reproduced both frame orders of one answered probe at five-hour 8 %, pinned by two tests red on the old code; CLI suite 812 passed, 1 skipped. Runner-only — no engine, CLI, protocol, payload, acceptance or dashboard change, and REPORT.md's product-version list stays at ten.
