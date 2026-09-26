---
node_id: b3ccf424-ab43-590c-95af-f700c3fe3217
slug: light-hill-1224
title: 'ADR-406: the agent sees its design (look) and is held to a design language'
created_at: '2026-09-26T13:27:50+00:00'
parents:
- polished-path-3774
summary: ''
---
## What
ADR-406: the product agent can see its own accepted design, and is held to a design
language for printed parts. Commit `ed252e44`.

## Why
hex2's design passed every fit check as flat bars and boxes. The agent called
`inspect` 26 times and never saw an image; its overlay told it "YOU CANNOT SEE YOUR
WORK", and every signal it had was a number boxes satisfy (polished-path-3774).

## Method
- `look`, a bridge-answered tool (`BRIDGE_TOOLS` in `cli/cadex_cli/tools.py`, not an
  engine op): renders the last accepted modelling reply's display with the `cadex
  render` rasteriser (`render.look`) and returns MCP `image` blocks, 768 px per view.
  Views `iso`, `iso_back`, `front`, `right`, `top`; `focus` frames named components;
  world-geometry components from the fit block are left out; inventory decides the
  colour (printed orange, purchased dark grey). A turn that looks before building
  rebuilds once and reads fit and inventory.
- Overlay: "YOU SEE YOUR WORK WITH `look`", a six-rule design language (no sharp
  outside corners, enclose not bolt on, one continuous form, mirror what has sides,
  proportion and clearance, printable) and look-critique-fix before done.
- Renderer caps 100k → 400k placed triangles, 600k → 1.2M placed vertices; the
  per-view pixel count clamps off-canvas spans (two negative widths had multiplied
  into a positive bill).

## Result
- On hex2's geometry: 110,688 triangles snapshot in 0.16 s, four views in 7.2 s.
- A live `claude -p` turn against a copy of hex2 called `look` and described the
  orange bars and ball feet it had not been told of: the harness passes MCP images.
  The first live turn exposed the look-first gap (index palette, floor framed),
  fixed and pinned by `test_bridge_look_first_in_a_turn_rebuilds_and_reads_fit_and_inventory`.
- `cli/tests/test_look.py` 8 tests; CLI suite 946 passed / 1 skipped against the
  staged engine (one walk test had failed only on GPU contention with hex2's
  trainer, passing under `JAX_PLATFORMS=cpu`); engine suite 2059 passed.
- Not yet measured: whether the design language changes what the agent produces.
  That is the next hexapod run's job, against hex2.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: dbb082d04496b8a8944973d67295ddc5802091f7

## State Impact

- target: damp-moon-9297 — The product agent itself can now see its work: the CLI tool surface gains a bridge-answered look tool (ADR-406, commit ed252e44) returning rendered images of the accepted build as MCP image content (printed orange / purchased grey, world geometry excluded, focus close-ups); a live claude -p turn confirmed the model receives and describes them. cadex render's caps rose to 400k placed triangles, so a 110,688-triangle hexapod renders.
- target: chilly-union-8972 — CLI overlay no longer tells the agent it cannot see; adds a design language for printed parts and a look-critique-fix loop before done (ADR-406). BRIDGE_TOOLS is a second tool list beside CLI_TOOL_OPS, outside the protocol surface.
