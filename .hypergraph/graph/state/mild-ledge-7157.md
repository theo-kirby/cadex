---
node_id: 95ccf09c-f764-594c-87cf-67123dc9e882
slug: mild-ledge-7157
title: The agent designs it right — the ot7 charter (ADR-341)
created_at: '2026-09-14T17:27:54+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

**F4–F7 and F10 done acceptance remain open.** The closing report consolidates all five refused provider calls and distinguishes implemented checks from unproven agent outcomes [rec: windy-otter-5423]. Iteration 37 could not reconcile because its contributor dispatch explicitly prohibited state/view writes; it retained that conflict as a record-only dead end and produced no new design, fit or smoke evidence [rec: hollow-comet-5408]. Reconcile judgement: preserve that dispatch restriction as historical context; this explicitly authorized maintainer pass folds its pending impact without changing any criterion's status [rec: hollow-comet-5408].

**Owner-directed work for run `ot7` (ADR-341): make the product agent design mechanisms that fit, on its own [rec: kind-dusk-1609].** It replaces the ot6 charter (ADR-328, `round-sun-8398`), whose D1, D2 and D4–D10 the owner ticked on 2026-09-14; D3, the rendered look, went to the owner's own manual work and does not carry [rec: nimble-wing-3050]. The measurement it is sized from: ot6 produced three buildable designs, but the product agent did not make them fit by itself — Finch was written by the actor with no model turn, the actor edited Robin's script twice, and Heron's three defects (a floor plane in the design, 248.2 mm³ of servo tab buried in its cheek, a horn left 0.2 mm from its link) were found by a hand-run probe and fed back as hand-written turns while the agent's printed output said the parts fit each time. The cause is in the product, not the model: the engine already measures every part pair's gap and overlap at the solved pose (`_measure_clearance` in `src/Mod/cadex/cadex_assembly_worker.py`), but the agent's tools cannot reach those measurements, its reply carries the script's stdout, its system prompt (`cli/cadex_cli/agent.py`) tells it to verify by printing, and nothing checks fit across a joint's range [rec: kind-dusk-1609].

In priority order [rec: kind-dusk-1609]:

1. **Measured fit in front of the agent.** After every design turn that builds, the reply and tools carry measured clearances and overlaps from the published result; the instructions say a printout is a claim and the measurements are the evidence. [rec: kind-dusk-1609]
2. **A design says what should touch.** Declared intended contacts and clearances between named parts, checked against the geometry. A failing fit is reported, never refused: the design still builds and accepts, and existing projects keep opening. [rec: kind-dusk-1609]
3. **Fit through the motion.** Every joint with declared limits is swept through its range, first contact reported at the value where it happens. [rec: kind-dusk-1609]
4. **Proof the agent uses it, unassisted.** The arm, balancer and biped prompts, in fresh projects, reach designs with no failing fit, no actor edit and no human design feedback, each passing a short smoke rollout. A design that does not get there is a valid measured result. [rec: kind-dusk-1609]

The owner's fixed choices, not open to actor interpretation [rec: kind-dusk-1609]: **the actor never edits a design** — in any `ot7-*` project every change to the script, its parameters or its accepted state comes from a product-agent turn, and when the agent cannot run the actor records the refusal and works on tools, checks or tests; **prompts are frozen** — create prompts and at most three continuation prompts per design are committed under `docs/probes/ot7/prompts/` before the first design turn, a continuation prompt names no part, number or defect, a changed prompt starts a new attempt, and every attempt is reported; **failing fit is reported, never refused**, and old projects keep opening and accepting; **the dashboard and the look are the owner's** — no edits to `cli/cadex_cli/review_static/`, `docs/REVIEW-DESIGN.md`, `docs/review-design/` or the video style, and the operator dashboard service is left alone; **no policy training** — smoke rollouts only, each bounded to five minutes; new test projects live outside the checkout under the operator's cadex-projects directory as `ot7-*`, and the ot6 projects are read-only, worked on as copies. Out of the frontier: printability rules beyond F2, a prompt benchmark beyond the three designs, reward design, print-ready export, catalog expansion beyond what a design needs, inherited-tree removals. Standing rules carry from ot6: committed receipts at most 16 KB and images 200 KB, no secrets, machine-specific absolute paths, private addresses or hostnames; exhaustion policy `report_done`; a reconcile pass every five work iterations or three unreconciled records, with the separate maintainer and planner off and the critic naming the next unit.

The ten done criteria F1–F10 are child state nodes: F1 `wild-horizon-5461`, F2 `winter-key-1482`, F3 `curious-quill-9036`, F4 `polished-forest-0215`, F5 `stormy-aspen-5433`, F6 `narrow-dune-9454`, F7 `rapid-grove-9687`, F8 `honest-ivy-8824`, F9 `eager-summit-3153`, F10 `first-snow-5587`. A record may say "ticks Fn" when its evidence exists; the human owns the checkbox edit. The charter's starting plan runs F5–F7's prompts first (frozen before any design turn), then F1, F2, F3, F8, F4, F5–F7, and F9–F10 last [rec: kind-dusk-1609]. Reconcile judgement: as for ot5 (`crisp-sun-1239`) and ot6 (`round-sun-8398`), the directive declared only the ten criterion targets and this umbrella is the architecturally right parent for them rather than the state root; the quality bar (every check ships with a fixture whose answer is known in advance and a test that fails on the old code; an unassisted-design claim carries prompt digests, turn count, transcript digests, per-turn fit report and smoke result) is the charter's, restated here so a fold can hold a record to it.

## Negative knowledge

None yet.

## Provenance

- kind-dusk-1609 — the ot7 operator directive: the charter (ADR-341) verbatim, the ten criteria F1–F10 declared as gaps
- nimble-wing-3050 — the ot6 owner review this charter follows from: nine criteria ticked, D3 handed to manual work, the next charter's mission named
- windy-otter-5423 — closing report consolidates evidence while F4–F7 and done acceptance stay open
- hollow-comet-5408 — contributor-only dispatch blocked iteration 37 reconciliation; historical restriction folded by the authorized maintainer
