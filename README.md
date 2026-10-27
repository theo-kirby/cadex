<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="cadex-logo-white.png">
    <img src="cadex-logo-black.png" alt="Cadex" width="96">
  </picture>
</p>

# Cadex

Verified against source: 2026-10-27

**Describe a robot or mechanism to your agent; get back a design you can
build and a policy that moves it.**

Cadex is a headless CAD engine for robots and mechanisms, built to be driven
by the AI agent you already use (Claude Code, Codex, Pi or any MCP client).
The agent writes one parametric Python script; Cadex builds it into exact
OCCT geometry, checks it, renders it, exports it, simulates it on MuJoCo and
verifies the control policies trained on it. You watch the whole thing in a
read-only browser dashboard.

> **Status:** pre-release, **0.2.0** ([`VERSION`](VERSION),
> [release notes](docs/releases/)); 0.3.0 is planned in
> [`docs/ROADMAP.md`](docs/ROADMAP.md). Linux x86-64 is the tested platform;
> macOS arm64 passes CI but is not tried by hand; Windows is unsupported.

## What it is

Three parts in one repository, and nothing else ([ADR-500](docs/DECISIONS.md)):

| Part | Where | What it does |
|---|---|---|
| **The engine** | repo root, `src/Mod/cadex/` | A FreeCAD fork on OCCT. `cadexd`, a per-project headless service, runs the project script in sandboxed workers and accepts only validated geometry. Five domains (part, partdesign, sketcher, mesh, assembly); the assembly domain also carries dynamics, MJCF export with exact inertias, tasks, gait references and policy rollouts. |
| **The dashboard** | `./cadex app` | The only UI, and read-only: model viewer, outliner, revisions, drawings, training curves, rollout playback. Standard-library Python, vanilla JS and vendored three.js. |
| **The agent bindings** | `cadex mcp`, `cadex guidance` | One MCP tool surface and one guidance text (a domain-neutral base plus optional styles: `printed-legged-robot`, `creature`, `gantry-machine`, `vehicle`, `product`). Cadex runs no model and holds no API key. |

Beside the product, not part of it: [`training/`](training/README.md), the
offboard PPO trainer (CPU for toy mechanisms, a GPU for gaits), and
[`analysis/`](analysis/README.md), offboard stress, topology optimisation and
a skeleton fit that ends in an editable script.

The script is the model: delete everything else and it rebuilds. Its
declared parameters rebuild with no agent at all (`cadex params`), and a
trained policy is an asset the engine verifies before it plays it.

## Quick start

Requires [pixi](https://pixi.sh).

```bash
git clone <this repo> && cd cadex
pixi run setup-engine && pixi run build-engine   # the headless engine
pixi run app                                     # dashboard at http://127.0.0.1:8765/

# point your agent at a project, then ask it for something
claude mcp add cadex -- "$PWD/cadex" mcp --project ~/cadex-projects/bracket
#   "a mounting bracket for a NEMA17, 4 mm wall"

# change a declared parameter without the agent
./cadex params --project ~/cadex-projects/bracket --set wall=6 --out /tmp/wall6
```

The dashboard serves every project under `~/cadex-projects` (or
`--projects` / `CADEX_PROJECTS`) on 127.0.0.1; put `tailscale serve` in
front of it to watch from another device. `./cadex --help` lists the rest:
`export`, `render`, `hero`, `section`, `clearance`, `train`, `evaluate`,
`smoke` and more ([docs/CLI.md](docs/CLI.md)).

## Tests

```bash
pixi run test-engine                        # engine contracts, no build needed
pixi run python -m pytest cli/tests         # CLI, tool surface, HTTP API, dashboard
pixi run test-release                       # the inherited FreeCAD ctest
```

The suites pin contracts, not coverage ([ADR-725](docs/DECISIONS.md)):
the protocol, the tool surface, the HTTP API, the licence rule, the offboard
boundaries and the read-only dashboard. Behaviour is verified by running it.

## Documentation

- [`docs/VISION.md`](docs/VISION.md): what Cadex is for, its principles and non-goals.
- [`docs/ROADMAP.md`](docs/ROADMAP.md): where it stands and what's next.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): how it is built.
- [`docs/XSCRIPT.md`](docs/XSCRIPT.md): the scripting model.
- [`docs/CLI.md`](docs/CLI.md): commands and the `--json` envelope.
- [`docs/INTEGRATION.md`](docs/INTEGRATION.md): the cadexd protocol.
- [`docs/DASHBOARD.md`](docs/DASHBOARD.md): the dashboard's design spec.
- The capabilities: [dynamics and control](docs/MUJOCO.md), [organic modelling](docs/ORGANIC.md), [structural analysis](docs/STRUCTURAL.md) and [design language](docs/DESIGN-LANGUAGE.md).
- [`docs/DECISIONS.md`](docs/DECISIONS.md): every decision, ADR by ADR.
- [`AGENTS.md`](AGENTS.md): the contract for agents working *on* this repo.

## About

*From the author:* Cadex is an experimental side project, far from
production software. It began as an attempt to combine Blender's interface
with FreeCAD's constraint-based modelling, and became a headless engine that
your own agent drives, with a browser page to watch it work. I make no claims
about its reliability or robustness, though anecdotally I have been quite
satisfied. It will always be free and open source. If you want a more
serious project with similar themes, look at
[VibeCAD](https://github.com/10-X-eng/vibecad) or [Smith](https://arche.co).

## Credits and license

**LGPL-2.1-or-later**, with no GPL code ([`LICENSE`](LICENSE),
[docs/PROVENANCE.md](docs/PROVENANCE.md)). Cadex is a derivative of
[FreeCAD](https://github.com/FreeCAD/FreeCAD) and is built on two kernels it
keeps upstream: [OCCT](https://dev.opencascade.org/) (LGPL-2.1) for geometry
and [MuJoCo](https://github.com/google-deepmind/mujoco) (Apache-2.0) for
dynamics. Until 2026-10-03 its desktop shell was a Blender fork; that code
is deleted (ADR-498), and tag `v1-blender-shell` keeps it. Cadex is not
affiliated with or endorsed by FreeCAD, Blender or MuJoCo.
Attribution: [`NOTICE`](NOTICE) and
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md). Policies:
[`SECURITY.md`](SECURITY.md), [`PRIVACY_POLICY.md`](PRIVACY_POLICY.md).
