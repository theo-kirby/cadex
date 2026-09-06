---
node_id: 0688ee42-efd0-5a7b-8ebc-c2f5907cdc69
slug: sweet-light-3396
title: 'The lifecycle audit: twelve legs measured headlessly, three still a person''s, iterate blocked, one engine defect'
created_at: '2026-09-06T01:15:46+00:00'
parents:
- wild-grotto-5497
summary: ''
---
## What

The lifecycle audit the goal's horizon ladder asks for: the §7b rehearsal
arc run again headlessly on this machine, leg by leg, on a scratch copy of
`~/cadex-balance-ns`, to list which legs the product agent can drive from
the CLI today, which still need a person or a guess, and what the iterate
step needs before it can run. Written up as `docs/MUJOCO.md` §7c (commit
on this branch), with the frontier ordered. No code changed.

## Why

Overseer direction for iteration 21 of `ouroboros/nt1`: file lifecycle is
done, so run the existing rehearsal headlessly, list every step that still
needs human input or a guess, and record it as a decision node with NEW
impacts targeting the lifecycle frontier. This is the audit that orders
the iterate work. Assumptions taken without a human: the mechanism was
reused from the rehearsal rather than re-authored (leg 1–2 are proven by
`gilded-trail-2519` and cost a model turn each); training was bounded to
200 iterations on CPU in the repo's untracked `.venv`; the project copy
lived in `/tmp`, never `~/cadex-balance-ns` itself.

## Method

- `cadex export --json` on the copy: rebuilt in 2.6 s including policy
  verify and rollout; STEP and STL written; task JSON, model XML, receipt
  and trace all `skipped: not a BREP output`.
- Trainer from `.venv` (3.13.12, jax 0.7.2 cpu, mujoco 3.10.0) on the
  staged bundle: 200 it × 64 envs, 22.5 s, reward/step 5.24, witness
  3.2e-08, sha256 `15df93e8…`.
- `put_asset` over raw NDJSON with a 40-line scratch driver on the
  latency-integration client: ok, 54 577 bytes.
- `cadex script --set` with the new name and sha256: accepted; rollout
  1719.2 total reward, full 300 steps, against 1729.9 for the 400-it run.
- `cadex params --set shove_n=0.20`: refused, exit 3, task digest moved
  and the policy no longer fits — the iterate step is blocked by design.
- One `./cadex -p` turn asking to retrain and bring the policy home: it
  reviewed the rollout itself through `inspect`, refused training and
  asset import cleanly, handed back `--num-envs`/`--output` (real flags
  are `--envs`/`--out`) and an invented "`put_asset` CLI command".
- That turn's `inspect scope=document` threw in the engine and the CLI
  hard-failed the reply: reproduced with `validate_response` on the
  `INSPECTION_FAILED` frame `CadexInspection.py` builds — missing eight
  `FAILURE_RESPONSE_SPEC` keys, carrying three forbidden ones.
- Verification: engine suite (pytest, `src/Mod/cadex/cadex_tests`) after
  the doc edit — result in the commit message.

## Result

Twelve legs measured. Works for the agent: 1, 2, 6, 7. Works only for a
person or by guessing a staging path: 3 (bundle out), 4 (training — no
shell), 5 (`put_asset` — not in the tool surface). Blocked: 8 (iterate —
a parameter sweep with a policy declared is refused and never writes the
bundle it would need). Missing: 9 (compare and record) and 10 (project as
a codebase: no `ARCHITECTURE.md`/`DECISIONS.md`/`PROGRESS.md`, no git).
Doc only: 11 (GUI attached) and 12 (remote training, B7 still blocked).
Ordered frontier, in §7c: CLI hands over non-BREP outputs → `put_asset`
in the CLI surface plus a no-model `cadex asset` → a `cadex train`
dispatcher plus real flags in the contract → an iterate shape (script
convention first) → the `INSPECTION_FAILED` frame fixed with a validator
test → the project scaffold with `PROGRESS.md` rows. One unexplained
oddity noted, not chased: one `cadex export` left two complete attempt
directories for one revision. The unreconciled tail is now two nodes.

Dispatch closed: 1 unit — the lifecycle audit: 12 legs measured headlessly, 4 agent-driven, 3 human, 1 blocked, 2 missing, one engine defect found, frontier ordered in docs/MUJOCO.md §7c.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt1
- commit: 095c865916bdcb62275fb5e1c08139c9b88dcc85

## State Impact

- target: NEW robot-lifecycle-walk — The agent-driven robot lifecycle walk (design → assembly → MJCF → task → local CPU training → verify → rollout → review → iterate) as a state of its own, measured 2026-09-06 on the §7b toy: legs 1,2,6,7 agent-driven from the CLI; 3 (bundle out: cadex export skips non-BREP outputs), 4 (training: no shell) and 5 (put_asset: not in the CLI surface) still a person's; 8 (iterate) blocked because a parameter sweep with a policy declared is refused at exit 3 and never writes the bundle it would need; 9 (compare/record) and 10 (project as codebase: no ARCHITECTURE/DECISIONS/PROGRESS.md, no git) missing; 11 (GUI attached) and 12 (remote training) doc only. Ordered frontier in docs/MUJOCO.md §7c: outputs the CLI hands over → put_asset in the CLI plus a no-model cadex asset → a cadex train dispatcher plus real flags in the contract → an iterate shape → the INSPECTION_FAILED frame → the project scaffold with PROGRESS.md rows
- target: late-pond-2851 — The rehearsal's two CLI gaps re-measured with one agent turn on 2026-09-06: refusals still clean, flags still guessed (--num-envs/--output for --envs/--out), and a put_asset CLI command invented. The lifecycle walk now has its own state node (robot-lifecycle-walk); this node keeps gait scale and B7
- target: chilly-union-8972 — cadex export writes only BREP outputs (task JSON, model XML, receipt and trace come back skipped), so a pipeline cannot get the training bundle or the rollout numbers without reading staging paths; and its strict reply validator turns the engine's malformed INSPECTION_FAILED frame into a hard CadexdError
- target: forest-wind-0342 — broken: CadexInspection.py's INSPECTION_FAILED refusal frame (tool, failure_code, failure_stage, error, scope, target, result_json_bytes) violates FAILURE_RESPONSE_SPEC — eight required keys missing, three forbidden keys present — confirmed with validate_response; the shell never validates replies so only the CLI sees it
