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

`hypergraph …` — in a dev checkout of the protocol repo, `uv run tools/hypergraph.py …`.

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
3. **Record node #1** (`hypergraph-record` discipline): child of the record root
   titled "Project initialized under Hypergraph", documenting the chosen
   architecture, with `## State Impact` listing one `- target: NEW <kebab-name> —
   seeded, status open` line per component. Record node #1 comes **first** so the
   skeleton can cite its minted slug — provenance is never written from memory.
   (A `NEW <kebab-name>` never auto-resolves to the slug step 4 mints; the mapping
   lives in this node's impact lines and step 4 fulfils it.)
4. **Seed the state skeleton**: one child of the state root per architecture
   component (`hypergraph new state --parent <state-root> --status open
   --prov "<record-node-1-slug> — seeded at project init" --reconcile`). Each
   follows the state-node template with `Status: open`, a one-line `## Current`
   describing intent, and `## Negative knowledge` = `None yet.`.
5. **Advance the HWM** through record node #1 so `high_water_mark:` names its slug:
   `hypergraph update <state-root> --body root.md --expect $(hypergraph update
   <state-root> --print-sha) --reconcile` (local-adapter §7).
6. **Write `.hypergraph/config.yml`** in the target repo from
   [config.example.yml](references/config.example.yml): project name, both roots'
   `node_id` + `slug`, and `graph_dir:`. Add `.hypergraph/cache/` to the repo's
   `.gitignore` — and make sure `.hypergraph/graph/` is **not** ignored; it is the
   project's memory.
7. **The gate**: `hypergraph sync --config .hypergraph/config.yml` — it exports,
   writes `STATE.md`, checks, and publishes if a mirror is configured. It must
   **exit 0** before you report success.
8. **Onboarding install** — the contract that makes arriving agents use what you
   just built. A repo with two graphs and no instructions to its agents has memory
   nobody consults:
   - Append [agents-block.md](references/agents-block.md) to the repo's `AGENTS.md`
     (create the file if absent) — idempotently: if `<!-- hypergraph:begin -->` is
     already present, replace the existing block rather than appending a second
     one. **Never break a `CLAUDE.md` → `AGENTS.md` symlink** — edit the target,
     never the link.
   - Write `.hypergraph/AGENTS.md`: the five non-negotiables expanded, this
     project's graph roots, the skills to use, and how to get the CLI
     (`uv tool install hypergraph-protocol` — it is a package, not a file).
   - **Install the skills, and make sure they can be committed:**
     ```
     hypergraph skills install            # into ./.claude/skills
     git check-ignore -v .claude/skills   # silence is what you want
     ```
     If a broad ignore rule (`.*`, `.claude/`) hides them, every instruction you
     just installed is dead on arrival for the next clone.
9. **Commit**: `git add .hypergraph/config.yml .hypergraph/graph STATE.md AGENTS.md
   .claude/skills`. The project is not initialized until the node files are
   committed.

## Guardrails

- Never link the two roots with a graph edge; the graphs stay topologically disjoint
  (SPEC: pointers are markdown slugs, not edges).
- Keep the skeleton small — components, not tasks. A handful of `open` nodes is a
  healthy day-one frontier.
- Named views are strictly post-init (SPEC: Views): init creates the two mandatory
  graphs only; a later reconcile pass adds a view with `hypergraph views add` if
  the project grows a second axis worth distilling.
- `--reconcile` is required for every state write (SPEC I3). Three writers ever
  pass it: init and adopt once each at setup, the reconcile skill ongoing. It is a
  gate, not a formality.
- Report the created slugs (both roots + skeleton) to the user; they are permanent
  handles.
