# AGENTS.md — Agent Entry Point

Verified against source: 2026-10-03. **This is the single agent contract.**
`CLAUDE.md` exists only to import it (`@AGENTS.md`) and holds nothing of its
own, so there is one file to read and one file to edit — which is what ADR-005
asked for, reached from the other direction (ADR-137).

Cadex is an AI-native CAD app. **This repository is the whole product**
(Phase 13a, ADR-030): clone it, `pixi run setup-engine && pixi run build-engine`, and you
have a running engine and CLI. The Blender shell is deleted (ADR-498); the
tag `v1-blender-shell` is the last tree that has it.

**Dynamics and control are built in** (ADR-102): Cadex simulates mechanisms
on MuJoCo, exports them as MJCF, and plays back policies trained on them.
This lived on a branch called `MJC` until 2026-08-01, when it was measured
and merged — 53.5 MB on a 3.3 GB application, and nothing at all at runtime
for a user who never calls it. **There is one branch.** The arc itself is
`docs/MUJOCO.md`; ADR-102 records why the split ended and what it cost.

Two halves, one repo, separated by a process boundary rather than a
repository boundary:

- **the engine**, at the repo root — a FreeCAD fork. The AI authors
  declarative **xscript** Python programs, and `cadexd`, a per-project
  headless service speaking NDJSON over stdio, runs them in sandboxed
  `FreeCADCmd` workers that produce detached BREP, publish into an
  ephemeral document, and stream tessellation back. Five domains:
  partdesign, sketcher, part, mesh, assembly — the assembly one also
  carrying dynamics, MJCF export, tasks, policies and rollouts.
- **the CLI and the dashboard**, under `cli/` — the only front end, a
  client of the protocol in `docs/INTEGRATION.md` (ADR-061). `./cadex -p
  "…"` runs one AI turn against a project; `./cadex params --set k=v`
  sweeps its parameters with no model in the loop at all; `./cadex review`
  serves the dashboard (`cli/cadex_cli/review_server.py`).
- **`training/`**, at the repo root — the offboard PPO trainer. Not part of
  the engine, in no payload, copied to a machine with a GPU (ADR-084).
- **`analysis/`**, beside it — the offboard structural analysis: stress,
  topology optimisation and shape search (ADR-141, ADR-143,
  `docs/STRUCTURAL.md`, all five slices closed). Same contract as
  `training/`, and one rule of its own: nothing in it may import a GPL
  package. It reaches the engine only by running `./cadex` as a subprocess
  (ADR-142), never by importing it. Its useful half came *in* rather than
  the tree moving: `mesh.check` and `part.stress` (ADR-144, ADR-145) are
  engine ops, and this tree stays offboard. **S4 is what the whole thing was
  for** (ADR-146, ADR-147): `analysis/skeleton.py` fits a strut graph to a
  carved density field and emits a **parametric xscript** rather than a mesh,
  so a generative result arrives as a feature tree a person can edit —
  which is `docs/VISION.md` principle 3 made literal, and the one thing no
  other generative-design tool does.

There is no Qt shell, no provider stack, and no API-key model loop — the AI
runs as the Claude Code CLI the user is already logged into, which drives the
Mesh tools over an MCP stdio shim and brings no API key or model loop of
ours. **Claude Code is the only harness** (ADR-497): the Codex and pi
backends (ADR-174, ADR-175) went with the shell.
`pixi run build-engine` produces `FreeCADCmd` and `CadexGeometryWorker` and
no application.

**Where this is going (ADR-025, ADR-030).** The product becomes **one
application we own** — a derivative of but not dependent on either FreeCAD
or the Blender UI. **OCCT stays** as the geometry kernel; the FreeCAD application
layer is to be replaced by our own pybind11 binding (Phase 11, engine stays
Python) and the Blender shell by our own Rust + wgpu + egui shell
(Phase 12), both behind the *unchanged* cadexd protocol. Neither is
scheduled and neither blocks anything: merging the repos moved the deadline
pressure off them, and the test-pinned protocol is what keeps them
available. What *is* live is Phase 13b — deleting from both inherited trees,
in place, under the normal removal protocol. **Do not start writing a
replacement engine or shell in this tree ahead of its phase.**

**`mesh.blender` is retired (ADR-496).** ADR-185's native Blender recipes
went with the shell; no project depends on a Blender runtime.

