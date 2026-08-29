---
node_id: f2ea38b9-e2b5-563f-9873-375887f645ee
slug: late-pond-2851
title: The RL training loop and mg-legs
created_at: '2026-08-09T15:22:27+00:00'
parents:
- salty-isle-4063
summary: ''
---
Status: open

## Current

**The training loop itself is proven, locally, end to end** — what remains blocked is gait scale. The whole arc (agent-authored mechanism → MJCF export → task → CPU training → verified policy → rollout → live plot in the editor) ran on the M4 Mac Mini in one afternoon at toy scale, twice: once hand-driven (ADR-170), once as a single prompt to the product agent [rec: staid-valley-0501] [rec: gilded-trail-2519]. The **GPU box** still runs its own checkout of `training/cadex_train.py` that predates ADR-104, so dispatching the next mg-legs run (B7) would silently ignore two new draws while recording the new algorithm string in the policy header — that dispatch stays blocked until the box's checkout is updated [rec: western-badger-3023].

The local CPU leg, now first-class [rec: stormy-cedar-1763]:

- A venv per `training/SETUP.md` §b (Homebrew 3.13; numpy 2.5.1 imposes a ≥3.12 floor pixi's 3.11 cannot meet). `--progress <project>/training-progress.json` lights the shell's Training panel with no `watch` leg [rec: stormy-cedar-1763].
- **The live training gate was broken and CI could not see it**: its pinned `--unroll 25` predates the ADR-084..088 episode changes and plateaus below threshold on every seed measured, while the trainer's default converges to 3.3+. The gate skips wherever jax is absent — every pixi environment, CI included — so a venv run is what actually exercises it. It now takes the best of three seeds [rec: stormy-cedar-1763].
- Measured toy-scale costs: ~5–6 it/s at 64 envs, ~2.2 GB peak RSS; the ADR-170 toy trained in 141 s total, the rehearsal task in 44 s [rec: stormy-cedar-1763] [rec: staid-valley-0501] [rec: gilded-trail-2519].

**The run is visible as a shape now** (ADR-169) [rec: mild-badger-7944] [rec: dry-garden-5337]: `progress.json` carries a `curve` field (512 `[iteration, reward]` pairs, additive under the unchanged schema on the ADR-101/ADR-103 precedent), and `mesh_agent/cadex_training_plot.py` draws it in the Training editor — the shell's first plot, the first draw handler on a Cadex space type, no operator classes because there is still no train button.

**The rehearsal named the gaps between here and the North Star as one CLI prompt** [rec: gilded-trail-2519]: the engine's trace reads +1729.95 against −302.17 zero-torque, full horizon, holds 2.1° off vertical, bracing check passed unprompted — but two of the arc's legs needed a human, and both are tool-surface gaps, not intelligence gaps. The CLI agent has **no shell** (cannot run the trainer; cannot read `training/SETUP.md`, so it handed back guessed, wrong flags) and **no `put_asset`** (cannot bring a policy home). Both refusals were clean and resumable. Follow-ups parked in `docs/IDEAS.md`, alongside a shell bug the rehearsal video surfaced (`hide_render` does not follow the hydrator's viewport hiding).

What works, and is not in doubt:

- **Training is offboard by design.** `training/` is not part of the product: CMake never installs it, no payload carries it, nothing in it enters `pixi.toml`, and it cannot import Cadex. The engine **verifies** a policy and never **produces** one [rec: jolly-walrus-3692] [rec: sage-wood-0687]. `device: "cpu"` in a policy header is a recorded feature — the artifact says what produced it [rec: staid-valley-0501].
- The loop is: author the mechanism in an ordinary xscript project → export MJCF → declare the task → train (GPU box for a gait, local CPU for a toy) → verify the returned weights against their witness → roll out. Every step but the GPU one is cheap [rec: humble-path-4466] [rec: staid-valley-0501].
- **`mg-legs` is the standing benchmark**: a pelvis and two legs built from MG90S servos. Run **B6** is the first policy in the project's history to step *and* survive — checkpoint 2400 scores 6/12, where every prior run scored zero at every checkpoint [rec: humble-path-4466].
- Selection is by **stepping-and-surviving, not by reward**, for the third measured time [rec: humble-path-4466].

**Two trainer flags landed from cdx-rl** (PRs #7 and #8, merged 2026-08-23; this log's ADR-159 — note their own "ADR-152"/"ADR-153" citations are cdx-rl's numbers and collide with the blueprint decisions of those numbers here):

- **`--init-from-task-change REASON`** makes a **curriculum** possible at all. `check_policy_fits` compares the bundle's whole-file digest, so a walker could reach a harder shove band only from a fresh network; the flag skips that one digest and **nothing else** — model digest, observation channels in order, the action table field by field and the network shape are all still checked — and the differing top-level keys must be a subset of `CURRICULUM_TASK_KEYS`, which answers one question: does the change alter what the network reads or what it emits? `--init-from-parent-task` is required beside it, because a `.cxpolicy` header carries its task's digest rather than its content [rec: merry-rain-9062].
- **`--command-slew-deg`** bounds the per-step change of the **issued** command, after the action filter and before the `ctrl` write, reset with the episode. A different operator from the EMA, which bounds smoothness and does not bound rate at all. Default 0.0 is **no limit** — the opposite convention from the filter's alpha, where 0 freezes the command and is refused — and at 0.0 the emitted graph is unchanged, so an existing policy trains the same [rec: merry-rain-9062].
- **The three trainer decisions that arrived from cdx-rl now have cadex ADR numbers**: the action filter is **ADR-160**, the curriculum warm start **ADR-161**, the command slew limit **ADR-162** — renumbered from cdx-rl's 151/152/153, which were already taken here by the blueprint-sheet decisions. All three are written out in `docs/DECISIONS.md` with their measurements, and `training/README.md` documents their flags for the first time [rec: weathered-sand-9705].
- **The standing rule**: cdx-rl proposes an ADR number in its own log; **this repository assigns the real one on merge, and the merging commit rewrites the citations.** It had happened twice (ADR-123/124 → 131/132, ADR-138/139) and was then skipped three times running [rec: weathered-sand-9705].

**Still open**: B7 (blocked on the GPU box's stale checkout, above); half the mg-legs episodes at the declared shove band end `tipped`, and backward is the worst direction [rec: humble-path-4466] [rec: western-badger-3023]. And the two CLI tool-surface gaps, which are the North Star's next moves [rec: gilded-trail-2519].

## Negative knowledge

- [scope: reading a trainer reward curve | confidence: high | evidence: humble-path-4466] Trainer reward is not survival, and selecting a checkpoint by reward has lost to selecting by measured behaviour three separate times. Select by stepping-and-surviving.
- [scope: looping evaluators | confidence: high | evidence: humble-path-4466] evaluate_episode multiplies domain randomisation into the model in place and never restores it, so any evaluator that reuses one model across a table drifts its own masses and inertias every episode. Build a fresh model per episode; both engine call sites already do.
- [scope: azimuth and facing direction | confidence: high | evidence: humble-path-4466] azimuth_degrees is about world +X and the engine has no concept of which way a mechanism faces. mg-legs faces +Y, so an entire investigation had its forward and lateral columns swapped. Measure the forward axis off the model rather than assuming it.
- [scope: reward figures recorded before ADR-101 | confidence: high | evidence: humble-path-4466] Every reward figure recorded before the never-ending-episode fix is non-comparable, because it was measured against an unbounded episode. Survival numbers are unaffected.
- [scope: a test that pins behaviour by source text | confidence: high | evidence: merry-rain-9062] A source-string assertion outlives the source it describes. PR #8 asserted the literal `command_slew_deg = 0.0` appears in the trainer, while a refactor **in the same PR** replaced it with a named `resolved_command_slew_deg()`; every other assertion in the file passed and CI went red on the one that had nothing to do with the feature. Assert on the thing that holds the rule, not on how it was first spelled.
- [scope: a stacked rebase over one file | confidence: high | evidence: merry-rain-9062] One hunk can be applied twice and nothing complains. `resolved_command_slew_deg` shipped **defined twice**, two identical copies differing only in an em-dash; the second silently wins, the first is dead, and the suite passes straight through the duplicate. Neither CI nor review saw it.
- [scope: merging a cdx-rl pull request | confidence: high | evidence: weathered-sand-9705] Deferring the citation rewrite is cheaper than it looks and wrong anyway. ADR-159 judged it "a bigger edit than the confusion warrants"; it was one `perl -pi -e` over three files, and the deferral concealed a third collision (the action filter) that nobody had noticed. Renumber on merge, in the merge.
- [scope: fixed-seed convergence gates | confidence: high | evidence: stormy-cedar-1763] Which seeds converge PPO is platform arithmetic, not semantics — seed 0 converged on the machine that authored the gate and plateaus deterministically on an M4. A convergence gate must buy more than one ticket, and a gate that skips in CI was last verified on whatever machine last bothered.
- [scope: MJX collision pairs | confidence: high | evidence: staid-valley-0501] MJX implements no cylinder↔box collision pair, and the engine accepts a model the trainer then refuses at `mjx.put_model`. Until an export-time warning exists, declare box collision (or contact-group masks that never form the pair) on anything cylindrical that must train.
- [scope: spin-out termination on overpowered tiny mechanisms | confidence: high | evidence: staid-valley-0501] The guard must comfortably exceed σ·torque_limit/I·Δt or exploration dies in a handful of steps and the guard becomes the curriculum — measured as mean episode length 3.7 of 100 and a reward plateau, fixed by raising the guard and letting the spin cost do the shaping.

## Provenance

- western-badger-3023 — the blocker: the GPU box runs its own checkout predating ADR-104
- jolly-walrus-3692 — training/ is offboard by design, with its own pinned venv
- humble-path-4466 — the mg-legs arc, B6, and how a policy is selected
- sage-wood-0687 — why the engine verifies a policy and never produces one
- merry-rain-9062 — ADR-159: the two cdx-rl trainer PRs merged — the curriculum warm start and the command slew limit — and the two defects fixed on arrival
- weathered-sand-9705 — the three trainer ADRs renumbered, and the standing rule restated
- stormy-cedar-1763 — the local CPU loop stands up: the venv, SETUP §b, and the live gate fixed to best-of-three seeds
- mild-badger-7944 — progress.json learns the curve: 512 pairs, additive, schema unchanged
- dry-garden-5337 — ADR-169: the reward curve reaches the Training editor, the shell's first plot
- staid-valley-0501 — ADR-170: the balance-toy litmus closes the local loop end to end, with its three findings
- gilded-trail-2519 — the rehearsal: one prompt, both traps dodged, the two CLI tool-surface gaps named
