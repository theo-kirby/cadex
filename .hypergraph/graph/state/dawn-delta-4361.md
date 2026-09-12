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

**Telemetry retention and live polling are implemented and browser-tested on fixtures; real fresh-biped GPU observation is still absent.** The offboard trainer's atomic `train/progress.json` snapshot now carries update time, task/model digests and bounded loss and episode-length histories (512-sample cap preserving first and last samples; a caught training failure keeps the last reported iteration and histories). The dashboard reads only each run's fixed progress file, polls every two seconds and renders metrics and SVG histories without reload. Starting/training snapshots older than 30 seconds are labelled stale (a freshness label, not a process-death claim); terminal done/failed snapshots do not expire. Checkpoint references are contained within the run and sha256-verified on each poll — "retained" means integrity, not engine policy verification. The headless browser fixture observed three separate atomic telemetry commits each within five seconds, historical model identity preserved, missing/partial output, stale-but-reachable server, failed and terminal states, and run switching without borrowing another run's curves; reader tests refuse traversal/symlink escapes, wrong task identities and nonfinite or oversized histories. No dependency, engine, protocol, payload or shell change; ADR-287 [rec: kind-fountain-5086].

Known limits: histories are sampled, not full-resolution; remote training-progress mirrors are outside this local path; hard kills can still leave stale rather than failed telemetry; per-poll checkpoint hashing overhead on long histories is unmeasured [rec: kind-fountain-5086]. Final-policy publication failures, which the same record listed as a stale-telemetry gap, now write failed telemetry (see D8, `cool-gate-3332`) [rec: long-cove-3626].

Charter criterion: **D3. Training is visible while it runs** The biped's real GPU training updates status, iteration, reward and loss histories, episode length and checkpoint availability without a page reload; committed telemetry appears within five seconds under the measured test conditions; missing or stale data is labelled. Evidence: a browser observation spanning multiple actual training updates plus telemetry tests — synthetic data alone cannot tick it. Declared target `gap-d3-training-visible-while-runs` [rec: lucky-comet-0031], introduced with no implementation claimed [rec: dusty-peak-9330]. Retain `open`: the fixture evidence is real but synthetic; the criterion needs the fresh biped's actual GPU training, which is blocked on the D9 creation (`silent-river-6649`).

## Negative knowledge

None yet.

## Provenance

- lucky-comet-0031 — the ot5 directive declared this criterion as gap `gap-d3-training-visible-while-runs`
- dusty-peak-9330 — the owner's charter revision (ADR-284) that introduced D1–D9, claiming none complete
- kind-fountain-5086 — ADR-287: retained loss/episode histories, checkpoint integrity, stale/failed/terminal labelling and live polling, with browser and writer tests on fixtures
- long-cove-3626 — ADR-288 closed the final-publication stale-telemetry gap this node's limits listed
