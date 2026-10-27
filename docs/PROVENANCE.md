# PROVENANCE.md — Where Cadex's Code Comes From

Verified against source: 2026-10-27

Cadex is not written from scratch. It is a **derivative work of a large
free-software project, FreeCAD**, carrying the design lessons of two more
it no longer contains: VibeCAD, which we built and then tore down, and
Blender, whose fork was Cadex's user interface until 2026-10-03 (§3). This
document says exactly which code came from where, under which licence, and what we changed — because a fork that cannot
answer that question honestly is not a project, it is a pile.

It is the outward-facing companion to the inherited-tree ledger,
[`FREECAD.md`](FREECAD.md), which carries the same story in operational
detail. The shell's ledger is history now:
[`history/BLENDER-TREE.md`](history/BLENDER-TREE.md).

## 1. The short version

| Source | What it became | Licence |
|---|---|---|
| [OCCT](https://dev.opencascade.org/) | the geometry kernel — every solid, boolean, and fillet | LGPL-2.1 with an exception |
| [MuJoCo](https://github.com/google-deepmind/mujoco) | the **dynamics** kernel — every simulation, MJCF export and policy rollout | Apache-2.0 |
| [FreeCAD](https://github.com/FreeCAD/FreeCAD) | **the engine** — the repository root | LGPL-2.1-or-later |
| [Blender](https://projects.blender.org/blender/blender) | the shell, until it was deleted (ADR-498) — nothing of it remains | GPL-2.0-or-later |
| VibeCAD (ours, predecessor) | the scripted-modeling engine inside `src/Mod/cadex/` | LGPL-2.1-or-later |

Cadex adds roughly **150,000 lines** of its own (October 2026): about 95,000
of engine Python under `src/Mod/cadex/` and one C++ file
(`CadexGeometryWorker.cpp`), about 30,000 in `cli/` (the CLI, the MCP server,
the dashboard server and pages, vendored three.js excluded), under 10,000 of
suites, and about 15,000 in the offboard `training/` and `analysis/` trees,
which are **not part of the product** (§5). Everything else in this
repository, which is the overwhelming majority of it, belongs to FreeCAD.

We do not track upstream. FreeCAD was imported as a squashed snapshot, as
Blender was, and the direction of travel is **subtractive**: we delete from
the inherited tree rather than merge into it. That is a deliberate trade — we give up
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
1, the Qt shell and provider stack in Phase 7 (ADR-021), and the `src/Gui`
directory itself in Phase 8 (ADR-213, ADR-214). `BUILD_GUI=ON` is rejected,
so the shipped engine has no GUI layer, and the shipped binaries
are `FreeCADCmd` and `CadexGeometryWorker` with no FreeCAD application at
all. The engine payload installs an explicit keep-list of modules; the Addon
Manager, Web, Start, Test, and Help modules are not on it.

**Version.** A snapshot of the FreeCAD 1.2 development line. `version.json`
was re-versioned to Cadex's own `0.2.0` (the v0.2.0 release) and no longer
states a FreeCAD version; the inherited `SECURITY.md` we replaced named `1.2dev` as the then
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

## 3. Blender — the shell, deleted

From 2026-07-25 to 2026-10-03 the product's user interface was a Blender fork
(Blender 5.3 alpha, by way of our own `mesh` fork), GPL-2.0-or-later, speaking to
the engine only over the cadexd protocol. ADR-495 disabled it and ADR-498 deleted
it; the tag `v1-blender-shell` is the last tree that carries it, its ledger is
[`history/BLENDER-TREE.md`](history/BLENDER-TREE.md), and
[`history/SHELL-PARITY.md`](history/SHELL-PARITY.md) records where each part went.
It left **no code**: the shell was GPL and the rest of the repository is LGPL, so
nothing of it was copied out, and what the dashboard and CLI do in its place is
re-derived (ADR-061). Ideas survive (the dark palette, the appearance roles, the
rollout playback), and ideas are not code. The detail is in
[`history/PROVENANCE-QUALIFICATIONS.md`](history/PROVENANCE-QUALIFICATIONS.md).

**Credit.** For two and a half months the interface Cadex presented —
viewport, navigation, tools, theming — was Blender's, built by the Blender
Foundation and its contributors. Cadex was never affiliated with or
endorsed by the Blender project.

## 4. MuJoCo — the dynamics kernel

**What it is here.** MuJoCo is to dynamics what OCCT is to geometry: a kernel
we keep, upstream and unmodified, rather than a tree we fork. `CadexDynamics.py`
translates a Cadex assembly into an `mjSpec`, steps it, and reads the result
back; `assembly.mjcf` writes MJCF by calling **MuJoCo's own writer**
(`MjSpec.to_xml()`) rather than serialising the format ourselves. We fork
FreeCAD because we intend to replace it. MuJoCo we keep.

**How it reaches a user, and this is the part that matters.** MuJoCo is not
a build dependency that stays behind on the build machine. `mujoco == 3.10.0`
is a **pypi wheel redistributed inside the shipped engine payload**, carried
there by name through `CARRIED_PYPI_PACKAGES` in
`package/rattler-build/scripts/relocate_conda_environment.py` (ADR-076),
because the pixi manifest was not re-solvable as conda once
conda-forge moved past our `occt == 7.8.1` pin (it re-solves again since
ADR-831; the move to a conda `mujoco` has not been made). It is 53.5 MB of the payload,
it ships inside the payload, and the payload build hard-fails if it cannot
import exactly that version out of the payload's own interpreter.

That makes it a third category this document did not previously have.
`src/3rdParty/` is vendored source; "build dependencies from conda-forge" stay
on the build machine. A pypi wheel that ships is neither, and it is the one
that carries a redistribution obligation.

**Licence flow.** Apache-2.0 → the engine's LGPL-2.1-**or-later**. The "or
later" is doing the work: Apache-2.0 is incompatible with LGPL-2.1-*only* and
compatible with the v3 family, so the "or later" clause is what makes the
combination clean. (The Blender shell, while it existed, made the same
election for its binary under GPL version 3 or later terms.) **The root `NOTICE` file carries the entry**, and
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
(ADR-084). Its seven dependencies — `jax`, `mujoco`, `mujoco-mjx`, `numpy`,
and since ADR-712 `brax`, `flax` and `optax` — are pinned in
`training/requirements.txt` and installed into a venv on that machine. None
of them but `mujoco` and `numpy` is in `pixi.toml` or the payload; tests
assert that no `jax` or `mjx` is in `pixi.toml` or under `src/Mod/cadex`
(`test_offboard_boundaries.py`, `test_engine_purity_guardrails.py`), and
nothing checks a staged payload for them.

`analysis/` is the second tree under that contract (ADR-141, ADR-142,
ADR-143) and is `[Cadex-new]`, LGPL-2.1-or-later, shipping in nothing on the
same terms. Its dependencies are **still exactly three** — `numpy`, `scipy`,
`mujoco` — pinned in `analysis/requirements.txt` and installed into a venv;
none is in `pixi.toml`, and `test_offboard_boundaries.py` asserts that, that
the pins are exact, and that no CMake rule references the tree. S2
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
and the engine may not import `analysis/`. A test solved the same benchmark
through both and required them to agree until ADR-725 deleted it. Nothing else crossed: topology
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
  deleted (ADR-021). Cadex now runs no model loop at all (ADR-538): the AI
  is whichever agent the person brings — Claude Code, Codex, Pi — under its
  own login, driving the engine through `cadex mcp`.
- **No GUI in the engine.** The engine became headless; the shell became a
  separate process across a protocol (ADR-017, ADR-018, ADR-022).

The `cadex-teardown` branch at `github.com/theo-kirby/vibecad` holds that
six-phase history. Nothing deleted there returns without an ADR — that rule
is in `AGENTS.md`, and [`FREECAD.md`](FREECAD.md) §4 is the do-not-resurrect
list.

## 7. One licence for everything we ship

Everything this repository carries of its own, and the FreeCAD tree it
descends from, is LGPL-2.1-or-later. Since ADR-498 there is **no GPL code
in the repository**: `test_licensing_compliance.py` fails if a tracked
source file declares a GPL SPDX identifier in its header or if anything is
tracked where the shell tree was again. Until then the engine was LGPL and the shell
GPL, kept apart as separate programs across the cadexd protocol, and that
rule is why the deletion took no code with it.

- The engine is a set of processes (`cadexd`, and `FreeCADCmd` workers
  beneath it) that speak NDJSON over stdin/stdout.
- `cli/` is a client of that protocol (ADR-061, [`CLI.md`](CLI.md)) and the
  dashboard is served from it. Both are LGPL-2.1-or-later. Nothing in them
  was copied from the shell: its protocol client, backend, MCP shim and
  modes were read as reference only, and every equivalent derives from the
  LGPL engine-side precedents in `src/Mod/cadex/cadex_tests/`.
- The protocol is pinned by tests on both the request and the response side
  (`docs/INTEGRATION.md`, ADR-027), which is what keeps a future front end
  replaceable.

What is shipped is the staged engine payload. It is LGPL-2.1-or-later, with
the MuJoCo wheel inside it Apache-2.0 and its conda packages each under
their own licence. One of those, `readline`, is GPL-3.0 and comes with the
standard conda Python runtime; that is a binary dependency of the payload,
not code in this repository, and it stays the counsel item ADR-171 flagged.
The payload carries its licence material at its root — `LICENSE`, `NOTICE`,
`THIRD_PARTY_LICENSES.md` and a per-package `licenses/` directory with
`MANIFEST.json` — and the complete corresponding source is this public
repository. This is a description of how the repository is structured, not
legal advice; if you are redistributing Cadex, read the licences.

## 8. Everything else

The lettered subsections after the list are the sources behind catalog data
and the third-party assets the engine and dashboard carry; code comments and
other docs cite them by letter (`PROVENANCE §8d`).

- **Bundled third-party code** lives in `src/3rdParty/` (Clipper2, PyCXX,
  salomesmesh, libE57Format, OndselSolver and others). Most keep their own
  licence file in-tree; the ones that do not are named, with their
  licences, in [`THIRD_PARTY_LICENSES.md`](../THIRD_PARTY_LICENSES.md) §2.
- **Runtime dependencies from conda-forge** (OCCT, Python, numpy/scipy and
  ~330 more, pinned in `pixi.lock`) **do not stay on the build machine —
  they are the payload.** The engine payload is a relocated copy of the
  pixi environment, so every conda package that survives the prune ships
  inside it. The prune drops the GUI toolkit and, since ADR-531 and
  ADR-532, LLVM, clang, Node and Perl, which the development environment
  carries and the engine never loads. OpenCV and PCL left the development
  environment too (ADR-831). An earlier revision of this bullet claimed the
  opposite. What each shipped package's licence is, and where its text
  landed, is recorded per-package in the payload's
  `licenses/MANIFEST.json`, written by `package/engine/collect_licenses.py`
  at staging time.
- **The one pypi wheel that ships** is `mujoco == 3.10.0` —
  §4. It is neither vendored source nor a build-only dependency, which is why
  it has a section of its own rather than a bullet here.
- **The CadexLight, CadexDark and CadexMono themes**, based on
  [OpenTheme by Obelisk79](https://github.com/obelisk79/OpenTheme)
  (LGPL-2.1), were Qt stylesheets under `src/Gui` and were deleted with it
  (ADR-214); no `.qss` file is tracked now. `NOTICE` still carries their
  entry.

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

- **Adafruit 4754 BNO085 IMU** (ADR-407): outline, four 2.5 mm mounting
  holes, the JP1/JP2 header pads and the chip's centre are parsed from the
  manufacturer's
  [EAGLE board at commit be9dc998](https://github.com/adafruit/Adafruit-BNO08x-PCB/blob/be9dc9984bb19b1e8ba31e8744917d0952993ef2/Adafruit_BNO08x.brd),
  and the 2.5 g mass from the [product page](https://www.adafruit.com/product/4754),
  checked 2026-09-25. The page notes a 2023-12 silkscreen revision the
  repository does not carry; the mechanical layout is assumed unchanged.
  1.6 mm thickness, the chip body size and density are approximate; the
  STEMMA QT edge connectors are surface-mount and carry no terminal rows.
  Same CC BY-SA upstream, not vendored.
- **Pololu 4092 D36V50F6 regulator** (ADR-407): board, 1.57 mm thickness,
  three 2.18 mm mounting holes and the twelve-hole pin grid from Pololu's
  [dimension drawing 0J1732](https://www.pololu.com/file/0J1732/d36v50fx-step-down-voltage-regulator-dimensions.pdf)
  (mil, converted exactly); mass and ratings from the
  [specifications](https://www.pololu.com/product/4092/specs). The pin
  *signals* are read off Pololu's labelled photo and are approximate until
  checked against the published STEP model, as are the component marker
  and the dropout read off Pololu's graph.

All five replace rounded board outlines with rectangular bounds and omit
connector bodies, detailed components, traces and silkscreen. The body is
an interface model, not an enclosure-clearance certification or a measured
mass model. `spec["approximate"]` lists the numeric assumptions; this
paragraph records the geometric omissions.

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

**Catalog implementation (2026-09-06, ADR-207).**
`lib.linear_actuator("l12-50-210-12-s", extension=0)` uses the same nominal
construction through ordinary part-domain recipes. Only this stroke, ratio,
voltage and S-switch variant is accepted. Extension must be finite within
[0,50] mm. `.spec` carries source links, the older-CAD discrepancy, distinct
qualified operating points, switch limitations and the omitted details above.
The library suite (deleted by ADR-725) checked actual worker BREP bore
surfaces, bounds and 180 canonical/placed material probes, plus publishing
through cadexd. No source
CAD, artwork or code is redistributed; no dependency or dynamics API added.

The nominal-geometry experiment that established the construction
([`probes/experiments/l12_nominal_probe.py`](probes/experiments/l12_nominal_probe.py))
is recorded in [`history/PROVENANCE-QUALIFICATIONS.md`](history/PROVENANCE-QUALIFICATIONS.md).

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

Not delivered: neither this drawing nor the follow-up sources (ADR-209)
give a complete mounting interface, so no solenoid is in the catalog. The
partial construction, its probe (`docs/probes/experiments/solenoid_412_probe.py`)
and the follow-up audit are in
[`history/PROVENANCE-QUALIFICATIONS.md`](history/PROVENANCE-QUALIFICATIONS.md).

## 8f. L3 joint qualification — SKF GE 6 C (2026-09-07)

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
physical inertia can be inferred from the exterior volumes. The construction
(`docs/probes/experiments/ge6c_joint_probe.py`) and its measured result are in
[`history/PROVENANCE-QUALIFICATIONS.md`](history/PROVENANCE-QUALIFICATIONS.md).

## 8g. L3 involute gearing — ISO 53 / ISO 54 (2026-09-07)

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
The sampled-involute construction and its deleted real-kernel test's result
(ADR-233) are in
[`history/PROVENANCE-QUALIFICATIONS.md`](history/PROVENANCE-QUALIFICATIONS.md).

**Rack and pinion (ADR-234).** `lib.rack_and_pinion` composes the two
values above with no new profile: centre distance = pinion pitch radius
plus a backlash shift of `backlash / (2 tan 20°)` (ISO 53's pressure angle;
the shift is the standard relation between a radial adjustment and the
circumferential play it opens, not a vendor number), travel per revolution
π·m·z, root clearance 0.25 m plus the shift on both sides.
A real-kernel test (deleted by ADR-725; ADR-234 records the result) measured
on the built solids, at nine phases for three configurations, zero common volume, both
root clearances, and a flank gap of `backlash·cos 20°/2` within the chord
sag; its negative controls measured a half-pitch collision and the
interference of an unshifted 12-tooth pinion, so the undercut warning in
`spec["approximate"]` is backed by a number (0.061 mm³ at m2z12r10, face
width 8) rather than a citation.

## 8h. orun1 catalog additions `[Cadex-new, ADR-485]`

The recipes are independently authored LGPL Cadex code. Interface numbers
come from the sources below, checked 2026-10-02. No vendor CAD, artwork or
drawing is redistributed. A STEP model was only measured, never copied in.

- **Feetech STS3215 C001:** the manufacturer's
  [C001 spec PDF](https://www.feetechrc.com/Data/feetechrc/upload/file/20260622/6391772523943436695270694.pdf)
  gives the case, spline, rear boss, ratings, bus and connector. Waveshare's
  [ST3215 2D drawing (DXF)](https://files.waveshare.com/upload/0/08/ST3215-2D.zip)
  gives the hole centres and the 10.11 mm axis offset, read from its
  entities. Which face carries which hole pair, the hole depth, and the
  cover and bump heights are inferred, and are listed in `approximate`.
- **Raspberry Pi 5:** the
  [Pi 5 mechanical drawing](https://datasheets.raspberrypi.com/rpi5/raspberry-pi-5-mechanical-drawing.pdf)
  gives the outline, holes and port positions. Port heights come from the
  [Pi 4 drawing](https://datasheets.raspberrypi.com/rpi4/raspberry-pi-4-mechanical-drawing.pdf).
  The thickness is measured off the drawing, and the mass is a retailer
  figure.
- **Raspberry Pi Camera Module 3:** the
  [mechanical drawing](https://datasheets.raspberrypi.com/camera/camera-module-3-standard-mechanical-drawing.pdf)
  and the [product brief](https://datasheets.raspberrypi.com/camera/camera-module-3-product-brief.pdf).
  The FPC receptacle's edge is inferred.
- **Pololu 3415 VL53L1X carrier:** Pololu's annotated
  [dimension](https://a.pololu-files.com/picture/0J7225.1200.jpg) and
  [pinout](https://a.pololu-files.com/picture/0J8679.1200.jpg) photos, and
  ST's [VL53L1X datasheet](https://www.pololu.com/file/0J1506/vl53l1x.pdf).
  The hole x and sensor position are measured from the photo.
- **Adafruit 2448 TB6612 motor driver** (ADR-490): outline, both 2.5 mm
  holes, the JP1/JP3/J1 pads with their nets, and the chip's body, parsed
  from the published
  [EAGLE board](https://github.com/adafruit/Adafruit-TB6612-Motor-Driver-Breakout-PCB/blob/514d5ded1aade108d0698d0e718a92c22ff5496f/Adafruit%20TB6612.brd)
  (CC BY-SA; dimensions transcribed, no file copied). Ratings, the 3 mm
  overall height and the 1.8 g mass come from the
  [product page](https://www.adafruit.com/product/2448). The PCB thickness
  and the chip's height are inferred from that height.
- **Pololu 1430 wheel 80×10 mm:** the
  [wheel drawings](https://www.pololu.com/file/0J1708/pololu-wheel-dimensions.pdf)
  (page 5), plus Pololu's STEP model, measured in this repo's kernel for the
  hub offset and bore, and since ADR-489 for the radii and depths of the
  hub, flange, spokes, rim and tyre. The STEP model itself is not in the
  repository: the geometry is rebuilt from those numbers.
- **Essentra 462178 screw-on foot:** Essentra's feet catalogue p.691, as
  [hosted by Farnell](https://www.farnell.com/datasheets/3110954.pdf).

## 8i. Catalog QDD actuator data `[Cadex-new, ADR-540]`

`lib.qdd("cubemars-ak10-9-v3")`, `lib.qdd("cubemars-ak70-10")`,
`lib.qdd("cubemars-ak80-9-v3")`, `lib.qdd("cubemars-ak60-6-v3")`,
`lib.qdd("cubemars-ak45-10-v3")` and `lib.qdd("robstride-rs04")` are
independently authored from their manufacturers' product pages, CubeMars's
accessed 2026-10-04:

- [AK70-10 KV100](https://www.cubemars.com/product/ak70-10-kv100-robotic-actuator.html):
  10:1, 48 V, rated 8.3 N·m at 310 rpm and 7.2 A, peak 24.8 N·m at 23.2 A,
  no-load 480 rpm, Kt 0.123 N·m/A, rotor inertia 753.4788 g·cm², back drive
  0.48 N·m, backlash 0.2°, 621 g. Its
  [2D drawing](https://store.tmotor.com/images/202408/141723615242833695.jpg):
  Ø89 body, Ø77 × 6 mm output step, Ø71 × 11.2 mm rear cover, 50.25 mm
  overall; 8-M3×10 front and 8-M3×3.5 rear on Ø83; 6-M3×7 output on Ø25.
  Third-party listings give 521 g; the manufacturer's 621 g is used.
- [AK80-9 V3.0 KV100](https://www.cubemars.com/product/ak80-9-v3-0-robotic-actuator.html):
  9:1, 48 V, rated 9 N·m at 390 rpm and 12 A, peak 22 N·m at 28 A, no-load
  570 rpm, Kt 0.095 N·m/A, rotor inertia 1118.3238 g·cm², back drive
  0.51 N·m, backlash 15 arcmin, 490 g. Its
  [2D drawing](https://www.cubemars.com/images/20250407/1744015272105618.png):
  Ø98 body, Ø48 × 3 mm output hub, 38.5 mm overall; 8-M3 on Ø85 front and
  rear; 6-M4 on Ø28 output. Hole depths are undimensioned (assumed 3 mm).

The heavy tier (ADR-713), from the same manufacturer's page and 2D
drawing, accessed 2026-10-15:

- [AK10-9 V3.0 KV60](https://www.cubemars.com/ko/product/ak10-9-v3-kv60-r-link-cable-package.html):
  9:1, 48 V, rated 18 N·m at 235 rpm and 10.7 A, peak 53 N·m at 31.9 A,
  no-load 320 rpm, Kt 0.16 N·m/A, rotor inertia 1002 g·cm², 940 g. Its
  [2D drawing](https://www.cubemars.com/images/file/20241126/1732601780310205.pdf):
  Ø98 case, stepped output end Ø82 / Ø55 / Ø30 over 10.2 mm, Ø71 rear cover,
  61.7 mm overall; 6-M4×8 front and 6-M4×4 rear on Ø90; 6-M4×7 output on
  Ø24. The page publishes neither back drive nor backlash; the catalog's
  0.6 N·m back drive is an estimate, flagged in its `approximate` list.

The 120 N·m tier (ADR-826), from RobStride's product page, accessed
2026-10-25:

- [RobStride 04](https://www.robstride.com/products/robStride04): 9:1,
  48 V (15–60 V), rated 40 N·m at 50 rpm and 27 Apk on a 345 × 345 mm
  aluminium heat sink, peak 120 N·m at 90 Apk, no-load 200 rpm, torque
  constant 2.1 N·m/Arms (output side), 1420 ± 20 g, 120 × 120 × 56 mm;
  stator holes "106 x 10 x 6 mm (M4)" and output flange holes
  "35.86 x 9 x 9 mm (M5)", read as pitch circle × count × depth. No
  dimensioned drawing, rotor inertia, back drive, backlash or rear-face
  holes are published: the envelope is one Ø120 × 56 mm cylinder from the
  product photograph, the rear face carries no holes, and the catalog's
  2045 g·cm² rotor inertia (the AK10-9's scaled as diameter⁴ × length) and
  0.8 N·m back drive are estimates, flagged in its `approximate` list.

The light tier (ADR-608), from the same manufacturer's pages and 2D
drawings, accessed 2026-10-09:

- [AK60-6 V3.0 KV80](https://www.cubemars.com/product/ak60-6-v3-0-kv80-robotic-actuator.html):
  6:1, rated at 24/48 V (the catalog takes 48 V): rated 3 N·m at 490 rpm and
  3.8 A, peak 9 N·m at 11.2 A, no-load 640 rpm, Kt 0.135 N·m/A, rotor
  inertia 243.5 g·cm², back drive 0.2 N·m, 380 g, Ø79 × 43 mm. No backlash
  figure is published ("low backlash"), so the row carries `None`. Its
  [2D drawing](https://www.cubemars.com/data/cms/202602/ak60-6-v3-0-robotic-actuator-2d-drawing.pdf):
  Ø79 × 29.5 mm body, Ø49 × 1 mm and Ø25 × 0.5 mm output steps, a 12 mm rear
  step (Ø57, the rear view's ring); 6-M3×6 front and 6-M3×3.5 rear on Ø68;
  6-M3×6 output on Ø20.
- [AK45-10 V3.0 KV75](https://www.cubemars.com/product/ak45-10-v3-0-kv75-robotic-actuator.html):
  10:1, 24 V: rated 2.5 N·m at 120 rpm and 1.9 A, peak 7 N·m at 5 A,
  no-load 180 rpm, Kt 0.127 N·m/A, rotor inertia 157.33 g·cm², back drive
  0.1 N·m, backlash 18 arcmin, 262 g, Ø53 × 45.2 mm. Its
  [2D drawing](https://www.cubemars.com/images/202607/AK45-10-V3.0-KV75-en-draw.png)
  ([PDF](https://www.cubemars.com/data/cms/202607/ak45-10-v3-0-kv75-2d-drawing.pdf)):
  Ø53 body, Ø37 × 1 mm output step; 6-M2.5×5 front on Ø47.5, 4-M2.5×5 rear
  on Ø47, 3-M2.5×6 output on Ø27. Resellers list 260 g and 150 rpm; the
  manufacturer's figures are used.

Bolt-circle clocking is read off the drawings, not dimensioned on them.
Kt and rotor inertia are taken as motor-side (Kt × ratio is near the
rated torque over the rated current); the output sees the inertia × ratio².
The AK70-10's 48 V speed-torque chart on the same page starts near 380 rpm,
below its tabulated no-load figure; the catalog keeps the table's number and
the note. No manufacturer artwork, CAD, or code is redistributed; no new
dependency.

## 8j. The render font `[third-party, OFL-1.1, ADR-568]`

Every caption, label and clock Cadex draws into an image or video
(`CadexStudio.Canvas.text`: the concept sheet, the blueprint sheet, the
evaluation film's overview and detail sheets, the rollout and evaluation
videos) is set in **Noto Sans Regular**, from one file beside the module:

| | |
|---|---|
| File | `src/Mod/cadex/NotoSans-Regular-subset.ttf` (9,712 bytes, sha256 `34b27ebe80768130e765e7c26e014abf5c459b0268e5fab5dcacbaeb35acfc45`) |
| Upstream | Noto Sans Regular, version 2.004 (`NotoSans-Regular.ttf`, sha256 `89c3c497…0ced2909d`), as packaged by Debian `fonts-noto-core` 20201225-2 from [notofonts](https://github.com/notofonts/latin-greek-cyrillic) |
| Copyright | Copyright 2015 Google LLC. All Rights Reserved. |
| Licence | SIL Open Font License 1.1 (`OFL-1.1`), text in `src/Mod/cadex/NotoSans-OFL.txt`; the font declares no Reserved Font Name |
| Modification | Subset with fontTools `pyftsubset` to printable ASCII and 17 symbols (° ± µ · × Ø – — ‘ ’ “ ” … − Ω Δ →), hinting and layout tables dropped. The glyph outlines are unchanged. |

The OFL lets the font be bundled and redistributed with any software; the
font stays under the OFL and the LGPL code that reads it is unaffected. It
is a font file, not a library: `CadexStudio` reads its outlines and
rasterises them in the standard library, so no font or image library enters
the engine or the payload. The 5×7 bitmap face it replaces is deleted.

## 8k. Machine parts data `[Cadex-new, ADR-646]`

`src/Mod/cadex/CadexParts.json` and `CadexMachineParts.py` are independently
authored LGPL Cadex data and code. Every family states its source and its
approximations in the file itself, and `lib.part(...).spec` carries both. No
vendor CAD, drawing or artwork is copied; the numbers were transcribed
2026-10-10.

- **Standards** (the numbers are the standard's): NEMA ICS 16 frame 17 and
  23 faces, bolt squares, pilots and shafts; the GT2 (2GT) 2.000 mm pitch
  and 0.254 mm pitch-line offset (Gates PowerGrip GT2 design manual);
  DIN 103 Tr8 trapezoidal screws; ISO 6432, ISO 15552 and ISO 6020-2 bores,
  rods and pressure ratings; DIN 6499 ER collet capacities; tyre size codes
  (outer diameter, section and rim are the code); EN 10270-1 music wire,
  with the spring rate computed from `G d^4 / (8 D^3 n)`; ISO 261/273/4762/
  10642/4032/7089 for M10 and M12.
- **Vendor tables**: HIWIN's MG miniature guideway catalogue for the
  MGNR9/12 rails and MGN9/12 C/H blocks (cross-checked against an
  interchange listing, lily-bearing.com, which gives MGN12H 47.6 mm long with
  seals against HIWIN's 45.4); the SFU1204 ball-nut table common to the SFU
  series; the vendor datasheets of the 17HS4401, StepperOnline 17HS19-2004S1,
  23HS22-2804S and 23HS30-2804S steppers for length, torque, rotor inertia
  and mass.
- **Typical, not one maker's** (named `approximate` in each family): the T8
  brass flange nut, GT2 pulley hubs and idlers, 20-series T-nut and corner
  bracket, cylinder dead lengths, barrel diameters and clevises, spindle
  lengths and masses, the plate casters, and the tyres' hubs and masses.
- **Mounting holes** (ADR-660, transcribed 2026-10-11 from the same
  tables): the rail's M3 counterbores at pitch P from an end distance of at
  least E, centred as on HIWIN's standard lengths L = (n - 1) P + 2E; the
  MGN block's four M3 holes on B x C at HIWIN's thread depth (3.5 mm MGN12,
  3 mm MGN9); the NEMA ICS 16 face's four tapped holes on the bolt square;
  the nut flanges' bolt circles, the SFU1204's six holes at 0 and +-45
  degrees each side of its flats (the DIN 69051 form B pattern). Tapped
  holes are modelled as open bores at the nominal size, as every catalog
  part's are.
- **The 20-series slot and its T-nut** (ADR-661, checked 2026-10-11).
  The slot is the B-type 6 mm slot of Misumi HFS5-2020 / Bosch Rexroth
  20x20: a 6.2 mm opening through a 1.8 mm lip, an undercut about 11 mm
  wide and 6.1 mm deep from the face. Misumi's HFS5-2020 table gives a
  section of 183 mm^2 at 0.5 kg/m; the modelled section is 191 mm^2. The
  M3 and M5 slide-in T-nuts are 10 mm long, 9.8 mm wide and 5 mm overall,
  with a 6 x 1 mm neck. That figure comes from the vendors' listings
  (e.g. VXB, "M5 sliding T-nuts for 2020 aluminum extrusion 6 mm"); one
  other listing gives 9.5 x 4.5, so the numbers vary by a few tenths
  between vendors. The 45-degree chamfer that clears the slot's flanks is
  Cadex's own. Before ADR-661 the modelled slot was 8 mm wide and 5 mm
  deep, and the T-nut was a 10 x 10 x 4.5 block. That block was wider than
  the undercut and taller than its 3.2 mm depth, so the catalog nut could
  not sit in the catalog slot. The wave-1 liquid-handler run found this
  (its `docs/rejected.md`).

## 8l. Catalog battery data `[Cadex-new, ADR-407]`

- **Gens Ace GEA2S100045D, 1000 mAh 2S 45C LiPo:** dimensions
  (72 × 36 × 13 mm), 64 g mass, C ratings and both leads as the
  manufacturer's [official store](https://genstattu.com/gens-ace-2s-1000mah-45c-lipo-battery-pack-with-deans-plug/)
  states them, checked 2026-09-25. `lib.battery` models the stated
  rectangular envelope only; the density is that mass over that envelope,
  and the 8.4 V full charge is the LiPo per-cell convention, not a
  sourced figure.

## 8m. Headless review rendering `[third-party, MIT, ADR-301]`

The CLI ships Three.js **r160**, copyright 2010–2023 three.js authors, MIT,
from upstream `build/three.module.min.js` as `review_static/three.module.js`.
Its full notice is `review_static/THREE-LICENSE.txt`. This pinned local copy
provides shared tone mapping, material lighting and shadow rendering without
runtime CDN access or an npm toolchain.

`review_static/environment.js` and the floor-only extract `floor.js` adapt
`neural-whoop/web/studio/environment.js` and `geometry.js` at commit
`31caeb28abb3bdab8d9030bfc91f0c3f48ffa63a`, copyright 2026 Theo, MIT.
`REFERENCE-LICENSE.txt` retains the complete notice. Changes use local imports,
allow the stage height to follow the CAD bounds, remove the 3 mm presentation
lift, make the environment floor front-sided for underside inspection, and
keep only the reference's dark palette (ADR-331): the light palette and the
theme setter are removed, so the module exports one `PALETTE` and no
`setTheme`. The light rig follows that reference's scene contract. Drone geometry, glyph
scaling, controls, dashboard and capture application code are not imported.
The sibling checkout is only a read-only comparison input; delivered Cadex
rendering is self-contained. Our scene/adapter code remains LGPL-2.1-or-later.

## 9. Where this goes

ADR-025 and ADR-030 record the intended endpoint: **one application we
own**, a derivative of but not dependent on FreeCAD. OCCT stays as the
geometry kernel. The FreeCAD application layer would be replaced by our own
binding (Phase 11). The Blender half of that endpoint arrived by subtraction
rather than replacement: the shell is deleted and the dashboard is the
interface (ADR-498). A desktop app, if one comes, copies the dashboard,
behind the unchanged cadexd protocol.

Phase 11 is not scheduled and blocks nothing. Until then this document
describes the truth: Cadex is one fork and roughly a hundred and fifty thousand
lines of our own (§1), and the parts that are not ours are the parts that make
it work.
