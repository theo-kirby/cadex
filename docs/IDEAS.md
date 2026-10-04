# IDEAS.md — Parking Lot

Verified against source: 2026-10-04 (ideas the shell's deletion, ADR-498, and ADR-537/538 settled are marked)

Uncommitted ideas surfaced during exploration. Nothing here is planned or
approved — promoting an idea means writing a `docs/DECISIONS.md` entry and a
roadmap item. Add freely, prune ruthlessly.

- **Geometry-nodes-style procedural layer over xscript.** The one project
  script is already a dataflow (params → features → outputs). A node-graph
  *view* of it — read-only at first — could make the script legible to
  non-programmers without adding a second source of truth. (This once
  pointed at Blender's geometry-nodes UI in the shell; the shell is deleted,
  ADR-498, so the view would be a read-only dashboard panel.)

- ~~**RNA-like reflection for params.**~~ **Moot** (ADR-498, ADR-537): no
  PropertyGroup to bridge into and no slider to generate, since the shell is
  deleted and the dashboard sets nothing. The original entry: Blender's DNA/RNA
  (`source/blender/makesrna/` upstream) generates UI, animation, and
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
  param values instant, and a `cadex params` sweep that revisits values
  would be free. (The dashboard already keeps each converted mesh by its
  tessellation hash, ADR-535; this idea is the engine-side cache.)

- ~~**Blender scene as a second cache tier.**~~ **Moot**: no front end keeps
  a scene file since the shell's deletion (ADR-498). Post-Phase 6, the Blender file
  could persist the last tessellation so a project opens instantly and
  reconciles against a background `rebuild` digest — open fast, verify
  lazily.

- ~~**Progressive tessellation for slider latency.**~~ **Built.** Stream a
  coarse mesh during drag, refine on release — this is the `draft` quality
  preset plus the shell's background standard refine, landed with the
  Blender shell (ADR-019). `docs/INTEGRATION.md` describes it as shipped;
  this entry pointed at it as an open question, which it stopped being. The
  drag and the refine went with the shell (ADR-498); the engine's `draft`
  preset remains.

- **Script regions as undo/diff units.** If the one script is executed as
  content-hashed regions, per-turn diffs and partial re-execution fall out
  of the same mechanism.

- ~~**`core.inspect` as the cadexd `inspect` verb, unchanged.**~~ **Built**:
  `inspect` is a cadexd op and one of the agent's tools
  (`cli/cadex_cli/tools.py`). The original entry: The bounded
  inspection contract already looks like a service API; keeping it verbatim
  across the split would keep provider prompts stable through Phase 5.

- **Assembly source camera visibility — shipped (ADR-228), then gone with
  the shell (ADR-498).** It was the shell's hydrator; the original entry: The hydrator
  now hides instanced raw solids and edge companions from camera renders,
  with independent ownership that preserves pre-hidden render sources.
  Actual hydration and EEVEE regression cover repeat hydration, component
  removal and unrelated explicit hides; see `history/ASSEMBLY-VISIBILITY-AUDIT.md`.
  This does not deliver general headless review tools or rollout video.

- ~~**The CLI agent's two missing legs for the North Star**~~ **Settled**:
  `put_asset` is in the tool surface (ADR-190), and since ADR-538 the agent
  is the person's own, with a shell, so it runs the trainer and reads
  `training/SETUP.md` itself. The original entry (ADR-170
  rehearsal): no `put_asset` in its tool surface (cannot bring a policy
  home) and no shell (cannot run the trainer, cannot read
  `training/SETUP.md`, so it hands back guessed flags). Adding `put_asset`
  is small; the training leg wants either a dispatcher op or the trainer's
  invocation shape in the agent contract.
  Re-measured and ordered, with the iterate step and the project-as-codebase
  gaps beside them, in `docs/MUJOCO.md` §7c (2026-09-06).

- ~~**A bridge CLI as a second tool transport, for bash-first agents.**~~
  **Settled by ADR-538**: the bridge is called in process, `cadex mcp` is the
  MCP transport any client registers, and a bash-first agent drives the
  project through the `cadex` commands. The original entry: The
  Mesh tool seam is the TCP bridge, and its one transport is MCP. (A native
  pi extension was a second until ADR-497 retired pi with the shell.) A tiny
  `mesh-tool` CLI (stdlib-only, like the shim — `mesh-tool list`,
  `mesh-tool call write_script --json '…'`) would let *any* agent with a
  shell drive the product with no protocol integration at all, README
  style. It would also be the
  cheapest possible harness for scripting the bridge in tests. Costs a
  hard look at authentication (the token would have to reach the shell)
  and at losing per-tool argv validation.
