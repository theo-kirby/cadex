---
node_id: 1ce931ee-e26c-5678-a3f9-21c02951af7e
slug: idle-ledge-8635
title: D1. A frozen judge agrees with the owner on designs it never saw (orun1)
created_at: '2026-10-02T17:01:59+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run orun1: **D1. A frozen judge agrees with the owner on designs it never saw.** `docs/probes/orun1/ratings.json` is the owner's ground truth and is never edited; `dev` designs build the judge, `heldout` designs measure it. Inputs are images only, rendered by the product at the accepted revision on the dark prototype floor. **The bar, on held-out:** pairwise agreement **≥ 80%** over pairs whose owner verdicts differ by two levels or more; every held-out Love above every held-out No; Kendall's tau over all pairs, reported with its count. Each judge version is measured on held-out once. The judge's prompt never reaches the product agent [rec: sweet-brook-2725]. Split: 29 dev / 26 held-out, **37** held-out gap pairs [rec: forest-sun-0304]. The human owns the checkbox.

**Evidence complete: frozen judge v2 meets the bar on held-out, awaiting the owner's tick** [rec: plain-horizon-5009]. Reconcile judgement: status `working` rather than closed, by the precedent of earlier criteria whose evidence was in and whose checkbox the owner had not yet ticked.

**Judge v2** (ADR-478, commit `374c1d7f`): pairwise, one call asks which of two robots the owner would rate higher; a design's score is its win fraction; it sees only the 1024 px studio hero `cadex render` draws from an `orun1-dev-<id>` / `orun1-ho-<id>` copy; `claude-opus-5-5`, effort high; position balanced by a pair hash. Frozen in `docs/probes/orun1/README.md` with its prompt verbatim and sha256 `0ebb5965…`, pinned in `runner/pairwise.FROZEN`; `--split heldout` is refused for any unfrozen version, a mirror, or an occupied output directory (14 tests in `runner/test_pairwise.py`) [rec: brisk-tree-8128].

| metric [rec: rich-wing-8546] [rec: brisk-tree-8128] [rec: plain-horizon-5009] | ot10 baseline (held-out) | v1 (dev) | v2 (dev, ×2 mirrored) | **v2 (held-out, once)** | bar |
|---|---|---|---|---|---|
| agreement, owner gap ≥ 2 | 13.5% (5/37) | 81.5% (44/54) | 90.7% (49/54) both | **97.3% (36/37)** | ≥ 80% |
| every Love above every No | fails 0/2 | holds 4/4 | holds 4/4 | **holds 2/2** | holds |
| Kendall τ-b | −0.079 / 325 | 0.261 | 0.307 / 0.298 | **0.436 / 325 pairs** | reported |

Sources: baseline [rec: rich-wing-8546]; dev [rec: brisk-tree-8128]; held-out, commit `d9136171`, results in `docs/probes/orun1/judge/v2-heldout`, 325/325 pairs first pass, $11.88 [rec: plain-horizon-5009]. Held-out scores by verdict: Love 1.00 and 0.80, Like mean 0.58, Meh mean 0.39, No 0.12 [rec: plain-horizon-5009].

**v2 is D4's judge.** The held-out set has been used for its one purpose; nothing may be tuned on it [rec: plain-horizon-5009].

**Caveats carried forward.** v2's dev figure is optimistic by construction (written after reading v1's misses) [rec: brisk-tree-8128]. It orders the extremes better than Like against Meh; held-out extremes are small (2 Loves, 1 No) [rec: plain-horizon-5009]. **Bias towards clean arms**, seen on dev (five of the top seven dev scores are arms) [rec: brisk-tree-8128] and again on held-out: the one reversed gap pair is `biped-c-exposed-mechanism` (Love) under `arm3-h-free` (Meh), reversed by aggregation, not by that pair's own call — D4's arm comparisons deserve a second look [rec: plain-horizon-5009]. Renders should run serially or at low parallelism, because reopen under load can still refuse (see F1) [rec: forest-sun-0304].

## Negative knowledge

- [scope: ot10's frozen rubric judge (T1–T7) on the orun1 held-out set | confidence: high | evidence: rich-wing-8546] It disagrees with the owner on 29 of 37 gap pairs and ranks the held-out No above both Loves; it cannot serve as D1's judge.
- [scope: orun1 judge v1 on dev | confidence: medium | evidence: brisk-tree-8128] v1 cleared dev by one pair; its misses were the loved plain arm losing to busier Meh arms, and character Likes losing to visor-box Nos because "both have faces". v2 changed only those two points.

## Provenance

- sweet-brook-2725 — orun1 operator-declared charter gap
- forest-sun-0304 — baseline pre-registered in the README; render runner proven on arm3; split counted 29/26 with 37 gap pairs
- polished-shade-7671 — catch-up record: baseline.py runner and the first 10 of 26 held-out scores (iterations 4–5)
- rich-wing-8546 — baseline complete: 13.5% gap-pair agreement, Love>No fails 0/2, τ-b −0.079 over 325 pairs
- brisk-tree-8128 — judge built on dev: pairwise hero-only v2 at 90.7% (49/54) in two mirrored replicates, frozen before any held-out call (ADR-478)
- plain-horizon-5009 — frozen v2 measured once on held-out: 97.3% (36/37), Love>No 2/2, τ-b 0.436 over 325; D1 bar met, awaiting owner tick
