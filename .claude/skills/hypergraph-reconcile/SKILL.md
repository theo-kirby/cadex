---
name: hypergraph-reconcile
description: The single-writer librarian pass for a Hypergraph project - folds declared State Impacts from unreconciled record nodes into the state graph, advances the high-water mark, regenerates STATE.md, and runs the invariant checker.
---

# Hypergraph Reconcile

The only **ongoing** writer of state nodes (SPEC I3) — init and adopt each pass
`--reconcile` once at setup; every later state write happens here. Reads record nodes
past the high-water mark, folds their declared impacts into the distilled state
graph, advances the HWM, and regenerates STATE.md. Protocol: [spec.md](references/spec.md).

If the project keeps **named views** (`views:` in the config — SPEC: Views), the
same single-writer rule holds *per view*, and this pass is the writer for every
one: each view has its own high-water mark over the record graph, and view-qualified
impacts (`policy/<slug>`) fold into their view exactly as unqualified ones fold into
state.

## The CLI

`hypergraph …` — in a dev checkout of the protocol repo, `uv run tools/hypergraph.py …`.

Every state write goes through `hypergraph update <slug> --expect <sha> --reconcile`
or `hypergraph new state … --reconcile` ([local-adapter.md](references/local-adapter.md)
§1/§2/§7). Both refuse without `--reconcile` — that flag is the I3 gate, and after setup this
is the only skill that passes it.

## When To Use

- After one or more hypergraph-record commits (the user asks to reconcile, or `check`
  reports unreconciled nodes / pending impacts).
- Before a milestone, handoff, or fresh-agent onboarding, so the frontier is current.
- **On the default branch, as the maintainer.** Contributors and parallel agents record
  only; the record graph merges without conflict, the state graph has one writer (SPEC
  I3), and reconciling on a side branch makes two. If you are on a feature branch or a
  fork, stop: record the work, open the pull request, and let the reconcile happen once
  after it merges. One pass over a merged batch writes one coherent claim.

Not for recording new knowledge — if you learn something *during* reconcile, stop and
record it first (SPEC I1), then reconcile it in.

## Workflow

1. **Load context**: `.hypergraph/config.yml`; read the state root's node file and
   parse `## Reconciliation` for the current HWM.
2. **Export both graphs** → `.hypergraph/cache/{record,state}.json`:
   `hypergraph export --config .hypergraph/config.yml`.
3. **Enumerate unreconciled nodes**: record nodes that are not ancestors of any
   frontier tip (reachability, never wall clock — a node authored before the last
   reconcile but merged after it is unreconciled). `check` prints the count and the
   pending impact targets; `hypergraph hwm` lists the nodes. If none, regenerate
   STATE.md and stop.
4. **Fold impacts, per state node** (batch all pending deltas for a target into one
   write). For each affected state node: read-sha → compose the complete new body →
   `hypergraph update --expect --reconcile`.
   - Apply the deltas: flip `Status:`, add/update claims in `## Current` with inline
     `[rec: <slug>]` citations, append `## Provenance` lines for every record node
     folded in (SPEC I4, I6).
   - `NEW` targets: create the state node under the architecturally right parent
     (usually the state root) — `hypergraph new state --parent <state-root-slug>
     --status … --prov "<record-slug> — why" --reconcile`.
   - Negative knowledge: entries carry scope, confidence, evidence slugs; a
     generalized scope needs a `decision:` slug pointing at a decision record node —
     if none exists, keep the scope narrow (SPEC I7).
   - **Compact while you're there**: merge redundant claims, trim superseded detail
     (the record graph keeps history), keep the node readable at a glance.
   - Judgment calls beyond the declared delta (e.g. an impact implies a status flip it
     didn't declare) are allowed but must stay derivable from the cited record nodes
     (SPEC I8) — when in doubt, fold only what was declared and note the discrepancy.
5. **Advance the HWM**: rewrite the state root's `## Reconciliation` with
   `high_water_mark:` = the record **tips** you folded through and `reconciled_at:` = now
   (SPEC I5), through the same read-sha → update sequence. Do this *after* the folds so
   a crashed run under-reports rather than skips.
   - The mark is the record graph's **tips**, comma-separated on one line:
     `high_water_mark: <tip>, <tip>, …` (SPEC I5). Often one slug — the newest node
     you folded; after a merge there are several, because a branch's tip is not an
     ancestor of main's. `hypergraph hwm --tips` prints exactly the frontier a
     fold-everything pass writes; plain `hypergraph hwm` lists what is outstanding,
     and anything still listed after you write the mark was not covered.
   - If `check` says nodes *predate* the mark and names `hwm --suggest`, this graph is
     crossing the v0.0.5 change. Run it and write the frontier it prints — those nodes
     were already folded, and folding them again duplicates claims.
5b. **Named views, if any: repeat steps 4–5 per view.** For each configured view
   (`hypergraph views ls`): fold that view's qualified impacts (`check` tallies them
   as `<view>/<target>`) into its nodes — `hypergraph new <view> … --reconcile` /
   `update … --reconcile`, same template, provenance citing record nodes only — then
   advance *that view's* `## Reconciliation` on its own root. The marks are
   independent: a view you did not touch keeps its old mark honestly, but folding a
   view's pending impacts without advancing its mark under-reports, same as state.
   A brand-new axis worth tracking is declared here, and only here:
   `hypergraph views add <name> [--md FILE] --reconcile`.
6. **Regenerate and check**:
   ```
   hypergraph sync --config .hypergraph/config.yml
   ```
   `sync` re-exports every graph (views included), regenerates STATE.md and each
   view's `md:` snapshot, runs `check`, and publishes.
   It stops before publishing if `check` reports violations. (The separate
   `export` / `render` / `check` commands still exist if you want the steps apart.)
7. **Publish.** `sync` already did this; run `hypergraph push` on its own if you split
   the steps. It exits 0 and prints one line whenever there is nothing for *this*
   checkout to publish — no mirror configured, not the default branch, or credentials
   that do not own the mirror — so there is nothing to decide: just run it. A **nonzero
   exit means one of two things**, and they are not the same:
   - *append-only breach* — a record node's body changed after it was published.
     Fix the local edit; a correction is a new child node, never an edit.
   - *drift* — the published copy no longer matches the node files. **Local files are
     canonical.** Fix drift by re-publishing, or by investigating who else wrote;
     never by editing node files to match.
8. **Commit.** `git add .hypergraph/graph STATE.md` (plus any view snapshots and the
   config, if `views add` ran) — the reconcile is not durable
   until the node files are committed. Do this *after* publishing, so the frontmatter
   `push` writes is caught by the same `git add`.
9. **Report honestly**: what was folded, what was created, checker output verbatim —
   including violations you could not fix. Impacts that could not be applied cleanly
   (ambiguous target, contradictory deltas) get reported, not guessed at.

## Guardrails

- Single writer: do not run two reconciles concurrently. A refused `--expect` mid-run
  means another writer is violating I3 — stop and report it.
- After a merge, start from `hypergraph sync`, never a bare `check`. The checker reads
  the exports, so a stale cache reports the pre-merge graph and hides everything that
  arrived. If a merge left conflict markers in a node file, `check` now fails on them —
  resolve the file, do not paste around it.
- Full-payload writes: `hypergraph update --body` replaces the whole body, so compose
  the complete new content before writing. It is not a diff.
- Never delete record nodes, never edit record content, never add cross-graph edges.
- Every claim you write must cite a record slug you actually read (SPEC I1/I4) — no
  provenance from memory.
- STATE.md is generated output; never hand-edit it to "fix" a checker complaint.
