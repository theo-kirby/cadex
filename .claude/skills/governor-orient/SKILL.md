---
name: governor-orient
description: Orient in a project whose research memory is a governor graph (a .flywheel/ repository with a governor root) - read what is true now, the frontier, and the unfolded tail before choosing work. Read-only, a few calls.
---

# Orient

The project's memory is one Flywheel graph: append-only **records** of what happened, and
a distilled **state** of what is true now, each claim citing the records it rests on
(the governor conventions, `docs/CONVENTIONS.md` in the governor repo).

1. `governor orient` prints, from the current graph:
   - the **frontier**: every claim that is `broken`, `blocked` or `open`;
   - the **unfolded tail**: records not yet folded into state, each with its declared
     impacts. Apply those impacts in your head on top of the state; state lags the tail
     by design.
   - the **architecture**: the state tree with each claim's first line;
   - the **most recent records**.
2. If the task names a claim or a record, read it whole: `governor snapshot` is the
   full graph as JSON (nodes by id, with `slug`, `title`, `content`, `kind`, `status`,
   `parents`; edges with `content`). Filter it with `jq` or a short script rather
   than printing it.
3. Before planning, read the claims you will touch and their `## Negative knowledge`:
   it exists so you do not rediscover a dead end.

Report in a few lines: what is true in the area you are about to work in, what the
frontier says about it, which tail records bear on it, and what you will do. Cite
slugs.

Never edit the graph while orienting. If `governor` is not found, the package is
`@theo-kirby/governor` (Node ≥ 24.15, plus the `flywheel` CLI).
