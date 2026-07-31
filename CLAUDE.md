# CLAUDE.md — Agent Entry Point

Verified against source: 2026-07-31. This file replaces the retired
`AGENTS.md` (see `docs/DECISIONS.md` ADR-005).

Cadex is an AI-native CAD app. **This repository is the whole product**
(Phase 13a, ADR-030): clone it, `pixi run setup && pixi run app`, and you
have a running application.

**You are on `MJC`, and `MJC` is a product vertical** (ADR-072): Cadex with
**dynamics and control built in**. Not a feature branch, not a merge
candidate, not awaiting anything — a version of the product that simulates
mechanisms on MuJoCo, exports them, and plays back policies trained on them.
`main` is the same product without that vertical, and stays that way so a
user modeling a bracket does not build or ship 53.5 MB of physics engine.
Changes flow `main` → `MJC` and never back. The branch rules are at the end
of this file; the arc itself is `docs/MUJOCO.md`.

Two halves, one repo, separated by a process boundary rather than a
repository boundary:

- **the engine**, at the repo root — a FreeCAD fork. The AI authors
  declarative **xscript** Python programs, and `cadexd`, a per-project
  headless service speaking NDJSON over stdio, runs them in sandboxed
  `FreeCADCmd` workers that produce detached BREP, publish into an
  ephemeral document, and stream tessellation back. Five domains:
  partdesign, sketcher, part, mesh, assembly — the assembly one carrying
  dynamics, MJCF export, tasks, policies and rollouts on this branch.
- **the shell**, under `shell/` — a Blender fork carrying the
  `mesh_agent` add-on. It is the product UI, it speaks the protocol in
  `docs/INTEGRATION.md`, and it ships the engine inside its own bundle. It
  knows nothing about dynamics and never will: a policy rollout reaches it
  as the simulation trace it already played.
- **`training/`**, at the repo root — the offboard PPO trainer. Not part of
  the engine, in no payload, copied to a machine with a GPU (ADR-070).

There is no Qt shell, no provider stack, and no API-key model loop — the AI
runs as the Claude Code CLI inside the shell. `pixi run build-engine`
produces `FreeCADCmd` and `CadexGeometryWorker` and no application; the
application is what `pixi run build-shell` installs, with the engine inside
it.

**Where this is going (ADR-025, ADR-030).** The product becomes **one
application we own** — a derivative of but not dependent on either FreeCAD
or Blender. **OCCT stays** as the geometry kernel; the FreeCAD application
layer is to be replaced by our own pybind11 binding (Phase 11, engine stays
Python) and the Blender shell by our own Rust + wgpu + egui shell
(Phase 12), both behind the *unchanged* cadexd protocol. Neither is
scheduled and neither blocks anything: merging the repos moved the deadline
pressure off them, and the test-pinned protocol is what keeps them
available. What *is* live is Phase 13b — deleting from both inherited trees,
in place, under the normal removal protocol. **Do not start writing a
replacement engine or shell in this tree ahead of its phase.**

Read `docs/VISION.md` before designing anything.

## Read this first (doc index, in order)

| Doc | What it answers |
|---|---|
| `docs/VISION.md` | What the product is; principles; non-goals. **Authoritative.** |
| `docs/ARCHITECTURE.md` | What exists today: pipeline, file map, project store, substrate. |
| `docs/XSCRIPT.md` | The scripting model — today (per-domain programs) vs target (one project script). |
| `docs/ROADMAP.md` | Phases 0–14, status checkboxes, exit criteria. Living status lives here. |
| `docs/MUJOCO.md` | **This branch's vertical**: dynamics and control, slices M0–M8 (all closed), the hazards, and the measured facts. ROADMAP Phase 14 is its status line. |
| `docs/DECISIONS.md` | ADR log. Append an entry for every removal or direction change. |
| `docs/PROVENANCE.md` | Which code came from FreeCAD, from Blender, and from VibeCAD; licences, credit, and how two licences share one repo. |
| `docs/FREECAD.md` | Inherited-tree ledger for the **engine**: kept / disabled / already-deleted. |
| `docs/BLENDER-TREE.md` | The same ledger for **`shell/`**, plus the eight-file diff against upstream Blender. |
| `docs/INTEGRATION.md` | **The process contract**: the cadexd protocol (test-enforced on both requests and responses) and the engine payload. |
| `docs/BLENDER.md` | The shell: `mesh_agent`'s file map, its tools, and how to run its suites. |
| `docs/IDEAS.md` | Parking lot for uncommitted ideas. |
| `docs/cadex-release-packaging.md` | One bundle: what ships, how it is gated. |
| `training/README.md` | The offboard trainer: why training is not in the engine, what it reads and writes, how a policy comes home. |
| `docs/history/` | Superseded VibeCAD-era docs. Historical context only — never cite as current. |

Doc conventions: each doc carries a `Verified against source:` date;
provenance tags `[FreeCAD-inherited]` / `[Blender-inherited]` /
`[VibeCAD-era]` / `[Cadex-new]`; *exists today* is kept separate from
*target*. When you change behavior, update the doc and its date in the same
PR.

