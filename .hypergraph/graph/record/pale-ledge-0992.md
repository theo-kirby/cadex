---
node_id: 2067d493-8fad-5c68-b012-3e4d95093aff
slug: pale-ledge-0992
title: 'ot10: ADR-421 fingerprint drops integrated measures; biped replay scores 15/21 and meets the full A5 bar'
created_at: '2026-09-28T00:32:18+00:00'
parents:
- wise-walrus-6002
summary: ''
---
## What
Fixed the engine defect that kept `ot10-biped-1` from reopening (ADR-421, commit `a526a292`), then replayed the biped: rendered it through the product, blind-scored it under the frozen procedure, and published it. **It meets every item of the frozen A5 bar: judged 15/21.** It is the first A5 design in the run to do so.

## Why
This is the unit the critic's message asked for, taken in full:
- drop per-face areas and total area from `shape_geometry_fingerprint`;
- bump the digest schema so an old stored digest is re-measured, not refused;
- add a regression that fails today;
- stop a failed restore from writing `latest_candidate` as accepted, with its own test;
- ADR and the packaged gate;
- replay, render, blind score, publish.

**One deviation, which the measurement forced.** With areas alone dropped, the reopen still refused. Diffing the three retained attempts under v2 found that two 0.4π mm fillet arcs on `src_hood` also drift in length: 1.256637061435912 against 1.2566370614359201. Edge length is an integral too, so v2 drops edge lengths as well. v2 was never published, so this needs no v3. P2 floor and the hexapod/quadruped reruns were left for later, as asked.

## Method
- `CadexGeometryDigest.py`: `GEOMETRY_DIGEST_SCHEMA` → `cadex-project-geometry-digest-v2`. The fingerprint keeps the counts, the exact vertex set and the bounding box. It drops edge lengths, face areas and the total area.
- `cadexd.py`:
  - a learned `accepted_geometry` now stores its `schema`;
  - `_remembered_geometry` ignores an entry with any other schema, or none, so the accepted attempt is re-measured;
  - the restore rollback write puts back the project's own `latest_candidate`.
- Tests. Each of these fails on the previous source and passes on the new one:
  - `test_geometry_digest.py`: the measured area and arc pairs;
  - a remembered digest under v1, and one with no schema (parametrised);
  - the "face grew"/"edge grew" params became count changes;
  - `test_cadexd_lifecycle.py::test_a_changed_script_is_still_refused_at_the_restore_pass` now asserts `latest_candidate` is unchanged (real FreeCADCmd; failed before, passes after);
  - the offset test asserts the stored schema.
- Docs: `docs/INTEGRATION.md` restore paragraph; ADR-421 in `docs/DECISIONS.md`.
- Replay:
  - the notes' `pipeline.sh`, unchanged: `cadex render`, the five `look` views, then `docs/probes/ot10/runner/judge.py` (3 calls, claude-opus-5-5, the frozen rubric sha `1c81caa2…`);
  - the refused receipts were kept beside it as `*-refused.*`, outside git;
  - the design was untouched.

## Result
- **ot10-biped-1 meets the A5 bar on every item:**
  - judged median 15/21: T1 2, T2 3, T3 3, T4 1, T5 2, T6 2, T7 2; calls were 15, 15 and 16;
  - lowest trait 1, above hex3's 2;
  - P1 0.002 (493/230,650), P2 0.068, P3 3;
  - static fit clean; swept fit complete and passing, 6/6;
  - electronics carried.
  - Published in `docs/probes/ot10/README.md` with six PNGs (all ≤ 117 KB) and `ot10-biped-1-score.json`.
- Render: 3 min 31 s in total, of which 101.2 s was acquisition and 7.2 s drawing (2.4 s for the hero), at 91,619 triangles.
- **Evidence:**
  - engine suite 2,236 passed, 53 skipped, at the final revision;
  - packaged lifecycle gate 23 passed, rebuilt and restaged at the final revision;
  - CLI suite 999 passed, 1 skipped. That run was on the areas-only intermediate; the only change since is engine-side (dropping edge lengths).
  - `test_ot10_contract.py` 13 passed.
- **Weakest traits:**
  - T4 = 1 in all three calls: flat link plates and box servo covers. It is the same weakest trait as the quadruped, so it is the obvious overlay/API lever.
  - T7 = 2: call 1 names no contact shadow, a high camera and jagged top-view edges. The top view is a `look` view, not the hero.
- **Concerns for the next iteration:**
  - `cadex render` issues `rebuild`, which re-accepts. On a design whose bytes drift, that moves `accepted_digest` (10e2fd59 → e3b08e38 in render, then ec926a44 after `look`) with the revision unchanged. This is existing behaviour, not this unit's, but scoring now commits a new digest into the project.
  - The project's `script.json` is left modified by the `look` step. That is the product's own state, and it was not reverted.
  - A5 still needs a hexapod and a quadruped that pass: both reruns with the sweep on are open. So is the P2 `floor` exclusion decision, which is in this biped's measured set too; excluding it can only lower the sharp share, so the biped's P2 result does not depend on it.
  - The unreconciled tail is now 3 nodes, so a reconcile is due.

Dispatch closed: 1 unit — ADR-421 geometry fingerprint drops integrated measures (areas and arc lengths) plus the latest_candidate restore fix; the ot10-biped-1 replay renders and scores 15/21, meeting the full A5 bar

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: a526a29271954ecf8f79dfbf2e8ed77957aa3798

## State Impact

- target: loyal-fountain-8709 — ot10-biped-1 meets every A5 bar item: judged 15/21 (T4 weakest at 1), P1 0.002, P2 0.068, P3 3, complete passing swept fit; hexapod and quadruped still need passing designs
- target: forest-wind-0342 — ADR-421: geometry digest v2 hashes only counts, vertex set, bounds and recipe (areas and edge lengths drift); v1-learned digests re-measured; a refused restore keeps latest_candidate
