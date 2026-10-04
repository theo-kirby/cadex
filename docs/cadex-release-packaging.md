# Packaging — The Engine Payload

Verified against source: 2026-10-04

**One repository builds one engine payload** (ADR-030, ADR-498). The
*engine payload* is a relocatable directory the CLI finds by manifest
(`cli/cadex_cli/engine.py`: `--engine`, `CADEX_ENGINE_ROOT`, or the build
tree). The CLI and its dashboard are pure Python under `cli/` and are not
packaged separately. There is no application bundle any more: the Blender
shell that carried the payload inside `Cadex.app` was deleted (ADR-498), and
`v1-blender-shell` is the last tree that builds it.

Three rounds of deletion got here. The Qt app packaging (`.app`/DMG,
AppImage, `.deb`, the portable 7z, the NSIS installer, `cadex-macos.yml`,
`cadex-windows-installer.yml`) went with the application it packaged
(ADR-021/023). The payload's *distribution* machinery — release-tag
publication here, SHA256 pinning and fetching in the shell — went with the
repository boundary it existed to cross (ADR-030). The shell's bundle build,
local install and bundle gate went with the shell (ADR-495, ADR-498). What
is left is the part that was always about the product: one payload,
discovery by manifest, and a gate that runs against the packaged tree.

## What ships

```
cadex-engine-<version>-<os>-<arch>/
  cadex-engine.json     the discovery manifest
  bin/freecadcmd        the engine host; cadexd runs inside it
  bin/CadexGeometryWorker
  bin/python            a real interpreter, not the dangling symlink the
                        payload shipped until M0 caught it
  lib/                  Qt6 Core/Xml/Concurrent/Network/DBus only
  lib/python3.11/site-packages/mujoco/
                        53.5 MB (ADR-075, ADR-076)
  Mod/cadex/            cadexd + the xscript pipeline
  Mod/{Part,PartDesign,Sketcher,Assembly,Mesh,MeshPart,Import,Material,
       Measure,Show}
  LICENSE, NOTICE, THIRD_PARTY_LICENSES.md
                        copied from the repo root (ADR-171)
  licenses/             per-package license texts harvested from the source
                        environment + MANIFEST.json, written by
                        package/engine/collect_licenses.py
```

The manifest is the contract (schema in ADR-020; consumed by the CLI, `cli/cadex_cli/engine.py`):

```json
{
  "schema": "cadex-engine-v1",
  "version": "0.0.1",
  "protocol": "cadex-cadexd-v1",
  "freecadcmd": "bin/freecadcmd",
  "module_dir": "Mod/cadex"
}
```

`freecadcmd` and `module_dir` are **relative to the manifest**, with forward
slashes on every platform. Finding the file is the whole of discovery: no
client guesses at `<prefix>/Mod/cadex` versus `<dir>/../Mod/cadex` versus a
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

**The product version** (ADR-166): `VERSION` at the repo root is the single
source of truth, bumped deliberately with `package/app/bump_version.sh`.
The engine payload is named from `CMakeLists.txt`'s `PACKAGE_VERSION`
instead; the shell bundle that used to stamp `VERSION` into its window title
is gone (ADR-495), so committing a changed `VERSION` is the release act.

## What is deliberately in the payload

**Non-GUI Qt.** FreeCAD's App layer links **Qt6Core and Qt6Xml**, and
`FreeCADCmd` inherits that — verifiable with `otool -L`. The keep list is
five, not four: `qt_keep="Core Xml Concurrent Network DBus"`
(`build_engine_payload.sh:125`). "Zero Qt" is not achievable and is not the
goal. The goal, and what the build asserts, is:

- no widget toolkit — no `Qt6Gui`, `Qt6Widgets`, `Qt6Quick`, `Qt6Qml`,
  `Qt6OpenGL`, `Qt6Svg`, `Qt6PrintSupport`, `Qt6UiTools`, `Qt6Designer`;
