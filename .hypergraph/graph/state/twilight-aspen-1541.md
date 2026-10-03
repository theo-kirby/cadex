---
node_id: af9ad815-4170-5455-9209-184716a81387
slug: twilight-aspen-1541
title: D2. From a browser alone, a person can watch and steer a design (orun2)
created_at: '2026-10-03T10:54:46+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run orun2: **D2. From a browser alone, a person can watch and steer a design.** - Each of the following is proven by a test driven through the existing headless Chromium path (`cli/cadex_cli/browser.py`) against a real engine: 1. **Start a turn.** Start a design turn from a prompt, optionally with an attached image. Watch it live as the transcript streams and the renders and model update as revisions are accepted. 2. **Move a slider.** Move a parameter slider and see the rebuilt model. Report p50 and p95 latency on a warm project beside the raw-NDJSON bar (`cadexd_latency_integration.py`). 3. **Leave a comment.** Comment on the whole design or on a picked part. The next agent turn receives it. 4. **Manage revisions.** Accept, reject and restore a revision. 5. **Inspect.** Use the section, exploded and collision views, and play a rollout in the viewer. 6. **Export.** Export STEP and STL, and download a concept sheet. - Write endpoints are safe by default: - the server binds 127.0.0.1; - writes need a per-launch token or a same-origin check; - remote viewing is documented as `tailscale serve` in front of it. [rec: winter-stone-5109]

Declared target: `gap-d2-from-browser-alone-person`. The human owns the charter checkbox; roles report results and do not tick it. Reconcile judgement: earlier runs have criteria with the same letters, so every orun2 gap title carries the run. Flip to working only when the criterion has measured evidence; it stays open until then [rec: winter-stone-5109].

## Negative knowledge

None yet.

## Provenance

- winter-stone-5109 — orun2 operator-declared charter gap
