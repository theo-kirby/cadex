# BLENDER-TREE.md — Inherited Shell Substrate Inventory

Verified against source: 2026-08-01

`shell/` is a Blender fork. This is its ledger — what we keep, what is
slated for removal, what is already gone — the peer of `docs/FREECAD.md`
for the engine half, in the same format and under the same rules.

The change policy is in `CLAUDE.md`: `shell/scripts/addons_core/mesh_agent/`
is ours and subtractive changes there are encouraged; **everything else
under `shell/` is inherited-Blender and conservative**. Removals execute
under the two-commit protocol in `docs/FREECAD.md` §3 (disable, verify;
delete, verify) and are logged in `docs/DECISIONS.md`.

Everything in this file is `[Blender-inherited]` unless noted.

**Provenance.** Imported 2026-07-25 as a squashed snapshot of the `mesh`
repository at `ac5af55948d` (branch `mesh-main`), plus one working-tree
change to `source/creator/CMakeLists.txt` since committed there as
`f7e85e80039` (ADR-030). Blender's own 163,789-commit history stayed behind,
deliberately: we delete from this tree, we do not track upstream. The
pre-merge history lives at `github.com/theo-kirby/mesh` (branch
`mesh-main`); the local working copy was deleted 2026-07-25.

## 1. Ours, inside the fork `[Cadex-new]`

These files exist in no upstream Blender and cannot conflict with one.

| Path | What | Lines |
|---|---|---|
| `shell/scripts/addons_core/mesh_agent/` | the add-on: chat, params, headers, the top bar, the cadexd protocol client, hydration, playback, picking, and — on `MJC` — the collision overlay and the policy-output readout | 8,684 (21 files) |
| `shell/source/blender/editors/space_cadex_chat/` | the Cadex Chat editor: transcript, message box, header (ADR-035) | 202 |
| `shell/source/blender/editors/space_cadex_params/` | the Cadex Parameters editor (ADR-035) | 170 |
| `shell/scripts/startup/bl_app_templates_system/Mesh/` | the app template: `startup.blend` carries the layout, `__init__.py` enables the add-on, installs the Cadex top bar and suppresses the splash (ADR-037, ADR-041, ADR-042) | 111 + a 267 KB `.blend` |
| `shell/tests/python/bl_mesh_agent{,_cadex}.py` | the agent suites; `bl_mesh_agent_cadex.py` prints the `CADEX-BLENDER-GATE` evidence line | 4,210 (2 files) |
| `shell/release/darwin/Blender.app/Contents/Resources/cadex_icon.icns` | the Dock icon. Generated from `cadex-logo-white.png` by `package/app/make_app_icon.py` — regenerate rather than edit (ADR-059) | a 249 KB binary |

The add-on was 5,714 lines across 20 files at import; ADR-030 took it to
4,577 across 17 by deleting the local bpy modes; ADR-035 added `spaces.py`
and took ~250 lines of geometry machinery out of `ui.py` (705 → 449);
ADR-041 added `topbar.py`; ADR-043 added the import-geometry operator and
tool (5,937 → 5,987). The app template was 294 lines, then 340, and is
now 111 because the layout is a file.

On branch `MJC` only, ADR-078 added `cadex_collision.py` (546) and ~270
lines across `cadex_backend.py`, `ui.py`, `tools.py` and `modes.py`, plus
~410 lines of gate suite; ADR-083 then added the Policy Outputs panel —
~100 lines of `cadex_animate.py`, ~75 of `ui.py`, 27 of `__init__.py` and
~95 of gate suite. `git diff --stat <merge-base> -- shell/` is **8 files,
+1,518/-4**, and every one of those files is under
`shell/scripts/addons_core/mesh_agent/` or `shell/tests/python/`. **It is
entirely inside code that is ours.** Nothing in §2 moved: the
inherited-tree delta is unchanged, §2a is still eight files and must stay
eight.

