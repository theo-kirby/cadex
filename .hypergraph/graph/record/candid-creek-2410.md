---
node_id: ddc7b07e-a8df-5665-a840-04c030518df7
slug: candid-creek-2410
title: Reconcile the harness, drawings, library and native recipe batch
created_at: '2026-09-05T21:41:48+00:00'
parents:
- smooth-lantern-7016
- windy-sage-5295
- simple-bramble-8616
summary: ''
---
## What

Reconciled the 17 records outstanding after the 2026-08-29 high-water mark into the current-state projection on main, at the owner's request. Added the parts-library state node under the engine and folded the ADR-174 through ADR-185 batch, including the demo licensing repair.

## Why

The publication snapshot explicitly left reconciliation pending. STATE.md still described mesh_agent as an add-on and omitted the shipped harnesses, drawing editor, library and native geometry runtime.

## Method

Read the reconciliation and record skills, graph configuration, pending records and affected state bodies. Enumerated outstanding records by graph reachability with hypergraph hwm, grouped impacts by target, and wrote complete bodies through hypergraph update with captured --expect hashes and --reconcile. Superseding drawing and model-selection records were folded into final behavior, retaining their provenance. Derived adjacent corrections update the root's application-code description and the CLI's recorded default/runtime requirements. Product and source files were not changed; product test results in state are attributed to the original records, not rerun here.

## Result

Six existing component nodes were updated, plus the root reconciliation marker, and brave-stone-9609 was created for the parts library. L0/L1 are working while L2/L3 and unsourced interfaces remain open. The existing file-lifecycle, gait-scale and inherited-reduction frontier remains unresolved. Native recipe platform bounds and unperformed real OAuth validation remain explicit. The snapshot, brainstorming and local-install records have no product state impact and are covered by the new mark. Regenerate STATE.md and validate the final exports with hypergraph sync/check before committing this pass.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 35b5cad87a6c84caadd461a2920c438b7b925417

## State Impact

none: Projection maintenance only; product claims and frontier changes derive from the folded feature records.
