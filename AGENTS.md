# AGENTS.md — Agent Entry Point

Verified against source: 2026-10-03. **This is the single agent contract.**
`CLAUDE.md` only imports it (`@AGENTS.md`), so there is one file to read and
one to edit (ADR-137).

## What Cadex is

Cadex is an AI-native CAD app for designing robots and mechanisms, and it is
**three things** (ADR-500):

1. **The engine**, at the repo root — a FreeCAD fork on OCCT. The AI authors
   a declarative **xscript** project script; `cadexd`, a per-project
   headless service speaking NDJSON over stdio, runs it in sandboxed
   `FreeCADCmd` workers that produce detached BREP and stream tessellation
   back. Five domains: partdesign, sketcher, part, mesh, assembly — the
   assembly one also carrying dynamics on MuJoCo, MJCF export, tasks,
   policies and rollouts (ADR-102, `docs/MUJOCO.md`). It builds, verifies,
   measures, renders, simulates and exports a design from its script.
2. **The dashboard**, `./cadex review` (`cli/cadex_cli/review_server.py`
   and `review_static/`) — the only UI. A person watches results there and
   steps in when needed. A standard-library server, vanilla JS and the
   vendored three.js: no npm, no bundler, no framework.
3. **The agent** — the Claude Code CLI the user is already logged into.
   **Claude Code is the only harness** (ADR-497). It drives
   the engine through one tool surface (`cli/cadex_cli/tools.py`) over an MCP
   stdio shim, with one guidance source (`CadexAgentGuidance.md` plus
   `agent.system_prompt`). Cadex has no API key, provider SDK or model loop
   of its own. `./cadex -p "…"` runs one turn; `./cadex params --set k=v`
   sweeps parameters with no model in the loop.

**This repository is the whole product** (ADR-030): clone it, `pixi run
setup-engine && pixi run build-engine`, and you have all three. The Blender
shell is deleted (ADR-498); tag `v1-blender-shell` is the last tree with it,
and the repository carries no GPL code.

Beside the product, and **not** the engine: `training/`, the offboard PPO
trainer (ADR-084), and `analysis/`, offboard stress, topology optimisation
and a strut-graph fit that emits a **parametric xscript**, not a mesh
(ADR-141, ADR-147). `analysis/` reaches the engine only by running
`./cadex` as a subprocess (ADR-142).

**Do not start** a replacement engine (Phase 11, a pybind11 binding on
OCCT) or a desktop app (which, if built, copies the dashboard). Both stay
available behind the test-pinned cadexd protocol; what is live is
subtraction from the inherited tree, in place.

Read `docs/VISION.md` before designing anything.

## Read this first

| Doc | What it answers |
|---|---|
| `STATE.md` | **What is true now** and the frontier. Generated from the state graph — never hand-edit. Cheapest orientation in the repo. |
| `.hypergraph/AGENTS.md` | The Hypergraph protocol here: the two graphs, the roots, the epoch. |
| `docs/VISION.md` | What the product is; principles; non-goals. **Authoritative.** |
| `docs/ARCHITECTURE.md` | What exists today: pipeline, file map, project store. |
| `docs/XSCRIPT.md` | The scripting model. |
| `docs/ROADMAP.md` | Phases, status checkboxes, exit criteria. |
| `docs/INTEGRATION.md` | **The process contract**: the cadexd protocol (test-enforced both ways) and the engine payload. |
| `docs/CLI.md` | The CLI: subcommands, exit codes, the `--json` envelope. |
| `docs/DASHBOARD.md` | The dashboard's design spec (ADR-501): hierarchy, type scale, the dark palette and floor shared by chrome, viewport and renders. Change the page and this doc together. |
| `docs/MUJOCO.md`, `docs/ORGANIC.md`, `docs/STRUCTURAL.md` | The verticals: dynamics and control (§7 is the drawing-to-trained-policy walkthrough), organic modelling, structural analysis. |
| `docs/DESIGN-LANGUAGE.md` | How a Cadex robot should look (ADR-479), scored with the judge frozen in `docs/probes/orun1/README.md`. |
| `docs/DECISIONS.md` | ADR log. Append an entry for every removal or direction change. |
| `docs/PROVENANCE.md`, `docs/FREECAD.md` | Licences and credit; the inherited-tree ledger (kept / disabled / deleted). |
| `docs/SHELL-PARITY.md` | Where each part of the deleted shell went: ported, covered, or dropped. |
| `docs/cadex-release-packaging.md` | The engine payload: what ships, how it is gated. |
| `training/README.md`, `training/SETUP.md` | The offboard trainer, and four ways to run it (ADR-089). |
| `analysis/README.md` | The offboard structural analysis and its licence rule. |
| `docs/IDEAS.md`; `docs/history/` | Parking lot; superseded docs (never cite as current). |

