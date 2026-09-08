---
node_id: a2f676b2-3db5-59a0-af22-bee1210a5b10
slug: weathered-trail-0874
title: Onboarding version guidance now refers to project configuration
created_at: '2026-09-08T08:46:03+00:00'
parents:
- green-shade-8828
summary: ''
---
## What

Corrected the stale Hypergraph onboarding version assertion and logged the removal in ADR-137. The onboarding command now labels the installed CLI version and points to hypergraph_version in .hypergraph/config.yml for the project-copy version.

## Why

Executed the actionable short bet [rec: green-shade-8828], which follows the maintainer/planner handoff requested by the overseer. This is standing orientation maintenance serving missions 1 and 2 and preserving the charter criterion "The walk exists and is tested headlessly"; it adds no lifecycle evidence and closes no new criterion. Existing state records that criterion as working; no missing lifecycle leg is established by this unit. Assumption: the newer concrete planner bet authorizes this correction after the older overseer handoff. No parked Later criterion is promoted.

## Method

Read STATE.md, the parent bet, the actor and record skills, .hypergraph/AGENTS.md, config and ADR-137. Read-only hypergraph --version returned hypergraph-protocol 0.0.13; config declares hypergraph_version: 0.0.13, while onboarding asserted 0.0.7. Removed the duplicated version assertion and retained the distinction between CLI upgrades and committed-copy refreshes. The verification date was already 2026-09-08. Ran hypergraph export --config .hypergraph/config.yml, hypergraph check with the record/state cache files and that config, and git diff --check.

## Result

Documentation-only correction. Export exited 0 (315 records before this record, 34 state nodes, 4 plan nodes); check exited 0 with 0 violations and 0 warnings; whitespace check exited 0. No product gate or build was run or claimed, as scoped by the bet. No ROADMAP checkbox is earned. No install, upgrade, network query, generated-skill rewrite, state edit or reconciliation occurred. Next: separate planning; the conditional repair is non-dispatchable because verification passed. Do not repeat this correction or expand it into an adjacent audit.

Dispatch closed: 1 unit — corrected onboarding version guidance and recorded documentation verification.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 7e213bf6ba05918c697ea934e980681ab2919daf

## State Impact

- target: early-arbor-7123 — onboarding distinguishes installed CLI version from project-copy version in config; stale 0.0.7 assertion removed, graph checks clean
