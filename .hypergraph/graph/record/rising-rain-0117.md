---
node_id: 6582f435-c186-53b7-a406-f1c875acd4a0
slug: rising-rain-0117
title: The section eye ranks by what it cuts, and says what it missed
created_at: '2026-09-08T23:52:15+00:00'
parents:
- sleepy-mesa-0821
summary: ''
---
## What

The derived section offset is now chosen by **what the plane actually cuts**,
not by how many bounding boxes it crosses, and no object's own centre plane
can be dropped from the candidate list any more (ADR-273, commit `3b04e535`).
`cli/cadex_cli/section.py` only; 265 CLI tests pass.

Advances the open charter criterion **"The agent can see its work without a
screen"** (`damp-moon-9297`) — the section-view call of the four.

## Why

Dispatched by the overseer: *"fix the section eye's coverage heuristic so it
cuts `cmp_swing_arm`. Ordering candidate planes by bounds crossed picks planes
that miss the solid; order by objects actually cut and re-measure both rigs
live."* This is plan unit 3 of `young-crane-9546`, and unit 1 (the live walk)
was attempted first as the rung requires — see `## Method`.

## Method

**The live walk, attempted first.** `CADEX_MODEL=claude-opus-5 ./cadex walk
--project ot4-quill --out … --resume`. **The provider did not refuse** —
`sleepy-mesa-0821`'s bet is confirmed live, the block was one model. The turn
ran (92.8 s), read the assembly, and answered. It failed at exit 3 for a
reason that is mine, not the tree's: my prompt asked it to review a *swing
arm*, and `ot4-quill` has none — housing and quill only. The turn correctly
refused to invent one, wrote `docs/swept-envelope.md` recording the swept-head
envelope and two follow-ups, and offered no script, which is what exit 3
means. `agent.json` kept `claude-opus-5`. **A walk with a prompt naming a part
the project does not have is not evidence about the walk**; the next attempt
needs a prompt read off the project's own `PROGRESS.md`.

**Then the unit, measured before it was written.** A probe cut *every*
candidate on the live `ot4-swing2` snapshot and tabulated per-object status.
Two findings, and the second was not in the bet:

1. Ranking by objects cut is right — `coverage` counts bounds, and a plane can
   cross a box and cut nothing of it.
2. **Ranking the eight candidates could not have reached the arm, because the
   arm's planes were not among the eight.** `MAX_DERIVED_CANDIDATES = 8`
   truncated by that same coverage proxy; the base plate and mount cluster
   filled all eight places, and 12.75 / 13.4 / 14.525 / 18.4 mm — the four
   planes that cut `cmp_swing_arm` — were never evaluated.

So: cut every candidate, rank by `objects_cut` with an available cut beating
an unavailable one and the bounds order demoted to a tiebreak; keep every
object's centre unconditionally and apply the work bound (now 48) to the
sibling planes only. One contour pass measured 4.3 ms over 13,432 triangles,
so a ten-object rig's whole sweep is under 0.1 s.

Two regressions, both failing on the old source: three two-lobed rings and a
post sharing the best-coverage plane that passes through all three gaps and
cuts the post alone; and the `ot4-swing2` shape asserting the arm's own planes
are candidates at all — and that the best drawing still omits it.

## Result

**The fix landed and the bet's predicted outcome did not.** Re-measured live
on both rigs through the walk's own `derived_section`:

| Rig | Objects | Candidates cut | Chosen | Objects cut | Before |
|---|---:|---:|---:|---:|---|
| `ot4-swing2` | 10 | 20 (was 8) | XZ −9.2 mm | **6 of 10** | 6, same plane |
| `ot4-carriage` | 2 | 5 | XZ 0.0 mm | **2 of 2** | 2, same plane |

`cmp_swing_arm` is **still `empty`**, and now for a reason that is a fact
about the mechanism rather than a defect in the eye: the arm and its pinch
fastener sit at y 10.9–20.9 mm, the mount cluster at −12.1–8.9 mm, and the
only planes reaching the arm (13.4 mm cuts 5, with the pinch bolt and nut)
reach neither mount nut nor bolt. **One XZ plane through that mechanism does
not exist.** The premise that a good enough derivation would find one is what
did not survive contact — the same shape of finding as `dry-rain-0489`'s.

What the run gets instead is that stated rather than hidden: the summary
carries `objects_cut` and the SVG label reads `6/10 objects cut` beside the
status. `ok` alone told a reviewing agent that four of ten parts were missing
from the page by saying nothing at all; asking for the missing one is now
`--offset-mm 13.4` away, and knowing to ask is the whole of it. `ot4-carriage`
is the control: 5 candidates, every one cuts both parts, nothing changed.

**Still missing before `damp-moon-9297` can be ticked**, and one of them is
new from this pass: `cadex section` defaults `--offset-mm` to 0.0
(`__main__.py:213`), so **only the walk ever derives an offset** — a person or
agent calling the section eye by hand gets the constant, which is the failure
ADR-267 set out to end. Making `--offset-mm` optional and derived-by-default
is the obvious next unit and was out of this one's declared scope. Beyond it:
the assembly inventory with catalog ids, and clearance/intersection naming the
offending pairs, are the two review calls still unbuilt.

Gate: `pixi run python -m pytest cli/tests` — **265 passed** (263 before, +2
new), 3 m 42 s. `cli/` only; no op, no protocol change, no engine or `shell/`
diff, so no build and no `pixi run gate` were required. Probe scripts were
written to `/tmp` and no probe output is committed.

The unreconciled tail is 2 nodes after this one; not fat.

Dispatch closed: 1 unit — the derived section ranks by objects actually cut and keeps every object's own plane (ADR-273); live re-measure says the swing arm is unreachable by any single XZ plane, so the drawing now says `6/10 objects cut` instead of `ok`.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 3b04e535ebc150ffa46602c95ae765bc616d82c2

## State Impact

- target: damp-moon-9297 — The section-view review call now derives its plane by cutting every candidate and ranking on objects actually cut, never dropping an object's own centre plane (ADR-273). Live: ot4-swing2 20 candidates, XZ -9.2 mm, 6 of 10 objects cut; ot4-carriage 5 candidates, XZ 0.0 mm, 2 of 2. cmp_swing_arm remains uncut because no single XZ plane reaches both the arm cluster (y 10.9-20.9) and the mount cluster (y -12.1-8.9); the summary and SVG label now carry objects_cut so the omission is legible. Newly known gap: cadex section defaults --offset-mm to 0.0, so only the walk derives.
- target: chilly-union-8972 — cli/cadex_cli/section.py: derived_section cuts every candidate and returns max by (available, objects_cut, -index); offset_candidates keeps every object's centre plane and applies MAX_DERIVED_CANDIDATES (8 -> 48) to siblings only; section_snapshot publishes objects_cut and the SVG label carries it. 265 CLI tests pass, +2 regressions failing on the old source. docs/CLI.md and the project-doc scaffold updated in the same commit.
