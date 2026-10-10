# PERFORMANCE-AUDIT.md — Build cost on large creature assemblies

Verified against source: 2026-10-10

What this is: a measured audit of where the time goes when an agent builds
and reads a large catalog assembly through `cadex mcp`, done after the
2026-10-09 creature runs timed out. It records the profile before and after
ADR-628, what that ADR fixed, and what remains, ranked. Numbers are from
copies of the projects in a scratch directory; the originals under
`~/cadex-projects/` were not touched.

## 1. The problem as reported

- Codex/GPT-6-Astra agents on `castra-deinonychus` and `castra-leopard`
  saw `tool call failed for cadex/write_script … timed out awaiting
  tools/call after 300s`, then the same for the `inspect` and `look` they
  sent next. The revision **was** accepted (revision 3 of the deinonychus,
  saved about 85 s into the call); the reply never arrived.
- A read-only status script did `open_project(…, budgets={"timeout_seconds":
  900})` on `castra-deinonychus`, then read anatomy and fit. It ran 36
  minutes at full CPU and was killed.

## 2. The projects

From each accepted attempt's `result.json` (`report_stats.py`):

| project | report | outputs | components | static pairs (exact) | sweep joints | refused by pair budget | sweep rows (moving) |
|---|---|---|---|---|---|---|---|
| castra-deinonychus | 65.0 MB | 872 | 290 | 41,905 (870) | 21: 6 complete | 15 | 251,430 (6,864) |
| castra-leopard | 29.6 MB | 845 | 281 | 39,340 (810) | 18: 2 complete | 16 | 78,680 (3,026) |
| cfix-deinonychus-a | 11.9 MB | 218 | 71 | 2,485 (147) | 32: 20 complete, 12 passive | 0 | 49,700 (8,776) |
| cfix-leopard-a | 9.8 MB | 203 | 66 | 2,145 (137) | 31: 19 complete, 12 passive | 0 | 40,755 (7,248) |

The castra pair is the problem class: 21 QDDs, each with housing screws and
output screws as their own components, so ~290 components and ~41,000
pairs. Of the 65 MB report, 54 MB is `clearance_sweep` (each complete joint
republishes all 41,905 pairs, 97% of them rigid copies of the static row)
and 7.4 MB is the static `clearance` list (98% culled rows).

## 3. Where the time went — before (HEAD `587ffd43`)

Measured with cProfile around the worker's `main()` (a re-run of the
accepted attempt's own `request.json`, so the fit-cache path resolves as in
a real run), cProfile/timestamps around the CLI's reads, and wall clocks on
`open_project`. The box is a shared 32-core machine; load was 8-20 during
the runs, so absolute numbers carry ±20%.

### 3a. The worker build (`castra-deinonychus`)

| phase | warm fit cache | cold fit cache |
|---|---|---|
| **worker total (wall)** | **58.1 s** | **129.5 s** (142.5 s on a second, sequential run) |
| static fit `_measure_clearance` | 1.6 s | 55.8 s (870 exact pairs: `_boundary_distance` 25.9 s, `_common_volume` 26.0 s of which `common` 24.7 s) |
| joint sweeps `_measure_joint_sweeps` | 6.1 s | 25.5 s (15 of 21 joints refused in <1 s each by the pair budget) |
| joint creation `setJointConnectors` (289 calls) | 18.2 s | 17.0 s — of which **290 incremental `assembly.solve()`** 12.8-14.1 s, `matchJCS` 3.3 s, `getDownstreamParts` 2.3 s |
| part build + facts (`serialize`, 290 parts: fuses, cuts, fillets) | 16.3 s | 15.3 s |
| display tessellation (290 shapes, `standard`) | 10.1 s | 10.1 s |
| assembly references (`part_shape_facts`) | 2.1 s | 2.1 s |
| MJCF export | 1.6 s | 1.6 s |

The builds themselves fit the 300 s budget with room to spare. Neither the
static fit's O(n²) loop (41,905 box tests, 1.6 s with a warm cache) nor the
shell-gap check was a sink.

### 3b. `open_project` (the restore pass)

| | warm cache | cold cache |
|---|---|---|
| castra-deinonychus | 51.7 s | 133.5 s |

The restore re-runs the whole worker, fit included, then keeps the
**previously** accepted attempt pinned (`accept_project_candidate`: an
identical acceptance does not replace the display-bearing attempt). So the
replay's fit was measured and thrown away, and the reads that follow are
served from the old attempt anyway.

### 3c. The bridge's post-build reads — the actual sink

After every accepted build the MCP bridge reads `fit` (`read_fit`), then
`inventory`, then `anatomy`, under its lock, before it replies. `read_fit`
pages `inspect scope=clearance` 50 rows a page and expands every nested
pointer, so it walks the static pairs and every complete joint's sweep rows.
Engine side, **every page** re-read and re-parsed the accepted
`result.json` and re-joined every pair with its labels before slicing 50.