Each doc carries a `Verified against source:` date and keeps *exists today*
apart from *target*. When you change behaviour, update the doc and its date
in the same PR.

## Repo map

```
cadex                     the CLI shim: ./cadex -p "..."  (docs/CLI.md)
cli/cadex_cli/            the CLI, the agent's tools, and the dashboard (LGPL)
cli/tests/                its suite; engine-needing tests skip without an engine
src/Mod/cadex/            the engine (file map in docs/ARCHITECTURE.md)
src/Mod/cadex/cadex_tests/  engine suite (headless; FreeCAD stubbed in conftest.py)
src/Mod/{Part,PartDesign,Sketcher,Assembly,Mesh,MeshPart}  capability substrate
src/{App,Base,Main}       inherited FreeCAD core (conservative zone)
training/                 offboard PPO trainer (ADR-084) -- not the engine
analysis/                 offboard structural analysis (ADR-141) -- not the engine
package/engine/           the engine payload build (ADR-023)
build/release/bin/        FreeCADCmd, CadexGeometryWorker (no application)
```

## Commands

```bash
pixi run setup-engine && pixi run build-engine   # the whole setup (ADR-060)
pixi run app                                     # the dashboard over ~/cadex-projects
./cadex -p "a 40x25x15 mm bracket with a 6 mm bore" --project ./b --out ./b/out --json
./cadex params --project ./b --set bore=8 --out ./b/v2   # spends no tokens
./cadex -p "add a 2 mm fillet" --project ./b --resume

pixi run test-engine                       # THE engine suite, no build needed
pixi run python -m pytest cli/tests        # the CLI and dashboard suite
pixi run build-release                     # C++/CMake (GUI is always OFF)
pixi run test-release                      # inherited ctest, NOT the above
pixi run stage-engine                      # payload -> build/engine/cadex-engine-<v>-<os>-<arch>/
pixi run cadexd                            # a standalone engine on stdio
pixi run python src/Mod/cadex/cadex_tests/cadexd_latency_integration.py  # slider latency bar
pixi run python analysis/topology.py --self-check   # analysis/README.md has the rest
```

Engine builds have no GUI (ADR-022, ADR-213); `BUILD_GUI=ON` is rejected.
Python-only changes under `src/Mod/cadex/` need `pixi run build-engine`
before the CLI's engine-needing tests see them, and `pixi run stage-engine`
before the payload does.

## Change policy

The philosophy is **remove more than we add** (`docs/VISION.md`).

- **`src/Mod/cadex/**`, `cli/**`, `training/**`, `analysis/**`, `docs/**`
  are ours — subtractive changes encouraged.** Every removal gets a
  `docs/DECISIONS.md` entry and is verified by build + tests in the same PR.
- **`training/` and `analysis/` are not the engine** (ADR-084, ADR-141): no
  CMake rule references them, no payload carries them, nothing in them
  enters `pixi.toml`; their exact pins live in their own `requirements.txt`.
  Tests assert all three. `analysis/requirements.txt` is three pins and
  stays three (ADR-143), and **`analysis/` may not import a GPL package** —
  test-enforced; CalculiX runs as a subprocess and `mmapy` is barred.
- **The repository is LGPL and carries no GPL code** (ADR-498,
  `docs/PROVENANCE.md` §7); `test_licensing_compliance.py` fails if a
  GPL-declared file returns. The shell at `v1-blender-shell` may be *read*;
  copying a line of it into `cli/` relicenses it (ADR-061).
- **Inherited FreeCAD core (`src/App`, `src/Base`) — conservative.**
  Smallest possible diff, no drive-by cleanup, call it out in the PR. A
  change that *reduces* the fork's delta against upstream is welcome
  (ADR-022). `src/Gui` is deleted (ADR-214) and stays deleted.
- **`src/Mod/<unused trees>`** go only by the removal protocol
  (`docs/FREECAD.md` §3): dependency audit, disable commit, delete commit,
  ADR.
