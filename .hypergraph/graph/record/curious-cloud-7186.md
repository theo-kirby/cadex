---
node_id: bae41a76-ffd7-574a-811c-4deb6c993318
slug: curious-cloud-7186
title: File and Edit go native, the window bars go away, and the product gets a version — ADR-166
created_at: '2026-08-29T09:27:40+00:00'
parents:
- civic-glade-9153
summary: ''
---
## What

ADR-166, three parts, one sitting with ADR-164/165:

1. **File and Edit are native macOS menus.** Built in
   `GHOST_SystemCocoa.mm` beside Blender's existing app/Window menus; each
   item carries a tag in `representedObject`, nil-targets
   `cadexMenuAction:` on the app delegate, which pushes the tag as a new
   `GHOST_kEventNativeMenu` (`GHOST_EventString`, the
   `GHOST_kEventOpenMainFile` shape); the tag→operator map lives in
   `wm_window.cc` so GHOST never learns an operator name. App menu literals
   now say About/Hide/Quit **Cadex**, and Settings… sits there per the HIG.
   `topbar.py` loses its menus and the `TOPBAR_HT_upper_bar` draw swap,
   keeping the four product operators (import asset, link part, refresh
   linked, export printable) + dialogs. No key equivalents on the items —
   Blender's keymap owns shortcuts. Open Recent and the stock Import/Export
   submenus did not survive (dynamic Blender menus a static NSMenu cannot
   host); noted in the ADR as revisit-if-missed.
2. **No top bar, no status bar.** `ED_screen_global_areas_refresh`
   (`screen_edit.cc`) frees the global areas instead of creating them,
   which also strips bars off windows loaded from saved files.
3. **Product version, starting 0.0.5.** Repo-root `VERSION` is the source
   of truth; `package/app/bump_version.sh [patch|minor|major]` bumps it.
   `build_app.sh stamp_version` writes it into the bundle
   (`Resources/cadex_version.txt` + `CFBundleShortVersionString`) with a
   commit-count `CFBundleVersion` (294 at first stamp), and re-signs
   ad-hoc. `wm_window_title_text` appends `" - Cadex <version>"` read from
   the stamp — title is now "Untitled - Cadex 0.0.5". Build number
   increments per commit with no state and no CI changes (CI runs
   build-shell, which stamps).

## Why

Operator direction: File/Edit belong in the OS menu bar like every Mac
app; the bottom status bar (mouse hints + Blender version) should go so
the window is all panels; the product should carry and display its own
version (0.0.5 now, 0.1.0 after a few more changes) with an
increment-on-build scheme.

## Method

Inherited-tree diff grew by four files, now ledgered as
`docs/BLENDER-TREE.md` **§2d — the window chrome**: `GHOST_Types.hh` (one
enum row), `GHOST_SystemCocoa.hh` (one declaration), `GHOST_SystemCocoa.mm`
(the menus + handler + three identity literals), `screen_edit.cc` (the
global-areas free). §2a stays eight files; `wm_window.cc`'s §2a row now
also carries the version suffix and the menu-event case. Verified:

- Full-screen capture of the running bundle: menu bar reads
  Apple/Cadex/File/Edit/Window, title "Untitled - Cadex 0.0.5", no
  in-window bars, editors edge to edge.
- System Events against the live app: File menu lists all ten rows,
  "Save As…" enabled=true (nil-target resolution works), and clicking
  Settings… opened the Preferences window — dispatch proven end to end.
- `pixi run gate`: exit 0, `"ok": true` (startup-layout test passes with
  the bars gone).
- `bl_mesh_agent.py`: "All tests passed"; `test_native_menu_targets_exist`
  replaces the topbar test and mirrors the C map — every target operator
  pinned to exist, the three in-window menus and the install machinery
  pinned gone. `bl_mesh_agent_cadex.py`'s template check drops its
  `_cadex_topbar` half.
- Stamp check: `cadex_version.txt` = 0.0.5, CFBundleShortVersionString =
  0.0.5, CFBundleVersion = 294.

## Result

The window is the editors and nothing else; the chrome is the OS's. Docs
updated: DECISIONS ADR-166, BLENDER.md (new "The window chrome" section,
topbar.py row, app-template section), BLENDER-TREE §2d + §2a row,
AGENTS.md (four groups), cadex-release-packaging.md (version stamping).
Uncommitted with the ADR-164/165 work, on top of `114e90ec`.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 114e90ec6d2f973c06f48a3b8e4ccd286b75422f

## State Impact

- target: shy-crane-2573 — File and Edit are native macOS menus (GHOST_kEventNativeMenu, tag→operator map in wm_window.cc, BLENDER-TREE §2d); the top bar and status bar are gone (global areas freed in screen_edit.cc); the window title is '<name> - Cadex <version>' read from a build stamp. VERSION at the repo root (0.0.5) is the product version, bump_version.sh bumps it, build_app.sh stamps bundle + Info.plist with a commit-count build number.