## Repo map

```
src/Mod/cadex/            the engine (start here; file map in docs/ARCHITECTURE.md)
src/Mod/cadex/cadex_tests/  pytest suite (headless; FreeCAD stubbed in conftest.py)
src/Mod/{Part,PartDesign,Sketcher,Assembly}   the four capability workbenches
src/Mod/{Mesh,MeshPart}   the mesh domain substrate
src/{App,Base,Main}       inherited FreeCAD core (conservative zone)
src/Gui                   present but NOT BUILT (BUILD_GUI=OFF, ADR-022);
                          deletion is Phase 8 — docs/FREECAD.md §3
shell/                    the shell — a Blender fork (conservative zone;
                          ledger and upstream diff in docs/BLENDER-TREE.md)
shell/scripts/addons_core/mesh_agent/   the add-on: ours, subtractive
                          changes encouraged (docs/BLENDER.md)
shell/lib/<platform>      submodules, NEVER content (1.3 GB prebuilt each)
                          NOTE: shell/ also carries ~790 MB in git-LFS
                          (binary assets, per shell/.gitattributes)
training/                 the offboard PPO trainer (ADR-070). NOT the engine:
                          CMake never installs it, no payload carries it,
                          nothing in it enters pixi.toml. Read its README
package/engine/           the engine payload build (ADR-023)
package/app/build_app.sh  the shell build, with the conda env scrubbed off
                          PATH — read its header before touching the build
package/rattler-build/scripts/relocate_conda_environment.py
                          CARRIED_PYPI_PACKAGES — how the mujoco wheel
                          reaches the payload (ADR-061)
docs/                     the documentation set above
build/release/bin/        FreeCADCmd, CadexGeometryWorker  (no FreeCAD binary)
build/engine/             the staged engine payload
shell/build_darwin/       the shell build tree and the installed bundle
```

## Commands

```bash
git lfs install               # once per machine, BEFORE cloning
pixi run setup                # first time: check out shell/lib/<platform>
pixi run app                  # build engine + payload + shell, then launch
pixi run install-app          # ...and copy it to /Applications so it opens like
                              # an app. Local install: the staged payload keeps
                              # resolving its libs out of this repo (ADR-058).

pixi run python -m pytest src/Mod/cadex/cadex_tests   # engine tests, no build needed
pixi run configure            # CMake configure (debug, GUI ON)
pixi run build                # build debug        | pixi run build-release (GUI OFF)
pixi run test                 # ctest              | pixi run test-release
pixi run build-engine         # configure + build + install the engine (release)
pixi run stage-engine         # the payload -> build/engine/cadex-engine-<v>-<os>-<arch>/
pixi run build-shell          # the shell, with that payload installed into the bundle
pixi run gate                 # CADEX-BLENDER-GATE against the built bundle
pixi run cadexd               # a standalone engine service on stdio
pixi run python src/Mod/cadex/cadex_tests/cadexd_latency_integration.py
                              # the slider-drag latency bar, over raw NDJSON
```

**Two toolchains that must not see each other.** The engine builds inside
the pixi/conda-forge environment; the shell builds against
`shell/lib/<platform>` with Xcode and a homebrew `cmake`/`ninja`. Conda on
`PATH` during a shell configure resolves the wrong zlib/png/OpenSSL/Python
and fails late or misbehaves at runtime. `package/app/build_app.sh` scrubs
the environment before it touches `shell/`; that is why `build-shell` is a
script and not a `cmd = ["cmake", ...]` task. Don't route the shell build
around it.

**Release builds have no GUI** (ADR-022): `pixi run freecad-release` no
longer launches an application — only the debug build does, and only as an
engineering convenience. The application you launch is the shell.
Python-only changes under `src/Mod/cadex/` need `pixi run build-engine`
before the shell's suites see them, and `pixi run stage-engine` before the
*bundled* engine does.

## Change policy

The philosophy is **remove more than we add** (`docs/VISION.md`). Zones:

- **`src/Mod/cadex/**`, `shell/scripts/addons_core/mesh_agent/**` and
  `docs/**` — subtractive changes encouraged.** These are ours. Dead code,
  unreachable branches, stale docs: delete them. Every removal gets a
  `docs/DECISIONS.md` entry (one line in an existing ADR or a new one) and
  is verified by build + tests in the same PR.
- **Inherited FreeCAD core (`src/App`, `src/Gui`, `src/Base`) —
  conservative.** Prefer not touching it; when you must, smallest possible
  diff, no drive-by cleanup, call it out in the PR. A change that *reduces*
  the fork's delta against upstream is the exception worth making (ADR-022).
