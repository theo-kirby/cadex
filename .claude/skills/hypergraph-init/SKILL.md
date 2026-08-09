---
name: hypergraph-init
description: Initialize the Hypergraph two-graph protocol (record graph + state graph) for a day-zero project. Creates both roots, seeds a state skeleton mirroring the architecture, writes .hypergraph/config.yml, and generates STATE.md. Use hypergraph-adopt for a repo that already has a history.
---

# Hypergraph Init

Sets up the [Hypergraph protocol](references/spec.md) for a project: an append-only
**record graph** and a small distilled **state graph**, with cross-graph provenance in
markdown. Both are node files committed under `.hypergraph/graph/`
([local-adapter.md](references/local-adapter.md)) — nothing to choose, nothing to sign
in to, so there is no storage question to put to the user.

## The CLI

Invocations below write `hypergraph …`. In a dev checkout of the protocol repo that is
`uv run tools/hypergraph.py …`; an adopter gets the bare `hypergraph` from
`uv tool install hypergraph-protocol`. Same tool, same flags — pick whichever resolves.

## When To Use

- The user wants to start tracking a project with Hypergraph.
- A repo has no `.hypergraph/config.yml` **and no meaningful past**.

Do NOT use on a repo that already has `.hypergraph/config.yml` — that project is
initialized; use hypergraph-record / hypergraph-reconcile / hypergraph-orient instead.
**A repo with a real history goes to hypergraph-adopt**, not here: init writes a
day-one frontier, which on a mature codebase is a fiction. Existing hosted graph,
years of commits, or docs describing what already works → adopt.

## Workflow

1. **Interview (short).** Ask only what you cannot infer from the repo:
   - Project name (default: repo directory name).
   - Architecture outline: the 3–8 top-level components/capabilities the state graph
     should mirror (propose a list from the repo layout; let the user edit it).
2. **Create the two roots** (parentless; local-adapter §1):
   - `<project> — record`: content briefly describes the append-only log discipline.
   - `<project> — state`: content = project overview + a `## Reconciliation` section
     with `high_water_mark: none` and `reconciled_at:` now (SPEC I5).
   ```bash
   # the CLI generates the state root's Reconciliation block; each call prints the
   # minted slug as its first stdout field
   hypergraph new record --root --title "<project> — record" --body record-root.md
   hypergraph new state  --root --title "<project> — state"  --body overview.md --reconcile
   ```
3. **Seed the state skeleton**: one child of the state root per architecture component
   (`hypergraph new state --parent <state-root> --status open --prov "…" --reconcile`).
   Each follows the state-node template with `Status: open`, a one-line `## Current`
   describing intent,
   `## Negative knowledge` = `None yet.`, and `## Provenance` citing the init record
   node's slug (create record node #1 first if you need the slug — order steps 3/4
   accordingly).
4. **Record node #1** (`hypergraph-record` discipline): child of the record root titled
   "Project initialized under Hypergraph", documenting the chosen architecture, with
   `## State Impact` listing `- target: <each seeded state slug> — seeded, status open`
   (or `NEW` lines if you created record node #1 before the skeleton).
5. **Advance the HWM** through record node #1 so `high_water_mark:` names its slug:
   `hypergraph update <state-root> --body root.md --expect $(hypergraph update
   <state-root> --print-sha) --reconcile` (local-adapter §7).
6. **Write `.hypergraph/config.yml`** in the target repo from
   [config.example.yml](references/config.example.yml): project name, both roots'
   `node_id` + `slug`, and `graph_dir:`. Add `.hypergraph/cache/` to the repo's
   `.gitignore` — and make sure `.hypergraph/graph/` is **not** ignored; it is the
   project's memory.
7. **Export + render**: `hypergraph export --config .hypergraph/config.yml` →
   `.hypergraph/cache/{record,state}.json`, then:
   ```
   hypergraph render --state .hypergraph/cache/state.json --config .hypergraph/config.yml -o STATE.md
   hypergraph check --record .hypergraph/cache/record.json --state .hypergraph/cache/state.json --config .hypergraph/config.yml
   ```
   The check must exit 0 before you report success.
8. **Commit**: `git add .hypergraph/config.yml .hypergraph/graph STATE.md`. The
   project is not initialized until the node files are committed.

## Guardrails

- Never link the two roots with a graph edge; the graphs stay topologically disjoint
  (SPEC: pointers are markdown slugs, not edges).
- Keep the skeleton small — components, not tasks. A handful of `open` nodes is a
  healthy day-one frontier.
- `--reconcile` is required for every state write (SPEC I3), and init is one of the
  two places allowed to pass it. It is a gate, not a formality.
- Report the created slugs (both roots + skeleton) to the user; they are permanent
  handles.
