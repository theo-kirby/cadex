# Flywheel Repository Adapter

The second implementation of [INTERFACE.md](INTERFACE.md), and opt-in: a project picks
it by declaring a `store:` block. The graphs' store of record becomes a **Flywheel local
repository** (`flywheel repo:*`, a `.flywheel/` directory at the main checkout's root),
and `.hypergraph/graph/` stays exactly what the [local adapter](local-adapter.md)
describes, one markdown file per node, but as a **gitignored working copy** of that
store, not as files committed in git.

```yaml
# .hypergraph/config.yml
store:
  kind: flywheel-repo
  flywheel_cli: 0.2.78     # pinned: a newer CLI can upgrade the repository format
```

Why a project would: the graph stops forking with the code. Every git worktree of the
checkout reads and writes the one graph instead of a branch slice of it, and the
repository syncs between machines through a hosted Flywheel repository
(`flywheel repo:push` / `repo:pull`). What it costs: record nodes stop appearing in
pull-request diffs and stop travelling with `git clone`, and
`check --since` changes meaning (below). Your project decides this; nothing above the
Storage section of SPEC.md changes either way.

Implementation: `tools/hypergraph_store.py`, which the core loads only when the block is
present. Tests: `tests/test_flywheel_store.py` (real CLI; skipped without it).

## How it works

The core is unchanged and still does all of its validation and file writing against
node files. The adapter wraps every command that is not read-only:

1. take an exclusive `flock` on `.hypergraph/store/lock` in the main checkout;
2. **refresh**: if the store's head moved past `.hypergraph/store/index.json` (another
   machine's commits arrived by `flywheel repo:pull`), re-materialize the nodes
   `repo:diff --base <index head> --head <head>` names, or every node when the old head
   left history (a rebase on pull);
3. run the command;
4. **push**: stage every node file whose bytes changed since the index (create, or set
   the changed fields; parents as lineage; non-root nodes contained under their
   graph's root) and commit once, with the command as the message (`hypergraph new
   record — <title>`).

`check`, `render`, `hwm` and `skills` never touch the store. `store` is the explicit
surface: `init`, `status`, `push`, `pull [--full]`, `verify`.

## Encoding

| Node file | Flywheel node |
|---|---|
| `slug` | `slug_name` (Flywheel accepts it on create) |
| `title`, `summary` | `title`, `summary` |
| frontmatter + body | `content` = body + `\n<!-- hypergraph:<kind>\n<frontmatter verbatim>-->\n` |
| `parents` | lineage relations, mirrored on every push |
| graph membership | containment under the graph's root node |
| `node_id` (`uuid5(slug)`), `created_at`, `artifacts`, `tags`, `origin` | the frontmatter, inside the trailer |

The trailer makes every file rebuildable byte for byte from the store alone, and it
renders invisibly on the hosted graph. Flywheel mints its own node ids and creation
times, and neither can be set on create. So the protocol's ids stay `uuid5(slug)`, and
the store's ids are bookkeeping in the index, the same rule as a mirror's slugs.

## Concurrency

A Flywheel repository has **one staging area**. Two writers staging at once sweep each
other's operations into the wrong commit, and the slower one's commit fails ("repository
head is stale"); this was measured. The lock serializes every stage-and-commit. It lives
in the main checkout, which `git rev-parse --git-common-dir` finds from any worktree, so
worktree agents share it. A batch interrupted mid-staging is recognized by its staging
digest (`own_staging` in the index) and discarded on the next push; staged work the
adapter did not leave is refused, never discarded.

A file edited locally while the same node changed in the store is a conflict: refresh
refuses and names the file instead of overwriting it.

## What changes for the protocol

- **Op 7's CAS** is unchanged (the body hash of the working-copy file), and the lock
  adds the store's own serialization underneath it.
- **`check --since <ref>`** cannot see record nodes in a git diff any more. It counts
  record nodes in the shared graph whose `created_at` is at or after the merge base's
  commit time. That is a weaker signal: it cannot tell whose branch a record belongs to.
- **Artifacts** stay repo-relative paths in frontmatter; the store does not take
  custody of bytes.
- **The mirror** (`hypergraph push`) still works but is redundant here: publish the
  repository itself with `flywheel repo:push`.

## Operating it

- New machine: clone the code, then put the repository at the checkout root. Use
  `flywheel repo:clone <id>` into a scratch directory and move its `.flywheel/` in, or
  `repo:restore` a backup into the root. Then run `hypergraph store pull --full` to
  write the working copy (about 2 minutes for 1,100 nodes).
- Adopting: add the `store:` block, gitignore `.flywheel/`, `.hypergraph/graph/` and
  `.hypergraph/store/`, run `hypergraph store init` (about 1.3 s per node), then
  `hypergraph store verify`, then `git rm -r --cached .hypergraph/graph`.
- Leaving: delete the `store:` block, un-ignore `.hypergraph/graph/` and commit the
  working copy. The node files are the local adapter's format already.
- Cost: each write is about 0.25 to 0.6 s per Flywheel call (Node start-up, and it grows
  with repository size), so a record node is about 2 s. Reads stay file-speed.