- no Qt Python bindings — no PySide, no shiboken;
- no scene-graph renderer — no Coin, Quarter or SoQt;
- no `libFreeCADGui`, because `BUILD_GUI=OFF` never produces one.

The script *prints* the Qt libraries it does carry, so the exception is
visible rather than assumed.

**MuJoCo** (ADR-075, ADR-076). The one deliberate
non-Qt addition, and the only third-party Python package the engine carries:
53.5 MB of `mujoco == 3.10.0`, without which `assembly.dynamics`,
`assembly.mjcf` and `assembly.rollout` do not exist. It reaches the payload
by **two different routes and both have silently dropped it before** — the
relocated path carries it only because `CARRIED_PYPI_PACKAGES` names it in
`package/rattler-build/scripts/relocate_conda_environment.py`, and the
stage-only path only because it copies `lib/` wholesale.

So the build **hard-fails** rather than trusting either
(`build_engine_payload.sh:244`):

```
mujoco_version="$("${payload}/bin/python" -c 'import mujoco; print(mujoco.__version__)' ...)"
[ "${mujoco_version}" = "3.10.0" ] || exit 1
```

Note that it *imports* rather than checking for a directory: a present
package proves nothing about a bundled dylib whose rpath was just rewritten.
That gate earned its keep on its first run by failing — not on mujoco, but
on `bin/python`, which was a **dangling symlink**. A conda `bin/python`
points at `bin/pythonX.Y`, the interpreter was not in the prune's keep list,
and the payload had been shipping a broken link for as long as the prune has
existed. Nothing noticed because nothing ran it: discovery goes through
`cadex-engine.json`, which names `freecadcmd`. ADR-023's rule paying out
exactly as written.

**Known and deferred:** about 30 MB of the 53.5 is `mujoco/experimental/`,
the MuJoCo studio viewer the engine never imports and which
`relocate_macos_runtime_rpaths.py` currently re-signs and re-points for
nothing. Pruning it would take the dynamics cost to roughly 21 MB. It is
worth doing, and it wants its own gate run rather than riding along with
something else (ADR-082 §4, ADR-102 §5).
## What deliberately does *not* ship

The **CLI** (`cli/`, ADR-061). It is a third client of the protocol, not a
part of the engine: it spawns `cadexd` and imports nothing from it but
`CadexdProtocol`, so shipping it inside the payload would put a *consumer*
of the manifest inside the thing the manifest describes. It runs from the
repository, against a built engine or against a staged payload through
`--engine` / `CADEX_ENGINE_ROOT` — which is exactly how the Linux CI job
exercises it, and how anyone can point it at a payload without a checkout of
the engine sources.

Packaging it — a wheel, a `pipx`-installable console script, or a second
tarball beside the engine's — is a real question and an unanswered one. It
is not blocked by anything here; nobody has needed it yet.

## What is accidentally in the payload

Measured 2026-07-25 on `main`, a **staged** payload is **2.3 GB**, and most
of that is not engine:

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

**That measurement predates the dynamics arc.** A staged payload now
measures **2.4 GB** (ADR-076), the difference being MuJoCo's 53.5 MB plus
the wheel's own bundled dylibs. Everything the section says about *why* the
figure is what it is holds unchanged: the 53.5 MB is the only line item in
either payload that is there on purpose.

**Why.** The staged path copies `.pixi/envs/default`, which is a *development*
environment: compilers, LLVM, node, a database client, CMake's documentation.
The prune list in `build_engine_payload.sh` removes the things that would be
embarrassing — Qt GUI, Coin, PySide, headers, unused workbenches — and
nothing else, because it was written to answer "did a widget toolkit leak
in?", not "is this small?".

