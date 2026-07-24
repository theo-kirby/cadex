<p align="center">
  <img src="docs/images/cadex-mark.svg" width="96" alt="Cadex mark">
</p>

# Cadex

**Cadex is an AI-native CAD application.** You describe the part; the AI
authors a declarative **xscript** Python program; the program runs in a
sandboxed headless worker and only validated geometry reaches your document.
The script is the model — parameters surface as sliders you can drag without
the AI in the loop, and the document is rebuildable from the script.

Cadex is a FreeCAD fork distilled to a single engine and four capability
areas: **Part, Part Design, Sketcher, Assembly** (a minimal mesh area is
planned). There are no modeling toolbars and no workbench concept to learn —
chat, sliders, model tree, script.

> **Status:** under active development, pre-release. The current Qt shell is
> interim; the long-term shell is a Blender fork fed by a headless geometry
> service. See `docs/VISION.md` and `docs/ROADMAP.md`.

![Cadex workspace showing a turbocharger assembly and the AI assistant](docs/images/cadex-workspace.png)

## Build and run

Requires [pixi](https://pixi.sh). From the repo root:

```bash
pixi run initialize        # git submodules (first time)
pixi run configure         # CMake configure (debug; use configure-release for release)
pixi run build             # build (debug) — or: pixi run build-release
pixi run freecad           # launch (debug) — or: pixi run freecad-release
```

Artifacts land in `build/<config>/bin/`: `FreeCAD` (the app), `FreeCADCmd`
(headless — also the xscript worker host), `CadexGeometryWorker`.

Tests:

```bash
pixi run test                                            # ctest suite
pixi run python -m pytest src/Mod/cadex/cadex_tests      # cadex engine tests (headless, FreeCAD stubbed)
```

## Set up an AI provider

You need an API key (Anthropic or OpenAI), a ChatGPT subscription (via the
bundled Codex runtime), or an OpenAI-compatible endpoint (xAI, Ollama, other
local servers).

Open **Preferences → Cadex**, choose a provider, then either:

- **OS keyring (recommended):** paste the key, **Save Key**, **Validate**; or
- **A `.env` file** you select explicitly (`ANTHROPIC_API_KEY=` /
  `OPENAI_API_KEY=`); Cadex never searches for `.env` files.

Then **Fetch models**, pick a model and a supported reasoning effort, and
**Apply**. Key resolution order: process environment variable → selected
`.env` file → OS keyring (an exported shell variable overrides the others).
For xAI/Ollama, select the OpenAI provider and set the base URL
(`https://api.x.ai/v1` / `http://localhost:11434/v1`).

## Use it

1. Create or open a document and **save it** (the assistant needs a durable
   project home; conversations and program source live with the project).
2. Describe the part — dimensions, interfaces, material, constraints. Attach
   reference images or the current view if useful.
3. **Send.** While a turn runs, the input becomes **Steer**; **Stop** ends
   the run after the current step.
4. Drag parameter sliders to explore the design space — sliders re-run the
   program directly, no AI turn.

## Documentation

Start with [`CLAUDE.md`](CLAUDE.md) (repo map, commands, change policy) and
the doc set under [`docs/`](docs/):
[VISION](docs/VISION.md) · [ARCHITECTURE](docs/ARCHITECTURE.md) ·
[XSCRIPT](docs/XSCRIPT.md) · [FREECAD](docs/FREECAD.md) ·
[BLENDER](docs/BLENDER.md) · [INTEGRATION](docs/INTEGRATION.md) ·
[ROADMAP](docs/ROADMAP.md) · [DECISIONS](docs/DECISIONS.md).
Release packaging: [docs/cadex-release-packaging.md](docs/cadex-release-packaging.md).

## Credits

- The CadexLight and CadexDark themes are based on [OpenTheme by Obelisk79](https://github.com/obelisk79/OpenTheme).
- Cadex is built on the work of the [FreeCAD project](https://github.com/FreeCAD/FreeCAD) and the wider [FreeCAD community](https://forum.freecad.org/), whose CAD engine made this project possible.
