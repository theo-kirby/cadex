---
node_id: faedf2f2-ef56-589e-ab12-c6edecb320fa
slug: terse-dew-6200
title: F6 continuation never reached the model; unreached calls spend no slot (ADR-386)
created_at: '2026-09-19T17:55:02+00:00'
parents:
- zesty-otter-7762
summary: ''
---
## What

F6's first frozen continuation was dispatched on `claude-opus-5` into
`ot7-robin-c`, and **never reached the model**. The launch-time window probe
read the five-hour window at 2 % and the seven-day at 1 %, so the product
agent had room; the CLI refused locally, in 5.98 seconds, before a provider
session existed:

> Could not open …/ot7-robin-c: The restore pass digest does not match the
> accepted digest.

No `transcript.jsonl` was written at all. The runner had two no-slot classes —
a provider usage limit (ADR-355) and a runner-bound kill (ADR-356) — and
neither fits a local refusal, so the call fell through to "a provider error
the call returned on its own", which **spends its slot and closes the design**.
That booked a frozen continuation the model never saw and forfeited Robin's
other two: the receipt read `status: failed`, `slots_spent: 2`,
`continuations_unspent: 0`.

Two things landed, as one fix (ADR-386, commit `8226b4b5`):

1. **The runner now recognises an `unreached` turn** and spends nothing for
   it. A turn is unreached when its child exited nonzero for neither of the
   other two reasons, wrote no provider frames, and left a CLI envelope with an
   error and an empty `session_id`. Both halves are required, so a synthetic
   `authentication_failed` frame (a stream) stays failed, a crash after the
   model spoke stays failed, and a call with no envelope stays failed — the
   same rule that missing evidence never means a passing result. Unlike a void
   or interrupted call it names **no fresh project**: nothing was consumed, so
   the attempt is *paused* with a `blocked` block, `remaining()` skips the row
   entirely, and `resume` re-sends the same prompt into a `turn-N-retry-M`
   directory that leaves the refusal's evidence in place. `run.py reclassify
   PROJECT` corrects a receipt written before the rule from the retained
   streams, keeping the superseded copy beside it; it can only ever demote a
   row the evidence proves never reached the model. Applied to `ot7-robin-c`,
   it returned the design to **one completed create turn with three
   continuations unspent**.

2. **The refusal itself is measured and documented, and deliberately not
   fixed** (`docs/probes/ot7/DIGEST-DRIFT.md`).

## Why

The charter names Robin's first continuation on `ot7-robin-c`, explicitly on
Opus, as the next substantive unit, and it advances F6 — the highest-ranked
open criterion with an unspent slot. The dispatch is what exposed both
findings. Nothing here was asked for instead of what the charter asked for:
the prompt was sent, under the window gate, exactly as directed.

The accounting fix rather than the deeper defect is this iteration's unit
because the deeper fix cannot be landed safely in one unattended unit (below),
and because leaving the accounting wrong would have silently closed F6 on a
call that never happened — the one thing the charter's "a usage limit is not
an attempt" rule exists to prevent, arriving through a door it did not cover.

## Method

Window probe on Opus (`run.py window --model claude-opus-5`) → allowed, 2 %.
Dispatch `run.py resume ~/cadex-projects/ot7-robin-c --model claude-opus-5
--turns 1` → exit 1 in 5.98 s, no transcript, envelope error at project open.

Then the diagnosis, all of it reproducible:

- **The mismatch is not stable.** Accepted digest `0a6fe0f5…`; three rebuilds
  of the same bytes gave `e9ffa272…` (in the project), `908ed881…` and
  `7d2a5051…` (two untouched copies, via `./cadex export`). The project is shut
  for good, differently every time.
- **Two outputs of 26 differ**, `wheel_l` and `wheel_r`, at the *same* byte
  length (16,927). The differing records are the geometry table: same curves,
  different order.
- **Isolated to one operation.** A minimal script through real `cadexd`, three
  separate processes each: `part.offset(cylinder, 0.15, output_type="solid")`
  → `ad7a46c2…`, `f1d2ecd2…`, `eed4f4fe…`, three different; a `fuse`/`cut`
  control → `260f3221…` three times. Robin's wheels are the design's only
  consumers of `part.offset`; Heron, which uses none, resumed through three
  continuations on 2026-09-17 without trouble.
- **The shape is identical; only its serialization is not.** Directly against
  the kernel, three processes: volume `232.666456132` mm³, 5 faces, 7 edges,
  4 vertices and the same edge-length multiset every time — while **4 of the 5
  individual faces export to different bytes each run**. So the instability is
  *inside* each face. Rebuilding the solid from faces sorted by centre of mass
  and area — the obvious canonicalization — does **not** stabilize the digest.
  That is a measured dead end, not a guess.

Verification: 7 new fixtures in `cli/tests/test_ot7_runner.py` (unreached
create; resume into the same project; four negatives that must stay failed;
the reclassify correction, idempotent on a second pass). All 7 **fail on the
old runner**, confirmed by stashing `run.py`. `cli/tests` 839 passed, 1
skipped. `pixi run test-engine` 2169 passed, 53 skipped. No engine, protocol,
payload or dashboard code was touched, and no design was edited by the actor
(`actor_design_edits: 0`).

## Result

**F6 is blocked, not exhausted.** Robin's create turn stands (0 of 276 static
pairs failing, swept coverage incomplete), its three continuations are unspent,
and the same frozen `continue-1` prompt is still next *in the same project*.
It cannot be sent until the rebuild refusal is fixed — a continuation would
refuse identically, in six seconds, forever.

**The blocking defect, for the next iteration.** `compute_project_digest`
(`cadex_project_worker.py:164`) identifies a BREP output by its exported bytes,
and `part.offset` — OCCT's `BRepOffset_MakeOffset` — does not produce the same
bytes twice. Any accepted design using it can never be reopened. **This is the
next unit, and it is a real design decision, not a patch:** the precedent to
follow is the mesh branch of that same function, which already uses an
order-insensitive fingerprint instead of artifact bytes (ADR-016). Redefining
the BREP branch outright would invalidate **every** stored `accepted_digest`
and break the charter's own "existing projects keep opening" (F2, F9), so it
needs a migration — most likely a versioned digest, or a per-output geometric
comparison consulted only when the bytes disagree, which keeps the guard's
real purpose (never re-accept *changed geometry*) while letting a
byte-unstable project open.

**Nothing that works today is at risk.** Heron, Finch and the retained ot6
designs use no `part.offset`; their digests are byte-stable and their projects
open. `ot7-robin-c` was already unopenable before this iteration touched it.

Concerns and assumptions the next iteration must know:

- The failed open *did* write `latest_candidate` and `updated_at` in
  `ot7-robin-c/script.json`. The accepted state is intact — the guard
  explicitly rewrites it before refusing — and the unreached row's
  `accepted_after` was snapshotted afterwards, so `resume`'s
  design-identity check passes. No actor edit occurred.
- Assumption taken, per the question policy's "most reversible option": an
  unreached call retries **in place** rather than in a fresh letter-suffixed
  project, because no slot, no session and no design state moved. Void and
  interrupted calls keep their fresh-project rule unchanged.
- F7 (Plover) is **not** blocked by this unless its design reaches for
  `part.offset`; that is unknown until its create turn runs. The window is
  open and F7's create slot is unspent, so F7 is dispatchable now if the
  critic prefers it over the digest fix.
- The unreconciled tail is 3 nodes after this one; a reconcile is due soon.

Dispatch closed: 1 unit — F6's Opus continuation never reached the model; the
runner no longer spends a frozen slot on a call the model never saw, Robin's
three continuations are restored, and the `part.offset` rebuild drift that
locks the project shut is measured, isolated and documented as the next unit.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 8226b4b559f3674c0ec23d339f161a76092a5be1

## State Impact

- target: narrow-dune-9454 — F6 is blocked, not exhausted: the Opus continuation on ot7-robin-c never reached the model (local project-open refusal, no provider stream), the runner's misbooking of it as a spent slot is corrected (ADR-386), and Robin's create turn plus three unspent continuations stand. F6 now waits on the part.offset rebuild-drift fix.
- target: chilly-union-8972 — run.py gains an unreached call class and a reclassify mode; the CLI itself is unchanged, and cli/tests is 839 passed / 1 skipped.
- target: forest-wind-0342 — measured defect: compute_project_digest identifies a BREP output by exported bytes, and part.offset (OCCT BRepOffset_MakeOffset) emits different bytes every process for an identical shape, so any accepted design using it can never be reopened. Isolated against a fuse/cut control; face-sorted canonicalization measured and ruled out. docs/probes/ot7/DIGEST-DRIFT.md.
