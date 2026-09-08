---
node_id: 414bd6de-2dd9-55de-b48a-1f324f5cc8d1
slug: silent-mist-5233
title: Two-servo leg rehearsal stops at the design provider quota
created_at: '2026-09-08T03:19:25+00:00'
parents:
- forest-hollow-9339
summary: ''
---
## What

Attempted the documented headless lifecycle walk once on the short plan's two-MG90S robot leg. The design leg exited 1 on the agent subscription limit before producing a script. This is a failed rehearsal, not evidence of a working fifth mechanism and not a new geometry defect.

## Why

Follows the rank-1 experiment in [rec: forest-hollow-9339], serving missions 2 and 6 and charter criteria **The walk exists and is tested headlessly** (`crisp-reef-5607`) and **The walk holds on a second mechanism** (`swift-dusk-2951`). The supplied overseer message asks for reconciliation and already-shipped remote/GUI work; the later explicit contributor prohibition forbids reconciliation, and the current plan and state record that documentation as working. Assumption: execute the current short-rung experiment, without waiting for a person or changing providers when quota refuses it.

On arrival eight source/test files had uncommitted inventory work (CLI main/inventory and their inventory/walk tests; engine CadexInspection, cadex_library_api, cadex_project_worker and test_inventory_scope). They were preserved. To keep their behavior out of this experiment, exported committed `cadex`, `cli`, `training`, and `src/Mod/cadex` with `git archive HEAD` into a fresh external scratch tree. No checkout source, bundle or staged payload was changed.

## Method

Read actor and hypergraph-record skills, STATE, PLAN, the current bet, previous bundle experiment, VISION, CLI walk contract and training SETUP. Baseline commit: `3d6636bd`. Used the archived CLI shim against the ordinary installed bundle refreshed by morning-summit-7848, with engine/module overrides and PYTHONPATH unset. Command shape:

```sh
JAX_PLATFORMS=cpu python monitor.py <snapshot>/cadex walk \
  --engine <installed-bundle-engine> --project <fresh-project> \
  --out <fresh-project>/runs/baseline --prompt '<prompt below>' \
  --trainer-python <existing-training-venv>/bin/python \
  --iterations 1 --envs 4 --seed 0 --timeout 600 --json
```

Prompt: A single robot leg with hip and knee driven by two TowerPro MG90S catalog servos, a thigh, a shin, a foot pad and M3 hardware. Fix the hip support to the world. Give the hip and knee revolute joints position servo actuators at MG90S torque and speed limits, with a joint-angle sensor per axis. Declare a toy training task holding the named crouch angle pair hip 0.4 rad and knee -0.8 rad, with a small effort cost and joint-range termination. Declare the policy so the task can be trained.

Model selected by the CLI: `claude-fable-5`. Existing process-tree monitor samples RSS at 0.2 seconds, cuts off at 2.9 GiB or 850 seconds, TERM then KILL fallback after five seconds. No trainer actually started, so training memory/time budget was unspent. Local ignored evidence: `build/lifecycle/nt3-i36-leg.json` and `build/lifecycle/nt3-i36-leg.err`; scratch project basename `cadex-nt3-i36-leg` under the system temporary directory. Paths are local evidence, not committed artifacts.

## Result

Design: **blocked**, exit 1 after 2.34 seconds. Exact error:

```text
You've hit your session limit · resets 8:30am (Europe/Madrid)
```

Whole command: exit 1, 2.8271 seconds, peak process-tree RSS 386,695,168 bytes, no monitor cutoff. Envelope `ok=false`, empty accepted revision/digest/outputs and empty review; error identifies `leg design, exit 1`. Assembly/MJCF/task, train, declare, rollout and review were **not reached**. No person or guess was used to force progress. No inventory exists to classify catalog placement versus fusion; no four views, section or bounds comparisons exist to inspect.

Project-doc scaffolds exist but have no accepted progress row and no project commit; the failed turn left `.gitignore`, ARCHITECTURE.md, DECISIONS.md, PROGRESS.md and agent.json untracked in its initialized scratch repository. Do not mistake scaffolding for an accepted design. No policy, checkpoint or rollout is committed by this unit.

No source edits, removal, direction change or landed ROADMAP item: no ADR/checkbox change or build was warranted. Engine/CLI suites and packaged/shell gates were not rerun: this is the plan's read-only rehearsal and does not validate the unrelated dirty inventory work. Hypergraph export and check passed: 0 violations, 0 warnings; two records are now unreconciled. GUI remained unlaunched; no remote dispatch or provisioning occurred.

The existing working lifecycle/second-mechanism claims are not falsified by a provider quota failure. What remains missing for this selected experiment is the entire two-servo leg run and its comparable PROGRESS numbers; it adds no completion evidence to either criterion. Next: retry this exact bounded walk after the provider's reported quota reset, without changing mechanism-specific code. The later inventory unit remains subject to its published-output feasibility gate; the inherited dirty implementation is not an accepted result of this dispatch. The record tail grows by one; reconciliation remains the maintainer's work.

Dispatch closed: 1 unit — the two-servo leg rehearsal stops at the design provider quota, with exact error and resource evidence recorded.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 3d6636bdb212a86098fbc960c3d705496f8a4464

## State Impact

- target: crisp-reef-5607 — Fresh two-servo leg rehearsal exits at design on provider session quota; no accepted revision, training or review, existing successful walk evidence unchanged.
- target: swift-dusk-2951 — Planned two-servo leg adds no comparable mechanism numbers: design was refused by provider quota before authoring; retry after reset remains.
