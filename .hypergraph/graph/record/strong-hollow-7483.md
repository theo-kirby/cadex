---
node_id: 78c432df-47c8-5994-aeb3-2e7bc4cb98ea
slug: strong-hollow-7483
title: F7's Plover create turn reaches Opus and is killed at the 30-minute bound
created_at: '2026-09-19T18:39:06+00:00'
parents:
- terse-dew-6200
summary: ''
---
## What

F7's frozen Plover create prompt was dispatched on `claude-opus-5` into a
fresh `ot7-plover-c`, after a window probe read `allowed` at 14 % of the
five-hour window and 2 % of the seven-day. The call reached the model and ran
the full **1800.0 s** turn bound — 124 frames, 49 tool calls (4
`describe_api`, 30 `inspect`, 10 `write_script`, 4 `edit_script`, 1
`rebuild`), 1.29 MB of transcript, zero actor design edits — and was killed at
the bound while reading its own measured fit back through `inspect
scope=clearance`. Under ADR-356 that is an **interruption**: no slot spent,
retry in `ot7-plover-d`. F7 still holds its create prompt and all three
continuations.

It is the first F7 call to produce geometry. The last revision it built
(`15be5515…`, never accepted) is a 30-component biped, 24 components
catalogued and 6 printed, measured at **13 failing of 435 static pairs** (12
intersections and 1 world-geometry failure, worst a centre screw 12.566 mm³
inside its own hip servo) and **52 failing swept pairs over 4 of 4 joints,
coverage complete**.

Committed: `docs/probes/ot7/attempts/plover-c-interrupted.json` (3,993 B), an
F7 section in `docs/probes/ot7/attempts/README.md`, and an F7 section plus a
corrected slot-table row in `docs/probes/ot7/REPORT.md`. Commit `afd3b773`.

## Why

This is exactly the critic's first option and the owner's named next unit: run
the product-model availability check, and if it passes, dispatch F7's frozen
create prompt on Opus into a fresh `ot7-plover-*` project. The check passed
(`status: allowed`, five_hour 14 %, `room: true`), so the design turn was the
live unit and the digest fix stayed the fallback.

One deviation from the runner's default: `--turns 1`, the create prompt only,
rather than the whole four-prompt schedule. Iteration 154 had just lost a
dispatch when its own runner died, and a kill part-way through a four-turn
schedule discards every completed turn with it, because the retry must go to a
fresh project. The turn was also launched under `setsid`, so it would outlive
this actor rather than die with it. Both choices are recorded here as
assumptions; neither touches a prompt or a slot.

## Method

1. `run.py window --model claude-opus-5` → `allowed`, five_hour 14 %,
   seven_day 2 %, `refused: null`, `room: true`.
2. `run.py plover ~/cadex-projects/ot7-plover-c --model claude-opus-5
   --turns 1`, detached, prompt digest `b95f98b7…` checked against the freeze
   by the runner before the project was created.
3. Read the runner's own finalised receipt and the retained `fit.json`,
   `clearance.json` and transcript; counted the tool calls from the
   transcript rather than from the stderr echo.
4. Compared create-turn cost across the three designs' retained receipts.
5. Wrote the compact receipt and the two doc sections; committed.

No product code, protocol or payload changed, so no build, suite or packaged
gate was run. `ot7-plover-c`'s script was never accepted and nothing in this
repo's engine or CLI was touched.

## Result

F7 is dispatchable and was dispatched; it is not blocked on provider capacity.
What it is blocked on is the clock. Create turns cost more the larger the
design — Heron **1,530.4 s** at 120 static pairs, Robin **1,676.4 s** at 276,
Plover **1,800.0 s** at 435 — so the biped is the first design whose create
turn does not fit in `TURN_BOUND_SECONDS = 1800`, and it was still making
progress when the clock fired. **A retry at the same bound has no reason to
end differently: `ot7-plover-d` should follow a raised bound, not precede
it.** That is the next unit I would take — one runner constant, its receipt
field and a fixture — and it is cheaper than the digest fix that F6 needs.

Two things the next iteration must know.

**The runner cannot finalise a receipt when the runner itself dies.** Iteration
154's `ot7-plover-b` has been stale at `status: running` since 18:01:53 UTC:
16 frames retained, an empty envelope, and no classification. `reclassify`
only re-reads rows already marked `completed`, so it does not reach this one.
The evidence is unambiguous — a child that never ended on its own, no slot
spent — and the committed receipt and the report both say so in prose, but no
tool asserts it. Fixing that is a real unit; leaving it is a stale receipt in
the evidence set.

**The 13 static and 52 swept failures are not an F7 result.** They describe an
unaccepted candidate the agent was mid-way through repairing. They are
evidence for F1–F3 — the measured-fit surface working on the largest design
ot7 has put through it, 435 pairs and a complete four-joint sweep — and for
nothing else. F7's bar is an accepted design at zero failing checks.

F6 remains blocked on the `part.offset` digest drift; nothing here touched it.

Dispatch closed: 1 unit — F7's create prompt reached Opus on `ot7-plover-c`, was killed at the 30-minute bound with 13/435 static and 52 swept failures measured on an unaccepted 30-component biped, spent no slot, and named the turn bound as the next thing to raise.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: afd3b77300bcbd41b0f7caa6c6fe58ab2e75ff5b

## State Impact

- target: rapid-grove-9687 — F7 is dispatchable and was dispatched: the frozen create prompt reached claude-opus-5 on ot7-plover-c (window allowed, 14%), ran the full 1800 s bound across 49 tool calls and was killed mid-repair — an ADR-356 interruption, no slot spent, all four slots still held, retry ot7-plover-d. First F7 call to produce geometry: an unaccepted 30-component biped (24 catalogued) measured at 13 failing of 435 static pairs and 52 failing swept pairs over 4 of 4 joints, complete coverage. The binding constraint is now TURN_BOUND_SECONDS=1800, not capacity: create turns cost 1530.4 s at Heron's 120 pairs, 1676.4 s at Robin's 276, 1800.0 s at Plover's 435, so plover-d must follow a raised bound.
- target: chilly-union-8972 — The ot7 collector has a gap it cannot classify: a receipt whose runner process dies mid-turn stays at status 'running' with an empty envelope (ot7-plover-b, iteration 154, 16 frames). reclassify only re-reads rows already marked completed, so nothing finalises it; the interruption is recorded in prose only.