| read | pages | per page | total |
|---|---|---|---|
| deinonychus `fit` | 5,942 | 0.48 s | **~2,900 s (48 min)** — measured: 4,821 pages in 2,333 s, then stopped at its 2,400 s cap |
| deinonychus `inventory` | 55 | — | 0.5 s |
| deinonychus `anatomy` | 2 | — | 0.5 s |
| leopard `fit` | 2,419 | 0.42 s | **~1,020 s (17 min)** |

This is both incidents:

- **The 300 s timeouts.** Worker + publication ≈ 85-90 s, then the fit
  read started and needed about 48 minutes. Codex's client gave up at 300 s; its
  next `inspect` and `look` queued behind the bridge's lock and timed out
  too.
- **The 36-minute "restore".** The restore was ~52-133 s; the rest was the
  fit read (anatomy is 2 pages).

### 3d. Timeouts and budgets across the layers

| layer | value | enforced by |
|---|---|---|
| Codex MCP client `tools/call` | **300 s** on these runs | the client — Cadex cannot see it |
| engine budget per worker run (ADR-517) | **300 s** default; the castra projects stored none in `agent.json` | `run_process` wall timeout and `RLIMIT_CPU` |
| sweep total (ADR-622) | min(180 s, run budget left − 20 s − ¼ of build age) | the worker |
| sweep child | 90 s each, four at once | `subprocess.run(timeout=)` |
| `CadexdClient.request` | 900 s (`DEFAULT_TIMEOUT_SECONDS`) | **not enforced while the engine is silent**: `_read_frame` blocks in `readline()` and only checks its deadline between frames |
| status script | `timeout_seconds: 900` | bounds each worker run, not the reads after it |

The mismatch: the client's 300 s equals the engine's default 300 s, and a
build reply arrives *after* the worker run plus publication plus the reads,
so any build that uses its budget, or any reply whose reads are slow, times
out in the client first — with the revision already accepted. A per-call
budget of 900 s did not help the status script because no worker run was
slow; the per-page reads were each short and unbounded in number.

## 4. What ADR-628 fixed, and the speedups

