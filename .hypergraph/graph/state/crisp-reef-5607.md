---
node_id: f9d8b739-9a02-5f30-89eb-3a1cb1a32b7a
slug: crisp-reef-5607
title: The walk exists and is tested headlessly
created_at: '2026-09-06T19:18:33+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Charter criterion: **The walk exists and is tested headlessly.** One documented entry point (a CLI prompt or a headless script) takes a mechanism from design → assembly → MJCF → task → toy-scale local CPU training → policy verify → rollout → review, on this machine, with no human step. Declared target `gap-walk-exists-tested-headlessly-one` [rec: empty-wolf-3962]. The nt3 operator directive re-seeds the same criterion, unticked, as this run's leading frontier: "run the documented headless lifecycle entry point end to end, on this machine, and record exactly which leg still needs a person or a guess" [rec: modest-summit-8554].

**Met on the repo-owned toy from an existing script, 2026-09-06 (ADR-199, commit a4248b26)** [rec: shy-cabin-0798]. `cadex walk` is the documented headless entry point (`docs/CLI.md` walk section, `docs/MUJOCO.md` §7c note, ROADMAP tick). Two real walks on the plate-and-arm toy: a placeholder digest to a verified rollout (`total_reward -27.1094`), then a reward change with a warm start (`-55.3480`), eight project commits. `review.json` lands under `--out` as the walk's own artifact; the scaffolded `.gitignore` keeps checkpoints, `train/` copies and `*-trace.json` out of the project's history while `assets/*.cxpolicy` stays committed. `cli/tests/test_walk.py` pins the digest edit, the review reader, leg order and flags, plus both real walks. Domain docs are exercised by the caller (`docs/sensors.md`), not generated [rec: shy-cabin-0798].

**Run end to end on this machine in nt3, 2026-09-07, on both example recipes** [rec: misty-rain-9048]. Under the charter's guards (0.2 s process-tree RSS sampling, 2.9 GB and 850 s cutoffs), at 1 iteration × 4 environments, seed 0, from the `examples/lifecycle` recipes installed by `cadex script --set`:

| project | wall | peak RSS | rollout `total_reward` |
|---|---|---|---|
| hinged-arm [rec: misty-rain-9048] | 15.3 s | 1.03 GB | -27.109384 |
| linear-carriage [rec: misty-rain-9048] | 13.1 s | 0.98 GB | -24159.195 |
| agent-designed pendulum rig, first attempt [rec: misty-rain-9048] | 15.8 s | 1.27 GB | none — stopped at `declare`, exit 3 |
| agent-designed pendulum rig, after the contract fix [rec: cool-fountain-2483] | 280.7 s | 1.23 GB | 425.997 |

Commit `64b92b29` is the doc-truth half of the first run: `docs/CLI.md` states all three counts the digest edit refuses on [rec: misty-rain-9048].

**Met from `--prompt` once, 2026-09-07 (commit 7d089bff)** [rec: cool-fountain-2483]. The walk from a prompt ran end to end, unattended, all four legs exit 0: design 262.03 s, train 14.50 s, declare 1.43 s, rollout 1.76 s; 280.7 s wall, 1.23 GB peak, inside the charter's 15-minute and 3 GB guards. Review: `total_reward` 425.997 (`lift_height` +427.193, `effort_cost` -1.194, `speed_cost` -0.001), 4673 policy parameters trained on CPU, witness error 4.48e-09, `review.json` (`cadex-walk-review-v1`) landed beside `ARCHITECTURE.md`, `DECISIONS.md` and `PROGRESS.md`. Same pendulum-rig prompt, guards and flags as the first attempt, so the comparison is like for like. The design turn wrote the inline-literal `assembly.policy(...)` call unprompted by any hand edit. With the two example mechanisms that is the loop closed on three mechanisms, one designed by the agent inside the walk [rec: cool-fountain-2483].

**The two legs the first prompt run named are closed** [rec: misty-rain-9048] — both were the walk's own defects, not the model's:

