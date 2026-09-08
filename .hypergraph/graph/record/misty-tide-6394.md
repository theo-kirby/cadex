---
node_id: e21163b6-e033-528f-a063-b3a9e9e4b030
slug: misty-tide-6394
title: Teach purchased hardware placement in lifecycle design guidance
created_at: '2026-09-08T03:54:45+00:00'
parents:
- modest-valley-3313
summary: ''
---
## What

Teach hardware placement in the CLI design instructions used by `cadex walk --prompt` and the new-project ARCHITECTURE.md scaffold: publish catalog bodies, place purchased instances as separate assembly components, keep them separate from printed solids, and allow transformed catalog bodies as clearance cutters without implying another purchase. Review the script alongside placed inventory. Update docs/CLI.md, append ADR-243's guidance follow-up, and tick the landed ROADMAP item. Extend the existing scaffold contract test to require delivery of each fact in both scaffold and agent overlay.

## Why

Follows modest-valley-3313 rank 1 and advances missions 2 and 6, charter criteria **The walk exists and is tested headlessly** and **The agent can see its work without a screen**. Their baseline evidence remains working. Inventory counts placed instances; it cannot establish catalog hardware consumed by boolean operations. Guidance is the smallest reversible response after the unsupported tally removal, without another registry, validator, API or dependency. Assumption: the existing shared CLI overlay is the correct design-instruction boundary; the walk delegates its design turns there. Existing project documents remain project-owned and are not overwritten.

The overseer also requested reconciliation, but this dispatch explicitly forbids reconciliation and state/plan writes. Leave that to the separate maintainer/planner rather than perform another unit.

## Method

Read STATE.md, graph contract, VISION, actor and record skills, the parent bet and removal evidence; inspect the walk, shared agent overlay, scaffold, engine resolution and existing tests. Change only CLI-owned instructions and contract assertions plus their documentation. The documentation verification date already equals 2026-09-08 and remains current. Run `pixi run python -m pytest cli/tests` against the built development engine: `.pixi/envs/default/bin/FreeCADCmd` with `src/Mod/cadex` source modules. No engine, protocol, payload or shell edit, so no build or other zone gate required. The suite includes its existing bounded local CPU trainer and real-walk tests. No provider dispatch, GUI or remote execution.

## Result

Full CLI suite: **195 passed, no skips, 217.22 s, exit 0**. Local output is `/tmp/cadex-40-cli.log` (not a versioned artifact). `git diff --check` passes. Hypergraph export and check are run before the commit. One logical guidance change; no runtime validation claim and no new test count because the existing scaffold contract test was extended. Risk: an agent may ignore guidance; tests prove the instructions are delivered, not compliance. Existing project scaffolds are intentionally not migrated.

Next: the planned fresh two-servo rehearsal only once the reported provider reset permits it, using the corrected engine and existing training limits. Inspect script and placed inventory manually and all review views; absence of catalog rows cannot prove absence of fused hardware. While quota blocks that unit, the independent scratch cache diagnosis remains the selected alternative. This unit does not tick any additional charter criterion: fresh agent behavior remains unmeasured, and the rehearsal must supply that evidence. Two unreconciled records now remain for the maintainer; no state or plan file was edited.

Dispatch closed: 1 unit — deliver and test concise purchased-hardware placement guidance.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 9899a69a62c01d314b0da2dc5b7727ac9d7f3a99

## State Impact

- target: calm-peak-5247 — Walk design instructions and fresh project scaffold teach purchased instances as separate components and transformed catalog cutters; full CLI suite 195 passed, agent compliance still unmeasured.
- target: damp-moon-9297 — Guidance asks for script review alongside placed inventory without purchase inference or claims about fused catalog geometry; fresh rehearsal remains necessary.
