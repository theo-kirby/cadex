---
node_id: ee76166f-316d-5647-9dd0-2b7a0f3a6104
slug: candid-forest-9800
title: Retrain Reed with longer feet and verify live dashboard restart
created_at: '2026-09-12T19:40:32+00:00'
parents:
- brave-field-8478
summary: ''
artifacts:
- docs/probes/reed-foot90/evidence.json
- docs/probes/reed-foot90/results.json
---
## What

Completed one review-driven 70→90 mm Reed foot-length experiment through the public `cadex walk --set` path: one bounded fresh GPU retraining, verified final video, real dashboard restart during training, two-design browser review and seeds 0–9/eight-second comparison. Added reproducible restart/history probes, a selectable-run extension to the existing evaluation harness, compact evidence and a user-facing report with ADR-292.

## Why

Advances D2/D5/D6/D9 under the critic's requested physical edit/retrain/video/restart unit. Both product-agent attempts (default and claude-sonnet-5) were refused by the provider's session limit before authoring. Instead of waiting or doing more baseline-only measurements, the actor applied the single accepted parameter edit through the supported CLI; project ADR-005 and design specs explicitly disclose this fallback and its support-area/mass/inertia hypothesis. This deviates from the requested product-agent authorship and does not claim to satisfy that requirement. Other effective parameters and task semantics remain unchanged; training task JSON differs only in model metadata. No checkpoint warm start, old-mechanism import or second training run.

## Method

Commands and exact identities are in docs/HEADLESS-BIPED-REVIEW.md and docs/probes/reed-foot90/{evidence,results}.json. External project ot5-biped retains the full artifacts. `systemd-run --user --scope --unit=cadex-foot90 -p MemoryMax=20G env XLA_PYTHON_CLIENT_MEM_FRACTION=0.45 timeout --signal=TERM --kill-after=20s 2100 ./cadex walk --project "$PROJECT" --out "$PROJECT/runs/foot90" --set foot_len=90 --name foot90.cxpolicy --iterations 240 --envs 1024 --seed 0 --timeout 1800 --leg-timeout 2000 --json` exited 0. The local offboard GPU trainer reported 317.802 s; 32 engine witness samples passed at maximum error 9.817e-08 versus 0.0001. Thirty one-second samples observed host peak 5,060,366,336 bytes and GPU maximum 15,084 MiB; GPU sampling is not a whole-run peak claim.

The real CLI dashboard was restarted on its same private-address port while one identical trainer PID/start-tick identity advanced iterations 35→43. Chromium labelled the outage stale, recovered the same document without navigation, and showed iterations 37/39/41/43 and growing loss histories. Final video rendering and existing project-local decode/playback/download check passed: six 512-square frames at 10 fps, 0.6 encoded seconds, 0.5 simulation seconds, seed 0. Browser history checks compare exact retained identity and design-spec content, all three 240-point curves, actual downloaded 70/90 mm foot meshes, model orbit/zoom, and both saved videos; baseline visibly historical.

The evaluation harness ran ten real public-engine CLI rollouts in ot5-biped-foot90-seeds-v2, pins model/task/policy hashes, reproduces seed 0 exactly and confirms its source project unchanged. All 250 pre-existing run/asset files still match the pre-edit manifest. Initial harness issues were explicit failures: training model expected loaded; STL assumed binary; document-link list confused with document content; and the first evaluation overlapped a browser evidence write and correctly refused source drift. Corrected observation/parsing/document access and a fresh evaluation copy all passed; the initial external logs/copy remain. No synthetic training evidence replaces real results.

`pixi run python -m pytest cli/tests`: 362 passed, 1 skipped in 304.69 s. Probe compilation and git diff --check passed. No engine/shell/protocol code changed, no new dependency, no build and no engine-suite rerun. External project history retains the accepted edit and final policy plus compact review evidence; bulk videos/checkpoints/traces remain outside the product repository.

## Result

Training identity cf98060cdac1… / 11394a342e1c…; playback identity 0596013572c6… / 395faa6bd23f…. Model hash 3f84f92d3f57…; final policy 4e573dd637af…; saved video 1e17ab439a02…. Revised policy falls in 9/10 seeds at 0.50–0.80 s; seed 9 survives eight seconds with +43.370 mm displacement. Mean observed duration 1.338 s and mean +X displacement 160.842 mm, versus baseline final 0.498 s / 200.854 mm and 10/10 falls. This remains poor gait, not repeatable walking or general improvement. Baseline checkpoint20 remains a 10/10 survivor.

D6 now has its missing real active-training restart evidence; existing completed-run save/reopen evidence remains intact. D5 and D2 gain distinct real physical-design models/specs/curves/videos, and D9 gains retraining/comparison. No whole-goal completion claim or charter checkbox edit.

A demonstrated D2 defect remains open: ordinary walk --set calls retain_training_view before training with no tessellation for the accepted swept attempt. foot90/training-view.json permanently records available:false, reason accepted attempt retained no tessellation. The browser truthfully reports missing; final rollout model works. Earlier probe3's custom harness rendered before retention, masking this ordinary-command gap. No snapshot was rewritten from later geometry. Next unit should fix/test this product path; product-agent revision authorship and full D7 real copy/retraining remain unproven. Assumption: only the actor's explicit parameter fallback was authorized, not relabelling it as product-agent work. No state nodes, STATE.md or PLAN.md were edited and no reconciliation was run.

Dispatch closed: 1 unit — revise Reed foot length, retrain once, verify restart/video/history and compare ten seeds

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 63a41252ce5958798220b692e07c3ef1b07657c1

## State Impact

- target: clever-field-7845 — Real private-address dashboard restart during foot90 GPU training passed: same single trainer PID/start ticks, iterations 35–43 and same browser document recovery; completes the missing active-training restart evidence.
- target: shy-meadow-0959 — Both physical designs pass real browser mesh/spec identity and orbit/zoom; ordinary walk --set exposes missing retained training tessellation, truthfully labelled and still unfixed.
- target: sharp-union-6036 — Baseline 70 mm and revised 90 mm feet retain distinct browser models/specs, 240-point curves and playable/downloadable videos; all 250 old run/asset files unchanged.
- target: silent-river-6649 — One actor-applied review-driven foot change and bounded 240-iteration GPU retraining complete; ten-seed result 9 falls and 1 survivor, with verified final video. Product-agent authorship remains unmet after two quota refusals.
