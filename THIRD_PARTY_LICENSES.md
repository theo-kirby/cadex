# THIRD_PARTY_LICENSES.md — the component-level license map

Verified against source: 2026-10-10

What third-party material this repository contains and redistributes, under
which license, and where each obligation is satisfied in the staged
engine payload. `NOTICE` carries the attribution entries; `docs/PROVENANCE.md`
tells the story; this file is the map. Disk is ground truth — the
licensing compliance suite asserts every `src/3rdParty/` directory appears
here.

## 1. The fork

| Tree | Upstream | License | License text |
|---|---|---|---|
| repository root (the engine) | [FreeCAD](https://github.com/FreeCAD/FreeCAD) | LGPL-2.1-or-later | root `LICENSE` (FreeCAD's, unchanged) |

Modified inherited files carry per-file modification notices; the
machine-readable list is `docs/inherited-modifications.json` and the
ledger is `docs/FREECAD.md`. The repository used to carry a second fork,
a Blender-derived shell under GPL-2.0-or-later. It was deleted with its
vendored code and its library submodules (ADR-498); the tag
`v1-blender-shell` is the last tree that has it.

## 2. Vendored source — `src/3rdParty/`

Eleven directories. Where the directory carries no license file, the
license is stated in the source headers and named here — that is the
record for them.

| Directory | License | License file in-tree |
|---|---|---|
| `Clipper2` | BSL-1.0 | `LICENSE` |
| `FastSignals` | MIT | `LICENSE` |
| `json` (nlohmann/json) | MIT | **none** — in-file SPDX tags in both headers |
| `lazy_loader` | Apache-2.0 (TensorFlow-descended, per file header) | **none** — stated in `lazy_loader.py`'s header |
| `libE57Format` | BSL-1.0 | `LICENSE.md` |
| `libkdtree` | Artistic-2.0 | `COPYING` |
| `lru-cache` | MIT | `LICENSE` |
| `OndselSolver` (submodule) | LGPL-2.1 | `LICENSE` |
| `PyCXX` | BSD-3-Clause-style (LLNL/UC Regents) | `CXX/COPYRIGHT` |
| `salomesmesh` | LGPL-2.1 | `LICENCE.lgpl.txt` |
| `zipios++` | LGPL | **none** — trailing per-file notices; some files carry none, which is upstream's state, not ours |

## 3. The shipped conda environment — the engine payload

The engine payload is a **relocated copy of the pixi/conda-forge
environment** (~340 packages, pinned in `pixi.lock`), pruned to the
headless engine. These packages do not stay on the build machine; they
ship inside the payload. The authoritative per-package record — name,
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
PySide/shiboken, Coin3D, LLVM and clang (ADR-531), OpenCV, PCL, Node and
Perl (ADR-532; OpenCV's licence text under `share/licenses/` is left in
place), CalculiX (`ccx`, GPL-2 — development-only,
subprocess-only, never redistributed), and everything in `training/` and
`analysis/`.

## 4. The dashboard's vendored scripts, and fonts

The dashboard (`cli/cadex_cli/review_static/`) is not in the engine
payload; it runs from this repository. It carries two third-party files,
each with its full notice beside it (`docs/PROVENANCE.md`, "Headless review
rendering"):

| File | Upstream | License | License text |
|---|---|---|---|
| `three.module.js` | [three.js](https://github.com/mrdoob/three.js) r160 | MIT | `THREE-LICENSE.txt` |
| `environment.js`, `floor.js` (adapted) | `neural-whoop` studio environment | MIT | `REFERENCE-LICENSE.txt` |

The engine payload carries one font: `NotoSans-Regular-subset.ttf`, a
subset of Noto Sans Regular 2.004 (Copyright 2015 Google LLC, SIL Open Font
License 1.1), installed beside `CadexStudio.py`, which letters every render
and video with it (ADR-568). Its licence text ships beside it as
`NotoSans-OFL.txt`; `docs/PROVENANCE.md` §8j records its source. The
dashboard's pages use the browser's system fonts.

## 5. Where each obligation is satisfied in the payload

| Obligation | Satisfied at |
|---|---|
| Engine LGPL text (FreeCAD lineage) | `LICENSE` |
| Attribution notices (MuJoCo Apache-2.0 §4(d), OCCT, OpenTheme, lineage) | `NOTICE` |
| This component map | `THIRD_PARTY_LICENSES.md` |
| Per-conda-package texts + machine-readable inventory | `licenses/` + `licenses/MANIFEST.json` |
| MuJoCo wheel license | `mujoco-*.dist-info/licenses/` inside the payload, mirrored under `licenses/` |
| Per-file modification notices (LGPL-2.1 §2(a)) | in the modified files themselves; list in `docs/inherited-modifications.json` |
| Complete corresponding source | this public repository |
