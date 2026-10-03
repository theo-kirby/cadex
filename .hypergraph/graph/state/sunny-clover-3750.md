---
node_id: b688c13f-c50a-563f-8a85-8063f0133e77
slug: sunny-clover-3750
title: S1. The shell is gone and nothing reaches for it (orun2)
created_at: '2026-10-03T10:54:40+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run orun2: **S1. The shell is gone and nothing reaches for it.** - `git ls-files shell | wc -l` is 0. - No pixi task, `package/` script, CMake rule, test, `.gitattributes` LFS rule or live doc refers to `shell/`, `mesh_agent`, a `.blend`, or `CADEX_BLENDER_EXECUTABLE`. ADRs and `docs/history/` are the exception. - The removal follows the two-commit protocol: a disable commit, then a delete commit, each green. - The licensing posture is restated without the GPL half: - `test_licensing_compliance.py`, `docs/inherited-modifications.json` and `docs/PROVENANCE.md` say what is now true; - an ADR records that the repo no longer carries GPL code, if that is what the audit finds. - **`mesh.blender` is retired**, with an ADR naming every project and example that used it: - the op, its runner, worker and adapters, `examples/blender_enclosure.py`, its tests and `docs/BLENDER-RECIPES.md` are all removed; - `OP_ARG_SPECS` and `docs/INTEGRATION.md` change in the same commit. - Codex and pi support is removed. - Shell-only tests are gone. Tests that only *mention* the shell are rewritten: - purity guardrails; - `rollout_bake_integration.py`; - `test_project_docs.py`. [rec: winter-stone-5109]

Declared target: `gap-s1-shell-gone-nothing-reaches`. The human owns the charter checkbox; roles report results and do not tick it. Reconcile judgement: earlier runs have criteria with the same letters, so every orun2 gap title carries the run. Flip to working only when the criterion has measured evidence; it stays open until then [rec: winter-stone-5109].

## Negative knowledge

None yet.

## Provenance

- winter-stone-5109 — orun2 operator-declared charter gap
