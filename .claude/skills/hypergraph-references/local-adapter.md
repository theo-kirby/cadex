# Local (git-native) Adapter

Maps [INTERFACE.md](INTERFACE.md) operations to files in the repo and subcommands of
`tools/hypergraph.py`. No network, no MCP, no account: the graphs live in the working
tree and travel with the repo.

Facts the protocol relies on:

- **Node = one markdown file**: `.hypergraph/graph/<record|state>/<slug>.md`, committed.
  YAML frontmatter carries identity and edges; everything below the closing `---` is the
  node `content` byte-for-byte — the exact string the checker parses.
- **Slug = filename = frontmatter `slug`**, `adjective-noun-####` (`SLUG_RE`), minted on
  create and never rewritten. Slugs are the cross-graph pointer currency.
- **`node_id = uuid5(HYPERGRAPH_NS, slug)`** — deterministic, so ids are reproducible
  from the files alone and never depend on randomness or on a server.
- **`parents` holds slugs, not ids** — readable and diffable; `export` resolves them.
- **Git is the concurrency substrate.** Op 7 additionally carries a content-hash CAS
  (`--expect`) so a stale in-tree write is refused rather than silently applied.

```markdown
---
node_id: 3e64ea0a-f035-5204-8cf2-465735478d01
slug: bright-harbor-2001
title: local — state
created_at: '2026-08-02T00:00:00+00:00'
parents: []
summary: ''
origin:                         # only on nodes from `import --fork` (see §Importing)
  backend: flywheel             # immutable provenance; never a push target
  node_id: 8e1c…                # the archive's id
  slug: bright-harbor-2001      # the archive's slug — same as `slug:` above
  revision: 3
  exported_at: '2026-08-01T00:00:00+00:00'
flywheel:                       # bookkeeping, only once mirrored (see ../docs/internal/mirror.md)
  node_id: 9e68…
  slug: wild-river-2201
  revision: 3
  pushed_at: '2026-08-02T04:00:00+00:00'
  content_sha256: ab12…         # what was last pushed — the change detector
---
Status: working

## Current
…
```

Working fixture: [`tools/fixtures/local-graph/`](../tools/fixtures/local-graph/) — five
node files plus the JSON they export to.

## Operation mapping

### 1. `create_root` → `hypergraph new <kind> --root`

```bash
hypergraph new record --root --title "<project> — record" --body record-root.md
hypergraph new state  --root --title "<project> — state"  --body overview.md \
                      --reconcile [--hwm none]
```

The state root's `## Reconciliation` block (`high_water_mark`, `reconciled_at`) is
generated for you (SPEC I5). Each command prints the minted slug as its first stdout
field — capture it (`SLUG=$(hypergraph new … | awk '{print $1}')`) and write both roots'
`node_id` + `slug` into `.hypergraph/config.yml`. A second root per graph is refused.

### 2. `append_record_node` → `hypergraph new record`

```bash
hypergraph new record --title "…" --body body.md \
    --parent <causal-slug> [--parent <second-causal-slug>] \
    --impact "<state-slug> — <delta>" [--impact "NEW <kebab-name> — <delta>"] \
    --repo-auto
```

`--body` carries the prose sections (`## What / ## Why / ## Method / ## Result`) and
accepts `-` for stdin. The CLI **generates** `## Repo` (from local `git` reads when
`--repo-auto`) and `## State Impact` (from the flags), so the machine-parsed sections
are well-formed by construction. Use `--none "<reason>"` instead of `--impact` when
current state truly doesn't change. Multiple `--parent` flags = multiple causal parents.

Before writing, the command runs the real checker over the candidate node: an impact
target that resolves to no state node, an unparseable impact line, or a missing
`## State Impact` fails at authoring time (exit 2, nothing written) rather than at
`check` time.

### 3. `read_node` → read the file

`.hypergraph/graph/<kind>/<slug>.md`. Frontmatter above the second `---`, content below.
For op 7 you also want the body hash: `hypergraph update <slug> --print-sha`.

### 4. `list_children` → grep the `parents` frontmatter

```bash
grep -l "^- <slug>$" .hypergraph/graph/state/*.md      # block-style parents list
```

Or, structurally, read the exported JSON — for the state graph that is one small file.

### 5. `get_tree` → `STATE.md`

`hypergraph render` already emits the state graph as an indented tree, frontier first.
Orientation under this backend is two file reads (`.hypergraph/config.yml`, `STATE.md`),
not a traversal.

### 6. `resolve_slug` → the path *is* the resolution

`.hypergraph/graph/<kind>/<slug>.md` exists or it doesn't; filenames are unique per
graph, so ambiguity is structurally impossible. `load_local_nodes` errors if a filename
and its frontmatter `slug` disagree.

### 7. `update_state_node` → `hypergraph update` (read → compare-and-swap)

Reconcile only (SPEC I3). The full safe sequence:

