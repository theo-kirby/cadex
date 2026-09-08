---
node_id: 4645efcf-c6f3-502c-9dff-154ccacd7df3
slug: lawful-ivy-4474
title: 'Inventory resolves all inspection previews: critic fix'
created_at: '2026-09-07T22:06:39+00:00'
parents:
- restless-star-0524
- fair-rose-5950
summary: ''
---
## What

Fix forward the critic rejection of fair-rose-5950: the CLI inventory reader now resolves and pages catalog_counts and uncatalogued_sources and expands previewed component rows and nested fields before rendering. Replace the component-only loop with one recursive inspection reader. Update docs/CLI.md, ADR-236 and the ROADMAP checkbox in the same change.

## Why

Advances the charter criterion **The agent can see its work without a screen**, state damp-moon-9297. The catalog roll-up was still a preview stub above the 1 KiB budget, so rendering tried to convert /catalog_counts to an integer. Large component rows could silently lose their names. This is the overseer's mandatory critic fix, ahead of the plan's next unit. The reversible choice is a CLI reader fix with actual engine-pager regressions, without changing the inspection contract, engine, payload or lifecycle walk.

## Method

Use CadexInspection._bounded_page directly behind a CLI test client. Two cases contain 60 distinct catalog counts and 60 uncatalogued outputs; the second also uses 1,400-character suffixes so component rows and their nested names are previews. Assert all three collections are previewed, follow multiple pages, preserve the assembly target, and compare the complete collections and every rendered name, catalog count, pose and volume. On the old reader both cases fail with ValueError: invalid literal for int() with base 10: '/catalog_counts'.

## Result

`pixi run python -m pytest cli/tests/test_inventory.py -q`: 5 passed in 4.33 s, including the real-engine assembly checks. `pixi run python -m pytest cli/tests -q`: 147 passed in 131.16 s, no skips or failures. `git diff --check` passed. Only CLI Python and documentation changed; no full build or packaged gate was needed or run.

The headless-review criterion remains open: named-angle rendering, section views, clearance/intersection and wiring the review calls into the lifecycle walk still remain. Next work is a separate maintainer pass when the unreconciled threshold is reached, then the remaining review calls per the overseer. No reconcile was run: this dispatch explicitly forbids it. The supplied overseer tail count was stale against the checked-out checkpoint, which already reconciled fair-rose-5950; this record adds to the subsequent planner tail.

Dispatch closed: 1 unit — fix complete inventory paging and rendering, answering the critic rejection of fair-rose-5950.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 0dc96c167e5167877d53f72fada0b1435084c0f2

## State Impact

- target: damp-moon-9297 — Inventory paging critic rejection fixed: real inspection-pager regressions verify 60 catalog totals, uncatalogued names and oversized component rows render completely; remaining review calls and walk wiring remain open.
- target: chilly-union-8972 — The inventory reader expands nested previews and pages mappings, lists and strings instead of paging only components; CLI gate 147 passed with no skips.
