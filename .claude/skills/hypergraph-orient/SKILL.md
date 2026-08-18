---
name: hypergraph-orient
description: Cold-start orientation for a Hypergraph project - land on the state graph, read the frontier (open/broken/blocked), and produce an orientation brief with provenance slugs for deep dives. Read-only, a handful of file reads.
---

# Hypergraph Orient

The read-only landing path for a fresh agent: state root → frontier → orientation
brief. The record graph exists precisely so you do *not* have to traverse it to know
what is true now. Protocol: [spec.md](references/spec.md).

## The CLI

Invocations below write `hypergraph …`. In a dev checkout of the protocol repo that is
`uv run tools/hypergraph.py …`; an adopter gets the bare `hypergraph` from
`uv tool install hypergraph-protocol`. Same tool, same flags — pick whichever resolves.

## When To Use

- Starting a session on a project that has `.hypergraph/config.yml`.
- The user asks "where were we?", "what's broken?", "what should I work on?".

Not for writing anything — this skill mutates nothing.

## Workflow

The graphs are files in the repo ([local-adapter.md](references/local-adapter.md)), so
orientation costs no tool budget at all and there is no degraded mode: the repo **is**
the graph.

1. Read `.hypergraph/config.yml` → `graph_dir` and the state root slug.
2. Read `STATE.md` — frontier first, architecture tree below, with the reconciled-through
   HWM in the header. That is the whole brief's raw material.
3. Read `.hypergraph/graph/state/<slug>.md` for the frontier nodes you need in full
   (negative knowledge, provenance slugs). **Prefer frontier nodes** — status `open`,
   `broken`, or `blocked` (SPEC I6) — over `working` ones; open a `working` body only
   as relevance demands.
4. Staleness is a git question, not an export-lag question: if `git status` shows
   uncommitted node files, or `STATE.md` predates the newest record file, say so and
   recommend `hypergraph export` + hypergraph-reconcile.

## Orientation brief (the deliverable)

- One line: project, reconciled-through HWM + timestamp, frontier size.
- Frontier items ranked `broken` → `blocked` → `open`, each with status, claim
  summary, relevant negative knowledge, and its `## Provenance` slugs as the
  **deep-dive pointers** — follow a slug into `.hypergraph/graph/record/<slug>.md`
  only when the task at hand needs that history.
- Flag staleness: if the HWM timestamp is old, or the user mentions work not reflected
  in state, recommend hypergraph-reconcile.

## Guardrails

- Read-only: no `hypergraph new` / `update` / `export`. Orientation writes nothing.
- Stay in the state graph until you have a concrete reason to open a record node; the
  budget exists to keep cold-start cost flat as the record graph grows.
- Don't re-summarize the whole record history — the brief is about *now* and *next*.
- If STATE.md and the node files disagree, trust the node files and say so. They are
  the graph; STATE.md is a generated snapshot of it.