1. **The digest edit no longer refuses an agent-authored script** [rec: cool-fountain-2483]. The first attempt factored `weights=` and `sha256=` into module constants, which `walk.py:_replace_keyword` cannot rewrite, and the authoring contract never said otherwise [rec: misty-rain-9048]. `CLI_OVERLAY` in `cli/cadex_cli/agent.py` now teaches both strings as inline literals at the call site, digest spelled out even as a placeholder, names the constant-factoring as the mistake, and marks the call as the one exception to the parametric rule. Two deterministic tests tie the prompt to the rewrite: `test_turn_loop.py` pins the contract text, and `test_walk.py` refuses the constant-factored script on both keywords, then feeds the prompt's own example through `walk._replace_keyword` and asserts the result byte for byte. `declare_policy` is unchanged: widening it to resolve module constants was refused, because the walk must not guess at a script it did not write. `docs/CLI.md` §2 leg 4 now says the contract teaches both the switch and the literals [rec: cool-fountain-2483].
2. **A failed design leg now names its cause** (commit dca63b13) [rec: ancient-wind-0117]. A `cadex -p` turn that ends with no accepted script used to report one bare sentence and drop everything the parent knew [rec: misty-rain-9048]. The `accepted is None` branch in `cli/cadex_cli/__main__.py` now reports, in one line, the last tool call the engine refused (op, failure code, clipped message) or "the engine refused nothing" with the ops the agent did call and "never offered a script", plus the agent's own closing words, each clipped to 400 characters (`REASON_CHARS`). No `walk.py` change: `run_leg` already copies a child envelope's `error` into the leg and `command_walk` interpolates it, so a design leg at exit 3 names its cause in the walk envelope. Three stubbed-turn tests in `test_turn_loop.py` against the real bridge and engine pin the refused-script, `describe_api`-only and empty cases. No automatic retry, no leg-order change, no `OP_ARG_SPECS` change [rec: ancient-wind-0117].

Zone gate after each unit: the full CLI suite, engine-backed walk tests included — 138 passed before the contract fix, 140 after it (125 s) [rec: cool-fountain-2483], 142 after the envelope, no skips (127 s) [rec: ancient-wind-0117].

**Why the criterion stays open: design-leg reliability, not shape** [rec: cool-fountain-2483] [rec: ancient-wind-0117]. The prompt path is one clean run out of two attempts across nt3; the first attempt died in 3.76 s after one `describe_api` call and its reason was discarded before the envelope fix, so its cause is still unknown [rec: misty-rain-9048]. One clean run does not distinguish "fixed" from "lucky". Both records decline to tick, and the reconcile agrees: the tick needs at least one more independent `--prompt` walk, now that a failure would be nameable. The general criteria the charter keeps separate — a second mechanism (`swift-dusk-2951`), the GUI-attached and remote modes (`witty-spark-2613`) — are untouched by these units and remain their own gap nodes [rec: ancient-wind-0117].

Reconcile judgement: status held at `open`. The 2026-09-06 `working` flip rested on walks from an existing script and was reverted when nt3 measured the prompt path failing [rec: misty-rain-9048]; the prompt path now has one clean run, which is the shape met but not the reliability the criterion's "no human step" demands. Flipping to `working` again on one run would repeat the earlier mistake.

## Negative knowledge

- [scope: what the walk commits from a training leg | confidence: medium | evidence: shy-cabin-0798] Before ADR-199 the `train` leg's commit carried `job.cxpolicy`, `job.best.cxpolicy` and the store copy — three copies of one policy. The store's asset is the project (ADR-194); checkpoints and traces are not, and the `.gitignore` says so. Reversible per project, because the file is editable.
- [scope: `declare_policy` in `cli/cadex_cli/walk.py` against agent-authored scripts | confidence: high | evidence: misty-rain-9048, cool-fountain-2483] The rewrite handles inline `weights="…"` / `sha256="…"` literals only; a script that names them through module constants is refused at exit 3. The fix went into the authoring contract, not the rewrite: resolving constants would make the walk guess at a script it did not write. A test now refuses the constant-factored script on both keywords, so the refusal is pinned as intended behaviour.
- [scope: the first design-leg failure inside `cadex walk --prompt` on 2026-09-07 | confidence: medium | evidence: misty-rain-9048, ancient-wind-0117] One observed fast failure (3.76 s, after one `describe_api` call) with the child's reason discarded, and one identical retry that succeeded in 214 s. Its cause is unrecoverable: the envelope that would have named it landed afterwards. Not reproduced on purpose.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- fond-mesa-1562 — fixed-toy evidence does not close the general entry point
- shy-cabin-0798 — ADR-199: cadex walk qualified on the toy through two real walks, review.json in the project, checkpoints and traces out of its history, 13 tests
- modest-summit-8554 — nt3 operator directive re-seeds the criterion unticked as this run's leading frontier
- misty-rain-9048 — the walk run end to end on this machine: clean on both example recipes with numbers, refused at the digest edit on an agent-designed project; docs/CLI.md names all three refusal counts
- cool-fountain-2483 — the authoring contract teaches weights=/sha256= as inline literals, two tests tie the prompt's example to the rewrite, and the walk from a prompt ran clean end to end (280.7 s, 1.23 GB, total_reward 425.997)
- ancient-wind-0117 — a turn with no accepted script reports its cause (last engine refusal or "refused nothing" plus closing words, 400-char clip); the walk carries it with no walk.py change; 142 CLI tests, no skips
