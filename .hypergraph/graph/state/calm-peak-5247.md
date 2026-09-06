---
node_id: a1de57cf-f3ca-5c7e-bc08-ee64cc0ae2e8
slug: calm-peak-5247
title: The robot lifecycle walk — design to policy to iterate, agent-driven and headless
created_at: '2026-09-06T01:27:43+00:00'
parents:
- salty-isle-4063
summary: ''
---
Status: open

## Current

Declared by the audit under the working name `robot-lifecycle-walk`; this node is that target [rec: sweet-light-3396].

The agent-driven robot lifecycle walk as a state of its own: design → assembly → MJCF → task → local CPU training → policy verify → rollout → review → **iterate**, driven from the CLI with no human in the loop, every artifact landing in the project directory. It is the goal's second priority and the `docs/MUJOCO.md` §7b rehearsal re-run as an audit; the training loop's own facts (venv, gate, mg-legs, B7) stay on the RL node [rec: sweet-light-3396].

**Measured 2026-09-06 on the §7b toy, headlessly, on scratch copies of the rehearsal project** (twelve legs, `docs/MUJOCO.md` §7c) [rec: sweet-light-3396] [rec: wise-tooth-2750] [rec: restless-harbor-4224] [rec: amber-moon-0981]:

- **Agent-driven from the CLI**: legs 1 and 2 (design, assembly — proven by the rehearsal, one model turn each), 6 (policy install by `cadex script --set` with name and sha256: accepted, rollout 1719.2 total reward over the full 300 steps against 1729.9 for the 400-iteration run), 7 (review), and since ADR-189 leg 3 as well. [rec: sweet-light-3396]
- **Leg 3, bundle out, closed** (ADR-189) [rec: wise-tooth-2750]: `cadex export` copies the task JSON, model XML, policy receipt and rollout trace into `--out` under their **staged** names and names each in the `--json` envelope; the exported folder is a bundle `training/cadex_train.py` accepts unchanged. Staged basenames were kept deliberately, because the task bundle names its model by them. **Leg 7 for a pipeline** closed with it: the trace's `policy` block carries `total_reward` and the five `reward_totals`, so review needs no staging path.
- **Leg 5, policy home, closed** (ADR-190) [rec: restless-harbor-4224]: `cadex asset --put FILE` (repeatable, because a policy travels with its receipt) stores files through the existing `put_asset` op and reports the store's listing — name, bytes, sha256 — as `assets` rows in the envelope; `put_asset` is now in the agent's tool surface, and the overlay tells the agent it cannot train and names `cadex export --out` and `cadex asset --put` as the caller's two ends of the leg instead of letting it guess. No `--rebuild` flag by decision: the rebuild that makes a policy real is the script change naming it, and folding that into the store write would hide the digest the script must carry. Chain 3→7 ran headlessly with only the trainer command typed by hand (2 it × 8 envs 16.2 s, 28 053 B stored, trace −297.4 for the untrained policy against the rehearsal's 1729.9).
- **Leg 4, training, closed** (ADR-191) [rec: amber-moon-0981]: `cadex train --out DIR --iterations N --envs N --put` rebuilds, exports the bundle, runs `training/cadex_train.py` under the training venv with flags pinned by name and test-read from the trainer's parser, and stores the policy with its sha256 in the envelope's `training` field. The code landed in iteration 24 (`bb2513a0`) unrecorded and is now documented. Measured 18.5 s wall for 2 it × 8 envs, task digest `602d62c1…` equal to the audit's. **Legs 3→7 are one command plus `cadex script --set`.** The agent itself still has no shell, so the leg is the caller's or a pipeline's by decision — a fifteen-minute subprocess inside a model turn is the wrong shape.
- **Blocked by design**: leg 8, iterate. `cadex params --set shove_n=0.20` on a project with a policy declared is refused at exit 3 because the task digest moved and the policy no longer fits, and the refused sweep never writes the bundle a retrain would need. [rec: sweet-light-3396]
- **Missing**: leg 9 (compare and record) and leg 10 (project as a codebase — no `ARCHITECTURE.md`, `DECISIONS.md` or `PROGRESS.md`, no git in the project directory). [rec: sweet-light-3396]
- **Doc only**: leg 11 (GUI attached) and leg 12 (remote training, B7 still blocked on the GPU box's checkout). [rec: sweet-light-3396]

**Ordered frontier** (§7c), items 1–3 done: 1 ~~outputs the CLI hands over~~ (ADR-189) → 2 ~~`put_asset` in the CLI tool surface plus a no-model `cadex asset`~~ (ADR-190) → 3 ~~a `cadex train` dispatcher plus real flags in the contract~~ (ADR-191) → **4 an iterate shape (script convention first) — next** → 5 the engine's `INSPECTION_FAILED` frame fixed with a validator test (tracked on the engine node) → 6 the project scaffold with `PROGRESS.md` rows [rec: sweet-light-3396] [rec: wise-tooth-2750] [rec: restless-harbor-4224] [rec: amber-moon-0981].

Reconcile judgement: status `open` rather than `blocked` — one leg is blocked by design, the rest is ordinary unbuilt work with an ordered frontier. Noted, not chased: every `cadex export` and every `cadex train` leaves a fresh complete attempt directory for the same accepted revision; harmless so far [rec: sweet-light-3396] [rec: wise-tooth-2750] [rec: amber-moon-0981].

## Negative knowledge

- [scope: a parameter sweep on a project with a policy declared | confidence: high | evidence: sweet-light-3396] `cadex params --set` is refused at exit 3 when the change moves the task digest, because the declared policy no longer fits, and nothing is written. Iterate cannot be a plain sweep; it needs a shape that drops or re-derives the policy before the retrain.
- [scope: the CLI agent asked to train inside a model turn | confidence: high | evidence: sweet-light-3396, restless-harbor-4224, amber-moon-0981] It has no shell, and it is not given one: before ADR-190 it guessed trainer flags and invented commands; now the overlay names `cadex train` and `cadex asset --put` as the caller's, and the real flags live in the `cadex train` contract, not in the agent's answer.
- [scope: exporting a training bundle | confidence: high | evidence: wise-tooth-2750] Do not rename exported artifacts to the output's name. The task bundle references its model by the staged basename and the trainer resolves it beside the task by that name; a renamed copy was tried first and the trainer needed a change to accept it.

## Provenance

- sweet-light-3396 — the lifecycle audit: twelve legs measured headlessly on the §7b toy, four agent-driven, three a person's, one blocked, two missing, two doc-only, and the frontier ordered in docs/MUJOCO.md §7c
- wise-tooth-2750 — ADR-189: cadex export hands over every staged non-BREP output under its staged name, the exported folder accepted by the trainer unchanged, §7c rows 3 and 7 closed
- restless-harbor-4224 — ADR-190: cadex asset --put and put_asset in the CLI tool surface, §7c row 5 closed, chain 3→7 run headlessly with only the trainer command by hand
- amber-moon-0981 — ADR-191: cadex train, the offboard trainer's dispatcher, documented and recorded, §7c row 4 closed, legs 3→7 one command plus cadex script --set
