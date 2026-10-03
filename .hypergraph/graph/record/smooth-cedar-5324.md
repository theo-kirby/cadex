---
node_id: 274a4665-cf08-50aa-8a7e-05a41fb613db
slug: smooth-cedar-5324
title: 'orun2 R1: Cadex is three things — ADR-500, AGENTS.md at 215 lines, VISION interface and non-goals'
created_at: '2026-10-03T13:42:55+00:00'
parents:
- mellow-pine-4848
summary: ''
---
## What

The first R1 unit of orun2: one direction-change ADR (ADR-500, "Cadex is three things: the engine, the dashboard, the agent"), AGENTS.md rewritten for the three-part product at 215 lines (from 353), and `docs/VISION.md`'s product statement, interface section and non-goals rewritten so neither names a Rust shell or a "Blender-class UX". A new test holds all three.

## Why

The critic accepted iteration 8's live-doc sweep (S1 closed) and named R1 next, with exactly these three items: the ADR (the bet, its cost, what would reverse it), AGENTS.md at 216 lines or fewer, and VISION's interface section and Rust-shell non-goals. R1 is the next criterion in the charter's priority order. `docs/DASHBOARD.md` and frontier pruning are left for later R1 units, as the critic said.

**Deviation from the critic's message.** The critic asked this iteration to (a) write iteration 8's missing record, which I did as `mellow-pine-4848`, and (b) then reconcile. I did **not** reconcile. This dispatch's own instructions forbid the reconcile skill and `hypergraph update` in a work iteration, "no exceptions". The loop config (`hypergraph.pressure: 3`) already makes housekeeping the next actor's iteration once three records are unreconciled, and there are now four (`crimson-union-6659`, `calm-quartz-1493`, `mellow-pine-4848` and this one). The tail is fat, and the next iteration should be the reconcile.

## Method

- **ADR-500** (appended to `docs/DECISIONS.md`) supersedes ADR-025's Rust + wgpu + egui shell (Phase 12) and VISION's "Blender-class UX" pillar. It keeps Phase 11 and "OCCT stays".
  - **Cost.** Its cost list cites `docs/probes/orun2/D1-BEFORE.md` and is concrete:
    - hands-on modelling UI dropped, not deferred;
    - no native viewport;
    - no other harness.
  - **Benefit:** 19,446 of 25,633 tracked files (75.9%), a second toolchain, a GPL half, 6,716 LFS objects, ~1.3 GB of library checkout, and a linux build where the documented app was macOS-only.
  - **Reversal conditions:** the owner wanting to model by hand more than occasionally; the dashboard failing to carry review without breaking charter A2; or autonomy no longer being the main mode.
- **AGENTS.md** keeps every rule and drops the history:
  - Organised as: What Cadex is (three numbered parts) → doc index (merged rows) → repo map → commands → change policy → methodology → dynamics invariants → the hypergraph block (verbatim between its markers) → Unattended runs.
  - Dropped prose: the MJC-branch history, the `analysis/` S4 narrative, the long `training/`/`analysis/` repo-map notes and the duplicate setup commands.
  - The "do not start a replacement engine" rule now reads: a replacement engine or a desktop app that copies the dashboard.
- **VISION:**
  - The product is three things.
  - The interface section describes the dashboard as the only UI: the views it serves, light steering through CLI code paths, the non-blocking agent channel, the A2 lightness rule, and no modelling tools.
  - Non-goals: "Two of anything" restated without the Rust shell, plus a new "Hands-on modelling UI" non-goal.
  - The CLI's turn orchestration is restated without the shell.
  - The macOS-notarization-of-a-Rust-app open question is removed.
- **Test:** `cli/tests/test_project_docs.py::test_agents_md_describes_the_three_part_product`.
  - It asserts AGENTS.md ≤ 216 lines and has the three numbered parts.
  - It asserts that neither AGENTS.md nor VISION contains `wgpu`, `egui` or "Blender-class UX".
  - It fails on the previous tree (353 lines, and `wgpu` in both files).

## Result

Commit `1bc9bae0`.

True now: R1 has three of its pieces:

- the direction-change ADR (ADR-500);
- AGENTS.md at 215 lines, under the charter's half-of-432 bar;
- VISION's interface section and non-goals no longer describe a Rust shell.

Both are test-pinned. Suites at this commit:

- `pixi run test-engine`: **2582 passed, 56 skipped**, exit 0.
- `cli/tests` with the GPU hidden: **1294 passed, 1 skipped**, exit 0.

R1 still open. Already done: the three `docs/BLENDER*.md` files are under `docs/history/`.

- `README.md`, `docs/ARCHITECTURE.md` and `docs/INTEGRATION.md` rewritten for the three-part framing.
- ROADMAP: Phase 12 superseded, Phase 13b's shell half closed, Phase 6 historical. The charter forbids hand-editing ROADMAP.md while asking for this; ADR-499 recorded that as an assumption.
- `docs/DASHBOARD.md` replacing REVIEW-DESIGN.md. AGENTS.md and VISION still point at REVIEW-DESIGN.md until it exists.
- Frontier pruning.

Some VISION paragraphs under Scope and Open questions still describe the shell's role historically: the cage-gesture overlay, "no shell diff", and "the shell never learns MuJoCo exists". These are outside this unit, and the DASHBOARD/R1 doc pass should restate them.

Concern: the operator added an "Owner notes" section to `.ouroboros/goal.md` during this iteration, uncommitted in the working tree. This iteration did not stage or edit it. Its decisions bear on later units:

- The live policy session is dropped.
- The blueprint composer is kept as a headless tool, scheduled after D2's write paths. It counts as a ported W1 row.
- `collision_view`'s agent half (the t=0 contact report) is kept.
- Agent timeout and memory budgets move to project config, with CLI overrides.

VISION's new "interactive blueprint editor" non-goal is consistent with this, because the composer is not an editor.

Reconcile is due: four unreconciled records.

Dispatch closed: 1 unit — R1 contract rewrite part 1: ADR-500 direction change, AGENTS.md cut to 215 lines, VISION interface and non-goals, test-pinned

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 1bc9bae0b1a3e426c546517a058a8cb4090f7ff0

## State Impact

- target: eager-sea-3906 — three R1 pieces landed (commit 1bc9bae0): direction-change ADR-500 (bet, cost, reversal); AGENTS.md rewritten for engine+dashboard+agent at 215 lines (bar 216); VISION's product, interface and non-goals no longer name a Rust shell. Pinned by test_agents_md_describes_the_three_part_product. Open: README/ARCHITECTURE/INTEGRATION framing, ROADMAP phases, DASHBOARD.md, frontier pruning
- target: shy-crane-2573 — ADR-500 supersedes the Rust shell (Phase 12); a desktop app, if ever built, copies the dashboard