ADR-083 is worth reading as the worked example of *why* that holds. The
panel wanted a window; a window is a space type, and a space type is
`DNA_space_enums.h` + `spacetypes.cc` + `rna_space.cc` + `BKE_context` +
two CMake lists + a new C++ directory — the whole of §2b, for a readout.
Drawn as a `Panel` in the editor that already exists it cost the inherited
tree nothing. The one thing that could not be avoided that way,
`match_region_with_redraws` having no `SPACE_CADEX_PARAMS` case, was paid
with a `frame_change_post` handler in the add-on instead of a line in
`screen_ops.cc`. **That trade — an add-on line for a §2b line — is the
move to reach for.**
Counted 2026-07-31 — treat these as of that date, not as a contract.

## 2. Modified upstream files — the whole delta

Two kinds of edit, and they age very differently. **2a** is product identity:
string literals and guarded CMake blocks, eight files, and it must stay eight.
**2b** is the price of owning editors and of not shipping the ones we do not
want (ADR-035, ADR-036) — a deliberate, bounded investment that roughly
tripled the surface. **2c** is the in-flight message-box work.

Every addition here is a future merge conflict. The distinction that matters
is *how* it conflicts: 2a and most of 2b conflict as insertions the compiler
finds, while a rewritten function body conflicts as logic. Phase 12 (ADR-025)
retires the Blender shell wholesale, which is the horizon on all of it.

### 2a. Product identity — eight files, and they stay eight

| File | Change | Why | On conflict |
|---|---|---|---|
| `source/blender/makesdna/DNA_userdef_types.h` | `app_template` default `""` → `"Mesh"` | A new user meets the chat-driven layout without finding it in a menu (ADR-024). `--app-template default` still escapes to stock Blender. | Keep `"Mesh"`, take upstream's changes to the surrounding struct. The literal is the whole change. |
| `source/blender/blenloader/intern/readfile.cc` | `read_userdef` resets `app_template` to the DNA default rather than to `'\0'` | Upstream's comment says *use the default one* but the code hardcodes upstream's default, so the row above only ever reached a profile with no `userpref.blend` at all — every existing profile started as stock Blender, and a double-clicked bundle cannot pass `--app-template` (ADR-058). | Two-line re-apply at the end of `read_userdef`. Take the literal from the DNA member initializer, never restate `"Mesh"` here. |
| `CMakeLists.txt` | `WITH_CADEX_ENGINE` option + `CADEX_ENGINE_DIR` cache path | Declares the option that bundles the engine. Additive: one `option()`, one `set(... CACHE PATH ...)`. | Re-add the block; it depends on nothing around it. |
| `source/creator/CMakeLists.txt` | `install()` rules for the engine payload under `WITH_CADEX_ENGINE`; `Blender.app` → `${CADEX_APP_NAME}.app` in the install destinations and `OUTPUT_NAME` | The engine block is additive, one guarded block beside the existing `scripts` install (ADR-023, ADR-030). The rename is six string literals routed through one variable so the product is `Cadex.app` (ADR-030). | Re-add the engine block after upstream's install rules; re-apply the variable wherever upstream reintroduces a `Blender.app` literal. |
| `build_files/cmake/testing.cmake`, `build_files/cmake/platform/platform_apple.cmake` | one `Blender.app` literal each → `${CADEX_APP_NAME}.app` | Same rename; these two hold the test-install and `DYLD_LIBRARY_PATH` paths that would otherwise point at a bundle that is not built. | One-line re-apply. |
| `source/blender/windowmanager/intern/wm_window.cc` | two string literals: `"Blender"` → `"Cadex"`, and `" - Blender {version}"` → `" - Cadex"` | The window title is the most visible instance of the product name (ADR-030). The upstream version string is dropped rather than relabelled — "Cadex 5.3.0 Alpha" would be a lie about which version of what; the shell version stays in the status bar and the About dialog. | Two-line re-apply inside `wm_window_title_text()`. |
| `release/darwin/Blender.app/Contents/Info.plist` | `CFBundleName`, `CFBundleExecutable`, `CFBundleIdentifier`, `CFBundleIconFile`; `CFBundleIconName` **removed** | The bundle's own identity (ADR-030). `CFBundleIconName` resolves into `Assets.car` and wins over `CFBundleIconFile` on macOS 11+, so leaving it would have meant shipping our icns and never showing it. | Keep our four values and keep `CFBundleIconName` absent; take upstream's other keys. |

