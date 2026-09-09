---
node_id: 0ad01bbd-e9cc-5e05-8a29-9dcd062b7abd
slug: copper-canyon-0231
title: The derived section met live geometry and lost, then won
created_at: '2026-09-08T22:41:40+00:00'
parents:
- cool-eagle-6400
summary: ''
---
## What

Ran the plan's short-rung unit #2 — a token-free `cadex walk` on `ot4-quill`
with no `--prompt` — to verify ADR-267's derived section in a live
`review.json`. The verification **failed**: `offset_source` was `derived` and
the candidates were ranked as designed, but the chosen plane was Y = 0 and the
quill was still `empty`. Diagnosed the cause, fixed it (ADR-270), and re-ran
the same walk to show the quill cut.

## Why

Charter criterion **"The agent can see its work without a screen"** (state node
`damp-moon-9297`), and behind it **"The walk exists and is tested headlessly"**
(`crisp-reef-5607`). The section eye was the one of the four that had never
been shown to cut the part a run exists to look at. The overseer named this
unit explicitly and the plan's negative knowledge said why it mattered: the
derivation "was verified against *stored* bounds from earlier runs and has
never cut live geometry."

Assumption taken without asking: a failed verification is the unit, not a
reason to stop. The charter says "a failed run names the next unit", and the
named unit here was small enough to close in the same iteration with the
evidence attached, so I closed it rather than handing a one-line defect
forward.

## Method

Reference command, no `--prompt` and no `--set`: seed 0, rollout seed 7, CPU
5 iterations x 16 environments, trainer timeout 600 s, leg timeout 120 s, fresh
`--out` and `--name`, under an external 0.2 s tree-RSS watchdog at 2.9 GB /
850 s that also hashes every prior run file before and after.

1. `runs/derived-section-41`. Exit 0, 23.821580 s, peak tree RSS
   1,980,588,032 bytes, 156 prior run files byte-unchanged. `review.json`:
   `offset_source: derived`, `offset_candidates_mm: [-21.2, 0.0]`,
   `offset_mm: 0.0`, `housing_component` ok with 1 loop, **`quill_component`
   empty**.
2. Cut explicitly at the discarded best candidate on the same accepted
   revision `8788efa6...`: `status: unsupported`, reason `plane contacts a
   tessellation vertex/edge/face` on **both** parts. The quill's bounding-box
   centre is its own symmetry plane and its tessellation seams sit exactly on
   it, so the best-coverage candidate is systematically the one `contours`
   refuses — and Y = 0 is supported precisely because it misses the quill.
   ADR-267's "quill 1 -> 2 of 2" was measured against stored bounds with box
   stand-ins, and a box has no seam on its own centre.
3. Probed two nudged planes explicitly: Y = -15.7 and Y = -26.7 both `ok` with
   the quill cut.
4. `cli/cadex_cli/section.py`: `offset_candidates` now offers, for the whole
   geometry and each object, the bounding-box centre **and that centre plus or
   minus a quarter of the same span** — still strictly inside the same bounds
   — ranked by coverage, then centres before siblings, then nearness to the
   overall centre. Eight-candidate bound, `offset_source`,
   `offset_candidates_mm`, artifact path and explicit `--offset-mm` unchanged.
5. Two regressions in `cli/tests/test_section.py`: the live failure rebuilt on
   a tessellated prism whose seams land on its symmetry plane (centre still
   ranked first, still refused, now recovered a quarter span away instead of at
   Y = 0), and the no-candidate-works case rebuilt on a plate lying in the cut
   plane. `cli/tests`: **261 passed** in 229 s.
6. `runs/derived-section-41b`, identical command. Exit 0, 23.830270 s, peak
   1,994,387,456 bytes, 177 prior run files byte-unchanged.

## Result

The section eye cuts the moving part in a live `review.json` for the first
time.

| | walk 41 (before) | walk 41b (after) |
|---|---|---|
| `offset_source` | derived | derived |
| candidates | -21.2, 0.0 | -21.2, -15.7, -21.1, -26.7, 0.0, 21.1 |
| chosen `offset_mm` | 0.0 | **-15.7** |
| housing | ok, 1 loop | ok, **3 loops** (bore walls) |
| quill | **empty** | **ok, 1 loop** |

The other three eyes are unchanged across both walks and against
`runs/stroke60-seed0-33`: render available with front/top/right/iso;
inventory 2 components, 0 catalogued; clearance 1 offending pair, 0 unknown,
1 pair checked, the known 960 mm3 `housing`/`quill` intersection the project's
own ADR-005 explains. Motion 30.078469436328 mm / 0 deg on `quill_component`
over 201 solved frames; rollout total reward 175.487211145051, identical to the
seed-0 reference. **This is coverage in objects cut, not a reward row and not a
fifth seed** — nothing about the mechanism, the policy or the training changed
between the two walks.

Landed: `841a579f` in the repo (section fix, two regressions, `docs/CLI.md`,
ADR-270 which corrects ADR-267's overstated per-mechanism claim) and `4fc0749`
in `ot4-quill` (the `PROGRESS.md` table above, plus the walks' own rows). No
engine, protocol, payload or `shell/` diff. Generated review artifacts stayed
local under the default ignore rules; the numbers are in `PROGRESS.md`, not the
dumps.

**Still missing before `damp-moon-9297` can be ticked:** the derivation is now
right on the one mechanism it was wrong on, but ADR-267's other two
measurements — swing-arm rig 5 -> 6 of 10, carriage 2 -> 2 of 2 — carry the
same box-stand-in provenance and have not been re-measured live. The
second-mechanism walk (`swift-dusk-2951`) is where that would land for free.

Dispatch closed: 1 unit — the live derived section missed the quill, the seam
on its own centre plane was the cause, quarter-span siblings fix it, and the
re-run cuts both parts.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 841a579f4d3ac9dd3f5c622a1aae26a1efb24fb0

## State Impact

- target: damp-moon-9297 — the section eye cuts the moving part in a live review.json for the first time: the derivation's best candidate is systematically a symmetry plane its own tessellation seams sit on, so it was falling back to a supported plane that missed the quill; quarter-span siblings (ADR-270) move the live quill cut from Y=0 (quill empty) to Y=-15.7 (housing 3 loops, quill 1 loop), with render, inventory, clearance, motion and reward unchanged
- target: crisp-reef-5607 — two token-free reference walks of the documented entry point ran end to end on this machine, exit 0 in 23.82/23.83 s, all legs and four review calls, prior run files byte-unchanged (156 and 177), no tokens spent
- target: chilly-union-8972 — cli/cadex_cli/section.py offset_candidates now offers each bounding-box centre plus that centre +/- a quarter of the same span, ranked after the centre it came from; explicit --offset-mm, offset_source, offset_candidates_mm, the eight-candidate bound and the artifact path are unchanged; cli/tests 261 passed
