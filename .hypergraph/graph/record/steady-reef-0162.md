---
node_id: fbc7caa4-6eae-56fa-a0a4-7a0f5955dfd3
slug: steady-reef-0162
title: Audit manufacturer STEP horns and pigtails without qualifying delivery
created_at: '2026-09-07T04:42:18+00:00'
parents:
- narrow-pebble-8020
summary: ''
---
## What

Audited bounded manufacturer STEP horn and pigtail leads; qualified neither.
Added docs/HORN-PIGTAIL-AUDIT.md, PROVENANCE reference, ADR-231 and the
completed audit checkbox in ROADMAP. No product code or vendor assets added.

## Why

Mission 4, red-loom-6298 and brave-stone-9609, following the already-recorded
bet narrow-pebble-8020. The overseer's reconciliation request conflicts with
the explicit prohibition in this contributor dispatch; use the current
checkpoint and bet, do not reconcile or edit state/plan/charter. Reversible
assumption: inspect the DS3218 archive already named in ROADMAP solely for
accessories, not as a new servo search. Stop delivery when qualification fails.

## Method

Read STATE, PLAN, hypergraph contract, actor and record skills, VISION and
relevant provenance/import source. Inspect two horn leads (goBILDA
1900-0025-0104, DS3218 archive) and two cable leads (Pololu #780, same archive).
Manufacturer/seller URLs and missing evidence are enumerated in the audit.
Download goBILDA ZIP outside repo; hash archive/member; inspect AP203 header
and millimetre unit. Installed pixi run FreeCADCmd script uses Part.read,
validity/topology/bounds and analytic cylinder surface measurements, exit 0
with AUDIT58_COMPLETE. No source artifacts redistributed. No GUI or training.
Run licensing pytest and git diff --check; export/check graph before commit.

## Result

Horn: one valid solid, 131 faces, volume 1157.652238130733 mm3; four diameter
4 mm hole axes at X=-8,-16,-24,-32 and Y=0 match published 8 mm pitch and
32 mm hub-to-last-hole reach. Repeated spline surface counts are 25 each at
radii 2.65 and 3.05 mm, not a fit/tolerance qualification. ZIP SHA-256
36435899424a48e917bee3b740446d579744917314cac2a27f07e78d1942a7d9;
STEP SHA-256 c2ae4475cd8f5b333f9dfceee811230a64e9390bb3d73d22ca9cb4acfd218e9f.
Exact mating identity and redistribution evidence unresolved. DS archive
returns HTTP 403 to urllib and empty web-tool output: no bytes/hash/content
claim. Pololu #780 is generic and lists zero resources: no manufacturer STEP.
Raw Part.read is not a script-owned import; existing mesh/.cxpart path does
not establish the conditional delivery premise. Neither category qualifies;
stop conditional delivery and replan before implementation. No broad catalog,
fork-delta or lifecycle closure. The tail now has two unreconciled records.
Licensing: 10 passed, 1 skipped in 0.31 s (staged payload absent from this test
environment); diff check passes. No build or engine/CLI/package/shell suite;
only documentation changes, and no runtime/reopen assurance claimed.
Next: planner should replace the conditional delivery bet, or separately
qualify rights, exact mating evidence and a script-owned route. No follow-up
search or new implementation is authorized by this failed audit alone.
Dispatch closed: 1 unit — manufacturer horn/pigtail audit records qualification blockers.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: ae5a8cb2d63ea78f595d155d37cb68bde4fcf60b

## State Impact

- target: red-loom-6298 — Bounded STEP audit qualifies neither category: goBILDA horn geometry measured but fit and redistribution unresolved; DS archive inaccessible; cable lead generic without CAD; replan conditional delivery.
- target: brave-stone-9609 — No catalog identities added; audit establishes that existing mesh and linked-part imports do not provide the assumed script-owned raw STEP delivery path.
