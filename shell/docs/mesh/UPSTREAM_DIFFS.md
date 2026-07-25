# Mesh: Upstream Diff Ledger

Every change to files that exist in upstream Blender must be recorded here so
merges from upstream tags stay cheap.

**The additive-only policy ended with cadex Phase 7** (cadex ADR-020,
decision 6; ADR-024). Through Phase 6 this fork added new files and edited
none. Shipping one application that works with no configuration requires
two upstream edits, both listed below. The rule now is not "never edit" but
**"every edit is listed here, kept minimal, and justified"** — each row
says what changed, why, and what a merge conflict in it would mean.

Merging upstream: `git merge <tag>` on `mesh-main` (never rebase).

## New files (no upstream conflict possible)

- `scripts/startup/bl_app_templates_system/Mesh/` — app template
- `scripts/addons_core/mesh_agent/` — agent add-on (incl. the cadex
  backend: `cadexd_client.py`, `cadex_backend.py`, `cadex_hydrate.py`,
  `cadex_pick.py` — cadex Phase 6, ADR-019 in the cadex repo)
- `tests/python/bl_mesh_agent.py` — headless agent tests
- `tests/python/bl_mesh_agent_cad.py` — CAD mode tests
- `tests/python/bl_mesh_agent_cadex.py` — cadex backend + decision-gate
  evidence (needs `MESH_FREECADCMD` pointing at a cadex build)
- `docs/mesh/` — this ledger and future Mesh docs
- `docs/mesh/CADEX_ENGINE.md` — the bundled engine: discovery, layout,
  version pin, how to point at a development build

## New files (Phase 7)

- `build_files/cadex_engine.txt` — pinned cadex engine version + per-platform
  SHA256
- `build_files/utils/fetch_cadex_engine.py` — fetch, verify and stage the
  engine payload
- `.github/workflows/mesh-build.yml` — the repository's first CI: build,
  stage the engine, run all three agent suites against the bundle

## Modified upstream files

| File | Change | Why | On conflict |
|---|---|---|---|
| `source/blender/makesdna/DNA_userdef_types.h` | `app_template` default `""` → `"Mesh"` (one string literal, plus a comment) | A new user should meet the chat-driven modelling template without finding it in a menu. Only a *fresh* profile takes the default; an existing `userpref.blend` keeps what it stored, and `--app-template default` still escapes to stock Blender. | Keep `"Mesh"`, take upstream's changes to the surrounding struct. The literal is the whole change. |
| `CMakeLists.txt` (repository root) | New `WITH_CADEX_ENGINE` option and `CADEX_ENGINE_DIR` cache path | Declares the option that bundles the cadex engine. Additive within the file: one `option()` and one `set(... CACHE PATH ...)`, no upstream lines touched. | Re-add the block; it depends on nothing around it. |
| `source/creator/CMakeLists.txt` | `install()` rules for the engine payload under `WITH_CADEX_ENGINE` | Puts the engine inside the bundle so Cadex mode needs no configuration (cadex ADR-023). Additive: one guarded block beside the existing `scripts` install, no upstream lines touched. | Re-add the block after upstream's install rules. |

**Chosen over the alternative.** `creator_args.cc` was the other route to a
default app template. A data default in a DNA header conflicts as a data
blob; argument-parsing code conflicts as logic, and the same escape hatch
(`--app-template default`) exists either way.
