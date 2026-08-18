# Hypergraph Protocol — v0.0.8

Hypergraph is a **substrate for autonomous research and engineering**: the memory
layer an agent needs to carry real work across months and across contexts without a
human holding the thread.

The failure it targets is structural rather than a matter of agent capability. A chat
log is not memory. A codebase records what was kept and never what was tried and
rejected. A task list rots as soon as reality moves. So each fresh context re-derives
what the last one knew, repeats dead ends nobody wrote down, and contradicts decisions
it never saw. The protocol's whole job is to make those outcomes unavailable: give
knowledge somewhere to go, make being wrong a first-class result, and put *what is
true now* in front of an arriving agent instead of everything that ever happened.

Mechanically it maintains **two graphs per project**, kept as [markdown files committed
in the repo](backend/local-adapter.md):

- **Record graph** — the append-only historical log of everything that happened:
  decisions, experiments, evidence, dead ends. Topology is causal/chronological.
- **State graph** — a small, single-writer, distilled projection of what is true *now*:
  the project's architecture, what currently works, what's broken or open (the
  **frontier**), and accumulated negative knowledge. Topology mirrors the project's
  architecture (components/capabilities), not history.

Every state node cites the record nodes it derives from. A claim answers to many pieces
of evidence and a piece of evidence bears on many claims, so those citations join sets
to sets across two graphs rather than forming a tree — that cross-graph structure is
the "hypergraph", and it is what makes any claim auditable back to what it rests on.

The point: a fresh agent landing on a mature project should orient to the frontier in a
handful of tool calls instead of traversing thousands of record nodes.

**Maturity, stated plainly.** The record graph is established practice — an append-only
causal log of what was done and why is a lab notebook under another name, and this
implements a known good idea. The state graph, and the cross-graph citation structure
that falls out of it, is the novel and **actively developing** half: whether a
single-writer distillation stays small and honest as its evidence base grows without
bound, and whether agents genuinely orient better against it than against raw history,
is the open question this protocol exists to test. The invariants below are stable
enough to build on and the projection above them is a live hypothesis.

## Vocabulary

- **Record node** — a node in the record graph. Immutable once committed (append-only
  discipline; the backend may technically allow edits, the protocol forbids them except
  for typo-level fixes that don't change meaning).
- **State node** — a node in the state graph. Mutable, rewritten in place by
  reconciliation. Represents one component/capability/concern of the project.
- **Slug** — a node's immutable human-readable handle: `adjective-noun-####` (e.g.
  `quiet-snow-3839`). Slugs are how the two graphs point at each other; cross-graph
  pointers are **structured markdown, never graph edges** — graph edges between the two
  DAGs would topologically merge them.
- **Frontier** — the set of state nodes with status `open`, `broken`, or `blocked`.
  This is what a fresh agent should read first.
- **High-water mark (HWM)** — the *frontier* of record tips whose declared state impact
  has been folded into the state graph. A record node is reconciled when it is an
  ancestor of one of them; a linear record graph has exactly one tip.
- **Reconcile** — the single-writer pass that folds record-node impact declarations
  into the state graph and advances the HWM.

## Invariants

Numbered invariants are the protocol. I2, I4, I5, I6, and I7 are mechanically enforced
by `tools/hypergraph.py check`; I1, I3, and I8 are procedural (enforced by the skills),
with the checker reporting proxies where it can.

### I1 — Record-first

No knowledge exists only in the state graph. New information (results, decisions,
failures, insights) lands in the record graph first; the state graph is a *projection*,
never the primary home of anything. Every state edit is triggered by, and cites, at
least one record node.

*Checker proxy:* claims in a state node's `## Current` section with no inline
`[rec: <slug>]` citation are reported as warnings.

### I2 — Impact declaration

Every record node except the record root carries a `## State Impact` section, parseable
as one of:

1. One or more impact lines:
   - `- target: <state-slug> — <delta>` — the delta to fold into an existing state node.
   - `- target: NEW <kebab-name> — <delta>` — reconcile should create a new state node.
2. Exactly `none: <reason>` — an explicit declaration that this node changes nothing
   about current state, with a non-empty reason.

