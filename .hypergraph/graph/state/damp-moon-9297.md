---
node_id: 531acaa2-823d-5218-88ca-dc1043987a63
slug: damp-moon-9297
title: The agent can see its work without a screen
created_at: '2026-09-06T19:18:34+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion: **The agent can see its work without a screen.** One CLI call each, with outputs landing in the project directory: render from named angles, section view through a named plane, list the parts of an assembly with catalog ids, and a clearance and intersection check that names the offending pairs. The lifecycle walk's review step uses them [rec: empty-wolf-3962]. The nt3 operator directive re-seeds the same criterion, unticked, as the second half of this run's frontier ("the lifecycle walk and the eyes it reviews itself with"); its ladder puts the four calls on the medium rung, one CLI call at a time, each wired into the walk's review step as it lands [rec: modest-summit-8554]. Declared target: `gap-agent-can-see-work-without`.

**One of the four calls has landed: the assembly inventory with catalog ids (ADR-236).** `inspect scope="inventory"` joins accepted assembly components to their source outputs, catalog identities, solved placements and source facts, with catalog totals and uncatalogued sources. `cadex inventory` writes the generated project document `docs/inventory.md` without AI or a rebuild. Real-engine assembly tests qualify the inventory; the original engine suite recorded 2070 passed / 52 skipped and the packaged lifecycle gate 15 passed, with no protocol change or `shell/` diff [rec: fair-rose-5950].

**The inventory paging critic rejection is fixed.** The CLI recursively expands nested previews and pages mappings, lists and strings, including catalog totals and uncatalogued sources. Real inspection-pager regressions cover 60 catalog totals, 60 uncatalogued names and oversized component rows, preserving every rendered name, count, pose and volume. The CLI gate recorded 147 passed with no skips; this fix changed only CLI Python and documentation [rec: lawful-ivy-4474].

**Still missing before the criterion can be ticked**: render from named angles, section view through a named plane, and the clearance and intersection check that names the offending pairs — each its own unit — and the walk's review step is not yet wired to any call, including the one that exists [rec: fair-rose-5950]. Reconcile judgement: held at `open`; the impact declares one quarter of the criterion and says so.

## Negative knowledge

- [scope: inventory inspection replies exceeding the 1 KiB per-key budget | confidence: high | evidence: lawful-ivy-4474] Paging only `/components` is insufficient: catalog totals, uncatalogued sources, component rows and nested strings can also be previews. The former reader failed converting `/catalog_counts` to an integer and could lose oversized names; recursive expansion is required and regression-tested.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- modest-summit-8554 — nt3 operator directive re-seeds the criterion unticked; the four calls sit on the medium rung
- fair-rose-5950 — ADR-236: the assembly inventory with catalog ids as `inspect scope="inventory"` plus `cadex inventory` writing docs/inventory.md; real-engine qualified; three calls and the review-step wiring remain
- lawful-ivy-4474 — fixes the inventory paging critic rejection with real inspection-pager regressions; remaining review calls and walk wiring stay open
