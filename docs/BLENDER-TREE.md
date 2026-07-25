# BLENDER-TREE.md — Inherited Shell Substrate Inventory

Verified against source: 2026-07-25

`shell/` is a Blender fork. This is its ledger — what we keep, what is
slated for removal, what is already gone — the peer of `docs/FREECAD.md`
for the engine half, in the same format and under the same rules.

The change policy is in `CLAUDE.md`: `shell/scripts/addons_core/mesh_agent/`
is ours and subtractive changes there are encouraged; **everything else
under `shell/` is inherited-Blender and conservative**. Removals execute
under the two-commit protocol in `docs/FREECAD.md` §3 (disable, verify;
delete, verify) and are logged in `docs/DECISIONS.md`.

Everything in this file is `[Blender-inherited]` unless noted.

**Provenance.** Imported 2026-07-25 as a squashed snapshot of
`/Users/theo/mesh` at `ac5af55948d` (branch `mesh-main`), plus one
uncommitted working-tree change to `source/creator/CMakeLists.txt`
(ADR-030). Blender's own 163,789-commit history stayed behind, deliberately:
we delete from this tree, we do not track upstream. `/Users/theo/mesh` is
kept as a read-only archive.

## 1. Ours, inside the fork `[Cadex-new]`

These files exist in no upstream Blender and cannot conflict with one.

| Path | What | Lines |
|---|---|---|
| `shell/scripts/addons_core/mesh_agent/` | the add-on: chat, params panel, the cadexd protocol client, hydration, picking | 4,577 (17 files) |
| `shell/scripts/startup/bl_app_templates_system/Mesh/` | the app template that suppresses Blender's UI and lays out the Cadex workspace | 294 |
| `shell/tests/python/bl_mesh_agent{,_cadex}.py` | the agent suites; `bl_mesh_agent_cadex.py` prints the `CADEX-BLENDER-GATE` evidence line | 1,522 (2 files) |

The add-on was 5,714 lines across 20 files at import; ADR-030 took it to
4,577 across 17 by deleting the local bpy modes. Counted 2026-07-25 — treat
these as of that date, not as a contract.

## 2. Modified upstream files — the whole delta

Six files, and that is the entire edit surface against stock Blender. Keep
it that way: every addition here is a future merge conflict, and the reason
the shell was cheap to absorb is that this table is short.

| File | Change | Why | On conflict |
|---|---|---|---|
| `source/blender/makesdna/DNA_userdef_types.h` | `app_template` default `""` → `"Mesh"` | A new user meets the chat-driven layout without finding it in a menu (ADR-024). Only a *fresh* profile takes the default; an existing `userpref.blend` keeps what it stored, and `--app-template default` still escapes to stock Blender. | Keep `"Mesh"`, take upstream's changes to the surrounding struct. The literal is the whole change. |
| `CMakeLists.txt` | `WITH_CADEX_ENGINE` option + `CADEX_ENGINE_DIR` cache path | Declares the option that bundles the engine. Additive: one `option()`, one `set(... CACHE PATH ...)`. | Re-add the block; it depends on nothing around it. |
| `source/creator/CMakeLists.txt` | `install()` rules for the engine payload under `WITH_CADEX_ENGINE`; `Blender.app` → `${CADEX_APP_NAME}.app` in the install destinations and `OUTPUT_NAME` | The engine block is additive, one guarded block beside the existing `scripts` install (ADR-023, ADR-030). The rename is six string literals routed through one variable so the product is `Cadex.app` (ADR-030). | Re-add the engine block after upstream's install rules; re-apply the variable wherever upstream reintroduces a `Blender.app` literal. |
| `build_files/cmake/testing.cmake`, `build_files/cmake/platform/platform_apple.cmake` | one `Blender.app` literal each → `${CADEX_APP_NAME}.app` | Same rename; these two hold the test-install and `DYLD_LIBRARY_PATH` paths that would otherwise point at a bundle that is not built. | One-line re-apply. |
| `source/blender/windowmanager/intern/wm_window.cc` | two string literals: `"Blender"` → `"Cadex"`, and `" - Blender {version}"` → `" - Cadex"` | The window title is the most visible instance of the product name (ADR-030). The upstream version string is dropped rather than relabelled — "Cadex 5.3.0 Alpha" would be a lie about which version of what; the shell version stays in the status bar and the About dialog. | Two-line re-apply inside `wm_window_title_text()`. |
| `release/darwin/Blender.app/Contents/Info.plist` | `CFBundleName`, `CFBundleExecutable`, `CFBundleIdentifier`, `CFBundleIconFile`; `CFBundleIconName` **removed** | The bundle's own identity (ADR-030). `CFBundleIconName` resolves into `Assets.car` and wins over `CFBundleIconFile` on macOS 11+, so leaving it would have meant shipping our icns and never showing it. | Keep our four values and keep `CFBundleIconName` absent; take upstream's other keys. |

`creator_args.cc` was the other route to a default app template and was
rejected: a data default in a DNA header conflicts as a data blob, whereas
argument-parsing code conflicts as logic. The same escape hatch
(`--app-template default`) exists either way.

## 3. Kept — the shell stands on these