Read `docs/VISION.md` before designing anything.

## Read this first (doc index, in order)

| Doc | What it answers |
|---|---|
| `STATE.md` | **What is true right now**, and what the frontier is. Generated from the state graph — never hand-edit. Read it first; it is the cheapest orientation in the repo. |
| `.hypergraph/AGENTS.md` | The Hypergraph protocol as it applies here: the two graphs, the roots, the epoch, the four non-negotiables. |
| `docs/VISION.md` | What the product is; principles; non-goals. **Authoritative.** |
| `docs/ARCHITECTURE.md` | What exists today: pipeline, file map, project store, substrate. |
| `docs/XSCRIPT.md` | The scripting model — today (per-domain programs) vs target (one project script). |
| `docs/ROADMAP.md` | Phases 0–17, status checkboxes, exit criteria. Living status lives here. |
| `docs/MUJOCO.md` | **This branch's vertical**: dynamics and control, slices M0–M9 (all closed), the hazards, and the measured facts. §7 is the **end-to-end walkthrough** — how to take a drawing to a trained policy, in the order that costs least. ROADMAP Phase 14 is its status line. |
| `docs/ORGANIC.md` | **Phase 15's vertical**: organic modelling and the CAD/mesh interface, slices O0–O3. §1 is the measurement it is sized from — a robot wolf built entirely in `part`, and the three ways it failed to weld its own seams. §4 is the benchmark log. |
| `docs/STRUCTURAL.md` | **Phase 16's vertical**: stress, topology optimisation and shape search, slices **S0–S4, all closed**. §3 is S0's measurements; §4 is the search loop and why it drives the CLI rather than importing it; §5 is SIMP and the marching-tetrahedra extraction; §6 is the in-engine half and what it deliberately did *not* build; §7 is the loop closed; **§8 is S4 — the fit that ends in a script rather than a mesh**, its spike-zero blend measurements, its coverage gate and the one premise that did not survive contact. S0–S2 and S4 are outside the engine by construction; S3 is one op on `mesh` and one on `part`, and costs no protocol op. |
| `docs/DECISIONS.md` | ADR log. Append an entry for every removal or direction change. |
| `docs/PROVENANCE.md` | Which code came from FreeCAD and from VibeCAD, what the deleted Blender shell left behind (nothing), licences and credit. |
| `docs/FREECAD.md` | Inherited-tree ledger for the **engine**: kept / disabled / already-deleted. |
| `docs/INTEGRATION.md` | **The process contract**: the cadexd protocol (test-enforced on both requests and responses) and the engine payload. |
| `docs/SHELL-PARITY.md` | Where each part of the deleted Blender shell went: ported, already covered, or dropped, with its test or ADR. |
| `docs/CLI.md` | The headless CLI: subcommands, exit codes, the `--json` envelope, and how it reaches the engine. |
| `docs/DESIGN-LANGUAGE.md` | **How a Cadex robot should look** (ADR-479): an engineered machine designed inside out, in an exposed-mechanism or panelled hard-surface finish, with no face, the `shell`/`mechanism`/`accent` roles and palette, joints, structure and feet, printability, presentation. Each rule cites the owner's blind ratings. `docs/probes/orun1/README.md` freezes judge v2, which it is scored with; ot10's rubric is retired (ADR-484). |
| `docs/REVIEW-DESIGN.md` | **The review dashboard's design spec** (ADR-328): purpose, hierarchy, type scale, the dark palette shared by chrome and viewport, spacing, breakpoints, and the measured "before" it is held against. Change the page and this doc together. |
| `docs/IDEAS.md` | Parking lot for uncommitted ideas. |
| `docs/cadex-release-packaging.md` | One bundle: what ships, how it is gated. |
| `training/README.md` | The offboard trainer: why training is not in the engine, what it reads and writes, how a policy comes home. |
| `training/SETUP.md` | How to actually run it, four ways: one GPU machine, CPU only, a separate GPU box, and driving that box with `remote_train.sh` (ADR-089). |
| `analysis/README.md` | The offboard structural analysis (ADR-141, ADR-143, ADR-147): what it reads and writes, how to declare a load case, how to declare a topology plan, how to fit a **parametric script** to the carve, how to read the report — and the licence rule this tree has that `training/` did not need. |
| `docs/history/` | Superseded VibeCAD-era docs. Historical context only — never cite as current. |

