---
node_id: 40155ee2-95e9-5797-8f10-bf8425c9a4b4
slug: misty-rain-9048
title: Run the headless lifecycle walk end to end and name the legs that still need a person
created_at: '2026-09-07T20:50:21+00:00'
parents:
- modest-summit-8554
summary: ''
---
## What

Ran the documented headless lifecycle walk end to end on this machine, three
times, and named the legs that still need a person.

Measured, all headless, all under the charter's memory and wall guards
(0.2 s sampling of process-tree RSS, 2.9 GB cutoff, 850 s cutoff around each
whole walk), at 1 iteration x 4 environments, `--seed 0`:

| project | legs | wall | peak RSS | rollout `total_reward` |
|---|---|---|---|---|
| `hinged-arm` (examples recipe) | train 11.69 s, declare 1.22 s, rollout 1.35 s, all exit 0 | 15.3 s | 1.03 GB | -27.109384 (lift -27.109073, control_cost -0.000311) |
| `linear-carriage` (examples recipe) | train 9.54 s, declare 1.23 s, rollout 1.35 s, all exit 0 | 13.1 s | 0.98 GB | -24159.195 (lift -24159.195, control_cost -2.28e-06) |
| agent-designed pendulum rig | design (separate), train 14.77 s exit 0, **declare exit 3** | 15.8 s | 1.27 GB | none — walk stopped |

Both example mechanisms complete the whole loop with no human step and land
`review.json` in the project. The third project is the finding.

Two legs need a person, and only one of them is a defect in the walk:

1. **The digest edit refuses an agent-authored script.** A fresh design turn
   (`./cadex -p "A simple pendulum test rig: ... and the policy switch
   convention so the lifecycle walk can install a trained policy"`) produced
   an accepted script that carries `policy_on=num(...)` and exactly one
   `assembly.policy(...)` call — but declares the two strings as module
   constants (`POLICY_WEIGHTS = "lift.cxpolicy"`, `POLICY_SHA256 = ""`) and
   passes them by name. `cli/cadex_cli/walk.py:_replace_keyword` rewrites
   *inline string literals*, so the walk stopped at exit 3: "the
   assembly.policy(...) call carries no weights=\"…\" string to rewrite". The
   authoring contract in `cli/cadex_cli/agent.py` (the `describe_api` prompt,
   lines 135-142) teaches the switch and never mentions the literals, so the
   model factored them out — a reasonable style choice the walk cannot
   accept. Closing this needs a person to hand-edit the script, which is
   exactly the human step the criterion forbids.
2. **The design leg failed once, opaquely, and a byte-identical retry
   succeeded.** Inside `cadex walk --prompt`, the child turn ended after one
   `describe_api` call in 3.76 s with "the turn finished without the engine
   accepting a script" and no reason from the child. The same argv run
   directly (`./cadex --project … -p <same prompt> --json --model
   claude-fable-5`) took 214 s, wrote a script with masses, a revolute joint,
   a position actuator, a lift task and the switch, and exited 0. So the leg
   works, but its failure envelope discards the child agent's own reason,
   which makes an unattended retry policy impossible to write.

The commit itself is the doc-truth half: `docs/CLI.md` documented two of the
three counts `declare_policy` refuses on. AGENTS.md methodology rule 1 says
the code wins, so the doc now names all three and points at the authoring
contract as the reason an agent-authored script trips the third.

## Why

Charter criterion advanced: **"The walk exists and is tested headlessly"**
(frontier `crisp-reef-5607`, mission item 2), the leading unit of the short
rung (`young-crane-9546` rank 1): run the documented entry point end to end
and record exactly which leg still needs a person or a guess.

The criterion cannot be ticked yet. What is still missing: the walk starting
from `--prompt` never reaches review, because the design leg and the digest
edit disagree about how a policy is declared. The example recipes prove the
loop from an existing script; they do not prove ideation → design → … →
review, which is what the criterion claims.

The plan's rank 1 says explicitly not to fix a leg and run the walk in the
same iteration, so both findings are left for the next unit. The next unit is
the smaller and more reversible of the two (question policy: prefer the
reversible option): **teach the authoring contract that `weights=` and
`sha256=` must be inline string literals** — one paragraph in
`cli/cadex_cli/agent.py`'s prompt plus a test — rather than widening
`declare_policy` to resolve module constants, which would make the walk
guess at a script it did not write.

## Method

- Prerequisites already on this machine: release engine at
  `build/release/bin/FreeCADCmd`, training venv at `.venv` (jax 0.7.2, CPU
  backend). No build was needed and none was run.
- Guard harness (`/tmp`, not committed): spawn the walk, sample process-tree
  RSS every 0.2 s, SIGKILL at 2.9 GB or 850 s — the discipline
  `examples/lifecycle/README.md` asks for, since `--timeout` bounds only the
  trainer.
- For each mechanism: `./cadex script --project build/lifecycle/<name> --set
  examples/lifecycle/<mech>/script.py --json`, then `JAX_PLATFORMS=cpu
  ./cadex walk --project … --out …/runs/baseline --trainer-python
  "$PWD/.venv/bin/python" --iterations 1 --envs 4 --seed 0 --timeout 600
  --json`. Fresh project paths each time, so no accepted policy is inherited.
- For the design leg: `cadex walk --prompt …` on a fresh project (failed
  fast), then the same turn standalone (succeeded), then `cadex walk` with no
  prompt over the resulting project (refused at declare).
- Read `walk.py:declare_policy` and `agent.py`'s prompt to confirm the
  refusal is a contract mismatch rather than a bug in the rewrite.
- Zone gate: `JAX_PLATFORMS=cpu pixi run python -m pytest cli/tests -q` —
  **138 passed in 127.04 s**, engine-backed walk tests included (the engine is
  built, so `test_walk.py`'s two real walks ran).

Nothing outside `docs/` changed. No GUI was launched, no remote dispatch, no
`pixi run app`. Projects live under `build/lifecycle/`, which is ignored.

## Result

The walk runs end to end, headlessly, unattended, on two mechanisms with one
unchanged entry point, and the numbers above are this machine's. It does not
yet run end to end from a prompt, and the reason is now measured rather than
suspected: the design turn's authoring contract and the digest edit's rewrite
disagree, and the design leg hides its child's failures.

Commit `64b92b29` — `docs/CLI.md` now states all three counts the digest edit
refuses on, dated 2026-09-07.

Dispatch closed: 1 unit — ran the documented lifecycle walk end to end on both example mechanisms (clean, with numbers) and on an agent-designed third (refused at the digest edit), and landed the doc-truth fix the run exposed.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 64b92b29fedb649ce8658cfc380187a412fdf3c8

## State Impact

- target: crisp-reef-5607 — The documented entry point completes the loop headlessly on both example mechanisms on this machine, measured (hinged-arm 15.3 s / 1.03 GB / total_reward -27.109384; linear-carriage 13.1 s / 0.98 GB / -24159.195), but it does NOT complete from --prompt: a design turn that declares the policy strings as module constants is refused at exit 3 by the digest edit, because declare_policy rewrites inline string literals only and agent.py's authoring contract never teaches that. The design leg additionally failed once in 3.76 s with the child agent's reason discarded, and an identical retry succeeded. Criterion stays open on those two gaps.
- target: witty-spark-2613 — Headless mode is exercised again on this machine, with guards (0.2 s RSS sampling, 2.9 GB and 850 s cutoffs) and observed peaks of ~1 GB and walls under 16 s; GUI-attached and remote modes remain documented-not-exercised as the charter requires.
