# The Cadex Engine Inside Mesh

Verified against source: 2026-07-25

Cadex mode builds its model with the **cadex engine** — a headless BREP/CAD
kernel service from the [cadex](../../../cadex) repository — not with
`bpy`. Mesh ships that engine inside its own application bundle so the mode
works with no configuration at all.

This document is the shell-side half of that arrangement. The protocol
itself is specified in cadex's `docs/INTEGRATION.md`; the decisions are
cadex ADR-020 (discovery contract), ADR-022 (why the engine is small
enough to bundle) and ADR-023 (bundling).

## What ships

A payload directory, carried inside the application:

```
macOS    Blender.app/Contents/Resources/cadex/
Linux    <install>/cadex/
Windows  <install>/cadex/
```

with this shape:

```
cadex-engine.json     the discovery manifest
bin/freecadcmd        the engine host; cadexd runs inside it
bin/CadexGeometryWorker
bin/python
lib/                  no Qt GUI, no PySide, no Coin
Mod/cadex/            cadexd and the xscript pipeline
Mod/{Part,PartDesign,Sketcher,Assembly,Mesh,MeshPart,Import,Material,Measure,Show}
```

It is roughly 30 MB of engine plus its runtime, and carries no widget
toolkit: the engine is built with `BUILD_GUI=OFF`. It does carry Qt6Core,
Qt6Xml, Qt6Concurrent and Qt6Network, because FreeCAD's App layer links
them for XML parsing and string handling — non-GUI Qt is unavoidable, Qt
GUI is absent and asserted absent at packaging time.

## Discovery

**Finding `cadex-engine.json` is the whole of discovery.** The manifest
names the binary and the module directory with paths relative to itself:

```json
{
  "schema": "cadex-engine-v1",
  "version": "0.0.2",
  "protocol": "cadex-cadexd-v1",
  "freecadcmd": "bin/freecadcmd",
  "module_dir": "Mod/cadex"
}
```

Nothing guesses at a platform layout. A manifest whose `schema` or
`protocol` this add-on does not recognise is **refused**, not attempted —
a shell that speaks a different protocol version should fail at preflight
with a sentence, not mid-request with a protocol error.

Resolution order (`cadexd_client.find_freecadcmd`):

1. the **Cadex Engine** add-on preference, if set;
2. `MESH_FREECADCMD`;
3. the **bundled payload's manifest**, found relative to
   `bpy.app.binary_path`;
4. `FreeCADCmd` or `freecadcmd` on `PATH`.

`MESH_CADEX_ENGINE` overrides step 3 with a directory of your choosing, and
`MESH_CADEXD_MODULE` overrides the module directory alone.

`cadex_backend.preflight()` returns `(ok, reason, remedy)` and is what the
preferences panel, the chat panel and the first cadex tool call all report
from, so one problem reads as one problem.

## Pointing at a development engine

While working on the engine itself, do not edit
`build_files/cadex_engine.txt`. Either:

```bash
# a payload built from the cadex repo
export MESH_CADEX_ENGINE=/path/to/cadex-engine-0.0.2-macos-arm64

# or a plain cadex build tree
export MESH_FREECADCMD=/path/to/cadex/build/release/bin/FreeCADCmd
```

The second form needs `Mod/cadex` beside the binary's directory or its
parent; both installed layouts are probed.

To run the headless gate against a development engine:

```bash
MESH_FREECADCMD=/path/to/cadex/build/release/bin/FreeCADCmd \
  blender --background --factory-startup \
  --python tests/python/bl_mesh_agent_cadex.py
```

It prints one `CADEX-BLENDER-GATE {...}` line: picking fidelity, slider
latency, restore, cancellation, and whether the engine came from the
bundle.

## The version pin

`build_files/cadex_engine.txt` pins the engine version and a **SHA256 per
platform**. `build_files/utils/fetch_cadex_engine.py` downloads, verifies
and stages it.

A platform whose digest reads `unpinned` is **refused**, not downloaded. A
shipped application bundle is the last place an unverified binary should be
able to reach, so the failure is loud and the fix is explicit: pin the
digest, or pass `--from-local` with a payload you built.

```bash
python build_files/utils/fetch_cadex_engine.py --stage build_darwin/cadex_engine
cmake -S . -B build_darwin -DWITH_CADEX_ENGINE=ON \
      -DCADEX_ENGINE_DIR=$PWD/build_darwin/cadex_engine
cmake --build build_darwin --target install
```

`WITH_CADEX_ENGINE=ON` with nothing staged is a configure-time
`FATAL_ERROR` naming the command to run — a bundle that silently ships
without an engine is worse than one that refuses to configure.

## Upgrading the engine

1. Build and release the payload from the cadex repository
   (`.github/workflows/cadex-engine.yml`); it publishes tarballs and
   `.sha256` files.
2. Update `version` and the per-platform digests in
   `build_files/cadex_engine.txt`.
3. If the wire protocol changed, cadex bumps `protocol` in the manifest and
   `PROTOCOL_SCHEMA` in `cadexd_client.py` must move with it — an
   unrecognised protocol is refused at discovery, so a mismatched pair
   fails at preflight rather than at runtime.
4. Run `tests/python/bl_mesh_agent_cadex.py` against the new payload.

## Open

- **macOS codesigning.** The embedded engine needs hardened-runtime
  entitlements of its own: `freecadcmd` spawns subprocesses and dlopens
  OCCT. Not yet exercised end to end through notarization.
- **Linux and Windows bundles.** The engine payload builds for them; only
  macOS arm64 has shell CI today (`.github/workflows/mesh-build.yml`).
- **Warm-standby worker.** The per-drag `FreeCADCmd --safe-mode` spawn
  still dominates the ~0.55 s slider median; the lever is engine-side.
