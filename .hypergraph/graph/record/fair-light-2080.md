---
node_id: 1ea07cd5-4598-5f8d-b8f0-6b91bf99adfe
slug: fair-light-2080
title: 'ot8 iteration 10: the graph re-checked at HEAD, no new work under report_done'
created_at: '2026-09-21T02:26:10+00:00'
parents:
- rough-ridge-4729
summary: ''
---
## What

Iteration 10 of ot8 started no new work. It checked that the graph is still valid at HEAD `d719b9c3`: `hypergraph export` exited 0 (634 record, 75 state and 4 plan nodes), and `hypergraph check` against those exports also exited 0 (0 violations, 1 warning).

## Why

The critic accepted done and gave two different instructions. Its header said to use the "creative" exhaustion policy and propose three new directions. Its body said the policy is report_done: start no new work, do not repeat an experiment, do not advance parked work, and at most re-check export/check. The charter's exhaustion policy is `report_done` ("Do not repeat an exhausted experiment, invent another mechanism or advance parked work to fill time"), and the charter wins. So I did not do what the header asked (three new directions in the plan plus one unit of them), because the owner's charter forbids it. I followed the body's only allowed action instead.

## Method

`hypergraph export --config .hypergraph/config.yml`, then `hypergraph check --config .hypergraph/config.yml --record .hypergraph/cache/record.json --state .hypergraph/cache/state.json`. The working tree was clean before and after. I changed no code, docs, plan or state.

## Result

What is true now: G1-G6 have measured evidence and the critic has accepted done once. G4 is still control-blocked and is not counted as a success. The graph exports and passes the check at HEAD. The one warning is I1 on `ancient-vine-9908`: a reconcile-judgement sentence without a `[rec: …]` citation. It is informational, not a violation, and only a reconcile pass may fix it. The unreconciled tail is this one node.

For the owner (from the critic): commit `39e02390` edited record `stormy-sand-3570` in place instead of adding a child correction. I did not rewrite history. That is the owner's call at merge.

The next iteration should also return no change unless the critic rejects. Two consecutive acceptances stop the run.

Dispatch closed: 1 unit — the graph checked valid at HEAD (export and check exit 0); no new work, per the charter's report_done policy

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot8
- commit: d719b9c3f588a6ca78e3aabcc66e0315d5752888

## State Impact

none: verification only; the charter's report_done exhaustion policy forbids new work after done was accepted
