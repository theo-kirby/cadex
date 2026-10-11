---
name: hypergraph-orient
description: Cold-start orientation for a Hypergraph project - land on the state graph, replay the unreconciled tail on top of it, read the frontier (open/broken/blocked), and produce an orientation brief that leads with "reconcile first" when the tail is fat on the default branch. Writes nothing but the gitignored cache.
---

# Hypergraph Orient

The landing path for a fresh agent: state root → unreconciled tail → frontier →
orientation brief. The state graph is a checkpoint and the unreconciled record
nodes are its replayable log (SPEC: Staleness and the reconcile trigger) — so a
stale high-water mark never means orienting stale: replay the tail's declared
impacts on top. The record graph exists precisely so you do *not* have to traverse
it to know what is true now. Protocol: [spec.md](references/spec.md).

The **state graph** stays the cold-start read even in a project with named views
(SPEC: Views) — the frontier lives there; extra views are specialist projections you
open only when the work is about their axis.

## The CLI

`hypergraph …` — in a dev checkout of the protocol repo, `uv run tools/hypergraph.py …`.

## When To Use

- Starting a session on a project that has `.hypergraph/config.yml`.
- The user asks "where were we?", "what's broken?", "what should I work on?".

Not for writing anything — this skill mutates nothing but the gitignored cache.

## Workflow

The graphs are files in the repo ([local-adapter.md](references/local-adapter.md)), so
orientation costs no tool budget at all and there is no degraded mode: the repo **is**
the graph.

1. Read `.hypergraph/config.yml` → `graph_dir` and the state root slug.
2. Read `STATE.md` — frontier first, architecture tree below, with the reconciled-through
   HWM in the header. That is the checkpoint half of the brief's raw material.
3. **Measure the tail.** Export first, then ask:
   ```
   hypergraph export --config .hypergraph/config.yml
   hypergraph hwm --record .hypergraph/cache/record.json --state .hypergraph/cache/state.json \
     --config .hypergraph/config.yml --impacts
   ```
   Never measure against the existing cache: it is gitignored and goes stale exactly
   when the tail gets fat — right after a merge (SPEC: Staleness and the reconcile
   trigger). Export writes only the gitignored cache; it touches no node file.
4. **Replay the tail.** The state graph is a checkpoint; the unreconciled nodes are
   its replayable log, and `--impacts` printed their declared deltas. Lay them over
   what STATE.md says — "state says `open`, but an unreconciled record already
   flipped it to `working`" — and orient against the *corrected* picture. Mark every
   replayed claim as **pending reconcile** in the brief; a declared delta is the
   recording agent's claim, not the librarian's distillation.
5. Read `.hypergraph/graph/state/<slug>.md` for the frontier nodes you need in full
   (negative knowledge, provenance slugs). **Prefer frontier nodes** — status `open`,
   `broken`, or `blocked` (SPEC I6) — over `working` ones; open a `working` body only
   as relevance demands.
6. **Recommend by tail size and branch** (the pressure trigger):
   - **Default branch, tail ≥ 3** — the brief *leads* with "reconcile first, then
     the task": recommend hypergraph-reconcile before the session's actual work.
     A fresh session start is exactly the context reconcile wants.
   - **Default branch, tail 1–2** — note it, replay it, proceed.
   - **Side branch or worktree, any tail** — never recommend reconciling here
     (record anywhere, reconcile only on the default branch — SPEC I3,
     Collaboration). Replay instead, and say the tail folds in on the default
     branch after merge. Note that a branch replays only the tail it can see:
     nodes merged to the default branch after the fork point are invisible until
     the branch merges it back in.

## Orientation brief (the deliverable)

- One line: project, reconciled-through HWM + timestamp, frontier size, tail size
  (unreconciled nodes).
- If the pressure trigger fired (step 6): "reconcile first" is the brief's first
  line after that, before any task-specific material.
- Frontier items ranked `broken` → `blocked` → `open`, each with status, claim
  summary, relevant negative knowledge, and its `## Provenance` slugs as the
  **deep-dive pointers** — follow a slug into `.hypergraph/graph/record/<slug>.md`
  only when the task at hand needs that history. Corrections replayed from the
  tail appear inline, flagged pending reconcile.
- Flag staleness the same way: if the user mentions work not reflected in state and
  the tail doesn't explain it either, say so — that work was never recorded (I1).

## Guardrails

- No `hypergraph new` / `update`. Orientation writes nothing but the gitignored
  cache (`export`, step 3) — no node file, no STATE.md, no commit.
- Never reconcile from inside this skill. The pressure trigger *recommends*
  hypergraph-reconcile; running it is the session's next move, not orient's.
- Stay in the state graph plus the tail's impact lines until you have a concrete
  reason to open a record node in full; the budget exists to keep cold-start cost
  flat as the record graph grows.
- Don't re-summarize the whole record history — the brief is about *now* and *next*.
- If STATE.md and the node files disagree, trust the node files and say so. They are
  the graph; STATE.md is a generated snapshot of it.