`<state-slug>` must resolve to an existing state node. `<delta>` is a non-empty
human-readable description of what changes (status flip, new claim, new negative
knowledge, supersession). Writing the impact is the *recording* agent's job — it is a
declaration, not a state write (see I3).

**Adoption-epoch exemption**: when the project config declares an epoch marker
(see Conventions: Adoption epochs), record nodes created *strictly before* the
marker node are legacy history and exempt from this invariant — the checker
reports their count as info instead of flagging them. The exemption is
check-time only: authoring a new record node is never epoch-exempt.

### I3 — Single-writer state

Only the reconcile pass writes state nodes. Recording agents — including many running
in parallel — only ever append record nodes with impact declarations. This avoids
stage-lease contention on hot state nodes and prevents weakest-agent drift in the
distilled projection. Procedural; the reconcile skill is the only skill that acquires
leases on state nodes.

### I4 — Provenance

Every state node except the state root has a `## Provenance` section listing the record
slugs it derives from, one per line:

- `- <record-slug> — <why this record node informs this state node>`

Every slug in `## Provenance` must resolve to a record-graph node. Claims in
`## Current` cite record slugs inline with `[rec: <slug>]`; every inline citation must
also resolve. Provenance is many-to-one: a state node typically cites many record nodes.

### I5 — High-water mark

The state root's content carries a `## Reconciliation` section:

```
## Reconciliation
- high_water_mark: <record-slug[, record-slug…] or none>
- reconciled_at: <ISO-8601 timestamp>
```

The mark is a **frontier**: the set of record tips whose entire ancestry has been folded
into state. A record node is *reconciled* exactly when it is an ancestor of some tip in
the frontier, itself included; everything else is **unreconciled** — enumerable by the
checker, which reports their count and per-state-node staleness. Unreconciled nodes are
normal between reconcile runs; a missing tip, or one that does not resolve to a record
node, is a violation.

Reachability, never wall-clock. The record graph is append-only but not linear: any
merge of concurrent work gives it several tips, and no single tip dominates the others.
A node authored before the last reconcile and merged after it is *not* an ancestor of
the frontier, so a rule that compares timestamps reports it as already folded and drops
it from the frontier permanently, with no violation anywhere. Clock skew between
machines widens the window. One tip — what a project with a linear record graph writes,
and the only form this section had before v0.0.5 — is a frontier of one.

`hypergraph hwm` reports the frontier and what is outstanding. `hwm --suggest` prints
the frontier that expresses, in ancestry, what the pre-v0.0.5 timestamp rule treated as
reconciled; a project upgrading across that change adopts it once, in a reconcile pass.

### I6 — Status vocabulary

The first non-blank line of every state node except the state root is:

```
Status: working | open | broken | blocked | superseded
```

- `working` — implemented and believed correct.
- `open` — planned/known-unknown; work not yet done.
- `broken` — was working or attempted, currently fails.
- `blocked` — cannot proceed until something outside this node changes.
- `superseded` — replaced by another state node (name it in `## Current`).

**Frontier = open ∪ broken ∪ blocked.**

### I7 — Negative knowledge

Entries in a state node's `## Negative knowledge` section are scoped,
confidence-rated, and evidence-cited:

```
- [scope: <where this applies> | confidence: low|medium|high | evidence: <slug>, <slug>] <statement>
```

An optional `| decision: <record-slug>` field cites the decision record that authorized
a generalization. If `scope` begins with `general`, the `decision:` field is
**required**: generalizing "2 failures" into "this approach is dead everywhere" is
itself a decision and needs its own decision record node. Evidence and decision slugs
must resolve to record nodes.

### I8 — Rebuildability (audit definition)

A re-derivation of any state node from its cited record nodes must be *semantically
equivalent* to the committed state node — same status, same claims, same negative
knowledge, possibly different wording. This is audit-grade provenance, not byte
determinism.

*Spot-check procedure:* pick a state node; fetch only the record nodes listed in its
`## Provenance`; without looking at the state node body, write down status + claims +
negative knowledge you'd derive; compare. A mismatch means either provenance is
incomplete (fix: add the missing record slugs, or record the missing knowledge first —
I1) or reconcile hallucinated (fix: rewrite the state node from its citations).

