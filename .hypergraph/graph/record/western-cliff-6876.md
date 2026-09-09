---
node_id: 8ac8d812-b588-5534-bf6c-cedd8a0bc2c5
slug: western-cliff-6876
title: The walk's section cuts where the geometry is
created_at: '2026-09-08T21:52:14+00:00'
parents:
- steady-chart-0544
summary: ''
---
## What

The walk's review section leg no longer cuts at a literal world XZ plane at
Y = 3.125 mm. `cli/cadex_cli/section.py` gains `offset_candidates` and
`derived_section`: the candidates are each accepted object's bounding-box
centre on the cut axis plus the whole geometry's, ordered by how many objects'
bounds the plane crosses, then by nearness to the overall centre, then by
value, capped at eight; `derived_section` writes the first candidate whose cut
is supported and falls back to the best candidate's own refusal when none is.
`write_section(offset=None)` selects that path, so the walk asks for a derived
cut and `cadex section --plane/--offset-mm` is unchanged, now recording
`offset_source: explicit`. `review.json` carries the chosen `offset_mm`,
`offset_source` and the ordered `offset_candidates_mm`, and the artifact
directory becomes `review/section/<accepted-revision>/XZ-<derived-offset>/`.
ADR-267, the ROADMAP line for the section review, `docs/CLI.md` (§ walk review
contract, the shared-mode artifact table, the `cadex section` block and the
historical ot4-quill measurement), `docs/MUJOCO.md` §7c and the project-doc
scaffold in `cli/cadex_cli/project_docs.py` are updated in the same commit,
with the scaffold's two pins in `cli/tests/test_project_docs.py` moved with it.

## Why

Charter criterion **"The agent can see its work without a screen"**
(`damp-moon-9297`), mission item 6: four review calls, one of which was
reporting nothing on a mechanism the constant was not tuned to. On
`ot4-quill` the housing spans Y −42.2…42.2 and the quill Y −32.2…−10.2, so the
3.125 mm plane cut the housing, returned `empty` for the quill, and reported
`status: ok` overall — in all six recorded section summaries in that project.
An eye that silently omits the moving part is worse than one that refuses.

This was the planner's short unit 2 and its declared always-dispatchable
fallback. Short unit 1 (the live provider iterate) was not taken: it is a
long, provider-dependent design turn, and the overseer's instruction was to
take a frontier leg rather than hold. The overseer's first item, the maintainer
reconcile, is forbidden to a work iteration, so it is left for the maintainer
pass; its second item was the "three modes" criterion's unspent legs, and
`witty-spark-2613` records both of those legs as already shipped (ADR-200/255
for the scripted remote handoff, ADR-201 for the GUI-attached mode doc), so
this unit takes the next open charter eye instead.

Assumption written down rather than asked: bounds coverage orders candidates,
it does not promise a contour — a plane can cross an object's bounds and cut a
cavity — so the per-object statuses stay the answer and the ordering is only a
heuristic for where to look first.

## Method

Measured the defect from the recorded runs first (`review/section/*/XZ-3.125/
summary.json` in `ot4-quill`, `ot4-swing2` and `ot4-carriage`), then simulated
the derivation against those same stored bounds before writing it: quill 1 → 2
of 2 objects crossed (offset −21.2 mm), swing-arm rig 5 → 6 of 10 (−9.2 mm),
carriage 2 → 2 (3.125 → 0 mm). No mechanism loses coverage.

Three new regressions in `cli/tests/test_section.py`, all over synthetic
quill-shaped geometry with no engine needed: the old constant reporting `ok`
while the moving part is `empty` against the derived plane cutting both; a
candidate that contacts its own tessellation being skipped for the next; and a
geometry where no candidate is supported reporting the refusal rather than a
false success. `cli/tests/test_walk.py` now asserts the walk's cut is
`offset_source: derived` at `offset_candidates(render_summary, "XZ")[0]`
rather than at 3.125.

## Result

The full CLI gate passed after the change: `pixi run python -m pytest cli/tests`
**256 passed, 0 skipped, 0 failed** in 229.34 s. Landed as commit `749be272`
with ADR-267 and the ROADMAP line in the same commit.

Coverage numbers above are computed from committed run summaries, not from a
fresh walk; a fresh headless walk was not run this iteration. The committed
`docs/probes/` baselines naming `XZ-3.125` are historical measurements and are
left as written. No new flag, op, protocol change, engine or `shell/` diff;
LGPL CLI zone and docs only.

Still missing before `damp-moon-9297` can be ticked: the four eyes have not
been re-exercised together on a real mechanism since this change — the next
headless walk is what shows the derived plane in a live `review.json`.

Dispatch closed: 1 unit — the walk's review section offset is derived from the accepted bounds instead of a literal 3.125 mm, with three regressions and the CLI gate at 256 passed.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 749be272d0812773965f98c10746bf2250491eb9

## State Impact

- target: damp-moon-9297 — The walk's section eye no longer cuts at a literal XZ Y=3.125 mm: the offset is derived from the accepted snapshot's own per-object bounds (each object's bbox centre plus the whole geometry's, ordered by objects' bounds crossed then nearness to the overall centre, first supported cut wins, at most eight candidates), reported through offset_mm / offset_source / offset_candidates_mm, with artifacts under review/section/<rev>/XZ-<derived-offset>/. On the three recorded mechanisms coverage rises and never falls (quill 1->2 of 2, swing-arm rig 5->6 of 10, carriage 2->2 at 0 mm). cadex section --plane/--offset-mm is unchanged and records offset_source: explicit. ADR-267, commit 749be272, cli/tests 256 passed 0 skipped. Not yet exercised in a fresh live walk.
- target: crisp-reef-5607 — The walk's review leg changes shape slightly: its section artifact directory is now XZ-<derived-offset> rather than XZ-3.125, and the project-doc scaffold and docs/CLI.md shared-mode artifact table say so; the leg's failure semantics, snapshot sharing and revision checks are unchanged.