`creator_args.cc` was the other route to a default app template and was
rejected: a data default in a DNA header conflicts as a data blob, whereas
argument-parsing code conflicts as logic. The same escape hatch
(`--app-template default`) exists either way.

### 2b. The Cadex editors — ADR-035 and ADR-036

Adding a space type to Blender means touching every exhaustive `switch` over
`eSpace_Type`. These are mechanical, `-Wswitch` finds the ones that matter,
and their number is a property of Blender's design rather than of ours. A
conflict here is a one-line re-add per row.

| File | Change | On conflict |
|---|---|---|
| `makesdna/DNA_space_enums.h` | `SPACE_CADEX_CHAT = 25`, `SPACE_CADEX_PARAMS = 26`; `SPACE_TYPE_NUM` bumped | Append only — the header says so. Renumbering breaks every saved `.blend`. |
| `makesdna/DNA_space_types.h` | two bare `SpaceLink`-header structs | Re-add. They have no fields and must not gain any: DNA is append-only forever. |
| `editors/include/ED_space_api.hh` | two declarations | Re-add. |
| `editors/space_api/spacetypes.cc` | two `ED_spacetype_cadex_*()` calls added; **eight removed** (ADR-036; `space_node` came back in ADR-066); six `ED_operatormacros_*` made conditional | The removals are the load-bearing half: this list *is* the editor menu. Take upstream's additions, then re-apply both edits. |
| `editors/CMakeLists.txt`, `editors/space_api/CMakeLists.txt` | two `add_subdirectory` / two `LIB` entries | Re-add. The hidden editors keep theirs — see ADR-036 on why compiling them out does not work. |
| `makesrna/intern/rna_space.cc` | two `rna_enum_space_type_items` rows, two `rna_Space_refine()` cases, `rna_def_space_cadex_*()` + calls | Rows go under the `General` heading, after `SPACE_VIEW3D`. |
| `makesrna/intern/rna_space.cc` | `rna_SpaceNodeEditor_tree_type_poll` filtered to `Cadex`-prefixed tree idnames (ADR-066) | The peer of the `space_file.cc` row below, and for the same reason: a node tree type is a *subtype* of `SPACE_NODE`, so not-registering cannot hide the stock four. Re-apply as the first statement of the poll; it keys on the identifier prefix, so a second Cadex tree needs no edit. |
| `makesrna/intern/rna_screen.cc` | `rna_Area_ui_type_itemf`: skip unregistered space types, hold group headings back until something survives under them | The one behavioural edit in 2b. Re-apply inside the loop; the enum rows themselves must never be deleted (`ED_area_name` indexes them). |
| `windowmanager/intern/wm_draw.cc`, `editors/interface/templates/interface_template_search_menu.cc`, `editors/animation/anim_filter.cc`, `blenkernel/intern/grease_pencil_convert_legacy.cc` | two cases each in exhaustive switches | `-Wswitch` fails the build if you forget. |
| `editors/interface/resources.cc` | both types mapped to `btheme->space_properties` (two sites) | Re-add, else the `default:` branch hands them the viewport's grey. |
| `blenkernel/BKE_context.hh`, `blenkernel/intern/context.cc` | `CTX_wm_space_cadex_chat()` / `_params()` + forward decls | Re-add. |
| `python/intern/bpy_rna_callback.cc` | `RNA_SpaceCadexChat` / `Params` → space id | Needed for `draw_handler_add`. |
| `blenkernel/intern/screen.cc` | both types added to the header/footer alignment lists | Keeps their headers pinned to the top like the other panel-column editors. |
| `editors/screen/area.cc`, `editors/screen/screen_edit.cc`, `blenloader/intern/versioning_280.cc` | null-guard three `SpaceType::create` paths, falling back to the viewport | **Required by ADR-036.** Inherited call sites still ask for `SPACE_IMAGE` (render result) and `SPACE_GRAPH` (drivers editor); without these it is a null deref. |
| `editors/space_file/space_file.cc` | `file_space_subtype_item_extend` drops the asset-browser item | The asset browser is a `SpaceFile` subtype, not a space type, so not-registering cannot hide it. |
| `scripts/startup/bl_ui/space_toolsystem_toolbar.py` | `classes` trimmed to the viewport's tool panel (ADR-036); `NODE_PT_tools_active` **added back** (ADR-066) | Registering a `ToolSelectPanelHelper` is what runs its `register()`, which is the only thing that sets `_tool_group_active`. Leaving it out was invisible while `SPACE_NODE` was unregistered; with the editor live, the first click into it raises `AttributeError` from `wm.tool_set_by_id`. Its `_defs_node_*` live in this same file, so it pulls in no `bl_ui.space_node`. |
| `blenkernel/intern/blendfile.cc`, `scripts/modules/addon_utils.py` | `cycles`, `pose_library`, `io_mesh_uv_layout` no longer enabled by default | Each registers against an editor we do not build and raised on every launch. Still installed. |
| `windowmanager/intern/wm_operators.cc` | 24 `WM_modalkeymap_assign` calls for missing operators removed | Each was a `CLOG_ERROR` per launch. |
| `scripts/startup/bl_ui/__init__.py` | nine `space_*` modules leave `_modules` | They cross-import each other; remove as a group or not at all. |
| `scripts/startup/bl_ui/space_toolsystem_toolbar.py` | image/node/sequencer tool panels no longer registered | Registering against a missing space type raises and **aborts bl_ui's whole registration loop**. |
| `scripts/presets/keyconfig/keymap_data/blender_default.py` | four node keymap items pass `None` instead of macro sub-operator properties | Raises in `_init_properties_from_data` otherwise. The rest of the dead keymaps stay — see §4. |

