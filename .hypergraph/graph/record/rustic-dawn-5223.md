---
node_id: cb5d2fc5-2a5e-5a23-b4d3-86468d428cac
slug: rustic-dawn-5223
title: 'ADR-585: a rerun script ungrounds and retires linked outputs in place'
created_at: '2026-10-07T17:45:47+00:00'
parents:
- windy-badger-4166
summary: ''
---
## What
A rerun script could not unground a component that was once grounded, nor retire a component output still referenced by the script's own component link; the agent had to rename outputs twice. Publication now counts assembly joint/simulation/view groups as the program's own (`_domain_internal_objects`) and defers retirement until every domain pass has run, then refuses only foreign references (ADR-585, commits 62a6e254, merge 68396ab7).

## Why
The excavator project's ADR-009 workaround (outputs renamed to `cp_<name>`).

## Method
`src/Mod/cadex/CadexScriptedDomainPublication.py`: `defer_retirement=True` on the domain publishers, `_refuse_foreign_retirement_uses` after all passes. Test `src/Mod/cadex/cadex_tests/test_publication_declared_state.py` against live FreeCADCmd; docs/XSCRIPT.md, docs/ARCHITECTURE.md.

## Result
Ground→unground→reground, a renamed source part, and a renamed Part Design body all publish; a foreign App::Link to a dropped output is still refused naming its owner. Fails without the fix with the excavator's two messages.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: f49be9c36b2cfeb4f4caddf6d1e43245d1b6696e

## State Impact

- target: forest-wind-0342 — publication honours script-declared grounding and output retirement without renames (ADR-585)
