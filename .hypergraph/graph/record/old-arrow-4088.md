---
node_id: 7021b708-824b-5305-bd25-6d8347926cb5
slug: old-arrow-4088
title: 'orun2 W1/D1: before-numbers measured and shell parity ledger skeleton'
created_at: '2026-10-03T11:01:31+00:00'
parents:
- winter-stone-5109
summary: ''
---
## What
D1's "before" numbers measured and committed (`docs/probes/orun2/D1-BEFORE.md`, plus the reusable `measure_d1.sh` for the "after" run). The parity ledger skeleton `docs/SHELL-PARITY.md` written: one row for each of the 47 `mesh_agent` entries, the 23 shell tools and the 7 Cadex editors, with no blank row. Commit `94b5be8f`. Nothing deleted.

## Why
The critic asked for the first rung of the horizon ladder. That rung: measure D1's before numbers, then write the parity skeleton only after reading every module, so that nothing is deleted unread (W1 and the question policy). Done as asked, with no deviation.

## Method
- **Tree numbers.** Taken from `git ls-files`, `git ls-tree -r -l`, the LFS-attributed pathspec and `wc -l` by tree at `a375745c`.
- **Clone to first page.**
  - Measured with `measure_d1.sh` on sb1x (32 cores):
    1. a `file://` pack clone of `ouroboros/orun2`;
    2. `pixi install`;
    3. `setup-engine`;
    4. `build-engine` with `CCACHE_DISABLE=1`;
    5. `./cadex review` on an empty project dir;
    6. curl for HTTP 200.
  - `cadex review` was first confirmed to serve an empty project.
- **Module audit.** All 44 Python modules plus `pi_tools.js` (about 29.6k lines) were read in full by three parallel read-only readers. Each reader described each module in its own words, without copying any GPL code. They grepped `cli/` and `src/Mod/cadex` for counterparts. I spot-checked the named counterparts (`collision_proxies`, `training_telemetry`, `presentation`, `list_runs`, `write_section`, `export_outputs` / `export_blueprints`, `CadexStudio.materials`, `printable_roster`); all of them exist.
- **Tests.** The docs and licensing tests in `cadex_tests` pass (33 passed, 1 skipped). No code was touched, so the full suites were not rerun.

## Result
**Tree and LOC, before:**
- 25,633 tracked files, of which `shell/` is 19,446 (75.9%).
- 6,716 LFS objects, all under `shell/`, declaring 824 MB. git-lfs is absent on sb1x, so these are pointers.
- Python LOC: 873,875 in total. `shell/` has 549,304, `mesh_agent` 29,629, `src/Mod/cadex` 139,983 and `cli/` 46,392.
- JS LOC: 2,531.
- C/C++ LOC: 3.59M in `shell/` and 761k in `src/`.

**Setup and clone to first page:**
- Setup is 4 steps on either route. The documented app route is macOS-only and needs git-lfs and Xcode. The linux engine-plus-review route is undocumented as a sequence and serves one project, read-only.
- Clone to first page took **114 s**: clone 6 s, `pixi install` 1 s (warm rattler cache; a cold download was not measured), `setup-engine` 1 s, and `build-engine` 105 s (1,185 C++ compiles with ccache off).

**Footprint:**
- `.pixi` is 5.65 GB.
- `build/release` is 226 MB.
- The staged payload is 3.26 GB.
- There is no app bundle on linux.

**Live references for S1 to clear:** 10 `pixi.toml` lines, 2 `package/` files, 9 test files and 192 live docs.

**Parity verdicts (proposed):** owner-to-confirm rows are `cadex_live` and the Live editor, `make_blueprint` / `save_blueprint` / `cadex_sheet`, `demo/biped.cadex`, the agent half of `collision_view`, and the prefs time and memory budgets.

**For later criteria:**
- **A1 concern:** the shell set `ENABLE_TOOL_SEARCH=false` (ADR-163) so that MCP tools are not deferred when built-ins are off. `cli/cadex_cli/agent.py` `_environment` does not. It is unconfirmed whether CLI turns are affected; A1 must check this and record the answer.
- **D2:** the dashboard is display-only today, so every steering PORT row is new D2 work. Two gaps were identified: the review mesh has no face-ID channel, which picking needs, and there are no exploded-view or actuator-bar readers.
- **Guidance:** §4 of the ledger lists the guidance that lived only in the shell, as input for A1.

The scratch clone is at `/tmp/orun2-d1`, outside the repo. The tail now holds 1 unreconciled record.

Dispatch closed: 1 unit — D1 before-numbers measured and the 47+23+7-row shell parity ledger skeleton written, every module read first.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 94b5be8fc2b61097a0443f20de2f26476bea6db0

## State Impact

- target: shady-clover-5534 — docs/SHELL-PARITY.md skeleton exists: 47 module, 23 tool and 7 editor rows, all read in full, none blank; statuses still interim (to port / drop proposed), no ADRs or ported tests yet
- target: sweet-bloom-8352 — before numbers measured (docs/probes/orun2/D1-BEFORE.md): 25,633 tracked files (19,446 shell), 6,716 LFS objects, 873,875 py LOC, 4 setup steps, 114 s cold clone→engine→first page on sb1x, payload 3.26 GB; measure_d1.sh ready for the after run
