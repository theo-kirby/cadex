---
name: hypergraph-record
description: Commit a unit of research/engineering work to a Hypergraph record graph with a State Impact declaration. Use during or after any meaningful unit of work in a project with .hypergraph/config.yml. Never writes state nodes.
---

# Hypergraph Record

The commit discipline for the append-only **record graph**. Every unit of work becomes
one record node with a declared state impact; a separate reconcile pass folds impacts
into the state graph. Protocol: [spec.md](references/spec.md).

## The CLI

Invocations below write `hypergraph …`. In a dev checkout of the protocol repo that is
`uv run tools/hypergraph.py …`; an adopter gets the bare `hypergraph` from
`uv tool install hypergraph-protocol`. Same tool, same flags — pick whichever resolves.

The graphs are markdown node files committed in this repo
([local-adapter.md](references/local-adapter.md)) — one `hypergraph` call per operation.

## When To Use

- During/after any unit of work (experiment, decision, fix, dead end) in a project
  that has `.hypergraph/config.yml`.
- Dead ends and failures especially — they are the raw material for negative knowledge.
- When the Operator or an agent sets a new direction (feature, research thrust,
  constraint) **before any work exists**: record a decision node capturing the
  intent, constraints, and rationale, attributed to its source, with `## State
  Impact` declaring `NEW <node>` (or deltas) so reconcile opens the gap on the
  frontier. Intent enters through the record graph like everything else (SPEC:
  Forward work).

- **On any branch, fork or machine.** Recording is the whole obligation for a
  contributor or a parallel agent: record nodes are one file each and merge without
  conflict, so a pull request that adds them is never a merge problem, and the claim
  lands in the diff beside the code it is about. Do not reconcile — the maintainer does
  that once on the default branch after the merge (SPEC: Collaboration).

Not for editing state nodes (that is reconcile's job — SPEC I3) or for orientation
(use hypergraph-orient).

## Workflow

1. Read `.hypergraph/config.yml` for the record root.
2. **Choose the parent by causal relation** (SPEC conventions): the record node whose
   result/decision this work follows from. Find it via STATE.md provenance slugs or
   `ls .hypergraph/graph/record/`. Branch from the root only for a genuinely
   independent new workstream — no root-spam. Extra causal parents: a second
   `--parent` flag.
3. **Compose content** from [record-node.md](references/record-node.md) — exact
   headings `## What / ## Why / ## Method / ## Result / ## Repo / ## State Impact`.
   `## Repo` carries the current commit SHA when code is involved.
4. **Always declare `## State Impact`** (SPEC I2), one of:
   - `- target: <state-slug> — <delta>` per affected state node (status flips, new
     claims, new negative knowledge, supersessions);
   - `- target: NEW <kebab-name> — <delta>` when reconcile should create a state node;
   - `none: <reason>` when current state truly doesn't change.
   Look up real state slugs in STATE.md — a wrong target fails `check`.
5. **Commit.** Write `## What/Why/Method/Result` to a body file, then:
   ```
   hypergraph new record --title "…" --body body.md --parent <slug> \
       --impact "<state-slug> — <delta>" --repo-auto
   ```
   The CLI generates `## Repo` and `## State Impact`, validates the node against the
   checker, and prints the minted slug. Exit 2 = nothing was written; fix and retry.
   Then `hypergraph export --config .hypergraph/config.yml` and **commit the node file
   to git** — an uncommitted node file is as invisible as no node at all.
6. **Attach evidence** when it exists (logs, plots, data): commit the files to the repo
   and reference them by path from `## Method` / `## Result`.
7. Tell the user the new slug and its declared impact. If impacts are piling up,
   suggest running hypergraph-reconcile.

## Guardrails

- **Never write state nodes** (SPEC I3) — not even a "trivial" status flip. Never
  `hypergraph new state` / `hypergraph update`; both refuse without `--reconcile`,
  which only the reconcile skill passes. Declare the impact instead.
- Record nodes are immutable once committed: follow-ups and corrections are new child
  nodes, not edits.
- One node per unit of work — don't batch a week into one node, don't split one
  experiment into five.
- Reproduction-grade content (`## Method` / `## Result`): numbers, commands,
  interpretation — enough for a third party to audit (SPEC I8 depends on it).
