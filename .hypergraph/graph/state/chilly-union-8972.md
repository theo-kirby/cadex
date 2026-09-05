---
node_id: 3325626a-1f72-5999-9ce6-5a38f2da49dd
slug: chilly-union-8972
title: The headless CLI
created_at: '2026-08-09T15:22:02+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

`cli/` plus the `./cadex` shim is a second **front end** and the third client of the cadexd protocol: no Blender, no display, no shell code. Ordinary projects need a built engine alone [rec: jolly-walrus-3692]; native Blender recipe projects additionally require `CADEX_BLENDER_EXECUTABLE` [rec: simple-bramble-8616].

- **Five** subcommands — `-p`, `params`, `script`, `export`, `link` — of which exactly one spends tokens. The point is a cost asymmetry: one expensive turn authors a *parametric* script, and a cheap loop then sweeps its parameters, or pulls a part in from another project, with no model in the loop at all [rec: jolly-walrus-3692] [rec: ancient-current-9419].
- Its whole model-facing tool surface is **generated from `OP_ARG_SPECS`**, so it cannot drift from the contract it drives [rec: jolly-walrus-3692]. `link_part` arrived that way — the model gained it with no CLI code at all, and `cadex link` exists only for the token-free path [rec: ancient-current-9419].
- It cost **no engine change and no protocol change**, which is the evidence it was built to produce: a third client that had needed the contract widened would have been evidence against the contract [rec: jolly-walrus-3692] [rec: simple-hollow-8675].
- `cli/` is **LGPL and `shell/` is GPL**, and the boundary is one-way and hard. Copying a line of the shell's client into `cli/` relicenses the engine side; derive from the engine-side precedents instead [rec: jolly-walrus-3692] [rec: lone-haven-0640].
- **It reads the store's deliverables without being able to make one** (ADR-150): `inspect scope=blueprint` is served — the asymmetry with the absent `image` scope is deliberate, a reference image being a shell-only input while a blueprint sheet is a stored deliverable of the project — and `export --blueprints` copies stored sheets into `--out` under their store names, entirely through inspect (listing, then a per-sheet resolved path). `put_blueprint` is deliberately absent from `CLI_TOOL_OPS`, because nothing headless can render a sheet [rec: windy-wolf-5012].
- Verified end to end on Linux, in CI, against both a build tree and a staged payload; since 2026-08-19 also exercised by hand on macOS (`export --blueprints` against a real store) [rec: windy-wolf-5012]. Its suite is **83 passed**, measured 2026-08-19 [rec: ancient-current-9419] [rec: windy-wolf-5012].

The CLI remains **Claude-only**, independent of the shell's three-harness selector [rec: merry-water-7647]. Its default is `claude-fable-5` since ADR-183, whose CLI validation recorded 83 passed [rec: curious-sail-8332].

## Negative knowledge

- [scope: cli/ on macOS | confidence: medium | evidence: jolly-walrus-3692] Nothing in the CLI is macOS-hostile, but it has never been run there by hand and 'should work' is not evidence. Expect the macOS CI job to be the thing that finds anything.
- [scope: copying code into cli/ | confidence: high | evidence: jolly-walrus-3692] Copying a line from the GPL shell's client into LGPL cli/ relicenses the engine side. It is not a judgement call — derive from the engine-side precedents instead.

## Provenance

- jolly-walrus-3692 — the CLI's whole design, its verified scope and its stated gaps
- simple-hollow-8675 — the protocol it is the third client of
- lone-haven-0640 — the LGPL/GPL boundary it sits on the engine side of
- ancient-current-9419 — the `link` subcommand, and the tool it gained from `OP_ARG_SPECS` for free
- windy-wolf-5012 — inspect scope=blueprint, export --blueprints, and why put_blueprint stays out of CLI_TOOL_OPS
- merry-water-7647 — shell harness choice does not widen the CLI provider surface
- curious-sail-8332 — CLI default update and 83-test run
- simple-bramble-8616 — optional headless Blender geometry runtime dependency
