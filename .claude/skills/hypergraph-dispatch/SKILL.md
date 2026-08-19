---
name: hypergraph-dispatch
description: Dispatch an agent at a target in a Hypergraph project - a frontier state slug, a prose goal, or a region of the state graph - work a bounded budget of units, and record everything as a causally-parented dispatch lineage. Reads live lane claims to avoid double work. Never reconciles, never writes state nodes.
---

# Hypergraph Dispatch

Point an agent at a target and let it work a bounded budget in its own lane. A
dispatch is ordinary contribution with a stated aim: one **dispatch decision node**
up front (the lane claim), work recorded as its children, an explicit closure line
at the end. Protocol: [spec.md](references/spec.md) (Collaboration → Dispatch and
lanes); providers: [lanes.md](references/lanes.md).

## The CLI

`hypergraph …` — in a dev checkout of the protocol repo, `uv run tools/hypergraph.py …`.
The `hypergraph dispatch` verb manages the local lane (worktree + branch); this
skill may name that verb but never a provider's internals — lane mechanics live
behind
[lanes.md](references/lanes.md), the way mirror mechanics live behind the CLI.

## When To Use

- The Operator (or a coordinating agent) says "work on X" where X is a frontier
  node, a stated goal, or an area of the project.
- An agent has budget to spend and needs the graph to tell it where — dispatch at a
  region and let orientation pick the gap.
- **Not** for doing the work in-place in an ongoing session (just work and use
  hypergraph-record), and **not** for reconciling (hypergraph-reconcile; dispatch
  never touches state).

## The target grammar

One of three forms:

1. **A frontier state slug** — "work this node." The target is an open/broken/
   blocked state node; its provenance slugs give the causal parent.
2. **A prose goal** — no state node names it yet. Record the Operator-directive
   decision node first (SPEC: Forward work): intent, constraints, rationale,
   attributed to its source. **That node is the dispatch node** — its impact is the
   `NEW <node>`/delta declaration, not `none:`.
3. **A region** — `within <state-slug>`: orient over that node's subtree, pick the
   best open/broken/blocked descendant not already claimed, and say why in
   `## Why` — the choice is part of the record.

**Budget**: N units of work, or a stated stopping rule. Default 1 unit. A unit is
what hypergraph-record calls a unit: one experiment, fix, decision, or dead end.

## The claim convention

The dispatch decision node is written **first**, before any work:

- Title: `Dispatch: <target>` — the prefix is the machine-readable part.
- Impact: `none: lane claim — dispatched at <target>; state changes when work
  lands` (form 2 above is the exception: its impact is the NEW/delta declaration).
- Causal parent: a provenance slug of the target (form 1/3), or the causal parent
  the directive follows from (form 2).

Work nodes are recorded as **children** of the dispatch node (each with a real
`## State Impact`, per hypergraph-record). Closure: the final child's `## Result`
ends with a line `Dispatch closed: <n> unit(s) <summary>`.

**A live claim** is an unreconciled `Dispatch:` node with no `Dispatch closed:`
line in any descendant. Claims are advisory, never locks: the worst failure is
duplicated work, which the record graph's merge story absorbs — nothing can
corrupt, because no dispatched agent writes state.

## Workflow

1. **Orient.** Run hypergraph-orient (or read STATE.md). Land on the frontier.
2. **Resolve the target and read the claims.** Live claims are found by:
   - `hypergraph hwm --record … --state …` — every unreconciled node;
   - among those, `grep -l "^title: 'Dispatch:" .hypergraph/graph/record/` (any
     unreconciled hit without a `Dispatch closed:` descendant is live);
   - `hypergraph dispatch ls` — lanes on this machine and their claim status.
   If the resolved target is claimed, pick elsewhere and **name the avoided claim
   in `## Why`**. If the target grammar leaves nothing to do (region exhausted,
   goal already met), **stand down at exit 0 and write nothing** — a no-op
   dispatch that records itself is noise.
3. **Open the lane** (when working outside the current checkout):
   `hypergraph dispatch open --at <target> [--budget N]`. With no agent
   configured it prints the manual steps — follow them; they end back at this
   skill's step 4 inside the lane.
4. **Record the dispatch node** (the claim convention above). Commit it.
5. **Work one unit.** Then hypergraph-record: a child of the dispatch node (or of
   the previous work node — keep the lineage causal), real impact, `--repo-auto`.
   Commit node + code together, on the lane branch if in a lane.
6. **Budget check.** Units remaining and evidence says continue → step 5.
   Otherwise close: the final child's `## Result` carries the
   `Dispatch closed: …` line.
7. **Report.** Slugs written, impacts declared, and the words "reconcile
   pending" — the maintainer folds this lineage on the default branch
   (`hypergraph dispatch harvest <lane>` brings a lane's commits home first,
   then `hypergraph dispatch close <lane>` tears the worktree down; it refuses
   while work is unharvested, and `--force` abandons it — say so out loud).

## Guardrails

- **Never reconcile; never write state nodes** (SPEC I3) — a dispatched agent is a
  contributor, and contributors record. Even when dispatched *at* a state node,
  the status flip is a declared impact, folded later by the maintainer.
- **Budget exhausted mid-unit**: record the partial unit honestly (what ran, what
  is unfinished, what the next agent needs), close the dispatch, stop. An
  abandoned lane with uncommitted work is the one unrecoverable outcome — which is
  why `dispatch close` refuses it without `--force`.
- **Re-dispatch is a new node.** Continuing a closed dispatch, or taking over a
  stale claim, starts a fresh `Dispatch:` node whose `## Why` names the
  predecessor. Never edit a committed dispatch node (record nodes are immutable).
- **Don't chain dispatches to dodge the budget.** A dispatch that spends its last
  unit dispatching again has worked zero units and claimed two targets. The
  budget ends the lineage; the *next* dispatch is the Operator's (or the
  coordinating agent's) call.
- **Stand down over guessing.** Wrong-looking target, unresolvable slug, region
  with no open descendants: exit 0 with a one-line reason, write nothing. The
  push/no-mirror posture, applied to work selection.
