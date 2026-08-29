<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="cadex-logo-white.png">
    <img src="cadex-logo-black.png" alt="Cadex" width="96">
  </picture>
</p>

# Cadex

Verified against source: 2026-08-29

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
**Cadex is an AI-native CAD application.** You describe the part; the AI
authors a declarative **xscript** Python program; the program runs in a
sandboxed headless worker, and only validated geometry reaches your model.
The script *is* the model — parameters surface as sliders you can drag
without the AI in the loop, and the model is rebuildable from the script at
any time.

There are no modeling toolbars and no workbench concept to learn. Chat,
sliders, model tree, script, viewport.

**Cadex has dynamics and control built in.** The
mechanism you designed falls, collides and is actuated on
[MuJoCo](https://github.com/google-deepmind/mujoco); `assembly.mjcf` exports
it with *exact* OCCT inertias rather than the convex-hull guesses standard
MJCF authoring settles for; `assembly.task` states the control problem as
data; a trainer solves it — on a GPU box for a gait, or right on your own
CPU for a toy-scale mechanism, with the reward curve drawing itself live in
the editor while it runs; and `assembly.rollout` plays the result back in
the viewport. See [docs/MUJOCO.md](docs/MUJOCO.md).

**The North Star** — the prompt this whole application is pointed at — is:
*"design me a quadruped robot, all 3D-printable, MG90 servos, and train it
to walk and wave."* One prompt, carried end to end by the agent: the parts,
the assembly, the MJCF export, the training dispatch, the policy
iteration — ending in a part sheet, print files, a BOM, a trained policy
and a gait video. Every vertical in this repository exists because that
sentence needs it. The whole arc has been rehearsed locally at toy scale
([docs/MUJOCO.md §7b](docs/MUJOCO.md)); **0.1.0** roughly means the
quadruped version of it works.

This lived on a branch called `MJC` until 2026-08-01. It was merged once
the cost was measured rather than assumed: 53.5 MB on a 3.3 GB application,
and nothing at all at runtime for anyone who never calls it
([ADR-102](docs/DECISIONS.md)).

![A ducted-fan drone frame in the Cadex viewport, its declared parameters as
sliders below, and the conversation that authored it on the
right](docs/cadex-example.png)

> **Status:** under active development, pre-release — currently **0.0.6**
> (the version the window chrome and the landing screen show).

The window is the product now: it opens on a **landing screen** with an
example project (a ducted-fan drone shipped in the bundle), a native menu
bar, and a chat column that is already live — typing into it dismisses the
page. Six Cadex editors replace Blender's: **Chat**, **Parameters**,
**Wiring**, **Training** (a run's numbers *and* its reward curve, polled
off one JSON file), **Live** (the accepted policy running endlessly in a
resident worker, with shove operators to test it), and the policy rollout
playing as ordinary baked keyframes. Beyond dynamics, two more verticals
are closed: **organic modelling** ([docs/ORGANIC.md](docs/ORGANIC.md)) and
**structural analysis** — stress, topology optimisation, and a skeleton
fit that turns a carved density field back into a *parametric script* a
person can edit ([docs/STRUCTURAL.md](docs/STRUCTURAL.md)).

## Build and run

Requires [pixi](https://pixi.sh) and **git-lfs**, plus a host toolchain for
the shell — on macOS that is the Xcode command line tools and
`brew install cmake ninja git-lfs`.

Install git-lfs *before* cloning. The shell tree keeps binary assets in LFS
(~790 MB, mostly `shell/tests/files/`, but also
`shell/release/datafiles/icons/` which the build installs and the
application reads). Clone without it and you get pointer text files where
those should be.

```bash
git lfs install
git clone <this repo> && cd cadex
pixi run setup      # check out the shell's prebuilt libraries (~1.3 GB)
pixi run app        # build the engine, the payload and the shell, then launch
```

The first build compiles two large C++ projects. On a machine with a cold
compiler cache that takes hours; measured end to end on an M-series Mac with
a warm `ccache` it is about 21 minutes (clone 9 s, setup 43 s, engine
5 min 27 s, payload 42 s, shell 14 min). After that it is incremental.
`pixi run app` re-runs each step, so it is also the everyday "build what
changed and launch it" command.

If you want the steps separately:

```bash
pixi run build-engine   # the headless engine (BUILD_GUI=OFF)
pixi run stage-engine   # -> build/engine/cadex-engine-<version>-<os>-<arch>/
pixi run build-shell    # the shell, with that engine installed into the bundle
pixi run gate           # the product gate against the built bundle
```

## How it fits together

Two halves in one repository, separated by a process boundary:

- **the engine** (repo root, a FreeCAD fork) — `cadexd`, a per-project
  headless service speaking newline-delimited JSON over stdio. It runs
  xscript programs in sandboxed workers, produces BREP, and streams
  tessellation with face and edge ID maps back.
- **the shell** (`shell/`, a Blender fork) — the application. It carries
  the engine inside its own bundle and finds it by reading a
  `cadex-engine.json` manifest, so a built application needs no
  configuration at all.

And two directories that are deliberately neither:

- **`training/`** — the offboard PPO trainer. It is not part of
  the product: CMake never installs it, no payload carries it, and it cannot
  import Cadex. A gait needs a GPU box; a toy-scale mechanism trains on
  your own CPU in seconds to minutes
  ([training/SETUP.md](training/SETUP.md) §b). Either way one `.cxpolicy`
  file comes home and the engine verifies it — there is no train button and
  nothing to press; the engine verifies a policy and never produces one.
  [training/README.md](training/README.md).
- **`analysis/`** — the offboard structural analysis: a hex-grid FEA core,
  CalculiX as an arm's-length second opinion, a SIMP topology optimiser,
  and the skeleton fit that ends in a script rather than a mesh. Same
  contract as the trainer, plus one rule of its own: nothing in it may
  import a GPL package. [analysis/README.md](analysis/README.md).

The protocol between them is pinned by tests on both the request and the
response side (`docs/INTEGRATION.md`), which is what keeps either half
replaceable.

The AI is the Claude Code CLI — driven from inside the shell, or by `cli/`
below. There is no API-key configuration either way.

## Without a screen

`cli/` is a second front end and a third client of the same protocol — no
Blender, no display, no shell code ([`docs/CLI.md`](docs/CLI.md)). It needs
a built engine and nothing else.

```bash
./cadex -p "a mounting bracket for a NEMA17, 4 mm wall" --project ./b --out ./b/out
./cadex params --project ./b --set wall=6 --out ./b/wall6   # no AI, no tokens
./cadex -p "make the fins 20% thinner" --project ./b --resume
```

One expensive turn writes a *parametric* script; after that a loop sweeps
its parameters and re-exports STEP/STL for the price of a rebuild, so an
external simulator can drive the design and the model is asked only when the
shape must change.

## Use it

1. Create or open a file and **save it** — the assistant needs a durable
   project home; conversations and the model script live with the project.
2. Describe the part: dimensions, interfaces, material, constraints. Attach
   reference images or the current view if useful.
3. **Send.** Click a face in the viewport to pin it; pins attach to your
   next message as ground truth for which face you mean.
4. Drag parameter sliders to explore the design space — sliders re-run the
   script through the engine directly, with no AI turn.

## Tests

```bash
pixi run test-engine                                  # engine suite, no build needed
                                                      # (the MJX-gated skips are by design)
pixi run python -m pytest cli/tests                   # the CLI suite
pixi run test-release                                 # ctest (diff against
                                                      # build/ctest_baseline_failures.txt)
pixi run gate                                         # CADEX-BLENDER-GATE, the product gate
```

## Documentation

Start with [`AGENTS.md`](AGENTS.md) (repo map, commands, change policy) and
the doc set under [`docs/`](docs/):
[VISION](docs/VISION.md) · [ARCHITECTURE](docs/ARCHITECTURE.md) ·
[XSCRIPT](docs/XSCRIPT.md) · [MUJOCO](docs/MUJOCO.md) ·
[ORGANIC](docs/ORGANIC.md) · [STRUCTURAL](docs/STRUCTURAL.md) ·
[INTEGRATION](docs/INTEGRATION.md) ·
[BLENDER](docs/BLENDER.md) · [CLI](docs/CLI.md) ·
[FREECAD](docs/FREECAD.md) · [BLENDER-TREE](docs/BLENDER-TREE.md) ·
[PROVENANCE](docs/PROVENANCE.md) ·
[ROADMAP](docs/ROADMAP.md) · [DECISIONS](docs/DECISIONS.md).
The trainer: [training/README.md](training/README.md).
Packaging: [docs/cadex-release-packaging.md](docs/cadex-release-packaging.md).
Policies: [PRIVACY_POLICY](PRIVACY_POLICY.md) · [SECURITY](SECURITY.md).

## Credits

Cadex is a derivative work of two projects, and keeps importing from
neither's release stream — we delete from these trees rather than track them.
It also depends on two kernels it does *not* fork, because we intend to keep
them.

- The geometry kernel is [OCCT](https://dev.opencascade.org/) (LGPL-2.1),
  reached through a fork of the [FreeCAD
  project](https://github.com/FreeCAD/FreeCAD) and built on the work of the
  wider [FreeCAD community](https://forum.freecad.org/).
- The application shell is a fork of
  [Blender](https://projects.blender.org/blender/blender) (GPL-2.0+).
- The dynamics kernel is
  [MuJoCo](https://github.com/google-deepmind/mujoco) (Apache-2.0), kept
  upstream and unmodified and redistributed inside the engine payload.
  Cadex is not affiliated with or endorsed by the MuJoCo project.
- The CadexLight, CadexDark and CadexMono themes are based on [OpenTheme by
  Obelisk79](https://github.com/obelisk79/OpenTheme) (LGPL-2.1).

Cadex is not affiliated with or endorsed by either project. Which code came
from where, under which licence, and what we changed is spelled out in
[docs/PROVENANCE.md](docs/PROVENANCE.md).

## License

Two licenses share this repository, one per fork, separated by the same
process boundary that separates the halves ([docs/PROVENANCE.md
§7](docs/PROVENANCE.md)):

- **The engine** — everything outside `shell/` — is
  **LGPL-2.1-or-later**; the root [`LICENSE`](LICENSE) is FreeCAD's,
  unchanged.
- **The shell** — `shell/` — is **GPL-2.0-or-later** in source form
  ([`shell/COPYING`](shell/COPYING)); the shipped binary is distributed
  under GPL version 3 or later terms, as Blender's own binaries are,
  because Apache-2.0 components in the bundle require it.

Third-party attribution lives in [`NOTICE`](NOTICE); the component-level
license map — vendored trees, the conda-forge payload, the one
redistributed pypi wheel — is
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md). A shipped bundle
carries all of that plus a per-package `licenses/` directory with a
machine-readable `MANIFEST.json`, under `Cadex.app/Contents/Resources/cadex/`.
