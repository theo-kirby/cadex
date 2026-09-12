---
node_id: 633b6929-a3e6-5607-b5b0-5310d776f9a1
slug: dawn-delta-4361
title: D3. Training is visible while it runs
created_at: '2026-09-12T14:51:24+00:00'
parents:
- crisp-sun-1239
summary: ''
---
Status: open

## Current

Charter criterion: **D3. Training is visible while it runs** The biped's real GPU training updates status, iteration, reward and loss histories, episode length and checkpoint availability without a page reload; committed telemetry appears within five seconds under the measured test conditions; missing or stale data is labelled. Evidence: a browser observation spanning multiple actual training updates plus telemetry tests — synthetic data alone cannot tick it. Declared target `gap-d3-training-visible-while-runs` [rec: lucky-comet-0031]. No evidence exists yet: the owner's redirect claims no implementation and no criterion completion [rec: dusty-peak-9330]. Flips to working only when the evidence the criterion names is recorded.

## Negative knowledge

None yet.

## Provenance

- lucky-comet-0031 — the ot5 directive declared this criterion as gap `gap-d3-training-visible-while-runs`
- dusty-peak-9330 — the owner's charter revision (ADR-284) that introduced D1–D9, claiming none complete