- **Never vendor a prebuilt library**, or commit secrets or machine paths.
- **The agent's tool surface is a contract**: change what
  `test_project_tool_surface.py` pins only with its tests and an ADR.

## Methodology

1. **Trust the docs, then verify.** If code and doc disagree, the code wins
   — fix the doc in your PR.
2. **Verify by running.** `src/Mod/cadex/`: `pixi run test-engine` minimum.
   `cli/`: `pixi run python -m pytest cli/tests` too — it *skips* its
   engine-needing half on a bare checkout, so a green run there proves less
   than it looks. C++/CMake: `pixi run build-release`, and diff ctest
   against `build/ctest_baseline_failures.txt` (~160 environmental
   failures). Protocol or payload: the packaged gate,
   `CADEX_ENGINE_ROOT=<payload> pytest
   src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py` — a passing source
   tree proves nothing about a payload (ADR-023). Report failures honestly.
3. **Small, owner-mergeable PRs.** One logical change, with outcome, risk
   and test evidence.
4. **Removals are normal work**, logged and proved. Resurrecting deleted
   functionality is a direction change: ADR and owner sign-off.
5. **No UI in the engine.** No Coin3D, no Qt, no workbench concepts under
   `src/`. A widget belongs in the dashboard (`cli/cadex_cli/review_static/`).
6. **The protocol keeps the halves swappable.** Requests (`OP_ARG_SPECS`)
   and responses (the ADR-027 goldens) are pinned. Changing
   `CadexdProtocol.OP_ARG_SPECS` changes `docs/INTEGRATION.md`'s op table in
   the same commit (test-enforced) and the CLI's client in the same PR.
   One repo is not a licence to reach across the boundary any other way.
7. **Update `docs/ROADMAP.md` checkboxes** when a work item lands.

### Dynamics invariants (ADR-102)

- `CadexDynamics.py` is reachable from the sandboxed worker but never from
  `cadexd` (`test_engine_purity_guardrails` asserts the import closure).
- **No `jax` or `mjx` under `src/Mod/cadex` or in a staged payload**
  (ADR-084): the engine verifies a policy but never produces one.
  `training/cadex_train.py` imports only the standard library at module
  scope; `CARRIED_PYPI_PACKAGES` (`package/rattler-build/scripts/
  relocate_conda_environment.py`, how mujoco reaches the payload) stays one
  entry long.
- The `test_dynamics_*` suites run headless with no build; MJX-gated tests
  skip under pixi by design and run from a `training/requirements.txt` venv.
- There is one branch; the old `MJC` ref points at its merge and takes no
  commits.

<!-- hypergraph:begin -->
## Hypergraph protocol

This repo's memory lives in two graphs under `.hypergraph/` (see `.hypergraph/AGENTS.md`)
— an append-only record of what happened, and a distilled projection of what is true
now, with every claim citing the evidence it rests on. Work that is not recorded did
not happen, and a dead end recorded is worth as much as a success:

1. **Orient on arrival**: run the `hypergraph-orient` skill or read `STATE.md` —
   the frontier (open/broken/blocked) is what matters now.
2. **Record every unit of work** (features, fixes, experiments, dead ends,
   decisions): the `hypergraph-record` skill — one causally-parented record node
   with a `## State Impact` section. Unrecorded work is invisible to the project.
   This **complements** `docs/DECISIONS.md` rather than replacing it: the ADR log
   stays the narrative record of decisions, and substantial work earns both.
3. **Never write state nodes**; declare impacts and let the
   `hypergraph-reconcile` skill fold them. `STATE.md` is generated — never
   hand-edit it.
4. **Verify before finishing**: `hypergraph export` + `hypergraph check` must
   exit 0. If it says this project's copies are behind the CLI, run
   `hypergraph upgrade` — the skills and this block are copies, and `uv tool
   upgrade` cannot see them.

The record graph's epoch marker is `winter-rain-7897` (2026-08-09); the 14 nodes
before it are prehistory, distilled from the repo and an author interview.
<!-- hypergraph:end -->

## Unattended runs

This repo is driven by Ouroboros, an unattended agent loop. Before you start, stop, or read one, read [`.ouroboros/AGENTS.md`](.ouroboros/AGENTS.md); past runs are in [`.ouroboros/RUNS.md`](.ouroboros/RUNS.md).
