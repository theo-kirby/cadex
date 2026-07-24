# CLAUDE.md — Agent Entry Point

Verified against source: 2026-07-24. This file replaces the retired
`AGENTS.md` (see `docs/DECISIONS.md` ADR-005).

Cadex is an AI-native CAD app: the AI authors declarative **xscript** Python
programs; sandboxed headless `FreeCADCmd` workers produce detached BREP; a
publisher applies validated results to the live document under a
transaction. Four domains: partdesign, sketcher, part, assembly. Endpoint:
headless engine (`cadexd`) behind a Blender shell. Read `docs/VISION.md`
before designing anything.

## Read this first (doc index, in order)

| Doc | What it answers |
|---|---|
| `docs/VISION.md` | What the product is; principles; non-goals. **Authoritative.** |
| `docs/ARCHITECTURE.md` | What exists today: pipeline, file map, project store, substrate. |
| `docs/XSCRIPT.md` | The scripting model — today (per-domain programs) vs target (one project script). |
| `docs/ROADMAP.md` | Phases 0–7, status checkboxes, exit criteria. Living status lives here. |
| `docs/DECISIONS.md` | ADR log. Append an entry for every removal or direction change. |
| `docs/FREECAD.md` | Inherited-tree ledger: kept / slated-for-removal / already-deleted. |
| `docs/INTEGRATION.md` | Engine/shell split, cadexd protocol sketch, decision gate. |
| `docs/BLENDER.md` | The `/Users/theo/mesh` fork: mesh_agent prototype + relevant Blender internals. |
| `docs/IDEAS.md` | Parking lot for uncommitted ideas. |
| `docs/cadex-release-packaging.md` | Release packaging. |
| `docs/history/` | Superseded VibeCAD-era docs. Historical context only — never cite as current. |

Doc conventions: each doc carries a `Verified against source:` date;
provenance tags `[FreeCAD-inherited]` / `[VibeCAD-era]` / `[Cadex-new]`;
*exists today* is kept separate from *target*. When you change behavior,
update the doc and its date in the same PR.

## Repo map

```
src/Mod/cadex/            the engine + interim UI (start here; file map in docs/ARCHITECTURE.md)
src/Mod/cadex/cadex_tests/  pytest suite (headless; FreeCAD stubbed in conftest.py)
src/Mod/{Part,PartDesign,Sketcher,Assembly}   the four capability workbenches
src/{App,Gui,Base,Main}   inherited FreeCAD core (conservative zone)
src/Mod/<others>          mostly unused, slated for removal — docs/FREECAD.md §3
docs/                     the documentation set above
build/{debug,release}/bin/  FreeCAD, FreeCADCmd, CadexGeometryWorker
```

## Commands

```bash
pixi run configure            # CMake configure (debug; configure-release for release)
pixi run build                # build debug        | pixi run build-release
pixi run freecad              # launch debug app   | pixi run freecad-release
pixi run test                 # ctest              | pixi run test-release
pixi run python -m pytest src/Mod/cadex/cadex_tests   # engine tests, no build needed
```

A prebuilt `build/release/` usually exists; Python-only changes under
`src/Mod/cadex/` take effect on next launch without rebuilding (the module
is installed/copied at build time — rerun `pixi run build-release` if your
change doesn't show up).

## Change policy

The philosophy is **remove more than we add** (`docs/VISION.md`). Zones:

- **`src/Mod/cadex/**` and `docs/**` — subtractive changes encouraged.**
  Dead code, unreachable branches, stale docs: delete them. Every removal
  gets a `docs/DECISIONS.md` entry (one line in an existing ADR or a new
  one) and is verified by build + tests in the same PR.
- **Inherited FreeCAD core (`src/App`, `src/Gui`, `src/Base`) —
  conservative.** Prefer not touching it; when you must, smallest possible
  diff, no drive-by cleanup, call it out in the PR.
- **`src/Mod/<unused trees>`** — removed only via the Phase 1 protocol
  (`docs/FREECAD.md` §3): dependency audit, disable-commit, delete-commit,
  DECISIONS entry.

Not subject to relaxation: don't break the provider tool-surface contracts
pinned by `cadex_tests/test_tool_surface_guardrails.py` without updating the
tests and logging the decision; don't commit secrets or machine paths.

## Methodology

1. **Trust the docs, then verify.** The docs above are dated; if code and
   doc disagree, the code wins — fix the doc in your PR.
2. **Verify by running.** Python edits: `pixi run python -m pytest
   src/Mod/cadex/cadex_tests` minimum. C++/CMake edits: `pixi run
   build-release` + launch. Report failures honestly, with output.
3. **Small, coherent, owner-mergeable PRs.** One logical change; state the
   user-visible outcome, risk, and test evidence. No mixed refactors.
4. **Removals are normal work** — log them (ADR) and prove them (build +
   tests). Resurrecting teardown-deleted functionality is a direction
   change: needs an ADR and owner sign-off.
5. **Don't invest in the disposable.** No Coin3D rendering work, no Qt
   chrome beyond the Phase 3 layout cap, no new workbench-style UI concepts.
6. **Update `docs/ROADMAP.md` checkboxes** when a work item lands.
