---
node_id: d91e0426-7ef8-5a69-b668-321c6d73cec2
slug: western-badger-3023
title: The author's current-state assessment
created_at: '2026-08-09T15:18:43+00:00'
parents:
- winter-rain-7897
summary: Interview answers on what is fragile, what is blocked, what is deliberate and what wastes a day — checked against ROADMAP, ARCHITECTURE and MUJOCO. The evidence the frontier is derived from.
---
## What

The author's own assessment of the project's current state, taken in the
adoption interview on 2026-08-09, plus the repository facts that corroborate or
qualify each answer. This is the evidence the state graph's frontier is derived
from.

## Why

Follows the epoch marker. The prehistory nodes record what happened; this
records what the author says is *true now*, which is the half no amount of
reading the tree produces.

## Method

Brain-dump against a seeded question list, then checked against
`docs/ROADMAP.md`, `docs/ARCHITECTURE.md` and `docs/MUJOCO.md`. Where the
author's answer and the repository agree, both are cited below. Where the answer
is memory only, it is marked.

## Result

**The two most fragile areas, in the author's words.**
1. **The dynamics, training and demonstration surfaces** — "sometimes it works
   and sometimes it doesn't, it's really not fully fleshed out; a lot of the
   windows have most of the stuff you need but not quite". Everything after the
   MJC merge is the newest and least settled code in the product.
2. **The file lifecycle inherited from Blender** — opening, saving, Save-As,
   creating a new file, how the `.cadex` project directory relates to the
   `.blend`, and how the menus come up. Corroborated by the repository, and
   worse than "fragile" in two measured places: nothing hydrates on the
   file-open path, so a `.blend` opened beside its project shows an empty
   viewport (`model_objects_on_open = 0`, measured in the shipped bundle,
   ADR-073); and a digest-moving engine change locks a project out of the UI at
   *open* with **no visible way back in** — `ensure_open` returns
   `CADEXD_RESTORE_FAILED`, Rebuild Model correctly refuses, and the operation
   that is the remedy (`write_script`) is behind a button that is not drawn in
   that state. Recovery today is by hand: `open_project restore=false` then
   `write_script`.

**Blocked on something outside this repository.** The GPU training box runs its
**own checkout** of `training/cadex_train.py`, and that checkout predates
ADR-104. Dispatching B7 would silently ignore two new draws while recording the
new algorithm string in the policy header, so the run is blocked rather than
skipped (`docs/ROADMAP.md`, Phase 14). The CPU sanity run is green: 50
iterations, σ 0.3006, witness 4.07e-08.

**The related projects, and what they are not.** `~/cdx-rl` and `~/cdx-mjc` are
**independent spin-off projects that use Cadex**; their agents occasionally open
a pull request here for a wishlist feature, and they are otherwise not part of
this repository's concerns. `~/arch` is **not a project at all** — it is where
the author keeps `.blend` and `.cadex` files, and those files are live: copy
before building or probing.

**What would waste a fresh agent's whole day**, which the author named first and
without hesitation: not understanding **which stack a thing is in**. C++ versus
Python; the Blender shell versus the FreeCAD engine versus Blender's own engine;
what `pixi` does and does not cover; **what needs a build versus what needs an
install**; and what runs on this machine versus the remote GPU box. That is an
orientation failure, not a coding failure, and it is the top reason to read
`docs/ARCHITECTURE.md` and `CLAUDE.md`'s command table before touching anything.

**Deliberately not being done** (decisions, not gaps): Phases 11 and 12 —
replacing the engine and the shell with our own — are unscheduled by choice
since ADR-030; O4 (subD) is parked with its two real blockers named instead;
there is no train button and nothing to press; there is no second provider stack
and no API-key path; and interactive mesh editing exists only as engine ops on a
declared table.

**On the docs.** The author declined to name a false doc claim and asked for it
to be checked instead. This pass read the doc set and found no claim the code
contradicts, but **the pass was doc-level, not a line-by-line audit against
source**, and every doc carries its own `Verified against source:` date. Treat
that as unverified rather than as a clean bill: where code and doc disagree, the
code wins and the doc gets fixed in the same PR.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 41e6aa6ceeed3078210e02c1f94d85bd715fbb9d

## State Impact

- target: NEW file-lifecycle — the Blender-inherited open/save/save-as/new path and the .blend<->.cadex relationship: broken, with two measured failures and a hand-only recovery
- target: NEW rl-training-loop — blocked: the GPU box runs its own checkout of the trainer, predating ADR-104, so B7 cannot be dispatched
- target: NEW dynamics-and-control — the newest and least settled surfaces in the product; author rates the training/demo panels as not fully fleshed out
- target: NEW orientation-and-build — knowing which stack a thing is in, and what needs a build versus an install, is the top day-waster
- target: NEW inherited-tree-reduction — Phases 11 and 12 are unscheduled by decision, not stalled