### 2c. The message box — ADR-034

| File | Change | On conflict |
|---|---|---|
| `editors/include/UI_interface_layout.hh`, `editors/interface/interface_intern.hh`, `editors/interface/interface_layout.cc`, `editors/interface/interface_handlers.cc`, `makesrna/intern/rna_ui_api.cc` | `confirm_only` on the text-box widget: commit the value only when the edit ends by explicit confirmation | The first *behavioural* edit in this table rather than a literal or an insertion, and the one most likely to conflict as logic. Re-apply inside `ui_textedit_end` / the layout API. |

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
| the nine unregistered editors: `space_action`, `space_clip`, `space_graph`, `space_image`, `space_nla`, `space_node`, `space_script`, `space_sequencer`, `space_spreadsheet` | — | **Disabled 2026-07-26 (ADR-036)**: not registered, so not in the editor menu. Compiling them out is the delete half and needs real work — kept subsystems reference 252 symbols across them. Deleting them also retires ~3,000 lines of now-dead keymap data in `blender_default.py`, which is what still prints ~92 `property ... not found` warnings on a headed launch. |
| grease pencil, the compositor | — | Whole editors the Cadex layout never opens. |
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

Nothing is currently scheduled. The app template mechanism, the one entry this
section carried, **landed 2026-07-26** — see §6.

## 6. Already deleted

- **The app template's layout machinery** (ADR-037, ROADMAP Phase 9):
  `_apply_simple_ui` and its 40-attempt retry loop, `_remove_other_workspaces`,
  `_collapse_to_viewport`, `_empty_scene`, `_hide_foreign_tool_panels`,
  `_style_props`, `_style_viewport`, `_open_params`, `MESH_PANELS`,
  `_hidden_panel_polls`, `_set_area_type`, `_reregister_with_draw`'s
  `PROPERTIES_HT_header` swap. 340 lines → 98, then 111 with ADR-041 and
  ADR-042. The layout is `Mesh/startup.blend`; what survives enables the
  add-on, installs the Cadex top bar and suppresses the splash, none of which
  a `.blend` can carry.
- **The geometry classifier** (ADR-035): `mesh_agent/ui.py`'s `_area_roles`,
  `_area_with_role`, `_column_role`, `chat_area`, `input_area`,
  `open_params_area`, `close_params_area`, `open_input_area`,
  `_configure_params_area`, `draw_chat_input_header`, and the constants
  `PARAMS_CONTEXT`, `_COLUMN_SLACK`, `INPUT_AREA_UNITS`. The space type is the
  answer now. 705 lines → 449.
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
