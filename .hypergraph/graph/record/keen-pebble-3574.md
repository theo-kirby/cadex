---
node_id: 6a498325-545b-567a-b677-b5d4db23d271
slug: keen-pebble-3574
title: Bound CLI payload guidance to the verified schema check
created_at: '2026-09-08T01:33:19+00:00'
parents:
- tiny-haven-0347
summary: ''
---
## What

Corrected docs/CLI.md §6 and the matching engine.py comment to state the verified nonempty schema-mismatch check and its limits. Added a dated removal note under ADR-061. Across the three changed files, prose/comments shrink by 27 whitespace-delimited words. Runtime behavior is unchanged.

## Why

Follow short rank 2 and the disposable resolver evidence in [rec: tiny-haven-0347], implementing the bounded bet in [rec: spring-wolf-7431]. This standing maintenance serves missions 1, 2 and 6 and protects charter criteria **The walk exists and is tested headlessly** (crisp-reef-5607) and **The agent can see its work without a screen** (damp-moon-9297): public engine-selection guidance must not overstate what protects their execution. Matching schemas can coexist with absent worker/API modules; no runtime defect or new validator is implied.

The reversible assumption is to preserve behavior and correct only its description. The overseer mentions reconciliation, but the dispatch explicitly forbids it without exceptions; leave the three-record tail to the separate maintainer. No Later criterion promotion.

## Method

Read actor and record skills, STATE, graph contract, VISION, causal records, resolver code, CLI §6 and project-doc scaffold. Replace the mixed-tree guarantee with rejection of unequal, nonempty manifest protocol and module PROTOCOL_SCHEMA strings; agreement proves neither worker completeness nor shared source provenance. Retain envelope engine identification. The CLI verification date is already 2026-09-08 and remains current; the ADR correction carries that date explicitly.

Compare ast.dump(ast.parse(...)) for HEAD and edited engine.py: identical. Check project_docs.py scaffold: it describes walk artifacts/modes and makes no payload-coherence claim. The lifecycle walk and scaffold contract do not change, so no scaffold edit is warranted. ROADMAP has no corresponding open implementation checkbox; this is a guidance correction preserving completed criteria, so no new feature checkbox or roadmap edit is warranted.

Run full CLI gate against the refreshed ordinary installed engine: set CADEX_ENGINE_ROOT to its manifest directory and JAX_PLATFORMS=cpu, then `pixi run python build/clearance-i9/monitor.py build/schema-guidance-i31/cli-gate.log pixi run python -m pytest cli/tests -q -ra`. The existing monitor samples the entire process tree every 0.25 seconds, terminates above 2.9 GB or 850 seconds, and kills after a five-second grace period. Raw log and monitor JSON remain ignored under build/schema-guidance-i31. No tests added, no engine source/protocol/payload/shell changes, no build or separate walk replay. Training exercised only by the existing full CLI gate at local toy scale; no remote dispatch or GUI launch.

## Result

Full CLI gate exit 0: **195 passed in 201.13 seconds, zero skips**. Guard reports 201.6724 seconds, 1,161,297,920 bytes peak process-tree RSS, no cutoff. This includes unit/fake tests and real engine/training cases; the protocol fixture loads source deliberately, so it does not imply every test used the installed payload. Resolver AST equality and git diff --check pass. No runtime removal occurred; no build is needed for comment/prose edits. Graph export/check are the final record gates.

Next: this clean correction exhausts the selected payload-identity guidance direction. No broader audit or replay follows. The protected lifecycle/review criteria remain working on existing evidence; nothing additional is missing before those accepted headless evidence claims can stand. Human-owned boxes remain untouched; GUI attachment remains documented-only and remote execution scripted-only. The tail reaches three unreconciled records with this unit; the separate maintainer/planner should reconcile and select subsequent standing work.

Dispatch closed: 1 unit — removed the payload-coherence overclaim, preserved runtime behavior, and passed all 195 CLI tests.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 13bad8d9d67b635016e6f149b8ff0d05db280e7d

## State Impact

- target: chilly-union-8972 — CLI §6 and resolver comment now state nonempty schema disagreement refusal without claiming payload completeness or shared provenance; ADR-061 correction, unchanged runtime, 195 CLI passes; selected guidance direction exhausted
- target: crisp-reef-5607 — Preserve working headless walk criterion; engine-selection guidance corrected and full installed-engine CLI gate passes with zero skips
- target: damp-moon-9297 — Preserve working headless review criterion; schema agreement no longer overclaims payload completeness; existing review evidence and limits unchanged