Doc conventions: each doc carries a `Verified against source:` date;
provenance tags `[FreeCAD-inherited]` / `[Blender-inherited]` /
`[VibeCAD-era]` / `[Cadex-new]`; *exists today* is kept separate from
*target*. When you change behavior, update the doc and its date in the same
PR.

## Repo map

```
cadex                     the CLI shim: ./cadex -p "..."  (docs/CLI.md)
cli/cadex_cli/            the CLI and the dashboard -- the protocol client
                          (ADR-061). LGPL; nothing may be copied here from
                          the deleted GPL shell (v1-blender-shell).
cli/tests/                its suite; engine-needing tests skip without one
src/Mod/cadex/            the engine (start here; file map in docs/ARCHITECTURE.md)
src/Mod/cadex/cadex_tests/  pytest suite (headless; FreeCAD stubbed in conftest.py)
src/Mod/{Part,PartDesign,Sketcher,Assembly}   the four capability workbenches
src/Mod/{Mesh,MeshPart}   the mesh domain substrate
src/{App,Base,Main}       inherited FreeCAD core (conservative zone)
src/Gui                   deleted in Phase 8 (ADR-214); residual GUI lineage
                          outside that boundary — docs/FREECAD.md §3
training/                 the offboard PPO trainer (ADR-084). NOT the engine:
                          CMake never installs it, no payload carries it,
                          nothing in it enters pixi.toml. Read its README
                          and SETUP.md; remote_train.sh dispatches to a GPU
                          box and is dispatch machinery only (ADR-089)
analysis/                 the offboard structural analysis (ADR-141,
                          ADR-142, ADR-143). The SECOND non-engine tree,
                          under the identical contract: no CMake rule, no
                          payload, nothing in pixi.toml. A hex-grid FEA core,
                          a load case measured from a MuJoCo rollout,
                          CalculiX as an arm's-length second opinion, a SIMP
                          topology optimiser with hand-written marching
                          tetrahedra, and a parameter search that drives
                          `./cadex params` as a subprocess rather than
                          importing anything. Its requirements.txt is THREE
                          pins and stays three. Nothing here may import a
                          GPL package — that one is test-enforced
package/engine/           the engine payload build (ADR-023)
package/app/bump_version.sh  bumps VERSION; the shell build that sat beside
                          it is gone (ADR-495)
package/rattler-build/scripts/relocate_conda_environment.py
                          CARRIED_PYPI_PACKAGES — how the mujoco wheel
                          reaches the payload (ADR-076)
docs/                     the documentation set above
build/release/bin/        FreeCADCmd, CadexGeometryWorker  (no FreeCAD binary)
build/engine/             the staged engine payload
```

## Commands

```bash
# The whole setup (ADR-060). No step needs git-lfs or Xcode: the Blender
# shell is deleted (ADR-498).
pixi run setup-engine         # just src/3rdParty/OndselSolver
pixi run build-engine
./cadex review --project <dir>   # the review dashboard

# The headless CLI (docs/CLI.md, ADR-061). Needs a built engine and nothing
# else -- no display. `params` spends no tokens.
./cadex -p "a 40x25x15 mm bracket with a 6 mm bore" \
        --project ./b --out ./b/out --json
./cadex params --project ./b --set bore=8 --out ./b/v2
./cadex -p "add a 2 mm fillet" --project ./b --resume
pixi run python -m pytest cli/tests            # its suite

# The offboard structural analysis (docs/STRUCTURAL.md, ADR-141). Needs no
# engine and no build; its numeric tests really run under pixi, because
# numpy, scipy, mujoco and ccx are all in this environment.
pixi run python analysis/cadex_stress.py --self-check     # the cantilever
pixi run python analysis/calculix.py --self-check         # ...and via ccx
pixi run python analysis/search.py plan.json --out ./sweep  # a parameter sweep
pixi run python analysis/topology.py --self-check          # carve a cantilever
pixi run python analysis/topology.py carve.json --out ./run
pixi run python analysis/skeleton.py carve.json --run ./run --out ./fit
                              # ...and fit a parametric SCRIPT to that carve.
                              # Add --project P to install it and size it,
                              # which rebuilds for real and needs an engine.

pixi run test-engine          # THE engine suite, no build needed
pixi run configure            # CMake configure (debug, GUI OFF)
pixi run build                # build debug        | pixi run build-release (GUI OFF)
pixi run test                 # inherited FreeCAD ctest, NOT the above
                              #                    | pixi run test-release
pixi run build-engine         # configure + build + install the engine (release)
pixi run stage-engine         # the payload -> build/engine/cadex-engine-<v>-<os>-<arch>/
pixi run cadexd               # a standalone engine service on stdio
pixi run python src/Mod/cadex/cadex_tests/cadexd_latency_integration.py
                              # the slider-drag latency bar, over raw NDJSON
```

