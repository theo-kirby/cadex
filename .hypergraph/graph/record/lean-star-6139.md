---
node_id: 7ac910d3-2473-5f97-9ccc-2ddd40788b95
slug: lean-star-6139
title: 'orun2 D3: run pages serve and render docs/probes/<run>/ read-only — orun1''s README and heroes from the repo (ADR-515)'
created_at: '2026-10-03T22:53:31+00:00'
parents:
- polished-reef-4161
summary: ''
---
## What

orun2 D3: a run's probe material on its page. `/r/<run>/` gains a **Probes** card that serves `docs/probes/<run>/` from the checkout read-only under `/r/<run>/probes/<path>`. It draws the directory's README with a new DOM-only markdown subset (`review_static/markdown.js`), shows its images as a gallery, and links every file. `api/run` carries a `probes` listing. ADR-515; `docs/DASHBOARD.md` §27 updated.

## Why

This is the critic's named next D3 unit, and it is the half of D3 that replaces `~/orun1-review/build.py`. orun1's README and its 60 owner-rated heroes now render in the dashboard from the repo alone. Target: `swift-nest-0229` (D3).

Deviation from the critic's message: it allowed "docs/probes/<run>/ or the paths the run's records link to". This unit serves only `docs/probes/<run>/`. Record-linked artifacts outside that directory are not reachable yet, and ADR-515 says so. Probes are read from the checkout's working tree, not the run branch, because probe material is committed and merged and a merged run's branch may be gone.

## Method

- In `cli/cadex_cli/review_server.py`, `OuroborosRuns` gains `_probe_base`, `probe_file` and `probes`. The guards are:
  - the probe directory must resolve to itself, so a symlinked dir is refused;
  - every segment must match `PROBE_SEGMENT` (no dot-files, no `..`, no encoded `/`);
  - only suffixes in `PROBE_KINDS` are served, never HTML;
  - no symlink is allowed anywhere on the path;
  - every response carries `Content-Security-Policy: sandbox` and `nosniff`, sent through a new `headers=` kwarg on `_send_file`.
- The listing caps at 2000 files and prunes `__pycache__`.
- Front end: `markdown.js` (builds DOM through textContent only and drops HTML comments), a probes card in `run.html`, `renderProbes` in `run.js` (redraws only when the listing changes), and CSS.
- Tests in `cli/tests/test_app.py`:
  - a fixture checkout with a README, a nested PNG, a JSON file, and hostile entries (dot-file, HTML, `.pyc`, symlinked file and dir out of the checkout, a symlinked probe dir). It asserts the exact listing, byte-exact serving with headers, and 404s for 13 bad paths;
  - a refusal outside a checkout;
  - a headless-Chromium test that copies the repo's committed `docs/probes/orun1/` into a checkout and opens `/r/orun1/`. It checks the README's headings, the ratings table (header, 9 rows, bold `type mean`), that no comment leaks, and that the `balancer-c-exposed-mechanism` hero is loaded (naturalWidth > 0) via `/r/orun1/probes/`, with all 60 PNGs in the gallery.
- A manual screenshot of the live `.ouroboros/runs` orun1 page showed the README rendering on the dark floor.

## Result

What is true now:
- `/r/orun1/` shows orun1's README and image gallery from the repo. `test_app.py` passes 19 of 19, including the 3 new tests.
- `pixi run python -m pytest cli/tests` (GPU hidden): 1364 passed, 1 skipped. `pixi run test-engine`: 2593 passed, 56 skipped. No protocol or payload change, so no packaged gate this unit.

Concerns for the next iteration:
- D3 still lacks two things: CLI agent turns listed as runs (the critic's next item), and record-linked artifacts outside `docs/probes/<run>/`.
- Two records (`mellow-otter-0798`, `polished-reef-4161`) are unreconciled before this one. The tail is three, which meets the charter's reconcile threshold.
- No new dependency.

Dispatch closed: 1 unit — run pages serve and render docs/probes/<run>/ read-only (ADR-515), orun1's README and heroes proven in headless Chromium

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 2aca3739c851073873d13f9f944cf335add1fda3

## State Impact

- target: swift-nest-0229 — each run's page now shows its probe material: docs/probes/<run>/ listed in api/run and served read-only at /r/<run>/probes/ (allow-listed suffixes, plain segments, no symlinks, CSP sandbox + nosniff), README drawn by markdown.js and images as a gallery; orun1's committed README and 60 heroes render from the repo alone, proven in headless Chromium (ADR-515, commit 2aca3739). Still open for D3: CLI agent turns as runs, and record-linked artifacts outside docs/probes/<run>/.
