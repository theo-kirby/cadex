# Hypergraph onboarding — cadex

This repository keeps its memory in **two graphs**, committed as markdown node
files under `.hypergraph/graph/`. They are storage, not a cache: they travel
with the repo, work offline and merge through git.

- **Record graph** — the append-only log of everything that happened: decisions,
  experiments, evidence, dead ends. Topology is causal.
- **State graph** — a small, single-writer projection of what is true *now*:
  architecture, what works, what is broken or open, and accumulated negative
  knowledge. Topology mirrors the architecture, not history.

Every state node cites the record nodes it derives from. That cross-graph
citation structure is the hypergraph, and it is why a fresh agent can orient in
a handful of reads instead of traversing 136 ADRs.

## This project

| | |
|---|---|
| Record root | `odd-banner-6071` |
| State root | `nimble-pine-0740` |
| Epoch marker | `winter-rain-7897` — "Adopted Hypergraph", 2026-08-09 |
| Adoption mode | **B (ground-up)** — no legacy graph existed |
| Archive | **none.** There was no hosted graph to import, so config carries no `archive:` block. That is correct, not an omission. |
| Generated snapshot | `STATE.md` at the repo root |

**Prehistory.** The 14 record nodes before the marker are *era and workstream
summaries*, distilled from the repository and from an author interview on
2026-08-09. They are honest summaries, not an event-by-event reconstruction, and
they are exempt from I2 template compliance. Claims that came only from the
interview are marked and carried at low confidence — those are the ones that
cannot be re-derived from the tree.

**The ADR log is not superseded.** `docs/DECISIONS.md` remains the narrative
record of decisions and the place a direction change is argued. The record graph
is where a unit of work lands *with a declared state impact*; the state graph is
the distilled projection. Substantial work usually earns both, and they should
agree.

## The four non-negotiables

**1. Orient on arrival.** Run the `hypergraph-orient` skill, or read `STATE.md`.
The **frontier** — every state node whose status is `open`, `broken` or
`blocked` — is what matters now. Today that is three nodes: the Blender-inherited
file lifecycle (`broken`), the RL training loop (`blocked` on the GPU box's stale
checkout), and inherited-tree reduction (`open`). Read the negative knowledge
before you plan; it exists so you do not spend a day re-discovering it.

**2. Record every unit of work.** Features, fixes, experiments, dead ends,
decisions — use the `hypergraph-record` skill. One record node, causally
parented (choose the parent by "this followed from that result", never by
recency), with a `## State Impact` section that is either impact lines or
`none: <reason>`. **Unrecorded work is invisible to the project.** A dead end is
worth as much as a success here, and often more.

**3. Never write state nodes.** Declare impacts and let the
`hypergraph-reconcile` skill fold them. `STATE.md` is generated — never
hand-edit it. Only reconcile writes state, which is what stops parallel agents
from drifting the projection.

**4. Verify before finishing.**

```bash
hypergraph export
hypergraph check --record .hypergraph/cache/record.json \
                 --state  .hypergraph/cache/state.json \
                 --config .hypergraph/config.yml
```

`check` must **exit 0**. `.hypergraph/cache/` is gitignored and regenerated;
the node files under `.hypergraph/graph/` are the storage and are committed.

## Getting the tool

The skills under `.claude/skills/hypergraph-*` **are committed** and arrive with a
clone. The `hypergraph` CLI is not — it is a Python package, so install it once
per machine:

```bash
uv tool install hypergraph-protocol      # provides `hypergraph`
hypergraph --version                     # this project is on 0.0.7
```

The CLI and the committed copies are upgraded by two different commands, and one
cannot see the other:

```bash
uv tool upgrade hypergraph-protocol      # the CLI on this machine
hypergraph upgrade                       # this repo's skills + AGENTS.md block
```

`check` warns when the two are out of step. **After `hypergraph upgrade`, re-read
the block in the root `AGENTS.md`**: it overwrites everything between the
sentinels, including this project's ADR-log clause and epoch note.

## Skills

| Skill | When |
|---|---|
| `hypergraph-orient` | Arriving cold. Read-only, a handful of file reads. |
| `hypergraph-record` | During or after any meaningful unit of work. |
| `hypergraph-reconcile` | The single-writer librarian pass; folds declared impacts, advances the high-water mark, regenerates `STATE.md`. |

## Conventions worth knowing here

- **Record nodes carry repo context.** `hypergraph new record --repo-auto` fills
  `## Repo` from git.
- **Evidence lives on record nodes**, never on state nodes.
- **State stays small.** Ten nodes today; the whole state graph should stay
  readable in one sitting. Reconcile compacts — the record graph keeps the
  detail.
- **Cite one slug per bracket.** `[rec: a] [rec: b]`, not `[rec: a, b]` — the
  I1 checker matches a single slug per citation.
- **Gaps are `open` state nodes, not task lists.** A claim phrased as
  state-of-the-world is falsified by work; a task list rots. An empty frontier
  on a project with known ambitions is a defect, not an achievement.
- **Bets are decision record nodes.** "Do X next, before Y, because Z" is a
  point-in-time decision and belongs in the record graph. Changing the plan
  never mutates anything — a new decision node supersedes the old bet.
