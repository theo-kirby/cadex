---
node_id: 846d7bc5-0497-5d13-a70b-dbc2c6f2da43
slug: winter-key-1482
title: F2. Fit intent is declared and checked
created_at: '2026-09-14T17:28:04+00:00'
parents:
- mild-ledge-7157
summary: ''
---
Status: working

## Current

**F2's static fit intent and known-answer evidence are present (ADR-347), pending the owner's checkbox.** `assembly.assembly(contacts=..., clearances=...)` declares named contact pairs and minimum-clearance triples; `assembly.component(world=True)` marks environment solids. Published exact-solid measurements report overlaps, missed contact, insufficient declared/default gaps and unknown measurements. Collision planes, planar CAD faces and explicitly marked world components yield separate world-geometry findings. CLI build replies, clearance reports and API descriptions expose this advisory contract; failing fit still accepts, and accepted identity survives reopen. Legacy calls omit the new definition keys [rec: crisp-ember-0302].

Real-OCCT fixtures reproduce Heron's 248.2 mm³ buried servo tab, 0.2 mm missed horn contact and collision plane, plus rotated planar geometry, touching pairs and declared/default gap failures. `docs/XSCRIPT.md` documents the API; `docs/probes/ot7/FIT-INTENT.md` carries receipts. Engine: 2,117 passed/53 skipped; packaged lifecycle: 16 passed; packaged fit transaction: 1 passed. The full CLI telemetry failure and passing isolated retry remain recorded under F9 [rec: crisp-ember-0302].

Charter criterion: **F2. Fit intent is declared and checked.** The script API declares intended contact and intended clearance, with a minimum, between named components. The checker reports four things: any overlap on any pair, a declared contact that is not touching within tolerance, a declared clearance below its minimum, and an undeclared pair closer than the default minimum. World geometry in a design, a floor or bench plane, is reported as its own failure. Nothing is refused at acceptance. Evidence: engine tests on fixtures that reproduce Heron's three ot6 defects, each reported with the right pair and number; `docs/XSCRIPT.md` documents the declarations. Declared target `gap-f2-fit-intent-declared-checked`; a record may say "ticks F2" when its evidence exists, and the human owns the checkbox edit [rec: kind-dusk-1609].

Reconcile judgement: change `open` to `working` because the declared implementation, fixtures, documentation and advisory acceptance evidence now exist; this does not assert a full-CLI green result or edit the owner's checkbox [rec: crisp-ember-0302].

## Negative knowledge

- [scope: static world-geometry detection | confidence: high | evidence: crisp-ember-0302] A solid bench cannot be distinguished from a printable base by shape alone, so environment solids require `world=True`; grounding alone is not evidence of world geometry. Confidence: high within this API's stated contract. Contact tolerance is 0.001 mm, default gap 0.1 mm and overlap tolerance 1e-6 mm³ [rec: crisp-ember-0302].

## Provenance

- kind-dusk-1609 — ot7 directive declared the F2 criterion
- crisp-ember-0302 — static fit intent, real-kernel fixtures, advisory acceptance/reopen and verification limits
