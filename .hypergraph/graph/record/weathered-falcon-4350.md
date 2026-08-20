---
node_id: 5050e6d8-02dc-5e41-a9e4-9ee5adbd42ea
slug: weathered-falcon-4350
title: 'ADR-155: Save-As lost its source-root hint to the next ordinary save'
created_at: '2026-08-20T16:47:15+00:00'
parents:
- ancient-current-9419
summary: ''
---
## What

A third measured failure in the file-lifecycle area, diagnosed from a real damaged
model and fixed: **Save-As lost the pointer back to the original project on the
first ordinary save afterwards**, so "Rebuild From Saved Script" carried no imported
geometry across and said nothing about it. ADR-155.

## Why

The user reported that `actuator-v9` refused to rebuild from its script after a
Save-As. The obvious reading — the ADR-046 asset carry is broken — turned out to be
wrong, and the real cause was one line up: the *hint* the carry reads had been
overwritten before the carry ever ran.

This is the same node as the `ancient-current-9419` negative-knowledge line about
Save-As and project assets, but a different mechanism. That one is about the shell's
suffix list dropping an asset **type**. This one drops **every** asset, of every
type, whenever the user pressed Ctrl-S between the Save-As and the rebuild — which
is the common order, because saving is what a person does after a Save-As.

## Method

Diagnosis, on the live project at `~/arch/actuator-v9.cadex` (read-only; every probe
ran on copies in a scratch directory):

- `script.py` 0 bytes, `accepted_digest` `""`, `latest_candidate.status` `failed`:
  `api.import_file: no staged mesh asset named 'esp32.stl' exists.`
- `assets/` held one of the two STLs the script imports. Siblings `actuator-v5/v6/v7`
  all held both, so the model itself was fine and the copy was not.
- The three attempt directories in the artifact trail told the sequence: attempts 1
  and 2 staged **no** assets and failed on the first import; attempt 3 staged one and
  failed on the second. One file per press — the shape of a user importing whatever
  the last error named, not of a carry running.

Ruling the engine out:

- `store_project_asset` accepts `esp32.stl` directly (4,157,751 bytes against a
  128 MiB budget) — stored fine.
- Two sequential `put_asset` calls over real NDJSON to `cadexd` — both `ok`.
- `migrate_assets` run headless in the shipped bundle against the same two files —
  `"Carried 2 imported file(s)"`. The carry loop was never at fault.

Finding it: `adopt_saved_script` on a scratch copy of `actuator-v9.blend`
reproduced the failure exactly, and printed `source_root` = the project's *own*
root. Reading `SOURCE_PROP` out of the decompressed .blend files confirmed it:

| file | stored hint |
|---|---|
| `actuator-v7.blend` | `…/actuator-v7.cadex` |
| `actuator-v9.blend` | `…/actuator-v9.cadex` ← must be v7 |
| `actuator-v9.blend1` (previous save) | `…/actuator-v9.cadex` |

`remember_source_root` ran on every `save_pre`, not only on Save-As. The Save-As
itself wrote the correct hint; the next ordinary save overwrote it with the file's
own root, because by then `bpy.data.filepath` already named the new file.
`source_root` rejects a candidate equal to the current root, `open_roots()` is empty
in a fresh session, so it returned `""` — and `migrate_assets` returned `(True, "")`
and let `write_script` die on the first import.

The fix, three parts:

- `remember_source_root(scene, filepath)` writes only when
  `destination_root(scene, filepath) != project_root(scene)`. `wm_files.cc` passes
  `save_pre` the destination path (and `""` for the startup file), so "does the root
  move" is answerable before the write. `destination_root` mirrors `project_root`'s
  derivation, explicit `ROOT_PROP` override included.
- `migrate_assets` returns a report instead of silence when it found nowhere to
  carry from, distinguishing a stale/empty source from the self-pointing hint a
  .blend damaged by the old handler carries.
- `test_save_as_carries_imported_geometry` now uses **two** assets (one could not
  distinguish a carry that stops after the first) and does an ordinary
  `save_mainfile()` between the Save-As and the adopt.

## Result

`pixi run gate` exit 0. `pixi run test-engine` 1869 passed, 33 skipped — no engine
file moved.

The regression test is load-bearing, checked by restoring the old unconditional
handler and re-running: **6 checks fail**, starting at `an ordinary save does NOT
overwrite that memory with its own root`, and the adopt failure carries the new
message — `No imported files came across: this file records its own project as their
source, so the original is not named anywhere in it.` With the fix, the report reads
`Carried 2 imported file(s) over from asset-orig.cadex: bracket.stl, widget.stl.`

Verified the recovery end to end on a scratch copy of the real model: with both
assets present, `adopt_saved_script` returns ok, **16 outputs accepted**, `script.py`
back to 34,558 bytes.

**What this does not fix.** A .blend already damaged by the old handler cannot be
repaired from inside itself — the imported files are wherever the original project
is, and nothing in the file names it any more. That case now gets a sentence saying
so instead of silence. `actuator-v9.blend` is in exactly this state and needs its
two STLs imported by hand once.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: db0c5fa4689f11da8208383f6eb256767ab2600f

## State Impact

- target: simple-willow-8989 — A third measured failure in this area, found and fixed (ADR-155). save_pre recorded the Save-As source-root hint on EVERY write, so the first ordinary Ctrl-S after a Save-As overwrote the pointer to the original project with the file's own root; source_root then rejected it for being current, migrate_assets carried nothing and returned (True, ""), and the rebuild died on the first mesh.import_file. remember_source_root now writes only when destination_root differs from project_root, and migrate_assets reports when it found nowhere to carry from. New negative knowledge, scope 'Save-As followed by an ordinary save', confidence high: a .blend damaged by the pre-ADR-155 handler records its own root as the source and CANNOT be repaired from inside itself -- the imported files must be re-imported by hand. Status stays broken: the two failures already on this node (nothing hydrates on open; the digest lockout with no button back) are untouched.
