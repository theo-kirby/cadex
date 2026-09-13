---
node_id: d10d261c-b580-57ad-907a-8d43a4392a77
slug: honest-path-3451
title: Revise Wren foot support from retained policy review
created_at: '2026-09-13T00:24:12+00:00'
parents:
- sage-tower-6445
summary: ''
artifacts:
- docs/probes/wren-fresh/revision.py
- docs/probes/wren-fresh/revision-evidence.json
- docs/probes/wren-fresh/README.md
---
## What

Make one review-driven Wren parameter revision through the public product CLI: foot_len 85 to 105 mm, with policy_on set to 0 for the changed model. Retain both original policy reviews and all training artifacts, document the physical hypothesis and a before/after comparison protocol, and verify historical model/video identity on the persistent dashboard. Deliver the reusable revision.py browser/mesh/inventory probe, compact revision-evidence.json and updated user-facing Wren/operator documentation.

## Why

Follow the critic's requested unit, advancing D5 (sharp-union-6036), D9 (silent-river-6649) and keeping D10 (deep-clover-6012) current. Wren's retained checkpoint 20 survives eight seconds on seed 0, whereas the final policy crosses its declared fell threshold at 0.46 s with -105.757 mm torso X displacement. The decoded final frame shows backward pitch; the checkpoint final frame remains upright. Increase heel support using an existing declared parameter, the smallest reversible authoring operation. This is a hypothesis, not proof that geometry caused learning instability. No deviation, new training experiment or whole-goal completion claim.

## Method

Inspected decoded final frames from both original saved videos. Before editing, captured a SHA-256 inventory of every file under Wren's runs directory and saved its script and manifest to evidence/revision50. Ran ./cadex --project PROJECT params --set policy_on=0 --set foot_len=105 --out PROJECT/evidence/revision50/export --json, then the public render command. Both exited 0 and reported project-local commits cfe516d and 5c14029. The latter also retained the project DECISIONS.md/PROGRESS.md rationale and comparison declaration. All other effective dimensions remain identical; source script text is byte-identical. Exported task bundles differ only in their model reference.

The existing script offsets each foot centroid by length/8: heel reach grows 31.875 to 39.375 mm, toe reach 53.125 to 65.625 mm. Each foot gains 7.936 g. Added mass/inertia and toe reach may hurt control. The final image is a torso-height termination, not evidence of a completed ground impact.

Declared before retraining: evaluate original checkpoint 20 and final policy, and the corresponding revised policies, on rollout seeds [0,1,2,3,4], eight-second maximum episodes, 50 Hz / 400 control steps, same reset distribution and fell threshold. Report per-seed torso X displacement, actual survival duration, fell/termination and total reward, plus mean/min survival and fall count. Original seed 0 already exists; seeds 1–4 remain unmeasured. Old-policy evaluation must use retained old model/task inputs. The upcoming from-scratch training uses the same 240 iterations, 1024 environments, training seed 0, checkpoint interval 20, 1800-second timeout and MemoryMax=20G as wren1, one run at a time in the existing environment.

Ran PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/revision.py PRIVATE_URL PROJECT on the persistent private-address port 8765. Both original playback runs load eight components, show their retained revisions/digests and 85 mm parameter, preserve playback through three polls, and download with the original video digest. Their policy assets match the saved policy hashes. The served STL feet actually measure 85 mm for both old runs and 105 mm for ACCEPTED NOW; this checks geometry rather than only labels. The accepted page shows disabled policy and no substituted historical video. Historical browsing and return to current pass. All 114 retained run files are byte-identical before and after the CLI edit and after browser review. Inspected the new accepted-model screenshot; raw screenshots, decoded frames, envelopes, inventory and comparison declaration remain project-local under evidence/revision50. This is same-machine private-network evidence, not a second-device or new D11 visual-similarity claim.

The first probe assumed binary STL and failed on the server's ASCII STL. Corrected the evidence probe to read either representation; the rerun passed. A final pass added actual policy-asset hash assertions and passed again. No product renderer/server code changed. The operator service was never stopped, replaced or switched. Charter-reload log confirms the owner revision was adopted before iteration 38; this actor follows the supplied charter.

## Result

Wren's accepted revision is a90b84033ced66e50409c25be6150d5042da2d5ea192e419cc31c04d09d20972, digest 502fc7ad0409f8cadb6fb2e46d077fcb55fcfd9c0da2db2cb620e24c261535c1. Port 8765 stays on ot5-wren. A fresh visit selects latest recorded attempt wren1-final (a8073874ab76...), now visibly HISTORICAL relative to the untrained accepted design; ACCEPTED NOW shows 105 mm feet. Checkpoint20 (ce541019cce8...) and final recordings remain available with unchanged identities. The new design has no policy/video or measured gait result yet. Published operator status says so explicitly. No Wren retraining, new dependency, product behavior change, build, shell edit, state-node edit or reconciliation.

Validation: full engine suite 2110 passed, 53 skipped in 269.27 s; full CLI suite 395 passed, 1 skipped in 374.19 s. The suites ran sequentially; their bounded training fixtures are not a Wren experiment. The final persistent-browser probe, py_compile and git diff --check pass. Logs remain in the machine's temporary wren50-engine, wren50-cli and wren50-browser log files. No incomplete zone verification or observed product regression. This record reaches three unreconciled records; the next separate reconcile pass is due. This contributor dispatch explicitly forbids reconciliation, so STATE.md, PLAN.md and state nodes remain untouched.

Dispatch closed: 1 unit — revise Wren's feet through the product CLI, preserve and browser-verify original reviews, and declare the retraining comparison.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 61dcf8d6859e42da2b779b9dfe4b10b41c499b25

## State Impact

- target: sharp-union-6036 — Wren's 85 to 105 mm foot edit preserves all 114 retained run files; persistent browser verifies original model meshes, specs, policy hashes and playable/downloadable videos after the edit.
- target: silent-river-6649 — Wren now has a review-driven accepted foot revision with old policy disabled and a declared seeds 0–4 eight-second before/after protocol; retraining and additional-seed evaluation remain unperformed.
- target: deep-clover-6012 — Port 8765 remains active on Wren: latest attempt wren1-final is visibly historical relative to new accepted revision a90b84033ced; accepted 105 mm feet and historical browsing/playback are verified, and operator status explains pending retraining.
