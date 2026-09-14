---
node_id: 846d7bc5-0497-5d13-a70b-dbc2c6f2da43
slug: winter-key-1482
title: F2. Fit intent is declared and checked
created_at: '2026-09-14T17:28:04+00:00'
parents:
- mild-ledge-7157
summary: ''
---
Status: open

## Current

Charter criterion: **F2. Fit intent is declared and checked.** The script API declares intended contact and intended clearance, with a minimum, between named components. The checker reports four things: any overlap on any pair, a declared contact that is not touching within tolerance, a declared clearance below its minimum, and an undeclared pair closer than the default minimum. World geometry in a design, a floor or bench plane, is reported as its own failure. Nothing is refused at acceptance. Evidence: engine tests on fixtures that reproduce Heron's three ot6 defects, each reported with the right pair and number; `docs/XSCRIPT.md` documents the declarations. Declared target `gap-f2-fit-intent-declared-checked`; a record may say "ticks F2" when its evidence exists, and the human owns the checkbox edit [rec: kind-dusk-1609].

The three ot6 defects the fixtures must reproduce, from Heron's design half (`civic-creek-8215`): a floor `assembly.collision("plane")` on the base (world geometry in a design), 248.2016 mm³ of servo-tab/cheek common volume, and a horn left 0.2 mm from its link. A failing fit is reported, never refused: existing scripts keep building and accepting, and old projects keep opening — the charter's standing constraint, and a reason to keep the change out of the acceptance gate. [rec: kind-dusk-1609]

Reconcile judgement: `open` — declared by the ot7 directive with no evidence yet; flips to `working` only when a record carries the criterion's evidence, on the reading ot5 and ot6 used (evidenced pending the owner's tick) [rec: kind-dusk-1609].

## Negative knowledge

None yet.

## Provenance

- kind-dusk-1609 — the ot7 directive (ADR-341) declared this criterion as gap `gap-f2-fit-intent-declared-checked`
