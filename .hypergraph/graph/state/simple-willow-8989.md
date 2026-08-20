---
node_id: f32512e7-9b0b-53c3-a2c1-b052424853ad
slug: simple-willow-8989
title: File lifecycle — open, save, Save-As, and .blend vs .cadex
created_at: '2026-08-09T15:22:02+00:00'
parents:
- shy-crane-2573
summary: ''
---
Status: broken

## Current

The file-handling path inherited from Blender — opening, saving, Save-As, creating a new file, how the `.cadex` project directory relates to the `.blend` that displays it, and how the menus come up. **The author names this as one of the two most fragile parts of the product** [rec: western-badger-3023].

Three failures here are measured rather than suspected [rec: western-badger-3023] [rec: weathered-falcon-4350]. **Two are open:**

- **Nothing hydrates when a file is opened.** `load_post` reaches `on_file_changed`, which drops the previous file's sessions and returns early when the `.cadex` directory already exists; nothing queues a rebuild. A `.blend` opened beside its project therefore shows an **empty viewport** — `model_objects_on_open = 0`, measured in the shipped bundle — until an agent tool call, a slider drag or Rebuild Model provokes the first request [rec: western-badger-3023].
- **A digest-moving engine change locks a project out of the UI with no visible way back in**, and the failure is at *open*, not at the next edit. `ensure_open` runs the restore pass, `CADEXD_RESTORE_FAILED` comes back, and every operation that would fix it is behind the same call. Rebuild Model correctly refuses. The operation that **is** the remedy is `write_script`, which already re-accepts on success — what is missing is a button that reaches it in this state [rec: western-badger-3023].

**Recovery today is by hand**: `open_project restore=false`, then `write_script`. Until a fix lands, every digest-moving change ships with a manual recovery — and digest-moving changes are routine here, because a retained artifact's bytes are part of the project's identity [rec: western-badger-3023] [rec: crisp-glacier-6395].

The fix is known and is a `shell/` diff, which makes it a decision rather than something to slip in: cache the failure code from the last open on the per-root state, and let the chat panel draw the re-accept box it already draws for an orphaned project [rec: western-badger-3023].

**The third is fixed** (ADR-155) [rec: weathered-falcon-4350]. **Save-As lost the pointer back to the original project on the first ordinary save afterwards**, so "Rebuild From Saved Script" carried no imported geometry across and said nothing about it. `save_pre` fires on every write, not only on Save-As, and `remember_source_root` recorded the current project root every time — so one Ctrl-S replaced the hint with the new file's own root, which `source_root` then rejects for being the current one. `migrate_assets` returned `(True, "")`, and the rebuild died on the first `mesh.import_file` with the engine's "no staged mesh asset named X" as the only visible symptom. Measured on `actuator-v9`, Saved-As from `actuator-v7`: its stored hint pointed at itself, and the artifact trail shows three rebuild attempts, the first two staging no assets at all and the third one, the error walking from the first import to the second — one file per press. The carry loop itself was never at fault; run headless against the same two files it carries both. `remember_source_root` now writes only when the destination root differs from the current one (`save_pre` is handed the destination, so the question is answerable before the write), and `migrate_assets` reports when it found nowhere to carry from [rec: weathered-falcon-4350].

**One adjacent feature was checked against this and cleared, at the engine level only.** Refreshing a linked part moves the consuming project's digest by design, so it was a candidate for the second failure above. It is not: refresh goes through the ordinary rebuild-and-accept path rather than swapping bytes under an accepted model, and a live test closes the project after a refresh, reopens it, and asserts the restore pass **performed and matched**. That is `open_project`, not the shell's `load_post` — it says nothing about the hydration failure, which is untouched [rec: ancient-current-9419].

## Negative knowledge

- [scope: opening a .blend beside its .cadex | confidence: high | evidence: western-badger-3023] Do not assume a file open hydrates the model. Nothing queues a rebuild on the file-open path, so the viewport is empty until a tool call, a slider drag or Rebuild Model provokes the first request.
- [scope: digest-moving engine changes | confidence: high | evidence: western-badger-3023] Rebuild Model cannot recover a project locked out by a digest change, and it is correct to refuse. The remedy is open_project restore=false then write_script, and no button reaches it — every digest-moving change ships with a manual recovery until that lands.
- [scope: Save-As and project assets | confidence: high | evidence: ancient-current-9419] Save-As carries assets forward through the shell's own suffix list, not the engine's. A new asset type absent from that list is dropped silently, and the copy fails later with a script that cannot run. `.cxpart` was fixed; `.cxpolicy` has the same gap and is still open.
- [scope: a .blend Saved-As and then saved again before ADR-155 | confidence: high | evidence: weathered-falcon-4350] Such a file records its **own** root as its asset source, so the original project is named nowhere in it. This cannot be repaired from inside the file — the imported files are wherever the original is — and the imports must be re-done by hand once. The fix stops new files entering this state and makes the state say so; it does not undo it.
- [scope: shell handlers fired by more than one user action | confidence: medium | evidence: weathered-falcon-4350] A `bpy.app.handlers` callback that records state must check *which* action fired it. `save_pre` serves Save-As and ordinary saves alike, and treating them the same is what destroyed the Save-As hint. The arguments Blender passes (here, the destination path) are what distinguish them.

## Provenance

- western-badger-3023 — the author names this as one of the two most fragile areas, and the two measured failures behind that
- crisp-glacier-6395 — why digest-moving changes are routine here rather than rare
- ancient-current-9419 — linked-part refresh checked against the lockout failure, and the Save-As asset gap it exposed
- weathered-falcon-4350 — the third measured failure, diagnosed on a real damaged model and fixed (ADR-155): the Save-As source-root hint overwritten by the next ordinary save, and the silence around it
