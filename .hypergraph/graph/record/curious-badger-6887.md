---
node_id: 6c3b217d-8dfd-58bf-8801-783baa0bd630
slug: curious-badger-6887
title: Remove stale engine-suite count from command guidance
created_at: '2026-09-08T08:53:24+00:00'
parents:
- cool-raven-8938
summary: ''
---
## What

Removed the stale `(1757 tests)` from AGENTS.md's `pixi run test-engine` comment, retaining the command and no-build guidance. Updated its verification date and appended the narrow removal to ADR-086, which introduced the task.

## Why

Execute the exact standing-maintenance unit selected by [rec: cool-raven-8938], targeting early-arbor-7123 and serving missions 1 and 2. This preserves charter criterion **The walk exists and is tested headlessly** by keeping its contributor verification guidance accurate; it supplies no new lifecycle evidence. No missing lifecycle leg is established by this correction, and no charter checkbox is earned. Existing working evidence remains the basis for criterion assessment.

The overseer's rejected handoff is answered by the already-landed maintainer commits 357f5116/f194160d and separate planner commit 358df12c, followed here by actual authorized work. Assumption: those completed role transitions satisfy the instruction rather than requiring another maintainer dispatch. No actor state write or handoff-only unit is needed.

## Method

Read STATE.md, the actor and hypergraph-record skills, graph contract/config, VISION, the latest bet and rejected handoff, and the cited evidence. Confirmed pixi.toml maps test-engine to the complete engine pytest directory; ADR-244 and [rec: lawful-dune-3795] record 2085 passed / 52 skipped. Removed the count instead of substituting another perishable number. Historical run counts remain evidence. No product ROADMAP checkbox applies to this documentation-only correction.

Ran git diff --check, hypergraph export --config .hypergraph/config.yml, and hypergraph check with the record/state caches and project config. Minted this single record with the selecting bet as causal parent, then repeated export/check and whitespace verification before committing.

## Result

Documentation verification passed: whitespace check exit 0; graph export/check exit 0 with zero violations and zero warnings. No product suite or build was run or claimed, as prescribed by the selected documentation-only bet. The correction changes no runtime behavior. State and charter files remain untouched.

Next: the conditional repair is non-dispatchable if final verification remains green; return to separate planning, without an actor handoff-only unit or adjacent audit. The parked live repair remains parked. No additional missing requirement for the lifecycle criterion was identified here.

Dispatch closed: 1 unit — remove stale engine-suite count from command guidance.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 358df12c396ff36cf2483697fd90fe4243bbe599

## State Impact

- target: early-arbor-7123 — Engine-suite guidance retains its full-directory task and no-build instruction without a stale test count; documentation verification passes.
