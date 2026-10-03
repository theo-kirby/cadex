---
node_id: e7b24b83-30f9-5c82-8179-a7eb57b7492a
slug: plain-horizon-5009
title: 'orun1 D1 held-out: frozen judge v2 meets the bar (97.3% gap pairs, Love>No, tau-b 0.436)'
created_at: '2026-10-03T01:29:51+00:00'
parents:
- brisk-tree-8128
summary: ''
---
## What

Frozen judge v2 (ADR-478) measured once on the orun1 held-out set (26 designs, 325 pairs). It meets every part of D1's bar: 97.3% gap-pair agreement (36 of 37), every Love above every No (2 of 2), and Kendall's τ-b 0.436 over 325 pairs. On the same pairs, ot10's frozen judge scored 13.5%, failed Love over No (0 of 2) and had τ-b −0.079. Commit `d9136171`.

## Why

D1 is the highest-ranked open orun1 criterion (`idle-ledge-8635`). The critic named this exact unit: draw the held-out heroes, run v2 once with the README command, commit the results under `judge/v2-heldout` and publish the three metrics beside the baseline. I did what was asked, with no deviation.

## Method

- An earlier session's `draw_set.py --split heldout --jobs 2` was still running at the start (16 of 26 drawn). I let it finish rather than start a second one. All 26 receipts show `render_ok` and look revision = accepted revision. Projects: `orun1-ho-<id>`. Renders stay outside the repo; their hashes are in the summary.
- `pairwise.py --version v2 --split heldout --inputs ~/cadex-projects/orun1-judge/heldout --out docs/probes/orun1/judge/v2-heldout --jobs 8`. The frozen-hash guard passed. 325 of 325 pairs were judged on the first pass, with no harness failure and no resume. Model claude-opus-5-5, effort high. A picked 50.5%. Cost $11.88.
- The README got a "D1 held-out result" section with the comparison table and scores by verdict. ADR-478 got a held-out-result line. The runner's tests pass (14). The committed files contain no machine paths.

## Result

- **D1 now has its measured evidence:** frozen v2 meets the held-out bar. Its scores by verdict: Love 1.00 and 0.80; Like mean 0.58; Meh mean 0.39; No 0.12. `quadruped-e-hard-surface` (Love) won all 25 of its comparisons.
- **The one reversed gap pair** is `biped-c-exposed-mechanism` (Love) against `arm3-h-free` (Meh). The aggregation reversed it, not the call: on that pair's own call the judge picked the Love. The Meh arm scored 0.88 against the Love's 0.80. The dev bias towards clean arms repeats, so D4's arm comparisons deserve a second look.
- **Caveats:** the held-out extremes are small (2 Loves, 1 No). The middle (Like against Meh) is ordered less well than the extremes.
- The held-out set has now been used for its one purpose. Nothing may be tuned on it. v2 is the judge D4 is scored with. The owner ticks D1; roles do not.
- **Next:** D2, rewriting the design language and the overlay with evidence for each rule. That includes the ADR that retires or rewrites the ot10 rubric.
- The tail is two unreconciled records (`brisk-tree-8128` and this one).

Dispatch closed: 1 unit — frozen judge v2 measured once on held-out: 97.3% (36/37), Love>No holds, τ-b 0.436/325 pairs; ot10 baseline 13.5%; D1 bar met

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun1
- commit: d9136171374a9f72d6761be95069a27daec8da58

## State Impact

- target: idle-ledge-8635 — frozen judge v2 measured once on the 26 held-out designs: 97.3% gap-pair agreement (36/37), Love>No holds (2/2), tau-b 0.436 over 325 pairs, beside ot10 baseline 13.5% / fails / -0.079; D1's bar is met with evidence, awaiting the owner's tick; v2 is D4's judge
