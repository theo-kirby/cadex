<!-- hypergraph:begin -->
## Hypergraph protocol

This repo's memory lives in the graphs under `.hypergraph/` (see `.hypergraph/AGENTS.md`)
— an append-only record of what happened, and one or more distilled views of what is
true now (the state graph always, plus any named views the config declares), with
every claim citing the evidence it rests on. Work that is not recorded did
not happen, and a dead end recorded is worth as much as a success:

1. **Orient on arrival**: run the `hypergraph-orient` skill or read `STATE.md` —
   the frontier (open/broken/blocked) is what matters now. To work a frontier gap
   deliberately (a target, a budget, a lane of your own), use the
   `hypergraph-dispatch` skill.
2. **Record every unit of work** (features, fixes, experiments, dead ends,
   decisions): the `hypergraph-record` skill — one causally-parented record node
   with a `## State Impact` section. Unrecorded work is invisible to the project.
3. **Never write state nodes**; declare impacts and let the
   `hypergraph-reconcile` skill fold them. `STATE.md` is generated — never
   hand-edit it.
4. **Verify before finishing**: `hypergraph sync` must exit 0 — it exports,
   regenerates `STATE.md`, checks, and publishes when a mirror is configured.
   If `check` says this project's copies are behind the CLI, run
   `hypergraph upgrade` — the skills and this block are copies, and `uv tool
   upgrade` cannot see them.
5. **Record on any branch; reconcile only on the default branch.** Record nodes
   are one file each and merge without conflict, so recording is always safe on
   a branch, fork or parallel lane — and it is the whole obligation there. The
   state graph has one writer: contributors record and open the pull request;
   the maintainer reconciles once after the merge.
<!-- hypergraph:end -->
