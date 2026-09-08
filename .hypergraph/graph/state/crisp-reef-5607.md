---
node_id: f9d8b739-9a02-5f30-89eb-3a1cb1a32b7a
slug: crisp-reef-5607
title: The walk exists and is tested headlessly
created_at: '2026-09-06T19:18:33+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion: **The walk exists and is tested headlessly.** One documented entry point (a CLI prompt or a headless script) takes a mechanism from design → assembly → MJCF → task → toy-scale local CPU training → policy verify → rollout → review, on this machine, with no human step. Declared target `gap-walk-exists-tested-headlessly-one` [rec: empty-wolf-3962]. The nt3 operator directive re-seeded the same criterion, unticked, as this run's leading frontier [rec: modest-summit-8554].

**Met, 2026-09-07: the walk from `--prompt` completed unattended twice in a row, on two mechanisms designed inside the walk** [rec: cool-fountain-2483] [rec: placid-sky-7374]. Three prompt-walk attempts across nt3: one failure predating both fixes below, then two clean runs on different prompts, mechanisms, joint types, actuator types and seeds. The second run changed nothing in the tree (`dfeccc9f`; `git status` clean) and the CLI suite passed 142 with no skips on it, engine-backed walks included [rec: placid-sky-7374]. This is the plan's tick rule satisfied — two clean of three with the one failure older than both fixes [rec: rustic-loom-0992, on the plan view] — and it answers the reliability doubt that held the node open after the first clean run.

| prompt walk | mechanism, joint, actuator | design | train | declare | rollout | wall | peak RSS | `total_reward` | witness err |
|---|---|---|---|---|---|---|---|---|---|
| nt3b [rec: cool-fountain-2483] | pendulum rig, revolute, position servo | 262.03 s | 14.50 s | 1.43 s | 1.76 s | 280.7 s | 1.23 GB | 425.997 | 4.48e-09 |
| nt3c [rec: placid-sky-7374] | vertical carriage, prismatic, bounded force motor | 172.59 s | 13.06 s | 1.25 s | 1.50 s | 189.4 s | 1.115 GB | 0.0035556 | 3.679e-09 |

Both at 1 iteration × 4 environments (seeds 0 and 1), `--timeout 600`, under the charter's guards (0.2 s process-tree RSS sampling, 2.9 GB and 850 s cutoffs), inside the 15-minute and 3 GB limits. `review.json` (`cadex-walk-review-v1`) landed in each project beside `ARCHITECTURE.md`, `DECISIONS.md` and `PROGRESS.md`. The nt3c design turn wrote the inline-literal `assembly.policy(...)` call with `policy_on` unprompted and recorded three of its own `DECISION:` lines as project ADRs (no collision geom on the rail; a raw force motor so the action space is the force range; termination at `carriage_z < 3` mm) [rec: placid-sky-7374]. Neither number is a claim about learned control: one PPO iteration is a smoke test of the loop, which is what the criterion asks for.

**Earlier evidence, still standing.** `cadex walk` is the documented headless entry point since ADR-199 (commit a4248b26; `docs/CLI.md` walk section, `docs/MUJOCO.md` §7c, ROADMAP tick): two real walks on the plate-and-arm toy from an existing script, `review.json` under `--out`, the scaffolded `.gitignore` keeping checkpoints, `train/` copies and `*-trace.json` out of the project's history while `assets/*.cxpolicy` stays committed; `cli/tests/test_walk.py` pins the digest edit, review reader, leg order and flags plus both real walks [rec: shy-cabin-0798]. Both `examples/lifecycle` recipes ran clean on this machine in nt3 (hinged-arm 15.3 s, 1.03 GB, -27.109384; linear-carriage 13.1 s, 0.98 GB, -24159.195), and commit `64b92b29` made `docs/CLI.md` state all three counts the digest edit refuses on [rec: misty-rain-9048].

**The two legs the first prompt run named are closed** — both were the walk's own defects, not the model's [rec: misty-rain-9048]:

1. **The digest edit no longer refuses an agent-authored script** (commit 7d089bff) [rec: cool-fountain-2483]. `CLI_OVERLAY` in `cli/cadex_cli/agent.py` teaches `weights=` and `sha256=` as inline literals at the call site, names constant-factoring as the mistake, and marks the call as the one exception to the parametric rule; `test_turn_loop.py` pins the contract text and `test_walk.py` refuses the constant-factored script on both keywords, then feeds the prompt's own example through `walk._replace_keyword` byte for byte. `declare_policy` is unchanged by decision.
2. **A failed design leg now names its cause** (commit dca63b13) [rec: ancient-wind-0117]. The `accepted is None` branch in `cli/cadex_cli/__main__.py` reports the last engine refusal (op, failure code, clipped message) or "the engine refused nothing" with the ops called, plus the agent's closing words, each clipped to 400 characters; `run_leg` already carries a child envelope's `error` into the walk envelope, so no `walk.py` change. Three stubbed-turn tests pin it. No automatic retry, no leg-order change, no `OP_ARG_SPECS` change.

Reconcile judgement: flipped `open` → `working` on the second clean prompt walk [rec: placid-sky-7374]. The 2026-09-06 `working` flip rested on walks from an existing script and was reverted when the prompt path failed [rec: misty-rain-9048]; the earlier caution after one clean run ("fixed or lucky") is now answered by an independent second run with every variable changed. What remains on the walk is not its shape: the GUI-attached and remote modes stay documented-not-exercised (`witty-spark-2613`), and the review frontier remains tracked by `damp-moon-9297`. The cold revisit also confirms committed render and section persistence [rec: fair-cedar-7455].

