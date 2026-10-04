---
node_id: af9ad815-4170-5455-9209-184716a81387
slug: twilight-aspen-1541
title: D2. From a browser alone, a person can watch and steer a design (orun2)
created_at: '2026-10-03T10:54:46+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: superseded

## Current

Open charter criterion for run orun2: **D2. From a browser alone, a person can watch and steer a design.** - Each of the following is proven by a test driven through the existing headless Chromium path (`cli/cadex_cli/browser.py`) against a real engine: 1. **Start a turn.** Start a design turn from a prompt, optionally with an attached image. Watch it live as the transcript streams and the renders and model update as revisions are accepted. 2. **Move a slider.** Move a parameter slider and see the rebuilt model. Report p50 and p95 latency on a warm project beside the raw-NDJSON bar (`cadexd_latency_integration.py`). 3. **Leave a comment.** Comment on the whole design or on a picked part. The next agent turn receives it. 4. **Manage revisions.** Accept, reject and restore a revision. 5. **Inspect.** Use the section, exploded and collision views, and play a rollout in the viewer. 6. **Export.** Export STEP and STL, and download a concept sheet. - Write endpoints are safe by default: - the server binds 127.0.0.1; - writes need a per-launch token or a same-origin check; - remote viewing is documented as `tailscale serve` in front of it. [rec: winter-stone-5109]

**Superseded: the dashboard is read-only (ADR-537).** It has no POST routes, no write token, no chat, sliders or verdict buttons; any non-GET/HEAD request gets 501. Steering moved to the person's own agent, which drives the project through `cadex mcp --project DIR` (ADR-538) [rec: still-ivy-2146]. Viewing is on `sweet-bloom-8352`; the agent binding is on `chilly-union-8972`.

**How it got there, 2026-10-04** [rec: glad-wood-4169] [rec: still-ivy-2146]:
- Before: all six items carried a real-engine Chromium test: turn with transcript and image attach (ADR-504, 507, 526) [rec: placid-bell-2440] [rec: sweet-mist-9111] [rec: lively-beacon-5538]; slider p50 582 ms / p95 636 ms beside raw `set_params` 0.381 s [rec: morning-peak-8268] [rec: clever-sky-3211]; comments (ADR-505) [rec: noble-glade-0483]; revisions (ADR-506) [rec: stormy-grove-7025]; collision, section, exploded and rollout playback (ADR-508, 510, 511) [rec: calm-falcon-6751] [rec: narrow-crest-4950] [rec: staid-wave-3739]; STEP/STL/sheet export (ADR-509) [rec: polished-lodge-7956]. Writes ran the CLI as a child behind a per-launch token and Origin check on 127.0.0.1 [rec: morning-peak-8268]; remote viewing is `tailscale serve` in front of the loopback bind [rec: sweet-mist-9111].
- ADR-533 cut the page to model, turn, sliders and revisions; the inspect, parts, dimensions, export, comment and render panels left the page while their API and CLI equivalents stayed [rec: glad-wood-4169].
- ADR-534 drafted the page as an app on branch `app-shell`: tiled resizable areas holding a 3D viewport (with rollout playback), a 2D viewport, Settings and Chat; light/dark theme; shaded or hairline render [rec: cool-road-8381].
- ADR-535 made remote use practical: first load 9.1 s → 3.9 s and reopen 8.2 s → 0.8 s at 30 Mbit (memoized manifest, content-ETagged STL, gzip), loads abort, retry and never freeze the page. Still slow: a parameter rebuild is 80–150 s, mostly the post-build fit checks (ADR-346) and the assembly pass [rec: careful-glacier-8772].
- ADR-537 then removed the turn, sliders and verdict buttons with every write route [rec: still-ivy-2146].

Declared target: `gap-d2-from-browser-alone-person`. The owner's direction retired the criterion rather than ticking it [rec: still-ivy-2146].

## Negative knowledge

None yet.

## Provenance

- winter-stone-5109 — orun2 operator-declared charter gap
- morning-peak-8268 — item 2 slider through cadex params behind a per-launch token; latency measured
- placid-bell-2440 — item 1 browser turn through cadex -p with streamed transcript (ADR-504)
- noble-glade-0483 — item 3 comments on design or picked part reach the next turn (ADR-505)
- stormy-grove-7025 — item 4 accept/reject/restore through cadex revision (ADR-506)
- sweet-mist-9111 — item 1 image attach through cadex -p --image (ADR-507); tailscale serve note pinned (backfilled record)
- calm-falcon-6751 — item 5 collision view: page and agent report t=0 contacts (ADR-508)
- polished-lodge-7956 — item 6 STEP/STL export and concept sheet download (ADR-509)
- narrow-crest-4950 — item 5 section and exploded views browser-proved (ADR-510)
- staid-wave-3739 — item 5 rollout playback through setPoses (ADR-511); item 5 complete
- lively-beacon-5538 — item 1 covers terminal-started turns: stored transcript and looks on the page (ADR-526)
- clever-sky-3211 — item 2 raw-NDJSON bar fully within bar after the preview skips fit (ADR-527)
- glad-wood-4169 — page cut to model, turn, sliders, revisions (ADR-533)
- cool-road-8381 — app-shell draft: areas, four editors, themes, hairline render (ADR-534)
- careful-glacier-8772 — cached/ETagged/gzipped model delivery, resilient loads; rebuild still 80-150 s (ADR-535)
- still-ivy-2146 — superseded: dashboard read-only (ADR-537); steering via cadex mcp (ADR-538)
