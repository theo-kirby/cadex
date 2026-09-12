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

**First real observation taken; the run being trained is now identified; a re-observation under the fix on the fresh biped is still needed.** During the biped's GPU probe (`runs/probe1`, see D9 `silent-river-6649`), the dashboard, served on the Tailscale address by the real `cadex review --host <tailscale> --port 0`, showed seven successive iterations (13 → 23) in 12 s on its own two-second poll, each 0.21–1.4 s after the corresponding committed `progress.json` update, with no reload, histories growing 14 → 24, state `training`, freshness `live`; a screenshot and `evidence/probe1-observe.json` are retained under the project, summarised in `docs/HEADLESS-BIPED-REVIEW.md` [rec: lucid-journey-6875]. That observation exposed a defect: the run under training showed `RELATION UNKNOWN` and no model because `run.json` started with null identity [rec: lucid-journey-6875]. ADR-289 (commit `7a63fa63`) fixes it: `cadex walk` starts `run.json` from the project manifest (accepted revision, digest, parameter specs, `identity_source` = `project manifest (script.json) at walk start`) before the trainer writes its first telemetry sample, so the page shows CURRENT and a borrowed, labelled model while training. This is fixture-browser-tested (a headless-Chromium test selects a training run, reads its identity, specs and borrowed model, then watches telemetry arrive); CLI suite 358 passed, 1 skipped. No real walk ran under the fix [rec: lively-gate-6535].

Implemented earlier and unchanged: the offboard trainer's atomic `train/progress.json` snapshot carries update time, task/model digests and bounded loss and episode-length histories (512-sample cap preserving first and last; a caught training failure keeps the last reported iteration and histories); the dashboard reads only each run's fixed progress file, polls every two seconds and renders metrics and SVG histories without reload; starting/training snapshots older than 30 seconds are labelled stale (a freshness label, not a process-death claim); terminal done/failed snapshots do not expire; checkpoint references are contained within the run and sha256-verified on each poll. Fixture browser coverage: three atomic commits each within five seconds, historical identity preserved, missing/partial output, stale-but-reachable server, failed and terminal states, run switching without borrowed curves; reader tests refuse traversal/symlink escapes, wrong task identities and nonfinite or oversized histories. ADR-287 [rec: kind-fountain-5086]. Final-policy publication failures now write failed telemetry (D8, `cool-gate-3332`) [rec: long-cove-3626].

Known limits: histories are sampled, not full-resolution; remote training-progress mirrors are outside this local path; hard kills can still leave stale rather than failed telemetry; per-poll checkpoint hashing overhead on long histories is unmeasured [rec: kind-fountain-5086]. The real observation spans 12 s of one probe, not a longer training [rec: lucid-journey-6875].

Charter criterion: **D3. Training is visible while it runs** The biped's real GPU training updates status, iteration, reward and loss histories, episode length and checkpoint availability without a page reload; committed telemetry appears within five seconds under the measured test conditions; missing or stale data is labelled. Evidence: a browser observation spanning multiple actual training updates plus telemetry tests — synthetic data alone cannot tick it. Declared target `gap-d3-training-visible-while-runs` [rec: lucky-comet-0031], introduced with no implementation claimed [rec: dusty-peak-9330]. Retain `open`: the real observation exists but was taken with the identity defect present; the criterion needs the fresh biped re-observed under ADR-289 over a longer training.

## Negative knowledge

None yet.

## Provenance

- lucky-comet-0031 — the ot5 directive declared this criterion as gap `gap-d3-training-visible-while-runs`
- dusty-peak-9330 — the owner's charter revision (ADR-284) that introduced D1–D9, claiming none complete
- kind-fountain-5086 — ADR-287: retained loss/episode histories, checkpoint integrity, stale/failed/terminal labelling and live polling, with browser and writer tests on fixtures
- long-cove-3626 — ADR-288 closed the final-publication stale-telemetry gap this node's limits listed
- lucid-journey-6875 — first real observation during the fresh biped's GPU probe; the null-identity defect
- lively-gate-6535 — ADR-289: run identity recorded from the manifest before training, fixture-browser-tested
