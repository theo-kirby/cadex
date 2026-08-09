---
node_id: 13a273a3-2e9a-591e-acf6-b8fefc39d856
slug: idle-lantern-9094
title: Organic modelling and the CAD/mesh interface
created_at: '2026-08-09T15:22:27+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Making the shapes a person actually asks for — a body, a limb, a skin over a mechanism — buildable by the agent and shapeable by the user without a chat turn [rec: solemn-chart-6274].

- **The section cage is the answer to `docs/VISION.md`'s longest-standing open question.** Interactive mesh editing arrives as **engine ops on a declared table**: a shape is a `cage(...)` of superellipse rings the script declares, `part.loft_cage` builds and `set_params(cages=[…])` sets. The shell draws the rings as an edge-only overlay and supplies only the **gesture** — drag a ring, press Apply. Nothing is authored outside the script, the mesh domain gained no editing surface, and no new space type was spent [rec: solemn-chart-6274].
- Blends survive: `part.fillet` bisects a failing edge set and reports what it found; `fuse(blend=…)` names the seam edges because it made them. The wolf welds 25 of 48 seams at 8 mm in 25.04 s against a 13.61 s baseline [rec: solemn-chart-6274].
- Mounts are a declared interface with a static interference check that refuses in cubic millimetres, and swept-volume clearance is held over a whole trace [rec: solemn-chart-6274].
- Lofts now measure how far the surface escapes the sections they were built from and refuse past a quarter of their span — which is how a loft enclosing **4.5× the volume** of a straight loft through its own identical sections was found at all [rec: solemn-chart-6274].
- **The robot wolf (`~/arch/woof.cadex`) is the standing benchmark**, with a per-slice log in `docs/ORGANIC.md` §4. Those project files are live: copy to a scratch directory before building or probing [rec: solemn-chart-6274].

**The standing direction behind this vertical** is that the agent uses every paradigm at its disposal and the user is never asked which one they are in. That is an explicit goal of the author's, approached one step at a time; an earlier attempt to unify the mesh and constraint systems wholesale did not land [rec: kind-ledge-5493].

**O4 (subD) is parked and unscheduled by decision** — and because the cage has been used in anger, what it still cannot do is known and is *not* subdivision: a **curved spine** (the wolf's neck and tail stayed hand-written) and **closing an end**. Both come first [rec: solemn-chart-6274].

## Negative knowledge

- [scope: an earlier mesh/constraint unification attempt | confidence: low | evidence: kind-ledge-5493] The author recalls trying to unify the two paradigms wholesale, possibly on a throwaway branch, and it did not land as a system. No commit range is identified and this is memory only — do not treat it as a bounded prior attempt.
- [scope: the section cage | confidence: high | evidence: solemn-chart-6274] The cage is straight and open-ended. It cannot express a curved spine or close an end, which is why the wolf's neck and tail stayed hand-written. Neither limitation is subdivision, so O4 would not fix them.
- [scope: building against ~/arch projects | confidence: high | evidence: solemn-chart-6274] The benchmark projects under ~/arch are live files. Copy to a scratch directory before building or probing, drive rebuilds through the test_project_rebuild driver rather than hand-editing script.py, and back the script up first — a refused write_script silently restores the last accepted one.

## Provenance

- solemn-chart-6274 — the whole O0-O3b arc, the wolf benchmark and what O4 is parked behind
- kind-ledge-5493 — the standing one-paradigm goal and the earlier unification attempt that did not land
