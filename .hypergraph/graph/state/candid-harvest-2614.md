---
node_id: b88f672e-257e-57ba-83f3-e9061ff94571
slug: candid-harvest-2614
title: D4. Policy videos render, persist and play headlessly
created_at: '2026-09-12T14:51:24+00:00'
parents:
- crisp-sun-1239
summary: ''
---
Status: open

## Current

**Real final-policy and intermediate-checkpoint videos are retained and browser-verified; active-training playback and failure isolation remain open.** Probe1's retained final policy was engine-verified against identical model/task bytes and recorded separately as `probe1-playback`, leaving failed probe1 unchanged. Seed 0 fell at 0.66 simulated seconds; eight frames at 10 fps encode 0.8 seconds. Private-address Chromium playback across refreshes, identity labels and byte-identical download passed, with all frames decoded [rec: amber-gate-7498].

Probe2 checkpoint20 was engine-verified and rendered while its trainer remained active: 81 frames, eight simulated seconds, 8.1 encoded seconds and 16.414 seconds rendering. Corrected browser playback/download and frame/timing checks passed after training stopped. An erroneous browser time-format assertion triggered external harness cleanup that interrupted the trainer before a final policy. The prior final video survives. Sparse committed intervals show progress during rendering, not causal overhead evidence [rec: merry-star-6951].

Keep `open`: successful browser playback during active training, a final video for the new run and reliable failure isolation remain unproved. The interruption was an external experiment-harness failure, not a product-renderer failure; no second-device test is claimed [rec: merry-star-6951]. Fixture download coverage proves received bytes and hashes using browser-accessible download directories, including snap Chromium [rec: ready-orchard-4806].

Charter criterion: **D4. Policy videos render, persist and play headlessly** At least one verified intermediate checkpoint is rendered and appears in the dashboard while training remains active, and the final policy also has a saved video; both play and download in the browser, each identifying model revision, policy digest, rollout seed and simulation time. Evidence: real biped video files, a decoded frame/timing check and a browser playback/download test; a failed render leaves training running and reports its own failure. Declared target `gap-d4-policy-videos-render-persist` [rec: lucky-comet-0031], introduced with no implementation claimed [rec: dusty-peak-9330].

## Negative knowledge

- [scope: headless Chromium download tests on a machine whose Chromium is the snap package | confidence: high | evidence: ready-orchard-4806] Snap confinement gives Chromium a private `/tmp` and refuses hidden paths under `$HOME`; a download directory in either place is invisible to the browser or to the host. A differently confined Chromium would need `CADEX_BROWSER` pointed at an unconfined binary.

## Provenance

- lucky-comet-0031 — the ot5 directive declared this criterion as gap `gap-d4-policy-videos-render-persist`
- dusty-peak-9330 — the owner's charter revision (ADR-284) that introduced D1–D9, claiming none complete
- long-cove-3626 — reproduced the baseline browser download failure against the clean startup commit
- ready-orchard-4806 — traced the failure to snap-confined Chromium; harness collects downloads where the browser can write and proves bytes and digest
- amber-gate-7498 — first real final-policy video, decoded and browser-played/downloaded
- merry-star-6951 — active-training checkpoint render, later successful browser verification and explicit interruption limits
