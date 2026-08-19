---
name: hypergraph-record
description: Commit a unit of research/engineering work to a Hypergraph record graph with a State Impact declaration. Use during or after any meaningful unit of work in a project with .hypergraph/config.yml. Never writes state nodes.
---

# Hypergraph Record

The commit discipline for the append-only **record graph**. Every unit of work becomes
one record node with a declared state impact; a separate reconcile pass folds impacts
into the state graph. Protocol: [spec.md](references/spec.md).

## The CLI

`hypergraph …` — in a dev checkout of the protocol repo, `uv run tools/hypergraph.py …`.
The graphs are markdown node files committed in this repo
([local-adapter.md](references/local-adapter.md)).

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

On a branch or fork, `hypergraph check --since <base-ref>` is the PR gate: it fails
when the branch changed files without adding a record node — run it before opening
the pull request.

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

   If this project keeps **named views** (a `views:` block in the config — SPEC:
   Views), the same two target forms may be view-qualified: `- target:
   <view>/<slug> — <delta>` and `- target: <view>/NEW <kebab-name> — <delta>`.
   Unqualified targets always mean the state graph. The view must already exist —
   an impact naming an undeclared view fails `check` (run
   `hypergraph views add <view> --md <FILE> --reconcile` first, from a reconcile
   pass; `views ls` lists what exists).
5. **Tag it, if this project keeps a vocabulary.** Read `.hypergraph/tags.yml`. If
   there is no such file, **tag nothing** — this project has not opted in, and one
   node with tags in a repo with none is noise. If there is one:
   - use **declared names only**, from `hypergraph tags list`;
   - to add a name, `hypergraph tags add <name>` — **never hand-edit the file**. A
     hand-merged duplicate name is the one unrecoverable tag failure;
   - pass them with `--tag <name>` (repeatable) in step 6.

   A tag is a way to **find** nodes, never a way to assert things about them — no
   invariant reads one, so a claim that lives only as a tag is invisible; it goes in
   the body and in `## State Impact`. Two or three per node (`kind:*`, `outcome:*`,
   `cluster:*`).
6. **Commit.** Write `## What/Why/Method/Result` to a body file, then:
   ```
   hypergraph new record --title "…" --body body.md --parent <slug> \
       --impact "<state-slug> — <delta>" --repo-auto [--tag kind:experiment]
   ```
   The CLI generates `## Repo` and `## State Impact`, validates the node against the
   checker, and prints the minted slug. Exit 2 = nothing was written; fix and retry.
   Then `hypergraph export --config .hypergraph/config.yml` and **commit the node file
   to git** — an uncommitted node file is as invisible as no node at all.
7. **Attach evidence** when it exists (logs, plots, data). Three things, and the
   third is the one that is easy to skip:
   - **Commit the files** — or don't. Gitignoring a 40 GB dataset is a legitimate
     call; it is yours to make. Just know that an uncommitted file that gets
     published is a file the mirror alone holds.
   - **Explain them** in `## Method` / `## Result`: what the run was, what the plot
     shows, what you concluded. Prose is the claim.
   - **Enumerate them** so a tool can find them. The list is the claim's index:
     ```
     hypergraph artifacts add <record-slug> research/runs/2026-08-14/train.log plots/loss.png
     hypergraph artifacts ls <record-slug>       # missing / untracked / outside repo
     ```
     or at authoring time, `hypergraph new record --artifact plots/loss.png …`.
     Paths are typed cwd-relative, like `git add`, and stored repo-relative so they
     survive a clone. Order matters and is preserved — the log before the plot it
     explains.

   **Never attach to a state node** — it is a `check` violation. Evidence hangs off
   the record node whose work produced it; a state node reaches it through
   `## Provenance` in one hop.
   If a file moves later, `hypergraph artifacts mv <record-slug> OLD NEW` repoints the
   record (it never touches the working tree — run `git mv` yourself).
8. Tell the user the new slug and its declared impact. If impacts are piling up,
   suggest running hypergraph-reconcile.

## Guardrails

- **Never write state nodes** (SPEC I3) — not even a "trivial" status flip. Never
  `hypergraph new state` / `hypergraph update`; both refuse without `--reconcile`,
  which only the reconcile skill passes. Declare the impact instead.
- Record nodes are immutable once committed: follow-ups and corrections are new child
  nodes, not edits.
- **`artifacts:` is the one exception, and only that key.** Editing the evidence list
  on a committed record node is fine — `hypergraph artifacts add|rm|mv` writes
  frontmatter and the append-only hash covers the *body*, exactly as `push` stamping
  `flywheel:` has always done. Editing the body is not fine, and `hypergraph update`
  still refuses record nodes outright. If the claim was wrong, write a child node.
- One node per unit of work — don't batch a week into one node, don't split one
  experiment into five.
- Reproduction-grade content (`## Method` / `## Result`): numbers, commands,
  interpretation — enough for a third party to audit (SPEC I8 depends on it).
