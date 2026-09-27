---
node_id: 9eadc90e-e6a8-5d70-9e21-2c3dd487812d
slug: true-tower-9405
title: A1. Cadex has a written design language and a frozen way to judge it
created_at: '2026-09-27T15:18:34+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run ot10: **A1. Cadex has a written design language and a frozen way to judge it.** It covers the language doc, a rubric of 5–8 traits scored 0–3, the frozen A3 proxies and A5 bar, a blind judge procedure, and hex3 scored as the baseline [rec: damp-dusk-8045].

Evidence reported complete, pending the owner's tick [rec: terse-falcon-8320]:
- `docs/DESIGN-LANGUAGE.md` is the language: shell over skeleton, `shell`/`mechanism`/`accent` roles with default palette bone `#E9E6DF`, graphite `#2F3237`, signal orange `#F26A1B`, at most three materials, joints as features, face, taper, printability, presentation. It cites references by filename only, and a test enforces this (ADR-411, commit `6c9a1542`). [rec: terse-falcon-8320]
- `docs/probes/ot10/README.md` + `contract.json` freeze seven traits T1–T7 (max 21; rubric sha256 `1c81caa2…`), proxies P1 `hardware_silhouette_share` ≤ 0.20, P2 `sharp_outside_edge_share` ≤ 0.25, P3 `material_count` ∈ {2, 3}, and the A5 bar: median-of-3 total ≥ 14, no trait at 0, above hex3, proxies in their bars. [rec: terse-falcon-8320]
- Judge: `runner/judge.py`, three isolated `claude -p` calls on `claude-opus-5-5` that see only the rubric, the references and the candidate renders; median taken. `cli/tests/test_ot10_contract.py` pins it (8 tests). [rec: terse-falcon-8320]
- **hex3 baseline: 2/21** (T2 1, T7 1, rest 0; calls 3/2/2, ~$0.11 each), raw replies in `docs/probes/ot10/hex3-baseline-score.json`. [rec: terse-falcon-8320]

Judgement (maintainer): status is `working` because every A1 bullet has measured evidence; the human still owns the checkbox. The judge's fixed output-format paragraph and the median-of-3 are the actor's stated assumptions [rec: terse-falcon-8320].

## Negative knowledge

None yet.

## Provenance

- damp-dusk-8045 — ot10 operator-declared charter gap
- terse-falcon-8320 — language, frozen rubric/proxies/A5 bar/judge, hex3 baseline 2/21
