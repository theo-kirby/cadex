<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="cadex-logo-white.png">
    <img src="cadex-logo-black.png" alt="Cadex" width="96">
  </picture>
</p>

# Cadex

Verified against source: 2026-10-03

Author:
"Cadex is an experimental side project, far from production software.
I've always liked Blender's interface and UX more than those of traditional CAD softwares,
and even plenty of unrelated software. I also love its flexibility, extensibility,
and massive range of capability. The biggest downfall for me was always the
inability to do constraint based modeling easily, and the limitations of the armature
based rigging system instead of proper linkages and simulation. Since both Blender
and FreeCAD are open source, I figured why not try to mash them together and
greedily try to achieve the best of both worlds. Also making the whole thing be
drivable by an agent seemed like an obvious value add, since they are so capable now.
I make no claims towards its reliability nor robustness, though anecdotally I have
been quite satisfied. This project will forever be free and open source.
If you are looking for a more serious project with similar themes, I highly recommend 
checking out [VibeCAD](https://github.com/10-X-eng/vibecad) or [Smith](https://arche.co)"

AI:
**Cadex is an AI-native CAD app for designing robots and mechanisms, and
it is three things** ([ADR-500](docs/DECISIONS.md)):

1. **The engine** — a FreeCAD fork on OCCT, at the repo root. The AI
   authors a declarative **xscript** Python program; `cadexd`, a headless
   per-project service, runs it in sandboxed workers, and only validated
   geometry is accepted. The script *is* the model: its declared parameters
   rebuild without the AI in the loop, and the model is rebuildable from the
   script at any time. The engine builds, verifies, measures, renders,
   simulates and exports a design.
2. **The dashboard** — `./cadex review`, a browser page and the only UI.
   A person watches results there and steps in when needed.
3. **The agent** — the Claude Code CLI you are already logged into, driving
   the engine through one tool surface. There is no API key and no model
   loop of Cadex's own.

The owner uses Cadex almost entirely through autonomous runs, so the
product is built around that: the agent designs, the engine checks, and a
person reviews and lightly steers from a browser. There are no modeling
toolbars and no workbench concept to learn. Until 2026-10-03 Cadex also
had a Blender-based desktop shell; it is deleted (ADR-498), and the tag
`v1-blender-shell` is the last tree that has it.

**Cadex has dynamics and control built in.** The
mechanism you designed falls, collides and is actuated on
[MuJoCo](https://github.com/google-deepmind/mujoco); `assembly.mjcf` exports
it with *exact* OCCT inertias rather than the convex-hull guesses standard
MJCF authoring settles for; `assembly.task` states the control problem as
data; a trainer solves it — on a GPU box for a gait, or right on your own
CPU for a toy-scale mechanism; and `cadex evaluate` holds the policy to its
task's success spec and films it. See [docs/MUJOCO.md](docs/MUJOCO.md).

**The North Star** — the prompt this whole product is pointed at — is:
*"design me a quadruped robot, all 3D-printable, MG90 servos, and train it
to walk and wave."* One prompt, carried end to end by the agent: the parts,
the assembly, the MJCF export, the training dispatch, the policy
iteration — ending in a part sheet, print files, a BOM, a trained policy
and a gait video. Every vertical in this repository exists because that
sentence needs it.

> **Status:** under active development, pre-release — currently **0.1.0**.

Beyond dynamics, two more verticals are closed: **organic modelling**
([docs/ORGANIC.md](docs/ORGANIC.md)) and **structural analysis** — stress,
topology optimisation, and a skeleton fit that turns a carved density field
back into a *parametric script* a person can edit
([docs/STRUCTURAL.md](docs/STRUCTURAL.md)).

## Build and run

Requires [pixi](https://pixi.sh). The Blender shell is deleted (ADR-498),
so git-lfs, Xcode and its 1.3 GB library checkout are not needed. The old
application is tagged `v1-blender-shell`.

```bash
git clone <this repo> && cd cadex
pixi run setup-engine   # the one submodule the engine compiles
pixi run build-engine   # the headless engine (BUILD_GUI=OFF)
./cadex review --project <dir>   # the review dashboard over one project
```

`pixi run stage-engine` stages the engine payload into
`build/engine/cadex-engine-<version>-<os>-<arch>/`.

## How it fits together

Three parts in one repository. The engine and the other two are separated
by a process boundary:

- **the engine** (repo root, a FreeCAD fork) — `cadexd`, a per-project
  headless service speaking newline-delimited JSON over stdio. It runs
  xscript programs in sandboxed workers, produces BREP, and streams
  tessellation with face and edge ID maps back.
- **the dashboard** (`cli/cadex_cli/review_server.py` and
  `review_static/`) — a standard-library Python server, vanilla JS and the
  vendored three.js; no npm, no bundler, no framework. It reads the project
  directory, which is the truth. Its design spec is
  [docs/DASHBOARD.md](docs/DASHBOARD.md).
- **the agent** — Claude Code, run by the CLI (`cli/`) over one tool
  surface (`cli/cadex_cli/tools.py`) and one guidance source. The CLI
  finds an engine in the build tree or, staged, by reading its
  `cadex-engine.json` manifest.

And two directories that are deliberately none of the three:

- **`training/`** — the offboard PPO trainer. It is not part of
  the product: CMake never installs it, no payload carries it, and it cannot
  import Cadex. A gait needs a GPU box; a toy-scale mechanism trains on
  your own CPU in seconds to minutes
  ([training/SETUP.md](training/SETUP.md) §b). Either way one `.cxpolicy`
  file comes home and the engine verifies it; the engine verifies a policy
  and never produces one. [training/README.md](training/README.md).
- **`analysis/`** — the offboard structural analysis: a hex-grid FEA core,
  CalculiX as an arm's-length second opinion, a SIMP topology optimiser,
  and the skeleton fit that ends in a script rather than a mesh. Same
  contract as the trainer, plus one rule of its own: nothing in it may
  import a GPL package. [analysis/README.md](analysis/README.md).

The protocol between the engine and the CLI is pinned by tests on both the
request and the response side (`docs/INTEGRATION.md`), which is what keeps
either side replaceable.

## Use it

Everything runs headless; the dashboard is where you look
([`docs/CLI.md`](docs/CLI.md)).

```bash
./cadex -p "a mounting bracket for a NEMA17, 4 mm wall" --project ./b --out ./b/out
./cadex params --project ./b --set wall=6 --out ./b/wall6   # no AI, no tokens
./cadex -p "make the fins 20% thinner" --project ./b --resume
./cadex review --project ./b    # watch it in a browser
```

One expensive turn writes a *parametric* script; after that a loop sweeps
its parameters and re-exports STEP/STL for the price of a rebuild, so an
external simulator can drive the design and the model is asked only when the
shape must change.

## Tests

```bash
pixi run test-engine                                  # engine suite, no build needed
                                                      # (the MJX-gated skips are by design)
pixi run python -m pytest cli/tests                   # the CLI suite
pixi run test-release                                 # ctest (diff against
                                                      # build/ctest_baseline_failures.txt)
```

## Documentation

Start with [`AGENTS.md`](AGENTS.md) (repo map, commands, change policy) and
the doc set under [`docs/`](docs/):
[VISION](docs/VISION.md) · [ARCHITECTURE](docs/ARCHITECTURE.md) ·
[XSCRIPT](docs/XSCRIPT.md) · [MUJOCO](docs/MUJOCO.md) ·
[ORGANIC](docs/ORGANIC.md) · [STRUCTURAL](docs/STRUCTURAL.md) ·
[INTEGRATION](docs/INTEGRATION.md) ·
[DASHBOARD](docs/DASHBOARD.md) · [CLI](docs/CLI.md) · [FREECAD](docs/FREECAD.md) ·
[PROVENANCE](docs/PROVENANCE.md) ·
[ROADMAP](docs/ROADMAP.md) · [DECISIONS](docs/DECISIONS.md).
The trainer: [training/README.md](training/README.md).
Packaging: [docs/cadex-release-packaging.md](docs/cadex-release-packaging.md).
Policies: [PRIVACY_POLICY](PRIVACY_POLICY.md) · [SECURITY](SECURITY.md).

## Credits

Cadex is a derivative work of FreeCAD, and does not track its release
stream — we delete from the tree rather than merge into it.
It also depends on two kernels it does *not* fork, because we intend to keep
them.

- The geometry kernel is [OCCT](https://dev.opencascade.org/) (LGPL-2.1),
  reached through a fork of the [FreeCAD
  project](https://github.com/FreeCAD/FreeCAD) and built on the work of the
  wider [FreeCAD community](https://forum.freecad.org/).
- Until 2026-10-03 the application shell was a fork of
  [Blender](https://projects.blender.org/blender/blender) (GPL-2.0+). It is
  deleted (ADR-498), and no Blender code remains.
- The dynamics kernel is
  [MuJoCo](https://github.com/google-deepmind/mujoco) (Apache-2.0), kept
  upstream and unmodified and redistributed inside the engine payload.
  Cadex is not affiliated with or endorsed by the MuJoCo project.
- The CadexLight, CadexDark and CadexMono Qt themes were based on
  [OpenTheme by Obelisk79](https://github.com/obelisk79/OpenTheme)
  (LGPL-2.1); they went with `src/Gui` (ADR-214), and NOTICE keeps the
  credit.

Cadex is not affiliated with or endorsed by FreeCAD or Blender. Which code came
from where, under which licence, and what we changed is spelled out in
[docs/PROVENANCE.md](docs/PROVENANCE.md).

## License

**LGPL-2.1-or-later.** The root [`LICENSE`](LICENSE) is FreeCAD's,
unchanged. Since the Blender shell was deleted (ADR-498) the repository
carries no GPL code, and the licensing suite holds it that way
([docs/PROVENANCE.md §7](docs/PROVENANCE.md)).

Third-party attribution lives in [`NOTICE`](NOTICE); the component-level
license map — vendored trees, the conda-forge payload, the one
redistributed pypi wheel — is
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md). A staged engine
payload carries all of that at its root, plus a per-package `licenses/`
directory with a machine-readable `MANIFEST.json`.
