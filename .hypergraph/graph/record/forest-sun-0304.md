---
node_id: 0febf5dd-da6a-52ef-9f53-dc64286536fa
slug: forest-sun-0304
title: 'orun1 F1 regression: ADR-476''s sorted blend search refused six held-out designs; reverted to kernel order (ADR-477)'
created_at: '2026-10-02T19:57:13+00:00'
parents:
- idle-loom-0473
summary: ''
---
## What

A fix to ADR-476, F1's own fix. Its sorted partial-blend search stopped six held-out sweep designs reopening and changed the fillets on eleven more. ADR-477 puts the partition back in the kernel's order and keeps ADR-476's recipe-level restore. Commit `3d17000e`. The same commit pre-registers the D1 baseline in `docs/probes/orun1/README.md` (ot10's judge, unchanged and measured once, with ties counted as disagreements), counts the split, and adds `docs/probes/orun1/runner/render_set.py`. Nothing has been sent to a judge.

## Why

The critic named the D1 baseline as the unit. Drawing its inputs, the first held-out copy (`orun1-ho-arm3-a-servo-joint`) refused to open: "api.fillet: no edge in the selection could be blended at that radius". A baseline needs every held-out design rendered at the geometry the owner rated, and F1 says an accepted project always reopens, so the regression came first and became this iteration's one unit. **Deviation:** the baseline was not measured. It is pre-registered and its render runner is proven, so it is next.

The critic also asked for a reconcile first. This dispatch forbids reconciling in a work iteration ("no exceptions"), so I did not run one. The tail is 1 node before this record and 2 after it.

## Method

- Wrote `/tmp` open drivers that run `open_project` with restore over raw NDJSON on fresh copies, eight at a time.
- Held-out census (26 designs):
  - engine `44889478` (ADR-476): 20 open, 11 of them by `recipe`, 6 refused;
  - engine `7e55ffed` (before F1): 25 open, 1 refused (`wildcard-b`, a digest mismatch the recipe path now covers).
- Cause: `_blend_order_key` sorts by curve type first. On arm3 that put every B-spline edge, the ones that cannot take 0.6 mm, ahead of every line. The bisecting partition then spent its 48-call cap rejecting 22 of them and blended 0 of 244 edges. `wildcard-h-free` failed downstream, a `fuse` that came back as 4 solids.
- Fix: deleted `_blend_order_key`, `_blend_canonical_order` and the measured-order retry. `cadex_part_worker.py` is now byte-identical to before ADR-476 apart from one comment.
- Replaced ADR-476's sort-pinning test with `test_a_capped_partial_blend_searches_in_the_order_the_design_was_accepted_in`. It uses 244 edges with every 8th a non-blendable `BSplineCurve`, and it fails on ADR-476's source with the arm3 refusal.
- ADR-477 written. ADR-476's sort bullet is marked withdrawn.

## Result

- **All 55 sweep designs and the 3 digestbug copies open, 58 of 58, when opened one at a time.** At eight in parallel (while the engine suite was also running), 55 opened: 48 exact, 3 `geometry`, 4 `recipe` (including `digestbug-balancer-b` and `digestbug-hexapod-h-free`). Of the three that refused:
  - `hexapod-c` and `wildcard-f` hit the 300 s domain timeout;
  - `digestbug-balancer-d` hit the blend probe's **15 s clock**: 10 calls, no edge probed.

  Rerun alone, all three opened, with `digestbug-balancer-d` opening on 4 of 4 fresh copies.
- **Remaining defect for F1:** a partial blend bounded by wall-clock time is still load-dependent, so a reopen can fail under load. ADR-477 does not change the clock. It is a candidate unit if F1 must hold under load. D1 renders should run serially or at low parallelism.
- `render_set.py` on a fresh `orun1-ho-arm3-a-servo-joint` copy drew the hero and the five look views at the accepted revision `2e812505…`, in 5 minutes. The hero matches the image the owner rated.
- Gates:
  - `pixi run test-engine`: 2545 passed, 61 skipped;
  - `cli/tests` with the GPU hidden: 1290 passed, 1 skipped;
  - build-engine and stage-engine, then the packaged `test_cadexd_lifecycle.py`: 24 passed (the payload no longer contains the sort).
- README correction (below the marker; the operator text above it is not edited): the split is **29 dev / 26 held-out**, not 27/28, and there are 37 held-out pairs whose verdicts differ by two levels or more.
- Next: run the pre-registered baseline. Copy each held-out design to `orun1-ho-<id>`, draw its inputs, run `docs/probes/ot10/runner/judge.py` (3 calls each), and compute the three metrics. The metric code and its test still need to be written; the README no longer names files that do not exist.
- Assumption: reverting to kernel order costs ADR-476's process-independence of which edges a capped blend keeps. The recipe path absorbs that, as it already does for `part.offset` drift.

Dispatch closed: 1 unit — reverted ADR-476's sorted blend search (it refused 6/26 held-out designs); 58/58 sweep+digestbug projects reopen; D1 baseline pre-registered, not yet run

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun1
- commit: 3d17000e4fe6334952342134e8b59de37e812011

## State Impact

- target: red-pond-8515 — ADR-476's sorted partial-blend search was itself a regression (held-out reopen 25/26 before it, 20/26 with it); ADR-477 reverts it and keeps the recipe restore; 58/58 sweep+digestbug projects reopen unloaded; open under load still fails on the blend probe's 15 s clock
- target: idle-ledge-8635 — D1 baseline (ot10 judge, held-out, measured once, ties count as disagreement) pre-registered in the orun1 README with its render runner proven; split counted as 29 dev / 26 held-out, 37 pairs differ by 2+ levels; nothing judged yet
