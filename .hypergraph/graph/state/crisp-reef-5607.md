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

**Met on the repo-owned toy from an existing script, 2026-09-06 (ADR-199, commit a4248b26)** [rec: shy-cabin-0798]. `cadex walk` is the documented headless entry point (`docs/CLI.md` walk section, `docs/MUJOCO.md` §7c note, ROADMAP tick). Two real walks on the plate-and-arm toy: a placeholder digest to a verified rollout (`total_reward -27.1094`), then a reward change with a warm start (`-55.3480`), eight project commits. `review.json` lands under `--out` as the walk's own artifact; the scaffolded `.gitignore` keeps checkpoints, `train/` copies and `*-trace.json` out of the project's history while `assets/*.cxpolicy` stays committed. `cli/tests/test_walk.py` (13 tests) pins the digest edit, the review reader, leg order and flags, plus both real walks; the CLI suite was 130 passed, no skips. Domain docs are exercised by the caller (`docs/sensors.md`), not generated [rec: shy-cabin-0798].

**Run end to end on this machine in nt3, 2026-09-07, three times** [rec: misty-rain-9048]. Under the charter's guards (0.2 s process-tree RSS sampling, 2.9 GB and 850 s cutoffs), at 1 iteration × 4 environments, seed 0, from the `examples/lifecycle` recipes installed by `cadex script --set`:

| project | wall | peak RSS | rollout `total_reward` [rec: misty-rain-9048] |
|---|---|---|---|
| hinged-arm | 15.3 s | 1.03 GB | -27.109384 |
| linear-carriage | 13.1 s | 0.98 GB | -24159.195 |
| agent-designed pendulum rig | 15.8 s | 1.27 GB | none — stopped at `declare`, exit 3 |

Both example mechanisms complete the whole loop with no human step and land `review.json` in the project. Zone gate: the full CLI suite, 138 passed in 127 s, engine-backed walk tests included. Commit `64b92b29` is the doc-truth half: `docs/CLI.md` now states all three counts the digest edit refuses on [rec: misty-rain-9048].

**Not met from `--prompt`: two legs still need a person, and the reason is measured** [rec: misty-rain-9048]:

1. **The digest edit refuses an agent-authored script** [rec: misty-rain-9048]. A fresh design turn produced an accepted script with `policy_on=num(...)` and exactly one `assembly.policy(...)` call, but declared the weights and sha256 strings as module constants and passed them by name. `walk.py:_replace_keyword` rewrites inline string literals only, so the walk stopped at exit 3 ("carries no weights=\"…\" string to rewrite"). The authoring contract in `cli/cadex_cli/agent.py`'s `describe_api` prompt teaches the switch and never mentions the literals, so the model's factoring was a reasonable style the walk cannot accept. A hand edit closes it, which is the human step the criterion forbids.
2. **The design leg failed once, opaquely, and a byte-identical retry succeeded** [rec: misty-rain-9048]. Inside `cadex walk --prompt` the child turn ended after one `describe_api` call in 3.76 s with "the turn finished without the engine accepting a script" and no reason from the child; the same argv run directly took 214 s and exited 0 with a full script. The leg works, but its failure envelope discards the child agent's reason, so an unattended retry policy cannot be written.

The record's recommended next unit is the smaller, reversible one: teach the authoring contract that `weights=` and `sha256=` must be inline string literals (one paragraph plus a test), rather than widening `declare_policy` to resolve module constants [rec: misty-rain-9048].

Reconcile judgement: flipped from `working` back to `open`. Two records agree: the operator re-seeded the criterion unticked for nt3 [rec: modest-summit-8554], and the nt3 run measured that the walk does not complete from a prompt, which is the ideation → design half the criterion claims [rec: misty-rain-9048]. The 2026-09-06 `working` flip rested on walks that started from an existing script, and the earlier judgement already noted the design leg was not re-driven by a model turn inside the walk [rec: shy-cabin-0798]. The example-recipe evidence stands and is not withdrawn. The general criteria the charter keeps separate — a second mechanism, the GUI-attached and remote modes — remain their own gap nodes (`swift-dusk-2951`, `witty-spark-2613`).

## Negative knowledge

- [scope: what the walk commits from a training leg | confidence: medium | evidence: shy-cabin-0798] Before ADR-199 the `train` leg's commit carried `job.cxpolicy`, `job.best.cxpolicy` and the store copy — three copies of one policy. The store's asset is the project (ADR-194); checkpoints and traces are not, and the `.gitignore` says so. Reversible per project, because the file is editable.
- [scope: `declare_policy` in `cli/cadex_cli/walk.py` against agent-authored scripts | confidence: high | evidence: misty-rain-9048] The rewrite handles inline `weights="…"` / `sha256="…"` literals only; a script that names them through module constants is refused at exit 3, and nothing in the authoring contract forbids that style. Measured on one agent-designed project; the refusal is a contract mismatch, not a bug in the rewrite.
- [scope: the design leg's failure envelope inside `cadex walk --prompt` | confidence: medium | evidence: misty-rain-9048] One observed fast failure (3.76 s, after one `describe_api` call) with the child's reason discarded, and one identical retry that succeeded in 214 s. Not reproduced on purpose; the cause of the first failure is unknown.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- fond-mesa-1562 — fixed-toy evidence does not close the general entry point
- shy-cabin-0798 — ADR-199: cadex walk qualified on the toy through two real walks, review.json in the project, checkpoints and traces out of its history, 13 tests
- modest-summit-8554 — nt3 operator directive re-seeds the criterion unticked as this run's leading frontier
- misty-rain-9048 — the walk run end to end on this machine: clean on both example recipes with numbers, refused at the digest edit on an agent-designed project; docs/CLI.md names all three refusal counts