```bash
SHA=$(hypergraph update <slug> --print-sha)      # 1. read the current body hash
# 2. compose the complete new content locally (state-node template) → new.md
hypergraph update <slug> --body new.md --expect "$SHA" --reconcile
```

- `--expect` is the optimistic lock: if the body changed since you read it, the write is
  refused (exit 2) with both hashes, and the file is left untouched. Re-read, re-fold
  your delta onto the current content, retry. This is INTERFACE's "the backend should
  still refuse a stale write".
- `--reconcile` is the I3 gate: without it the command refuses to touch any state node
  and points at the reconcile skill.
- Record nodes are refused outright — the record graph is append-only; corrections are
  new child nodes.
- `--body` is a **full replace**, like the Flywheel adapter's payload. Compose the whole
  node, not a diff. The new content is checker-validated before the write lands.

### 8. `export_graph` → `hypergraph export`

```bash
hypergraph export --config .hypergraph/config.yml       # → .hypergraph/cache/{record,state}.json
```

Emits the canonical export shape (`node_id`, `slug_name`, `title`, `content`, `summary`,
`tags`, `artifacts`, `parent_ids`, `created_at`), nodes ordered by `created_at` then `node_id` per
INTERFACE's determinism note. This is the *whole* integration surface: `check`,
`render`, and any external renderer (hypergraph-viz) consume these files without
knowing which backend produced them.
The cache stays gitignored — it is regenerable from the node files at any time.

### 9. `attach_artifact` — repo-relative paths in frontmatter

A record node names the files its claims rest on in an `artifacts:` list, omitted
entirely when empty:

```yaml
artifacts:
  - research/runs/2026-08-14/train.log
  - plots/loss-curve.png
```

```bash
hypergraph artifacts add <record-slug> plots/loss-curve.png   # cwd-relative, like `git add`
hypergraph artifacts ls                                       # every path, with what is wrong with it
hypergraph artifacts mv <record-slug> OLD NEW                 # after a `git mv`, in position
hypergraph new record --artifact plots/loss-curve.png …       # at authoring time
```

Input is **cwd-relative**, exactly as `git add` takes it; storage is
**repo-root-relative** with POSIX separators, because that is the form that survives a
clone. The repo root comes from `--repo`, else `git rev-parse --show-toplevel`, else
cwd — deliberately *not* a config key, since an absolute path committed into the repo
goes stale the moment the checkout moves and takes every artifact path with it.

**The body and the list are both required, and they are not the same thing.**
`## Method` / `## Result` is where a path is *explained* — what the run was, why the
plot shows what it shows, what you concluded. `artifacts:` is where it is *enumerated*,
so a tool can find it without parsing prose. The prose is the claim; the list is its
index. Dropping the prose leaves a file nobody can interpret; dropping the list leaves
evidence no `check` or `push` can see. Keep both.

**Record nodes only.** `artifacts:` on a state node is a `check` violation: a state
node is rewritten on every reconcile, so a pointer hung there has no stable owner. The
route is one hop and already exists — `## Provenance` cites the record node, and the
record node carries the files.

**Editing `artifacts:` on a committed record node is legal, and this is why.** The
record graph is append-only in its *bodies*: the node's `sha256` — what the CAS in
op 7 locks on, what `push` compares, what `push --verify` rests on — hashes the body
alone. Frontmatter a tool owns has always been outside that boundary; `push` stamps
`flywheel:` into frozen nodes on every run, and `upgrade --graph tags` rewrites `tags:` on nodes
years old. `hypergraph artifacts` never touches the title, the summary or the body, so
it cannot reach the hash. `hypergraph update` still refuses record nodes outright: a
correction to a *claim* is a new child node, never an edit.

`check` reports paths that are wrong about the world — moved, listed twice, resolving
outside the repo, spelled in a case that only resolves on macOS — as **warnings, and
still exits 0**. An artifact is often a gitignored dataset a fresh clone was never
going to have, and failing CI over its absence would make the feature useless for the
evidence it exists to hold. A project that declares no artifacts hears nothing at all.

**STATE.md does not change, deliberately.** State nodes cannot carry artifacts, and
inlining the artifacts of every cited record node would churn the file on each
reconcile and destroy the property that makes it useful — readable in one sitting. The
pointer chain is already one hop: STATE.md → the state node's `## Provenance` →
`hypergraph artifacts ls <record-slug>`.

Mirroring these files to a hosted graph is a separate concern, under "Mirroring to a
hosted graph" below and in [mirror.md](../docs/internal/mirror.md). The repo stays canonical; the
mirror holds a copy.

### 10. `tag` *(optional)* — frontmatter plus a committed vocabulary

Assignment is a `tags:` list of **names** in the node's frontmatter, omitted entirely
when empty. The vocabulary — colours, `one_only`/`track_history` flags, and whatever
id a mirror minted — lives in a committed `.hypergraph/tags.yml`, keyed by graph kind
because declaration is per graph root and this protocol has two:

