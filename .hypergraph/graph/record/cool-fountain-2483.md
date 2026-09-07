---
node_id: 7fe0c679-042d-575b-a834-71165602d49d
slug: cool-fountain-2483
title: Teach the authoring contract the policy literals, and the walk from a prompt runs clean
created_at: '2026-09-07T21:09:28+00:00'
parents:
- glad-snow-3838
summary: ''
---
## What

Taught the CLI's authoring contract the one thing the walk's digest edit
needs from a design turn, and then re-ran the walk from a prompt as evidence.

One paragraph in `CLI_OVERLAY` (`cli/cadex_cli/agent.py`): the two strings
behind the `policy_on` switch — `weights=` and `sha256=` — must be written
as inline string literals at the `assembly.policy(...)` call site, with the
64-character digest spelled out even when it is a placeholder; factoring
either into a module constant is named as the mistake, and this one call is
marked as the exception to the parametric rule the same prompt pushes
everywhere else.

Two deterministic tests, so the prompt and the rewrite cannot drift apart:

- `test_turn_loop.py::test_the_prompt_teaches_the_two_policy_strings_as_inline_literals`
  pins the contract text and the named mistake.
- `test_walk.py::test_declare_refuses_the_constant_factored_script_and_takes_the_taught_one`
  refuses the constant-factored script on **both** keywords (this is exactly
  what nt3's first walk from a prompt hit), and then extracts the example
  call out of `CLI_OVERLAY` itself and feeds it through
  `walk._replace_keyword`, asserting the rewritten result byte for byte. If
  the prompt's example ever stops being rewritable, that test fails.

`docs/CLI.md` §2 leg 4 said the authoring contract "teaches the switch but
not yet the literals"; it now says it teaches both, and names the test that
holds them together.

`declare_policy` is unchanged. Widening it to resolve module constants was
considered and refused (plan rank 1 forbids it, and the question policy
prefers the reversible option): the walk must not guess at a script it did
not write.

## Why

Charter criterion: **"The walk exists and is tested headlessly"** (frontier
`crisp-reef-5607`, mission item 2). Short-rung rank 1 of the plan
(`young-crane-9546`), and the overseer's dispatch for this iteration, with
two asks: pin it deterministically rather than by a 214 s prompt re-run, and
then re-run the `--prompt` leg once as evidence.

`misty-rain-9048` measured why the walk from a prompt stopped: the design
turn wrote `POLICY_WEIGHTS = "lift.cxpolicy"` above the call and passed it by
name, which reads better and is refused, because the digest edit is a literal
rewrite. The prompt taught the switch and said nothing about the literals, so
the model's style choice was the walk's exit 3.

## Method

- Read `walk.py:_replace_keyword` / `declare_policy` and `agent.py`'s
  `CLI_OVERLAY` to place the paragraph where the switch is already taught.
- Wrote the two tests, then the doc edit in the same commit.
- Zone gate: `JAX_PLATFORMS=cpu pixi run python -m pytest cli/tests -q` —
  **140 passed in 125.17 s** (138 before this unit; the engine is built, so
  `test_walk.py`'s two real end-to-end walks ran).
- Commit `7d089bff`.
- Evidence run, after the commit, headless, fresh project under
  `build/lifecycle/` (gitignored), same guard discipline as the first run:
  a harness sampling process-group RSS every 0.2 s with a 2.9 GB and 850 s
  SIGKILL cutoff, `--iterations 1 --envs 4 --seed 0 --timeout 600`,
  `--trainer-python $PWD/.venv/bin/python`, `--model claude-fable-5`, and the
  same pendulum-rig prompt `misty-rain-9048` used, so the comparison is like
  for like. No GUI, no remote dispatch, no `pixi run app`.

## Result

**The walk from `--prompt` ran end to end, unattended, all four legs exit 0.**

| leg | exit | seconds |
|---|---|---|
| design | 0 | 262.03 |
| train | 0 | 14.50 |
| declare (the digest edit) | 0 | 1.43 |
| rollout | 0 | 1.76 |

Whole walk: **280.7 s wall, 1.23 GB peak RSS**, well inside the charter's
15-minute and 3 GB guards. Review: `total_reward` **425.997**
(`lift_height` +427.193, `effort_cost` -1.194, `speed_cost` -0.001), policy
sha256 `35f96576…`, weights `lift_task.cxpolicy`, training 4673 parameters on
CPU, witness error 4.48e-09. `review.json` (`cadex-walk-review-v1`) landed in
the project beside `ARCHITECTURE.md`, `DECISIONS.md` and `PROGRESS.md`.

The design turn wrote the call the contract now teaches, unprompted by any
hand edit:

```
    pol = assembly.policy(
        lift_task,
        weights="lift_task.cxpolicy",
        sha256="35f9657648d0c5a255708bad7d2c50a169c2ece184ee07cc5bfadd82c93ba620")
```

(the digest above is the walk's rewrite of the placeholder the turn wrote).

So ideation → design → assembly → MJCF → task → local CPU training → policy
verify → rollout → review completed with **no human step**, from one
documented entry point, on this machine. With `misty-rain-9048`'s two example
mechanisms, that is the criterion's claim met on three mechanisms, one of
them designed by the agent inside the walk.

What is still missing before `crisp-reef-5607` can be ticked with confidence:
**reliability of the design leg, not its shape.** The prompt path is now
1 clean run out of 2 attempts across the run — the first attempt in
`misty-rain-9048` died in 3.76 s after one `describe_api` call, and the walk
discarded the child's own reason. One clean run does not distinguish "fixed"
from "lucky"; the swallowed reason is what makes that impossible to tell
apart unattended, and it is the plan's rank 2 and the next unit. A person
reading a failed walk today still cannot see why the design leg failed.

Nothing else in the tree changed. The unreconciled tail is 2 nodes; that is
the maintainer's to fold, not mine.

Dispatch closed: 1 unit — taught the authoring contract that the policy weights/sha256 must be inline literals, pinned it with two deterministic tests that tie the prompt's example to the walk's rewrite, and re-ran the walk from a prompt clean end to end (four legs, exit 0, 280.7 s, 1.23 GB, total_reward 425.997).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 7d089bffb98994cf596c6932b68d25bb22344d6c

## State Impact

- target: crisp-reef-5607 — the walk from --prompt now completes all four legs unattended (design 262.03 s, train 14.50 s, declare 1.43 s, rollout 1.76 s, all exit 0; 280.7 s wall, 1.23 GB peak, total_reward 425.997, review.json landed). The digest edit no longer refuses an agent-authored script: CLI_OVERLAY teaches weights=/sha256= as inline literals and two tests tie the prompt's example to walk._replace_keyword. Remaining risk is design-leg reliability, not shape: 1 clean run of 2 attempts, and the failure envelope still swallows the child's reason.
