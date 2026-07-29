# PROVENANCE.md — Where Cadex's Code Comes From

Verified against source: 2026-07-28

Cadex is not written from scratch. It is a **derivative work of two large
free-software projects**, carrying the design lessons of a third that we
built and then tore down. This document says exactly which code came from
where, under which licence, and what we changed — because a fork that cannot
answer that question honestly is not a project, it is a pile.

It is the outward-facing companion to the two inherited-tree ledgers,
which carry the same story in operational detail:
[`FREECAD.md`](FREECAD.md) for the engine, [`BLENDER-TREE.md`](BLENDER-TREE.md)
for the shell.

## 1. The short version

| Source | What it became | Licence |
|---|---|---|
| [OCCT](https://dev.opencascade.org/) | the geometry kernel — every solid, boolean, and fillet | LGPL-2.1 with an exception |
| [FreeCAD](https://github.com/FreeCAD/FreeCAD) | **the engine** — the repository root | LGPL-2.1-or-later |
| [Blender](https://projects.blender.org/blender/blender) | **the shell** — `shell/` | GPL-2.0-or-later |
| VibeCAD (ours, predecessor) | the scripted-modeling engine inside `src/Mod/cadex/` | LGPL-2.1-or-later |

Cadex adds roughly **40,000 lines** of its own across both halves —
~33,700 in the engine (`src/Mod/cadex/`), ~4,600 in the shell add-on
(`mesh_agent/`), ~1,800 in the app template and the shell's Cadex test
suites. Everything else in this repository, which is the overwhelming
majority of it, belongs to FreeCAD or Blender.

We do not track either upstream. Both were imported as squashed snapshots,
and the direction of travel is **subtractive**: we delete from these trees
rather than merge from them. That is a deliberate trade — we give up
upstream fixes to gain a tree we can actually finish removing.

## 2. FreeCAD — the engine

**What it is here.** The repository root *is* a FreeCAD fork. The engine
uses FreeCAD as an application framework and a set of geometry workbenches:
`App::Document` and its transaction machinery, the properties and expression
system, the units and math primitives in `Base`, and the `FreeCADCmd` entry
point that every sandboxed xscript worker runs as a subprocess.

**What we kept, and why.** Four capability workbenches back the four CAD
domains — `Part` (direct OCCT shapes and booleans), `PartDesign` (bodies and
sketch-based features), `Sketcher` (the planegcs constraint solver),
`Assembly` (links, joints, the Ondsel solver) — plus `Mesh`/`MeshPart` for
the mesh domain and `Import` for STEP/IGES exchange. The full keep list,
with reasons, is [`FREECAD.md`](FREECAD.md) §1.

**What we removed.** A great deal, under a two-commit protocol (disable and
verify; delete and verify) with an ADR for each: unused workbenches in Phase
1, and the entire Qt/Coin3D GUI in Phase 7 — `BUILD_GUI=OFF` means the
shipped engine compiles not one line of `src/Gui`, and the shipped binaries
are `FreeCADCmd` and `CadexGeometryWorker` with no FreeCAD application at
all. The engine payload installs an explicit keep-list of modules; the Addon
Manager, Web, Start, Test, and Help modules are not on it.

**Version.** A snapshot of the FreeCAD 1.2 development line. `version.json`
was re-versioned to Cadex's own `0.0.1` and no longer states a FreeCAD
version; the inherited `SECURITY.md` we replaced named `1.2dev` as the then
current development series. The `OndselSolver` and `GSL` submodules still
point at their upstream repositories.

**Licence.** LGPL-2.1-or-later. The root [`LICENSE`](../LICENSE) is
FreeCAD's, unchanged, and every file we wrote under `src/Mod/cadex/` carries
`SPDX-License-Identifier: LGPL-2.1-or-later`.

**Credit.** The geometry Cadex produces is FreeCAD's geometry, computed by
FreeCAD's code over OCCT, and it exists because of the work of the
[FreeCAD community](https://forum.freecad.org/) over two decades. Cadex is
not affiliated with or endorsed by the FreeCAD project, and problems in
Cadex are not FreeCAD's to answer for — see [`SECURITY.md`](../SECURITY.md)
for where to report what.

## 3. Blender — the shell

**What it is here.** `shell/` is a Blender fork, and it is the product's
user interface: the window manager, the editors, the GPU layer, DNA/RNA,
BMesh, and the `.blend` file format. When you run Cadex you are running this
tree.

**Provenance.** Imported 2026-07-25 as a squashed snapshot of our own `mesh`
repository at `ac5af55948d`, which was itself a Blender fork — Blender 5.3
alpha. Blender's 163,789-commit history stayed behind, deliberately.

**What we changed — eight files, in seven changes.** That is the entire delta
against stock Blender, and keeping it that short is why the shell was cheap
to absorb.
The changes are: a default app template so a new user meets the Cadex
layout, and the `read_userdef` line that makes that default reach an
existing profile too (ADR-058); two CMake additions that bundle the engine;
the product rename (`Blender.app` → `Cadex.app`, and the window title); and
the macOS bundle's `Info.plist` identity. Every one is listed in
[`BLENDER-TREE.md`](BLENDER-TREE.md) §2 with a conflict-resolution note,
because each is a future merge conflict and we would rather write down how
to resolve it now.

**What we added.** Three things that exist in no upstream Blender and so can
never conflict with one: the `mesh_agent` add-on (chat, the parameter panel,
the cadexd protocol client, hydration, picking), the `Mesh` app template
that suppresses Blender's default UI, and the Cadex test suites.

**What we plan to remove.** Phase 13b: Cycles and other subsystems that a
CAD shell does not need, each behind a `WITH_*` option that makes the
disable half of the removal protocol nearly free.

**Licence.** GPL-2.0-or-later. Blender's own `shell/COPYING` is present and
unchanged; every file we wrote under `mesh_agent/` carries
`SPDX-License-Identifier: GPL-2.0-or-later`, as the GPL requires of work
that links into the tree.

**Credit.** The interface Cadex presents — viewport, navigation, tools,
theming, file format — is Blender's, built by the Blender Foundation and its
contributors. Cadex is not affiliated with or endorsed by the Blender
project, is not a Blender add-on distribution, and should not be mistaken
for either.

## 4. VibeCAD — the predecessor

Cadex's relationship to VibeCAD is not inspiration. It is **descent**:
`src/Mod/cadex/` was imported wholesale from the `cadex-teardown` branch of
our own VibeCAD repository, and much of the engine still carries the
`[VibeCAD-era]` provenance tag in [`ARCHITECTURE.md`](ARCHITECTURE.md) for
exactly that reason. The scripted runtime, the sandboxed process runner, the
domain API/worker pairs, the publication transaction, and the C++ geometry
validation worker were all written there.

**What VibeCAD was.** A FreeCAD fork with a Qt shell, a multi-provider AI
stack (API keys, model pickers, an in-app provider settings page), several
geometry engines side by side — build123d, OpenSCAD, native per-workbench
tool packs — and eighteen scripted domains.

**What we learned by deleting it.** Every one of those choices was removed,
and the removals are the design of Cadex:

- **One engine, not four.** build123d, OpenSCAD and the native tool packs
  went; xscript is the only modeling surface. Multi-engine multiplied
  validation, documentation, and prompt complexity without product value
  (ADR-001).
- **Four domains, not eighteen.** Then five, when a minimal mesh domain
  earned its place (ADR-016).
- **One script, not eight lifecycle calls per domain.** The per-domain
  multi-program surface became a single project script (ADR-011, ADR-013).
- **No provider stack.** The Qt shell and the whole API-key model loop were
  deleted (ADR-021); the AI is now the Claude Code CLI, running under the
  user's own login. The screenshot of a provider settings page in
  `docs/images/` is a photograph of something that no longer exists.
- **No GUI in the engine.** The engine became headless; the shell became a
  separate process across a protocol (ADR-017, ADR-018, ADR-022).

The `cadex-teardown` branch at `github.com/theo-kirby/vibecad` holds that
six-phase history. Nothing deleted there returns without an ADR — that rule
is in `CLAUDE.md`, and [`FREECAD.md`](FREECAD.md) §4 is the do-not-resurrect
list.

## 5. How two licences live in one repository

The engine is LGPL-2.1-or-later; the shell is GPL-2.0-or-later. They are
**separate programs communicating over a documented protocol**, not one
program linked together:

- The engine is a set of processes (`cadexd`, and `FreeCADCmd` workers
  beneath it) that speak NDJSON over stdin/stdout.
- The shell add-on speaks that protocol through a dependency-free client
  (`cadexd_client.py`) which imports **no cadex code whatsoever**. That rule
  is enforced as a licence boundary, not as a style preference, and merging
  the two repositories into one did not relax it (see
  [`BLENDER.md`](BLENDER.md)).
- The protocol is pinned by tests on both the request and the response side
  (`docs/INTEGRATION.md`, ADR-027), which is also what keeps either half
  replaceable.

The shipped bundle distributes both, so the distribution as a whole carries
GPL-2.0-or-later obligations, and the complete corresponding source is this
public repository. This is a description of how the repository is
structured, not legal advice; if you are redistributing Cadex, read the
licences.

## 6. Everything else

- **Bundled third-party code** lives in `src/3rdParty/` (Clipper2, PyCXX,
  salomesmesh, libE57Format, OndselSolver, GSL and others) and in Blender's
  `shell/extern/`. Each keeps its own licence file; the licence texts
  Blender ships are in `shell/doc/license/`.
- **Prebuilt libraries** for the shell come from Blender's own
  `projects.blender.org` library repositories, consumed as submodules under
  `shell/lib/<platform>`. They are never vendored into this tree.
- **Build dependencies** for the engine (OCCT, Qt6, Coin3D, compilers) come
  from conda-forge through pixi, pinned in `pixi.lock`.
- **The CadexLight and CadexDark themes** are based on
  [OpenTheme by Obelisk79](https://github.com/obelisk79/OpenTheme).

## 7. Where this goes

ADR-025 and ADR-030 record the intended endpoint: **one application we
own** — a derivative of, but not dependent on, either FreeCAD or Blender.
OCCT stays as the geometry kernel. The FreeCAD application layer would be
replaced by our own binding (Phase 11) and the Blender shell by our own
renderer (Phase 12), both behind the unchanged cadexd protocol.

Neither is scheduled, and neither blocks anything. Until then this document
describes the truth: Cadex is two forks, an add-on, and about forty thousand
lines of our own, and the parts that are not ours are the parts that make it
work.