| Tree | Why kept |
|---|---|
| `shell/source/blender/` | the editors, window manager, DNA/RNA, GPU layer, and BMesh. The shell *is* this. |
| `shell/source/creator/` | entry point and the install rules that place the engine in the bundle. |
| `shell/intern/ghost` | windowing and input. |
| `shell/lib/<platform>` | submodules, never content — 1.3 GB of prebuilt libraries per platform from `projects.blender.org`. `update = none` in `.gitmodules`; `pixi run setup` checks out the one this platform needs. |
| binary assets in **git-LFS** | 6,712 files, ~790 MB, declared by extension in `shell/.gitattributes` (`*.dat`, `*.blend`, images, `*.a`, `*.dylib`, …). See §7. |
| `shell/build_files/` | the CMake platform layer the shell configures through. |
| `shell/release/darwin/` | the `.app` skeleton, `Info.plist`, icons. Keeps its inherited directory name (`Blender.app`) deliberately — renaming it would churn every file underneath for no product benefit; only what is *installed* is renamed. |

## 4. Removal candidates — Phase 13b, not yet started

Each is a `WITH_*` CMake option, which makes the *disable* half of the
protocol nearly free: flip it off, verify the gate, commit; delete the tree
and verify again, commit. None of them is on the path from a chat message to
tessellated BREP on screen.

| Tree / option | Size | Note |
|---|---|---|
| `WITH_CYCLES` → `shell/intern/cycles` | ~48 MB source, and by inspection the single largest block of build time | A path tracer. Cadex renders solid-shaded BREP tessellation. |
| `shell/tests/files/` | 784 MB | Blender's own render/regression fixtures. The single biggest line item in the working tree. Nothing in the four gate suites reads it. |
| `shell/locale/` | 80 MB | Translations for a UI the app template hides. |
| the VSE, grease pencil, the compositor | — | Whole editors the Cadex layout never opens. |
| `shell/release/datafiles/` (unused parts) | — | Audit before touching: the matcap the viewport style asks for lives here. |

The engine half has its own list — `src/Gui` (Phase 8), `src/Mod/{Start,Test,Help}`
(built, shipped in nothing — `docs/FREECAD.md` §1), and the 2.3 GB staged
payload that carries LLVM twice (`docs/cadex-release-packaging.md`).

**Do not start these mid-move.** They are ordinary subtractive work under
the normal protocol, one tree per pair of commits, each independently
verifiable against `CADEX-BLENDER-GATE`.

## 5. Scheduled deletions from our own code

Not inherited — ours, and listed here so the two halves of the shell's
shrinkage are in one place.

- **The app template mechanism** (294 lines). It exists purely to suppress
  Blender's UI. It goes when a startup configuration replaces it, as its own
  commit — deleting it before then just restores stock Blender's interface
  (`docs/ROADMAP.md` Phase 9).

## 6. Already deleted

- **The local bpy modes** (ADR-030, Phase 9): `cad_api.py`, `validation.py`,
  `scene_graph.py`, the local half of `model.py` / `model_api.py` /
  `tools.py`, `modes.py`'s CAD overlay and mode registry, the mode dropdown,
  and `tests/python/bl_mesh_agent_cad.py`. This was where nearly all the deep
  Blender coupling lived — BOOLEAN/BEVEL modifiers, the depsgraph, BVHTree,
  `orphans_purge` — so it is also the largest single decoupling win
  available on the shell side.
- **`build_files/utils/fetch_cadex_engine.py`** and
  **`build_files/cadex_engine.txt`** (ADR-030): release-tag fetching and
  per-platform SHA256 pinning for the engine payload. Both existed only to
  move a payload between two repositories.
- **`.github/workflows/mesh-build.yml`** (ADR-030): folded into the root
  `.github/workflows/cadex-app.yml`, which builds the engine it ships.

## 7. git-LFS, and what it costs

Blender's `.gitattributes` tracks binaries **by extension** — `*.dat`,
`*.blend`, `*.png`, `*.exr`, `*.a`, `*.dylib`, `*.whl` and ~40 more — so
importing the tree brought git-LFS with it. Measured at the first push
(2026-07-25): **6,712 objects, ~790 MB**, against a plain-git pack of only
81 MB. Where it lives:

| Path | LFS files |
|---|---|
| `shell/tests/files/` | 6,351 |
| `shell/release/datafiles/`, `release/windows/`, `release/darwin/` | 340 |
| `shell/assets/` | 15 |

Three things follow, and none of them are obvious from the tree:

- **git-lfs is required to clone**, not optional. `release/datafiles/icons/`
  is LFS, and the build installs those into the bundle for the application
  to read — a clone without git-lfs puts pointer *text* files there. The
  test fixtures failing would be tolerable; corrupt runtime datafiles are
  not. `README.md` says so first, before the clone line.
- **It is close to GitHub's free ceiling.** The free tier is 1 GB of LFS
  storage and 1 GB of bandwidth *per month*; we are at ~790 MB of storage,
  and every full clone spends ~790 MB of bandwidth. Two clones in a month
  exceeds it. This is a quota to watch, not a hypothetical.
- **The fix is already the top of §4.** `shell/tests/files/` is 6,351 of the
  6,712 objects and the single biggest line item in the working tree.
  Removing it under the normal protocol takes LFS from ~790 MB to ~50 MB and
  the problem stops existing. That was already the #1 Phase 13b candidate on
  size grounds; the LFS quota is a second, sharper reason.

The first push also **failed once** before succeeding: the LFS upload
completed, then the ref update died with *"Connection to github.com closed
by remote host"*. A plain retry worked, since the LFS objects were already
server-side by then. Worth knowing so the next person does not go hunting —
and worth noting that the shell script idiom `git push … | tail` reports
`tail`'s exit status, not the push's, which is how a failed push can look
like a clean one.
