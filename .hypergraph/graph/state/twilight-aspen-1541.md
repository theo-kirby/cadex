---
node_id: af9ad815-4170-5455-9209-184716a81387
slug: twilight-aspen-1541
title: D2. From a browser alone, a person can watch and steer a design (orun2)
created_at: '2026-10-03T10:54:46+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Open charter criterion for run orun2: **D2. From a browser alone, a person can watch and steer a design.** - Each of the following is proven by a test driven through the existing headless Chromium path (`cli/cadex_cli/browser.py`) against a real engine: 1. **Start a turn.** Start a design turn from a prompt, optionally with an attached image. Watch it live as the transcript streams and the renders and model update as revisions are accepted. 2. **Move a slider.** Move a parameter slider and see the rebuilt model. Report p50 and p95 latency on a warm project beside the raw-NDJSON bar (`cadexd_latency_integration.py`). 3. **Leave a comment.** Comment on the whole design or on a picked part. The next agent turn receives it. 4. **Manage revisions.** Accept, reject and restore a revision. 5. **Inspect.** Use the section, exploded and collision views, and play a rollout in the viewer. 6. **Export.** Export STEP and STL, and download a concept sheet. - Write endpoints are safe by default: - the server binds 127.0.0.1; - writes need a per-launch token or a same-origin check; - remote viewing is documented as `tailscale serve` in front of it. [rec: winter-stone-5109]

**Write path and safety.** Every dashboard write runs the CLI as a child process (one write path, A3), behind a per-launch token and an Origin check, on 127.0.0.1 [rec: morning-peak-8268]. Remote viewing is `tailscale serve` in front of the loopback bind, `docs/DASHBOARD.md` §22, pinned by `test_remote_viewing_is_tailscale_serve_in_front_of_loopback` [rec: sweet-mist-9111].

| Item | State | Evidence |
|---|---|---|
| 1. Start a turn | evidenced | POST `api/turn` runs `cadex -p`; GET `api/turn` streams its stderr; Chromium test shows the live transcript then the accepted revision drawn (ADR-504) [rec: placid-bell-2440]. Image attach: `cadex -p --image` (magic-byte and size check, stream-json image blocks, at most 4); the page's Attach image passes files via a scratch dir outside the project, removed after the turn; Chromium test against a real engine shows `claude` receives the exact bytes (SHA-256) (ADR-507) [rec: sweet-mist-9111] |
| 2. Slider | evidenced | POST `api/params` runs `cadex params`; release-to-drawn p50 582 ms / p95 636 ms (n=5) beside raw `set_params` 0.381 s (0.482 s with display; bar 0.65 s) [rec: morning-peak-8268] |
| 3. Comment | evidenced | `cadex comment` writes `comments.jsonl`; the next `cadex -p` receives pending comments ahead of its prompt; POST `api/comment`; Chromium test picks parts by click and a page-started turn receives both comments (ADR-505) [rec: noble-glade-0483] |
| 4. Revisions | evidenced | `cadex revision accept/reject/restore` behind POST `api/revision`; Chromium test accepts, rejects (exact revision back), restores (same geometry), and a page turn receives the verdicts (ADR-506) [rec: stormy-grove-7025] |
| 5. Inspect | **partial** — collision evidenced; section, exploded, rollout playback open | `core.inspect scope=contacts` (t=0 MJCF contacts grouped by pair; pinned in the tool surface) and `#collision-contacts` on the page; Chromium test against a real engine: page and agent report the same pairs, and the page slider clears a 2 mm interpenetration (ADR-508) [rec: calm-falcon-6751] |
| 6. Export | evidenced | POST `api/export` runs `cadex export` into the ignored `review/export/<revision>/` behind the token; Chromium test downloads a valid STEP, a 12-facet 30×20×6 mm STL and the concept-sheet PNG (`test_dashboard_export.py`, ADR-509) [rec: polished-lodge-7956] |

**Remaining:** item 5's section view (interactive cut), exploded view (the engine's `exploded_view` moves) and rollout playback (frames through `setPoses`) [rec: calm-falcon-6751] [rec: polished-lodge-7956].

Declared target: `gap-d2-from-browser-alone-person`. The human owns the charter checkbox; roles report results and do not tick it. Reconcile judgement: stays `working` — five of six items carry real-engine Chromium evidence; item 5 has three of four views open [rec: polished-lodge-7956].

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
