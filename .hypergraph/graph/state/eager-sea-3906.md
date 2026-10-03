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

**Every named R1 item now has evidence; the checkbox is the owner's.** [rec: light-path-5130]

- **ADR, AGENTS.md, VISION** (commit `1bc9bae0`): direction-change ADR-500 (the bet, its cost, what would reverse it); `AGENTS.md` at 215 lines (bar 216); VISION's product, interface and non-goals no longer name a Rust shell. Pinned by `test_agents_md_describes_the_three_part_product` [rec: smooth-cedar-5324].
- **README, ARCHITECTURE §1, INTEGRATION, ROADMAP** (commit `06bdb19a`): framed as engine + dashboard + agent; ROADMAP Phase 12 superseded, Phase 13b's shell half closed, Phase 6 historical. Pinned by `test_readme_architecture_and_integration_describe_the_three_parts` [rec: careful-rain-8917].
- **BLENDER docs** in `docs/history/`: `BLENDER-RECIPES.md` [rec: clear-heron-4371], `BLENDER.md` and `BLENDER-TREE.md` [rec: calm-quartz-1493]; confirmed in place [rec: even-clover-8953].
- **`docs/DASHBOARD.md`** replaces `REVIEW-DESIGN.md` as the UI spec (git mv, ADR-501, commit `f132d3e9`), keeping hierarchy, type scale, dark palette and dark floor; live pointers re-pointed. Pinned by `test_dashboard_md_replaces_review_design_as_the_ui_spec` [rec: even-clover-8953].
- **Frontier pruning**: ot7 F4–F7 and F10, ot10 A5 and A7, and orun1 C1 superseded, each with its reason; the shell-era phrasing in the training and roadmap nodes dropped [rec: light-path-5130]. `STATE.md` regenerates and `hypergraph check` is run by this reconcile.

Reconcile judgement: status stays `working`, not ticked — every named piece is evidenced, but the human owns the charter checkbox [rec: light-path-5130]. Declared target: `gap-r1-contract-describes-three-part` [rec: winter-stone-5109].

## Negative knowledge

None yet.

## Provenance

- winter-stone-5109 — orun2 operator-declared charter gap
- smooth-cedar-5324 — ADR-500, AGENTS.md at 215 lines, VISION's interface and non-goals; the rest of R1 still open
- clear-heron-4371 — BLENDER-RECIPES.md moved to docs/history/ with mesh.blender's retirement
- calm-quartz-1493 — BLENDER.md and BLENDER-TREE.md moved to docs/history/ with the shell's deletion
- careful-rain-8917 — README, ARCHITECTURE, INTEGRATION and ROADMAP describe the three parts (06bdb19a)
- even-clover-8953 — docs/DASHBOARD.md replaces REVIEW-DESIGN.md (ADR-501, f132d3e9)
- light-path-5130 — frontier pruned: ot7/ot10/orun1 stale criteria superseded; the last R1 piece
