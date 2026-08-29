# THIRD_PARTY_LICENSES.md — the component-level license map

Verified against source: 2026-08-29

What third-party material this repository contains and redistributes, under
which license, and where each obligation is satisfied in the shipped
bundle. `NOTICE` carries the attribution entries; `docs/PROVENANCE.md`
tells the story; this file is the map. Disk is ground truth — the
licensing compliance suite asserts every `src/3rdParty/` directory appears
here.

## 1. The two forks

| Tree | Upstream | License | License text |
|---|---|---|---|
| repository root (the engine) | [FreeCAD](https://github.com/FreeCAD/FreeCAD) | LGPL-2.1-or-later | root `LICENSE` (FreeCAD's, unchanged) |
| `shell/` (the shell) | [Blender](https://projects.blender.org/blender/blender) | GPL-2.0-or-later (source); binaries distributed under GPL-3.0-or-later terms | `shell/COPYING` (Blender's, unchanged) |

Modified inherited files in both trees carry per-file modification
notices; the machine-readable list is `docs/inherited-modifications.json`
and the ledgers are `docs/FREECAD.md` and `docs/BLENDER-TREE.md`.

## 2. Vendored source — `src/3rdParty/`

Fourteen directories. Where the directory carries no license file, the
license is stated in the source headers and named here — that is the
record for them.

| Directory | License | License file in-tree |
|---|---|---|
| `3Dconnexion` | LGPL (3DxWare SDK, per file headers) | **none** — the headers reference a `LICENSE` file the partial vendoring did not carry |
| `Clipper2` | BSL-1.0 | `LICENSE` |
| `FastSignals` | MIT | `LICENSE` |
| `GSL` (Microsoft Guidelines Support Library, submodule) | MIT | `LICENSE` + `ThirdPartyNotices.txt` |
| `json` (nlohmann/json) | MIT | **none** — in-file SPDX tags in both headers |
| `lazy_loader` | Apache-2.0 (TensorFlow-descended, per file header) | **none** — stated in `lazy_loader.py`'s header |
| `libE57Format` | BSL-1.0 | `LICENSE.md` |
| `libkdtree` | Artistic-2.0 | `COPYING` |
| `lru-cache` | MIT | `LICENSE` |
| `OndselSolver` (submodule) | LGPL-2.1 | `LICENSE` |
| `OpenGL` | Khronos (MIT-style, per header) | **none** — stated in each header (`api/GL/`) |
| `PyCXX` | BSD-3-Clause-style (LLNL/UC Regents) | `CXX/COPYRIGHT` |
| `salomesmesh` | LGPL-2.1 | `LICENCE.lgpl.txt` |
| `zipios++` | LGPL | **none** — trailing per-file notices; some files carry none, which is upstream's state, not ours |

Blender's vendored third-party code is under `shell/extern/` and is
covered by §4.

## 3. The shipped conda environment — the engine payload

The engine payload is a **relocated copy of the pixi/conda-forge
environment** (~340 packages, pinned in `pixi.lock`), pruned to the
headless engine. These packages do not stay on the build machine; they
ship inside `Cadex.app`. The authoritative per-package record — name,
version, license, and where its text landed — is written at staging time
by `package/engine/collect_licenses.py` into the payload's
`licenses/MANIFEST.json`, with the harvested license texts beside it under
`licenses/<package>/`.

Highlights and elections:

- **OCCT** (`occt`) — LGPL-2.1 **with the OCCT exception**; both texts
  ship under `licenses/occt/`, and the staging script hard-fails without
  them.
- **freetype** — dual-licensed FTL / GPL-2.0; **Cadex elects the FTL**.
- **gmp** — dual-licensed GPL / LGPL-3.0-or-later; **Cadex elects
  LGPL-3.0-or-later**.
- **readline** — GPL-3.0, carried as part of the standard conda Python
  runtime. Flagged as a counsel item in ADR-171 rather than resolved here.
- **mujoco 3.10.0** — Apache-2.0, the one pypi wheel in the payload
  (`docs/PROVENANCE.md` §4). Its wheel LICENSE ships in its dist-info and
  is mirrored under `licenses/`; `NOTICE` carries the attribution.

What is *not* in the payload, by prune or by contract: Qt GUI libraries,
PySide/shiboken, Coin3D, CalculiX (`ccx`, GPL-2 — development-only,
subprocess-only, never redistributed), and everything in `training/` and
`analysis/`.

## 4. The shell's prebuilt libraries and vendored trees

`shell/extern/` (Blender's vendored code) and `shell/lib/<platform>`
(Blender's prebuilt library submodules, never vendored into this tree) are
covered by Blender's own license manifest, which the bundle installs
verbatim at `Cadex.app/Contents/Resources/text/license/` (per-license
texts, `licenses.json`, SPDX identifiers) — the same material every
Blender release ships. Source for the prebuilt libraries is Blender's
public library repositories at `projects.blender.org`.

## 5. Fonts

The fonts the shell ships (interface font, monospace) come from Blender's
`release/datafiles/fonts` and are covered by Blender's license manifest in
§4 (OFL and similar). The engine payload carries no fonts of its own.

## 6. Where each obligation is satisfied in the bundle

| Obligation | Satisfied at |
|---|---|
| Blender GPL text + its third-party licenses | `Contents/Resources/text/license/` (Blender's own manifest, verbatim) |
| Engine LGPL text (FreeCAD lineage) | `Contents/Resources/cadex/LICENSE` |
| Attribution notices (MuJoCo Apache-2.0 §4(d), OCCT, OpenTheme, lineage) | `Contents/Resources/cadex/NOTICE` |
| This component map | `Contents/Resources/cadex/THIRD_PARTY_LICENSES.md` |
| Per-conda-package texts + machine-readable inventory | `Contents/Resources/cadex/licenses/` + `licenses/MANIFEST.json` |
| MuJoCo wheel license | `mujoco-*.dist-info/licenses/` inside the payload, mirrored under `licenses/` |
| Per-file modification notices (LGPL-2.1 §2(a) / GPL-2 §2(a)) | in the modified files themselves; list in `docs/inherited-modifications.json` |
| Complete corresponding source | this public repository, plus Blender's public lib repos for `shell/lib/*` |
