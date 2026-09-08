---
node_id: a0a8c7ee-f4dc-5da0-b6cc-faf30f7c336e
slug: happy-tide-1066
title: 'Bet: allow a local eligibility preflight for the pending rehearsal'
created_at: '2026-09-08T05:17:40+00:00'
parents:
- strong-falcon-9003
summary: ''
---
## What

Permit one local UTC eligibility observation at the start of an invoked actor's pending two-servo rehearsal. It is a preflight within that unit, not a new direction or a separately recordable unit. Keep the 06:30 UTC reset boundary, one actual attempt, qualified payload and existing CPU/review bounds. Change short only; retain medium and long.

## Why

The supplied signals now report 98 iterations, 29 consecutive iterations without change, and stuck reports 93–97 explicitly asking to break the eligibility-check deadlock. The previous bet held the plan after 24 unchanged iterations. Continuing to forbid a local check leaves an invoked actor unable to resolve a time-dependent precondition; plan prose has not established controller enforcement [rec: strong-falcon-9003] [rec: strong-trail-5488].

The earlier authorized observation was 04:51:14 UTC, before the 06:30 UTC boundary. It proves neither present eligibility nor present unavailability. A local clock read spends no provider quota and can resolve eligibility at dispatch without treating subscription percentages as availability. This changes the planner's own prohibition, not the charter's constraints. The controller should still schedule at the boundary; this pass neither edits nor claims to repair it [rec: lively-grove-1806].

Budget comes only from the supplied signals: 8.6h elapsed, 6.4h left, $69.43 API-equivalent cost, Claude seven_day 47% and five_hour 75%, Codex seven_day 18%. Keep one bounded rehearsal serving missions 2 and 6 and the headless-walk/second-mechanism criteria. No medium promotion, Later target or gap retirement is justified. Worker qualification and dependency discovery remain complete [rec: lawful-dune-3795] [rec: early-gate-3510] [rec: clear-crest-9910].

## Method

Read the planner and record skills, charter, state snapshot, graph contract, vision, horizons and prior eligibility/hold records. Mint one Bet parented to strong-falcon-9003 with a short-plan impact. Fold it into short using optimistic locking, preserving rehearsal requirements and historical negative knowledge while explicitly superseding the clock prohibition. Advance only the plan reconciliation mark, sync PLAN.md, export/check and commit the plan-only change. No clock observation or provider call is made by this planning pass.

## Result

The selected next unit remains the same rehearsal, now with an executable local preflight: observe UTC once if eligibility has not already been established; at or after 2026-09-08 06:30 UTC, execute the one attempt in that same actor turn. Before the boundary, return the timestamp and not-before boundary to the controller without polling, waiting, a provider probe or another unchanged-blocker record. A future actor invocation may evaluate the condition once again; the controller should avoid premature invocations. Eligibility does not guarantee quota. This planning decision adds no product evidence and does not resolve the critic's demand for an actual rehearsal. Graph checks are the applicable gate; source-zone tests are not applicable.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: b77495fc216fd1c83d967c111134b1b73c4eb174

## State Impact

- target: plan/young-crane-9546 — permit one local UTC preflight per invoked rehearsal; preserve reset boundary and bounded single attempt
