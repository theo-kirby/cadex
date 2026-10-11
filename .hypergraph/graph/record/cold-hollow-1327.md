---
node_id: 011b9a3d-9ccc-5ace-b9c9-1db0c2f07eb1
slug: cold-hollow-1327
title: 'Flywheel 0.2.78 local repositories: upgrade and hypergraph import rehearsal'
created_at: '2026-10-11T11:39:58+00:00'
parents:
- winter-pond-1701
summary: ''
---
## What

Upgraded the Flywheel CLI 0.1.107 → 0.2.78 (system Node 22 → 24.21 for its local
repositories) and rehearsed moving this repo's Hypergraph graphs into a Flywheel
local repository, in a scratch directory only. Nothing in the repo changed.

## Why

Owner asked whether Flywheel's new local-repo system can replace the git-native
Hypergraph store, and for a full migration plan backed by testing.

## Method

Scratch scripts (session scratchpad, not committed): smoke.py (every repo:* verb),
concurrency.py (two writers on one repo), rehearse.py (import record 986 + state 143 +
plan 4 nodes: node:create with slug kept, lineage per parent, containment under the
graph root, commit every 300 ops; created_at, old node_id and artifact paths in a
content trailer), roundtrip.py (rebuild the export JSON and diff it with the cache).

## Result

- Import: 1133 nodes, 3436 CLI calls, 0 errors, 24.5 min; per-op 0.22 s on an empty
  repo rising to ~0.5 s at full size; db.sqlite 34 MB; backup 9.9 MB in 1.2 s,
  restore 1.4 s; push --dry-run: 13 commits, 13 MB, visibility only_you (not pushed).
- Round trip: 0 differing fields (slug, title, content, summary, parents,
  created_at, artifacts) across all 1133 nodes.
- Read cost: rebuilding the export takes 155 s (node:get + lineage:list per node,
  8 parallel) vs 0.31 s for `hypergraph export` — no bulk export verb exists.
- Concurrency: one shared staging area per repository; writer B's commits swept
  writer A's staged nodes under B's messages and all of A's commits failed
  "repository head is stale". No data lost; attribution wrong.
- node_id and created_at are not settable on create (source_created_at stays null);
  slug_name is. `.flywheel/` is not gitignored by init; git worktrees do not discover
  the main checkout's repository.
- `flywheel update --yes` while a job runs removes the binary briefly and killed the
  first import attempt; it also installed a new flywheel-repo skill.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 94c059d4b6060eb32fd0c3f98d68770d2ed292d1

## State Impact

none: exploratory rehearsal in scratch space; migration not decided
