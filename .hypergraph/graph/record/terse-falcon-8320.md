---
node_id: 632e0d8a-5839-5468-ab7e-0b8190a877ec
slug: terse-falcon-8320
title: 'ot10 A1: Cadex design language, frozen rubric and blind judge; hex3 baseline 2/21'
created_at: '2026-09-27T15:52:48+00:00'
parents:
- damp-dusk-8045
summary: ''
---
## What
ot10 A1, short-term rung 1. I wrote Cadex's design language
(`docs/DESIGN-LANGUAGE.md`) and froze the instrument that judges it
(`docs/probes/ot10/README.md`, `contract.json`, `runner/judge.py`,
`cli/tests/test_ot10_contract.py`, ADR-411). I also scored hex3's
accepted design as the baseline. Commit `6c9a1542`.

## Why
The critic named A1 (`true-tower-9405`) as this unit and said to skip
the stale `young-crane-9546` clearance bets. The charter ladder puts the
language and the rubric before any product change, and A5 needs the bar
frozen before its first probe. I did what the critic asked, with no
deviation.

## Method
- I read `reference/README.md` and all ten `reference/images/1-core/`
  images, plus hex3's gap log and render. No reference image was
  copied, committed or embedded. The language cites them by filename
  only, and a test enforces that.
- **Language.** It has sections on form (shell over skeleton, one body
  primitive, radii 10–20%, split lines), three appearance roles
  (`shell`, `mechanism`, `accent`) with a default palette (bone
  `#E9E6DF`, graphite `#2F3237`, signal orange `#F26A1B`, plus
  alternates) and at most three materials, joints as round features,
  and a proposed signature, the Cadex joint cap (a graphite disc with an
  accent ring). Further sections cover the face, proportion and taper,
  printability, presentation (hero angle, lighting, backdrop, shadow,
  concept sheet) and the order of design (concept, skeleton, shell,
  `look`).
- **Rubric.** Seven traits (T1 shell, T2 palette, T3 joints, T4 form, T5
  character, T6 proportion, T7 presentation), each scored 0–3 against
  written anchors, for a maximum of 21. The rubric block's sha256
  `1c81caa2…` is pinned.
- **Proxies**, frozen:
  - P1 `hardware_silhouette_share` ≤ 0.20;
  - P2 `sharp_outside_edge_share` ≤ 0.25 (a sharp edge is a convex
    normal turn above 60°, measured as length share over the non-seam
    edges of printed solids);
  - P3 `material_count` of 2 or 3.
- **A5 bar.** A median-of-3 judged total ≥ 14, no trait at 0, above
  hex3, the proxies within their bars, and the charter's fit gates.
- **Judge.** Three fresh `claude -p` calls on `claude-opus-5-5`, effort
  high, with no fallback. Each runs in an empty temp dir with
  `--setting-sources project`, `--strict-mcp-config`, Read as the only
  tool and `--no-session-persistence`. `--add-dir` covers only the
  reference dir (read in place) and a candidate dir with the renders
  renamed `candidate-N.png`. The system prompt is the pinned
  instructions plus the rubric and nothing else. I first confirmed that
  an isolated call reads a reference image and reports `claude-opus-5-5`.
- **Baseline renders.** I copied hex3 to `/tmp` (the project stays
  read-only) and used a throwaway script (not committed) that calls
  `render.acquire_snapshot` and `render.look` with inventory colouring
  and the floor left out. It produced the five `look` views at 768 px,
  15–33 KB each, committed under `docs/probes/ot10/`. The snapshot
  rebuild takes about 3.5–7 min on this machine.

## Result
- **hex3 baseline: 2 of 21.** The medians are T1 0, T2 1, T3 0, T4 0,
  T5 0, T6 0, T7 1. The three calls gave 3, 2 and 2 and differed only on
  T2 (2, 1, 1). Each call took about 20 s and cost about $0.11. All raw
  replies are in `docs/probes/ot10/hex3-baseline-score.json`.
- `test_ot10_contract.py` passes (8 tests). The full cli suite passed:
  970 passed, 1 skipped. I did not run `pixi run test-engine`, because
  nothing under `src/` changed. The payload gate is not applicable.
- **Assumptions:**
  - The judge's context is the rubric plus a short fixed instruction
    paragraph (the output format), which the charter's "rubric, refs,
    renders, nothing else" allows.
  - Three calls with a median is my choice for variance control.
  - The candidate set for later probes is the A2 hero plus the five
    `look` views. hex3's set is the five `look` views, because it
    predates A2.
- **For the next units:**
  - A3 must implement the proxies exactly as defined and re-measure hex3
    on P1–P3. The README says so, and P3 is 2 today by construction.
  - The language's palette and roles are targets. None of it is product
    behaviour yet.
  - The judge reads references from the gitignored `reference/`, so it
    only runs on this machine.
- The tail is now 1 record, so no reconcile is due.

Dispatch closed: 1 unit — A1 design language, frozen rubric/proxies/bar/blind judge, hex3 baseline scored 2/21 (ADR-411, 6c9a1542)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 6c9a15421854a8960cbd6f3ca116099ee9086aed

## State Impact

- target: true-tower-9405 — docs/DESIGN-LANGUAGE.md and docs/probes/ot10/README.md (contract.json, runner/judge.py, test_ot10_contract.py, ADR-411, commit 6c9a1542) exist: 7-trait 0–3 rubric (sha 1c81caa2), proxies P1≤0.20/P2≤0.25/P3∈{2,3}, A5 bar total≥14 no trait 0 above baseline, blind 3-call median claude-opus-5-5 judge; hex3 baseline scored 2/21 (T2 1, T7 1, rest 0). A1 evidence complete pending owner tick; proxies on hex3 await A3.
