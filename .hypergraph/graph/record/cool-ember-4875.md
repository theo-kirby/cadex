---
node_id: 54ad7e47-793f-5c6b-9de8-1cee896d29f3
slug: cool-ember-4875
title: F7's biped lands on plover-e, and a closing smoke stops colliding (ADR-391)
created_at: '2026-09-19T23:16:18+00:00'
parents:
- weathered-fountain-7838
summary: ''
---
## What

F7's frozen create prompt went live on Opus in a fresh `ot7-plover-e`, ran
2,695.8 s, ended on its own, and produced **a biped with a measured, failing
fit report** — the first Plover call that measured the agent rather than this
repository. Its slot is spent and its three continuations are unspent.

While it ran, the ot7 collector's closing-smoke defect was fixed (ADR-391,
commit `3958959c`): `evidence/smoke` was created with a bare `mkdir()`, so a
second closure on the same project raised `FileExistsError` *after* the model
had spoken and *before* the status that closes the attempt was persisted.
`ot7-robin-c` carries such a directory today with `continue-3` still to
dispatch, so the next F6 turn would have hit it.

Committed: `3958959c` (collector + ADR-391 + README + REPORT section),
`873763e5` (the plover-e receipt and its report section).

## Why

Exactly the critic's message: capacity is the scarce resource, F7 held all
four slots and its turn runs long, so the dispatch went first and the
collector fix filled the wall-clock beside it. The fix is also the stated
precondition on F6's `continue-3`, which is the unit after this one. Nothing
under `src/Mod/cadex` was touched while the turn was live (ADR-390's process
fact); the whole diff is the collector, its tests and docs.

Frontier: `rapid-grove-9687` (F7), with `chilly-union-8972` (the CLI and its
collector) carrying the fix.

## Method

**The dispatch.** `run.py window --model claude-opus-5` read the five-hour
window at 17 % against the 45 % gate, then
`run.py plover $PROJECTS/ot7-plover-e --model claude-opus-5 --turns 1`.
One prompt, one window probe, no actor edit of any kind.

**The fix.** The closing smoke now takes the first free name —
`evidence/smoke`, then `evidence/smoke-retry-N` — on the same rule the turn
directories already use, and the receipt names the directory it used in
`smoke.evidence_dir`. Earlier smoke evidence is never overwritten. The
fixture walks the whole reachable chain with the runner's public entry
points: a pre-ADR-386 receipt closed on a refusal, `reclassify` giving the
slot back, the retry closing on a provider failure, and the second closing
smoke landing beside the first. It fails on the old code with the exact
`FileExistsError`, verified by stashing the fix.

`pixi run python -m pytest cli/tests` — **843 passed, 1 skipped** in 552 s.
No engine, protocol or payload change, so no engine suite or packaged gate is
implicated.

## Result

**F7 has a design result.** `ot7-plover-e`, accepted revision `a6f75c23…`:
29 components — four catalog MG90S servos with hip and knee pitch per leg,
four `mg90s-single_arm` horns, four MR128 bearings, twelve bolts — and five
printed parts (pelvis, two thighs, two shins) as the only uncatalogued
sources. Free base, no world geometry. Static fit **12 failing of 406**
(394 clear, 0 below clearance, 0 unknown); attachments **24 of 24 touching**,
nothing reported; sweep **complete on all four joints** at a 15° step, 48
failing rows over **exactly 12 distinct pairs** — the same twelve. Every
failure is one class: a fastener modelled solid where the printed part has no
clearance hole for it (8 tab screws at 4.0715 mm³, 4 centre screws at
15.7080 mm³). 52 tool calls, 194,037 output tokens, zero actor edits, window
cost 15 points. Receipt: `docs/probes/ot7/attempts/plover-e-create.json`.

**The collector no longer loses a closure.** F6's `continue-3` on
`ot7-robin-c` is unblocked and is the natural next unit; F7's `continue-1` is
the one after, and both need a window reading under 45 %.

Concerns for the next iteration. (1) The five-hour window read 32 % at the
turn's last frame and resets at 2026-09-20T02:10 UTC; two more design turns
in this window is plausible, three is not. (2) `overageDisabledReason:
out_of_credits` appears in every window frame — it is not a refusal today,
but it is the shape a stop would take. (3) The plover-e receipt is `paused`,
so no smoke has run on it; F7's smoke arrives only at its closure. (4) The
unreconciled tail is three records deep after this one, and the reconcile is
due at five.

Dispatch closed: 1 unit — F7's create turn dispatched and collected on
`ot7-plover-e` (a biped, 12 of 406 static failures, three continuations
unspent), with the collector's closing-smoke collision fixed beside it
(ADR-391).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 873763e59ff86cdadcb0ec24832316a9d955a52b

## State Impact

- target: rapid-grove-9687 — F7 now has a design result: the frozen create prompt reached the model on ot7-plover-e, ran 2,695.8 s, ended on its own and spent one slot, and its accepted revision a6f75c23 is a real four-servo biped (29 components, catalog MG90S servos, horns, MR128 bearings and bolts, five printed parts, free base, no world geometry) with a failing but complete fit report: 12 of 406 static pairs intersecting, 24 of 24 attachments touching, all four joints swept complete at 15 deg with 48 rows over 12 distinct pairs, all one defect class (fasteners with no clearance hole). Zero actor edits, three continuations unspent, no smoke yet.
- target: chilly-union-8972 — The ot7 collector's closing smoke takes the first free directory name (evidence/smoke, then smoke-retry-N) and records it in smoke.evidence_dir (ADR-391, commit 3958959c). A reopened attempt that closes a second time no longer raises FileExistsError after the model has spoken and before the closing status is persisted, which would have left the receipt at 'running' and let a later resume spend a frozen continuation on a closed attempt. ot7-robin-c's continue-3 is unblocked. cli/tests: 843 passed, 1 skipped.
