---
node_id: b0f8d9dd-56df-5d86-b74f-352fd8001d1e
slug: brisk-tree-8128
title: 'orun1 D1 judge built on dev: pairwise hero-only, v2 at 90.7% (49/54) twice, frozen before held-out'
created_at: '2026-10-02T23:37:04+00:00'
parents:
- rich-wing-8546
summary: ''
---
## What

Built orun1's D1 judge on the 29 dev designs only, and froze one version before any held-out call (ADR-478, commit `374c1d7f`). The judge is **pairwise**: each call asks which of two robots the owner would rate higher, and a design's score is the fraction of comparisons it wins. It sees only the 1024 px studio hero that `cadex render` draws on the dark floor from an `orun1-dev-<id>` copy at the accepted revision. That is the one picture per design the owner rated from. Each call runs in ot10's isolation. Position is balanced by a hash of each pair.

| dev (54 gap pairs, 406 pairs) | v1 | v2 | v2 mirrored |
|---|---|---|---|
| gap ≥ 2 agreement | 81.5% (44/54) | **90.7% (49/54, 1 tie)** | 90.7% (49/54, 1 tie) |
| Love > No | holds 4/4 | holds 4/4 | holds 4/4 |
| τ-b | 0.261 | 0.307 | 0.298 |

**v2 is frozen** in `docs/probes/orun1/README.md` ("D1 frozen judge: v2") with its prompt verbatim and sha256 `0ebb5965…`, pinned in `pairwise.FROZEN`.

## Why

The critic named this unit: D1 rung 3, the top-priority open criterion (`idle-ledge-8635`). Its steps were: build on dev only; choose the form, with pairwise suggested; measure dev gap-pair agreement and Love>No and publish them; freeze only if dev clears comfortably; leave held-out untouched. All four were done.

v1 cleared dev by only one pair. Its 10 misses fell into two patterns: (a) the loved plain arm `arm5-g-minimal` lost to Meh arms that show more hardware; (b) the committed-character Likes lost to the visor-box Nos because "both have faces". v2 changes only those two points. The mirror replicate checked that v2's margin was not position or call noise before it was frozen.

The critic's pre-unit fix (PLAN.md left uncommitted) was already resolved: `git status` was clean at the start and PLAN.md showed no diff, so there was nothing to commit or check out.

## Method

- `runner/draw_set.py --split dev --jobs 2` copied each `sweep-<id>` to `~/cadex-projects/orun1-dev-<id>` and drew `render_set.py`'s set. All 29 drew with no refusal, taking about 1h45m at two at a time. The renders stay outside the repo; each summary records the accepted revision and the hero's sha256.
- `runner/pairwise.py`: versions v1 and v2, `--mirror`, resumable `pairs.jsonl`, and `summary.json` computed with `metrics.py` unchanged. `metrics.split_verdicts` was added so the dev split can be scored.
- Held-out guard: `--split heldout` is refused for any version not in `FROZEN` with its exact hash, for a mirror, and into a directory that already holds a held-out result.
- `runner/test_pairwise.py` has 14 tests with metrics, all passing. They cover the dev split count (29 designs, 54 gap pairs), stable and balanced order, mirror inversion, parse, scoring, no verdict words in any prompt, the frozen hash, and each refusal path of the held-out guard. Each refusal test checks its message, so a missing-input exit cannot pass for a refusal.
- Cost: three runs of 406 calls each, $43.64 in total, about 4 s a call.

## Result

- **D1 now has a frozen judge version (v2) and a dev result. No held-out measurement by it exists yet.** The next unit is the single held-out measurement:
  1. `draw_set.py --split heldout --out <dir> --jobs 2`. This replaces the `orun1-ho-*` copies the baseline left.
  2. `pairwise.py --version v2 --split heldout --inputs <dir> --out docs/probes/orun1/judge/v2-heldout --jobs 8`.
  3. Publish the result beside the baseline, whatever it is.
- Concerns:
  - v2's dev figure is optimistic by construction, because v2 was written after reading v1's misses.
  - τ-b is about 0.3: the judge separates the extremes better than it orders Like against Meh.
  - It rates arms high (five of the top seven dev scores are arms). That may cost D4 nothing, since D4 compares within a type, but it is a cross-type bias.
  - A held-out failure means a v3 motivated by dev only, measured once.
- Assumption: a version may be iterated on dev within one unit. Freezing was justified because two replicates agreed at a 10.7-point margin.
- The ot10 rubric is not retired; that is D2's ADR.
- No new dependency. No product, engine or protocol change, so the engine suites were not rerun.
- The unreconciled tail is 1 record.

Dispatch closed: 1 unit — D1 judge built on dev (v1 81.5%, v2 90.7% ×2 replicates), v2 frozen before any held-out call

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun1
- commit: 374c1d7f8c399ad0df33f54a202673c44e0fde33

## State Impact

- target: idle-ledge-8635 — Judge v2 (pairwise, hero only, claude-opus-5-5 high, win-fraction score) frozen in docs/probes/orun1/README.md before any held-out call (ADR-478, commit 374c1d7f): dev 90.7% gap-pair agreement (49/54) in two position-mirrored replicates, Love>No 4/4, tau-b ~0.30; v1 was 81.5%. Held-out measurement of v2 not yet run — it is the next unit.
