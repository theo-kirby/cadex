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

Two failures are measured rather than suspected:

- **Nothing hydrates when a file is opened.** `load_post` reaches `on_file_changed`, which drops the previous file's sessions and returns early when the `.cadex` directory already exists; nothing queues a rebuild. A `.blend` opened beside its project therefore shows an **empty viewport** — `model_objects_on_open = 0`, measured in the shipped bundle — until an agent tool call, a slider drag or Rebuild Model provokes the first request [rec: western-badger-3023].
- **A digest-moving engine change locks a project out of the UI with no visible way back in**, and the failure is at *open*, not at the next edit. `ensure_open` runs the restore pass, `CADEXD_RESTORE_FAILED` comes back, and every operation that would fix it is behind the same call. Rebuild Model correctly refuses. The operation that **is** the remedy is `write_script`, which already re-accepts on success — what is missing is a button that reaches it in this state [rec: western-badger-3023].

**Recovery today is by hand**: `open_project restore=false`, then `write_script`. Until a fix lands, every digest-moving change ships with a manual recovery — and digest-moving changes are routine here, because a retained artifact's bytes are part of the project's identity [rec: western-badger-3023] [rec: crisp-glacier-6395].

The fix is known and is a `shell/` diff, which makes it a decision rather than something to slip in: cache the failure code from the last open on the per-root state, and let the chat panel draw the re-accept box it already draws for an orphaned project [rec: western-badger-3023].

## Negative knowledge

- [scope: opening a .blend beside its .cadex | confidence: high | evidence: western-badger-3023] Do not assume a file open hydrates the model. Nothing queues a rebuild on the file-open path, so the viewport is empty until a tool call, a slider drag or Rebuild Model provokes the first request.
- [scope: digest-moving engine changes | confidence: high | evidence: western-badger-3023] Rebuild Model cannot recover a project locked out by a digest change, and it is correct to refuse. The remedy is open_project restore=false then write_script, and no button reaches it — every digest-moving change ships with a manual recovery until that lands.

## Provenance

- western-badger-3023 — the author names this as one of the two most fragile areas, and the two measured failures behind that
- crisp-glacier-6395 — why digest-moving changes are routine here rather than rare
