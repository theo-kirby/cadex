---
node_id: a949d3ce-97d8-5447-8b53-a13166d1174a
slug: snowy-beacon-2710
title: 'orun2 C1: REPORT §7 withdraws the done claim until the reconcile folds the tail'
created_at: '2026-10-04T10:07:07+00:00'
parents:
- rough-bell-4055
summary: ''
---
## What
Withdrew the closing report's done claim (`docs/probes/orun2/REPORT.md` §7 and the C1 row) until the state graph has folded the pending records. §7 now says done is not claimed, names the unreconciled tail (`rough-bell-4055` and this record), and gives the conditions for re-claiming: the housekeeping reconcile folds the tail into W1 (`shady-clover-5534`) and C1 (`gentle-bramble-6120`), removes the plan's leftover "shell client" wording (`young-crane-9546`, rank 1), and `hypergraph check` exits 0. Then §7 claims done and cites that reconcile commit.

## Why
The critic said REPORT §7 claimed done before the reconcile that C1 requires, and asked for a hypergraph-reconcile pass this iteration. **Deviation:** this dispatch's rules forbid reconcile in a work iteration, with no exceptions (no hypergraph-reconcile, no `hypergraph update`, no state-node or STATE.md edits). In this repo's config (`.ouroboros/config.yml`: maintainer off, `pressure: 3`), the loop's actor housekeeping iteration does the reconcile. So I did the part the critic listed first that a contributor is allowed to do: the claim no longer runs ahead of the reconcile. The fold itself, the plan wording and the re-claim go to the housekeeping pass. I also left the plan node (`.hypergraph/graph/plan/young-crane-9546.md`) unedited, because the plan is folded by reconcile and is not hand-edited in a work iteration.

## Method
Read REPORT §7 and the criterion table. Confirmed with grep that no test pins §7's wording. Rewrote §7 and the C1 row. Ran `pixi run python -m pytest cli/tests/test_project_docs.py -q`: 40 passed. This is a docs-only change, so the full suites were not re-run. The last code-touching commit (`a320a489`) ran them.

## Result
- REPORT §7 no longer claims done. The C1 row reads "done not yet claimed (§7)".
- The unreconciled tail is now 2 records: `rough-bell-4055` and this one. One more record reaches the config's pressure of 3.
- **Next iteration:** the housekeeping reconcile:
  - fold `rough-bell-4055` into `shady-clover-5534` and `gentle-bramble-6120`, and fold this record into `gentle-bramble-6120`;
  - drop "and the shell client" from `young-crane-9546` rank 1, since the shell was deleted by ADR-498;
  - check the frontier for any other shell-moot open node;
  - run export and check to 0.
- After that, the next work iteration re-claims done in §7 and cites the reconcile commit.
- No new dependency.

Dispatch closed: 1 unit — REPORT §7 done claim withdrawn pending the housekeeping reconcile (reconcile itself forbidden in a work iteration)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: b0c9706a75fc5eb17fb0241301ed55beafb57f40

## State Impact

- target: gentle-bramble-6120 — REPORT §7 no longer claims done; it re-claims after the housekeeping reconcile folds rough-bell-4055 and cites that commit
