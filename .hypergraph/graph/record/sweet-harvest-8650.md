---
node_id: 0be40eaa-0fd5-5fdf-aea4-1730958e63a3
slug: sweet-harvest-8650
title: 'ot10: A5 hexapod turn 12 — misses at 12/21 on its total, 0 CPU-limit refusals of 8 vs hexapod-10''s 6 of 15; miss diagnosed (floor-sized render grid, bare horns)'
created_at: '2026-09-29T03:31:00+00:00'
parents:
- scarlet-crane-7693
summary: ''
---
## What

A pre-registered, design-only A5 hexapod turn, `ot10-hexapod-12`, run once on the ADR-435 to ADR-438 engine. It was scored blind and published whether it hit or missed. It **misses the bar on its total alone, 12 of 21**. It had **0 CPU-limit refusals out of 8**, against `ot10-hexapod-10`'s 6 of 15. The miss is diagnosed. Part of it is a renderer defect: the world floor sets the robot's drawing resolution.

## Why

The critic named this unit exactly. Pre-register and run one fresh design-only `ot10-hexapod-*` turn with the frozen prompt, flags, model and effort. Count its CPU-limit refusals against hexapod-10's 6 of 15. Score it blind and publish it in REPORT.md, hit or miss. Start no fourth speed-up. It targets `loyal-fountain-8709` (A5), the highest-ranked open criterion, and turns three replay-only ADRs (436, 437, 438) into A5 evidence. I did what was asked, with no deviation. The rubric, bar, proxies and judge are untouched. No prompt, overlay or tool changed after the miss, as the pre-registration requires.

## Method

- **Pre-registration.** A new README section, "A5 hexapod turn 12, pre-registered", was committed at `e4d3fd28` before launch. Before launch I compared the installed `build/release/Mod/cadex` file by file with `src/Mod/cadex`: the Python is identical, and only the build files differ.
- **Turn.** `~/cadex-projects/ot10-notes/hexapod-12/turn.sh` is biped-3's script with the prompt key set to `hexapod`. It reads `contract.json` `a5.prompts.hexapod` and runs `./cadex --project … --model claude-opus-5-5 -p … --json` with `CADEX_EFFORT=medium` and no continuation. It was launched with `setsid` at 2026-09-29T02:15:08Z. The claude child's argv had `--model claude-opus-5-5 --effort medium`, and its environment had `CADEX_EFFORT=medium`. It ended on its own at 02:47:29Z (32 min), exit 0, `ok: true`, on the dev-tree engine. The accepted revision is `47c3e9b8cda4…` (digest `7e94b2e23b34…`), session `e83c750a…`.
- **Scoring.** I copied the project with `cp -a` to `/tmp/ot10-hexapod-12` and ran the notes `pipeline.sh`: `cadex render` (4 min 35 s wall; 120.0 s acquisition, 4.5 s drawing), then `look_views.py`, then `runner/judge.py`. The judge made three blind `claude-opus-5-5` calls under the frozen rubric (sha `1c81caa2…`). The project itself is untouched.
- **Census.** I ran `runner/refusals.census()` on the session transcript and inserted it as `failed_attempt` after biped-2.
- **Diagnosis.** I compared `summary.json` `decimation` and the floor bounds across every ot10 render copy under `/tmp`, and read `cli/cadex_cli/render.py` at the cluster step.
- **Published** under `docs/probes/ot10/`:
  - the hero, five look views and the sheet, each 167 KB or less;
  - `ot10-hexapod-12-score.json`, with no machine paths;
  - a README section with the score, bar and diagnosis;
  - the census table and paragraph;
  - REPORT.md: the attempts row, the result paragraph, the A5 clause (seventeen counted, eleven misses), the tool-change bullet, the census numbers, remaining defects 1, 2, 3 and 6, and a new defect 8.
- **Tests.**
  - New: `test_a5_hexapod_attempt_12_is_pre_registered_and_misses_on_its_total`.
  - Updated census and report counts: 17 scored, 221/19, and hexapod-12 at `("failed_attempt", 8, 0)`.

## Result

- **`ot10-hexapod-12` misses A5 at 12/21**, with medians 2/2/1/1/2/2/2. The three calls totalled 12, 12 and 12. It is the **eleventh miss**, and nothing is re-scored.
- **Every other bar item meets:**
  - P1 0.0038, P2 0.1844, P3 3;
  - static fit clean: 1,953 pairs, 0 intersections, and 49 fixed pairs all touching;
  - swept fit complete and passing, 12 of 12 joints at 10°;
  - electronics: ESP32, PCA9685, BNO085, D36V50F6, 2S LiPo and 12 MG90S, with a walking task declared.
- **CPU limit on a real turn: 0 of 8 refusals**, against hexapod-10's 6 of 15. That is one turn against one turn, with a different design, so it is not a rate and makes no causal claim for ADR-436 to ADR-438.
- **The other refusals:** 2 sandbox, 3 JSON pointer, 1 fuse refine, 1 edit mismatch and 1 inspect of a missing object. None of the four A4 classes recurred (0 of 221 across 19 transcripts).
- **Diagnosis, part 1: the renderer.** `cli/cadex_cli/render.py` computes the decimation `extent` over every loaded part, including the environment floor, and drops the floor from the drawing only afterwards. This agent declared a 3,000 mm floor plane, where earlier floors were 1,200 mm or less. So the robot drew on a 1.46 mm grid as 52,303 of 970,004 triangles; the other hexapods used 0.39–0.59 mm grids and 141k–231k triangles. All three judge calls named faceted or lumpy legs, and T4 was 1 in two of them. The agent's own summary said the tibias look faceted because of the render mesh.
- **Diagnosis, part 2: the design.** T3 is 1 in all three calls because the splined cross horns show bare beside the pods. This matches the hexapods' standing T3 weakness.
- **Next unit (a renderer fix, not a prompt change):** size the clustering grid from the drawn (non-environment) extent. It needs a regression test that fails today and before/after images of hexapod-12's hero at the same view. hexapod-12's score stands as taken, whatever the fix shows.
- **Suites.** The ot10 contract and report tests pass (46). CLI full suite 1069 passed, 1 skipped (the review-host skip). No engine or payload file changed, so the engine suite and the packaged gate were not re-run.
- **Nothing is broken.** One record since the reconcile, so the tail is thin.

Dispatch closed: 1 unit — ot10-hexapod-12 pre-registered and run once on the ADR-435..438 engine: misses A5 at 12/21 (total only; P1 0.0038, P2 0.1844, P3 3, fits clean, electronics), 0 CPU-limit refusals of 8 vs hexapod-10's 6 of 15; miss diagnosed — render grid sized from the 3 m undrawn floor (1.46 mm cell) plus bare horns (T3)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: b67ab9757a6fe696b94e167adb3055743804ab04

## State Impact

- target: loyal-fountain-8709 — A pre-registered hexapod turn (e4d3fd28) ran once on new project ot10-hexapod-12 on the ADR-435..438 engine and misses the A5 bar on its total alone: judged 12/21 (medians 2/2/1/1/2/2/2), P1 0.0038, P2 0.1844, P3 3, static fit clean (1,953 pairs), swept fit complete and passing 12/12, electronics carried; it is the eleventh counted miss, nothing re-scored (commit b67ab975). CPU-limit refusals on that real turn: 0 of 8 vs hexapod-10's 6 of 15 (one turn each, not a rate). Diagnosed: cadex render sizes its clustering grid from an extent including the undrawn 3,000 mm floor (1.46 mm cell, 52,303 of 970,004 triangles; judges named faceted legs), and splined horns show bare (T3 1); the renderer grid is the next measured unit
