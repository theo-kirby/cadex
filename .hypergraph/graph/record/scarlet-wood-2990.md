---
node_id: 6c43dfa2-11af-5559-8326-953cf13f8043
slug: scarlet-wood-2990
title: 'V3 page half: revision timeline in the 3D viewport with ghost and digest tint (ADR-547)'
created_at: '2026-10-05T12:37:21+00:00'
parents:
- honest-jasper-7877
summary: ''
---
## What

V3's page half: the 3D viewport plays the design's history on a revision timeline (ADR-547, commit `26f86db5`).
- **Routes**, both reads of the ADR-546 store:
  - `GET /api/model/revision/<ordinal>` (`revision_model` in `revision_meshes.py`) returns one stored revision's model in the accepted model's shape. Each component carries its part's `sha256`, its `mesh` and a `changed` flag. It adds `previous` (the stored revision before it, with components only when that one was retained), `changed` (outputs whose part digest differs, or `null` when there is nothing retained to compare) and `compare`. An unretained revision answers `available: false` with its reason and no components. An unknown ordinal is a 404.
  - `GET /mesh/revision/<sha256>.stl` returns one kept part as STL. It is served only for a lowercase sha256 the store holds whose bytes still hash to it. The ETag is the content, the response revalidates with a 304, and the STL memo is shared with accepted meshes (`_stl_entry`).
  - `/api/project`'s `revisions` entries gain `retained`, or `retained_reason`.
- **Page**:
  - The 3D source picker gains **Revision history**.
  - `#revision-timeline` (`#revision-pick`, `#revision-label`, `#revision-status`, with `data-follow`, `data-state` and `data-ordinal`) has one stop per stored revision, oldest to newest. The newest end follows new revisions and an older stop stays picked, as the checkpoint scrubber does.
  - Unchanged parts are drawn in `--paper-ink`, changed ones in `--info`. The previous revision is a ghost (`setGhost`/`loadGhost` in `review_scene.js`) in `--ink-2` at 22% opacity, only where it differs: another digest, another placement, or a removed part. It sits outside the model group, so it does not affect bounds, picking or the hairline style.
  - An unretained stop draws nothing and says `not shown: <reason>` in `--warn`.
  - A Revisions menu row (`data-retained`) opens its revision on the timeline. That is a view, not a restore.
- **Docs**: DASHBOARD.md §2 has the hooks and behaviour; CLI.md has the routes and the trail fields; ARCHITECTURE.md is updated; ADR-547 is added.
- Also in this iteration, and committed in the same commit: the missing record for iteration 8's ADR-546 unit, `honest-jasper-7877`.

## Why

I did what the critic asked, in its order:
1. Fix first: write ADR-546's missing record, with an impact on `peaceful-spire-1615` and parent `forest-mist-3382`, and with both full suites measured on that commit with the GPU hidden. Done as `honest-jasper-7877`. I measured the suites in a separate worktree at `11a107b2`.
2. The unit: V3's page half, as specified. That covers the GET routes, the timeline, the ghost, the tint, absence that never borrows another revision's geometry, the browser test across at least three revisions checking ordinals and the current revision against the Revisions menu, and DASHBOARD.md in the same commit.

**Deviation.** The critic also asked for a reconcile. I did **not** run one: this iteration's dispatch rules forbid the reconcile skill in a work iteration, with no exceptions. The tail is now four unreconciled records: `snowy-water-3502`, `forest-mist-3382`, `honest-jasper-7877` and this one. That is past the charter's three-record threshold, so the next iteration should be a reconcile pass.

On "pin it the way existing routes are pinned": there is no route-contract test yet (that is P1). I pinned the new routes as the checkpoint route is pinned, with server tests on their response shape and refusals, and with documentation in CLI.md. P1's contract test will absorb them.

Two choices are mine:
- **A source, not a mode.** The accepted model view stays exactly as it was. The timeline appears when the owner picks Revision history, or clicks a Revisions menu row.
- **The ghost only where the previous revision differs.** An identical part at the same placement would lie on top of its own copy and wash the model out. "Changed" (the tint) means the part's digest, per the charter. A part that only moved is ghosted at its old place but not tinted.

