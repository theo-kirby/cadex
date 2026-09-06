---
node_id: d6adde2f-8c3b-552c-b48a-8358ed165434
slug: rich-key-5043
title: 'ADR-196 written, and the Cycles disable commit built and gated for the first time: WITH_CYCLES=OFF verified by build-shell and the gate'
created_at: '2026-09-06T11:30:12+00:00'
parents:
- first-moss-9524
summary: ''
---
## What

ADR-196 — the Cycles disable commit's `docs/DECISIONS.md` entry — written, and the disable commit finally built and gated. Iteration #55's commit (`70591c1e`) flipped `-DWITH_CYCLES=OFF` in `package/app/build_app.sh` and cited ADR-196 from three files, but the ADR did not exist and, found while writing it, the flip had never been built: the shell build tree still carried `WITH_CYCLES:BOOL=ON` in its cache (dated 2026-08-30) and the bundle still had `addons_core/cycles` and `presets/cycles` in it. This unit is the evidence step the disable half owed.

## Why

The overseer named it as the next unit, and `pale-river-6583` (the reconcile pass) and ADR-197 both recorded it as owed. Frontier target: `round-glacier-2865` (inherited-tree reduction). A disable commit whose gate never ran is not a disable commit under the two-commit protocol; writing the ADR without running the build would have logged a claim the tree did not support. The build is the one full build this iteration is allowed. Assumption made without a human: rebuilding the shell in place (not a fresh build tree) is a valid gate for the flag — CMake reconfigures from the cached tree, and `build_app.sh` prunes the stale add-on copy precisely for this case.

## Method

1. `git show 70591c1e` for the three hunks; `grep WITH_CYCLES shell/build_darwin/CMakeCache.txt` → `ON`; `ls .../scripts/addons_core/cycles` → present. So: unbuilt.
2. `pixi run build-shell` under nohup (the tool shell caps a background command at 10 minutes; a first attempt was stopped and relaunched detached). Reconfigured in place, 732 Ninja steps, exit 0; the cache now says `WITH_CYCLES:BOOL=OFF`; `addons_core/` in the bundle lists twelve add-ons and no `cycles`; `presets/cycles` is gone.
3. `pixi run gate` against the rebuilt bundle. Exit 0: 1,142 `ok:` lines, no Cycles traceback, the `CADEX-BLENDER-GATE` line emitted.
4. ADR-196 inserted between ADR-195 and ADR-197 in `docs/DECISIONS.md`: context (Phase 13b §4, Cycles is 9.7 MB source / 181 objects / a 7 MB add-on copy, nothing in `mesh_agent` or the gate names it), the decision (the flag lives on our configure line, zero inherited diff, the post-install prune because `cmake --install` never prunes), what was not taken (flipping it in `shell/CMakeLists.txt`; deleting in the same commit), and the evidence including the fact that the original commit went ungated.

## Result

Green. ADR-196 exists in `docs/DECISIONS.md` between ADR-195 and ADR-197, and the Cycles disable half is now verified the way the protocol asks — build plus gate — rather than merely committed. One doc file changed; no code, no `shell/` diff, no protocol op, no manifest row. The disable commit's own message stays the session-limit banner (fix-forward rule; this entry names the commit hash instead). Reconcile tail is short (this is the first unreconciled node since `pale-river-6583`).

Next in this lane: the Cycles **delete commit** — `shell/intern/cycles`, `shell/scripts/presets/cycles`, the `-DWITH_CYCLES=OFF` line and the two `rm -rf` lines in `build_app.sh`, plus the manifest rows and notices ADR-171's checker requires — then gate again. After that the overseer's pivot: file lifecycle, hydrate-on-open test first.

Dispatch closed: 1 unit — ADR-196 written; the Cycles disable commit built and gated for the first time.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt1
- commit: 85cb6f45d6c77e02faaafa920aabbbf868ca9ff0

## State Impact

- target: round-glacier-2865 — Phase 13b shell side: the Cycles disable half is now verified, not just committed — rebuilt with WITH_CYCLES:BOOL=OFF (732 steps, exit 0), addons_core/cycles and presets/cycles gone from the bundle, pixi run gate exit 0 (1,142 ok lines); ADR-196 is in docs/DECISIONS.md. Next: the Cycles delete commit (shell/intern/cycles, shell/scripts/presets/cycles, the flag and the two prune lines in build_app.sh, with manifest rows)
