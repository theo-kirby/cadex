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

**One of the four calls has landed: the assembly inventory with catalog ids (ADR-236, commit 5045847a)** [rec: fair-rose-5950]. `inspect scope="inventory"` walks the pinned accepted attempt's `result.json`: one row per `component_link` output carrying the `source_output` whose geometry it places (the ADR-049 stamp), that output's `catalog` identity where there is one, the solved placement and a six-key `source_facts` block; plus a `catalog_counts` roll-up and the `uncatalogued_sources` a hand-modelled output lands in. `cadex inventory` is the CLI call — no AI, no tokens, no rebuild — and it renders `docs/inventory.md` in the project, the first generated doc under a project's `docs/`, marked as such in its own first line. The output is a project document rather than a JSON blob by decision (ADR-193's shape: what an agent reads on its next visit is the project's documents); the machine-readable form is one `inspect` call away. Real-engine qualified: `cli/tests/test_inventory.py` builds a plate with two catalogued M3 bolts through the real kernel and asserts the rendered doc names `bolt m3x12-socket`, `bolt m3x16-socket` and the hand-modelled `plate` under "Not from the catalog"; `test_inventory_scope.py` pins the stamp, the digest-stillness, the join, the roll-up and two refusals. Engine suite 2070 passed / 52 skipped, CLI 145 passed, packaged lifecycle gate 15 passed; no protocol change, no `shell/` diff [rec: fair-rose-5950]. The library-side half (the `catalog` stamp on library-value outputs) is tracked on `brave-stone-9609`; the subcommand on `chilly-union-8972`.

**Still missing before the criterion can be ticked**: render from named angles, section view through a named plane, and the clearance and intersection check that names the offending pairs — each its own unit — and the walk's review step is not yet wired to any call, including the one that exists [rec: fair-rose-5950]. Reconcile judgement: held at `open`; the impact declares one quarter of the criterion and says so.

## Negative knowledge

- [scope: `inspect scope="inventory"`'s summary reply when the component list outgrows the 1 KiB per-key budget | confidence: high | evidence: fair-rose-5950] The `components` key comes back as a preview stub — the ordinary `inspect` contract — so a reader that trusts the first reply is wrong the moment an assembly has more than a few components. `read_inventory` follows the `/components` page chain instead, and the engine test asserts it. The first draft got this wrong and the test caught it.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- modest-summit-8554 — nt3 operator directive re-seeds the criterion unticked; the four calls sit on the medium rung
- fair-rose-5950 — ADR-236: the assembly inventory with catalog ids as `inspect scope="inventory"` plus `cadex inventory` writing docs/inventory.md; real-engine qualified; three calls and the review-step wiring remain
