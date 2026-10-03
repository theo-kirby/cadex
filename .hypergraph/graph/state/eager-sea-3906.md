---
node_id: c7f88b6b-b26e-55c7-9d45-ce6e61e6b710
slug: eager-sea-3906
title: R1. The contract describes the three-part product (orun2)
created_at: '2026-10-03T10:54:46+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Open charter criterion for run orun2: **R1. The contract describes the three-part product.** - Rewrite these for engine + dashboard + agent: - `docs/VISION.md`: the interface section, and the non-goals that named the Rust shell; - `AGENTS.md`, at **no more than half its current 432 lines**; - `README.md`, `docs/ARCHITECTURE.md`, `docs/INTEGRATION.md`; - `docs/ROADMAP.md`: - Phase 12 is superseded by "a desktop app that copies the dashboard"; - Phase 13b's shell half is closed; - Phase 6 is marked historical. - One direction-change ADR states the bet, what it costs, and what would make the owner reverse it. - `docs/BLENDER.md`, `docs/BLENDER-TREE.md` and `docs/BLENDER-RECIPES.md` move to `docs/history/`. - A new `docs/DASHBOARD.md` replaces `docs/REVIEW-DESIGN.md` as the UI spec. It keeps that document's palette, type scale and dark-floor rules. - **The state graph's frontier lists only live work.** Every stale open criterion is superseded through a record that gives its reason: - ot7: F4–F7, F10; - ot10: A5, A7; - orun1: C1; - anything else the shell made moot. `STATE.md` regenerates clean, and `hypergraph check` exits 0. [rec: winter-stone-5109]

**Progress** (commit `1bc9bae0`) [rec: smooth-cedar-5324]:

- **Landed:** the direction-change ADR-500 (the bet, its cost, what would reverse it); `AGENTS.md` rewritten for engine + dashboard + agent at 215 lines (bar 216); VISION's product, interface and non-goals no longer name a Rust shell. Pinned by `test_agents_md_describes_the_three_part_product` [rec: smooth-cedar-5324].
- **Already moved by S1:** `BLENDER-RECIPES.md` [rec: clear-heron-4371], `BLENDER.md` and `BLENDER-TREE.md` [rec: calm-quartz-1493] are in `docs/history/`.
- **Still open:** README / ARCHITECTURE / INTEGRATION framing, the ROADMAP phases (12, 13b, 6), `docs/DASHBOARD.md`, and frontier pruning [rec: smooth-cedar-5324].

Reconcile judgement: `open` → `working` — part of the criterion has landed with a pinning test; several named pieces remain, so it is far from tickable. Declared target: `gap-r1-contract-describes-three-part`; the human owns the charter checkbox [rec: winter-stone-5109].

## Negative knowledge

None yet.

## Provenance

- winter-stone-5109 — orun2 operator-declared charter gap
- smooth-cedar-5324 — ADR-500, AGENTS.md at 215 lines, VISION's interface and non-goals; the rest of R1 still open
- clear-heron-4371 — BLENDER-RECIPES.md moved to docs/history/ with mesh.blender's retirement
- calm-quartz-1493 — BLENDER.md and BLENDER-TREE.md moved to docs/history/ with the shell's deletion