**Engine builds have no GUI** (ADR-022, ADR-213): debug and release both
configure headlessly; explicit `BUILD_GUI=ON` requests are rejected.
`pixi run freecad-release` does not launch an application.
Python-only changes under `src/Mod/cadex/` need `pixi run build-engine`
before the CLI's engine-needing tests see them, and `pixi run stage-engine`
before the staged payload does.

## Change policy

The philosophy is **remove more than we add** (`docs/VISION.md`). Zones:

- **`src/Mod/cadex/**`, `cli/**`, `training/**`, `analysis/**` and
  `docs/**` — subtractive changes
  encouraged.** These are ours. Dead code, unreachable branches, stale docs:
  delete them. Every removal gets a `docs/DECISIONS.md` entry (one line in an
  existing ADR or a new one) and is verified by build + tests in the same PR.
- **`training/**` and `analysis/**` are at the root because they are *not*
  the engine** (ADR-084, ADR-141). Same contract for both: no CMake rule may
  reference them, no payload may carry them, and nothing in them may enter
  `pixi.toml` — their dependencies live in their own exactly-pinned
  `requirements.txt` and are installed into a venv on whatever machine runs
  them. Tests assert all three; moving either under `src/Mod/cadex/` would be
  one CMake line away from dragging jax, or a solver, into the payload.
  **`analysis/**` additionally may not import a GPL package** — the obvious
  tools for structural work are the GPL ones, so that is a test rather than
  a note. CalculiX is driven as a subprocess and stays pruned out of the
  payload, and `mmapy` (the standard MMA optimiser) is barred for the same
  reason. Its `requirements.txt` is **three pins and stays three**: S2's
  geometry extraction is sixty hand-written lines of marching tetrahedra
  rather than a fourth dependency, which is what kept it there (ADR-143).
- **The repository is LGPL and carries no GPL code** (ADR-498,
  `docs/PROVENANCE.md` §7), and `test_licensing_compliance.py` fails if a
  GPL-declared file comes back. The deleted shell's `cadexd_client.py`,
  `backend.py`, `mcp_shim.py` and `modes.py` (at `v1-blender-shell`) may be
  read as reference; copying a line of them into `cli/` relicenses it and
  is not a judgement call (ADR-061). Derive from the LGPL engine-side
  precedents in `cadex_tests/` instead.
- **Inherited FreeCAD core (`src/App`, `src/Gui`, `src/Base`) —
  conservative.** Prefer not touching it; when you must, smallest possible
  diff, no drive-by cleanup, call it out in the PR. A change that *reduces*
  the fork's delta against upstream is the exception worth making (ADR-022).
- **`src/Gui` is deleted (ADR-214).** Do not resurrect it. Remaining GUI-lineage
  source outside that boundary needs its own dependency audit and removal protocol.
- **Never vendor a prebuilt library into the tree.**
- **`src/Mod/<unused trees>`** — removed only via the Phase 1 protocol
  (`docs/FREECAD.md` §3): dependency audit, disable-commit, delete-commit,
  DECISIONS entry.

Not subject to relaxation: don't break the provider tool-surface contracts
pinned by `cadex_tests/test_project_tool_surface.py` without updating the
tests and logging the decision; don't commit secrets or machine paths.

## Methodology

1. **Trust the docs, then verify.** The docs above are dated; if code and
   doc disagree, the code wins — fix the doc in your PR.
