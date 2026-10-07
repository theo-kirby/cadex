---
node_id: 2b5f3d05-83e8-5f63-b60a-0ee1758de98b
slug: copper-forest-7830
title: H3. A passed evaluation produces a shove video
created_at: '2026-10-06T07:42:22+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run orun4: **H3. A passed evaluation produces a shove video.** The passing policy is filmed taking horizontal pushes drawn from the task's disturbance model (`CadexDynamics` disturbances), each marked on screen when it lands; the film shows whether it recovers. It uses the H1 font and the existing film pipeline (`cli/cadex_cli/film.py`, `video.py`) and plays in the 2D viewport beside the evaluation films. Push magnitudes and the recovery outcome are written beside the video from the rollout itself; a fall is filmed as a fall. The human owns the checkbox [rec: light-mist-9160].

**Implemented, evidence complete, pending the critic** (ADR-571, commit a0fae3fa) [rec: frosty-cabin-1461].

- **Episode**: after the heroes, a pass (CLI `evaluate`, `--film-only`, and the MCP tool) runs one more episode in the evaluation child — the spec's first seed and conditions, with the task's trained shoves, each non-sustained entry cut into three non-overlapping slices of its start window (`evaluate_runner.shove_task`), never above the trained band; measured by the engine's `evaluate_success` [rec: frosty-cabin-1461].
- **Film** (`cli/cadex_cli/shoves.py`, via `film._video`): `shove.webm` with an arrow at the pushed body and its force, held 0.6 s, per-push lines with `recovered in <s>`, the ending on the last frame, all in the H1 font. Report block `cadex-shove-film-v1` (pushes, outcome, caption, read from the episode); fail / `--no-video` / no trained shove → `skipped` with a reason. `/api/project` rows carry `shove`; allowlisted; the 2D viewport lists `· shoves` after the heroes with the caption under it. Still: `docs/probes/orun4/h3-shove.png` [rec: frosty-cabin-1461].
- **Measured** on `orun4-biped-sts` (policy `235b65eba72d`, 10/10 unpushed), deterministic over two runs: episode 0.5 s, 64-frame video ~100 s; pushes 0.33 N at 3.12 s and 0.90 N at 5.75 s, the walker tipped at 6.30 s; caption `fell: tipped at 6.30 s`, and the film shows the fall [rec: frosty-cabin-1461].
- **Boundaries kept**: shove code lives in `shoves.py` because `film.py` is pinned to name no behaviour; the CLI does not import `evaluate_runner` (purity guardrail: no `CadexDynamics` in the dashboard closure) — the trace name travels in the plan [rec: frosty-cabin-1461].
- **Gates**: `pixi run test-engine` 2611 passed, 58 skipped; CLI in thirds, GPU hidden, 400 / 360+1 skipped / 443 passed. Cost: ~+30 s on `test_evaluate.py` [rec: frosty-cabin-1461].

## Negative knowledge

- [scope: the scratch copy's reference policy `235b65eba72d` on `orun4-biped-sts` | confidence: high | evidence: frosty-cabin-1461] It passes its walk spec 10/10 unpushed but does not hold pushes from its own training band: it tipped at 6.30 s after a 0.90 N push, deterministically over two runs. A finding about that policy, not a film defect.

## Provenance

- light-mist-9160 — operator-declared orun4 charter gap (gap-h3-passed-evaluation-produces-shove)
- frosty-cabin-1461 — shove video on a passed evaluation, pushes marked, a fall filmed as a fall (ADR-571)
