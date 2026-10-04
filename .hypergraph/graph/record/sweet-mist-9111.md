---
node_id: 3f736e7e-a3ac-5a21-b3d2-f6625ce107da
slug: sweet-mist-9111
title: 'orun2 D2: an image attached to a prompt, from the CLI (--image) and the dashboard (ADR-507) — backfilled record'
created_at: '2026-10-03T18:31:25+00:00'
parents:
- stormy-grove-7025
summary: ''
---
## What

orun2 D2 item 1's missing half: a person can attach an image to a design prompt from the dashboard, and the turn receives it (ADR-507). Underneath it is a new CLI flag, `cadex -p PROMPT --image PATH` (repeatable, at most 4). In the same unit, `docs/DASHBOARD.md` gains §22: remote viewing is `tailscale serve` in front of the 127.0.0.1 bind. A test pins that section.

## Why

Backfilled in iteration 23 at the critic's request: iteration 22 committed this unit (commit `50a8a6cf`) without minting its record. The body below is the one iteration 22 drafted, corrected only where its suite evidence was incomplete.


The critic named this unit: D2 item 1 needs "optionally with an attached image", through the same `cadex -p` path, with no second write path (A3), behind the token, and proved by a Chromium test against a real engine. The critic also asked for the `tailscale serve` note pinned by a test. Both were done as asked. The agent runs with `--tools ""`, so it cannot open a file path. The CLI therefore had to learn to carry an image first.

## Method

- **CLI (`cli/cadex_cli/agent.py`, `__main__.py`, `report.py`).**
  - `image_attachment`/`read_image` check an image by its leading bytes (PNG, JPEG, GIF, WebP) and by size (3.75 MB, so base64 stays under the API's 5 MB).
  - A refused, unreadable or fifth image exits 2 before any engine starts.
  - With images, `ClaudeTurn` runs `claude -p --input-format stream-json` and writes one user message on stdin: the text block, then base64 image blocks. Without images the command line is unchanged.
  - Each image gets a `· attached` progress line, which is the transcript.
  - The envelope gains `attachments` (name, type, bytes, sha256; never the bytes).
  - `--image` with anything but `-p` is a parser error.
- **Server (`review_server.py`).**
  - `POST api/turn` takes `images: [{name, data(base64)}]`. Images are checked with the same function the CLI uses.
  - Names are sanitised. Images go to a scratch dir outside the project, passed as `--image=<file>` on the same child, and the dir is removed when the turn ends.
  - A turn body may be up to `TURN_BODY_LIMIT` (≈20 MB). Other routes keep 64 KiB. The token check still runs before the body is read.
  - The snapshot carries `images`, and the reply carries `attachments`.
- **Page.**
  - `#turn-attach` (Attach image / Remove image) and a hidden `#turn-image` file input.
  - `#turn-images` lists the picked files in the accent ink. A started turn clears it.
  - `window.cadexReview.attachImages/attached` are exposed for tests.
- **Before building on it**, one real call: Claude Code 2.1.288 with `--input-format stream-json --tools ""` and a 32×32 blue PNG on stdin. Haiku 4.5 answered "Blue". About $0.03 for two calls.
- **Test fakes.** `fake_claude.py` reads a stream-json stdin and writes each image block's media type and the SHA-256 of its decoded bytes beside SEEN. `MockTurn.run` takes `images`. The two `_run_once` fakes in `test_ot7_runner.py` take the new `images=()` keyword. This follows the private signature. No assertion was weakened.
- **Docs.**
  - `docs/DASHBOARD.md` §19 (Attach image) and the new §22 (remote viewing).
  - `docs/CLI.md` prompt flags.
  - ADR-507.
  - `docs/SHELL-PARITY.md` rows:
    - `agent.py` and `capture.py`: image attach ported.
    - `get_attached_image`: already covered, because the image is in the turn's own message.
    - the Chat editor: ported (ADR-504, ADR-507).

## Result

What is true now:
- **Test files.**
  - `cli/tests/test_prompt_images.py` (5 tests, including one against a real engine).
  - `test_dashboard_writes.py`:
    - `test_a_turn_carries_its_images_as_cli_image_files`;
    - `test_browser_attaches_an_image_to_a_turn_and_the_turn_receives_it`, in headless Chromium against a real engine;
    - `test_remote_viewing_is_tailscale_serve_in_front_of_loopback`.
- **What the browser test shows.** A file is put into `#turn-image` through a DataTransfer. `claude` receives an image block with the same SHA-256. The turn lands a 48 mm plate, which the page redraws. The CLI's `PROGRESS.md` row is written, and the attachment clears.
- **Suites.**
  - `pixi run test-engine`: 2583 passed, 56 skipped.
  - First CLI run with the GPU hidden: 1 failure, in `test_ot7_runner`'s private `_run_once` fakes (fixed as above).
  - **The full CLI re-run after that fix never reported**: iteration 22 ended while it ran in the background and its task was killed, so commit `50a8a6cf` ("ouroboros #22: no record") landed with no full green CLI run on record. The targeted files passed (`test_prompt_images.py` 5 passed; the dashboard-write selections passed). Iteration 23 runs the full CLI suite over a tree that contains this code and reports it in its own record.
  - No protocol, `OP_ARG_SPECS`, payload or tool-surface change, so no packaged gate is needed.

D2 status: items 1 (now with image), 2, 3 and 4 have browser tests. Items 5 (section, exploded and collision views, plus rollout playback in the viewer) and 6 (export STEP/STL, download a concept sheet) remain. The remote-viewing note is done.

Assumptions:
- Attached images are not stored in the project. Only their digest is recorded in the envelope. This is reversible: copy them to `attachments/` (ADR-507, "What would reverse it").
- The doc says a proxy that rewrites `Host` makes writes fail safe as cross-origin. Whether `tailscale serve` preserves `Host` was **not measured**: the actor may not run `tailscale serve`. The owner should confirm it on sb1x.

Next, per the critic: D2 item 6 (export and concept-sheet download), then item 5.

Dispatch closed: 1 unit — dashboard image attach through `cadex -p --image` (ADR-507) with a real-engine Chromium test, plus DASHBOARD.md §22 tailscale-serve remote viewing, pinned

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 50a8a6cfb8044179fc255b404ab10081ac86c4a2

## State Impact

- target: twilight-aspen-1541 — item 1's optional image evidenced: cadex -p --image (magic-byte check, stream-json image blocks) and the dashboard's Attach image through the same cadex -p in a scratch dir removed afterwards; headless-Chromium test against a real engine shows the turn receives the exact bytes; DASHBOARD.md §22 tailscale-serve note pinned; open: items 5-6