2. **Verify by running.** Python edits under `src/Mod/cadex/`: `pixi run
   python -m pytest src/Mod/cadex/cadex_tests` minimum. Edits under `cli/`:
   `pixi run python -m pytest cli/tests` as well — and note that suite
   *skips* the engine-needing half when nothing is built, so a green run on
   a bare checkout proves less than it looks like. C++/CMake edits:
   `pixi run build-release`; ctest has ~160 pre-existing environmental
   failures, so diff against `build/ctest_baseline_failures.txt` rather than
   expecting 100%. Anything touching the protocol or the payload: run the
   packaged gate (`CADEX_ENGINE_ROOT=<payload> pytest
   src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py`) — a source tree that
   passes proves nothing about a payload, as ADR-023 records. Report
   failures honestly, with output.
3. **Small, coherent, owner-mergeable PRs.** One logical change; state the
   user-visible outcome, risk, and test evidence. No mixed refactors.
4. **Removals are normal work** — log them (ADR) and prove them (build +
   tests). Resurrecting teardown-deleted functionality is a direction
   change: needs an ADR and owner sign-off.
5. **Don't build UI in the engine.** No Coin3D rendering, no Qt, no
   workbench concepts under `src/`. If it has a widget in it, it belongs in
   the dashboard (`cli/cadex_cli/review_static/`).
6. **The protocol is a contract between two halves that must stay
   swappable.** It is no longer a contract across repositories, and it is
   more valuable for it: pinning requests (`OP_ARG_SPECS`) and responses
   (the ADR-027 goldens) is what keeps Phases 11 and 12 available. Changing
   `CadexdProtocol.OP_ARG_SPECS` means changing `docs/INTEGRATION.md`'s op
   table in the same commit (a test enforces it) and updating the CLI's
   client in the same PR. Being in one repo is not a licence to reach across
   the boundary in any other way.
7. **Update `docs/ROADMAP.md` checkboxes** when a work item lands.

## The dynamics vertical (ADR-102)

`docs/MUJOCO.md` and its slices M0–M9 (**all closed**, ADR-085 for M0–M8,
ADR-097/098/099 for M9, ADR-100 for M9b, ADR-101 for M9c);
`CadexDynamics.py` and the
`assembly.{body,dynamics,collision,actuator,joint_dynamics,mjcf,task,policy,
rollout,reset_variation,disturbance}` surface; the `test_dynamics_*` suites;
`training/`; the mujoco lines in `pixi.toml`/`pixi.lock`;
and `CARRIED_PYPI_PACKAGES` in
`package/rattler-build/scripts/relocate_conda_environment.py`.

This was a separate branch, `MJC`, from 2026-07-30 to 2026-08-01. The rules
that governed the split — one-way syncs, branch-marked doc blocks, an empty
shell diff — are **retired with it** (ADR-102), and if you find a doc
still saying otherwise, the doc is stale. The `MJC` ref still exists,
pointing at the merge; nothing should be committed to it.

Working rules on top of the change policy above:

- **Two invariants that are cheap to break by accident**, both test-pinned
  and neither about a branch: `CadexDynamics.py` is reachable
  from the sandboxed worker but never from `cadexd`
  (`test_engine_purity_guardrails` asserts the import closure exactly); and
  **no `jax` or `mjx` anywhere under `src/Mod/cadex` or in a staged payload**
  (ADR-084 — training is offboard, and the engine verifies a policy but never
  produces one).
- **`training/` is not part of the engine** (ADR-084). `training/cadex_train.py`
  is the offboard PPO trainer: it lives at the repo root because CMake never
  installs it, it is in no payload, and its four exactly-pinned dependencies
  are in `training/requirements.txt` and installed into a venv **on whatever
  machine trains**. Nothing in it enters `pixi.toml` — `CARRIED_PYPI_PACKAGES`
  stays one entry long. It imports only the standard library at module scope
  and reports whether `CadexDynamics` was importable so a test can assert the
  negative. Read `training/README.md` before touching it.
- **Verify dynamics work with `pixi run python -m pytest
  src/Mod/cadex/cadex_tests`** — the `test_dynamics_*` suites run headless
  with no build. Anything touching the payload still needs the packaged gate;
  ADR-023's rule that a passing source tree proves nothing about a payload
  is what caught the dangling `bin/python` in M0. The MJX-gated tests
  (phase 0 measurements, real training runs) **skip** in the pixi environment
  by design; to run them, use a venv built from `training/requirements.txt`
  — the suites are written to run from either interpreter.

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
