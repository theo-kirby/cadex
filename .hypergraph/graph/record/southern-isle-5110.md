---
node_id: 228ea5bc-5946-5ba1-a9e8-44ab3128d585
slug: southern-isle-5110
title: Audit inactive Main GUI launcher branches and template
created_at: '2026-09-07T03:03:38+00:00'
parents:
- placid-chart-1292
summary: ''
---
## What

Audited the four inactive Main portable-launcher GUI branches and unused GUI resource template; documented the exact later removal boundary in PHASE8-AUDIT.md, ADR-226, FREECAD.md and ROADMAP.md. No implementation or generated artifact changed.

## Why

Targets mission 3 and round-glacier-2865, following the Main audit bet in placid-chart-1292. The overseer requests a maintainer pass and replan before Material deletion, but this work dispatch explicitly forbids reconciliation without exceptions. Assumption: defer Material deletion and take the already planned independent documentation audit. The supplied checkpoint already incorporates the Material disable and its tail lists one record, contrary to the overseer's three-record premise. No state, plan or charter edits.

## Method

Read STATE, actor/record skills, graph contract, VISION, Main sources/CMake, earlier audit and git show 9f7c3268. Enumerated tracked text outside shell/docs/graph/run metadata (binary and >2 MB files excluded); searched build/setup/package consumers and current debug/release rules and Main artifacts. Verified both candidates exist at the import commit and lack manifest entries. Ran the existing packaged lifecycle and licensing suites together and git diff --check.

## Result

Existing packaged gate: 26 passed in 15.32 s. No build/configure/install/stage, full engine pytest, inherited CTest, Windows execution or GUI launch; this is documentation and static audit evidence only. Prior Main removal already disabled the GUI macro/resource consumers. The active Windows command-line launcher/resources must survive. Stale debug autogen metadata still cites the retired template; later removal must quarantine it and repeat rule checks. Future shared-source edits require a manifest entry/notice and explicit Windows validation limitations; broad GUI-source and fork-delta claims remain open.

Next: the separate maintainer/planner should resolve the overseer ordering request; Material deletion remains untouched, and Main implementation requires a subsequent bet and its documented gates. Hypergraph export/check must pass before commit.

Dispatch closed: 1 unit — audit inactive Main GUI launcher branches and template.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: b0d5c95adb184ce58de3df8d54799869670bb6f1

## State Impact

- target: round-glacier-2865 — Main audit qualifies four inactive GUI arms and unused resource template after prior target disable; retain Windows command-line behavior, require later bet and Windows validation, stale debug metadata cleanup and new launcher manifest notice. No implementation removed; Material deletion deferred under overseer ordering conflict.
