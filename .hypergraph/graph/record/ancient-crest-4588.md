---
node_id: 33521601-c395-5d6a-aff5-e8ceead3d924
slug: ancient-crest-4588
title: 'Cycles delete commit evidenced, and the second Phase 13b shell removal started: WITH_INTERNATIONAL disabled, built and gated (ADR-198)'
created_at: '2026-09-06T11:55:03+00:00'
parents:
- rich-key-5043
summary: ''
---
## What

Two things in the Phase 13b shell lane, both against `round-glacier-2865`. (1) The Cycles **delete** commit (`3aa6926b`, iteration #84) finally has its evidence: iteration #86 launched the build and gate but its session ended before they finished, leaving ADR-196 with a literal `EVIDENCE_PLACEHOLDER`; the logs completed at 13:44 and 13:47 and this iteration verified and wrote the numbers (`7fd5444e`). (2) The **second** shell-side removal is started: the translation subsystem, `-DWITH_INTERNATIONAL=OFF` on `build_app.sh`'s configure line plus a post-install prune of `datafiles/locale`, ADR-198, built and gated in this iteration (`e1ae6a57`).

## Why

The overseer named both: record the Cycles two-commit protocol with its gate, and start the second removal the goal requires. Frontier target `round-glacier-2865` (inherited-tree reduction). Candidate chosen by the question policy — the most reversible option: `shell/locale/` is a `WITH_*` option (unlike `shell/tests/files/`, the larger item, which has no flag), upstream builds the OFF configuration itself (`blender_lite.cmake`, `bpy_module.cmake`), nothing under `mesh_agent/` or the gate suites calls `bpy.app.translations`, and fonts install unconditionally so the option's old "fonts and text" wording does not bite. Assumption made without a human: one build covering the locale flip is also sufficient evidence that the tree still configures with `shell/intern/cycles` absent — it is, since CMake reconfigured from scratch over the deleted directory. Caveat stated in ADR-196 rather than hidden: the cached tree already held `WITH_CYCLES=OFF`, so the `option()` default flipped in `shell/CMakeLists.txt` is only proven by a fresh configure, which the one-build budget did not allow.

## Method

1. Found `/tmp/build-shell-86.log` (stamped build 497, six Ninja steps, 173 installs, no Cycles in `addons_core/` or `presets/`) and `/tmp/gate-86.log` (1,142 `ok:`, `CADEX-BLENDER-GATE` `"ok": true`, `OK`), both finished after #86 stopped. `test_licensing_compliance.py` passes at HEAD. Wrote the numbers into ADR-196; committed docs-only.
2. Audited the option: `option(WITH_INTERNATIONAL ... ON)` in `shell/CMakeLists.txt`, the install block in `source/creator/CMakeLists.txt` (49 `.po` → `.mo` via `msgfmt`, 77 MB in the bundle), `blentranslation`'s three guards, the two upstream configs that force OFF, `_addons_hidden_core` and `BKE_blendfile_userdef_from_defaults` (neither lists `ui_translate`).
3. Edited `build_app.sh` (flag + prune + comment), `docs/BLENDER-TREE.md` §4 row, `docs/ROADMAP.md` Phase 13b line, appended ADR-198 with the not-taken list.
4. `pixi run build-shell` then `pixi run gate`, chained under nohup: configure 1.0 s, cache `WITH_INTERNATIONAL:BOOL=OFF`, 737 Ninja steps (the define reaches `makesrna`), `libbf_blentranslation` relinked, exit 0, build 499, `datafiles/` = `assets colormanagement fonts icons studiolights`. Gate exit 0, 1,142 `ok:`, `"ok": true`, `model_objects_on_open` 1, `engine_from_bundle` true, `OK`.

## Result

Green. Cycles is the first tree fully through the two-commit protocol with both halves built and gated; the locale disable is the second removal's first half, verified the same way. Two commits, zero inherited diff, no manifest row, no protocol op. Reconcile tail: this node plus `rich-key-5043` — short.

Next in this lane: the locale **delete** commit — `git rm -r shell/locale` (80 MB, 49 `.po`), default `WITH_INTERNATIONAL` to `OFF` in `shell/CMakeLists.txt` (§2a, already manifested, as ADR-196 did), drop the flag from `build_app.sh` and keep the prune line, build and gate. Then the goal's inherited-tree criterion is met with two removals, and the lane can pivot to file lifecycle (hydrate-on-open test — note the gate already reports `model_objects_on_open: 1` and `hydrate_on_open_seconds`, so that criterion may need only a check, not a build).

Dispatch closed: 1 unit — the Cycles delete commit's evidence written into ADR-196, and the second Phase 13b removal (WITH_INTERNATIONAL, shell/locale) disabled, built and gated as ADR-198.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt1
- commit: e1ae6a570db7434921dfe689547cb6a12caa93ae

## State Impact

- target: round-glacier-2865 — Phase 13b shell side: Cycles is fully through the two-commit protocol, both halves built and gated (ADR-196 complete, evidence from the #86 logs: six steps, build 497, gate 1,142 ok). Second removal started: WITH_INTERNATIONAL=OFF on build_app.sh's configure line and datafiles/locale (77 MB) pruned from the bundle (ADR-198), built (737 steps, build 499, exit 0) and gated (exit 0, 1,142 ok, CADEX-BLENDER-GATE ok:true). Next: the locale delete commit — git rm shell/locale, option default OFF in shell/CMakeLists.txt, flag out of the script