**Latest bounded recipe and cold-revisit evidence:** a fresh hinged-arm CPU walk completed in 16.80 s at sampled peak process-tree RSS 1,056,636,928 bytes. Its verified 50-step rollout retained total reward -27.109384220927513 and witness error 1.3841167412209642e-09. After the producing process exited, six separate public CLI commands (script, asset, inventory, clearance, render and section) preserved accepted revision/digest, policy assets and a byte-identical restored trace. Full built-engine CLI gate: **195 passed, zero skipped** (218.91 s). No persistence defect or recovery was found; this maintenance direction is exhausted and status remains `working`. This is toy CPU evidence, not useful learned control, a prompt reliability trial, GUI/remote execution or packaged qualification; timings overlapped the gate and are observations, not benchmarks [rec: fair-cedar-7455].

**Documentation corrections landed:** VISION principles 5 and 3 now agree with the supported CPU walk: offboard training is a dependency/payload boundary, and policy asset status follows the script rebuild boundary rather than GPU duration. Reconcile judgement: retain `working` on the existing toy CPU evidence; neither prose correction reran or recertified the runtime, identified a missing leg, or expanded GUI/remote qualification [rec: polished-moss-9358] [rec: neat-summit-3586].

**Ordinary installed-bundle qualification now passes.** The baseline design refused the stale bundled API import before acceptance, training or review; this deployment failure did not invalidate the prior working lifecycle evidence [rec: northern-hill-9362]. Supported staging, one shell build and bundle installation resolved it without a source fix. Fresh hinged-arm design and the full CPU walk then passed in 16.04 s at 1,054,588,928 bytes peak process-tree RSS, with one iteration, four environments and seed 0. Witness error was 1.3841167412209642e-09 and rollout total reward -27.109384220927513. Same installed-root packaged lifecycle and full CLI gates passed 15 and 195 tests respectively, with no skips; the matching built-bundle background shell gate also passed. Reconcile judgement: retain `working`; the packaging direction is exhausted. This qualifies the local installed-engine route at toy scale, not useful learned control, a new prompt reliability trial, hermetic portability, GUI-attached lifecycle or remote training [rec: strong-raven-3067].

## Negative knowledge

- [scope: what the walk commits from a training leg | confidence: medium | evidence: shy-cabin-0798] Before ADR-199 the `train` leg's commit carried `job.cxpolicy`, `job.best.cxpolicy` and the store copy — three copies of one policy. The store's asset is the project (ADR-194); checkpoints and traces are not, and the `.gitignore` says so. Reversible per project, because the file is editable.
- [scope: `declare_policy` in `cli/cadex_cli/walk.py` against agent-authored scripts | confidence: high | evidence: misty-rain-9048, cool-fountain-2483] The rewrite handles inline `weights="…"` / `sha256="…"` literals only; a script that names them through module constants is refused at exit 3. The fix went into the authoring contract, not the rewrite: resolving constants would make the walk guess at a script it did not write. A test pins the refusal as intended behaviour.
- [scope: the first design-leg failure inside `cadex walk --prompt` on 2026-09-07 | confidence: medium | evidence: misty-rain-9048, ancient-wind-0117] One observed fast failure (3.76 s, after one `describe_api` call) with the child's reason discarded, and one identical retry that succeeded in 214 s. Its cause is unrecoverable: the envelope that would have named it landed afterwards. Not reproduced on purpose; the two clean runs since [rec: placid-sky-7374] make it the outlier, not the pattern.
- [scope: comparing `total_reward` across prompt-walk projects | confidence: high | evidence: placid-sky-7374] The two reward expressions are different objectives in different units, so 425.997 and 0.0035556 compare runs of one project only, never designs against each other — the same caveat `examples/lifecycle/README.md` records for the two example mechanisms.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- fond-mesa-1562 — fixed-toy evidence does not close the general entry point
- shy-cabin-0798 — ADR-199: cadex walk qualified on the toy through two real walks, review.json in the project, checkpoints and traces out of its history, 13 tests
- modest-summit-8554 — nt3 operator directive re-seeds the criterion unticked as this run's leading frontier
- misty-rain-9048 — the walk run end to end on this machine: clean on both example recipes with numbers, refused at the digest edit on an agent-designed project; docs/CLI.md names all three refusal counts
- cool-fountain-2483 — the authoring contract teaches weights=/sha256= as inline literals, two tests tie the prompt's example to the rewrite, and the walk from a prompt ran clean end to end (280.7 s, 1.23 GB, total_reward 425.997)
- ancient-wind-0117 — a turn with no accepted script reports its cause (last engine refusal or "refused nothing" plus closing words, 400-char clip); the walk carries it with no walk.py change; 142 CLI tests, no skips
- placid-sky-7374 — the second independent prompt walk (vertical carriage, prismatic, force motor, seed 1) ran clean end to end on an unchanged tree: 189.4 s, 1.115 GB, total_reward 0.0035556; two clean of three attempts, the criterion declared met
- brave-delta-4193 — bounded documented arm walk refreshes CPU training, verified baseline rollout and committed review evidence; CLI 161 passed without skips
- fair-cedar-7455 — fresh CPU walk and six cold public commands preserve accepted identity, policy assets and restored trace; CLI 195 passed without skips
- lucky-canyon-6724 — preserve working CPU-walk evidence while tracking the unimplemented VISION rationale correction
- polished-moss-9358 — VISION principle 5 corrected to the offboard dependency boundary and supported CPU path; no runtime rerun
- neat-summit-3586 — VISION principle 3 policy-asset rationale corrected without changing the asset contract or runtime evidence
- northern-hill-9362 — installed-bundle baseline stops at design; prior working lifecycle evidence preserved
- strong-raven-3067 — refreshed installed engine accepts design and full bounded CPU walk; same-root lifecycle/CLI gates and matching background shell gate pass
