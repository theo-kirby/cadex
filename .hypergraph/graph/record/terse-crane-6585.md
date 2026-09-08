---
node_id: 39e0caac-b5e1-589d-8223-4942db07d85f
slug: terse-crane-6585
title: 'Bet: strip the held iterate to its core and give the rung a token-free floor'
created_at: '2026-09-08T22:16:36+00:00'
parents:
- idle-falcon-3004
summary: ''
---
## What

The live project-history iterate stays ranked first for a third pass, but
stripped to the conditions that are load-bearing and explicitly authorized
rather than hedged. Beneath it the rung gains two units that are dispatchable
with no provider at all: a token-free walk that puts the derived section plane
into a live `review.json` alongside the other three eyes, and carrying
`--detach` through the CLI's walk. Medium retires the landed section item and
says plainly what a human still needs in order to tick each seeded criterion.

## Why

**The top unit has now been ranked first twice and taken zero times.**
`western-cliff-6876` records the reason in its own words: "Short unit 1 (the
live provider iterate) was not taken: it is a long, provider-dependent design
turn." `idle-falcon-3004` took an overseer-named leg instead. Nothing about
the world blocks it — `claude` is on PATH at `/home/theo/.local/bin/claude`,
`build/release/bin/{FreeCADCmd,CadexGeometryWorker}` exist, `ot4-quill` carries
the ARCHITECTURE / DECISIONS / PROGRESS history the turn is supposed to read,
and supplied Claude five-hour usage is 20% consumed with 37.4h of run left.
What blocks it is the unit's own framing: the rung stated it as a paragraph of
eleven preconditions — an engine-source check, a CPU shape, three seeds, two
timeouts, a memory watchdog, exclusion rules, artifact preservation, four
review verifications, two doc updates and a gate — which reads as a setup
project rather than one iteration. The rails were each learned from a real
prior failure and none is being withdrawn; they move into the negative
knowledge that already holds them, and the unit states what it is *for*. The
charter is unambiguous that this is the leading item ("One thing leads this
run: the lifecycle walk, run end to end on this machine"), and equally
unambiguous that a bad outcome is still an outcome: "a failed run names the
next unit."

**The "frontier unmoved for 7 iterations" signal is structural here and should
not be read as a stall.** All four charter-seeded criteria sit at `working` in
the projection, and the reconciler is explicit that the tick "stays a charter
decision rather than a maintainer one" (`damp-moon-9297`). The only three
`open` state nodes are `round-glacier-2865` (reduction — charter demoted it to
standing work), `brave-stone-9609` (catalog — parked on the later rung) and
`late-pond-2851` (gait — blocked at scale). No unit this rung can take will
move that count. The honest progress measure is whether the walk's still
unexercised legs get exercised.

**The rung lost its always-dispatchable fallback when the section unit landed,
and `western-cliff-6876` names its replacement.** That record closes with the
gap it left: "the four eyes have not been re-exercised together on a real
mechanism since this change — the next headless walk is what shows the derived
plane in a live `review.json`." The derivation was verified against *stored*
bounds from previous runs, never against a live cut. A walk with no `--prompt`
spends no tokens (the parser says so: "Spends tokens only for --prompt"), runs
in the ~850 s the seed runs cost, and produces exactly that evidence. It is
not a fifth seed and must not be reported as one — the measurement is section
coverage, not a reward row.

## Method

Rewrite `## Current` on `young-crane-9546` (three ranked units) and
`strong-birch-7412` (retire the landed section item; state the per-criterion
tick conditions). Add one negative-knowledge entry to each: on short, that the
stripped unit-1 rails still hold and that a provider refusal hands down the
rung rather than ending the iteration; on medium, that the frontier-unmoved
count is structural. `late-valley-7350` is untouched — nothing landed against
the parked rungs. No charter gap is retired, proposed `blocked`, or marked
done, and no new direction is spent.

## Result

A planning pass only: no code, no state node, no charter edit. Success is the
next iteration taking unit 1 and reporting what the design turn did with the
project's own history — or, if the provider refuses, taking unit 2 in the same
iteration and landing the first live derived section.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: dc3fa228791d828602ca2b605465a0fa91233fbc

## State Impact

- target: plan/young-crane-9546 — rank three units: the stripped live iterate, a token-free walk proving the derived section live, and --detach through the walk
- target: plan/strong-birch-7412 — retire the landed section item; state what a human still needs to tick each seeded criterion; record that the unmoved-frontier count is structural
