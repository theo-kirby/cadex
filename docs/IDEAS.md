# IDEAS.md — Parking Lot

Verified against source: 2026-07-31 (paths only; the ideas are uncommitted)

Uncommitted ideas surfaced during exploration. Nothing here is planned or
approved — promoting an idea means writing a `docs/DECISIONS.md` entry and a
roadmap item. Add freely, prune ruthlessly.

- **Geometry-nodes-style procedural layer over xscript.** The one project
  script is already a dataflow (params → features → outputs). A node-graph
  *view* of it — read-only at first — could make the script legible to
  non-programmers without adding a second source of truth. Blender's
  geometry-nodes UI is right there in the shell.

- **RNA-like reflection for params.** Blender's DNA/RNA
  (`shell/source/blender/makesrna/`) generates UI, animation, and
  Python access from one property definition. Cadex params could get the
  same treatment: one declaration in the script drives slider, protocol
  schema, and inspection output. (The two vocabularies this idea wanted to
  unify are both gone: `set_parameter_controls` dissolved in ADR-013 and the
  shell's `mesh_model.params()` in ADR-030. There is one declaration
  today — `params()`/`num()` in the script — so what is left of the idea is
  generating the *slider metadata* from it rather than hand-bridging
  `param_specs` into a PropertyGroup.)

- **Per-revision tessellation cache.** Revisions are already
  content-addressed (`docs/XSCRIPT.md`). Caching tessellation + ID maps per
  revision hash would make cadexd `set_params` responses for previously seen
  param values instant, and slider scrubbing across a cached range would be
  free.

- **Blender scene as a second cache tier.** Post-Phase 6, the .blend file
  could persist the last tessellation so a project opens instantly and
  reconciles against a background `rebuild` digest — open fast, verify
  lazily.

- ~~**Progressive tessellation for slider latency.**~~ **Built.** Stream a
  coarse mesh during drag, refine on release — this is the `draft` quality
  preset plus the shell's background standard refine, landed with the
  Blender shell (ADR-019). `docs/INTEGRATION.md` describes it as shipped;
  this entry pointed at it as an open question, which it stopped being.

- **Script regions as undo/diff units.** If the one script is executed as
  content-hashed regions, chat-turn diffs and partial re-execution fall out
  of the same mechanism.

- **`core.inspect` as the cadexd `inspect` verb, unchanged.** The bounded
  inspection contract already looks like a service API; keeping it verbatim
  across the split would keep provider prompts stable through Phase 5.