## Conventions (skill-enforced)

- **Record topology is causal.** Choose a record node's parent by causal relation —
  "this work followed from that result" — not recency, and never default to root-only
  branching. Independent workstreams may branch from the root.
- **State topology mirrors architecture.** State children of the state root are the
  project's components/capabilities. Depth stays shallow (2–3 levels). Reorganizing
  state topology is a reconcile-only operation and needs a decision record node.
- **Record nodes carry repo context.** When code is involved, record the repo, branch
  and commit SHA in `## Repo` (`hypergraph new record --repo-auto` fills it from git).
- **Evidence lives on record nodes.** Artifacts (logs, plots, datasets) attach to
  record nodes, never state nodes. State nodes point at them via provenance slugs.
- **State stays small.** The whole state graph should be readable in one sitting.
  Reconcile compacts: merge redundant claims, drop superseded detail (the record graph
  keeps the history), keep negative knowledge tight.

## Collaboration

More than one person or agent works most repos: worktrees, branches, a fork and a pull
request, a fleet of cloud agents. The two graphs already split along the line that git
merges on, so the rule follows from the invariants rather than extending them.

- **The record graph merges for free.** It is append-only with one file per node, so two
  branches produce two new files and a merge produces no conflict. The merged graph shows
  the fork truthfully: concurrent nodes share a parent, and the DAG records that they
  were concurrent. A slug collision across branches is an add/add conflict on the same
  filename — loud, which matters because the node id is derived from the slug.
- **The state graph has one writer** (I3), so concurrent branches edit the same files.

Therefore: **contributors record; the maintainer reconciles.** A pull request carries
facts — new record nodes, which merge cleanly and arrive in the diff as files, so the
claim is reviewed beside the code that justifies it. The default branch carries claims.
Reconcile runs there, once, over everything merged since the last pass; a single pass
across a batch produces one coherent claim where N passes produce N overlapping edits.

- **Publish from the default branch only.** A mirror is a projection of published
  history — a build artifact of the branch, like a docs site. Publishing from a feature
  branch puts nodes on an append-only store that may never merge, and an append-only
  store has no clean retraction. `hypergraph push` stands down at exit 0 anywhere else,
  and on a clone whose credentials are not the mirror's owner, so the reconcile workflow
  is identical for a maintainer and a contributor. CI passes `--require-mirror`, because
  that is the one place a silent no-op is indistinguishable from a healthy deploy.
- **After a merge, `sync` rather than `check`.** The checker reads exports; a stale cache
  hides every merged node.
- **Never commit a conflict marker.** A node body git's merge driver wrote satisfies
  every other invariant. The checker rejects it, at authoring time and at check time,
  because a published record node is immutable and the damage would be permanent.
- **A repo fork is not a graph fork.** Forking a repository on a hosting service copies
  the graph verbatim — same slugs, same node ids — and that is correct: the fork is the
  same project, and a pull request merges back into the same graph. `import --fork`
  means something else entirely: starting a *new* project from someone else's graph,
  which mints new identity and files the source under `archive:` (see below).

## Adoption epochs

Projects that adopt Hypergraph mid-life have history the protocol cannot retrofit:
imported legacy graph nodes (or none at all) that predate the templates. The
adoption boundary is an **epoch marker** — the "Adopted Hypergraph" decision record
node written by the hypergraph-adopt skill — declared in config:

```yaml
epoch:
  marker: <record-slug>   # nodes created strictly before the marker's created_at are legacy
```

- Record nodes created strictly before the marker are exempt from I2/template
  compliance; `check` reports the exempted count as info. Everything at or after
  the marker is held to the full protocol. Authoring is never epoch-exempt.
- An unresolvable `epoch.marker` is a violation — a silently ignored epoch would
  re-flag every legacy node.
- **Parentage**: with a fully imported legacy graph, the marker's causal parent is
  the newest legacy node; in a ground-up (mode-B) adoption it is the newest
  authored prehistory node — both resolve locally, and a graph has exactly one
  parentless root. Only in epoch-split mode (huge graphs; older history left on
  the archive) is the marker itself the local record root, recording the archive
  lineage in its content — parent slugs that don't resolve locally are rejected,
  so an edge pointing into the archive is not representable in the first place.