```yaml
version: 1
record:
  - name: kind:experiment
    bg_color: '#1F3A5F'
    text_color: '#E8F0FB'
    flywheel: {tag_id: tag-e71abca66e6c, root_node_id: …, pushed_at: '…'}
  - name: studio-baseline
    archive_name: "★ studio-baseline"   # kept when import had to transliterate
    one_only: true
    track_history: true                 # declarative input to a backend that has it
state: []
```

```bash
hypergraph tags list                        # the vocabulary plus usage counts
hypergraph tags add kind:experiment         # never hand-edit the file
hypergraph new record --tag kind:experiment …
```

Three things worth stating rather than discovering:

- **The file is optional.** An undeclared name still works and takes a colour derived
  from its own digest, so two machines agree without coordinating. Absent means "this
  project declares no vocabulary", not "this project has no tags".
- **It is not in `config.yml`.** `push` has to *update* entries in place to stamp the
  ids a mirror minted, and `config.yml` is only ever appended to textually so its
  hand-written comments survive.
- **`check` is tag-blind**, with one exception: where `tags.yml` exists, an undeclared
  name is a *warning*. Never a violation — no invariant reads a tag, and failing a
  build over one would invent an obligation the spec does not carry.

The tag id a mirror minted is bookkeeping, not identity: names travel, ids do not.
See [mirror.md](../docs/internal/mirror.md) for how `push` publishes them, and for
`hypergraph upgrade --graph tags`, which carries them into a repo that adopted
before any of this existed.

## Importing an existing graph

`import` explodes graph-export JSON into node files, preserving the source `node_id` and
`slug_name` **verbatim** — so an existing project's config, provenance slugs, and HWM
all stay valid across the migration:

```bash
# fetch the export first — `hypergraph mirror pull` writes both files (../docs/internal/mirror.md), then:
hypergraph import --record .hypergraph/cache/record.json \
                  --state  .hypergraph/cache/state.json
git add .hypergraph/graph && git commit -m "Import the graph into the repo"
```

`import` is idempotent (unchanged files are skipped) and refuses to clobber a differing
file without `--force`. It stamps each node's `flywheel:` block so the mirror knows what
has already been pushed — this is the **re-home** case: you own the source graph and
you keep mirroring to it, so its ids stay the push target. Do not pass `--fork` here.

**Adopting a project with a pre-protocol past** (the hypergraph-adopt skill, mode A):
`import --fork`. The graph you are importing belongs to somebody else, so the copy
takes its own mirror identity:

- node_ids and slugs are preserved verbatim, as always — config, provenance slugs and
  the HWM stay valid;
- the source ids are written to **`origin:`** (`backend`, `node_id`, `slug`,
  `revision`, `exported_at`) — immutable provenance, read by nothing;
- **`flywheel:` is omitted**, so `push --plan` plans every imported node as a `create`
  under roots this project owns. The project re-publishes its whole imported history
  with the original topology (SPEC: Adoption epochs).

Getting this wrong is silent in both directions: import a foreign graph *without*
`--fork` and the mirror push omits every legacy node (nothing is created, `--verify`
still passes if the archive is spliced into the export); import your own graph *with*
`--fork` and the next push duplicates the entire graph.

The source graph stays untouched as the frozen archive (`archive:` in config). An
*archive's* attachments do **not** survive import: op 9 travels repo-relative paths,
and the archive's bytes are not in this repo, so the archive reference stays the only
pointer to them and `push --lineage` says so at the mirror record root (below).
`hypergraph upgrade --graph artifacts` records an inventory of what the archive holds under
`origin.artifacts` — where they are, never a copy of them. Artifacts *recorded after
adoption* are ordinary repo files and travel with the repo like everything else. In epoch-split mode (huge graphs, history left on the archive) the marker
is authored with `--root`: node files can only parent on slugs that resolve locally, so
the archive lineage is recorded in the marker's content instead of as a parent edge.

## Mirroring to a hosted graph

Optional, one-way, and **not part of this adapter**: `hypergraph push` can publish the
committed node files to a Flywheel graph the project owns, so the mirror is a
regenerable projection and the repo stays canonical. The CLI does all of it — there is
no plan for a caller to execute and no MCP call to make by hand.

Mechanics, failure modes and the re-homing migration: [mirror.md](../docs/internal/mirror.md).

## Failure handling

- All local-backend errors exit **2** with a one-line `error:` on stderr; `check` keeps
  its own 0/1 contract. `push --plan` exits 1 when the plan carries violations. The
  canonical exit-code table is in [docs/cli.md](../docs/cli.md).
- Structural problems are caught on load, not silently tolerated: slug not matching
  `SLUG_RE`, filename ≠ frontmatter slug, duplicate `node_id`, missing or unparseable
  `created_at` (the unreconciled/HWM partition is timestamp-ordered), a parent slug with
  no node, malformed frontmatter.
- Concurrency: single-writer by protocol, `--expect` by mechanism, git by substrate.
  Two agents reconciling at once produce a merge conflict in `.hypergraph/graph/state/`,
  which is the honest outcome — resolve it in git, then re-`export` and `check`.
