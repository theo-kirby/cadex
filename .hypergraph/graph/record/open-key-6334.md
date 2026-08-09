---
node_id: 990852fa-605c-59bb-a137-32e103252bcc
slug: open-key-6334
title: 'Prehistory: the branch ends — MJC merges into main'
created_at: '2026-08-09T15:16:12+00:00'
parents:
- sage-wood-0687
summary: The cost was measured rather than assumed — 53.5 MB on a 3.3 GB app, nothing at runtime — so the permanent branch became the product. One branch since.
---
## What

`MJC` stopped being a permanent branch and became the product (ADR-102). The
`MJC` ref still exists, pointing at the merge; nothing should be committed to
it. **There is one branch.**

## Why

Follows the MJC arc. ADR-078 had made the branch permanent on the argument that
a bracket modeller should not pay for a physics engine. The author measured that
cost instead of continuing to assume it.

## Method and Result

**53.5 MB on a 3.3 GB application, and nothing at all at runtime** for a user
who never calls it — because `CadexDynamics.py` is deferred-imported and
reachable only from the sandboxed worker. About 30 MB of the 53.5 is
`mujoco/experimental/`, a studio viewer the engine never imports; pruning it is
known and deferred.

What the merge dissolved: the one-way sync discipline, the branch-marked doc
blocks, and the empty-`shell/`-diff rule. What it did **not** dissolve is the
boundary underneath it — dynamics is engine-side, the shell never learns MuJoCo
exists, and training happens on a machine we do not ship to.

The `shell/` diff was spent afterwards, deliberately and once, on the collision
overlay (ADR-091), and only inside `mesh_agent/` and the gate suite. The rule
that replaced "empty diff" is what the empty-diff rule was always a proxy for:
**every line of our `shell/` diff is under
`shell/scripts/addons_core/mesh_agent/` or `shell/tests/python/`, and the
inherited Blender tree is untouched.** `docs/BLENDER-TREE.md` §2a is eight files
and must stay eight.

One consequence for anyone reading history: the merge **renumbered part of the
ADR log**. ADR numbering is not contiguous and must not be assumed to be —
ADR-054 was deliberately never written (the item was measured at 17.7 ms, ~4.2 %
of a drag, and declined, keeping its number in `ROADMAP.md` so it can be
revived), 069–072 and 111 are absent, and 060–067 plus 074 were renumbered on
the merge. Cite an ADR by number **and** title.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 41e6aa6ceeed3078210e02c1f94d85bd715fbb9d

## State Impact

- target: NEW dynamics-and-control — dynamics is ordinary product surface on one branch, not a vertical on a fork.
- target: NEW orientation-and-build — ADR numbering is not contiguous; the `MJC` ref is frozen at the merge.