- Legacy history is never truncated: it is either imported verbatim or referenced
  via the config's `archive:` block (see hypergraph-adopt).
- **A full import is a fork.** The imported nodes keep the archive's ids as
  provenance only (`origin:` in the node file); the repo becomes the continuing
  graph and owns its whole history, with the original topology. The archive stays
  frozen and read-only: it is the artifact pointer and nothing more.
- **Artifacts do not travel.** The storage layer has no artifact operation, so
  anything the archive holds as an attachment stays on the archive. A continuing
  graph must say so explicitly rather than let its completeness be assumed.
- **A continuing graph is not a copy of the graph it forked from.** Lineage is
  content: it belongs in a node body that names the archive and states what did and
  did not come across — never in a title, and never as a structural pretence that
  the two graphs are one. (If the project also mirrors itself to a hosted store, the
  mirror projects the repo and never the archive; mechanics live in
  [backend/mirror.md](backend/mirror.md).)

## Forward work and Operator directives

The state graph carries intent as well as fact — but never as task lists.

- **Gaps, not tasks.** Future work is represented as `Status: open` state nodes (or
  open children of a `working` component): claims that a capability does not exist or
  is incomplete. Claims phrased as state-of-the-world cannot rot the way task lists
  do — they are falsified by work, and the falsification channel is I2: whoever does
  the work must declare `target: <node> — status open → working`. An empty frontier
  on a project with known ambitions is a defect, not an achievement.
- **Bets are decision records.** "Do X next, before Y, because Z" is a point-in-time
  decision, not a state fact. It lives in the record graph as an immutable decision
  node; execution nodes later become its children. Changing the plan never mutates
  anything — a new decision node supersedes the old bet, and reconcile updates
  whatever the state graph claims about current priorities.
- **Operator directives enter through the record graph.** When the Operator (or any
  agent) introduces a new direction — a feature, a research thrust, a constraint —
  the flow is: (1) a decision record node capturing the intent, constraints, and
  rationale, attributed to its source; (2) a `## State Impact` section declaring
  `NEW <node>` or deltas to existing state nodes; (3) reconcile folds it, so the gap
  appears on the frontier with provenance. Nothing lands in the state graph without a
  record pointer — I1 applies to intent exactly as it applies to results.
- **Granularity.** Architectural capabilities and known gaps earn state nodes.
  Fine-grained tasks ("fix this function") belong in neither graph. Open nodes are
  the most expensive kind to carry — each is a standing claim the frontier surfaces
  to every arriving agent.
- **The arriving agent decides.** Decision records preserve why the last bet was
  made; they do not bind the next agent. Overriding a prior bet is done by writing a
  new decision record — disagreement is recorded, never silent.

## Node templates

Exact headings are load-bearing — the checker parses them. See
[templates/record-node.md](templates/record-node.md) and
[templates/state-node.md](templates/state-node.md).

- Record node content: `## What / ## Why / ## Method / ## Result / ## Repo / ## State Impact`
- State node content: `Status:` line, then `## Current / ## Negative knowledge / ## Provenance`
- State root content: project overview + `## Reconciliation`

## Per-project files

Created by the `hypergraph-init` skill (day zero) or the `hypergraph-adopt` skill
(projects with a past) in the target repo:

- `.hypergraph/config.yml` — project name, record root and state root (node_id + slug);
  adopted projects add `epoch:` and, for imported legacy graphs, `archive:` (which
  also feeds `push --lineage`). `hypergraph_version:` records which release last
  installed this project's *copies* of what the tooling ships — the skills, the
  AGENTS.md block, the workflows — which nothing else in the repo names; it is not a
  compatibility floor, because node files are additive and an older reader is fine on
  a newer graph. See [templates/config.example.yml](templates/config.example.yml).
- `.hypergraph/graph/{record,state}/<slug>.md` — the node files: frontmatter carrying
  identity and parent slugs, body carrying the content verbatim. One optional block is
  protocol — **`origin:`**, where an imported node came from (immutable provenance,
  written once by `import --fork`). A **`flywheel:`** block may also appear: mirror
  bookkeeping that `push` writes and nothing else reads, `check` included.
