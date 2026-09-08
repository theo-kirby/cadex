---
node_id: 7eb36f2a-4be2-598a-9a43-ccce9cb043cc
slug: fair-rose-5950
title: 'Assembly inventory with catalog ids: the first headless review call'
created_at: '2026-09-07T21:52:59+00:00'
parents:
- placid-sky-7374
summary: ''
---
## What

`inspect scope="inventory"` and `cadex inventory`: the parts of the accepted
assembly, with catalog ids, as one CLI call landing a file in the project
(ADR-236). Commit `5045847a`.

Two halves, and neither works alone:

- **The stamp.** `lib.bolt("M3", 12)` returns a `LibraryPart` that knows its
  family and part number, but `.body` is an ordinary part solid, so a script
  returning it published an anonymous solid and the identity died at the
  result contract. `cadex_library_api` now records
  `{canonical definition: {family, part_number}}` for every body a generator
  hands back during a run, cleared at each `create_library_api` staging, and
  `cadex_project_worker._stamp_catalog_identity` writes it onto the matching
  output as a top-level `catalog` key.
- **The join.** `inspect scope="inventory"` walks the pinned accepted
  attempt's `result.json`: one row per `component_link` output carrying the
  `source_output` whose geometry it places (the ADR-049 stamp), that output's
  `catalog` where there is one, the solved placement and a six-key
  `source_facts` block; plus a `catalog_counts` roll-up and the
  `uncatalogued_sources` a hand-modelled output lands in.

`cadex inventory` is the CLI call: no AI, no tokens, no rebuild. It pages
`/components` and renders `docs/inventory.md` in the project — a generated
doc, the only one under a project's `docs/` that is, and it says so in its
own first line.

## Why

Charter criterion **The agent can see its work without a screen**
(`damp-moon-9297`), and plan rank 3, which the overseer named as this
iteration's target after two clean prompt walks closed rank 1 and rank 2. The
criterion asks for four calls; this is *list the parts of an assembly with
catalog ids*, and it was the one with a join already waiting to be made — the
`source_output` stamp has existed since ADR-049 and nothing joined it to
anything.

It also serves `crisp-reef-5607` indirectly: the walk's review step is the
leg with the least behind it, and an agent that cannot say *what* it
assembled cannot review it.

**Assumption written down, since nobody was here to ask:** the criterion says
"outputs landing in the project directory", and I chose one generated
markdown file under the project's `docs/` rather than a JSON blob beside it.
The reason is ADR-193's shape — what an agent reads on its *next* visit is
the project's documents, and a table checked into the project's own
repository outlives the run that produced it. The machine-readable form is
one `inspect` call away, so a second file would have been redundant. This is
reversible: adding `docs/inventory.json` later costs four lines.

**The one design decision that mattered.** The obvious place for the catalog
identity is the value's `properties`, and it is the wrong place:
`compute_project_digest` hashes `definition`, so a catalog key there would
move every existing `lib.*` project's digest and lock it out — the class of
change ADR-064 had to force a re-accept for. The identity is written *beside*
the definition, with the definition as the join key, exactly as
`artifact_by_definition` already joins a component source to its output. A
test asserts the canonical definition is byte-identical across the stamp.

## Method

No protocol change, deliberately: `inspect` already takes `{"scope": str}`
and already answers a generic `value`, so `OP_ARG_SPECS`, `OP_RESPONSE_SPECS`
and the ADR-027 goldens are untouched and `shell/` gets **no diff at all**.
`docs/INTEGRATION.md`'s `inspect` row documents the new scope anyway, since
that row is what a client reads. The shell's `inspect_model` tool does not
offer the scope, on the precedent `wiring` set — a scope no canvas has a
picture for is not worth adding to the inherited tree.

Files: `CadexInspection.py` (capture + `_complete_inventory`),
`cadex_library_api.py` (the side table), `cadex_project_worker.py` (the
stamp), `cli/cadex_cli/inventory.py` (new), `cli/cadex_cli/__main__.py` and
`tools.py` (the subcommand and the scope enum), plus two new test files.

Gates run, honestly:

- `pixi run build-engine` — needed, since the CLI suite reaches the
  *installed* modules and the first run of the new CLI test failed on the
  stale copy exactly as AGENTS.md warns.
- `pixi run test-engine` — **2070 passed, 52 skipped** (2062 + the 8 new).
- `pixi run python -m pytest cli/tests` — **145 passed** (142 + the 3 new).
- `pixi run stage-engine`, then the packaged lifecycle gate against that
  payload (`CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-macos-arm64
  pytest test_cadexd_lifecycle.py`) — **15 passed**.
- `pixi run gate` **not run**, and does not apply: `git status` shows no
  `shell/` path in the diff.

## Result

The call works, end to end, against a real engine. `cli/tests/test_inventory.py`
builds a plate with two catalogued M3 bolts standing on it through the real
kernel and asserts the rendered doc names `bolt m3x12-socket`,
`bolt m3x16-socket`, and the hand-modelled `plate` under "Not from the
catalog"; the envelope note reads `inventory: 3 component(s), 2 catalogued`.
`test_inventory_scope.py` pins the stamp, the digest-stillness, the join, the
roll-up, an unknown-assembly refusal and a no-accepted-revision refusal.

One thing the first draft got wrong and the test caught: the summary reply's
`components` key comes back as a *preview stub* the moment the list outgrows
the 1 KiB per-key budget — the ordinary `inspect` contract — so the CLI reader
follows the `/components` page chain rather than trusting the first reply.
That is now what `read_inventory` does and what the engine test asserts.

**What is still missing before `damp-moon-9297` can be ticked:** three of the
four calls. Render from named angles, section view through a named plane, and
the clearance and intersection check that names the offending pairs. Each is
its own unit, and the walk's review step should be wired to each as it lands
rather than at the end. This unit closes none of the frontier criteria on its
own; it is the first quarter of one.

Also corrected in passing: the plan's slug for this ADR was ADR-233, which
was taken by the gear generator between the plan being written and this
iteration. It is ADR-236. `docs/CLI.md`'s CLI file map was missing
`train.py`, `walk.py` and `project_docs.py`; it now lists them.

The unreconciled tail is 3 nodes with this one, at the maintainer's threshold.

Dispatch closed: 1 unit — assembly inventory with catalog ids: a `catalog`
stamp on library-value outputs that cannot move a digest, an `inspect
scope="inventory"` join over it, and `cadex inventory` writing
`docs/inventory.md` in the project; 2070 engine tests, 145 CLI tests, the
packaged gate 15, no protocol change and no `shell/` diff.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 5045847a50381e314b365c37043706629061d8de

## State Impact

- target: damp-moon-9297 — one of the criterion's four calls lands: assembly inventory with catalog ids exists as `inspect scope="inventory"` plus `cadex inventory`, writing `docs/inventory.md` into the project; real-engine qualified (ADR-236). Render-from-angles, section view and clearance/intersection remain open, and the walk's review step is not yet wired to any of them, so the criterion stays open.
- target: brave-stone-9609 — library values now carry catalog identity downstream: `LibraryPart`'s family and part number are stamped onto the matching output beside its definition, so a `lib.*` part is identifiable in the accepted report rather than anonymous once `.body` is returned. The stamp cannot move a project's content digest (join by canonical definition, ADR-236/ADR-064).
- target: chilly-union-8972 — the CLI gains a ninth subcommand, `cadex inventory`: no AI, no tokens, no rebuild. It pages `inspect scope="inventory"`'s `/components` chain and renders `docs/inventory.md` in the project — the first generated doc under a project's `docs/`, marked as such in its own first line.
