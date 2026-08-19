# Lane Providers

Dispatch runs an agent *at* a target somewhere it can work without colliding with
anyone else. That somewhere is a **lane**: an isolated checkout with its own branch,
provisioned by a provider, harvested back into the repo when the work is done. This
table is the provider seam — what any lane provider must satisfy for the
hypergraph-dispatch skill and the `hypergraph dispatch` CLI to hold unchanged.

**One provider ships**: **local** — a git worktree on a `lane/<slug>` branch,
driven by `hypergraph dispatch`. A **box** provider (a remote, sandboxed machine
per lane) is the named future direction; it is documented here as a seam and
deliberately not implemented.

Lanes are a **tool property, not protocol**. Nothing in SPEC.md's invariants knows
lanes exist: a dispatched agent is an ordinary contributor (SPEC: Collaboration)
whose record nodes arrive by ordinary git merge. A project that never dispatches
loses nothing; a provider that violates this table breaks dispatch, not `check`.

## Operations

| # | Operation | Signature (conceptual) | Notes |
|---|-----------|------------------------|-------|
| 1 | `provision` | `(spec) → lane` | Mint an isolated workspace at the current published state. **The provider mints the lane identity; the dispatching agent never names it.** |
| 2 | `inject` | `(lane, scripts, credentials) → ()` | Deliver what the lane needs to run. **Via stdin, never argv.** |
| 3 | `run` | `(lane, brief) → exit status` | Start the agent with the dispatch brief on stdin. Exit status attests **the harness ran** — never that the work succeeded. |
| 4 | `harvest` | `(lane) → arrived nodes` | Bring the lane's committed work back into the repo. **Strictly precedes teardown.** |
| 5 | `teardown` | `(lane) → ()` | Destroy the lane. **Refuses while unharvested.** |

## Contract notes

- **The provider mints lane identity (op 1).** An agent that names its own lane
  will eventually name someone else's: two dispatches that pick the same
  memorable name collide silently, and the collision surfaces as one agent's
  work in another's workspace. Minted identity makes collision structurally
  impossible — the same reasoning as minted node slugs. (Field lesson from the
  Harness hygiene state node, `fair-field-3265`: fleet discipline learned
  against live accounts.)
- **Scripts and secrets travel on stdin, never argv (op 2).** An argv is
  world-readable process state: it lands in `ps` output, shell history, crash
  reports, and process-monitoring logs for as long as the process runs. A lane
  provider that passes a credential — or the script that embeds one — as an
  argument has published it to every process on the machine. Stdin is a pipe
  with one reader. The same rule covers the dispatch brief (op 3): targets and
  attribution are not secrets, but the channel should not fork on a judgment
  call about what is sensitive.
- **Exit status is a harness fact, not a work fact (op 3).** An agent that ran,
  worked, and recorded honestly that the experiment failed exits 0. An agent
  whose harness crashed exits nonzero. Dispatch reads exit status to decide
  whether the *lane* is broken, and reads the record graph — the arrived nodes —
  to learn what the *work* found. Conflating the two turns every negative result
  into a retry.
- **Harvest strictly precedes teardown (ops 4–5).** The one irreversible mistake
  a provider can make is destroying work that was never brought home. Ordering
  it in the interface — teardown *refuses* while unharvested, rather than
  documentation asking nicely — makes the mistake unrepresentable. For the local
  provider, harvest is nearly free: the lane's work is commits on a `lane/<slug>`
  branch, so harvest **is a git merge** — which is the record graph's own merge
  story (SPEC: Collaboration, "the record graph merges for free") doing the
  work. A remote provider must add transport; it must not subtract the ordering.
- **Redaction happens in memory, before the first write.** Anything a lane
  captures that may hold secrets (transcripts, tool output, environment dumps)
  is scrubbed before it first touches disk in the harvested repo — a redaction
  pass that runs after writing has already leaked to the filesystem, to backups,
  and to git history. Providers that capture nothing beyond the lane's own
  commits (the local provider) satisfy this vacuously.
- **A lane is not a graph fork.** The lane branch carries ordinary record nodes;
  merging it is the same act as merging a contributor's pull request. No lane
  identity appears in the graph — the dispatch decision node (the lane claim)
  lives in the *record graph* and names the target, not the lane.

## The local provider

`hypergraph dispatch` implements this table with git alone:

- `provision` — `git worktree add` on a fresh `lane/<slug>` branch, slug minted
  by the CLI (op 1).
- `inject`/`run` — if `dispatch.agent` is configured, the agent command is
  launched with the lane directory substituted and the dispatch brief written to
  its stdin (ops 2–3). With no agent configured, `dispatch open` **stands down at
  exit 0** and prints the manual steps — the same posture as `push` with no
  mirror.
- `harvest` — merge `lane/<slug>` into the current branch; report which record
  nodes arrived (op 4).
- `teardown` — `dispatch close`: refuses while the branch is unmerged (`--force`
  to override, which is the operator saying the work is abandoned); then
  `git worktree remove` + branch delete (op 5).

A box provider would implement the same five rows against a remote machine —
provision a sandbox, inject over the wire, harvest as a fetch+merge — and
nothing above this section would change.
