# CLAUDE.md — Agent Entry Point

Verified against source: 2026-07-25. This file replaces the retired
`AGENTS.md` (see `docs/DECISIONS.md` ADR-005).

Cadex is an AI-native CAD app. **This repository is the engine, and only
the engine** (Phase 7, ADR-020/021): the AI authors declarative **xscript**
Python programs, and `cadexd` — a per-project headless service, NDJSON over
stdio — runs them in sandboxed `FreeCADCmd` workers that produce detached
BREP, publishes into its own ephemeral document, and streams tessellation
back. Five domains: partdesign, sketcher, part, mesh, assembly.

**The shell is elsewhere.** The product UI is the Blender fork at
`/Users/theo/mesh` (`scripts/addons_core/mesh_agent/`), which talks to this
engine over the protocol in `docs/INTEGRATION.md` and ships it inside its
own bundle. There is no Qt shell here, no provider stack, and no API-key
model loop — the AI runs as the Claude Code CLI inside the shell. A release
build produces `FreeCADCmd` and `CadexGeometryWorker` and no application.

Read `docs/VISION.md` before designing anything.

## Read this first (doc index, in order)

| Doc | What it answers |
|---|---|
| `docs/VISION.md` | What the product is; principles; non-goals. **Authoritative.** |
| `docs/ARCHITECTURE.md` | What exists today: pipeline, file map, project store, substrate. |
| `docs/XSCRIPT.md` | The scripting model — today (per-domain programs) vs target (one project script). |
| `docs/ROADMAP.md` | Phases 0–8, status checkboxes, exit criteria. Living status lives here. |
| `docs/DECISIONS.md` | ADR log. Append an entry for every removal or direction change. |
| `docs/FREECAD.md` | Inherited-tree ledger: kept / disabled / already-deleted. |
| `docs/INTEGRATION.md` | **The two-repo contract**: the cadexd protocol (test-enforced) and the engine payload. |
| `docs/BLENDER.md` | The shell: `mesh_agent`'s file map, its tools, and how to run its suites. |
| `docs/IDEAS.md` | Parking lot for uncommitted ideas. |
| `docs/cadex-release-packaging.md` | The engine payload: what ships, how it is gated. |
| `docs/history/` | Superseded VibeCAD-era docs. Historical context only — never cite as current. |

Doc conventions: each doc carries a `Verified against source:` date;
provenance tags `[FreeCAD-inherited]` / `[VibeCAD-era]` / `[Cadex-new]`;
*exists today* is kept separate from *target*. When you change behavior,
update the doc and its date in the same PR.

## Repo map

```
src/Mod/cadex/            the engine (start here; file map in docs/ARCHITECTURE.md)
src/Mod/cadex/cadex_tests/  pytest suite (headless; FreeCAD stubbed in conftest.py)
src/Mod/{Part,PartDesign,Sketcher,Assembly}   the four capability workbenches
src/Mod/{Mesh,MeshPart}   the mesh domain substrate
src/{App,Base,Main}       inherited FreeCAD core (conservative zone)
src/Gui                   present but NOT BUILT (BUILD_GUI=OFF, ADR-022);
                          deletion is Phase 8 — docs/FREECAD.md §3
package/engine/           the engine payload build (ADR-023)
docs/                     the documentation set above
build/release/bin/        FreeCADCmd, CadexGeometryWorker  (no FreeCAD binary)
```

The shell lives in the **mesh repository**; changes there are its own
commits. `docs/BLENDER.md` is the integration reference.

## Commands

```bash
pixi run python -m pytest src/Mod/cadex/cadex_tests   # engine tests, no build needed
pixi run configure            # CMake configure (debug, GUI ON)
pixi run build                # build debug        | pixi run build-release (GUI OFF)
pixi run test                 # ctest              | pixi run test-release
pixi run cadexd               # a standalone engine service on stdio
pixi run python src/Mod/cadex/cadex_tests/cadexd_latency_integration.py
                              # the slider-drag latency bar, over raw NDJSON
bash package/engine/build_engine_payload.sh           # the shipped payload
```

**Release builds have no GUI** (ADR-022), so `pixi run freecad-release`
no longer launches an application — only the debug build does, and only as
an engineering convenience. Python-only changes under `src/Mod/cadex/` need
`pixi run build-release` to reach `build/release/Mod/cadex` before the
engine or the Blender suites see them.

To exercise the real product, run the shell's suites in the mesh repo; see
`docs/BLENDER.md`.

## Change policy

The philosophy is **remove more than we add** (`docs/VISION.md`). Zones:

- **`src/Mod/cadex/**` and `docs/**` — subtractive changes encouraged.**
  Dead code, unreachable branches, stale docs: delete them. Every removal
  gets a `docs/DECISIONS.md` entry (one line in an existing ADR or a new
  one) and is verified by build + tests in the same PR.
- **Inherited FreeCAD core (`src/App`, `src/Gui`, `src/Base`) —
  conservative.** Prefer not touching it; when you must, smallest possible
  diff, no drive-by cleanup, call it out in the PR. A change that *reduces*
  the fork's delta against upstream is the exception worth making (ADR-022).
- **`src/Gui` is not built.** Don't add to it, don't fix it, don't delete it
  outside the Phase 8 protocol.
- **`src/Mod/<unused trees>`** — removed only via the Phase 1 protocol
  (`docs/FREECAD.md` §3): dependency audit, disable-commit, delete-commit,
  DECISIONS entry.

Not subject to relaxation: don't break the provider tool-surface contracts
pinned by `cadex_tests/test_project_tool_surface.py` without updating the
tests and logging the decision; don't commit secrets or machine paths.

## Methodology

1. **Trust the docs, then verify.** The docs above are dated; if code and
   doc disagree, the code wins — fix the doc in your PR.
2. **Verify by running.** Python edits: `pixi run python -m pytest
   src/Mod/cadex/cadex_tests` minimum. C++/CMake edits: `pixi run
   build-release`; ctest has ~164 pre-existing environmental failures, so
   diff against `build/ctest_baseline_failures.txt` rather than expecting
   100%. Anything touching the protocol or the payload: run the packaged
   gate (`CADEX_ENGINE_ROOT=<payload> pytest
   src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py`) — a source tree that
   passes proves nothing about a payload, as ADR-023 records. Report
   failures honestly, with output.
3. **Small, coherent, owner-mergeable PRs.** One logical change; state the
   user-visible outcome, risk, and test evidence. No mixed refactors.
4. **Removals are normal work** — log them (ADR) and prove them (build +
   tests). Resurrecting teardown-deleted functionality is a direction
   change: needs an ADR and owner sign-off.
5. **Don't build UI here.** No Coin3D rendering, no Qt, no workbench
   concepts. If it has a widget in it, it belongs in the mesh repository.
6. **The protocol is a contract with another repository.** Changing
   `CadexdProtocol.OP_ARG_SPECS` means changing `docs/INTEGRATION.md`'s op
   table in the same commit (a test enforces it) and checking the shell.
7. **Update `docs/ROADMAP.md` checkboxes** when a work item lands.
