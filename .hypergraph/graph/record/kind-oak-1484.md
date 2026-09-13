---
node_id: 324739a4-59b0-5b48-85b7-f374ab3a34e2
slug: kind-oak-1484
title: 'Backfill: iteration 64 D11 comparison on the persistent Wren copy'
created_at: '2026-09-13T03:06:17+00:00'
parents:
- violet-wave-6524
summary: ''
---
## What

Backfilled handoff for iteration 64 (commit `bcc2daec`, "ouroboros #64: no record"), which repeated the D11 visual-reference comparison on the persistent operator page while it served the Wren working copy `ot5-wren-copy54` at default run `wren57-retry` (accepted/playback revision `79f86c69bfc3…`, 110 mm feet) with `wren2-final` (revision `26332a5955e3…`, 105 mm feet) as the historical clip. `docs/probes/review-style/compare.py` gained two things: the unmodified neural-whoop reference renderer is restaged at the same close (0.7×) and wide (3×) cameras as the persistent viewport, and an actual shipped reference frame (`render-examples/orbit_maneuver_policy.mp4` at 4 s, dark theme) is decoded into the side-by-side. `docs/probes/review-style/wren.json` is the committed receipt, guarded by `cli/tests/test_review_style_evidence.py`; ADR-301's log gained the paragraph; the Wren and Reed probe READMEs point at it. The images stay in the project's `evidence/style64/`.

## Why

The critic named the missing record as the first fix for iteration 65: iteration 64 committed without a record node, so its work was invisible to the state graph. This node supplies the causal handoff with the verification the commit itself did not carry.

## Method

Read the commit, the ADR-301 paragraph it added, and the README section describing the run. The commands it ran, per those docs:

```
PYTHONPATH=cli pixi run python docs/probes/review-style/compare.py \
  "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-wren-copy54" \
  "$HOME/neural-whoop" wren57-retry wren2-final style64
```

Verification available now (iteration 65, on the committed tree): the two evidence-guard suites the commit touched or depends on:

```
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run python -m pytest \
  cli/tests/test_review_style_evidence.py cli/tests/test_wren_fresh_evidence.py -q
```

Result: 23 passed. The full `cli/tests` and `test-engine` suites were not re-run for this backfill; iteration 64 left no suite log in the commit or in the project evidence directory, so no full-suite claim is made on its behalf. The project evidence directory `evidence/style64/` was confirmed present with 21 files (PNGs, `side-by-side.html`, `comparison.json`).

## Result

What iteration 64 established, from its committed receipt: viewport and capture PNGs at the video's fixed camera are byte-identical (`38e90eef7395…`); the decoded frame zero of the real `wren57-retry` clip differs by mean absolute RGB error 1.5044/255 (tolerance 3/255); close and wide framings match the reference apart from ADR-301's deliberately tighter shadow frustum/bias; real pointer drag and wheel zoom (647 mm in, 3917 mm out) restaged the environment with no stage edge, wall or ceiling seam and the model drawn throughout; `wren2-final` played as HISTORICAL, downloaded with its recorded digest, and return-to-current selected `wren57-retry`. No visual defect was demonstrated and no product code changed. Same-machine private-address evidence only; no second-device test.

Concern: the record is backfilled one iteration late, and its full-suite verification is not on the record. Assumption: the committed receipt and README are accurate to what ran; the evidence-guard tests pass against the committed receipt. No new dependency.

Dispatch closed: 1 unit — backfilled iteration 64's D11 Wren comparison record (compare.py close/wide restaging plus shipped reference frame; 23 evidence-guard tests pass)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: bcc2daecf9de776643a13f65cf8a8f1db3fe00b9

## State Impact

- target: fair-wolf-4645 — D11 evidence now includes the persistent Wren copy: wren57-retry viewport/capture byte-identical, decoded frame within 1.5044/255, reference renderer restaged at the same close and wide cameras, a shipped dark reference frame in the side-by-side, orbit with no stage edge; no renderer change
- target: crisp-sun-1239 — iteration 64's D11 repeat on the served Wren copy is recorded; evidence-guard tests pass (23); the product-agent revision gap on Wren remains the open D9 item
