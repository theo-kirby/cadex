# The Engine Payload

Verified against source: 2026-07-25

**This repository does not package an application.** Since Phase 7
(ADR-020/023) it packages an *engine payload*: a relocatable directory that
the Blender shell carries inside its own bundle and finds by manifest. The
user installs Mesh; the engine comes with it.

The Qt app packaging — `.app`/DMG, AppImage, `.deb`, the portable 7z and the
NSIS installer, together with `cadex-macos.yml` and
`cadex-windows-installer.yml` — was deleted with the application it packaged
(ADR-021/023). `cadex-release.yml` became `cadex-engine.yml`, with the same
triggers.

## What ships

```
cadex-engine-<version>-<os>-<arch>/
  cadex-engine.json     the discovery manifest
  bin/freecadcmd        the engine host; cadexd runs inside it
  bin/CadexGeometryWorker
  bin/python
  lib/                  Qt6 Core/Xml/Concurrent/Network only
  Mod/cadex/            cadexd + the xscript pipeline
  Mod/{Part,PartDesign,Sketcher,Assembly,Mesh,MeshPart,Import,Material,
       Measure,Show}
```

The manifest is the contract (schema in ADR-020; consumed by the shell):

```json
{
  "schema": "cadex-engine-v1",
  "version": "0.0.2",
  "protocol": "cadex-cadexd-v1",
  "freecadcmd": "bin/freecadcmd",
  "module_dir": "Mod/cadex"
}
```

`freecadcmd` and `module_dir` are **relative to the manifest**, with forward
slashes on every platform. Finding the file is the whole of discovery: no
shell guesses at `<prefix>/Mod/cadex` versus `<dir>/../Mod/cadex` versus a
macOS `.app` interior ever again.

## Building it

```bash
bash package/engine/build_engine_payload.sh [<pixi-env>] [<output-dir>]
```

It relocates the environment (`relocate_conda_environment.py` — a raw copy
would leave the build prefix baked into Mach-O load commands and Python
metadata), prunes to the engine, repairs install names and rpaths on macOS,
writes the manifest, and refuses to finish if a GUI dependency leaked in.

`CADEX_ENGINE_STAGE_ONLY=1` copies without relocation for local
verification. **Not shippable** — the build prefix survives — but enough to
run the gate.

Full relocation requires a rattler-built conda package, where the engine's
own files are package-managed; that path lives in
`.github/workflows/cadex-engine.yml`.

## What is deliberately in the payload

Non-GUI Qt. FreeCAD's App layer links **Qt6Core and Qt6Xml**, and
`FreeCADCmd` inherits that — verifiable with `otool -L`. "Zero Qt" is not
achievable and is not the goal. The goal, and what the build asserts, is:

- no widget toolkit — no `Qt6Gui`, `Qt6Widgets`, `Qt6Quick`, `Qt6Qml`,
  `Qt6OpenGL`, `Qt6Svg`, `Qt6PrintSupport`, `Qt6UiTools`, `Qt6Designer`;
- no Qt Python bindings — no PySide, no shiboken;
- no scene-graph renderer — no Coin, Quarter or SoQt;
- no `libFreeCADGui`, because `BUILD_GUI=OFF` never produces one.

The script *prints* the Qt libraries it does carry, so the exception is
visible rather than assumed.

## The gate: `CadexEnginePayloadSmoke`

```bash
CADEX_ENGINE_ROOT=<payload> pixi run python -m pytest -q \
  src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py
```

Registered as a ctest when `CADEX_ENGINE_ROOT` is set. It runs the **full
cadexd lifecycle** against the packaged tree, discovered through the
manifest exactly as the shell discovers it: open, `describe_api`,
`write_script` with display, `set_params`, `inspect`, `resolve_pin`,
`kill -9`, respawn, restore-digest equality, `rebuild`, mid-run `cancel`,
`shutdown`.

**This gate is not ceremonial.** The first payload it ran against could not
model at all — `No module named 'PySide'`, because
`src/Mod/Assembly/JointObject.py` imported Qt at module scope and the
assembly worker imports that module for its document classes. Every test in
the source tree had passed, because the development environment has Qt
installed. A weaker gate (`freecadcmd --version`, which is what the old
launcher smoke did) would have shipped it.

Rule of thumb: **a source tree that passes proves nothing about a payload.**

## Releasing

`.github/workflows/cadex-engine.yml` runs on a nightly schedule, on manual
dispatch, and on tags matching `v*` or `cadex-*`:

```bash
git tag cadex-2026.07.25
git push origin cadex-2026.07.25
```

It builds the payload per platform, runs the gate, and publishes tarballs
plus `.sha256` files. The digests are the point: the mesh repository pins a
version and a per-platform SHA256 and verifies on fetch.

## Shell side

The mesh repository pins the engine in `build_files/cadex_engine.txt`,
verifies on fetch, refuses an unpinned platform, and installs under
`WITH_CADEX_ENGINE`. See `docs/mesh/CADEX_ENGINE.md` there.

## Open

- **macOS notarization of the embedded engine.** Hardened runtime plus
  per-binary entitlements: `freecadcmd` spawns subprocesses and dlopens
  OCCT. Not yet exercised end to end.
- **Linux and Windows.** The payload builds for both; only macOS arm64 has
  shell CI (`mesh-build.yml` in the mesh repo).
