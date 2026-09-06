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

**Measured 2026-09-06 on the §7b toy, headlessly, on a scratch copy of the rehearsal project** (twelve legs, `docs/MUJOCO.md` §7c) [rec: sweet-light-3396] [rec: wise-tooth-2750]:

- **Agent-driven from the CLI**: legs 1 and 2 (design, assembly — proven by the rehearsal, one model turn each), 6 (policy install by `cadex script --set` with name and sha256: accepted, rollout 1719.2 total reward over the full 300 steps against 1729.9 for the 400-iteration run), 7 (review), and since ADR-189 leg 3 as well. [rec: sweet-light-3396]
- **Leg 3, bundle out, closed** (ADR-189) [rec: wise-tooth-2750]: `cadex export` copies the task JSON, model XML, policy receipt and rollout trace into `--out` under their **staged** names and names each in the `--json` envelope; the exported folder is a bundle `training/cadex_train.py` accepts unchanged (2 iterations × 8 envs, exit 0, task digest `602d62c1…` matching the audit's). Staged basenames were kept deliberately, because the task bundle names its model by them and `load_bundle` resolves the model beside the task that way. **Leg 7 for a pipeline** closed with it: the trace's `policy` block carries `total_reward` and the five `reward_totals`, so review needs no staging path.
- **Still a person's, or a guess**: leg 4 (training — the CLI agent has no shell; asked to retrain it handed back `--num-envs`/`--output` for the real `--envs`/`--out`) and leg 5 (`put_asset` is not in the CLI tool surface; the agent invented a `put_asset` CLI command). Both refusals were clean. Training itself works from the repo's untracked `.venv`: 200 iterations × 64 envs in 22.5 s on CPU, and `put_asset` over raw NDJSON accepts the result. [rec: sweet-light-3396]
- **Blocked by design**: leg 8, iterate. `cadex params --set shove_n=0.20` on a project with a policy declared is refused at exit 3 because the task digest moved and the policy no longer fits, and the refused sweep never writes the bundle a retrain would need. [rec: sweet-light-3396]
- **Missing**: leg 9 (compare and record) and leg 10 (project as a codebase — no `ARCHITECTURE.md`, `DECISIONS.md` or `PROGRESS.md`, no git in the project directory). [rec: sweet-light-3396]
- **Doc only**: leg 11 (GUI attached) and leg 12 (remote training, B7 still blocked on the GPU box's checkout). [rec: sweet-light-3396]

**Ordered frontier** (§7c), with item 1 done: 1 ~~outputs the CLI hands over~~ (ADR-189) → 2 `put_asset` in the CLI tool surface plus a no-model `cadex asset` → 3 a `cadex train` dispatcher plus real flags in the contract → 4 an iterate shape (script convention first) → 5 the engine's `INSPECTION_FAILED` frame fixed with a validator test (tracked on the engine node) → 6 the project scaffold with `PROGRESS.md` rows [rec: sweet-light-3396] [rec: wise-tooth-2750].

Reconcile judgement: status `open` rather than `blocked` — one leg is blocked by design, the rest is ordinary unbuilt work with an ordered frontier. Noted, not chased: every `cadex export` leaves a fresh complete attempt directory for the same accepted revision (three on the audit's copy after two runs); harmless so far [rec: sweet-light-3396] [rec: wise-tooth-2750].

## Negative knowledge

- [scope: a parameter sweep on a project with a policy declared | confidence: high | evidence: sweet-light-3396] `cadex params --set` is refused at exit 3 when the change moves the task digest, because the declared policy no longer fits, and nothing is written. Iterate cannot be a plain sweep; it needs a shape that drops or re-derives the policy before the retrain.
- [scope: the CLI agent asked to train or import a policy | confidence: high | evidence: sweet-light-3396] It has no shell and no `put_asset`, so it guesses trainer flags and invents commands. The refusals are clean; the flags it hands back must not be trusted until a `cadex train` dispatcher puts the real ones in the contract.
- [scope: exporting a training bundle | confidence: high | evidence: wise-tooth-2750] Do not rename exported artifacts to the output's name. The task bundle references its model by the staged basename and the trainer resolves it beside the task by that name; a renamed copy was tried first and the trainer needed a change to accept it.

## Provenance

- sweet-light-3396 — the lifecycle audit: twelve legs measured headlessly on the §7b toy, four agent-driven, three a person's, one blocked, two missing, two doc-only, and the frontier ordered in docs/MUJOCO.md §7c
- wise-tooth-2750 — ADR-189: cadex export hands over every staged non-BREP output under its staged name, the exported folder accepted by the trainer unchanged, §7c rows 3 and 7 closed
