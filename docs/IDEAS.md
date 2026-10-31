# IDEAS.md — Parking Lot

Verified against source: 2026-10-30

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
  tessellation per part digest under `review/revisions/`, ADR-546; and since
  ADR-782 the worker keeps each part's BREP by content identity under
  `script_artifacts/part-cache/`, so a revisited value rebuilds no unchanged
  part. What is left of this idea is skipping the worker spawn, assembly and
  tessellation for a whole revision already seen.)

- **A joint gimbal in the viewport (owner, 2026-10-19).** Pick a joint (or a
  part, meaning the joint that moves it) and drag a rotation ring or slide
  arrow on it, Blender-style. (The Pose editor, ADR-969, built the posing:
  sliders over each joint's range, the tree and closed linkages following,
  the stops shown. Left: the in-viewport ring, and flagging a pose that
  collides.)

- **Script regions as undo/diff units.** If the one script is executed as
  content-hashed regions, region-level diffs between revisions and partial
  re-execution fall out of the same mechanism (ADR-782 already caches per
  part, below the script).

Pruned on 2026-10-16 as moot, built or settled: RNA-like reflection for
params and a Blender scene as a cache tier (no shell, no sliders: ADR-498,
ADR-537); progressive tessellation (built with the shell, ADR-019, and gone
with it; the engine's `draft` preset remains); `inspect` as a cadexd verb
(built); assembly source camera visibility (shipped, ADR-228, then gone with
the shell); the CLI agent's missing North Star legs and a bridge CLI for
bash-first agents (settled by ADR-190 and ADR-538: `put_asset` is a tool,
the agent is the person's own, and `cadex mcp` plus the `cadex` commands
are the transports). Their original text is in git history.
