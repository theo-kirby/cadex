# PROVENANCE.md — Where Cadex's Code Comes From

Verified against source: 2026-09-07

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
current development series. The `OndselSolver` submodule still points at its upstream repository.
The unused Microsoft GSL submodule was removed after Start (ADR-222).

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

**Optional geometry runtime (ADR-185).** The same Blender binary can now
evaluate native xscript mesh recipes in a separate OS-sandboxed process.
`src/Mod/cadex/cadex_blender_runner.py` and `cadex_blender_worker.py` are newly,
independently authored LGPL adapters; no shell implementation was copied into
them. The latter imports bpy only when executed by Blender. No Blender
library is imported into cadexd, the FreeCAD worker, or the headless CLI.
The Blender binary retains its existing GPL attribution and licensing.

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

**What we remove.** Phase 13b: subsystems a CAD shell does not need, each
behind a `WITH_*` option that makes the disable half of the removal
protocol nearly free. Cycles was the first through both halves
(ADR-196, 2026-09-06): `shell/intern/cycles` is gone from the tree, and
its licence material with it — nothing of ours derived from it.

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
  salomesmesh, libE57Format, OndselSolver and others) and in Blender's
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

## 8a. Catalog board data `[Cadex-new, ADR-202]`

The L2 recipes are independently authored LGPL Cadex code. Numerical
interface facts and pin labels are transcribed from the sources below,
checked 2026-09-06. No vendor PCB layout, artwork, STEP model, schematic or
software is redistributed. PCB axes match XSCRIPT's lower-left datum.

