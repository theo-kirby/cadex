---
node_id: e2e3f736-0605-59c1-bf2d-719031a59d41
slug: frosty-cabin-1461
title: 'H3: a passed evaluation is filmed taking the task''s shoves (ADR-571)'
created_at: '2026-10-06T20:04:25+00:00'
parents:
- peaceful-nest-6589
summary: ''
---
## What

H3: a passed evaluation is filmed taking shoves (ADR-571). After the heroes, `cadex evaluate` (also `--film-only`, and now the agent's `evaluate` tool) runs one more episode through the evaluation child: the spec's first seed under the spec's conditions, with the **task's** trained shoves in place of the spec's, each non-sustained entry cut into three non-overlapping slices of its start window (`evaluate_runner.shove_task`), played and measured by the engine's own `evaluate_success`. `shoves.film_shoves` draws `shove.webm` with the existing `film._video`/`video._studio_frames` pipeline and an overlay (`shove_marks`): an arrow in `--warn` at the pushed body in the push's direction with its force, held 0.6 s from landing; top-left lines per landed push with `recovered in <s>` once settled; the ending on the last frame. The report's `shove` block (`cadex-shove-film-v1`) carries the pushes, the outcome and a caption, all read from the episode. `/api/project` rows carry `shove` {state, video, caption}; the allowlist serves the video; the 2D viewport lists `· shoves` after the heroes, with the caption under the video (`#sheet-caption`). Also fixed: the MCP `evaluate` bridge never called ADR-570's `add_heroes`; it now calls both.

## Why

The critic named H3 next, with the scratch copy's passing policy, the CadexDynamics disturbance model, H1 font, film.py/video.py, 2D viewport, and magnitudes/outcome from the rollout. Done as asked. One design choice beyond the letter: the task declares one shove per 10 s episode, so the film tiles each trained shove into three pushes inside its own window, never raising magnitudes beyond the trained band (reason in ADR-571). The bridge fix was found while wiring H3: B2 says the agent need not ask for heroes, and the agent's path did not make them.

## Method

- `cli/cadex_cli/evaluate_runner.py`: `shove_task`, `SHOVES_PER_ENTRY`, `SHOVE_TRACE_NAME`; `plan["shove"]`.
- `cli/cadex_cli/evaluate.py`: `_run_child` split out of `run_evaluation`; `add_shove`, `shove_files`; agent view and prose line.
- `cli/cadex_cli/shoves.py` (new; `film.py` is pinned to name no behaviour): `shove_pushes`, `shove_outcome`, `shove_caption`, `shove_marks`, `film_shoves`. `film.py`: `_video(name=, draw=)`; `.gitignore` names `*.webm`.
- `__main__.py`, `bridge.py`, `review_server.py` (`_shove`), `review.js`, `review.css`.
- Docs: `docs/CLI.md` (new section, envelope, files, page), `docs/DASHBOARD.md`, `docs/ARCHITECTURE.md`, ADR-571. Still: `docs/probes/orun4/h3-shove.png` (274,513 B).
- Tests: `test_evaluate.py` (slices, pushes/outcome/caption incl. a fall and an unread recovery, three skips, live pass with three pushes inside their slices and the trace's draws equal to the report's, `--no-video` skip, fail skip), `test_loop.py` (agent tool reports both skipped on a fail), `test_review_evaluation.py` (row, allowlist, Chromium: captioned video after the heroes).
- Live: `./cadex evaluate --project ~/cadex-projects/orun4-biped-sts --film-only` twice (deterministic).

## Result

True now: a passed evaluation writes `shove.webm` + `shove` block beside `evaluation.json`, in CLI and MCP paths; fail / `--no-video` / no trained shove are `skipped` with the reason. Measured on `orun4-biped-sts` (policy `235b65eba72d`, 10/10 unpushed): the shove episode took 0.5 s, the 64-frame video ~100 s; pushes 0.33 N at 3.12 s, 0.90 N at 5.75 s (third due at 6.95 s never landed); **the walker tipped at 6.30 s**, failing W1/W2/W4 under the pushes. The film shows the fall; the caption reads `fell: tipped at 6.30 s`. That is a finding about the reference policy (passes its walk spec, does not hold three pushes from its own training band), not a film defect. Same outcome on both runs.

Gates (final tree, GPU hidden): `pixi run test-engine` 2611 passed, 58 skipped (344 s); CLI thirds 400 passed (166 s), 360 passed 1 skipped (432 s), 443 passed (128 s). Two failures on the way, both fixed in this unit: `test_film.py` pins that `film.py` names no behaviour (so the shove code moved to `shoves.py`, and the ignore pattern became `*.webm`), and `test_engine_purity_guardrails` caught the dashboard closure (`evaluate.py`) reaching `evaluate_runner` → `CadexDynamics` (so the CLI no longer imports the runner; the trace name travels in the plan and the child's `no_shove_to_film` refusal maps to `skipped`). `test_review_design` rejected a dynamic `#sheet-caption` hook in DASHBOARD.md's hierarchy table; reworded.

Concerns for next iteration: the CLI suite gains one engine episode + small video in two live evaluate tests (~+30 s on test_evaluate.py). ADR-570's claim that the agent's tool drew heroes was false until this commit. No new dependency. Reconcile is due (third unreconciled record of the tail).

Dispatch closed: 1 unit — H3 shove video on a passed evaluation (ADR-571), plus the agent-path heroes fix

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: a0fae3faf76c2f9515ff2e318cf1885d390e3be2

## State Impact

- target: copper-forest-7830 — H3 has its evidence (ADR-571, a0fae3fa): a pass plays one more episode under the task's trained shoves (three slices per shove), filmed with each push marked in the H1 font through film._video; pushes, recovery and ending written from the episode; shown in the 2D viewport with a caption; on orun4-biped-sts the passing walker tipped at 6.30 s after a 0.90 N push and the film shows it
- target: dry-vale-5761 — the agent's MCP evaluate tool now draws the two heroes too (ADR-571 fix); ADR-570 had said it did, but the bridge never called add_heroes