- **The rest of `shell/**` — inherited Blender, same conservative rules.**
  The delta against upstream Blender is listed in full in
  `docs/BLENDER-TREE.md` §2, in three groups that age differently: **§2a**
  product identity (eight files of string literals and guarded CMake blocks —
  *this one must stay eight*), **§2b** the Cadex editors (ADR-035, ADR-036 —
  additive rows in enums, exhaustive switches and CMake lists, plus the
  registration list that *is* the editor menu), and **§2c** the message box
  (ADR-034). Every line added there is a future merge conflict; what differs
  is whether it conflicts as an insertion the compiler finds or as rewritten
  logic. Prefer the former, and say which you are adding. Removals go through
  the two-commit protocol in `docs/FREECAD.md` §3 — and on this side the
  disable commit is often a `WITH_*` CMake option or simply not registering a
  space type, so it is nearly free.
- **`src/Gui` is not built.** Don't add to it, don't fix it, don't delete it
  outside the Phase 8 protocol.
- **`shell/lib/<platform>` are submodules, not content.** Never commit their
  contents; never vendor a prebuilt library into the tree.
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
   python -m pytest src/Mod/cadex/cadex_tests` minimum. C++/CMake edits:
   `pixi run build-release`; ctest has ~160 pre-existing environmental
   failures, so diff against `build/ctest_baseline_failures.txt` rather than
   expecting 100%. Anything touching the protocol or the payload: run the
   packaged gate (`CADEX_ENGINE_ROOT=<payload> pytest
   src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py`) — a source tree that
   passes proves nothing about a payload, as ADR-023 records. Anything
   touching `shell/`: `pixi run gate`. Report failures honestly, with
   output.
3. **Small, coherent, owner-mergeable PRs.** One logical change; state the
   user-visible outcome, risk, and test evidence. No mixed refactors.
4. **Removals are normal work** — log them (ADR) and prove them (build +
   tests). Resurrecting teardown-deleted functionality is a direction
   change: needs an ADR and owner sign-off.
5. **Don't build UI in the engine.** No Coin3D rendering, no Qt, no
   workbench concepts under `src/`. If it has a widget in it, it belongs in
   `shell/scripts/addons_core/mesh_agent/`.
6. **The protocol is a contract between two halves that must stay
   swappable.** It is no longer a contract across repositories, and it is
   more valuable for it: pinning requests (`OP_ARG_SPECS`) and responses
   (the ADR-027 goldens) is what keeps Phases 11 and 12 available. Changing
   `CadexdProtocol.OP_ARG_SPECS` means changing `docs/INTEGRATION.md`'s op
   table in the same commit (a test enforces it) and updating the shell's
   client in the same PR. Being in one repo is not a licence to reach across
   the boundary in any other way.
7. **Update `docs/ROADMAP.md` checkboxes** when a work item lands.

## The dynamics vertical (ADR-060, ADR-063, ADR-067, ADR-072)

What this version of the product carries that `main` does not:
`docs/MUJOCO.md` and its slices M0–M8 (**all closed**, ADR-071);
`CadexDynamics.py` and the `assembly.{body,dynamics,collision,actuator,
joint_dynamics,mjcf,task,policy,rollout}` surface; the `test_dynamics_*`
suites; `training/`; the mujoco lines in `pixi.toml`/`pixi.lock`; and
`CARRIED_PYPI_PACKAGES` in
`package/rattler-build/scripts/relocate_conda_environment.py`. A sync from
`main` must never drop those.

Working rules on top of the change policy above:

- **Changes flow `main` → `MJC`, never back.** If what you are fixing is not
  dynamics-specific — a bug in the trace path, a payload prune, a doc that is
  wrong on both branches — it belongs on `main` first and reaches here on the
  next sync. Ask before landing such a fix here.
- **The docs here are this branch's own** (ADR-072). The append-only,
  branch-marked-block rule ADR-063 imposed on `VISION.md`, `ROADMAP.md` and
  this file is **retired**: write the dynamics material into the body where
  it belongs, and resolve the occasional sync conflict by hand in favour of
  this branch's wording. `docs/DECISIONS.md` is still append-only on both
  branches, so conflicts there are expected and resolved in date order. The
  rule still stands, unchanged, for the inherited `shell/` tree
  (`docs/BLENDER-TREE.md`) — that tree is not ours to rewrite.
- **The `shell/` diff stays empty.** `git diff main...MJC -- shell/` prints
  nothing, and the whole arc landed without spending it. Two known rough
  edges wait behind it (`import_geometry`'s success wording, `_ASSET_SUFFIXES`
  staying at three members) — ADR-072 §4 names them. Spending the diff is a
  decision, not a fix you slip in.
- **Three invariants that are cheap to break by accident**, all test-pinned:
  nothing in `shell/` imports mujoco; `CadexDynamics.py` is reachable
  from the sandboxed worker but never from `cadexd`
  (`test_engine_purity_guardrails` asserts the import closure exactly); and
  **no `jax` or `mjx` anywhere under `src/Mod/cadex` or in a staged payload**
  (ADR-070 — training is offboard, and the engine verifies a policy but never
  produces one).
- **`training/` is not part of the engine** (ADR-070). `training/cadex_train.py`
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