- **Espressif ESP32-DevKitC V4, WROOM-32E:** the manufacturer's
  [dimension drawing](https://dl.espressif.com/dl/schematics/esp32_devkitc_v4_dimensions.pdf)
  specifies the PCB and header pitch/offsets, including the module overhang;
  the [V4 user guide's J2/J3 tables](https://documentation.espressif.com/esp-dev-kits/en/latest/esp32/esp32-devkitc/user_guide.html)
  supply all 38 pin labels. The two 19-pin rows are electrical interfaces,
  not mounting holes. Nominal 1 mm terminal bores, 1.6 mm PCB thickness,
  module-marker dimensions/position and density are approximate. The guide
  identifies flash-reserved pins and module-dependent GPIO16/17; a pin
  label is not a promise that the pin is free for a peripheral.
- **Raspberry Pi Zero 2 W:** the manufacturer's
  [mechanical drawing](https://datasheets.raspberrypi.com/rpizero2/raspberry-pi-zero-2-w-mechanical-drawing.pdf)
  supplies the PCB outline bounds and four mounting-hole centres. The
  [official standard 40-pin header drawing, figure 3](https://datasheets.raspberrypi.com/rpi4/raspberry-pi-4-datasheet.pdf)
  supplies the GPIO labels (including ID_SD/ID_SC, reserved for HAT EEPROM).
  GPIO terminal positions are nominal: a 2.54 mm grid starting at
  (8.37, 25.23), estimated from the Zero drawing, not dimensioned there.
  Mounting bores of 2.75 mm, terminal bores of 1 mm, 1.6 mm thickness,
  chip-marker dimensions/position and density are also approximate.
- **Adafruit 815 PCA9685 revision C:** dimensions, mounting bores and
  electrical pad coordinates come from the manufacturer's
  [revision C board at commit 32578c83](https://github.com/adafruit/Adafruit-16-Channel-PWM-Servo-Driver-PCB/blob/32578c83a5ba2946249b80b1aa1fb18ae4e61e7d/Adafruit%20PCA9685%20rev%20C.brd),
  reached via its [downloads page](https://learn.adafruit.com/16-channel-pwm-servo-driver/downloads).
  Translate the board coordinates by (+1.905, +6.477) to reach the catalog
  datum; mounting pads become a 55.88 by 19.05 mm pattern. JP3/JP4 are
  the I2C/power headers, the four servo blocks carry all 16 channels, and
  J1 is the power-input footprint. V+_IN precedes the reverse-polarity
  protection; the other V+ pads are the protected rail. Nominal 1.6 mm
  thickness, chip-marker dimensions/position and density are approximate.
  The source hardware design is by Limor Fried/Ladyada for Adafruit
  Industries, published under CC BY-SA; it remains upstream, not vendored.

All three replace rounded board outlines with rectangular bounds and omit
connector bodies, detailed components, traces and silkscreen. The body is
an interface model, not an enclosure-clearance certification or a measured
mass model. `spec["approximate"]` lists the numeric assumptions; this
paragraph records the geometric omissions.

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


## 8b. Catalog N20 gearmotor data `[Cadex-new, ADR-205]`

Independently authored LGPL envelope for **Pololu #2367**, 100:1 MP 6 V,
no encoder or extended rear shaft. Sources read 2026-09-06:

- [Pololu specifications](https://www.pololu.com/product/2367/specs): 9.5 g;
  at 6 V, 220 RPM (±20%) and 70 mA (±50%) no-load; extrapolated stall
  0.67 A and 0.94 kg·cm, converted with 98.0665 N·mm per kg·cm. Stall is
  not a continuous operating point and can damage the motor/gearbox.
- [Product details](https://www.pololu.com/product/2367): exact reduction
  (35×37×35×38)/(12×11×13×10). No continuous torque rating is inferred.
- [Dimension drawing 0J949](https://www.pololu.com/file/0J949/micro-metal-gearmotors-dimensions.pdf),
  page 4, dated 2024-04-03 (precious metal brushes, no encoder): 12×10 mm
  cross section, gearbox L=9 mm, rear OL maximum 25.6 mm, shaft tip 10 mm
  forward of face, diameter 3 mm, flat-to-opposite 2.5 mm, boss diameter
  4 mm and height 0.7 mm; M1.6 centres at ±4.5 mm.

The web table says 25 mm body length; its footnote says 26 mm. Use the
more explicit drawing's 25.6 mm maximum for the rear envelope. The 9 mm
usable D length comes from the product description; its start at Z=1 mm
and sharp axial transition are simplifications. A solid rectangular rear
box fills gears and terminals, and omits corner radii; this is an external
space reservation, not internal geometry, density or inertia. Thread major
diameter bores have an assumed 1 mm depth (not a screw engagement limit).
No STEP, drawing artwork or third-party code is copied into the repository.


## 8c. Catalog BLDC envelope data `[Cadex-new, ADR-206]`

`lib.bldc("hobbywing-30415200")` is independently authored from HOBBYWING's
Skywalker 2820 SL 550KV product data, accessed 2026-09-06:

- [Manufacturer specifications](https://www.hobbywing.com/en/products/skywalker2814.html):
  product 30415200, 550 rpm/V, 6S LiPo, 144.5 g, no-load 1.38 A at 22.2 V.
- [2820SL dimension drawing](https://www.hobbywing.com/en/uploads/file/20231121/6ce36297af7f04e8e0c41c3b28a36dbd.pdf):
  case diameter 35.1 mm, case length 40 mm, rear boss diameter 11 mm
  projecting 2 mm (42 minus 40), shaft projection 18 mm, total length
  60 mm. Shaft diameter 5 mm; collar diameter 10.5 mm. Rear M3 pairs
  span 19 and 25 mm. The chosen local X/Y axes align with these pairs,
  independent of cable clocking.

The collar length is undimensioned: the model reserves the whole shaft
projection at collar diameter, rather than guessing free shaft length.
Shaft coupling fit remains unsupported. Nominal M3 bores use assumed 1 mm
depth; threads and screw engagement are not modelled. The filled case
unites rotor and stator; leads, connectors, prop adapter and cross mounting
plate are absent. No installation clearance or physical inertia guarantee.

The product table's current and power entries are 40.9 A and 910.2 W **for
46 seconds**, despite the column's continuous wording. Cooling conditions
are incomplete. These values stay in explanatory notes, not numeric control
limits. No torque rating or torque constant is inferred from kV. No
manufacturer artwork, CAD, or code is redistributed; no new dependency.

## 8d. L12 linear-actuator catalog geometry `[Cadex-new, ADR-207]`

Accessed 2026-09-06: Actuonix's [L12 datasheet, revision F, November
2019](https://www.actuonix.com/assets/images/datasheets/ActuonixL12Datasheet.pdf)
and [L12 STEP archive](https://www.actuonix.com/assets/images/datasheets/L12_STP.zip),
linked by its [documentation index](https://www.actuonix.com/datasheets).
No downloaded files are redistributed. SHA-256 identities:

- PDF: `461dc22b85db497409182ac3cc02a5171fa0ea7817ed0f419b2c37708bcfeee3`
- ZIP: `5797939e2ebad2b5a4e9207e26b81ff2ec268a745e3703e743bcd44fa6a08f42`

The drawing specifies 4.25 mm mounting bores and retracted centre spacing
`52 + stroke` mm. The archive (member timestamps 2016-10-05) disagrees:
OCCT measurements of its bore cylinder axes give **0.5 mm more** in all eight
files. Extension travel itself agrees. These are CAD measurements, not
measurements of hardware or manufacturing tolerances.

| Stroke (mm) | Datasheet closed (mm) | STEP closed (mm) | STEP extended (mm) |
|---|---|---|---|
| 10 | 62 | 62.5 | 72.5 |
| 30 | 82 | 82.5 | 112.5 |
| 50 | 102 | 102.5 | 152.5 |
| 100 | 152 | 152.5 | 252.5 |

Reproduce after extracting the archive into the current directory, using
the existing headless engine (no GUI or imported manufacturer Python):

```sh
build/release/bin/FreeCADCmd -c 'import glob, Part
for path in sorted(glob.glob("l12_*mm_*.stp")):
    shape = Part.read(path)
    centres = sorted({round(face.Surface.Center.y, 6)
        for solid in shape.Solids for face in solid.Faces
        if isinstance(face.Surface, Part.Cylinder)
        and abs(face.Surface.Radius - 2.125) < 1e-6})
    assert len(centres) == 2 and shape.isValid(), path
    print(path, centres, centres[1] - centres[0])'
```

The first implementation constrains selection to **L12-50-210-12-S**,
with the supplied clevis end. Datasheet nominal geometry takes precedence
over this older CAD's axial placement; `.spec` preserves the discrepancy.
The drawing's 9 mm rear-end dimension must not be treated as a dimension
to the hole centre. Housing transitions and clevis fit are bounded by the named approximation
limits below.

For this selection the datasheet gives 12 V, 80 N maximum lifted force,
6.5 mm/s unloaded speed, and a peak-power point of 62 N at 3.2 mm/s.
These are distinct operating points, not simultaneous force/speed limits.
Duty cycle is at most 20%; operating temperature is -10 to +50 °C.
Application life still needs testing. The S switches stop within 0.5 mm
of a stroke end: geometric extension `[0, 50]` is not a promise that either
endpoint is powered-reachable. Neither source supplies a validated dynamics
model. `lib.linear_actuator` now implements this bounded nominal exterior; no fit
guarantee is established.

### Nominal geometry experiment (2026-09-06)

[`experiments/l12_nominal_probe.py`](experiments/l12_nominal_probe.py) builds
an independently authored primitive approximation with the existing OCCT
engine. Its header gives the headless reproduction command; it imports no
manufacturer file. Datum is the rear bore centre, travel is +Z, and both
bores run along X. The newer drawing determines centre spacing and 4.25 mm
bore diameter. This experiment established the construction now used by
`lib.linear_actuator`; it does not establish a tolerance model.

Additional measurements from the already identified `l12_50mm_in.stp`:
the supplied clevis (zero-based solid 10) has planar bore-side flats at
X = ±3 mm. At source Y = -67, Z = 3, material exists at X = 2.9 but not
3.1 mm. The rear lug (solid 2 at this probe) has material at X = 3.9 but
not 4.1 mm at source Y = 35.5, Z = 3. These establish nominal bore-region
widths of 6 and 8 mm in that CAD, not fit tolerances. Reproduce with
`Part.read` as above, then `shape.Solids[10].isInside(FreeCAD.Vector(x,-67,3),
1e-7,True)` and `shape.Solids[2].isInside(FreeCAD.Vector(x,35.5,3),1e-7,True)`.
The sleeve's CAD bounds are approximately X/Z ±6, Y -60 to 0.

The experiment uses those bore widths and a 12 mm square sleeve. Its 9 mm
shaft and clevis diameter, 37 mm housing length, and 14.9/18 mm housing
dimensions follow the drawing. **Placement and transitions are explicit
approximations:** housing Z 4.5–41.5, rear lug Z -4.5–8, sleeve Z 35.5–95.5,
shaft Z 90–(98+extension), and clevis Z (97.5+extension)–(106.5+extension).
The rear lug is a box; the clevis is a flat-ended cylinder clipped to its
6 mm flats. This does not reproduce the rounded clevis tip, threaded neck,
housing bumps, fillets or local seams. The 9 mm rear drawing dimension is
**not** interpreted as a hole-centre offset. No blanket 0.5 mm correction
is applied to the manufacturer's surfaces.

The filled, fused solids omit internals, shaft hollowing, thread engagement,
clamps, mounting brackets, fasteners, cable/connector and their clearance.
They are neither a conservative overall collision envelope nor physical
mass/inertia geometry. Assembly fit, installation clearance, strength,
switch reachability and dynamics remain unverified.

| Extension (mm) | Measured bore spacing (mm) | Approximation volume (mm³) | Material/void probes, canonical + placed |
|---|---|---|---|
| 0 | 102 | 18730.103513 | 60 passed |
| 23.5 | 125.5 | 20225.108917 | 60 passed |
| 50 | 152 | 21910.966075 | 60 passed |

Each shape is valid with one solid. Bounds are X [-7.45,7.45], Y [-7.5,10.5],
Z [-4.5,106.5+extension] mm. Probes check the full bore width, points just
inside/outside the bore wall and lug flats, and sleeve/shaft material.
A 120° rotation about (1,1,1) followed by translation (100,30,20) preserves
volume and all probes, checked against the explicit coordinate mapping
(x,y,z) → (100+z,30+x,20+y). The volume grows because the exterior model
fills the exposed shaft; these numbers are kernel diagnostics only.

Next: translate this bounded construction into the existing LibraryPart
contract, retain these approximation limits in `.spec`, reject unsupported
selection/extension, and verify the actual recipe through the worker and
packaged gates. This experiment does not close L3 implementation.


**Catalog implementation (2026-09-06, ADR-207).**
`lib.linear_actuator("l12-50-210-12-s", extension=0)` uses the same nominal
construction through ordinary part-domain recipes. Only this stroke, ratio,
voltage and S-switch variant is accepted. Extension must be finite within
[0,50] mm. `.spec` carries source links, the older-CAD discrepancy, distinct
qualified operating points, switch limitations and the omitted details above.
The library suite checks actual worker BREP bore surfaces, bounds and 180
canonical/placed material probes, plus publishing through cadexd. No source
CAD, artwork or code is redistributed; no dependency or dynamics API added.

## 8e. Solenoid 412 source and partial geometry audit `[Cadex-new, ADR-208]`

Accessed 2026-09-07. Adafruit's [product 412](https://www.adafruit.com/product/412)
links the supplier Chaocheng TAU0730TM-14 documents below. The page identifies
its 12 V replacement as dating from 2018-01-17, but advertises 5.5 mm throw;
that is not the drawing's travel. This audit targets the documented supplier
variant, not every unit historically sold as 412.

| Source | Identity | SHA-256 of downloaded PDF |
|---|---|---|
| [Drawing](https://cdn-shop.adafruit.com/product-files/412/412_C514-B_diagram.PDF) | Part 10104-00073014, version 1, 2021-08-30 (filename says C514-B) | `adaa02703b1129b36f8a01174592ff464a68cc1a7ad1c7628bd83b9f47b44574` |
| [Technical specification](https://cdn-shop.adafruit.com/product-files/412/C514-datasheet.pdf) | TAU0730TM-14, version A, design 21/07/12, three pages | `6fd2bac2a24fcabca3323469fcf3e8f76f449f0e073a1b01f2e041d73a2cf808` |

**Electrical qualifications.** The specification gives 12 V, 40 ohms at
20°C, nominal 0.3 A (±5%) and 3.6 W, with 50% duty. Force is approximately
0.5 N at 4 mm and at least 5 N at zero gap; its standard test conditions
are 60±2°C, 65±5% RH, 1013 mbar, empty load and a vertical armature.
Temperature rise is at most 65°C at 12 V with one second on/one second off;
operation is -5 to 60°C, 45–85% RH. These are supplier claims, not Cadex
measurements. Neither point supplies a force curve or starting-force rating
at full drawing travel. Duty percentage alone does not specify an arbitrary
safe pulse length; no continuous-force, thermal or dynamics model is inferred.

**Drawing facts and missing interfaces.** The drawing explicitly depicts
energized holding position and lists 4.9 mm stroke. Body dimensions are
29.7±0.1 by 17 (+0.25/-0.1) by 14±0.1 mm; overall axial length is
51.9±0.1 mm. The push cap is diameter 5 by 10 mm, its tip projects
15.4 (+0/-0.1) mm beyond the main body face, and the rear head diameter is
6.9 mm. Mounting centres have an 18.2±0.05 mm transverse separation, but
hole diameter, axial positions, tab profile and plate thickness are not
specified. Do not scale pixels into manufacturing dimensions. The exposed
neck diameter, cap attachment and rear head height also lack callouts.

**Reproducible partial construction.** Run:

```bash
build/release/bin/FreeCADCmd -c 'exec(open("docs/experiments/solenoid_412_probe.py").read())'
```

The independently authored experiment fills a box and cylinders; no supplier
CAD, drawing, code or artwork is redistributed. Z=0 is the main body's push
face, +Z is the energized push direction. `gap=0` represents the drawing's
held position; opening translates both plunger ends by `-gap`, within
[0,4.9] mm. This is a geometric convention, not powered endpoint proof.
The centered body occupies X ±8.5, Y ±7, Z [-29.7,0]. Its centering on the
plunger is an explicit approximation. The push cap occupies Z
[5.4-gap,15.4-gap]. The rear tip is inferred from the overall length as
-36.5-gap. A diameter-3 neck and a 2 mm long rear head are **cosmetic
choices**, not sourced dimensions. The omitted small face step is absorbed
into the filled-body/neck approximation.

Mounting tabs/holes, spring, retaining clip, leads, internal coil, armature
steps, insulation, chamfers and threads are omitted. Thus this is a partial
visual exterior, neither an installation/collision envelope nor physical
mass/inertia geometry. In particular no nominal mounting interface is proved.

| Gap (mm) | Measured Z bounds (mm) | Volume (mm³) | Canonical + placed probes |
|---|---|---|---|
| 0 | [-36.5,15.4] | 7411.834705 | 24 passed |
| 2.3 | [-38.8,13.1] | 7411.834705 | 24 passed |
| 4.9 | [-41.4,10.5] | 7411.834705 | 24 passed |

All three are valid single solids, with measured cap diameter/axial extents
and 51.9 mm total length. Placement maps (x,y,z) to (100+z,30+x,20+y),
with volume preserved and material/void probes repeated. Negative, nonfinite
and product-page 5.5 mm travel are refused by the experiment. The packaged
lifecycle/library **baseline** passes 76 tests, no skips; it does not test
an unimplemented solenoid API. No engine source, build or payload changed.

**Remaining leg.** Catalog delivery with sourced mounting interfaces is not
yet justified. Obtain a dimensioned mounting drawing for this exact revision,
or select a different traceable solenoid with complete interfaces in a new
bounded source unit. Do not repeat this partial construction, invent hole
locations, or block all L3: joints and other documented solenoids remain
available work. Full L3 stays open.

### Follow-up: incompatible older drawing and Ledex B7 (ADR-209)

Accessed 2026-09-07. This follow-up does **not** change the partial 412
construction or authorize a solenoid catalog API.

The [TAU-0730TM drawing](https://bc-robotics.com/datasheets/TAU-0730TM.pdf)
linked by [BC Robotics](https://bc-robotics.com/shop/small-push-pull-solenoid/)
is one page without a manufacturer title block, revision or date. SHA-256:
`288d672ee2cecf9c0e97176a856af2bd0e9a1523d9c5f768bde619c171545c5e`.
It depicts slots with R1.6 ends, 3.2 mm between arc centres, 20 mm
transverse separation and 16 mm axial separation; the lower slot centre
is 7 mm from the body end. Its body length is 30.5 mm and overall length
53.4 mm. Those dimensions conflict with the current 412 drawing's
18.2 mm transverse spacing, 29.7 mm body and 51.9 mm overall length.
Its illustrated actuation state is not stated. This is a discovery lead,
not manufacturer evidence for TAU0730TM-14: **do not transplant its slots**.
The indexed [Jameco specification](https://www.jameco.com/Jameco/Products/ProdDS/2219330.pdf)
could not be fetched (HTTP 403); it supplies no additional verified evidence.

The manufacturer-hosted [Ledex B7 sheet](https://www.johnsonelectric.com/pub/media/image/tmp/metric-imperial/B7_20210611.pdf)
offers a better mounting reference. Two pages; filename date 20210611,
no printed revision; SHA-256
`d699124bc39731bd25aa09d238fd538207459444f2d3ef760b55dedf8eab4864`.
For B7-212-B-4 it lists 12 V continuous at 20°C, 47.67 ohms;
18/24/38 V at 50/25/10% duty, with repeated-pulse on-time limits
110/27/8 seconds. Data is typical, force testing horizontal, no heatsink;
the listed holding force is 15.1 N, not a force law.

The energized drawing gives body 29.40 by 19.20 by 16.00 mm,
overall 36.47 mm, and two M3x0.5 mounting holes. One centre is 19 mm
from the rear face; the second is 12 mm nearer that face, with 10 mm
vertical separation (5 mm either side of the plunger axis).
This supports a nominal mounting-plane layout. It does **not** specify
tap depth, allowable screw penetration or frame thickness. Plunger end
diameter 6 mm, neck diameter 3 mm and end/neck lengths 1.5/2.5 mm are
dimensioned, but the intermediate shoulder is not. The force plot ends
at 0.4 inches; no mechanical maximum stroke is stated. Do not turn that
axis limit into a travel stop. No B7 geometry was constructed or tested.

The manufacturer's [open-frame catalog](https://www.johnsonelectric.com/pub/media/image/tmp/metric-imperial/20200212_Open_Frame_DC_in_2_.pdf)
(39 pages, filename date 20200212; SHA-256
`9b681436726ff19465ea42820624b245dfcb25ba15ff6db50ef7dd3c86716226`) has no `B7` text hit, and its
page-4 selection table has no B7 row to resolve the travel limit.
The [older tubular catalog](https://www.relayspec.com/suppliers/j/johnson_electric/news/2018/09_20b/Tubular%20mm_v2.pdf)
was located but no tubular variant was qualified in this unit.

**Decision and next leg.** Neither examined variant meets the planned
complete-interface contract. Keep solenoid implementation open and advance
to the planned joints source unit, rather than repeating this audit.
Resume B7 only with manufacturer engagement/travel evidence or a separately
justified, explicitly narrower contract; no claim that other solenoids are
unsupportable follows from this bounded search. No source assets, geometry,
runtime code or dependencies were added; existing packaged gates verify
the baseline only.

### 8f. L3 joint qualification — SKF GE 6 C (2026-09-07)

**Source identity.** SKF *Spherical plain bearings and rod ends*, publication
BU/P1 06116/1 EN, May 2013, copyright SKF Group 2013,
[manufacturer PDF](https://www.skf.com/binaries/pub12/Images/0901d19680154a05-06116_1-EN_tcm_12-122020.pdf),
downloaded 2026-09-07, SHA-256
`df51e55192dc9ce138e371e2f5047cfbceeba7f2ac6246f92e5bd3d7f24930cb`.
Printed pages 132–133 (PDF pages 134–135) were rendered and visually checked:
the GE 6 C row and its adjacent dimension/abutment row are the second rows.
This qualifies that publication's variant, not a claim about current inventory
or interchangeability with GE 6 E. No supplier CAD, PDF or code is vendored.

**Nominal contract (mm).** Bore d=6, outside D=14, inner width B=6,
outer width C=4, spherical diameter dk=10. Origin is the concentric sphere
centre; neutral bore and housing axes are Z. Inner end faces are Z=±3,
outer end faces Z=±2. These provide shaft and housing mating datums.
Both ring chamfer dimensions r1/r2 are 0.3 minimum. Source abutment limits:
shaft shoulder diameter da=7.4 minimum, 8 maximum; housing shoulder opening
Da=9.5 minimum, 12.7 maximum; shaft/housing fillet radii ra/rb=0.3 maximum.
The catalog's 13° tilt is conditional on the shaft shoulder not exceeding
da max. Test-only cylinders check limiting nominal shoulders on both sides;
no mating hardware is delivered.

**Qualified ratings.** Steel/PTFE sintered-bronze maintenance-free radial
spherical plain bearing. Catalog basic dynamic/static load ratings are
3.6/9 kN, and listed mass is 0.004 kg. These are manufacturer rating inputs,
not allowable robot working loads, axial ratings, fatigue life, torque,
friction or an actuator model. Application load direction, duty, mounting,
fit and operating conditions require separate selection. No dynamics or
physical inertia can be inferred from the exterior volumes below.

**Independent construction.** [ge6c_joint_probe.py](experiments/ge6c_joint_probe.py)
uses OCCT sphere/cylinder intersection and subtraction. The outer ring is
a Ø14 × 4 cylinder with a radius-5 spherical cavity; the inner ring is that
sphere clipped to width 6 with a Ø6 through bore. Inner tilt is about Y
through the common centre, bounded to ±13°; arbitrary assembly joint solving
is not introduced. Chamfers, liner thickness, manufacturing seams and radial
running clearance are omitted. The two ideal spherical surfaces coincide:
this is nominal geometry, not a tolerance model, press-fit guarantee,
conservative collision envelope or a manufacturing drawing. It supports
the bounded `lib.joint("skf-ge-6-c", tilt_degrees=...)` value using existing
primitives (ADR-211). The body retains two solids; metadata preserves the
source revision/hash, shoulder limits and qualified ratings.

**Reproduce and result.** Run the FreeCADCmd command in the probe's header
against the existing built headless engine. At -13/0/6.5/13°, each ring is
a valid single solid, outer/inner volumes are 318.348056/245.044227 mm³,
matching independent analytic integrals. Ring overlap is zero, a Ø5.98
test shaft remains clear, actual bore/OD cylinders and spherical surfaces
match nominal dimensions, and 96 material/void probes pass across canonical
and obliquely rotated/translated placements. Nonfinite/out-of-range tilt is
rejected. Ø8 shaft shoulders and Ø9.5 housing openings have zero interference
with the opposing ring at all four tilts (16 nominal shoulder checks).
Qualification-stage packaged lifecycle/library baseline: 76 passed, no skips, 16.23 s.
That audit needed no engine-source edits, build, staging or full engine suite;
the baseline is not packaged joint verification.
This establishes the stated approximation only. Delivery tests in
`test_library.py` exercise the recipe through the actual part worker, including
canonical/placed interfaces, analytic volumes, shoulder clearances and
material/void probes at four tilts, plus cadexd publication and discovery.
The commands for delivery verification are the full engine suite,
`pixi run build-engine`, completed `pixi run stage-engine`, then the packaged
lifecycle/library gate; ADR-211 records the result. Full L3 and the solenoid
interface gaps remain open.

### 8g. L3 involute gearing — ISO 53 / ISO 54 (2026-09-07)

**Source identity.** ISO 53:1998 *Cylindrical gears for general and heavy
engineering — Standard basic rack tooth profile*, type A: 20° pressure
angle, addendum 1.0 m, dedendum 1.25 m, bottom clearance 0.25 m, whole depth
2.25 m. ISO 54:1996 *Cylindrical gears for general engineering and for heavy
engineering — Modules*, series I: 1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10,
12, 16, 20, 25, 32, 40 and 50 mm. The public iTeh preview pages (ISO 53:1998
and the ISO 54:1977 edition, both linked from
`CadexCatalog.GEAR_STANDARD["sources"]`) were read for the coefficients and
the module series; the standards themselves were not purchased, downloaded
or vendored, so no file hash applies. A standard has no vendor, revision
page or licence question: every number is a coefficient of the module, and
the series II modules and the sub-millimetre modules are deliberately not
accepted until a design needs them.

**Nominal contract (mm).** For a spur gear of module m and z teeth: pitch
diameter m·z, base diameter m·z·cos 20°, tip diameter m(z+2), root diameter
m(z−2.5), circular pitch π·m and tooth thickness π·m/2 at the pitch circle.
Datum is the gear axis (+Z) with the base face in the datum plane; tooth 0
is centred on +X. For a rack of z teeth: length z·π·m along +X from X=0,
pitch line on Y=0, tips at Y=+m, roots at Y=−1.25 m, straight 20° flanks;
the back face sits `height` below the tips, `height` must exceed 2.25 m.
Tooth counts are bounded to [6, 200] for gears and [1, 200] for racks; a
gear under 17 teeth carries the undercut warning in `spec["approximate"]`.

**Independent construction.** One generator in `cadex_library_api.py`
samples the involute of the base circle eight times per flank between the
base (or root, when larger) circle and the tip circle, joins the flanks with
tip and root arcs into one counter-clockwise polygon, and extrudes the face;
below the base circle the flank is a radial line. Root fillets, tip relief,
backlash, profile shift and helix are omitted, and no density, strength or
torque rating is supplied. Tip and root vertices lie exactly on their
circles, so the real-kernel test measures the standard's diameters from the
built solid's vertices rather than from the recipe.

**Reproduce and result.** `test_gear_real_kernel_diameters_and_volumes`
builds m2z20 (bore 6), m2z8, m1z60 (bore 4) and m1z6 gears plus m2z10 and
m1.5z4 racks through the actual part worker: each is one valid solid, tip
and root radii match m(z+2)/2 and m(z−2.5)/2 within 1e-7, the volume lies
between the root and tip cylinders, the bore is the only cylindrical
surface, pitch-circle probes bracket the π·m/2 thickness, the rack pitch is
π·m and its tooth height 2.25 m, and the rack volume equals the exact
trapezoid sum. Placed instances keep their volume. cadexd publication of
canonical and placed gear and rack outputs is in
`test_the_library_builds_on_the_real_kernel`; ADR-233 records the gates.

**Rack and pinion (ADR-234).** `lib.rack_and_pinion` composes the two
values above with no new profile: centre distance = pinion pitch radius
plus a backlash shift of `backlash / (2 tan 20°)` (ISO 53's pressure angle;
the shift is the standard relation between a radial adjustment and the
circumferential play it opens, not a vendor number), travel per revolution
π·m·z, root clearance 0.25 m plus the shift on both sides.
`test_rack_and_pinion_real_kernel_mesh_and_clearance` measures on the built
solids, at nine phases for three configurations, zero common volume, both
root clearances, and a flank gap of `backlash·cos 20°/2` within the chord
sag; its negative controls measure a half-pitch collision and the
interference of an unshifted 12-tooth pinion, so the undercut warning in
`spec["approximate"]` is backed by a number (0.061 mm³ at m2z12r10, face
width 8) rather than a citation.

### Fifth servo candidates (2026-09-07; ADR-229)

[Cadex-new] The [bounded source audit](FIFTH-SERVO-AUDIT.md) pins two Hitec
manufacturer sheets by URL, revision and SHA-256. Neither HS-311 nor HS-422
qualifies for the unchanged recipe: mounting-slot and output-datum evidence
must be resolved before delivery. No source assets or public SKU were added;
the four existing servo identities remain the catalog's coverage.

### Manufacturer horn and pigtail STEP qualification (2026-09-07; ADR-231)

[Cadex-new] [The bounded audit](HORN-PIGTAIL-AUDIT.md) pins and probes
goBILDA 1900-0025-0104 STEP, checks the named DS3218 archive lead and
rejects a generic cable listing without manufacturer CAD. Neither category
qualifies: asset permissions and exact horn compatibility remain unresolved;
DS download access fails; no small script-owned STEP import path is established.
No vendor bytes or catalog identities were added. Replan before delivery.
