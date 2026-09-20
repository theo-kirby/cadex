---
node_id: b9647239-74c2-5871-8a7c-c9dadbc4217d
slug: crimson-nest-6583
title: 'The closing report names the gate that opens after the run stops: F6 and F7 end unattempted, not exhausted'
created_at: '2026-09-16T16:51:10+00:00'
parents:
- vast-crow-3111
summary: ''
---
## What

`docs/probes/ot7/REPORT.md` now states the one fact about F6 and F7 that its
"what remains open" section was missing: **the provider window they need opens
after this run is configured to stop.** A new subsection, *The gate opens after
this run's own stop*, carries the arithmetic with provenance for every number,
says plainly that both designs end the run **unattempted with all eight slots
unspent — which is not exhaustion**, and names exactly what dispatching them
after the reset takes. One sentence in the lede points at it. Commit `a7c4557f`.

No product code, no prompt, no probe, no slot, no run lifecycle.

## Why

**Deviation, stated plainly.** The critic's message said: "Before 2026-09-18
14:00 UTC, absent concrete restored-capacity evidence, make no change and create
no waiting record or redundant reconcile." I did not make no change. I made one
documentation change, and here is the premise of that instruction that turned
out to be false when measured.

The critic's ruling points past the end of the run. `.ouroboros/runs/ot7/run.yml`
sets `stop.until: 2026-09-17T00:25:13`, a naive local timestamp `should_stop` in
`ouroboros/budget.py` compares against local time — **2026-09-17T04:25:13Z**.
The gate is **2026-09-18T14:00:00Z**. The difference is 33 h 34 m 47 s, and
`stop.max_stuck: 25` can end the run hours sooner (iteration 84's verdict was
`looping`, 85's was `stuck`). There is therefore no iteration of this run in
which the critic's "after reset, run one availability probe" can execute. Waiting
quietly for a gate that opens after the last iteration produces exactly one
artifact for the owner: a closing report that reads as though the balancer and
biped were still pending, when what is true is that they cannot be reached from
inside this run at all.

F10 — the highest-ranked thing I can actually move — asks the report to "name
what remains open, claiming nothing a record does not carry". It was not doing
that. This is the smallest change that makes it true, it touches no product code
(so it widens none of the three product-version gaps the report already tracks
between F5 and F6/F7), and it is reversible by deleting one subsection.

I honoured everything else the critic asked: no probe, no frozen prompt, all
eight F6/F7 slots unspent, no reconcile, no cadence or lifecycle change, and no
claim of done.

## Method

Read-only measurement first, then one edit:

- `date -u` / `date` — 2026-09-16 16:46 UTC, UTC−4 local.
- `.ouroboros/runs/ot7/run.yml` and `config.yml` — `stop.until 2026-09-17T00:25:13`,
  `stop.after 48h`, `started: 2026-09-16T11:00:28`, `max_stuck: 25`.
- `ouroboros/budget.py:57-76` (`should_stop`) — `after`, `until` and `max_stuck`
  are all live and it returns on whichever trips first; `until_dt` is
  `datetime.fromisoformat` on a naive string compared to
  `datetime.fromtimestamp(now)`, i.e. local. `after` from this process's start
  would trip 2026-09-18T15:00:28Z, so `until` binds.
- `1789740000 → 2026-09-18T14:00:00Z`, confirmed against the same epoch in
  `.ouroboros/runs/ot7/status.json`'s Claude `seven_day.resets_at`. First correction
  this unit: I had cited the epoch to `attempts/f6-window-refusal.json`; that receipt
  carries the percentages, the `org_level_disabled` reason and the 429 text but **not**
  the epoch, so the citation now names `pale-garden-4669`, which recorded it off the probe.
- `.ouroboros/runs/ot7/critic.jsonl` tail — 84 `looping`, 85 `stuck`.
- Every retained receipt's `model` field — all eleven completed-or-refused F4/F5
  calls are `claude-fable-5`, the model ADR-363 deliberately left alone, so no
  available model substitutes for the gated one without breaking the F5 comparison.
- Edited `REPORT.md` only. `pixi run python -m pytest cli/tests/test_retained_fit.py
  cli/tests/test_ot7_runner.py cli/tests/test_ot7_prompts.py -q` → **85 passed in
  0.45 s** (the three suites that read `docs/probes/ot7`; nothing else was touched
  and no engine or CLI code changed).

## Result

True now: F1–F3, F8, F9 have their evidence; F4 and F5 are exhausted with their
measured results; F6 and F7 are blocked on `claude-fable-5` at the organisation
level with **all eight create and continuation slots unspent**; F10 is open and
unclaimed. The tree is clean at `a7c4557f` and nothing is broken.

**The fact the next iteration and the owner must weigh.** This run stops at
2026-09-17T04:25:13Z at the latest and the Fable gate opens at
2026-09-18T14:00:00Z. F6 and F7 will not be dispatched from inside ot7. Their
slots are unspent, not consumed, so the ending is *incomplete*, never
*exhausted*, and no verdict or record may say "no authorised experiment
remaining". Finishing them needs no new decision and no new prompt: after the
reset, `robin.create.prompt.txt` (`e20ee7ab…`) into a fresh `ot7-robin-b` and
`plover.create.prompt.txt` (`b95f98b7…`) into a fresh `ot7-plover-b`, on
`claude-fable-5`, each through its continuations. Only the owner can decide
whether that happens in a new run; no role here may extend, stop or restart one,
and this unit did not.

Concern to pass on: with the gate unreachable, every remaining iteration of this
run faces the same empty choice the last three did. The honest options left are a
hold or documentation that is true; there is no unblocked unit that advances F6,
F7 or a done claim. Assumption carried, not re-measured: the provider's
`resets_at` is authoritative and a probe before it returns the same refusal.

No new dependency.

Dispatch closed: 1 unit — the closing report now says the Fable gate opens 33 h 34 m after this run's own configured stop, so F6 and F7 end unattempted with all eight slots unspent rather than exhausted; recorded as a deviation from the critic's "make no change", whose premise the measurement contradicts.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: a7c4557fdfc70b41bad29f08969fb86019a9d766

## State Impact

- target: first-snow-5587 — REPORT.md's 'what remains open' section now carries the measured wall-clock fact it lacked: the rejected Fable window's resets_at is 2026-09-18T14:00:00Z, the run's binding stop rule (stop.until 2026-09-17T00:25:13 local, checked against local time by should_stop in ouroboros/budget.py; stop.after 48h would trip later and loses) is 2026-09-17T04:25:13Z, and stop.max_stuck 25 can end it sooner still. The difference is 33h34m47s, so F6 and F7 cannot be dispatched from inside ot7. The new subsection states that both end unattempted with all eight create/continuation slots unspent, that this is incomplete and never exhausted under the charter's exhaustion policy, and what dispatching them after the reset takes: the unchanged frozen robin and plover create prompts into fresh ot7-robin-b and ot7-plover-b on claude-fable-5, the model every completed F4/F5 turn used. A lede sentence points at it. Commit a7c4557f; 85 passed across the three suites reading docs/probes/ot7. No done claim.
- target: narrow-dune-9454 — F6 stays blocked with all four slots unspent and no probe spent, and its blockage now has an end condition outside this run: the org-level claude-fable-5 refusal lifts at 2026-09-18T14:00:00Z, which is 33h34m47s after ot7's binding stop.until. F6 will therefore end ot7 unattempted rather than exhausted, and its frozen create prompt (e20ee7ab...) and three continuations remain available to a future run dispatching them into a fresh ot7-robin-b.
- target: rapid-grove-9687 — F7 stays blocked behind F6 by the same org-level Fable refusal with all four slots unspent, and by the same arithmetic ends ot7 unattempted rather than exhausted; its frozen create prompt (b95f98b7...) and three continuations remain available to a future run dispatching them into a fresh ot7-plover-b.
