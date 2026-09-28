---
node_id: 518f01ca-cf18-5c87-8d99-25a9e0d8d35d
slug: shady-ember-3607
title: 'ot10: hexapod attempt 8 judged 8/21; live document wedged on orphaned Joints groups, leg probe accepted'
created_at: '2026-09-28T11:52:47+00:00'
parents:
- lawful-basin-3006
summary: ''
---
## What
A5 hexapod attempt 8 on the new project `ot10-hexapod-8`. The frozen hexapod prompt ran once with the same argv, `claude-opus-5-5`, `CADEX_EFFORT=medium` and no continuation, launched at revision `070a8c23` (after ADR-428). It was rendered from a `/tmp` copy, judged blind under the frozen A1 procedure (three calls) and published in `docs/probes/ot10/README.md` with a score file, six renders and a contract test (commit `6237ebfd`).

## Why
The critic asked for exactly this unit: hexapod attempt 8 under the same frozen conditions, so that the result measures ADR-428 alone, scored blind and published whether it passes or misses. It serves A5 (`loyal-fountain-8709`). I did what was asked. The critic also asked for a diagnosis from the renders and proxies if T3 or T4 missed. The miss had a different cause, so the diagnosis below is of that cause, and no tool or overlay was changed.

## Method
- Turn: 2026-09-28T11:02:54Z to 11:36:59Z (34 min), exit 0, `ok: true`, accepted revision `b69465f94e40…`, digest `3e3927796084…`.
- `cadex render`: 1 min 13 s in all (38.2 s acquisition, 8.5 s drawing, 172,659 triangles).
- The five look views were drawn with `ot10-notes/look_views.py`, then `runner/judge.py` was run on the hero plus the five views.
- Refusals were counted from the session transcript with `ot10-notes/refusals.py`.
- Scratch notes live outside git, under `~/cadex-projects/ot10-notes/hexapod-8/`.

## Result
**Misses A5 on four counts:**
- The judged total is **8/21**. The medians are T1 1, T2 1, T3 2, T4 1, T5 0, T6 1, T7 2, from calls of 8, 8 and 9.
- T5 is 0.
- The swept fit is incomplete: all 12 joints are unswept.
- The design carries no electronics, no MJCF and no task.

Static fit is clean: 946 pairs, 940 clear, 0 intersections, and one failing row, the floor's advisory world-geometry row. P1 is 0.020, P2 0.097 and P3 is 2. Only `c_tub` declares an appearance role.

**This is not a looks verdict.** The accepted revision is a six-leg probe with a box for a body. The agent's intended design (a pillow hood, a visor face, orange foot tips) was never published.

**Diagnosis:**
- Three full builds hit the 300 CPU-second limit. The first two used superellipse B-spline lofts for the hood and pan.
- After the third kill, every write was refused with `PUBLICATION_UNTAGGED_OBJECT: ['Joints', 'Joints001']`, even a one-box script. Retiring `tray` and `tub` was also refused because foreign objects still reference them.
- The agent had no reset tool, so it stopped and wrote an honest failure report.
- The agent claims that renaming or retiring an assembly output orphans its `Joints` group. That is **unverified**. The source does show that publication creates an untagged `Assembly::JointGroup "Joints"` under each assembly (`CadexScriptedDomainPublication.py` ~885/922), and the ownership lint refuses untagged objects.
- A live document that no script can publish past is a product defect in the engine zone.

**The next unit** reproduces the wedge as a failing regression test, starting from a retired or renamed assembly output and a CPU-killed publish, then fixes it. The fix goes through the packaged gate, before any overlay or prompt change.

What ADR-428 shows here: the legs are curved and narrow towards a ball foot in the side view. The judge's T4 of 1 names the probe's plate body.

A4: none of the four refusal classes recurred. There were 20 refusals in all:
- 3 CPU-limit;
- 7 after the wedge;
- 4 sandbox or source-policy;
- 2 `api.fuse`;
- 2 `edit_script` replacements whose text did not occur once;
- 1 guessed JSON pointer;
- 1 `inspect` refusal.

The full `cli/tests` suite was started at this revision and had not finished when this was recorded. `test_ot10_contract.py` passes 20/20. No engine code changed.

Dispatch closed: 1 unit — hexapod attempt 8 judged 8/21 and published as a miss; the live document wedged on orphaned Joints groups, so the next unit is a regression for that engine defect.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 6237ebfd242bb18301bb1c5e5e7b2b45da98c6cd

## State Impact

- target: loyal-fountain-8709 — hexapod attempt 8 (ot10-hexapod-8) misses A5 at 8/21 with T5 0, incomplete sweep and no electronics, because the live document wedged on PUBLICATION_UNTAGGED_OBJECT ['Joints','Joints001'] after CPU-limit kills; it is not a looks verdict, and the next unit is an engine regression for the wedge
