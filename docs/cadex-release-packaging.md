# Packaging — One Bundle

Verified against source: 2026-07-28

**One repository builds one application** (ADR-030). `pixi run app` produces
the bundle, and the *engine payload* — a relocatable directory the shell
carries inside that bundle and finds by manifest — is now an intermediate
artifact of the same build rather than a release the shell downloads.

Two rounds of deletion got here. The Qt app packaging (`.app`/DMG, AppImage,
`.deb`, the portable 7z, the NSIS installer, `cadex-macos.yml`,
`cadex-windows-installer.yml`) went with the application it packaged
(ADR-021/023). The payload's *distribution* machinery — release-tag
publication here, SHA256 pinning and fetching in the shell — went with the
repository boundary it existed to cross (ADR-030). What is left is the part
that was always about the product: one bundle, discovery by manifest, and a
gate that runs against the packaged tree.

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
own files are package-managed — see "Staged, or relocated" below.

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

## What is accidentally in the payload

Measured 2026-07-25, a **staged** payload is **2.3 GB**, and most of that is
not engine:

```
lib/       2.2 GB     of which  python3.11  856 MB
                                libLLVM.21.1  134 MB
                                libLLVM.18.1  116 MB   (two LLVMs)
                                libnode.137    72 MB
                                libclang-cpp   69 MB
share/     171 MB     gir-1.0 27 MB · locale 26 MB · cmake-4.2 22 MB
                      icons 15 MB · mysql 11 MB
Mod/       4.4 MB     the workbenches the domains actually load
bin/       452 KB     freecadcmd, CadexGeometryWorker, python
```

**Why.** The staged path copies `.pixi/envs/default`, which is a *development*
environment: compilers, LLVM, node, a database client, CMake's documentation.
The prune list in `build_engine_payload.sh` removes the things that would be
embarrassing — Qt GUI, Coin, PySide, headers, unused workbenches — and
nothing else, because it was written to answer "did a widget toolkit leak
in?", not "is this small?".

Two honest consequences:

- The **"no GUI" gate is narrower than it reads.** It greps for `*Gui.so`
  under `Mod/` and `libFreeCADGui*` under `lib/`, so stale
  `lib/FreeCADGui.so`, `FemGui.so` and `InspectionGui.so` left in the pixi
  env by older installs are copied and pass. Pre-existing, unrelated to any
  recent work, and on the Phase 13b list.
- **A release payload has never been measured.** Relocation builds from a
  rattler package environment, which would not contain the toolchain at all,
  so the shipped size is probably far smaller — but that path has not been
  run here (see "Staged, or relocated"), so this is reasoning, not a
  measurement, and should not be quoted as one.

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

## Staged, or relocated

`package/engine/build_engine_payload.sh` has two modes and the difference is
not a quality setting.

- **Relocated** (`pixi run stage-engine-release`, the default path of the
  script) rewrites Mach-O load commands and Python metadata using conda's
  package manifests. It only works when the engine's own files are
  package-managed — i.e. inside a rattler build. Against a `cmake
  --install`ed development environment it fails outright with *"the
  package-managed environment is incomplete"*. This is what a release ships.
- **Staged** (`pixi run stage-engine`, `CADEX_ENGINE_STAGE_ONLY=1`) copies
  the environment without relocating. The build prefix stays baked into load
  commands, so the result is correct **on the machine that built it and
  nowhere else**. That is exactly what `pixi run app` needs and exactly what
  a release must not contain.

`pixi run app` uses the staged path deliberately: a developer bundle that
runs here is the goal, and the honest alternative — requiring a rattler
build before you can launch the app you just edited — is not a build loop
anyone would use.

## Installing it locally

```bash
pixi run install-app      # build, then copy the bundle to /Applications
pixi run uninstall-app    # remove it
```

`install-app` rsyncs `shell/build_darwin/bin/Cadex.app` to
`/Applications/Cadex.app` (override with `CADEX_INSTALL_DIR`) and pokes
Launch Services so Spotlight, Launchpad and the Dock see it immediately. It
refuses to `--delete` into a destination that is not an application bundle.
Re-running it after a rebuild is incremental.

**This is a local install of a staged payload, and that is a real
limitation.** Every Mach-O under `Contents/Resources/cadex` carries exactly
two rpaths, both absolute into the repository:

```
/Users/<you>/cadex/.pixi/envs/default/lib
/Users/<you>/cadex/build/release/lib
```

The bundle *carries* its own `lib/` and never looks at it. So the installed
app reads its libraries out of the source tree: move or delete the repo and
Cadex launches and then fails to model. The command prints this every time.
Making the installed bundle standalone is the relocation + notarization work
under "Open" below, not a flag on this command.

A double-clicked bundle starts in the Cadex layout because
`UserDef::app_template` defaults to `"Mesh"` (ADR-024) and `read_userdef`
resets to that default rather than to the empty string (ADR-058). Finder
cannot pass `--app-template`, so this is what makes an installed app the
product rather than stock Blender.

## Building and releasing

`.github/workflows/cadex-app.yml` runs on a nightly schedule, on manual
dispatch, on `main`, and on tags matching `v*` or `cadex-*`. Its `app` job
builds the engine, stages the payload, gates it through
`test_cadexd_lifecycle` against the *packaged* tree, builds the shell with
the payload installed, checks that `cadex-engine.json` really is inside the
bundle, and runs the agent suites and `CADEX-BLENDER-GATE` out of it with
every `MESH_*` variable unset. The artifact is the application.

The `engine` job builds and gates the engine on Linux. We do not build a
Linux shell yet; keeping that job is a decision, not an oversight.

## Open

- **macOS notarization of the embedded engine.** Hardened runtime plus
  per-binary entitlements: `freecadcmd` spawns subprocesses and dlopens
  OCCT. Not yet exercised end to end.
- **Linux and Windows.** The payload builds for both; only macOS arm64
  builds a shell bundle, in CI or anywhere else.
- **A relocated payload has never been built on this machine.** The
  relocating path needs a rattler build, so every payload verified during
  the merge (ADR-030) was a staged one. The relocation code is unchanged and
  untested by that work.
