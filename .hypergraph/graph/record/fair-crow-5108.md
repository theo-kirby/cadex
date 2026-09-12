---
node_id: 5f39c337-a799-5b1b-99e3-a84b0caa3295
slug: fair-crow-5108
title: Product-agent shin55 revision trained live on the persistent dashboard with ten-seed review
created_at: '2026-09-12T22:15:45+00:00'
parents:
- royal-arrow-2065
summary: ''
---
## What

The product agent (claude-sonnet-5, the project's stored model) authored Reed's review-driven revision through the CLI: shin_len 80 → 55 mm with the 100 mm feet kept, task semantics unchanged, policy_on off first, its reasoning recorded as project ADR-007 and a design-specs entry (CLI commit af0339d, accepted revision fe266d481062…). One bounded GPU training on the working copy ot5-biped-copy29 followed (240 × 1024, seed 0, checkpoints every 20, 1800 s timeout, 20 GiB cap, no warm start), observed on the persistent operator dashboard rather than a temporary server; a checkpoint 20 video was published and browser-checked on port 8765 while training continued, the renderer's overhead was measured from trainer-committed iteration intervals, the final policy was retained with its video, the ten-seed comparison was run in an independent copy, and the persistent URL was verified at experiment start, at completion and after one post-training restart. The experiment exposed a review defect, fixed as ADR-302 with a regression: outputs with byte-identical BREP (a mirrored pair of limbs) lost all but one side's mesh in the accepted view and the retained training view.

## Why

Advances silent-river-6649 (D9) and deep-clover-6012 (D10) exactly as the critic asked after royal-arrow-2065: close the product-agent authorship gap, run one bounded retraining, keep port 8765 current with identity verified at start and completion, publish a checkpoint video during training with measured overhead, retain the final video and earlier results. A one-word capacity probe (the negative knowledge from the earlier quota refusals) preceded the request and succeeded; the agent then authored without refusal. The ADR-302 fix was taken in the same unit because the persistent dashboard showed the running biped with one leg during this very experiment, the charter puts exposed review defects in scope, and the fix is one mapping plus a test; it changes no protocol, engine or shell.

## Method

Prompt retained as the copy's evidence/agentrev.prompt.txt: the recorded 70/90/100 mm results, choose exactly one physical geometry revision with its mechanism, keep reward/termination/reset/control/episode/torque/limits, policy_on to 0 first, record decisions and specs, do not train. Command: timeout 900 ./cadex --project "$COPY" --out "$COPY/evidence/agentrev" --json -p "$(cat …/agentrev.prompt.txt)"; receipt evidence/agentrev-agent.json (exit 0, digest a0dc163fde65…, only shin_len and policy_on changed). Then PYTHONPATH=cli:cli/tests pixi run python "$COPY/evidence/shin55-experiment.py" "$COPY" shin55 "http://$(tailscale ip -4):8765/": params export with policy_on=0, model XML asserted different from copy100's, training view retained, running record written, trainer launched in a systemd scope, evidence/agentrev_observe.py opened the persistent URL fresh (default selection asserted, orbit/zoom, seven live iterations), checkpoint 20 imported via cadex asset / script --set / params policy_on=1 into runs/shin55-checkpoint20, video rendered only after the trainer had returned to ordinary iterations (≥ 23), evidence/agentrev_check_video.py decoded and played it on the persistent URL, final policy stored and retained as runs/shin55-final with its own video, all nine prior run.json digests asserted unchanged. docs/probes/operator-review/verify.py ran against the persistent URL for shin55-final after completion and again after systemctl --user restart cadex-operator-review. docs/probes/reed-baseline/evaluate.py copied the stopped project to ot5-biped-shin55-seeds and rolled seeds 0–9 through ./cadex script --set. docs/probes/reed-agentrev/summarize.py writes the compact evidence.json. Project history committed in the copy (aab7455); bulk videos, traces and checkpoints stay project-local.

Verification: focused review-server suite 32 passed, 1 skipped (90 s); the new regression fails on the old source and passes on the new; full CLI suite with --basetemp outside the checkout 374 passed, 1 skipped in 373.94 s, run after the trainer exited; git diff --check clean. No engine, protocol, payload or shell change, so no engine suite rerun, packaged gate or build.

## Result

D9 now has product-agent revision authorship with a bounded retraining, playable videos for both designs and a common-seed comparison; D10 has persistent-URL evidence across a real experiment start and completion. Facts: trainer exit 0, 850 s wall, reward/step 0.508, host peak 8.28 GB, GPU peak 15,134 MiB. Fresh visit during training selected RUN shin55 with page iterations 3–11 within 0.26–1.69 s of commit, one navigation. Checkpoint 20 (policy 4745829c6f80…, witness 3.66e-08) survived 8 s on seed 0; its video 89bfc9ecde0e… (81 frames, style cadex-prototype-light-v1) rendered in 14.2 s while committed iteration went 18 → 34; nine iteration intervals inside the render window had median 1.414 s (max 1.463) against 1.438 s before and 1.341 s after, so the shared-scene renderer's overhead on GPU training was not measurable under these conditions; the trainer's own checkpoint publication (~53 s per boundary) dominates. Final policy 609ef8e83c18… (witness 7.03e-08), video c23508ad3e92… (6 frames, 0.46 s), fresh visit after completion selected RUN shin55-final with playback, download digest match, historical probe3-final and return to current. Ten seeds: 4 falls (0.44–0.90 s on seeds 0, 2, 5, 6), 6 eight-second survivors at 44.7–49.5 mm forward, mean duration 5.034 s, mean forward displacement 79.1 mm, seed-0 trace reproduced, source unchanged — survival improved over probe3 (10 falls) and foot90 (9 falls) on the same seeds; it is a standing shuffle, not a walking gait. Persistent service still running on port 8765, published status ot5-biped-copy29 / shin55-final. ADR-302 landed: accepted model now retains all eight Reed meshes (verified over the API after the restart); frozen training views of shin55, copy100 and probe3 keep their partial meshes as recorded, by the no-rebuild constraint.

Concerns and assumptions: no second-device visit; the dashboard restart happened after training, not during it, deliberately. The shin55 run record was frozen before ADR-302, so its training-time view shows five of eight parts and says so. The ten-seed evaluation rows live in the seeds copy; the compact summary is committed. No new dependency. The unreconciled tail is now three records; a reconcile pass is due. Whole-goal completion is not claimed; D9 still wants a lifecycle report linking D1–D8 evidence, and D11 owner acceptance remains explicit.

Dispatch closed: 1 unit — product-agent shin55 revision, live checkpoint-published retraining on the persistent dashboard, ten-seed review and the ADR-302 mesh fix

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 57030af0e94fed1184901200b637e908a676f57c

## State Impact

- target: silent-river-6649 — Product agent authored the review-driven shin_len 80→55 mm revision (project ADR-007); bounded GPU retraining, checkpoint/final videos and a ten-seed comparison (4 falls, 6 survivors, 79.1 mm mean) now exist beside the earlier designs; lifecycle report linking D1–D8 still open
- target: deep-clover-6012 — Persistent port 8765 observed across a real experiment: running run selected by default before first iteration, live updates, checkpoint video during training, shin55-final selected after completion, restart-after-training reverified; second-device visit still absent
- target: shy-meadow-0959 — ADR-302: byte-identical outputs each keep their accepted tessellation, so mirrored limbs no longer lose a side in the accepted view or retained training views; earlier frozen views stay as recorded
