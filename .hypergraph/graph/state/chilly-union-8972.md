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

- **Seven** subcommands — `-p`, `params`, `script`, `export`, `link`, `asset`, `train` — of which exactly one spends tokens. The point is a cost asymmetry: one expensive turn authors a *parametric* script, and a cheap loop then sweeps its parameters, pulls a part in from another project, stores a policy, or dispatches a training run, with no model in the loop at all [rec: jolly-walrus-3692] [rec: ancient-current-9419] [rec: restless-harbor-4224] [rec: amber-moon-0981].
- Its whole model-facing tool surface is **generated from `OP_ARG_SPECS`**, so it cannot drift from the contract it drives [rec: jolly-walrus-3692]. `link_part` arrived that way — the model gained it with no CLI code at all, and `cadex link` exists only for the token-free path [rec: ancient-current-9419]. `put_asset` joined `CLI_TOOL_OPS` last (`source_path` required, `name` optional), with prose saying the reply's sha256 is the digest `assembly.policy` requires [rec: restless-harbor-4224].
- It cost **no engine change and no protocol change**, which is the evidence it was built to produce: a third client that had needed the contract widened would have been evidence against the contract [rec: jolly-walrus-3692] [rec: simple-hollow-8675]. ADR-190 and ADR-191 held to that: no protocol op, no engine change, no `shell/` diff [rec: restless-harbor-4224] [rec: amber-moon-0981].
- `cli/` is **LGPL and `shell/` is GPL**, and the boundary is one-way and hard. Copying a line of the shell's client into `cli/` relicenses the engine side; derive from the engine-side precedents instead [rec: jolly-walrus-3692] [rec: lone-haven-0640].
- **It reads the store's deliverables without being able to make one** (ADR-150): `inspect scope=blueprint` is served — the asymmetry with the absent `image` scope is deliberate, a reference image being a shell-only input while a blueprint sheet is a stored deliverable of the project — and `export --blueprints` copies stored sheets into `--out` under their store names, entirely through inspect (listing, then a per-sheet resolved path). `put_blueprint` is deliberately absent from `CLI_TOOL_OPS`, because nothing headless can render a sheet [rec: windy-wolf-5012].
- **`export` hands over every staged output, not only the BREP ones** (ADR-189, `docs/CLI.md` §3) [rec: wise-tooth-2750]. It converts BREP outputs to STEP/STL as before and copies every other staged artifact — a mesh's `.ply`, the MJCF `.xml`, the task, policy receipt and rollout trace `.json` — into `--out` under its **staged** filename, naming each in the `--json` envelope's `files` under its suffix; only an output with nothing staged is skipped, as `no staged artifact`. The staged basename is kept because the task bundle names its model by it, so the `--out` directory is a training bundle `training/cadex_train.py` accepts unchanged. Before this the audit found every non-BREP output `skipped`, so no pipeline could reach the training bundle or the rollout numbers without reading staging paths [rec: sweet-light-3396].
- **`asset` is the headless door into the project store** (ADR-190, `docs/CLI.md` §2–§4) [rec: restless-harbor-4224]: `--put FILE` is repeatable (a policy travels with its receipt), `--name` renames when there is one file, and the store's listing — name, bytes, sha256 — comes back as the optional `assets` envelope field, which is what a pipeline pipes into `cadex script --set`. With no `--put` it lists the store by following `inspect scope=assets`'s page chain (the value is paged under `path`, so the listing follows `next_offset` like `read_script_source`). Usage errors fire before the engine runs; the engine's refusal is exit 3. No `--rebuild` flag by decision.
- **`train` dispatches the offboard trainer** (ADR-191, `docs/CLI.md` §2–§4, §8) [rec: amber-moon-0981]: `--iterations`, `--envs`, `--seed`, `--label`, `--init-from`, `--task`, `--name`, `--put`, `--timeout`, `--trainer-python`. It rebuilds, exports the bundle, runs `training/cadex_train.py` and, with `--put`, stores the policy; the optional `training` envelope field carries the trainer's receipt as printed. The interpreter is `--trainer-python`, then `$CADEX_TRAIN_PYTHON`, then `<repo>/.venv`, then `~/cadex-train-venv`, and is never created. `cli/` depends on `training/cadex_train.py` by path and on its flag names by test (read from the trainer's parser), and `training/` stays out of every payload. Measured 18.5 s wall for 2 it × 8 envs on the §7b toy.
- **One known hard failure, caused in the engine**: the CLI validates every reply strictly, and the engine's `INSPECTION_FAILED` refusal frame (from `inspect scope=document` throwing) violates `FAILURE_RESPONSE_SPEC`, so the CLI turns it into a hard `CadexdError` mid-turn where the shell, which never validates replies, would carry on. Unchanged by ADR-189 through ADR-191; the fix is engine-side and tracked on the engine node [rec: sweet-light-3396] [rec: wise-tooth-2750].
- Verified end to end on Linux, in CI, against both a build tree and a staged payload; since 2026-08-19 also exercised by hand on macOS [rec: windy-wolf-5012]. Its suite is **103 passed** on 2026-09-06 against the built dev-tree engine, nothing skipped, the real-trainer test included [rec: amber-moon-0981]; it was 92 after ADR-190 [rec: restless-harbor-4224], 85 after ADR-189 [rec: wise-tooth-2750] and 83 on 2026-08-19 [rec: ancient-current-9419] [rec: windy-wolf-5012].

