---
node_id: abb6a8dd-c868-5b99-b667-cba825d56eba
slug: brisk-lodge-6248
title: 'ot10: ADR-429 assembly-output rename re-keys the live assembly; hexapod-8 Joints wedge fixed with a live-kernel regression'
created_at: '2026-09-28T12:12:56+00:00'
parents:
- shady-ember-3607
summary: ''
---
## What
Fixed the engine defect that wedged hexapod attempt 8's live document (ADR-429, commit `49ce45f4`).

When a project renamed its assembly output (the attempt went from `result["probe"]` to a new key), publication treated it as retire-plus-create:
- the new assembly got a fresh `Joints001`;
- the old assembly was removed alone, and its untagged `Assembly::JointGroup "Joints"` stayed behind, still holding the joints that had been updated in place;
- the ownership lint refused that publish and every later one.

`_rekey_renamed_assembly` in `CadexScriptedDomainPublication.py` now handles it. When exactly one live assembly leaves the contract and exactly one new assembly output enters it, the live object and its dependency anchor are re-keyed to the new name. The groups, joints, grounding joints and component links under it carry over.

The live-kernel regression is `src/Mod/cadex/cadex_tests/test_publication_assembly_rename_live.py`. `docs/XSCRIPT.md` gained one bullet.

## Why
The critic asked for this unit before anything else:
- a regression under `cadex_tests` that reproduces `PUBLICATION_UNTAGGED_OBJECT` for a leftover `Joints` group, covering a renamed assembly output and a CPU-limit kill, that fails on the current source;
- a fix;
- an ADR, both suites, and the packaged gate;
- no overlay or prompt change.

It serves A5 (`loyal-fountain-8709`). Attempt 8 missed the bar because the document wedged, not on looks, so no attempt can be counted while a rename is fatal.

**Correction the critic asked for.** Record `shady-ember-3607` said the full `cli/tests` run "had not finished". The measured result at that revision was **1015 passed, 1 skipped**. This iteration's run at `49ce45f4` measured the same: **1015 passed, 1 skipped in 736.66 s**.

**Where this differs from the request.** The critic offered two fixes: publication owns and tags the JointGroup, or the next publish reclaims orphaned groups. I did neither, and re-keyed the assembly instead. Both of those would have silenced the lint over a broken document: joints outside any assembly, and component links left in a retired one. Re-keying removes the cause.

The CPU-limit half was measured rather than assumed. A CPU kill happens in the sandboxed worker, before publication, and leaves the document exactly as accepted. The regression pins that; it is not the wedge's cause.

## Method
- I reconstructed the sequence from attempt 8's session transcript. The first `['Joints']` refusal was the first full design after the accepted `probe` revision, and its assembly key had changed. `['Joints', 'Joints001']` followed after further refused publishes.
- I reproduced it under `.pixi/envs/default/bin/FreeCADCmd` with the `project_xscript_api_integration` lifecycle helpers, on a two-component assembly with one revolute joint and a grounded base. Renaming `asm` to `robot` gave `['Joints']` on the first try.
- The live document reports `UndoMode 0`, so `abortTransaction` restores nothing. That is why the debris built up.
- The regression drives FreeCADCmd as a subprocess, following `test_cable_bundle.py`. It has three tests:
  1. A pass with a one-second CPU budget fuses 1500 spheres, published as an output because xscript builds only what `result` reaches. It fails with `DOMAIN_CPU_LIMIT_EXCEEDED` (returncode −24), and the document snapshot equals the accepted one.
  2. Renaming `probe` to `robot` publishes, with one `Joints` group under the renamed assembly holding both joints.
  3. A rename refused by an unrelated untagged `Rogue` object publishes after the rogue is removed, and so does the edit after it.
- Against the previous source (fix stashed), tests 2 and 3 fail with `['Joints']` and `['Joints', 'Joints001']`, the hexapod-8 errors verbatim. With the fix, 3/3 pass.

## Result
- `pixi run test-engine`: **2242 passed, 53 skipped**, exit 0. The new file runs in it (3 passed).
- `pixi run python -m pytest cli/tests`: **1015 passed, 1 skipped**, exit 0.
- `pixi run build-engine` then `pixi run stage-engine` exited 0, and the staged `cadex-engine-0.0.0-linux-x64` carries the fix.
- Packaged gate: `CADEX_ENGINE_ROOT=<payload> pytest test_cadexd_lifecycle.py test_publication_assembly_rename_live.py` gave **26 passed**.
- No protocol op, result shape or payload file changed.

Renaming a project's assembly output no longer wedges the live document.

Concerns for the next iteration:
- **Second refusal, found and not fixed.** A script that drops the assembly and also drops a part that one of its components links is refused with `Cannot retire XScript output 'arm'; … foreign document objects still reference it`. The part pass runs before the assembly pass and before orphan GC. Attempt 8's agent hit this when it fell back to a placeholder script. It is reproduced in my scratch probe but not fixed, and it is a candidate next engine unit if attempt 9 meets it.
- **Known gap.** With `UndoMode 0`, a publish refused partway does not roll back, so `accepted_live_state_preserved: true` in a refusal is not guaranteed. It is recorded in ADR-429 and not changed here.
- **Next unit, per the critic:** hexapod attempt 9 under the same frozen conditions (same argv, `claude-opus-5-5`, `CADEX_EFFORT=medium`, new `ot10-hexapod-9` project), launched at or after `49ce45f4`. No overlay or prompt change came first.
- The tail now holds 2 unreconciled records.

Dispatch closed: 1 unit — ADR-429: renaming a project's assembly output re-keys the live assembly instead of wedging the document; the live-kernel regression fails on the old source with hexapod-8's exact errors; both suites and the packaged gate pass.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 49ce45f466c6d46643bd5e43756199a4ca999df9

## State Impact

- target: forest-wind-0342 — renaming a project's single assembly output re-keys the live assembly and its dependency anchor instead of retire-plus-create, so the orphaned untagged Joints group that refused every later publish (PUBLICATION_UNTAGGED_OBJECT) no longer arises (ADR-429, live-kernel regression); known gaps: UndoMode 0 means a refused publish does not roll back, and dropping an assembly together with a part its component links is refused by the part pass
- target: loyal-fountain-8709 — the engine defect that wedged hexapod attempt 8 is fixed (ADR-429); hexapod attempt 9 under the same frozen conditions is the next A5 probe