**LLVM and clang are pruned now (ADR-531).** No ELF in the payload links
`libLLVM*`, `libclang*`, `libLTO`, `libRemarks` or `lib/clang`'s sanitizer
runtimes except each other: they serve Qt's tools, PySide's generator and
the compiler. The script deletes them and the leak gate refuses them. On
2026-10-04 the same tree staged at **3,258,031,078 B** before and
**2,588,443,821 B** after (−669,587,257 B, −20.6%; 40,916 → 40,578 files).
The rest of the development environment (node, perl, opencv, pcl, the
compiler's own `lib/gcc`) is still copied.

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
manifest exactly as the CLI discovers it: open, `describe_api`,
`write_script` with display, `set_params`, `inspect`, `resolve_pin`,
`kill -9`, respawn, restore-digest equality, `rebuild`, mid-run `cancel`,
`shutdown`.

**It is 12 tests, up from 6 at M0**, because every slice of the
dynamics arc added the one thing a source-tree run cannot prove: that the
capability works out of a *packaged* engine. `12 passed` is the expected
result; anything less is a payload problem, not a test problem.

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
  nowhere else**. That is exactly what local verification and the packaged
  gate need, and exactly what a release must not contain.

## Building and releasing

`.github/workflows/cadex-app.yml` runs on a nightly schedule, on manual
dispatch, on `main`, and on tags matching `v*` or `cadex-*`. It has two
engine-only jobs, macOS arm64 and Linux x64. Each sets up and builds the
engine, runs the engine and CLI suites, stages the payload, and gates it
through `test_cadexd_lifecycle` against the *packaged* tree; the Linux job
also drives the packaged engine through the CLI.

**Both jobs have been red since at least 2026-07-25, and neither has ever
reached its gate** (ADR-060). They fail at `Engine unit suite` — `pixi run
python -m pytest src/Mod/cadex/cadex_tests` — with `No module named pytest`,
because `pytest` was not declared in `pixi.toml` until ADR-060, and every
later step is skipped. So the sentence above describes an intent, not an
observation: the packaged gate has never run in CI on either platform, which
is how a payload that broke every assembly joint shipped on both. Verified
locally on Linux; what the macOS gates say when they first run is not yet
known.

## Open

- **macOS notarization of the embedded engine.** Hardened runtime plus
  per-binary entitlements: `freecadcmd` spawns subprocesses and dlopens
  OCCT. Not yet exercised end to end.
- **The first green CI run.** ADR-060 removes the step that stopped every
  run before its gate. Nothing downstream of that step has ever executed on
  either platform, so the next run is the first real report either job has
  made — treat its output as new information, not as a regression.
- **Windows.** The payload builds for it; no CI job gates it.
- **A relocated payload has never been built on this machine.** The
  relocating path needs a rattler build, so every payload verified during
  the merge (ADR-030) was a staged one. The relocation code is unchanged and
  untested by that work.

## What license material ships where

One set, the engine payload's (ADR-171; `docs/PROVENANCE.md` §7). Blender's
license manifest shipped inside the shell's bundle and went with it
(ADR-498).

- **The payload's root** — staged by
  `package/engine/collect_licenses.py` at payload-build time: the root `LICENSE` (LGPL-2.1, FreeCAD's), `NOTICE`
  (MuJoCo, OCCT, OpenTheme, lineage), `THIRD_PARTY_LICENSES.md`, and
  `licenses/` — per-conda-package license texts harvested from the source
  environment (OCCT's LGPL + exception, FreeCAD's own LICENSE.html, the
  mujoco wheel's LICENSE, ~everything share/doc carried before the prune
  deleted it) plus `licenses/MANIFEST.json` (schema `cadex-licenses-v1`),
  the machine-readable per-package inventory of the whole shipped
  environment.

`build_engine_payload.sh` hard-fails if the named obligations are missing
from the staged payload (OCCT exception text, NOTICE, mujoco LICENSE,
MANIFEST), and `test_licensing_compliance.py`'s packaged-gate test
re-checks a staged payload via `CADEX_ENGINE_ROOT`.