1. **Inspection pages are served from one join.** `CadexInspection` memoises
   the joined inventory/clearance/anatomy value per accepted report (keyed
   on the report file's stat identity and the accepted revision), and the
   preview size test stops encoding at its 1 KiB limit.
2. **The restore pass measures no fit** when its replay cannot become the
   served attempt (working revision = accepted revision and the pinned
   report is on disk). Exports, traces and policies — digest material — are
   still built, so the digest proof is unchanged.
3. **The client timeout is documented against the engine budget**
   (`docs/CLI.md` §2a): the client's tool timeout should be the engine
   budget plus a minute.

Measured after (same copies, same box):

| measurement | before | after |
|---|---|---|
| deinonychus `fit` read (5,942 pages) | ~2,900 s | **12.2 s** (2 ms a page; same verdict, 41,905 pairs, 65 failing) |
| leopard `fit` read (2,419 pages) | ~1,020 s (0.42 s a page: 1,211 pages measured in 509 s) | **5.8 s** |
| deinonychus `open_project`, cold cache | 133.5 s | **43.2 s** |
| leopard `open_project` (after: cold cache) | 90.0 s (warm cache; under the test suite's load) | **42.8 s** |
| status script: open + anatomy + fit (deinonychus) | >36 min (killed) | **57 s** |
| MCP `write_script` reply after acceptance (deinonychus) | +48 min of reads | **+13 s** of reads |
| worker build | 58 s warm / 130-143 s cold | unchanged |

**Tried and backed out: the sweep's pair budget.** 15 of the
deinonychus's 21 joints (16 of the leopard's 18) are reported `pair budget
exceeded: 14784 moving pairs, more than 2000` and never swept, because the
budget counts every moving pair *before* the box cull; only 21-34 pairs per
joint survive it. Counting after the cull was a six-line change and swept
them, measured sequentially on one copy:

| build | worker wall | sweep | joints complete | report |
|---|---|---|---|---|
| HEAD, cold cache | 142.5 s | 27 s | 6 / 21 | 65 MB |
| budget after cull, cold | 270.1 s | 167 s (the ADR-622 budget) | 14 / 21 | 132 MB |
| budget after cull, next build | 100.2 s | 50 s | 21 / 21 | **191 MB** |

Every complete joint republishes all 41,905 pairs, so full coverage makes
the report three times larger and the fit read ~17,600 pages. It is not in
this branch; it should land together with R1.

## 5. What remains, ranked by impact

| # | item | measured cost now | fix | estimated effort |
|---|---|---|---|---|
| R1 | **Sweep rows republish every rigid pair.** 97% of `clearance_sweep` rows (245k of 251k here) are copies of the static row; they are why the fit read is 5,942 pages and the report 65 MB. With every joint swept (R2) it is 191 MB. | 12 s of reads per reply, 54 MB of report, the worker's JSON write and every reader's parse | Publish only `relative_motion` rows per joint, with a count of the rigid ones; `CadexFitReport.sweep_summary` already reads only moving rows. Static `clearance` can likewise carry culled pairs as a count plus the exact rows. A published-shape change (XSCRIPT.md promises every pair), so an ADR and the owner's sign-off. | 1 day |
| R2 | **Most joints of a large creature are never swept.** The pair budget counts moving pairs before the box cull (§4). | 15 of 21 joints unchecked in motion (deinonychus), 16 of 18 (leopard) | Count after the cull — done and measured above — once R1 lands; the cold sweep then needs R4 too. | 1 h after R1 |
| R3 | **The fit cache is versioned by the whole 8,500-line assembly worker.** Any edit to `cadex_assembly_worker.py` (this one included) makes every project's next build cold: deinonychus 58 → 130 s, and every sweep starts over. | +70 s per project on the first build after each engine change; more with the sweep now running | Version the cache on the bytes of the measuring functions (`_measure_clearance`, `_boundary_distance`, `_shell_distance`, `_common_volume`, `_clipped_common_is_zero`, `_measure_samples`, `_sweep_joint`, the cull constants) plus the kernel. Risk: a missed dependency serves stale numbers. | 0.5 day |
| R4 | **Cold sweep cost.** A sweep child is single-CPU in the build (four children on the worker's four pinned CPUs): `distToShape` is 0.10 s a call there against 0.018 s unpinned; the claw child takes 31 s in the build, 25 s pinned alone, 7.5 s unpinned. Full coverage of the deinonychus is ~1,000 CPU-s. | 27 s cold today, because most joints are refused; 167 s once R2 lands | Measure each pair at the sample with the least box gap first and stop at the first contact sample (already partly done), reuse a pair's numbers across joints whose motion leaves it rigid, or run sweeps after the reply (an asynchronous fit) so they never sit in a tool call. The last is a direction change. | 1-3 days |
| R5 | **290 incremental solves during joint creation.** FreeCAD's `setJointConnectors` calls `solveIfAllowed` per joint: 12.8-14.1 s of solve, plus `matchJCS`/`getDownstreamParts` 5.6 s — 19 s, a third of a warm build. | 19 s per build | Turn the Assembly `SolveInJointCreation` preference off inside the worker and solve once. Changes the solver's starting configuration, so solved placements (and digests) may move in the last digits: needs a corpus run over the accepted projects before landing. | 0.5 day + corpus run |
| R6 | **Static fit, cold.** 870 exact pairs: `common` 24.7 s over 750 touching pairs (mostly screws in their housings and links welded to housings), distance 25.9 s. | 56 s cold, 1.6 s warm | Pairs welded by a fixed joint are read by the attachments report; their common volume could be bounded by the clipped check alone, or measured once per part pair across placements (the cache already does the latter warm). | 1 day |
| R7 | **Display tessellation** of 290 shapes on every accepted build. | 10 s | Cache tessellation by BREP digest + quality in the project store (display is digest-neutral). | 0.5 day |
| R8 | **The client's 900 s timeout is not enforced** while the engine is silent (`readline()` blocks). | unbounded waits | `select` on the pipe before `readline`, with the client's own line buffer. | 2 h |
| R9 | **Read-only callers still restore.** Every `open_project` re-runs the worker (43 s here) even for a status read; inspection scopes read the pinned attempt from the store and do not need it. | 43 s per read-only open | Read-only commands open with `restore: false`. | 2 h |
| R10 | **The agent cannot see the budgets in force.** | timeouts that look like hangs | `cadex mcp`'s brief could state the engine budget and the recommended client tool timeout. | 1 h |

## 6. How it was measured

Scripts lived in the session scratchpad, not the repo: `drive.py` (open and
time events), `reads.py` (open, then time `read_fit`, `read_inventory_summary`
and the anatomy read, counting inspect requests; `MODULE_DIR` points it at a
`git archive` of HEAD for the before numbers), `profile_worker.py` (re-run an
accepted attempt's `request.json` under cProfile in a fresh attempt
directory, `--cold` deletes the fit cache, `--keep-sweeps` keeps each sweep
child's input), `profile_sweep.py` (one child under cProfile, optionally
pinned to one CPU), `report_stats.py` (§2). The Codex timeline came from
`~/.codex/sessions/2026/10/09/rollout-…-01a12197…jsonl`.
