---
node_id: 8d62d718-ac2b-51f6-b804-06a2b4b14ba9
slug: floral-arrow-7365
title: Rehearse and document explicit CPU toy lifecycle selection
created_at: '2026-09-08T16:14:49+00:00'
parents:
- dry-grove-2638
summary: ''
---
## What

Rehearsed the public model-free hinged-arm walk with explicit CPU selection in the discovered CUDA-capable trainer venv. Corrected training/SETUP.md §b, linked that contract from the CLI guide and project scaffold, and recorded ADR-253 and the ROADMAP item.

## Why

This follows dry-grove-2638 short unit 1 and maintains charter criteria “The walk exists and is tested headlessly” and “The agent can see its work without a screen.” The concrete defect was an installation-based CPU assumption despite CUDA-capable venv discovery. Assumption: select CPU through the existing environment variable; preserve production backend defaults. The overseer's requested role passes already preceded the current plan; actor reconciliation remains forbidden.

## Method

Created an isolated temporary project repository, accepted examples/lifecycle/hinged-arm/script.py through `./cadex script --project "$PROJECT" --set examples/lifecycle/hinged-arm/script.py --json`, and copied the example sensors document into its docs directory. Ran exactly one training walk:

```bash
JAX_PLATFORMS=cpu ./cadex walk --project "$PROJECT" \
  --out "$PROJECT/runs/cpu-baseline" --name cpu14.cxpolicy \
  --iterations 1 --envs 4 --seed 0 --timeout 600 --json
```

No explicit trainer path: the command discovered the home-directory cadex-train-venv. External process-tree RSS sampling every 0.2 s enforced a 2.9 GB cutoff and an 850 s whole-walk cutoff. Initial monitoring setup lacked psutil; replaced it with standard `ps` sampling before training. Initial sensor-copy setup lacked the docs directory; created it and repeated script acceptance before the sole training run.

Evidence remains uncommitted in the temporary `cadex-ot4-cpu14` project, `runs/cpu-baseline/review.json`, PROGRESS.md and project Git history; stdout/stderr are temporary `cadex-cpu14-walk` files. No generated review dump, checkpoint or trace enters this repository. The source change is guidance only, with no engine, payload or protocol changes.

## Result

Walk exit 0, monitored elapsed 14.6015 s, peak aggregate process-tree RSS 1,541,804,032 bytes. Receipt device CPU, trainer wall 1.27 s, final batch reward/step -0.38019815, witness error 2.0698448e-9 against 1e-4 tolerance. Verified rollout total reward -27.10938422. All three applicable legs (train, declare, rollout) passed; existing script supplied design/assembly. All four reviews passed: two uncatalogued components, four nonempty named renders, XZ section status ok, one checked base/swing pair below 0.1 mm clearance with zero common volume, zero unknowns, bounds check pass. Engine/source comparison matched 56 top-level Python files with no differences; this is not binary provenance. Project commit 73e684d records the successful walk and PROGRESS.md numbers; working tree clean.

The criteria already have working state evidence; no new lifecycle leg remains exposed by this rehearsal. Toy CPU execution and initial-pose reviews do not prove gait improvement, swept-motion clearance, GUI execution or actual remote dispatch. Next is the selected shared CPU fixture and receipt assertions in existing real CLI training tests; no repeated recovery or CUDA investigation.

Validation: `pixi run python -m pytest cli/tests` with no outer CPU override: 223 passed, no skips, 230.12 s; log in temporary `cadex-cpu14-tests.log`. `git diff --check` passed. No build was needed for documentation and scaffold prose. Hypergraph export/check run before commit.

Dispatch closed: 1 unit — rehearse and document explicit CPU toy lifecycle selection.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 608171b3ea530c6c76152f60837a35f87480b594

## State Impact

- target: crisp-reef-5607 — Public toy walk explicitly selected CPU in the discovered CUDA-capable venv; 14.6 s, 1.54 GB peak RSS, verified policy and all reviews. Setup and project scaffold now state the CPU contract; CLI gate 223 passed.
- target: damp-moon-9297 — CPU rehearsal completed four named renders, XZ section, two-component inventory and the expected touching base/swing clearance finding; reviews remain initial-pose only.