## Method

- I read the ADR-546 store, `accepted_model`, the mesh routes, `review.js`'s checkpoint scrubber and `review_scene.js`, and built the new pieces on those patterns.
- `cli/tests/test_review_revisions.py`, 3 tests:
  - Two tests with no engine, on a hand-written four-revision biped store:
    - the changed foot and its ghost;
    - a torso that only moved, not counted as changed;
    - an unretained first revision, and a successor with nothing to compare;
    - the trail's `retained` and `retained_reason`;
    - 404s for an unknown ordinal, a non-numeric ordinal, an unknown digest, an uppercase digest, a path escape, and a blob whose bytes no longer match its name;
    - the 304.
  - One Chromium test against the **real engine**. A biped is written, then its foot is set to 55, then to 70, with the third revision landing while the page is open. It scrubs 3 → 2 → 1 and checks:
    - each stop's own foot digest;
    - the newest tints `foot_l` with `--info`, ghosts the old foot, and leaves the torso in `--paper-ink`;
    - revision 1 has no ghost and no tint;
    - the timeline's `(ordinal, current)` list equals the Revisions menu's, `[(1,F),(2,F),(3,T)]`;
    - a menu row click opens revision 2;
    - the newest end follows again.
    
    It then deletes revision 1's index row, as in a store from before ADR-546: that stop draws 0 components and says `not shown: accepted before this project retained revision meshes (ADR-546); its geometry was not kept`, and revision 2 draws with no ghost.
- I checked a screenshot by eye: the tinted foot, the timeline and the status line on the dark floor. It is not committed.
- Suites at `26f86db5`'s tree, with the GPU hidden (`CUDA_VISIBLE_DEVICES="" JAX_PLATFORMS=cpu`):
  - `pytest cli/tests -rs`: **1150 passed, 1 skipped, 0 failed** (16 min 45 s). The one skip is `test_review_server.py:721`, which needs `CADEX_REVIEW_HOST`.
  - `pixi run test-engine`: **2585 passed, 58 skipped**.
  - The protocol and payload are untouched, so the packaged gate was not needed.

## Result

What is true now: V3 has both halves.
- Retention (ADR-546) is measured: 9 kept biped revisions take 8,544 B of blobs plus a 26,854 B index, against 102,596 B for full copies.
- The page half (ADR-547) has a real-engine browser test across three revisions, with a ghost, a tint, honest absence, and agreement with the Revisions menu.

Still open under V3: **the explicit backfill CLI command** that rebuilds old revisions to fill the gap. The charter says rebuilding is "an explicit CLI command, not a side effect". The page already says why an old revision has no model. Until the command exists, `orun3-biped`'s 13 pre-ADR-546 revisions read as not retained.

Concerns:
- The ADR-546 worktree run showed 11 skips against this tree's 1. Both runs had the engine; `test_revision_meshes` passed in the worktree. The extra skips are most likely tests that read files git does not carry, which a fresh worktree lacks. That run had no `-rs`, so this is not proven. The run on the main tree is clean.
- The page still fetches through `BASE + '/api/…'`. Making that relative is P1's job, and the two new routes join P1's contract.
- The tail has four unreconciled records, so a reconcile is due.

No new dependency.

Dispatch closed: 1 unit — V3 page half: revision timeline in the 3D viewport with ghost, digest tint and honest absence (ADR-547), real-engine browser test; plus ADR-546's missing record (honest-jasper-7877)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun3
- commit: 26f86db5be3e0c9e728429841f869227ca07d36b

## State Impact

- target: peaceful-spire-1615 — Page half landed (ADR-547, commit 26f86db5): GET /api/model/revision/<ordinal> + /mesh/revision/<sha256>.stl over the ADR-546 store; a Revision history source puts #revision-timeline in the 3D viewport (newest follows, older pinned), changed-digest parts tinted --info, previous revision ghosted where it differs, unretained revisions draw nothing and say why; Chromium test against the real engine scrubs 3 biped revisions and matches the Revisions menu's ordinals and current. Suites green (cli 1150/1 skip GPU hidden, engine 2585/58). Remaining V3 bullet: the explicit backfill command for pre-ADR-546 revisions.
