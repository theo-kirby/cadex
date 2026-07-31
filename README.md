<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="cadex-logo-white.png">
    <img src="cadex-logo-black.png" alt="Cadex" width="96">
  </picture>
</p>

# Cadex

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

![A ducted-fan drone frame in the Cadex viewport, its declared parameters as
sliders below, and the conversation that authored it on the
right](docs/cadex-example.png)

> **Status:** under active development, pre-release.

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
pixi run python -m pytest src/Mod/cadex/cadex_tests   # engine suite, no build needed
pixi run python -m pytest cli/tests                   # the CLI suite
pixi run test-release                                 # ctest (diff against
                                                      # build/ctest_baseline_failures.txt)
pixi run gate                                         # CADEX-BLENDER-GATE, the product gate
```

## Documentation

Start with [`CLAUDE.md`](CLAUDE.md) (repo map, commands, change policy) and
the doc set under [`docs/`](docs/):
[VISION](docs/VISION.md) · [ARCHITECTURE](docs/ARCHITECTURE.md) ·
[XSCRIPT](docs/XSCRIPT.md) · [INTEGRATION](docs/INTEGRATION.md) ·
[BLENDER](docs/BLENDER.md) · [CLI](docs/CLI.md) ·
[FREECAD](docs/FREECAD.md) · [BLENDER-TREE](docs/BLENDER-TREE.md) ·
[PROVENANCE](docs/PROVENANCE.md) ·
[ROADMAP](docs/ROADMAP.md) · [DECISIONS](docs/DECISIONS.md).
Packaging: [docs/cadex-release-packaging.md](docs/cadex-release-packaging.md).
Policies: [PRIVACY_POLICY](PRIVACY_POLICY.md) · [SECURITY](SECURITY.md).

## Credits

Cadex is a derivative work of two projects, and keeps importing from
neither's release stream — we delete from these trees rather than track them.

- The geometry kernel is [OCCT](https://dev.opencascade.org/) (LGPL-2.1),
  reached through a fork of the [FreeCAD
  project](https://github.com/FreeCAD/FreeCAD) and built on the work of the
  wider [FreeCAD community](https://forum.freecad.org/).
- The application shell is a fork of
  [Blender](https://projects.blender.org/blender/blender) (GPL-2.0+).
- The CadexLight and CadexDark themes are based on [OpenTheme by
  Obelisk79](https://github.com/obelisk79/OpenTheme).

Cadex is not affiliated with or endorsed by either project. Which code came
from where, under which licence, and what we changed is spelled out in
[docs/PROVENANCE.md](docs/PROVENANCE.md).
