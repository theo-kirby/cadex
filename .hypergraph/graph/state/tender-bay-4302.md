---
node_id: 18c6c5ac-55ee-5955-9b90-cd5968e9f4a6
slug: tender-bay-4302
title: G2. The arm's catalog-provenance gap has a bounded measured outcome
created_at: '2026-09-20T18:48:22+00:00'
parents:
- ancient-vine-9908
summary: ''
---
Status: working

## Current

**G2's success bar is met and measured, on the initial create prompt alone, with all three continuations unspent [rec: winter-creek-7660].** In a new empty project `ot8-heron-b`, the frozen `heron.create.prompt.txt` — byte-identical to ot7's and so to ot6's — was dispatched against today's product on `claude-opus-5`. Turn 0 **completed on its own** (exit 0, 3,015 s, `actor_design_edits: 0`, one slot spent), and the accepted result measures:

- **static fit pass** — 0 failing of 105 pairs; 105 clear, 0 intersection, 0 below clearance, 0 unknown [rec: winter-creek-7660].
- **swept fit pass** — coverage complete, 2 of 2 joints at 10° steps, 0 skipped, 0 failing [rec: winter-creek-7660].
- **attachments** — 12 pairs, verdict touching, 0 reported [rec: winter-creek-7660].
- **inventory** — 15 components; `servo/mg90s` ×2, `servo_horn/mg90s-single_arm` ×2, `bearing/mr128` ×2, `bolt/m2x6-socket` ×4, `bolt/m2x16-socket` ×2; `derived_catalog_sources` **empty**; `uncatalogued_sources` exactly the three printed parts `base`, `upper_arm`, `forearm` [rec: winter-creek-7660].
- **smoke pass** — ordinary `cadex smoke`, `failing: []`, all four checks (finite, penetration, support, termination), hold mode, 1.0 s, 51 samples, MuJoCo 3.10.0 [rec: winter-creek-7660].

Accepted identity: revision `957044ae…` = working revision, digest `9cec3cc6…`. The inventory's revision and the smoke's accepted revision are the same `957044ae…`, so fit, inventory and smoke are three readings of one pin. Receipt: `docs/probes/ot8/retained/g2-heron-create.json` (5,520 bytes), commit `17fe466e` [rec: winter-creek-7660].

**The ot7 comparison, which is the point of the criterion [rec: winter-creek-7660].** `ot7-heron-c`'s accepted pin (`58ff41b4…`) carries `catalog_counts` of bearings and bolts *only* — no servo row and no servo_horn row at all — and lists `servo_shoulder_solid`, `servo_elbow_solid`, `horn_shoulder_solid` and `horn_elbow_solid` among its `uncatalogued_sources`. Same component count, same ask, four purchased parts modelled by hand. ot8's four are catalog parts. **The gap ot7 left is closed by the product, not by a repair prompt and not by hand**: continuations 1, 2 and 3 are unspent and stay unspent under the freeze. (ot7's receipts predate the `derived_catalog_sources` field and read `null` there; the comparison rests on `catalog_counts` and `uncatalogued_sources`, which both runs carry.)

**`ot8-heron` — no suffix — is a closed void project, not a result [rec: winter-creek-7660].** A first dispatch was made on it at 19:43Z with the five-hour window at 20 %, and a session limit (429) cut it off mid-turn after 2,867 s and 51 model messages. The collector classified it **void** under ADR-355: no slot spent, project closed, retry named `ot8-heron-b`. Its evidence is retained and cited, and it may never be reported as a design failure or a success in either direction. The live G2 project is `ot8-heron-b`, dispatched after a re-probe read the window reset to 1 % (seven-day 22 %).

*Reconcile judgement*: `working` rather than `open`, on the ot7 precedent that a criterion whose evidence exists is `working` while the human owns the checkbox. Every clause of G2's bar has a measurement behind it and none is short [rec: winter-creek-7660].

## Negative knowledge

- [scope: a full design-create dispatch begun with the five-hour Opus window already well spent | confidence: high | evidence: winter-creek-7660] It does not finish. The void `ot8-heron` call was dispatched at 20 % and consumed the rest of the window before the turn ended; the successful `ot8-heron-b` call started at 1 % and completed in 3,015 s. The actor session shares that window with the product call, so the actor staying quiet while a turn runs is part of the dispatch, not a courtesy. A no-slot diagnosis runs fine on a tight window; a design dispatch should start near the bottom of a fresh one.

## Provenance

- keen-stone-1720 — the criterion as the ot8 charter declares it
- humble-fox-6370 — the ot7 baseline it is measured against: two modified servos and two modified horns
- winter-creek-7660 — G2 measured end to end on `ot8-heron-b`: zero failing static and swept fit, all four purchased parts catalogued, zero actor design edits, a passing ordinary smoke on the accepted pin, three continuations unspent, and `ot8-heron` closed void under ADR-355
