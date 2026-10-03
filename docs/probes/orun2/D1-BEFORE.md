# D1 — the "before" numbers (orun2)

Verified against source: 2026-10-03. Measured on sb1x (linux-64, 32 cores,
60 GB RAM) at `a375745c`, the orun2 run branch before any deletion. The
"after" column is filled by re-running `measure_d1.sh` once `shell/` is gone.
Every number below was measured. Nothing in this file is an estimate unless it
says so.

## Tree

| | before |
|---|---|
| Tracked files | **25,633** |
| … of which under `shell/` | **19,446** (75.9%) |
| … `src/` / `docs/` / `.hypergraph/` / `cli/` / `tools/` / `package/` / `analysis/` / `training/` | 3,412 / 968 / 944 / 109 / 70 / 24 / 8 / 7 |
| Tracked blob bytes at HEAD (`git ls-tree -r -l`) | 436,436,320 (of which `shell/` 294,412,510) |
| Git-LFS objects (all under `shell/`) | **6,716**, declaring 824,152,570 bytes. git-lfs is not installed on sb1x, so this checkout holds pointer files |
| `.gitattributes` LFS rules | `shell/.gitattributes`, 111 lines. No root `.gitattributes` |
| Submodules | `shell/lib/{linux_x64,macos_arm64,windows_arm64,windows_x64}` (none checked out here), `src/3rdParty/OndselSolver` |
| Fresh-clone `.git` | 269,075,679 bytes |
| Fresh-clone working tree (no `.git`, `.pixi`, `build`; LFS as pointers) | 453,179,173 bytes |

## Lines of code by tree (tracked files, `wc -l`)

| tree | Python | JS | C/C++ |
|---|---|---|---|
| `shell/` | 549,304 | 426 | 3,593,128 |
| … `shell/scripts/startup/mesh_agent/` | 29,629 (incl. a 566-line demo script twice) | 91 (`pi_tools.js`) | — |
| `src/` | 216,785 | 301 | 761,009 |
| … `src/Mod/cadex/` | 139,983 | 0 | — |
| `cli/` | 46,392 | 1,804 (`review_static/`; `three.module.js` is vendored) | — |
| `tools/` | 17,605 | 0 | — |
| `docs/` | 16,292 | 0 | — |
| `analysis/` | 6,986 | 0 | — |
| `package/` | 3,439 | 0 | — |
| `training/` | 3,219 | 0 | — |
| **all** | **873,875** | **2,531** | |

## Setup steps

| route | steps | prerequisites |
|---|---|---|
| The documented application (README "Build and run") | 4: `git lfs install`, `git clone`, `pixi run setup` (~1.3 GB `shell/lib`), `pixi run app` | pixi, git-lfs, Xcode CLT, `brew install cmake ninja git-lfs`. **macOS only**: on linux there is no application to reach |
| The engine plus today's dashboard on linux (the route D1 asks for) | 4: `git clone`, `pixi run setup-engine`, `pixi run build-engine`, `./cadex review --project <dir>` | pixi only. Not documented as one sequence: `cadex review` serves **one** project, read-only, and there is no projects-directory view |

Also measured: the live references that S1 must remove. There are 10 `pixi.toml` lines
naming `shell/`, `build_app` or `mesh_agent`. There are 2 `package/` files, 9 test files under
`cadex_tests` and `cli/tests`, and 192 live docs (outside `docs/history/` and
`DECISIONS.md`) that name `shell/`, `mesh_agent` or `CADEX_BLENDER_EXECUTABLE`.
No CMake file outside `shell/` names them.

## Clone to the dashboard's first page (linux route)

`measure_d1.sh <repo> ouroboros/orun2 <scratch>`:
- the clone was a `file://` pack transfer;
- the compiler cache was off (`CCACHE_DISABLE=1`);
- the pixi package cache was **warm**.

| step | cumulative wall time |
|---|---|
| `git clone` | 6 s |
| `pixi install` | 7 s (warm rattler cache: links, no download; a cold download was not measured) |
| `pixi run setup-engine` | 8 s |
| `pixi run build-engine` (1,185 C++ compiles, 32 cores) | 113 s |
| `./cadex review` → first page `HTTP 200`, 9,472 bytes | **114 s** |

## Installed footprint (linux)

| | bytes |
|---|---|
| `.pixi` environment | 5,649,462,867 |
| `build/release` (`FreeCADCmd`, `CadexGeometryWorker`, modules) | 226,308,245 (fresh clone) |
| Staged engine payload `build/engine/cadex-engine-0.0.0-linux-x64` (this checkout) | 3,258,061,207 |
| Application bundle | none on linux. The shell builds only on macOS, and its bundle was not measured here |

## What "after" has to show

The same script on the post-delete branch should show:
- the tracked-file and LOC drop;
- no LFS objects;
- a setup sequence that needs no git-lfs, Xcode or `shell/lib`;
- a documented command that serves a projects directory rather than one
  project.
