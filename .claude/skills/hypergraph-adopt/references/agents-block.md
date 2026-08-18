<!-- hypergraph:begin -->
## Hypergraph protocol

This repo's memory lives in two graphs under `.hypergraph/` (see `.hypergraph/AGENTS.md`)
— an append-only record of what happened, and a distilled projection of what is true
now, with every claim citing the evidence it rests on. Work that is not recorded did
not happen, and a dead end recorded is worth as much as a success:

1. **Orient on arrival**: run the `hypergraph-orient` skill or read `STATE.md` —
   the frontier (open/broken/blocked) is what matters now.
2. **Record every unit of work** (features, fixes, experiments, dead ends,
   decisions): the `hypergraph-record` skill — one causally-parented record node
   with a `## State Impact` section. Unrecorded work is invisible to the project.
3. **Never write state nodes**; declare impacts and let the
   `hypergraph-reconcile` skill fold them. `STATE.md` is generated — never
   hand-edit it.
4. **Verify before finishing**: `hypergraph export` + `hypergraph check` must
   exit 0. If it says this project's copies are behind the CLI, run
   `hypergraph upgrade` — the skills and this block are copies, and `uv tool
   upgrade` cannot see them.
<!-- hypergraph:end -->
