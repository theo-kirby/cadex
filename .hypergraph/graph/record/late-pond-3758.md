---
node_id: 0297464d-ca9d-5f82-8ea6-9e4c8aec0a12
slug: late-pond-3758
title: Remove unused GSL checkout after Start and close its manifest evidence
created_at: '2026-09-07T01:43:20+00:00'
parents:
- fair-snow-3443
summary: ''
---
## What

Removed the unused Microsoft GSL gitlink, its submodule entry and checkout
references in pixi setup-engine, app setup and the legacy build helper.
Updated AGENTS setup, provenance, third-party license inventory, FREECAD
ledger, ROADMAP checkbox and ADR-222. Resolved Start's reserved committed-
HEAD manifest check before changing the tree.

## Why

One bounded unit from short item 1, following fair-snow-3443, serving mission
3 and round-glacier-2865/windy-pebble-4630. Start's separate disable/delete
removed GSL's only compiled consumer. The reversible boundary is to remove
only that dead dependency tail; no CMake reference remains to remove.
The overseer's reconciliation request conflicts with the explicit work-
iteration prohibition; no state, plan or .ouroboros edits were made.

## Method

Tracked case-insensitive search for Microsoft.GSL, gsl/, gsl:: and
3rdParty/GSL across the post-Start engine/build tree and shell separately.
The only residual engine mention is Import DXF's ownership TODO comment.
Checked the GSL worktree clean, then git rm of its gitlink; no contents
vendored. Restored adjacent shell comments that git rm removed from
.gitmodules. No inherited source changed, so no manifest/notice edit.
Ran setup-engine, configure-release, one build-release, Bash syntax checks,
licensing/purity pytest and all four Cadex CTests. Local ephemeral logs:
/tmp/cadex-gsl-{setup,configure,build,tests,ctest}.log. No payload rules
changed: no install/staging or packaged gate claimed. No full engine suite,
full inherited CTest, GUI, remote machine or fresh-cache build run.

## Result

Before edits, committed-tree licensing: 10 passed, 1 payload-only skip in
0.30 s, including test_the_manifest_matches_git_reality. This satisfies
Start's final reserved condition; Help and Start now meet the two whole-tree
engine removal criterion. GSL is dependency cleanup, not a third module.
Setup and release configure succeed; one release build exits 0. Bash syntax
checks pass. Licensing/purity: 22 passed, 1 payload-only skip in 2.48 s.
Cadex CTests: 4/4 passed in 17.47 s. Runtime source and both surviving-file
modification sets are unchanged. No claim that the broad delta criterion
is closed. The legacy helper still has a pre-existing stale AddonManager
checkout reference: separate maintenance, not expanded into this unit.
Next: N20 independent actual-worker interface verification from short item
2. A separate maintainer owns reconciliation; the observed initial tail
contained fair-snow-3443, and this record adds one more.
Dispatch closed: 1 unit — remove GSL's unused checkout tail and resolve Start's final manifest evidence condition.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: c5b60790fc630846e8168021c48054de096559b8

## State Impact

- target: round-glacier-2865 — ADR-222 removes the unused Microsoft GSL gitlink and three checkout references after Start; setup, release configure/build, licensing/purity and four Cadex CTests pass. No retained CMake consumer or inherited source edit. Next planned unit is N20 interface verification.
- target: windy-pebble-4630 — Start's reserved committed-HEAD manifest check passed before this unit (licensing 10 passed, 1 payload-only skip). Together with the recorded disable/delete gates, Help and Start now satisfy the two whole-tree engine removal criterion.
