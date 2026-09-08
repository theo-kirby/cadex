---
node_id: 141509a9-5686-54a5-80fd-24bc993655bf
slug: lucid-snow-0350
title: Provider-free hinged-arm walk passes with scratch ignore-scaffolding caveat
created_at: '2026-09-08T08:02:23+00:00'
parents:
- cool-garden-5811
summary: ''
---
## What

Ran the selected provider-free hinged-arm lifecycle rehearsal once against the existing qualified stage. Script acceptance, CPU training, policy declaration, verification/rollout and headless review all succeeded. No product source was changed.

## Why

Follows the finite standing-maintenance bet [rec: cool-garden-5811], advancing continued evidence for charter criteria **The walk exists and is tested headlessly** and **The agent can see its work without a screen** (missions 1, 2 and 6). The supplied overseer request for reconciliation/planning was already reflected in STATE and the newer bet; this contributor dispatch obeyed the explicit prohibition on reconciliation and selected the updated short unit. Live provider repair remains parked. This run cannot supply agent-design, resumed repair, second-mechanism, GUI or remote evidence. Existing working criterion evidence is not retired or promoted.

## Method

At repo HEAD ca5ca00a, use E=the existing build/engine/cadex-engine-0.0.0-macos-arm64 stage, T=$PWD/.venv/bin/python, P=a fresh external scratch directory named cadex-nt3-i190-arm. Logs remain in its sibling cadex-nt3-i190-evidence directory, outside the product repository.

Commands, with variables denoting local paths rather than committed machine paths:

```sh
git init -q "$P"
./cadex script --engine "$E" --project "$P" --set examples/lifecycle/hinged-arm/script.py --json
JAX_PLATFORMS=cpu .pixi/envs/default/bin/python "$MONITOR" ./cadex walk --engine "$E" --project "$P" --out "$P/runs/baseline" --trainer-python "$T" --iterations 1 --envs 4 --seed 0 --timeout 600 --json
```

MONITOR is the existing nt3_monitor.py wrapper: launches a new session, samples descendant RSS via ps every 0.2 s, terminates the process group at 850 seconds or 2.9*1024^3 bytes. It reported no cutoff. Inspect persisted review.json, PROGRESS.md, git subjects and tracked/ignored lists; decode and visually inspect the four embedded PNG previews; inspect XZ SVG paths and contour metadata. No stage refresh, full build, provider call, fake design turn, GUI or remote execution. No CLI/engine/shell source zone changed, so no source suite/build gate was invoked: the real staged end-to-end command is this experiment's validation.

## Result

Both commands exited 0. Whole monitored walk 15.6578 s; sampled process-tree peak 1,059,848,192 bytes (0.987 GiB); walk's internal timer 15.4694 s. Train/declare/rollout legs 11.35/1.08/1.25 s, each exit 0. CPU trainer: one iteration, four environments, seed 0; training wall 1.16464 s, 4,609 parameters, reward/step -0.3801981508731842. Policy e3108bb763bf5e71636fca4bbb697d487e63919411377ff10975e9a1843608a3; witness error 1.3841167412209642e-09. Verified rollout seed 3: 50 control steps, 27 frames, total_reward -27.109384220927513 (lift -27.10907313052507; control_cost -0.000311090402448284). Toy execution evidence, not learned useful control.

Review: two components, zero catalogued components. One initial-pose pair checked, base/swing below clearance (0 mm distance, 0 mm3 common volume), zero unknown pairs, exactly as the example documents. Render front/top/right/iso covered 23678/91348/23700/75694 pixels; images show the plate and arm in solved placement. XZ at Y=3.125 mm is available/ok with a closed contour for each named object; SVG paths inspected, no separate rasterized section inspection. Render and section match rollout revision 63cd29194a373d23a3906370a5733fefa27c2812da4a3b7470dac4945bd5595c and digest 31b1848c15d8fbf21aa73403f31cd23cba3aa174ddc88c8492444ef3f4137980.

PROGRESS contains script/train/script/params/walk rows and the corresponding five commits. Latest scratch commit 406976f subject is `cadex walk 1 it × 4 envs → runs/baseline`; absolute --out becomes the same portable label in the progress row. Review JSON, inventory/clearance docs and all five SVGs are tracked. Scratch status is clean.

Experiment setup limitation: I pre-initialized the external scratch git repository, which bypassed first-visit git/ignore scaffolding documented in docs/CLI.md. It therefore has 68 tracked files and zero ignored files, including generated checkpoints and rollout traces, automatically committed by the CLI. This was an actor setup error against the no-checkpoint/rollout-commit constraint, not evidence of a product ignore defect. No generated files entered the Cadex repository; no history was rewritten. Ordinary first-visit ignore behavior was not exercised and must not be claimed as passing. Future authorized fresh-project work should let the CLI initialize the project instead of pre-initializing git. No rerun is justified by this setup mistake within the selected one-run unit.

Next: return this successful downstream lifecycle result and explicit setup limitation to the planner. No reproducible product failure was demonstrated, so the conditional correction is not dispatchable. Do not repeat the rehearsal automatically or retry/probe the live provider. The charter checkboxes remain human-owned; missing new evidence is live resumed modification and any other separately authorized coverage, not another provider-free baseline. ADR/ROADMAP edits are unnecessary for an experiment with no shipped behavior or removal. Hypergraph export/check must pass before committing this record.

Dispatch closed: 1 unit — provider-free lifecycle passed; scratch git initialization bypassed ignore scaffolding, recorded without claiming that coverage.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: ca5ca00ac544e769d40fcc668a82aa14091b2b9f

## State Impact

- target: crisp-reef-5607 — Existing-stage provider-free hinged-arm walk passed in 15.6578 s and 0.987 GiB; preinitialized scratch git bypassed ignore scaffolding, so no first-visit ignore coverage or live repair evidence
- target: damp-moon-9297 — Fresh walk persisted four inspected named previews, an XZ section, two-component inventory and the documented base/swing clearance finding at matching rollout revision
