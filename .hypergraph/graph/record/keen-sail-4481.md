---
node_id: 212fd75c-2b25-514c-8028-d0ba4614e792
slug: keen-sail-4481
title: 'Iterate is a script convention plus the curriculum pair on cadex train (ADR-192): §7c row 8 closes'
created_at: '2026-09-06T06:08:19+00:00'
parents:
- amber-moon-0981
summary: ''
---
## What

The iterate leg of the robot lifecycle walk (`docs/MUJOCO.md` §7c row 8, frontier item 4) closed as a **script convention plus two flags** (ADR-192). The trained policy is declared behind a numeric switch parameter (`policy_on=num(1.0, min=0, max=1, step=1)` guarding `assembly.policy`, `assembly.rollout` and their `result` entries), so a parameter sweep that moves the task digest is accepted with the switch at 0 — `set_params` never refuses a dropped output, only `write_script` does (ADR-045) — and exports the bundle at its new digest. `cadex train` now carries the ADR-161 curriculum pair, `--init-from-parent-task BUNDLE` and `--init-from-task-change REASON`, by name beside `--init-from`, refused apart as a usage error before the engine runs, so the retrain is warm across the change. Then the digest edit with `cadex script --set`, and `cadex params --set policy_on=1` verifies and rolls out. Four commands, one digest edit, no human step. Documented in `docs/CLI.md` §2 (the train flags and an "Iterating" paragraph with the convention) and §8, `docs/MUJOCO.md` §7c row 8 and item 4, the CLI agent's overlay (so a script it authors carries the switch), a ROADMAP tick, and ADR-192.

## Why

Item 4 of the ordered frontier on `calm-peak-5247`, the goal's second priority, after items 1–3 closed (ADR-189/190/191). The audit had measured row 8 blocked by design: the refusal is right and writes nothing, so nothing could produce the bundle a retrain needs. The audit named the reversible answer first — a script convention, a flag only if that proved clumsy — and the question policy says prefer the convention. Assumptions made without a human: the ADR number is 192 (nothing claims it); the switch is a `num` with a `>= 0.5` test because parameters are numeric only and adding a `flag(...)` type would be an engine change for a convention that does not need one; the stored parameter value outliving a script write is left as it is, so the re-enable is a separate `params` call rather than a hidden reset. Not taken: a `params --drop-policy` flag or an engine op.

## Method

Read the audit node, the §7c table, `cli/cadex_cli/train.py`, `command_train`/`command_params`, `dropped_outputs` in `CadexScriptedRuntime.py` (only `write_script` is checked), `ParamsCollector` (numeric only), the trainer's `check_curriculum_change` and `CURRICULUM_TASK_KEYS`. Added the two kwargs to `trainer_command`, the two parser flags and a together-or-usage-error check to `command_train`. Copied `~/cadex-balance-ns` to `/tmp/nt1-iter/proj` (never the live project) and ran the chain for real: switch script accepted → `cadex export --out run0` (parent bundle `602d62c1…`, trace 1729.9) → `params --set shove_n=0.20` refused exit 3 with both digests → `params --set policy_on=0 --set shove_n=0.20 --out sweep` accepted, bundle `369a0dd5…`, no policy/run outputs → `train --iterations 2 --envs 8 --put --name balance2.cxpolicy --init-from assets/balance.cxpolicy --init-from-parent-task run0/balance_task-task.json --init-from-task-change "shove band 0.12 N -> 0.20 N"` exit 0 in 17.8 s, iteration 0 at +1.52 reward/step (cold sits at −0.95), sha256 `4f2d62b1…` equal in receipt and store, header `training.init_from.task_change` with `keys: ["disturbance"]` → digest edit and `script --set` (policy_on still 0.0) → `params --set policy_on=1 --out run2` exit 0, trace `policy_sha256` `4f2d62b1…`, 127.8 total reward. Wrote four tests in `cli/tests/test_train.py`: the pair pinned against the trainer's parser, refused apart, passed to a fake trainer as given, and the whole chain on the toy with the real trainer (two runs at 1 it × 4 envs) including the exit-3 refusal with the digest named. Ran `cli/tests` with the built engine and the training venv present.

## Result

- Row 8 closes: the walk's legs 1–8 are agent-authored scripts and CLI commands with no human step. Legs 9 (compare and record) and 10 (project scaffold) are the frontier; item 5 (`INSPECTION_FAILED` frame) is untouched.
- The comparison the walk needed exists: 1729.9 (0.12 N, 400 it) against 127.8 (0.20 N, one warm toy step) in the two traces' `policy` blocks — a number, not a result, and row 9 is where it gets recorded.
- Gate for `cli/`: `pixi run python -m pytest cli/tests` **105 passed** in 72.7 s with the built engine and the training venv present, nothing skipped (103 before; `test_train.py` alone 13 passed in 50.5 s, the real-trainer iterate chain included). No engine, shell or protocol change, so no other gate applies.
- Noted, not chased: the trainer's `init-from`/`curriculum` lines go to stdout and the dispatcher shows only stderr, so they never reach the terminal (the header carries the facts); the receipt has no warm-start field; every `cadex train` still leaves a fresh attempt directory.
- The unreconciled tail was zero on arrival; this node makes it one. The overseer's note that file lifecycle is open is stale: ADR-186/187/188 landed and `simple-willow-8989` is `working`.

Dispatch closed: 1 unit — iterate is a script convention plus the curriculum pair on `cadex train` (ADR-192); §7c row 8 closes, the chain run headlessly on a scratch copy and pinned by a real-trainer test.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt1
- commit: c9b9e2c851d29ea05823c3872fbabd5bc2c018d0

## State Impact

- target: calm-peak-5247 — §7c row 8 (iterate) closes as a script convention, not a flag (ADR-192): the policy is declared behind a numeric switch parameter (policy_on) the sweep blanks; set_params never refuses a dropped output, so cadex params --set policy_on=0 --set <change> is accepted and exports the bundle at its new digest; cadex train carries --init-from-parent-task and --init-from-task-change (ADR-161's pair) so the retrain is warm across the change; the digest edit with cadex script --set and cadex params --set policy_on=1 verify and roll out — four commands, one digest edit, no human step; the CLI agent's overlay names the convention; measured on a scratch copy of the §7b toy (refusal exit 3 at 602d62c1→369a0dd5, warm retrain 2 it × 8 envs in 17.8 s with iteration 0 at +1.52 reward/step, re-declared at 4f2d62b1…, trace 127.8 against the parent's 1729.9) and pinned by a real-trainer test; frontier item 4 done, legs 1–8 agent-driven; rows 9 (compare and record) and 10 (project scaffold) are next; a stored parameter value outlives a script write, which is why the re-enable is its own params call
- target: chilly-union-8972 — cadex train gains --init-from-parent-task BUNDLE and --init-from-task-change REASON, passed through by name and refused apart from --init-from as a usage error before the engine runs; docs/CLI.md §2 carries an Iterating paragraph with the policy_on switch convention and the four commands; cli/tests 105 passed (103 before)
