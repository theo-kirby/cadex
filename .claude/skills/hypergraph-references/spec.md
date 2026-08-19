# Hypergraph Protocol — v0.0.13

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

A project may keep further named projections of the same record graph — **views**
(see Views). The state graph is the first and only mandatory one.

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
- **View** — a named, derived, single-writer graph over the record graph (see Views).
  The state graph is view #1: mandatory and privileged. Extra views are optional and
  declared per project.
- **View node** — a node in a named view. Same shape, template and invariants as a
  state node; "state node" in I4–I7 reads as "view node" within each view.
- **High-water mark (HWM)** — the *frontier* of record tips whose declared impact
  has been folded into a view. Each view carries its own; a record node is reconciled
  for a view when it is an ancestor of one of that view's tips. A linear record graph
  has exactly one tip.
- **Reconcile** — the single-writer pass that folds record-node impact declarations
  into a view and advances that view's HWM.

## Invariants

Numbered invariants are the protocol. I2, I4, I5, I6, and I7 are mechanically
enforced by `tools/hypergraph.py check`, alongside structural checks that are not
invariants (conflict markers, artifact placement, root identification). I1, I3, and
I8 are procedural (enforced by the skills), with the checker reporting proxies where
it can — and in `check --since <ref>` mode, I1 itself becomes mechanical across a
branch: changed files with no new record node fail the check.

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
   - `- target: <view>/<view-slug> — <delta>` and `- target: <view>/NEW <kebab-name>
     — <delta>` — the same two forms aimed at a named view (see Views). An
     unqualified target always means the state graph, so every pre-views record
     node keeps parsing.
2. Exactly `none: <reason>` — an explicit declaration that this node changes nothing
   about current state, with a non-empty reason.

`<state-slug>` must resolve to an existing state node; a qualified `<view>` must be
declared in the project config and its `<view-slug>` must resolve in that view.
`<delta>` is a non-empty human-readable description of what changes (status flip, new
claim, new negative knowledge, supersession). Writing the impact is the *recording*
agent's job — it is a declaration, not a state write (see I3).

**Adoption-epoch exemption**: when the project config declares an epoch marker
(see Conventions: Adoption epochs), record nodes created *strictly before* the
marker node are legacy history and exempt from this invariant — the checker
reports their count as info instead of flagging them. The exemption is
check-time only: authoring a new record node is never epoch-exempt.

### I3 — Single-writer state

Only the reconcile pass writes state nodes — and, with named views, the rule is
**single writer per view**: every view (the state graph included) is written only by
its reconcile pass. Recording agents — including many running in parallel — only
ever append record nodes with impact declarations. This avoids stage-lease
contention on hot state nodes and prevents weakest-agent drift in the distilled
projection. Procedural. Three writers ever pass the `--reconcile` gate: init and
adopt once each at setup (seeding and distilling), and the reconcile skill ongoing —
every view write after setup goes through it (`views add` minting a view root is
part of a reconcile pass by definition, hence its own `--reconcile` gate).

### I4 — Provenance

Every state node except the state root has a `## Provenance` section listing the record
slugs it derives from, one per line:

- `- <record-slug> — <why this record node informs this state node>`

Every slug in `## Provenance` must resolve to a record-graph node. Claims in
`## Current` cite record slugs inline with `[rec: <slug>]`; every inline citation must
also resolve. Provenance is many-to-one: a state node typically cites many record nodes.

### I5 — High-water mark

Every view root's content — the state root's, and each named view root's — carries a
`## Reconciliation` section:

```
## Reconciliation
- high_water_mark: <record-slug[, record-slug…] or none>
- reconciled_at: <ISO-8601 timestamp>
```

The mark is a **frontier**: the set of record tips whose entire ancestry has been folded
into that view. A record node is *reconciled* exactly when it is an ancestor of some tip
in the frontier, itself included; everything else is **unreconciled** — enumerable by
the checker, which reports their count and per-view pending impacts. The marks are
independent per view: a project reconciles its state graph and a named view on
different cadences without either lying about the other. Unreconciled nodes are
normal between reconcile runs; a missing tip, or one that does not resolve to a record
node, is a violation.

Reachability, never wall-clock. The record graph is append-only but not linear: any
merge of concurrent work gives it several tips, and no single tip dominates the others.
A node authored before the last reconcile and merged after it is *not* an ancestor of
the frontier, so a rule that compares timestamps reports it as already folded and drops
it from the frontier permanently, with no violation anywhere. Clock skew between
machines widens the window. One tip — what a project with a linear record graph writes,
and the only form this section had before v0.0.5 — is a frontier of one.

