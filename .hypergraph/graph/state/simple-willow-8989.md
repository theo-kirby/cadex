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

Three failures here were measured rather than suspected [rec: western-badger-3023] [rec: weathered-falcon-4350]. **Two are fixed, one is open**, and one adjacent gap (the `.cxpolicy` Save-As suffix) is known and untaken.

**Fixed: opening a file now hydrates the model** (ADR-186) [rec: twilight-isle-0370]. Before, `load_post` reached `on_file_changed`, which returned early when the `.cadex` directory already existed and queued nothing, so a `.blend` opened beside its project showed an **empty viewport** — `model_objects_on_open = 0` in the shipped bundle — until a tool call, a slider drag or Rebuild Model provoked the first request [rec: western-badger-3023]. Now `load_post` → `on_file_changed` → `cadex_backend.queue_open`: for a saved file whose project directory exists, the open is queued and a timer-driven pump (the drag and refine pumps' shape: queued → opening → rebuilding, with the project-still-current rule at every step) runs the restore-verified `open_project` and the display `rebuild` on a worker thread and hydrates on the main thread. `ensure_open` drains a queued open for its root before doing anything else, so a tool call racing the queue never issues a second `open_project`. Gate test `test_opening_a_file_hydrates` deletes the baked objects, drains the queue by hand and asserts `model_objects_on_open > 0`: measured 1, with `hydrate_on_open_seconds = 2.03` — equal to the synchronous `open_seconds` on the same run, so the pump adds nothing. `pixi run gate`: 1113 checks, 0 failures. Two deliberate exclusions: **Save-As does not queue an open** (saving model A over `b.blend` beside a `b.cadex` would otherwise repaint the viewport with model B on the spot), and **an unsaved scene's temporary root never queues** (guarded on `bpy.data.filepath`). A failed open at load now reaches the parameters panel's alert row, a chat status line, and `open_failure_code` on the per-root `_State` — the hook the lockout fix below needs [rec: twilight-isle-0370].

**Open: a digest-moving engine change locks a project out of the UI with no visible way back in**, and the failure is at *open*, not at the next edit. `ensure_open` runs the restore pass, `CADEXD_RESTORE_FAILED` comes back, and every operation that would fix it is behind the same call. Rebuild Model correctly refuses. The operation that **is** the remedy is `write_script`, which already re-accepts on success — what is missing is a button that reaches it in this state [rec: western-badger-3023]. **Recovery today is by hand**: `open_project restore=false`, then `write_script`. Until a fix lands, every digest-moving change ships with a manual recovery — and digest-moving changes are routine here, because a retained artifact's bytes are part of the project's identity [rec: western-badger-3023] [rec: crisp-glacier-6395]. Half the fix is now in place: the failure code is cached on the per-root state [rec: twilight-isle-0370]. What remains is the chat panel drawing the re-accept box it already draws for an orphaned project, wired to `write_script` [rec: western-badger-3023].

**Fixed: Save-As lost the pointer back to the original project on the first ordinary save afterwards** (ADR-155) [rec: weathered-falcon-4350], so "Rebuild From Saved Script" carried no imported geometry across and said nothing about it. `save_pre` fires on every write, not only on Save-As, and `remember_source_root` recorded the current project root every time — so one Ctrl-S replaced the hint with the new file's own root, which `source_root` then rejects for being the current one. `migrate_assets` returned `(True, "")`, and the rebuild died on the first `mesh.import_file` with the engine's "no staged mesh asset named X" as the only visible symptom. Measured on `actuator-v9`, Saved-As from `actuator-v7`. `remember_source_root` now writes only when the destination root differs from the current one, and `migrate_assets` reports when it found nowhere to carry from [rec: weathered-falcon-4350].

**One adjacent feature was checked against the lockout and cleared, at the engine level only.** Refreshing a linked part moves the consuming project's digest by design, but refresh goes through the ordinary rebuild-and-accept path rather than swapping bytes under an accepted model, and a live test closes the project after a refresh, reopens it, and asserts the restore pass **performed and matched** [rec: ancient-current-9419].

## Negative knowledge

- [scope: Save-As, and an unsaved scene's temporary root | confidence: high | evidence: twilight-isle-0370] Do not assume a file open hydrates the model in these two cases. Hydrate-on-open (ADR-186) queues only for a saved `.blend` whose `.cadex` directory exists; Save-As is deliberately not queued (it would repaint the viewport with the other model on the spot) and the unsaved temp root is guarded out. The former blanket rule from western-badger-3023 is retired for the ordinary open.
- [scope: digest-moving engine changes | confidence: high | evidence: western-badger-3023] Rebuild Model cannot recover a project locked out by a digest change, and it is correct to refuse. The remedy is open_project restore=false then write_script, and no button reaches it — every digest-moving change ships with a manual recovery until that lands.
- [scope: Save-As and project assets | confidence: high | evidence: ancient-current-9419] Save-As carries assets forward through the shell's own suffix list, not the engine's. A new asset type absent from that list is dropped silently, and the copy fails later with a script that cannot run. `.cxpart` was fixed; `.cxpolicy` has the same gap and is still open.
- [scope: a .blend Saved-As and then saved again before ADR-155 | confidence: high | evidence: weathered-falcon-4350] Such a file records its **own** root as its asset source, so the original project is named nowhere in it. This cannot be repaired from inside the file and the imports must be re-done by hand once. The fix stops new files entering this state; it does not undo it.
- [scope: shell handlers fired by more than one user action | confidence: medium | evidence: weathered-falcon-4350] A `bpy.app.handlers` callback that records state must check *which* action fired it. `save_pre` serves Save-As and ordinary saves alike, and treating them the same is what destroyed the Save-As hint. The arguments Blender passes (here, the destination path) are what distinguish them.

## Provenance

- western-badger-3023 — the author names this as one of the two most fragile areas, and the two measured failures behind that
- crisp-glacier-6395 — why digest-moving changes are routine here rather than rare
- ancient-current-9419 — linked-part refresh checked against the lockout failure, and the Save-As asset gap it exposed
- weathered-falcon-4350 — the third measured failure, diagnosed on a real damaged model and fixed (ADR-155): the Save-As source-root hint overwritten by the next ordinary save, and the silence around it
- twilight-isle-0370 — hydrate on open fixed (ADR-186): the queued open and its pump, the gate test measuring model_objects_on_open = 1, the two deliberate exclusions, and the open failure code cached on the per-root state for the lockout box
