---
node_id: b88f672e-257e-57ba-83f3-e9061ff94571
slug: candid-harvest-2614
title: D4. Policy videos render, persist and play headlessly
created_at: '2026-09-12T14:51:24+00:00'
parents:
- crisp-sun-1239
summary: ''
---
Status: working

## Current

**Wren's checkpoint-20 video was verified, rendered, played and downloaded while training remained active; its final-policy video is also retained and browser-verified.** Engine witness errors were below 1e-4 for both. Checkpoint video has 81 decoded frames/8.1 encoded seconds for eight simulated seconds; final video has six frames/0.6 encoded seconds for a 0.46-second seed-0 fall. Identity labels, download digests, polling-preserved playback and historical/current selection passed. The shared delivered scene style is reused; this is not a new D11 reference comparison or a second-device check [rec: sage-tower-6445].

**Probe3 has browser-verified intermediate playback/download while training is active and a retained verified final-policy video.** Checkpoint20 passes the engine witness check, runs eight simulated seconds and yields 81 decoded frames/8.1 encoded seconds. Both sequential checkpoint render collections pass playback, three refreshes, matching-byte download and revision/policy/seed/time labels while training remains active. The currently referenced repeated video and the original bytes/receipt remain retained [rec: light-brook-2640].

The successful 240-iteration trainer produces a verified final policy and a seven-frame/0.7 encoded-second video of a seed-0 fall at 0.52 simulated seconds. Final decoding, playback across refreshes, download digest and labels pass after correcting a numeric-format assertion; collection reuses existing artifacts without further training or rendering [rec: light-brook-2640].

Judgement: mark `working` because the required active checkpoint, final video and reported failed-render isolation are now demonstrated. A missing-trace render request exits 1 while training stays active; this proves that refusal path, not an encoder crash. Renderer throughput cost is unisolated, and browser evidence is on this machine's private address rather than a second device [rec: light-brook-2640].

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
- light-brook-2640 — active intermediate and final video verification; missing-trace refusal leaves trainer active
- sage-tower-6445 — Wren active-training checkpoint and final-policy videos with engine witnesses, decoded timing and browser playback/download
