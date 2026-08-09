---
node_id: f02283fb-8d91-5487-aac1-bcb166d41503
slug: winter-rain-7897
title: Adopted Hypergraph
created_at: '2026-08-09T15:16:51+00:00'
parents:
- crisp-glacier-6395
- jolly-walrus-3692
- mellow-hawk-8610
- solemn-chart-6274
- slender-basin-4979
- kind-ledge-5493
summary: 'Mode-B adoption on 2026-08-09: 14 prehistory nodes authored from the repo and an author interview, this epoch marker, and a ten-node state graph. No legacy graph existed, so nothing was imported and nothing was truncated.'
---
## What

Cadex adopted the Hypergraph two-graph protocol on 2026-08-09. This node is the
**epoch marker**: record nodes created strictly before it are legacy history and
exempt from I2 template compliance; everything at or after it is held to the full
protocol, and authoring is never exempt.

## Why

The project had 16 days of dense history — 248 commits, 136 ADRs, and a doc set
that is deliberately evidence-grade — and no machine-readable projection of
*what is true now*. The ADR log answers "why did this happen"; it does not answer
"what should I not waste a day on", which is what an arriving agent needs first.

Parented on all six prehistory tips, so the marker is the single record tip and
the high-water mark over it covers the whole authored history.

## Method

**Mode B — ground-up adoption.** There was no legacy hosted graph to import:
nothing in the repository referenced a graph store, and the survey found no
anchors. Nothing was truncated and no archive reference is needed, because there
was no archive. Config carries an `epoch:` block and **no `archive:` block**,
which is correct for mode B and is not an omission.

Authored, in order:
1. `hypergraph adopt --survey` for the computed facts (git shape, timeline
   signals, churn, doc inventory, onboarding files).
2. A full read of `docs/VISION.md`, `README.md`, `docs/IDEAS.md`,
   `docs/ROADMAP.md` (all 1,617 lines), `docs/ARCHITECTURE.md`,
   `docs/MUJOCO.md` §5–§6, `docs/ORGANIC.md` §3–§4, and the 136 ADR titles.
3. **An interview with the author** (2026-08-09), taken as a brain-dump against a
   seeded question list. This is where the pre-repo era, the era names, the
   machines, the undocumented dead ends and the fragility assessment came from —
   none of it is derivable from the tree.
4. `hypergraph adopt --init`, which minted both roots and wrote the config.
5. **Fourteen prehistory record nodes**, one per era or workstream, each citing
   the doc, ADR or interview answer its claims came from.
6. This marker, then the state graph distilled from the prehistory nodes'
   declared impacts.

## Result

- Record graph: 14 prehistory nodes plus two roots plus this marker.
- State graph: ten nodes — seven components under the root and three children —
  with a frontier of three (`file-lifecycle` broken, `rl-training-loop` blocked,
  `inherited-tree-reduction` open).
- **What did not come across, stated rather than assumed**: no artifacts, because
  there was no source graph to carry them from. Every claim in the state graph
  cites a prehistory node, and every prehistory node names its own evidence — a
  doc, an ADR number, a commit range, or the interview. Interview-only claims are
  marked as such and carried at low confidence, because they are the ones that
  cannot be re-derived from the repository.
- The ADR log is **not superseded**. `docs/DECISIONS.md` remains the narrative
  record of decisions and stays the place a direction change is argued; the
  record graph is where a unit of work lands with a declared state impact, and
  the state graph is the distilled projection. Work that earns an ADR usually
  earns a record node too, and they should agree.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 41e6aa6ceeed3078210e02c1f94d85bd715fbb9d

## State Impact

none: the marker records the conversion itself and changes nothing about the product; the state graph it enables is distilled from the prehistory nodes' own declared impacts
