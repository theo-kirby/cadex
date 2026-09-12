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

Charter criterion: **D4. Policy videos render, persist and play headlessly** At least one verified intermediate checkpoint is rendered and appears in the dashboard while training remains active, and the final policy also has a saved video; both play and download in the browser, each identifying model revision, policy digest, rollout seed and simulation time. Evidence: real biped video files, a decoded frame/timing check and a browser playback/download test; a failed render leaves training running and reports its own failure. Declared target `gap-d4-policy-videos-render-persist` [rec: lucky-comet-0031]. No evidence exists yet: the owner's redirect claims no implementation and no criterion completion [rec: dusty-peak-9330]. Flips to working only when the evidence the criterion names is recorded.

## Negative knowledge

None yet.

## Provenance

- lucky-comet-0031 — the ot5 directive declared this criterion as gap `gap-d4-policy-videos-render-persist`
- dusty-peak-9330 — the owner's charter revision (ADR-284) that introduced D1–D9, claiming none complete
