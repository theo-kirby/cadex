---
node_id: d8a4eaea-f4e9-51c4-aa8c-03e6b8ebce64
slug: light-tower-4418
title: 'ot10 A4: four hex refusal classes prevented in describe_api and named in the refusal (ADR-416)'
created_at: '2026-09-27T18:28:32+00:00'
parents:
- sweet-sage-3253
summary: ''
---
## What

ot10 A4 (ladder short-4): the four refusal classes hex2 and hex3 each learned the API by — a wrong horn style name, `edit_script` before any accepted script, the wrong number of assembly / solver_diagnostics outputs, and a joint (or component) listed but not returned or returned twice — are each prevented in the `describe_api` text the agent reads, and each refusal now names its fix. ADR-416. Also, the critic's side ask: P2's `unresolved_edges` is surfaced in the proxy and its one-line summary.

## Why

The critic named A4 short-4 as the next unit, with each class pinned by a regression built from the real hex2/hex3 refusal texts, plus surfacing `unresolved_edges` so P2 is not a silent lower bound. Both were done. A2's 60 s bar stays open and was not touched.

## Method

- Pulled the actual tool inputs and refusal texts out of the hex2/hex3 Claude Code session logs (local, not committed): `s.horn("arm")`/`s.horn("single")`; `edit_script` right after a refused first `write_script`; a 14 KB script returning `result["asm"]` with no `assembly.solve`; joints appended to a Python list and never put in `result`.
- Found that the engine's own `revision_rule` was stale: it told the agent "a failed candidate becomes the working revision", which ADR-044's rollback made false. That made the hex3 edit a reasonable reading of the contract.
- Reference fixes (prose inside existing `describe_api` keys, no shape change): the servos catalog note lists every horn style and the default; `revision_rule` says refused candidates roll back and `edit_script` edits only the accepted source; `result_contract` states the assembly result shape and two idioms that produce it.
- Refusal fixes: the horn error names the style meant (substring, then stdlib `difflib`); `NO_PROJECT_SCRIPT` says the last write was refused and rolled back, with `required_changes`; `_graph_contract` names how many assemblies and diagnostics it found by output name and gives the line to add; unreturned joints and components are named by label or list position, unlisted outputs by name; a value under two keys names both.
- `cadex_tests/test_authoring_refusal_classes.py`: 14 tests. With the four source files stashed, 12 fail; the 2 that pass either way are controls (an empty project, a complete result).
- `cli/cadex_cli/inventory.printed_edges` sums `unresolved_edges`, `render.edge_proxy` carries it, and `describe_proxies` appends "a lower bound: N edge(s) unresolved" when N > 0. There is a new test in `cli/tests/test_look.py`.

## Result

All four hex refusal classes are now prevented in the reference and named in the refusal (ADR-416).

Verification at this revision:
- `pixi run test-engine`: 2229 passed, 53 skipped.
- `pytest cli/tests`, full rerun: 989 passed, 1 skipped.
- The engine was rebuilt and staged, and the payload was checked to contain the new code. The packaged lifecycle gate (`CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64 pytest test_cadexd_lifecycle.py`) gave 23 passed.
- The new suite fails 12 of 14 tests on the old source.

Concerns for the next iteration:
- A4's last clause, "A5's transcripts show none of these refusals recurring", can only be evidenced by an A5 probe. It is not claimed here.
- The CLI overlay's design section (`cli/cadex_cli/agent.py`, the PRINTABLE bullet) has a sentence cut off at "no unsupported", which runs into "BE DONE…". The agent reads it on every turn. Leave it to the overlay rewrite (ladder medium-1), or fix it first.
- `cli/tests/test_review_disk_use.py::test_browser_shows_disk_use_…` failed once in the full CLI run (headless browser, `null.click`), then passed alone and in the rerun. It is flaky, not broken by this change.
- No new third-party dependency. `difflib` is stdlib.

Dispatch closed: 1 unit — A4's four hex refusal classes prevented in the reference and named in the refusal (ADR-416), plus P2 unresolved_edges surfaced

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: f3699ba7bcdf71e40c881ffb728b2193cc16bc0d

## State Impact

- target: odd-tree-6681 — The four hex2/hex3 refusal classes are closed at the source (ADR-416, commit f3699ba7). Horn styles are listed in the library catalog note and a wrong style names the one meant. revision_rule now says a refused candidate is rolled back and edit_script edits only the accepted source; it no longer claims a failed candidate becomes the working revision. NO_PROJECT_SCRIPT says so and carries required_changes. result_contract states the assembly result shape. The count refusal names the missing assembly.solve line, and unreturned joints and components are named by label. 14 regressions (cadex_tests/test_authoring_refusal_classes.py) use the real hex inputs; 12 fail on the old source. Open: the overlay rewrite, and A5 transcripts showing no recurrence.
- target: warm-basin-7003 — P2 reports unresolved_edges summed over printed placements, and the proxy summary calls the share a lower bound when that count is nonzero (ADR-416).
