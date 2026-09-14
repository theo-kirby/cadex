---
node_id: 0c71b7d0-970a-5028-a6c9-cd3894e6a386
slug: wild-horizon-5461
title: F1. The agent sees measured fit
created_at: '2026-09-14T17:28:04+00:00'
parents:
- mild-ledge-7157
summary: ''
---
Status: open

## Current

Charter criterion: **F1. The agent sees measured fit.** After every design turn that builds, the tool reply carries a fit summary computed from the published clearance measurements, never from stdout: the check counts and every failing pair by name with its distance and common volume. `clearance` is an inspect scope on the agent's tool surface. The system prompt no longer tells the agent to verify fit by printing. Evidence: `test_project_tool_surface.py` updated with an ADR; a transaction test in which a script prints "no overlap" while its solids overlap receives the overlap in its reply; `docs/CLI.md` updated. Declared target `gap-f1-agent-sees-measured-fit`; a record may say "ticks F1" when its evidence exists, and the human owns the checkbox edit [rec: kind-dusk-1609].

What exists today, as the charter measured it: the engine already measures every part pair's gap and overlap at the solved pose (`_measure_clearance` in `src/Mod/cadex/cadex_assembly_worker.py`), but the agent's tools cannot reach those measurements, its reply carries the script's stdout, and its system prompt (`cli/cadex_cli/agent.py`) tells it to verify by printing. ot6 recorded the consequence three times on Heron: the printout said the parts fit while the retained clearance table said otherwise (`civic-creek-8215`). A change to the agent's tool surface updates `test_project_tool_surface.py` and earns an ADR; prefer extending an existing inspect scope over a new op. [rec: kind-dusk-1609]

Reconcile judgement: `open` — declared by the ot7 directive with no evidence yet; flips to `working` only when a record carries the criterion's evidence, on the reading ot5 and ot6 used (evidenced pending the owner's tick) [rec: kind-dusk-1609].

## Negative knowledge

None yet.

## Provenance

- kind-dusk-1609 — the ot7 directive (ADR-341) declared this criterion as gap `gap-f1-agent-sees-measured-fit`