- `.hypergraph/cache/{record,state}.json` — graph exports consumed by the checker and
  renderer (gitignored; regenerated by reconcile).
- `STATE.md` — generated snapshot of the state graph (regenerated by reconcile, never
  hand-edited). Frontier at the top, architecture tree below.
- `AGENTS.md` sentinel block (`<!-- hypergraph:begin/end -->`, from
  [templates/agents-block.md](templates/agents-block.md)) + `.hypergraph/AGENTS.md` —
  the onboarding contract installed by adopt, kept idempotent by the markers.

## Tooling

`tools/hypergraph.py` (single-file uv script) consumes JSON exports — no auth, no
network, deterministic, CI-ready:

```
uv run tools/hypergraph.py check  --record .hypergraph/cache/record.json --state .hypergraph/cache/state.json
uv run tools/hypergraph.py render --state .hypergraph/cache/state.json --config .hypergraph/config.yml -o STATE.md
uv run tools/hypergraph.py viz    --record .hypergraph/cache/record.json --state .hypergraph/cache/state.json --config .hypergraph/config.yml -o .hypergraph/viz.html
```

`check` exits nonzero on any I2/I4/I5/I6/I7 violation. `viz` emits a self-contained
interactive HTML visualization (no network, no JS dependencies): a single
toggleable view over both graphs — with presets reproducing the classic record,
state, columns, and force arrangements, plus an everything-on default — where
`## Provenance` citations and `## State Impact` declarations are drawn as
cross-graph links — the markdown pointers made visible, still never graph edges.
An optional `viz: blob:` block in `.hypergraph/config.yml` presets the page's blob
geometry, so a tuning travels with the repo; it is display configuration only and
no invariant reads it.

## Storage

The node files **are** the storage: `.hypergraph/graph/<kind>/<slug>.md`, committed to
the repo ([backend/local-adapter.md](backend/local-adapter.md)). `hypergraph export`
turns them into the same JSON the checker consumes, so nothing above this section
depends on how they are kept. No network, no account, no service to be signed in to;
the graphs travel with the repo, work offline, and merge through git.

The protocol is nonetheless written against ~10 abstract operations
([backend/INTERFACE.md](backend/INTERFACE.md)). That is a **portability property, not a
choice to be made at init**: it states what a *replacement* store would have to
satisfy, and it is why nothing above this section mentions files. One implementation
ships.

Op 7 ("refuse a stale write") is satisfied by a body-hash compare-and-swap, and
`--reconcile` is the mechanical I3 gate — the only commands that write state nodes
refuse to run without it.

**Mirroring is optional, one-way, and out of band.** `hypergraph push` can publish
committed node files to a hosted graph the project owns (Flywheel), so the mirror is a
regenerable projection and the repo stays canonical. It is a property of the tool, not
of the protocol: **the skills do not know it exists**, and a project with no mirror
configured never touches that path. Mechanics: [backend/mirror.md](backend/mirror.md).

## Future work (out of scope for v0.0.5)

Committed forward work lives in the state graph as open frontier nodes (see Forward
work above) — for this repo, that is where field dogfooding is tracked. The list below
is speculative protocol machinery only, not yet worth a standing state claim:

- Repo-drift check: `check` warns when the repo HEAD is ahead of the newest record
  node's `head_commit_sha` — unrecorded work is otherwise invisible (unreconciled
  and unrecorded are different failure modes; the checker only sees the former).
- Export-freshness check: `check` warns when the cache export's `exported_at`
  predates recent activity — an agent that records after its last export leaves
  `check` reporting 0 unreconciled while the live graph is ahead.
- Hooks-based `unreconciled` auto-tagging of record nodes past the HWM.
- `provenance.json` machine-readable artifact per state node.
- One-only `current-best` tags for competing approaches.
- Artifacts (op 9) and tags (op 10), which the shipped storage does not implement.
- Bidirectional sync with a mirror. Today git is the merge substrate and the mirror is
  a one-way projection — with drift detection via `push --verify` and a mirror-only
  slug legend, but no slug translation inside mirrored bodies.
