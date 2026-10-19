# IDEAS.md — Parking Lot

Verified against source: 2026-10-19

Uncommitted ideas surfaced during exploration. Nothing here is planned or
approved — promoting an idea means writing a `docs/DECISIONS.md` entry and a
roadmap item. Add freely, prune ruthlessly.

- **A node-graph view of the script.** The one project script is already a
  dataflow (params → features → outputs). A read-only node-graph *view* of
  it, as a dashboard panel, could make the script legible to
  non-programmers without adding a second source of truth. (It once pointed
  at Blender's geometry-nodes UI; the shell is deleted, ADR-498.)

- **Per-revision tessellation cache.** Revisions are already
  content-addressed (`docs/XSCRIPT.md`). Caching tessellation + ID maps per
  revision hash would make cadexd `set_params` responses for previously seen
  param values instant, and a `cadex params` sweep that revisits values
  would be free. (The dashboard already keeps each converted mesh by its
  tessellation hash, ADR-535, and the CLI keeps every accepted revision's
  tessellation per part digest under `review/revisions/`, ADR-546; this idea
  is the engine-side cache that would make a revisited value skip the
  worker.)

- **A joint gimbal in the viewport (owner, 2026-10-19).** Pick a joint (or a
  part, meaning the joint that moves it) and drag a rotation ring or slide
  arrow on it, Blender-style, to move it through its range while the rest of
  the mechanism follows: the tree below it, and a closed linkage re-solved,
  the way the clearance sweep already drives one (ADR-593). Show the joint's
  angle and its stops, and flag a pose that collides. It is posing, not
  editing: the pose is view state like the camera, it never writes the
  script, and a reset returns to the build pose, so the dashboard stays
  read-only (ADR-537). It would have answered "render the foot in each
  position" (the orun11 spring foot) without a script. It needs the
  solver's poses on demand from the engine, or a client-side tree walk for
  open chains.

- **Script regions as undo/diff units.** If the one script is executed as
  content-hashed regions, per-turn diffs and partial re-execution fall out
  of the same mechanism.

Pruned on 2026-10-16 as moot, built or settled: RNA-like reflection for
params and a Blender scene as a cache tier (no shell, no sliders: ADR-498,
ADR-537); progressive tessellation (built with the shell, ADR-019, and gone
with it; the engine's `draft` preset remains); `inspect` as a cadexd verb
(built); assembly source camera visibility (shipped, ADR-228, then gone with
the shell); the CLI agent's missing North Star legs and a bridge CLI for
bash-first agents (settled by ADR-190 and ADR-538: `put_asset` is a tool,
the agent is the person's own, and `cadex mcp` plus the `cadex` commands
are the transports). Their original text is in git history.