`hypergraph hwm` reports the frontier and what is outstanding (`--view <name>` for a
named view's). `hwm --suggest` prints
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
  Concretely: a record node carries an `artifacts:` list of **repo-relative paths**
  beside the prose that explains them, so the evidence is both interpretable and
  findable. A path is the portable identity — it survives a clone, a fork and a
  backend that mints its own ids (INTERFACE op 9). A state node carrying one is a
  violation: state is rewritten on every reconcile, so a pointer there has no stable
  owner.
- **State stays small.** The whole state graph should be readable in one sitting.
  Reconcile compacts: merge redundant claims, drop superseded detail (the record graph
  keeps the history), keep negative knowledge tight.

## Views

A **view** is a named derived graph over the record graph — the same construction as
the state graph, of which the state graph is simply the first instance. Mathematically
each view node is a hyperedge over record vertices (its provenance set); in
engineering terms a view is one projection over the shared event log. A project that
wants a second axis of distillation — an RL project tracking *policy evolution*, say,
beside its architectural state — declares a `policy` view instead of overloading the
state graph with it.

- **The record graph stays the sole ground truth.** I1 generalizes: no knowledge
  exists only in *a* view. Every view is rebuildable from the record nodes it cites.
- **The state graph is view #1 — mandatory and privileged.** The frontier, orient,
  and STATE.md all read the state graph and only it. Extra views are optional; a
  project with none is exactly a pre-views project.
- **View nodes are state nodes.** Same template (`Status:` / `## Current` /
  `## Negative knowledge` / `## Provenance`), and I4–I7 apply per view, with
  "state node" read as "view node". Provenance cites **record nodes only** —
  view-over-view provenance is not representable, so views cannot stack.
- **Single writer per view** (I3). Each view is written only by its own reconcile
  pass; recording agents reach it exclusively through view-qualified impact
  declarations: `- target: <view>/<slug> — <delta>` and
  `- target: <view>/NEW <kebab-name> — <delta>` (I2). Unqualified targets mean the
  state graph, which is why every pre-views record node — immutable by I1 — stays
  valid.
- **Reconciliation is per view** (I5). Each view root carries its own
  `## Reconciliation` over the record graph. `hypergraph views add` seeds a newborn
  view's high-water mark with the current record tips, so a late-born view starts
  caught up rather than owing the whole history a reconcile.
- **Declaration is config.** A view exists when the config's `views:` block names it
  (`hypergraph views add <name> [--md FILE] --reconcile` mints the root and appends
  the block). Names are kebab-case (`[a-z][a-z0-9-]*`), never `record`/`state`/`cache`
  (reserved), and never slug-shaped — the name qualifies impact targets, so the
  grammar owns its shape. An impact naming an undeclared view is an I2 violation.
- **Artifacts stay on record nodes** — the existing state rule, per view.
- Views export beside the classic pair (`cache/<name>.json`) and may render a
  snapshot beside STATE.md (`md:` in the config block).

**Compatibility.** The node-file format is unchanged — a pre-views CLI reads a graph
that uses views, ignores the `views:` config key, and never looks under
`graph/<view>/`. The one honest exception: pre-0.0.13 `check` reports a
view-qualified impact line as an I2 unparseable-line violation. That is
checker-strictness drift the versioning policy allows, but stated plainly: **a
project that adds views needs ≥0.0.13 tooling; projects without views are unaffected
in both directions.**

**Out of scope (v1), deliberately:** mirror push of extra views (`push` publishes
record+state only; views are rebuildable projections, and push notes the skip),
per-view status vocabularies or templates, view-over-view provenance, orient reading
extra views, dispatch targeting views, `views rm`/rename, `import`/`adopt --pull` of
view graphs, and per-view tag vocabularies.

(Naming note: an earlier, superseded state node titled "Views" — `lawful-ash-6222` —
described panels of the removed in-core visualizer; these named views are unrelated.)

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

### Dispatch and lanes

Dispatch is the act of pointing an agent at a target — a frontier node, a stated
goal, or a region of the state graph — and letting it work a bounded budget in an
isolated **lane**. It adds no invariant: a dispatched agent is a contributor by
definition, so contributors-record / maintainer-reconciles above covers it whole.

- **Dispatch enters through the record graph.** Every dispatch begins as a decision
  record node (`Dispatch: <target>`), causally parented on the target's provenance,
  with the work nodes arriving as its children. The same flow as any Operator
  directive (see Forward work) — intent is recorded before work exists.
- **The dispatch decision node is an advisory lane claim.** An unreconciled
  `Dispatch:` node with no closure line in a descendant marks the target as being
  worked. Other dispatches read the claims and pick elsewhere. The claim is
  advisory, never a lock: two agents that miss each other duplicate work — the
  merge story absorbs that — and nothing can corrupt, because neither writes state.
- **Lanes are a tool property, like the mirror.** Providers (git worktree today;
  see [backend/lanes.md](backend/lanes.md)) are CLI mechanics the protocol never
  reads. A project that never dispatches loses nothing.

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
- **An archive's artifacts do not travel.** What travels is a repo-relative path,
  and an archive's attachments are bytes on someone else's store — so anything the
  archive holds stays on the archive, and a continuing graph must say so explicitly
  rather than let its completeness be assumed. Artifacts *recorded after* adoption
  are ordinary repo files and travel with the repo like the node bodies do.
- **Tags travel; pointer-tag history does not.** Tag *names* come across on the
  imported nodes and into `tags.yml`, because a name is the tag's portable identity
  in the same way a slug is a node's. What does not come across is the move history of
  a one-only "current best" pointer: those hops carry a timestamp and no reason, so
  they are written into the **epoch marker's body as prose**. That routing is what
  makes it a decision rather than a loss — and it is the adopting agent's job, not the
  tool's, because only a human or an agent reading the graph can say *why* the pointer
  moved. A repo that adopted before tags travelled is repaired by
  `hypergraph upgrade --graph tags`, not by re-running the adoption.
- **A continuing graph is not a copy of the graph it forked from.** Lineage is
  content: it belongs in a node body that names the archive and states what did and
  did not come across — never in a title, and never as a structural pretence that
  the two graphs are one. (If the project also mirrors itself to a hosted store, the
  mirror projects the repo and never the archive; mechanics live in
  [docs/internal/mirror.md](docs/internal/mirror.md).)

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
- **Dispatch is this flow, aimed.** Working a frontier gap in a lane starts with the
  same decision-record shape — see Dispatch and lanes under Collaboration.

## Node templates

Exact headings are load-bearing — the checker parses them. See
[templates/record-node.md](templates/record-node.md) and
[templates/state-node.md](templates/state-node.md).

- Record node content: `## What / ## Why / ## Method / ## Result / ## Repo / ## State Impact`
- State node content: `Status:` line, then `## Current / ## Negative knowledge / ## Provenance`
  — and this is also the view-node template, verbatim (SPEC: Views).
- State root content: project overview + `## Reconciliation` — likewise every view root's.

## Per-project files

Created by the `hypergraph-init` skill (day zero) or the `hypergraph-adopt` skill
(projects with a past) in the target repo:

- `.hypergraph/config.yml` — project name, record root and state root (node_id + slug);
  adopted projects add `epoch:` and, for imported legacy graphs, `archive:` (which
  also feeds `push --lineage`); projects with named views add a `views:` block
  (`views.<name>.root` + optional `views.<name>.md`), written by `hypergraph views
  add`. `hypergraph_version:` records which release last
  installed this project's *copies* of what the tooling ships — the skills, the
  AGENTS.md block, the workflows — which nothing else in the repo names; it is not a
  compatibility floor, because node files are additive and an older reader is fine on
  a newer graph. See [templates/config.example.yml](templates/config.example.yml).
- `.hypergraph/graph/{record,state}/<slug>.md` — plus `graph/<view>/<slug>.md` per
  named view — the node files: frontmatter carrying
  identity and parent slugs, body carrying the content verbatim. One optional block is
  protocol — **`origin:`**, where an imported node came from (immutable provenance,
  written once by `import --fork`). An optional **`tags:`** list of names may also
  appear: annotation, and **no invariant reads it**. A claim that exists only
  as a tag is invisible to the
  protocol, so a claim belongs in a node body. `check` is tag-blind, with one
  exception: where `tags.yml` exists, an undeclared name is a *warning*. A
  **`flywheel:`** block may also appear: mirror bookkeeping that `push` writes and
  nothing else reads, `check` included.
- `.hypergraph/tags.yml` — optional, committed: the tag vocabulary (names, colours,
  flags, and whatever id a backend minted), keyed by graph kind because tag creation
  is per graph root; it covers `record` and `state` only — named views keep no
  per-view vocabulary. Absent means "this project declares no
  vocabulary", not "this project has no tags": an undeclared name still works and
  takes a colour derived from its own digest. Edited through `hypergraph tags`, never
  by hand — a hand-merged duplicate name is the one unrecoverable tag failure.
- `.hypergraph/cache/{record,state}.json` — plus `cache/<view>.json` per named view —
  graph exports consumed by the checker and
  renderer (gitignored; regenerated by reconcile).
- `STATE.md` — generated snapshot of the state graph (regenerated by reconcile, never
  hand-edited). Frontier at the top, architecture tree below. A named view with an
  `md:` target gets the same treatment beside it.
- `AGENTS.md` sentinel block (`<!-- hypergraph:begin/end -->`, from
  [templates/agents-block.md](templates/agents-block.md)) + `.hypergraph/AGENTS.md` —
  the onboarding contract installed by init and adopt, kept idempotent by the markers.

## Tooling

`tools/hypergraph.py` (uv script) consumes JSON exports — no auth, no network,
deterministic, CI-ready. The tooling is two files: the core, offline; and
`tools/hypergraph_mirror.py`, the optional mirror's networked half, which offline
commands never import at all:

```
uv run tools/hypergraph.py check  --record .hypergraph/cache/record.json --state .hypergraph/cache/state.json
uv run tools/hypergraph.py render --state .hypergraph/cache/state.json --config .hypergraph/config.yml -o STATE.md
```

The full subcommand reference and the canonical exit-code table live in
[docs/cli.md](docs/cli.md).

`check` exits nonzero on any I2/I4/I5/I6/I7 violation. `check --since <ref>` adds
the branch-mode I1 check: comparing `<ref>...HEAD`, work outside the graph with no
new record node added is a violation — the PR gate, and the only mechanism that
reaches a contributor who never read AGENTS.md.

**Visualization is not part of this tool.** The JSON exports
(`.hypergraph/cache/{record,state}.json`) are the contract: any external
renderer reads them and draws both graphs, with the markdown pointers made
visible — still never graph edges.

One command keeps an already-adopted project current, with two halves whose effects
cost different things — the `--graph` flag names the boundary. Bare **`upgrade`**
refreshes this project's *copies* of what the tooling ships — the skills, the
AGENTS.md block, the workflows — and every effect of it is `git checkout`-reversible.
**`upgrade --graph`** repairs *graph content*: a registry of typed repairs that carry
a capability backwards into a repo that adopted before the capability existed.
Because it rewrites the graph and may spend writes that cannot be un-spent, the graph
half is **detect-only until `--apply`** — the one place in this tooling where a dry
run is the default — and plain detected drift exits 0, since a capability that landed
after your adoption is not a broken invariant.

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
configured never touches that path. Mechanics: [docs/internal/mirror.md](docs/internal/mirror.md).

## Versioning

One version number covers the spec, the CLI and the shipped skills — the
`vX.Y.Z` in this document's header, held equal to the distribution by test.
Releases are listed in [CHANGELOG.md](CHANGELOG.md), which also names the
labels that were retracted without ever being published (0.9.0 is one; a repo
stamped with a retracted label re-stamps via `hypergraph upgrade`).

**What a minor bump (0.x → 0.y) may change:**

- Checker strictness — new violations, tightened parsing. A rule that flags a
  correct live graph is treated as a defect in the rule, and this repo's own
  graph is a standing regression test for that.
- The CLI surface — subcommands and flags may be added, renamed or removed
  (removals are announced one release ahead where practical; the `heal` alias
  and the `viz` stub are precedents).
- Prose output — the wording of `check` findings, progress lines and errors is
  **not** a contract. Machine consumers read the JSON exports and the exit
  codes, never the prose.

**What is stable:**

- **Invariant numbers are permanent.** I1–I8 mean what this document says they
  mean; a retired invariant's number is never reused, and a changed enforcement
  (as when I5 became an ancestry frontier at v0.0.5) keeps the number and
  documents the migration.
- **Exit codes are a contract**: 0 = success or a deliberate stand-down
  (no mirror configured, wrong branch, nothing to do); 1 = findings
  (violations, drift); 2 = usage or environment error (bad flags, missing
  config or export, refused operation). CI may rely on them.
- **The node-file format is additive.** An older CLI reads a newer graph; new
  frontmatter keys never change the meaning of existing ones, and the body
  hash (`sha256` over the body alone) stays the append-only boundary.
- **The export JSON shape** consumed by `check`/`render` — the keys the
  committed export-contract baseline pins.
