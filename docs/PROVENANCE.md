# PROVENANCE.md — Where Cadex's Code Comes From

Verified against source: 2026-08-29

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
| [MuJoCo](https://github.com/google-deepmind/mujoco) | the **dynamics** kernel — every simulation, MJCF export and policy rollout | Apache-2.0 |
| [FreeCAD](https://github.com/FreeCAD/FreeCAD) | **the engine** — the repository root | LGPL-2.1-or-later |
| [Blender](https://projects.blender.org/blender/blender) | **the shell** — `shell/` | GPL-2.0-or-later |
| VibeCAD (ours, predecessor) | the scripted-modeling engine inside `src/Mod/cadex/` | LGPL-2.1-or-later |

Cadex adds roughly **161,000 lines** of its own across both halves, or about
**100,000** if you do not count tests:

| Ours | Lines | Where |
|---|---|---|
| the engine, Python | 59,981 | `src/Mod/cadex/*.py` |
| the engine's suites | 51,248 | `src/Mod/cadex/cadex_tests/` |
| the engine, C++ | 1,031 | `CadexGeometryWorker.cpp` |
| the shell assistant package | 24,061 | `shell/scripts/startup/mesh_agent/` |
| the shell's Cadex suites | 10,321 | `shell/tests/python/bl_mesh_agent*.py` |
| the headless CLI | 5,065 | `cli/` — a second front end, not a second engine (ADR-061) |
| the offboard trainer | 2,643 | `training/` — **not part of the product** (§5) |
| the offboard analysis | 6,980 | `analysis/` — **not part of the product** (§5) |
| the app template | 99 | `shell/scripts/startup/bl_app_templates_system/Mesh/` |

Everything else in this repository, which is the overwhelming majority of
it, belongs to FreeCAD or Blender. Measured 2026-08-29 (`wc -l` over the
listed globs); these numbers drift as the trees grow, so treat the date as
part of the claim.

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

**What we changed — four groups, about forty-three files.** The delta
against stock Blender is listed in full, file by file, in
[`BLENDER-TREE.md`](BLENDER-TREE.md) §2, in four groups that age
differently: **§2a**, product identity — the default app template, the
engine-bundling CMake, the rename, the bundle's `Info.plist` — which is
eight files of string literals and guarded blocks *and must stay eight*;
**§2b**, the price of owning six Cadex editors and unregistering the ones
we do not ship (ADR-035, ADR-036, ADR-108) — additive rows in enums,
exhaustive switches and CMake lists across ~25 files; **§2c**, the
message-box widget behavior (ADR-034); and **§2d**, the native menu bar and
window chrome (ADR-166). Every file carries a conflict-resolution note in
the ledger and a per-file modification notice in its header, and the full
list is pinned machine-readably by `docs/inherited-modifications.json` and
the licensing compliance suite. An earlier revision of this section claimed
eight files were the *entire* delta; that was §2a's true claim, mis-scoped
to the whole tree.

**What we added.** Three things that exist in no upstream Blender and so can
never conflict with one: the `mesh_agent` package (chat, the parameter panel,
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

## 4. MuJoCo — the dynamics kernel

**What it is here.** MuJoCo is to dynamics what OCCT is to geometry: a kernel
we keep, upstream and unmodified, rather than a tree we fork. `CadexDynamics.py`
translates a Cadex assembly into an `mjSpec`, steps it, and reads the result
back; `assembly.mjcf` writes MJCF by calling **MuJoCo's own writer**
(`MjSpec.to_xml()`) rather than serialising the format ourselves. We fork
FreeCAD and Blender because we intend to replace them. MuJoCo we keep.

**How it reaches a user, and this is the part that matters.** MuJoCo is not
a build dependency that stays behind on the build machine. `mujoco == 3.10.0`
is a **pypi wheel redistributed inside the shipped engine payload**, carried
there by name through `CARRIED_PYPI_PACKAGES` in
`package/rattler-build/scripts/relocate_conda_environment.py` (ADR-076),
because the pixi manifest has not been re-solvable as conda since
conda-forge moved past our `occt == 7.8.1` pin. It is 53.5 MB of the payload,
it ships inside `Cadex.app`, and the payload build hard-fails if it cannot
import exactly that version out of the payload's own interpreter.

That makes it a third category this document did not previously have.
`src/3rdParty/` is vendored source; "build dependencies from conda-forge" stay
on the build machine. A pypi wheel that ships is neither, and it is the one
that carries a redistribution obligation.

**Licence flow.** Apache-2.0 → the engine's LGPL-2.1-**or-later**. The "or
later" is doing the work: Apache-2.0 is incompatible with LGPL-2.1-*only* and
compatible with the v3 family, so the "or later" clause is what makes the
combination clean. On the shell side the same clause does the same work:
the Blender-derived **binary** is distributed under GPL version 3 or later
terms (§7 below) — exactly as Blender's own binaries are, and for the same
reason, Apache-2.0 components in the bundle — while the source stays
GPL-2.0-or-later. **The root `NOTICE` file carries the entry**, and
Apache-2.0 §4(d) means the attribution requirement is real rather than
courteous — see the vendored-LGPL note in `docs/VISION.md`'s non-goals,
which names MuJoCo alongside OCCT. The wheel's own LICENSE ships in the
payload and `package/engine/collect_licenses.py` hard-fails if it does not.

**Version.** Exactly pinned, and for a stated reason rather than caution:
MuJoCo's own `VERSIONING.md` disclaims cross-version numerical
reproducibility, and Cadex asserts content-digest equality on every project
open. A silent MuJoCo upgrade would make existing projects refuse to open.

**Credit.** The physics Cadex simulates is MuJoCo's physics, computed by
MuJoCo's own solver and written out by MuJoCo's own MJCF writer, and it
exists because of the work of the MuJoCo team at Google DeepMind and its
contributors. Cadex is not affiliated with or endorsed by the MuJoCo
project. What Cadex adds is on the other side of the boundary: standard MJCF
authoring guesses inertia from convex hulls or hand-tunes it, and we have the
BREP, so `<inertial>` gets exact `GProp_GProps` mass properties.

## 5. `training/` and `analysis/` — ours, and not part of the product

`training/cadex_train.py` is `[Cadex-new]`, LGPL-2.1-or-later like the rest
of the engine, and **it ships in nothing**. CMake never installs it, no
payload carries it, and it is copied by hand to a machine with a GPU
(ADR-084). Its four dependencies — `jax`, `mujoco`, `mujoco-mjx`, `numpy` —
are pinned in `training/requirements.txt` and installed into a venv on that
machine. None of them is in `pixi.toml`, none is in the payload, and a test
asserts that no `jax` or `mjx` reaches either.

`analysis/` is the second tree under that contract (ADR-141, ADR-142,
ADR-143) and is `[Cadex-new]`, LGPL-2.1-or-later, shipping in nothing on the
same terms. Its dependencies are **still exactly three** — `numpy`, `scipy`,
`mujoco` — pinned in `analysis/requirements.txt` and installed into a venv;
none is in `pixi.toml`, and `test_analysis_stress` asserts that no CMake rule
references the tree and that nothing from it reaches a staged payload. S2
kept that count by writing its own marching tetrahedra rather than taking
`scikit-image` for one function (ADR-143).

It carries one licence rule of its own, and it is the reason this section
now names two directories rather than one. **Nothing under `analysis/` may
import a GPL package**, because the obvious tools for structural work are
the GPL ones — `gmsh`, `pymeshlab`, `mmapy`, `ccx2paraview`, `pygalmesh`,
`pymeshfix`, `tetgen`, JAX-FEM. `mmapy` is the sharpest of those: it is the
standard MMA optimiser, it is what a stress-constrained topology run would
reach for, and it is GPL-3 — which is a large part of why S2 minimises
compliance and leaves stress to a second measurement (ADR-143). A GPL import in a repository-resident,
engine-side file is not a judgement call, so it is a test rather than a
note. **CalculiX is the one GPL tool this repository does use, and it is
used as a subprocess** — `analysis/calculix.py` writes a text deck, runs
`ccx`, and reads a text result; it is never linked and never imported,
which is the same arm's length FreeCAD's own LGPL Fem module kept. `ccx`
comes from conda-forge via `pixi.toml` for development and **is not
redistributed**: `package/engine/build_engine_payload.sh` keeps exactly four
binaries and `ccx` is not one of them.

Both are listed here because a reader auditing what this repository
redistributes should be able to find the directories that look like a
dependency surface and confirm that they are not one.

**What `analysis/` sent in-engine, and what it did not.** ADR-145 added
`src/Mod/cadex/CadexStress.py`, a linear-elastic solve that is `[Cadex-new]`
and LGPL-2.1-or-later like the rest of the engine, and which *does* ship —
CMake installs it and the payload carries it. It costs no new payload
dependency, because `numpy` and `scipy` were already there. It is a **second
implementation** of `analysis/cadex_stress.py`'s numeric core rather than a
copy of it, written that way because `analysis/` may not import the engine
and the engine may not import `analysis/`; a test solves the same benchmark
through both and requires them to agree. Nothing else crossed: topology
optimisation, refinement sweeps, CalculiX and rollout-measured load cases all
stay offboard.

## 6. VibeCAD — the predecessor

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
is in `AGENTS.md`, and [`FREECAD.md`](FREECAD.md) §4 is the do-not-resurrect
list.

## 7. How two licences live in one repository

The engine is LGPL-2.1-or-later; the shell is GPL-2.0-or-later. They are
**separate programs communicating over a documented protocol**, not one
program linked together:

- The engine is a set of processes (`cadexd`, and `FreeCADCmd` workers
  beneath it) that speak NDJSON over stdin/stdout.
- The shell assistant package speaks that protocol through a dependency-free client
  (`cadexd_client.py`) which imports **no cadex code whatsoever**. That rule
  is enforced as a licence boundary, not as a style preference, and merging
  the two repositories into one did not relax it (see
  [`BLENDER.md`](BLENDER.md)).
- The protocol is pinned by tests on both the request and the response side
  (`docs/INTEGRATION.md`, ADR-027), which is also what keeps either half
  replaceable.
- `cli/` is a **third** client of that protocol (ADR-061,
  [`CLI.md`](CLI.md)) and is on the engine's side of the line:
  LGPL-2.1-or-later, like everything else we wrote outside `shell/`. The
  boundary runs one way and is not a judgement call — the shell's
  `cadexd_client.py`, `backend.py`, `mcp_shim.py` and `modes.py` solve four
  of the same problems and **not one line of them is copied there**. They
  were read as reference; every equivalent derives from the LGPL
  engine-side precedents in `src/Mod/cadex/cadex_tests/`, and the system
  prompt is written fresh.

The shipped bundle distributes both halves side by side, and the right
frame for it is **aggregation**: each component stays under its own
licence, because putting separate programs in one archive does not
relicense any of them. The Blender-derived binary in the bundle is
distributed under GPL version 3 or later terms (the GPL-2.0-or-later
source's "or later", elected the same way Blender's own releases elect it,
because Apache-2.0 components require it); the engine payload beside it
stays LGPL-2.1-or-later; the MuJoCo wheel inside that stays Apache-2.0.
The complete corresponding source for all of it is this public repository,
plus Blender's public library repositories for the prebuilt
`shell/lib/<platform>` submodules. The licence material itself ships in
two places: Blender's own `Resources/text/license/` for the shell binary,
and `Resources/cadex/` — `LICENSE`, `NOTICE`, `THIRD_PARTY_LICENSES.md`
and a per-package `licenses/` directory with `MANIFEST.json` — for the
engine payload. This is a description of how the repository is structured,
not legal advice; if you are redistributing Cadex, read the licences.

## 8. Everything else

- **Bundled third-party code** lives in `src/3rdParty/` (Clipper2, PyCXX,
  salomesmesh, libE57Format, OndselSolver, GSL and others) and in Blender's
  `shell/extern/`. Most keep their own licence file in-tree; the ones that
  do not are named, with their licences, in
  [`THIRD_PARTY_LICENSES.md`](../THIRD_PARTY_LICENSES.md) §2. The licence
  texts Blender ships are in `shell/doc/license/`.
- **Prebuilt libraries** for the shell come from Blender's own
  `projects.blender.org` library repositories, consumed as submodules under
  `shell/lib/<platform>`. They are never vendored into this tree.
- **Runtime dependencies from conda-forge** (OCCT, Python, numpy/scipy and
  ~330 more, pinned in `pixi.lock`) **do not stay on the build machine —
  they are the payload.** The engine payload is a relocated copy of the
  pixi environment, so every conda package that survives the prune ships
  inside `Cadex.app`. An earlier revision of this bullet claimed the
  opposite. What each shipped package's licence is, and where its text
  landed, is recorded per-package in the payload's
  `licenses/MANIFEST.json`, written by `package/engine/collect_licenses.py`
  at staging time.
- **The one pypi wheel that ships** is `mujoco == 3.10.0` —
  §4. It is neither vendored source nor a build-only dependency, which is why
  it has a section of its own rather than a bullet here.
- **The CadexLight, CadexDark and CadexMono themes** are based on
  [OpenTheme by Obelisk79](https://github.com/obelisk79/OpenTheme)
  (LGPL-2.1); the derived `.qss` files say so in their headers, and NOTICE
  carries the entry.

## 9. Where this goes

ADR-025 and ADR-030 record the intended endpoint: **one application we
own** — a derivative of, but not dependent on, either FreeCAD or Blender.
OCCT stays as the geometry kernel. The FreeCAD application layer would be
replaced by our own binding (Phase 11) and the Blender shell by our own
renderer (Phase 12), both behind the unchanged cadexd protocol.

Neither is scheduled, and neither blocks anything. Until then this document
describes the truth: Cadex is two forks, an assistant package, and about forty thousand
lines of our own, and the parts that are not ours are the parts that make it
work.
