---
node_id: f2ea38b9-e2b5-563f-9873-375887f645ee
slug: late-pond-2851
title: The RL training loop and mg-legs
created_at: '2026-08-09T15:22:27+00:00'
parents:
- salty-isle-4063
summary: ''
---
Status: blocked

## Current

Blocked on the **GPU training box**, which runs its own checkout of `training/cadex_train.py` that predates ADR-104. Dispatching the next run (B7) would silently ignore two new draws while recording the new algorithm string in the policy header, so the run is blocked rather than skipped. The CPU sanity run is green: 50 iterations, σ 0.3006, witness 4.07e-08 [rec: western-badger-3023].

What works, and is not in doubt:

- **Training is offboard by design.** `training/` is the one top-level directory that is not part of the product: CMake never installs it, no payload carries it, nothing in it enters `pixi.toml`, and it cannot import Cadex. The engine **verifies** a policy and never **produces** one, which is what keeps it free of an optimiser, an accelerator and even numpy [rec: jolly-walrus-3692] [rec: sage-wood-0687].
- The loop is: author the mechanism in an ordinary xscript project → export MJCF → declare the task → train on the GPU box → verify the returned weights against their witness → roll out locally over twelve seeds. Every step but the last is cheap, which is why a feasibility gate runs before GPU time is bought [rec: humble-path-4466].
- **`mg-legs` is the standing benchmark**: a pelvis and two legs built from MG90S servos. Run **B6** is the first policy in the project's history to step *and* survive — checkpoint 2400 scores 6/12, where every prior run scored zero at every checkpoint [rec: humble-path-4466].
- Selection is by **stepping-and-surviving, not by reward**, for the third measured time [rec: humble-path-4466].

**Two trainer flags landed from cdx-rl** (PRs #7 and #8, merged 2026-08-23; this log's ADR-159 — note their own "ADR-152"/"ADR-153" citations are cdx-rl's numbers and collide with the blueprint decisions of those numbers here):

- **`--init-from-task-change REASON`** makes a **curriculum** possible at all. `check_policy_fits` compares the bundle's whole-file digest, so a walker could reach a harder shove band only from a fresh network; the flag skips that one digest and **nothing else** — model digest, observation channels in order, the action table field by field and the network shape are all still checked — and the differing top-level keys must be a subset of `CURRICULUM_TASK_KEYS`, which answers one question: does the change alter what the network reads or what it emits? `--init-from-parent-task` is required beside it, because a `.cxpolicy` header carries its task's digest rather than its content [rec: merry-rain-9062].
- **`--command-slew-deg`** bounds the per-step change of the **issued** command, after the action filter and before the `ctrl` write, reset with the episode. A different operator from the EMA, which bounds smoothness and does not bound rate at all. Default 0.0 is **no limit** — the opposite convention from the filter's alpha, where 0 freezes the command and is refused — and at 0.0 the emitted graph is unchanged, so an existing policy trains the same [rec: merry-rain-9062].

**Still open**: half the episodes at the declared shove band end `tipped`, and backward is the worst direction. B7 is the run that would spend the tenth observation kind — and it is the run the stale checkout blocks [rec: humble-path-4466] [rec: western-badger-3023].
- **The three trainer decisions that arrived from cdx-rl now have cadex ADR numbers**: the action filter is **ADR-160**, the curriculum warm start **ADR-161**, the command slew limit **ADR-162** — renumbered from cdx-rl's 151/152/153, which were already taken here by the blueprint-sheet decisions. All three are written out in `docs/DECISIONS.md` with their measurements, and `training/README.md` documents their flags for the first time [rec: weathered-sand-9705].
- **The standing rule**: cdx-rl proposes an ADR number in its own log; **this repository assigns the real one on merge, and the merging commit rewrites the citations.** It had happened twice (ADR-123/124 → 131/132, ADR-138/139) and was then skipped three times running [rec: weathered-sand-9705].


## Negative knowledge

- [scope: reading a trainer reward curve | confidence: high | evidence: humble-path-4466] Trainer reward is not survival, and selecting a checkpoint by reward has lost to selecting by measured behaviour three separate times. Select by stepping-and-surviving.
- [scope: looping evaluators | confidence: high | evidence: humble-path-4466] evaluate_episode multiplies domain randomisation into the model in place and never restores it, so any evaluator that reuses one model across a table drifts its own masses and inertias every episode. Build a fresh model per episode; both engine call sites already do.
- [scope: azimuth and facing direction | confidence: high | evidence: humble-path-4466] azimuth_degrees is about world +X and the engine has no concept of which way a mechanism faces. mg-legs faces +Y, so an entire investigation had its forward and lateral columns swapped. Measure the forward axis off the model rather than assuming it.
- [scope: reward figures recorded before ADR-101 | confidence: high | evidence: humble-path-4466] Every reward figure recorded before the never-ending-episode fix is non-comparable, because it was measured against an unbounded episode. Survival numbers are unaffected.

- [scope: a test that pins behaviour by source text | confidence: high | evidence: merry-rain-9062] A source-string assertion outlives the source it describes. PR #8 asserted the literal `command_slew_deg = 0.0` appears in the trainer, while a refactor **in the same PR** replaced it with a named `resolved_command_slew_deg()`; every other assertion in the file passed and CI went red on the one that had nothing to do with the feature. Assert on the thing that holds the rule, not on how it was first spelled.
- [scope: a stacked rebase over one file | confidence: high | evidence: merry-rain-9062] One hunk can be applied twice and nothing complains. `resolved_command_slew_deg` shipped **defined twice**, two identical copies differing only in an em-dash; the second silently wins, the first is dead, and the suite passes straight through the duplicate. Neither CI nor review saw it.
- [scope: merging a cdx-rl pull request | confidence: high | evidence: weathered-sand-9705] Deferring the citation rewrite is cheaper than it looks and wrong anyway. ADR-159 judged it "a bigger edit than the confusion warrants"; it was one `perl -pi -e` over three files, and the deferral concealed a third collision (the action filter) that nobody had noticed. Renumber on merge, in the merge.


## Provenance

- western-badger-3023 — the blocker: the GPU box runs its own checkout predating ADR-104
- jolly-walrus-3692 — training/ is offboard by design, with its own pinned venv
- humble-path-4466 — the mg-legs arc, B6, and how a policy is selected
- sage-wood-0687 — why the engine verifies a policy and never produces one
- merry-rain-9062 — ADR-159: the two cdx-rl trainer PRs merged — the curriculum warm start and the command slew limit — and the two defects fixed on arrival
- weathered-sand-9705 — the three trainer ADRs renumbered, and the standing rule restated