The CLI remains **Claude-only**, independent of the shell's three-harness selector [rec: merry-water-7647]. Its default is `claude-fable-5` since ADR-183, whose CLI validation recorded 83 passed [rec: curious-sail-8332].

## Negative knowledge

- [scope: cli/ on macOS | confidence: medium | evidence: jolly-walrus-3692] Nothing in the CLI is macOS-hostile, but it has never been run there by hand and 'should work' is not evidence. Expect the macOS CI job to be the thing that finds anything.
- [scope: copying code into cli/ | confidence: high | evidence: jolly-walrus-3692] Copying a line from the GPL shell's client into LGPL cli/ relicenses the engine side. It is not a judgement call — derive from the engine-side precedents instead.
- [scope: giving the CLI agent a tool that spawns the trainer | confidence: high | evidence: amber-moon-0981] Not taken by decision: the agent has no shell, and a fifteen-minute subprocess inside a model turn is the wrong shape. The leg is the caller's or a pipeline's, one command, and the overlay says so.

## Provenance

- jolly-walrus-3692 — the CLI's whole design, its verified scope and its stated gaps
- simple-hollow-8675 — the protocol it is the third client of
- lone-haven-0640 — the LGPL/GPL boundary it sits on the engine side of
- ancient-current-9419 — the `link` subcommand, and the tool it gained from `OP_ARG_SPECS` for free
- windy-wolf-5012 — inspect scope=blueprint, export --blueprints, and why put_blueprint stays out of CLI_TOOL_OPS
- merry-water-7647 — shell harness choice does not widen the CLI provider surface
- curious-sail-8332 — CLI default update and 83-test run
- simple-bramble-8616 — optional headless Blender geometry runtime dependency
- sweet-light-3396 — the lifecycle audit: export skipped every non-BREP output, and the strict reply validator hard-fails on the engine's malformed INSPECTION_FAILED frame
- wise-tooth-2750 — ADR-189: export copies every staged non-BREP artifact under its staged name, the exported folder is a trainer-accepted bundle, suite at 85
- restless-harbor-4224 — ADR-190: the `asset` subcommand, `put_asset` in CLI_TOOL_OPS, the `assets` envelope field, suite at 92
- amber-moon-0981 — ADR-191: the `train` subcommand, the `training` envelope field, the interpreter search order, suite at 103
