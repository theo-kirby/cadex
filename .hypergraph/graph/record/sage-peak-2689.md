---
node_id: 4c55e400-6375-59ff-8438-488d7652c26a
slug: sage-peak-2689
title: The unchanged walk verifies a linear carriage beside the arm baseline
created_at: '2026-09-06T20:40:57+00:00'
parents:
- stormy-quill-5350
summary: ''
artifacts:
- examples/lifecycle/README.md
- examples/lifecycle/hinged-arm/PROGRESS.md
- examples/lifecycle/linear-carriage/PROGRESS.md
- examples/lifecycle/linear-carriage/script.py
---
## What

Ran a second repository-owned mechanism, a vertical linear carriage, through
unchanged `cadex walk`, alongside a fresh hinged-arm baseline. Added the two
xscript projects, project architecture/decision/sensor documents, comparable
PROGRESS.md reports, reproduction commands and a real-engine/trainer regression
test asserting the carriage exports a slide joint and verifies its policy.
ADR-203 and ROADMAP record the qualification. The CLI project scaffold and
CLI/MUJOCO docs distinguish training-batch reward from verified rollout reward.

## Why

One unit from the short plan and the overseer's explicit second-mechanism
instruction, targeting swift-dusk-2951 (mission 2). L2's source and packaged
gates landed in parent stormy-quill-5350. Reversible assumption: use an ideal
slider/force motor instead of adding a catalog dependency or hardware physics.
The arm uses a revolute/torque motor, so the second mechanism crosses an
existing joint and actuator type boundary. No walk implementation workaround
was needed. Keep poor control performance visible rather than tune the reward.

These examples are children of Cadex's existing work tree: the CLI correctly
creates no nested repository or automatic commits. This experiment's one
parent-repository commit versions their source, documents and measured numbers;
all policy assets, checkpoints, traces and accepted caches remain untracked.
Source recipes carry policy-disabled placeholder hashes for a fresh run.

## Method

Read actor/record skills, STATE/PLAN, the record tail, VISION, CLI walk and
training contracts, project scaffolding and the existing LGPL arm fixture.
Installed each source with `./cadex script --project P --set SOURCE --json`,
then used the identical `./cadex walk --project P --out P/runs/baseline
--iterations 1 --envs 4 --seed 0 --timeout 600 --trainer-python <repo-venv>
--json`, with JAX_PLATFORMS=cpu. No model call, GUI, remote dispatch or build.
A parent watchdog sampled summed descendant RSS every 0.2 s, stopping above
2.9 GB or 850 s; the trainer separately had a 600 s timeout. Neither fired.

Read each actual exported trace, task and review. Both episodes are 1 s at
50 Hz, both verified rollouts use seed 3 and reach 50 steps. Total reward is
the sum of after-step rewards; rollout reward/step divides by 50. Trainer
reward/step is the receipt's final exploratory training-batch mean, not the
verified rollout average. Height term is -1e-4*(com_z-60)^2 with mm positions;
control cost is -1e-6*abs(effort), but N versus N·mm prevents design ranking.
Both projects' PROGRESS.md retain both rows, definitions and policy/task hashes.

## Result

- Arm: rollout total -27.1093842209; rollout mean -0.542187684419;
  trainer mean -0.380198150873. Walk 15.22 s, sampled tree RSS 986218496 bytes.
- Carriage: rollout total -24159.1953563; rollout mean -483.183907126;
  trainer mean -82.3199081421. Walk 13.52 s, sampled tree RSS 979582976 bytes.
- All train/declare/rollout legs exited 0. Witness errors were
  1.38411674122e-09 (arm) and 5.41889473918e-09 (carriage). Both reached the
  50-step horizon without early termination. The carriage falls to origin
  z=-4699.378313 mm at 1 s: a one-iteration policy on an ideal unlimited guide
  is pipeline evidence, not learned height holding or hardware validation.
- `JAX_PLATFORMS=cpu pixi run python -m pytest cli/tests`: 138 passed in
  143.15 s, exit 0, no skips. Includes the actual slider walk and arm iterate.
- `git diff --check`: exit 0. Hypergraph export/check exit 0 (no warnings
  or violations). No engine/protocol/payload/shell implementation changed;
  engine build, engine suite and packaged/shell gates were not run.

Next: the second-mechanism pipeline criterion has evidence; control quality
remains open. The short-plan L2 and second-mechanism units have landed, so the
separate maintainer/planner pass can pull forward the next rung (including
foreign-revision mutation safety). This third unreconciled record reaches the
maintainer trigger. This actor does not reconcile, edit state or alter the
charter, per the explicit work-iteration prohibition.

Dispatch closed: 1 unit — second mechanism through the unchanged walk, with matched baseline metrics and real CLI verification.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 9f3231d687082753406a29e7df19ba2213edfef1

## State Impact

- target: swift-dusk-2951 — Working: ideal vertical slider/force motor through unchanged cadex walk; both repo-owned projects carry comparable PROGRESS.md definitions and baseline numbers, 50-step verified rollouts, sub-1-GB sampled RSS, and real CLI regression coverage (138 passed). No mechanism-specific workaround; carriage control quality remains poor after one iteration.
- target: calm-peak-5247 — Lifecycle qualified on revolute/torque and slider/force mechanisms with unchanged entry point; project scaffold distinguishes training and verified rollout means. ADR-203 and reproduction examples retain source/docs/numbers only.
