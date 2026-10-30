# CLI.md — Cadex, headless

Verified against source: 2026-10-30. Provenance: [Cadex-new] (ADR-061).

`cli/` is **the client of the cadexd protocol** — the only one (ADR-498):
no display, no `bpy`, no shell code. It is how an agent, a person at a
terminal and a pipeline drive a project. **Cadex has no agent of its own**
(ADR-538): the agent is the person's — Claude Code, Codex, Pi, any MCP
client — and it reaches the engine through `cadex mcp`, which serves the
tools and the guidance over MCP stdio, and through the commands below.

```bash
claude mcp add cadex -- "$PWD/cadex" mcp --project "$PWD/bracket"   # once, per project
./cadex guidance                                       # what the agent is told
./cadex params --set fin_angle=12 --out ./sweep/12     # no AI in the loop
```

## 1. Why it exists

The engine was never the part that needed a screen. It is a headless NDJSON
service, and as of ADR-060 it builds, tests, packages and models on a
headless Linux box.

What the CLI unlocks is not "the same thing without a window". It is a
**cost asymmetry**: the agent authors a *parametric* script once, and after
that a cheap loop sweeps its parameters and re-exports with no model in the
loop at all. An external simulator — airflow, FEA, print-time — feeds its
numbers back, and the agent is asked again only when the *shape* has to
change.

```bash
# the agent, through cadex mcp: "an impeller with 7 blades, 40 mm hub"
for angle in 8 10 12 14 16; do
    ./cadex params --project ./impeller --set blade_angle=$angle \
                   --out ./sweep/$angle --json > ./sweep/$angle.json
    simulate ./sweep/$angle/impeller.step >> results.txt
done
# the agent again: "the 14° case stalls at the tip — thicken the tip chord"
```

The agent's two requests cost tokens. The loop between them does not.

## 2. Commands

No command spends tokens: the only model in the room is the agent a person
brings.

| Command | What it does |
|---|---|
| `cadex mcp [--idle S]` | Serve the project's tools to an agent over MCP stdio (§2a). The engine opens on the first tool call and closes after `--idle` quiet seconds (default 30, held three times as long as the engine took to open, at most 900 s, ADR-685; 0 holds it), releasing the project for the agent's own `cadex … --wait` commands; a session that accepted a build lands one `PROGRESS.md` row and one project commit as it closes. Every tool call appends one line to `review/activity.jsonl` (ADR-549): `t`, `tool`, `args` (a summary — a long string only by its length, a list by its size, an object by its keys, 160 characters at most), `outcome` (`ok` or `error`), `detail`, `ms` and `call`. A call also writes an in-flight line as it starts (ADR-553): `outcome: running`, `t` its start, and the server's `pid`; its finished line, with the same `call`, hides it on read, and an in-flight line whose process has gone reads `lost`. An in-flight `evaluate` makes `/api/project`'s `stage` `evaluating`. The log is capped at 64 KiB (rewritten keeping the newest lines within 32 KiB), ignored by the project's git, and `GET /api/project`'s `activity` carries its newest ten entries. |
| `cadex guidance [--project DIR]` | Print the whole guidance an agent driving Cadex follows: the domain-neutral base, then the project's chosen style when it chose one (`cadex style`, ADR-560). A stored style the engine does not carry is a usage error. No engine. |
| `cadex params --set k=v` | Set declared parameters and rebuild. Skips the fit unless `--fit` is given (ADR-876). |
| `cadex script` | Print the project script. |
| `cadex script --set FILE` | Replace the script from a file and rebuild. The build skips the fit (its `fit` reads `deferred`) unless `--fit` is given (ADR-876). An accepted build carries `verdicts`, the brief an MCP build reply carries (ADR-689, §4). |
| `cadex export` | Write the accepted revision's outputs (§3), copied from the attempt the store retained under the accepted pin, digest-checked; no script runs and no engine opens (ADR-848). With `--rebuild`, or when the store has no valid retained attempt (or the working script is not the accepted one), it opens the engine with the restore pass, rebuilds and writes, as before. |
| `cadex section --plane XY [--offset-mm 8]` | Cut accepted tessellation through a world plane; revision-bearing SVG and JSON under `review/section/` (ADR-240, "Section and render" below). Omit `--offset-mm` and the offset is derived from the accepted bounds (ADR-273, ADR-275). |
| `cadex render` | Read retained accepted display (rebuild only when unavailable) and write front/top/right/iso SVG previews, a 1024 px studio `hero.png` (ADR-412), the concept sheet `sheet.png` (ADR-430) and `review/render/summary.json`, bearing the accepted revision (ADR-239). CPU only. |
| `cadex hero [--only ITEMS] [--run NAME] [--software] [--no-engine] [--focus REGEX]` | Write the project's presentation folder, `hero/` (ADR-677, `docs/DASHBOARD.md` §26): five stills in different looks, a dashboard screenshot, the concept sheet, the chosen rollout as `rollout.mp4`, and `hero-landscape.mp4` and `hero-square.mp4` (a turn that wipes clay → aluminium → wireframe → the design's materials, then the rollout and the training curves, plus a faster wireframe turn). The rollout is the longest episode any run's policy lasted, the newest among equals, or `--run`'s. Needs headless Chromium (GPU when there is one; `--software` forces software WebGL) and FFmpeg; opens the engine only to draw a missing concept sheet (`--no-engine`: never). `hero/hero.json` names what was made and why anything was not; exit 0 only when everything asked for was made. `--only` takes a comma-separated subset of `stills`, `dashboard`, `sheet`, `rollout`, `video` and `views`; a bare run makes all but `views`, which writes `view-{hero,side,front,rear,top,head}.png` from fixed cameras measured from the design's front towards the parts `--focus` names (default a creature's head) (ADR-792). The folder keeps itself out of the project's git. |
| `cadex hero-grid PROJECT... --out FILE [--still NAME] [--columns N] [--tile-width PX]` | Tile one still (default `wireframe`) or view from each project's `hero/` folder into one labelled image, two to a row by default (ADR-677, ADR-792). FFmpeg; no engine, no row, no commit. |
| `cadex clearance` | Write `docs/clearance.md`: every component pair, labels and catalog ids, minimum distance (mm), common volume (mm³) and verdict, at the initial solved pose, from published measurements (ADR-237). When the accepted build deferred the fit, it first rebuilds the same revision with the fit on, which is the check after `script --set` or `params` (ADR-876). Exit 0 means the report was written, not that all pairs are clear. `--sweep` writes the published joint sweeps to `docs/clearance-sweep.md` (ADR-350). The same rows reach the agent as `inspect scope=clearance` and, summarised, as the `fit` block on every build reply (§4). |
| `cadex inventory` | Write `docs/inventory.md`: one row per placed component with the output it places, its catalog family and part number, its appearance role (ADR-413) and solved pose; a declared palette below (ADR-236). Reads the pinned accepted attempt — no rebuild. |
| `cadex link --from DIR` | Bring a part in from another project, or refresh one. |
| `cadex asset --put FILE` | Copy a file into the project store — a trained `.cxpolicy`, its provenance, a mesh, a `.cxpart`. With no `--put`, list the store. |
| `cadex train --out DIR` | Rebuild, export the training bundle into `--out`, run the offboard trainer on it from its venv, and report the receipt. `--put` stores the policy; `--remote` runs the trainer on the box through `training/remote_train.sh`; `--dry-run` reports the plan and trains nothing. |
| `cadex smoke --out DIR` | Simulate retained accepted artifacts with zero action or held position actuators and check finite state, exact component overlaps, floor support and closed loops (ADR-352, "Smoke" below). |
| `cadex evaluate` | Hold the accepted policy against its task's success spec (ADR-456): one rollout per frozen seed, a verdict per seed and per predicate, a film, and on a pass the heroes and the shove video (ADR-457, ADR-459, ADR-570, ADR-571; "Evaluate" below). No rebuild, no trainer. |
| `cadex walk --out DIR` | The lifecycle walk as one command: an optional change (`--set`), train and store (locally or `--remote`), re-declare the policy in the script, verify and roll out, review. Every leg is a child `cadex` command bounded by `--leg-timeout` (default 3600 s); `review.json` lands in `--out`. |
| `cadex review --host ADDR --port N` | Serve **this one project's** dashboard, read-only (ADR-286, ADR-537): GET and HEAD only, no engine, nothing written. Default `127.0.0.1:8765`. The page is `docs/DASHBOARD.md`; what the server serves is "The review dashboard" below. |
| `cadex style [NAME \| --clear]` | The project's design style (ADR-560): one named, optional set of guidance rules that `cadex guidance --project` prints after the base. NAME must be a `Mod/cadex/CadexAgentStyle.<NAME>.md` the engine carries; `--clear` returns to the base alone. Stored in `agent.json`. The envelope's `style` is `chosen`, `available` and `about` (each style's one sentence, ADR-625). No engine, no row, no commit. |
| `cadex budgets [--set NAME=VALUE ...]` | The project's engine budgets (ADR-517): `timeout_seconds` (at most 3600) and `memory_limit_mb` (at most 131072), stored in `agent.json` and sent as `open_project`'s `budgets` by every later run; the engine fills an unset one from its default (300 s and 6144 MB unless its preferences say otherwise). `--set NAME=0` unsets one. `GET /api/project` carries them read-only. No engine, no row, no commit. |
| `cadex revision list\|reject\|restore\|backfill [SELECTOR]` | Going back through the revisions (ADR-506). `list`: the stored trail (`script_history/`, ADR-045), oldest first, with values, digest and `models` (whether each ordinal's model is `retained` in `review/revisions/`, ADR-546). `reject` puts back the revision accepted before the current one; `restore SELECTOR` (an ordinal or a revision prefix) puts back that one, through `write_script` with `replace` and then its recorded values — each a run with its row and commit. The envelope's `revisions` says `target`, `from`, `accepted`, whether that is `exact`ly the target, and `same_geometry` (a parameter the target left at its default cannot be unset once stored). `backfill` (ADR-548) keeps a model for every stored revision that has none, rebuilding each in a scratch project and keeping it only when the engine lands on exactly its revision id; a miss is a `failed` row with the reason. No row, no commit for `list` and `backfill`. |
| `cadex app [--projects DIR] [--host ADDR] [--port N]` | Serve the dashboard over a **directory of projects** (ADR-502): `/` is a home page of project cards (ADR-605) — every subdirectory holding a `script.json`, `review/activity.jsonl`, `.cadex-cli.lock` or `agent.json`, so a session is listed from its first tool call (ADR-575), re-read on each request — and each project's review page is under `/p/<name>/`. Every URL is relative to the page (ADR-551), so it works mounted under a proxy's path prefix. **A bare `cadex` is this command**, and so is `pixi run app`. The directory is `--projects`, then `CADEX_PROJECTS`, then `~/cadex-projects`, created if absent. Default `127.0.0.1:8765`; read-only (ADR-537). |

Flags, valid on either side of the subcommand:

| Flag | Meaning |
|---|---|
| `--project DIR` | Project root; **created if absent** by a command that runs the engine. Default `./.cadex`, or `$CADEX_PROJECT`. `review`, `budgets`, `style` and `revision` need one that exists. |
| `--out DIR` | Write exported files here. Omit and nothing is written. |
| `--format step,stl` | Any of `step`, `stl`, `brep`. Default `step,stl`. |
| `--offset-mm N` | `section`: where along the plane normal to cut. Omit it to derive the offset (ADR-275). |
| `--sweep` | `clearance`: write the published joint sweeps to `docs/clearance-sweep.md` (ADR-350). |
| `--min-clearance-mm N` | `clearance`: flag distances strictly below N (default 0.1 mm). |
| `--max-common-volume-mm3 N` | `clearance` and `smoke`: flag volumes strictly above N (default 0.000001 mm³). Thresholds must be finite and nonnegative; changing them does not rebuild. |
| `--assembly OUTPUT` | `inventory` and `clearance`: the assembly output. A project publishes at most one, so this is a check. |
| `--seconds S`, `--mode hold\|zero`, `--penetration-mm N`, `--rest-speed-mm-s N`, `--max-tilt-degrees N`, `--fps N`, `--timeout S`, `--model NAME`, `--task NAME` | `smoke` ("Smoke" below). |
| `--policy NAME`, `--task NAME`, `--weights FILE`, `--timeout S`, `--film SEEDS`, `--no-video`, `--detail-start S`, `--detail-step S`, `--film-only` | `evaluate` ("Evaluate" below). |
| `--rebuild` | `export` only: restore and rebuild the accepted script on this engine before writing, re-proving its digest (ADR-848). The rebuild asks for standard display, as `export`'s, `train`'s and `link`'s rebuilds all do, so the attempt it pins keeps triangles for `look`, renders and films (ADR-851). |
| `--blueprints` | `export` only: also copy the stored blueprint sheets into `--out`, store filenames kept (ADR-150, ADR-157). |
| `--engine ROOT` | A staged engine payload. Default: `$CADEX_ENGINE_ROOT`, then the dev tree (§6). |
| `--engine-timeout S`, `--engine-memory MB` | The engine budgets for this call only (ADR-517), over the stored ones; `walk` hands them to every leg. Every engine run's envelope carries `budgets`: `in_force`, `stored`, and each one's `source` (`override`, `project` or `engine`). |
| `--json` | Emit the machine-readable envelope on stdout (§3). |
| `--version` | Print `cadex <VERSION>` and exit (ADR-673). |
| `--wait` | Block for the project lock instead of failing. |

`script --set` also takes `--replace`, which says you mean to drop an output
the accepted revision declares — without it such a script is refused,
because `write_script` replaces the whole script (ADR-045). The refusal
needs only the names the script returns, so it comes before any output is
built (ADR-682). A refused source is kept at `review/script.rejected.py`,
and `script.py` is put back to the accepted revision, with a `script:` note
saying so (ADR-599).

### 2a. Driving a project with your agent: `cadex mcp` (ADR-538)

Register `cadex mcp --project DIR` with the agent you already use, once per
project, and talk to the agent; open the dashboard beside it to watch.

```bash
# Claude Code
claude mcp add cadex -- /path/to/cadex/cadex mcp --project /path/to/bracket
# Codex (~/.codex/config.toml)
#   [mcp_servers.cadex]
#   command = "/path/to/cadex/cadex"
#   args = ["mcp", "--project", "/path/to/bracket"]
#   tool_timeout_sec = 420
# any other MCP client: a stdio server, that command and those arguments
./cadex app            # the read-only dashboard, http://127.0.0.1:8765/
```

The server answers `initialize` with a **brief** as its `instructions`, a
paragraph under 2,000 characters that names the project, tells the agent to
run `<repo>/cadex guidance --project <project>` in its shell before its
first tool call, and says which style the project chose. The whole guidance
is far longer than Claude Code's default 2,048-character cap on a server's
instructions, so it travels through the agent's shell. `tools/list`
answers with the tool surface — `describe_api`, `write_script`,
`edit_script`, `set_params`, `rebuild`, `inspect`, `link_part`,
`put_asset`, `look`, `draw_blueprint`, `train_start`, `train_status`,
`train_stop`, `evaluate` — and neither opens an engine.

The first tool call takes the project lock (waiting for a `cadex` command
that holds it) and opens the engine; the server lets both go after `--idle`
quiet seconds and opens them again on the next call. **The engine opens
without the restore pass** (ADR-689): every tool reads the stored accepted
attempt or runs the script afresh. Only an `inspect` of `scope=document` or
`scope=object`, which read cadexd's live document, opens with the restore.
So the agent's own `cadex render`, `export`, `section`, `train` or `walk`
on the same project runs between bursts of tool calls, with `--wait`.

The CLI's `params`, `render`, `hero` sheet, `section`, `inventory`, `link`,
`asset` and `train` sessions also open with `restore: false` (ADR-875).
Store reads need no live document; edits and training run their own build.
`render` and `section` use retained accepted tessellation, with one explicit
rebuild if it cannot be read. An explicit `export --rebuild` still proves
restart determinism.

The transport is JSON-RPC 2.0, one object per line. `initialize` echoes
the client's `protocolVersion` when it is one of
`mcp.SUPPORTED_PROTOCOL_VERSIONS` (2024-11-05, 2025-03-26, 2025-06-18) and
answers the newest otherwise; `serverInfo.version` is `VERSION` (ADR-673).
An unparsable line is answered `-32700`, a batch or bare value `-32600`,
and a method that raises `-32603`, so one bad message never ends the
server. A `tools/call` naming an unpublished tool is refused before any
engine opens.

**The client's tool timeout must outlast the engine budget** (ADR-630). A
build reply arrives after the worker run (bounded by `timeout_seconds`,
300 s by default), the publication and the bridge's fit, inventory and
anatomy reads. Give the client at least the engine budget plus a minute,
e.g. `tool_timeout_sec = 420`, and raise both together.

Each tool call prints one line on stderr, which an MCP client keeps in its
server log. When the server lets the engine go after a session that
accepted a build, it lands one `PROGRESS.md` row (`mcp: write_script,
set_params ×2`, with the accepted revision and digest) and one commit in the
project's own repository. A session that only read lands nothing. Stdout
carries nothing but the protocol.

### Linking, assets and training

`link` takes `--from DIR` (the other project's root, never changed),
`--output NAME` (omit it and the refusal lists what it declares) and
`--name FILE` (default `<output>.cxpart`). **Refresh is the same command**
(ADR-138): the op overwrites the stored container. A run that finds the
other project moved rebuilds this one behind it, as one accepted revision;
a run that finds nothing moved rebuilds nothing. A rebuild that then fails
against the new shape exits `3`.

`asset` takes `--put FILE`, repeatable, and `--name NAME` for a single
`--put` (same suffix). It is the door for a trained policy (ADR-190): the
envelope's `assets` rows carry each stored file's `sha256`, the digest
`assembly.policy(weights=…, sha256=…)` requires. **It never rebuilds**: a
stored file changes nothing until a script names it. A file type the store
does not hold is the engine's refusal (exit `3`); a missing `--put` is a
usage error. With no `--put` it lists the store.

`train` is the training leg as one command (ADR-191): it rebuilds, exports
the accepted outputs into `--out` (required), finds the one training task
(or `--task NAME`'s), runs `training/cadex_train.py` on it under the
training venv, and puts the trainer's receipt in the envelope as
`training`. Training stays offboard (ADR-084): the trainer is a subprocess,
and the project lock is held for the rebuild and, with `--put`, the store
write, not between. Its flags are carried by name: `--iterations N` (200),
`--envs N` (256 — drop it hard on CPU, `training/SETUP.md`), `--seed N`
(an unsigned 32-bit integer, default 0; the rollout seed stays in the
script), `--label TEXT`, `--init-from POLICY` (warm start, same task
digest), `--init-from-parent-task BUNDLE` with `--init-from-task-change
REASON` (warm start across a task change, ADR-161; the three travel
together), `--name NAME.cxpolicy` (default `<task>.cxpolicy`), `--timeout
SECONDS` (0 is no limit), `--checkpoint-every N` (ADR-544, §4),
`--stop-on-collapse` (ADR-410) and `--allow-ungrounded` (ADR-408, §4). The
trainer's other flags — the PPO hyperparameters, `--critic-warmup`,
`--init-from-base`, `--family`, `--minibatches`, `--max-grad-norm`,
`--reward-floor`, `--teacher` and the rest — are not `cadex train` flags;
run `training/cadex_train.py` directly for those, or use `train_start`
(§4), which passes some of them. The interpreter is `--trainer-python
PATH`, then `$CADEX_TRAIN_PYTHON`, then `<repo>/.venv/bin/python`, then
`~/cadex-train-venv/bin/python`; **nothing creates a venv**, and none
found is exit 1 with the places tried. `--put` stores the policy and
reports its `assets` row. **It never rebuilds after training**: the policy
is real when a script names it. A revision that exports no training task is
exit 3 before the trainer runs; a trainer that exits non-zero or hits
`--timeout` is exit 1 with its stderr on ours.

The training slot (§5) is one per machine: `cadex train` holds it while its
local trainer runs.

**Iterating — change the mechanism or the task, retrain, compare** uses a
**numeric switch parameter** in front of the policy (ADR-192), because a
sweep that moves the task digest is refused while a policy is declared
against that task:

```python
p = params(..., policy_on=num(1.0, min=0.0, max=1.0, step=1.0))
...
if p.policy_on >= 0.5:
    policy = assembly.policy(task, weights="walk.cxpolicy", sha256="…")
    run = assembly.rollout(policy, frames_per_second=50, seed=7)
    result["policy"] = policy
    result["run"] = run
```

```bash
./cadex params --set policy_on=0 --set shove_n=0.20 --out ./sweep   # accepted: the bundle
./cadex train --out ./run2 --put --name walk2.cxpolicy \
    --init-from ./run1/walk.cxpolicy --init-from-parent-task ./run1/walk-task.json \
    --init-from-task-change "shove band 0.12 N -> 0.20 N"          # warm, across the change
# edit the script: weights="walk2.cxpolicy", sha256=<the envelope's>
./cadex script --set ./script.py
./cadex params --set policy_on=1 --out ./run2                       # verify + rollout
```

`set_params` never refuses a dropped output, so blanking the switch is an
ordinary accepted revision that exports the task at its new digest. A
stored parameter value outlives a script write, which is why the last step
is a `params` call. `cadex walk` is these four commands and the edit as one.

### The walk (ADR-199)

**Build the engine before you walk.** The walk compares the installed
engine's top-level Python files with `src/Mod/cadex` and reports `match`,
`different` or `unavailable` as `walk.engine_source_comparison` and on
stderr (ADR-251), but never rebuilds or refuses: an unbuilt change runs the
*previous* runtime. For a toy CPU walk, set `JAX_PLATFORMS=cpu`
([training setup §b](../training/SETUP.md#b-cpu-only)).

`cadex walk --out DIR` runs these legs, each a **child `cadex` command**
that lands its own row and commit:

1. Nothing to design: the walk starts from the project as the agent left
   it, whose script declares its task.
2. With `--set NAME=VALUE`: `cadex params --set policy_on=0 --set …
   --out DIR/sweep`. Do not pass `--set policy_on=…`: the walk owns it.
3. `cadex train --out DIR/train --put` with `--iterations`, `--envs`,
   `--seed`, `--label`, `--name`, `--task`, `--timeout`,
   `--trainer-python`, `--checkpoint-every`, `--allow-ungrounded`, the
   warm-start triple, and `--remote` / `--allow-cpu`. The walk always adds
   `--stop-on-collapse`.
4. **The digest edit**: the walk reads the script, rewrites the two string
   literals of its one `assembly.policy(task, weights="…", sha256="…")`
   call to the stored policy's name and sha256, writes `DIR/script.py` and
   lands it with `cadex script --set`. A script is refused at exit 3, with
   the convention named, when it has no `policy_on=num(...)` parameter, not
   exactly one `assembly.policy` call, or that call without `weights=` and
   `sha256=` as inline string literals (`weights=POLICY_WEIGHTS` is
   refused). The guidance teaches both.
5. `cadex params --set policy_on=1 --out DIR/rollout` — verify and roll out.
6. The review, as `walk.review` in the envelope and **`DIR/review.json`**
   (`cadex-walk-review-v1`): the trace's `policy` block (`total_reward`,
   per-term `reward_totals`, the policy's sha256), the trainer's receipt
   figures, the parameters, and the legs with exit codes and timings, paths
   relative to `DIR`. Run the walk under the project (`--out
   <project>/runs/<name>`) and its commit includes `review.json`,
   `docs/inventory.md` and `docs/clearance.md`.

`review.json` carries these blocks, each from one engine session that
rebuilds standard display once and snapshots it:

- `gait` (ADR-409, ADR-433): for one free-floating body, its tilt
  (tipped at 45°), unwrapped heading (turned at 90°), a termination, and
  the median mean episode length over the trainer's last 50 iterations
  against the horizon (under 90% is "ended early"). A finding makes
  `walked` false; the walk still succeeds. Travel and speed are reported,
  never judged. For a task with a success spec, `behaviour` says the
  authority is `cadex evaluate` and the gait reading is advisory.
- `inventory`: `available`, `component_count`, `catalogued_count` and the
  project-relative path to the latest `docs/inventory.md`.
- `clearance` (ADR-238): the accepted pairs at the initial solved pose, the
  thresholds (0.1 mm, 1e-6 mm³), offending and unknown pairs with labels,
  and `bounds_check` (ADR-248) — the same pairs re-read against the render
  snapshot's world bounds, `pass`, `fail` or `unavailable`: agreement
  between two paths, not validation of either. **Clearance reports; it
  does not gate.** The walk's `PROGRESS.md` row carries the offending count
  with its change against the last walk row that had one (ADR-271).
- `motion` (ADR-259): per component, `position_range_mm`,
  `max_displacement_mm` and `max_rotation_deg` (`2·acos(|q₀·q|)`) against
  the **first solved frame** (frame 0 of an assembly trace is the input
  pose and is excluded; `frames_counted`, `frames_excluded`). Translation
  and rotation are both reported and **never ranked against each other**:
  `examples/lifecycle/hinged-arm` travels 0.0000 mm and rotates 178.8°,
  `linear-carriage` travels 4739 mm and rotates 0°. The row reads `motion
  travel_mm N on <component>, travel_deg N on <component> over N solved
  frame(s)`, each with its change against the last walk that carried it
  (ADR-260). A delta is not a verdict.
- `documentation` (ADR-256): the note subjects the trained MJCF declares
  (`<actuator>` asks for `docs/actuators.md`, `<sensor>` for
  `docs/sensors.md`), the project's notes and the `missing` ones. A
  missing note is a finding, never a failure, and the CLI never writes it.
- `render`: the four SVG views and the hero under
  `review/render/<accepted-revision>/`; a render that fails is
  `available: false` with the reason and the rest of the review stands.
- `section` (ADR-267, ADR-270, ADR-273, ADR-277): a world XZ cut whose
  offset is derived from the snapshot's own bounds — each object's centre
  on the cut axis plus the whole geometry's, each with two quarter-span
  siblings; every candidate is cut and the one that cuts the most objects
  wins, and no object's own centre plane is ever dropped. It carries
  `offset_mm`, `offset_source: derived`, `offset_candidates_mm`,
  `objects_cut` and `missed_objects` (each uncut object's status and
  whether it `moved` in the rollout, joined by exact component identity).

Rendering, section, revision mismatch and inspection errors fail the walk;
retained files from an older run are never reported as current. A failed
leg stops the walk with the leg's name and error, and the exit is the leg's
for a usage error or refusal, `1` otherwise. A failed walk adds no review
row.

**Every leg is bounded in wall clock** (ADR-261). `--leg-timeout SECONDS`
(default 3600, `0` for no limit) stops a leg that runs longer: it reports
exit **124** and the walk exits `1`. The stop is a **subtree kill** — the
leg runs in its own session, gets `SIGTERM`, then `SIGKILL` to the group
five seconds later — because the thing that hangs is usually the trainer
under the child. `SIGINT` and `SIGTERM` to the walk are relayed to the
running leg. `--timeout` is the trainer's own limit, not the walk's; the
train leg gets `max(--leg-timeout, --timeout + 300 s)`.

**Retry after failed retraining.** The accepted sweep stays applied with
`policy_on=0`; earlier policies, runs and rows survive, and partial trainer
output is not stored. Use a fresh `--out` and policy `--name`, warm-start
from the last good policy and its parent task, and declare the task change:

```bash
JAX_PLATFORMS=cpu ./cadex --project "$P" walk --out "$P/runs/walk-recovered" \
  --name job3.cxpolicy --init-from "$P/runs/walk-2/train/job2.cxpolicy" \
  --init-from-parent-task "$P/runs/walk-2/train/job-task.json" \
  --init-from-task-change "lift weight increased from 0.0002 to retained 0.0003" \
  --iterations 1 --envs 4 --timeout 600 --json
```

`examples/lifecycle/` holds the hinged arm and a vertical linear carriage
with a slide joint and a force motor (ADR-203), with reproduction commands
and baseline numbers; they prove coverage, not a ranking. Dated walk
rehearsals are in [`history/CLI-EVIDENCE.md`](history/CLI-EVIDENCE.md).

**MJX lacks some MuJoCo geom pairs** — box/cylinder, cylinder/mesh,
box/ellipsoid and ellipsoid/mesh. `assembly.task` refuses a task whose
exported model has such a candidate collision pair, naming the geoms
(ADR-281); a cylinder is still legal on a model nobody trains. A trainer
that fails anyway is named in the envelope (ADR-280).

**Artifacts** (paths relative to the project, `DIR = runs/<name>`; the same
in local and remote training, and in the scaffold's `## Training` section):

| Leg | Artifact |
|---|---|
| Design / assembly | `script.py`, `ARCHITECTURE.md`, `DECISIONS.md`, `docs/<subject>.md` |
| MJCF / task / training | `runs/<name>/train/` (model, task bundle, returned policy) |
| Store / declare | `assets/<name>.cxpolicy`, `runs/<name>/script.py` |
| Verify / rollout | `runs/<name>/rollout/` (including the simulation trace) |
| Review | `docs/inventory.md`, `docs/clearance.md`, `runs/<name>/review.json`, `review/render/<accepted-revision>/{front,top,right,iso}.svg`, `hero.png` and `summary.json`, `review/section/<accepted-revision>/XZ-<derived-offset>/{section.svg,summary.json}`, `PROGRESS.md` (remote rows marked `(remote)`) |
| Record | `runs/<name>/run.json` (below) and `runs/<name>/project-docs/` |

### Training on a remote machine (ADR-200)

`cadex train --remote` and `cadex walk --remote` run the train leg through
`training/remote_train.sh train` (ADR-089, `training/SETUP.md` §d) and
nothing else changes: the bundle is exported into `DIR/train`, the script
copies it to the box named by `training/.remote.env`, runs the box's trainer
with **the same flags after `--`**, and copies the policy back to the path
the local trainer would have written. The CLI **verifies the returned file
hashes to the receipt's sha256**, records the box's path under
`training.trainer_out`, and the rest of the walk cannot tell where the
trainer ran.

- **Plan it first** (ADR-255): `cadex train --remote --dry-run` rebuilds,
  exports, and reports `training_plan` — the files (`bundle`, `model`,
  `policy`, `stored_asset`) and the ordered `steps` (`export → train →
  verify → store`, with `copy-out` and `copy-back` around the trainer
  remotely), `executed: false`. It reaches no box; `training/remote_train.sh
  check` is the reachability test. An unreachable box is the script's
  `FAIL:` line in `error` (exit 1).
- **A run the box reports as `device: cpu` fails** unless `--allow-cpu`
  (which needs `--remote`). `--trainer-python` with `--remote` is a usage
  error; the box's venv is `CADEX_TRAIN_VENV`.
- **A warm start travels** (ADR-268): the dispatcher carries
  `--init-from`'s policy and `--init-from-parent-task`'s bundle into a
  `warm/` directory and re-points the flags, refusing a missing warm file,
  the joined `--init-from=PATH` form, or two warm files with one basename.
- **Detached** (ADR-278): `cadex train --remote --detach` returns exit 0
  with `training.state: "pending"`, the dispatcher's `run_id`, `target`,
  `remote_dir`, `pid` and `policy_name`, also written to
  `--out/training-receipt.json`. Nothing is verified, stored or declared.
  Bring it home with `remote_train.sh watch RUN_ID DEST` or `pull RUN_ID
  DEST`. `--detach` needs `--remote` and rejects `--dry-run`.
- **The walk detaches in two halves** (ADR-282): `cadex walk --remote
  --detach` stops at `--out/walk-pending.json` (`cadex-walk-pending-v1`:
  the locator, the bundle and its sha256, the launch seed, the legs run, and
  the two commands that finish the run). After `watch` or `pull`, `cadex
  walk --complete --project P --out DIR` runs `collect` (the returned policy
  through `cadex asset --put`), then `declare`, `rollout` and the review.
  It refuses `--set`, `--remote`, `--allow-cpu` and `--detach`, and refuses
  at `EXIT_REJECTED` a `training-progress.json` not `done`, a policy that
  does not hash to the receipt in `train.log`, a receipt naming another
  task, or a bundle that moved since the launch.
- **`--timeout` and `--leg-timeout` are local**: they end the SSH process,
  not remote training; `remote_train.sh stop` stops the box.

### The run record (ADR-285)

`review.json` carries a walk's numbers; **`run.json`**
(`cadex-run-record-v1`) carries its identities, so a reader with no engine
can tell which model, parameters, task and policy a run belongs to. `cadex
walk` writes it as `running` at the start (and again before the train leg
when the sweep moved the accepted revision), then `ok`, `failed` (with the
leg and its error), `stopped` (Ctrl-C or `SIGTERM`, the signal in `error`;
a `train_stop` lands the same with its reason, ADR-559; exit 1) or
`pending` (a detached train leg). Before training, the walk freezes the
accepted assembled view, parameter values and specs and the project
documents in `training-view.json`, `training-view/*.stl` and
`project-docs/` (ADR-291); `train_start` freezes the same view. If another
design is accepted between that and the train leg, training refuses.
`cadex params` requests standard tessellation as part of acceptance
(ADR-293), so the sweep's model is ready for that snapshot.

It carries `model` (the `accepted_revision` and `digest`, with
`identity_source`: the manifest at walk start, then each leg's envelope;
`not reached` only when nothing spoke), `params` (`values`, and `specs`
read at the accepted revision, with `specs_source`), `task`, `training`
(`requested` flags and the trainer's `receipt`), `policy` (name, sha256,
`asset`), `rollout`, `legs`, `videos`, `artifacts` (run-relative) and
`project_artifacts` (project-relative), and `project_docs` (the project's
documents copied with their sha256s, at most 32 files of 256 KB,
`PROGRESS.md` before this run's row). **Every path is relative**; a file
outside the run and the project is `null`. **`policy.asset` is
`assets/<name>` only when the store held that file with the recorded digest
when the record was written** (ADR-326); the trainer's own copy is
`artifacts.policy`.

**The reader** is `cadex_cli.review_record.read_project_review(root)`: the
accepted identity now, the documents and decision headings, and every run
under `runs/`, oldest first, each reference resolved against the disk. It
**only reads**. Each run carries `relation` (`current`, `historical` or
`unknown`), `outcome` in words, and `problems`: missing references,
snapshot pages whose digest moved, references that **escape their base**
(by `..`, an absolute path or a symlink — reported and never opened), and,
for an `ok` run, a policy only the trainer retained, with the command that
stores it (ADR-327). A `running` record whose `walk.lock` (or the loop's
`supervisor.lock`) nobody holds reads as `failed` with `recorded_status:
"running"` (ADR-559). A run from before records existed is read from its
`review.json` and labelled `unrecorded`.

Each run also carries **`policy_store`** (ADR-326), read on every poll:
`state` is `stored`, `digest mismatch`, `unstored`, `refused` (the locator
escapes the project) or `none`; `retained` is the trainer's copy;
`next_action` and `store_command` are the commands — `cadex asset
--project <project-dir> --put <project-dir>/runs/<run>/train/<name>`, which
names the project twice because `--put` resolves against the working
directory and `--project` defaults to `./.cadex`. Store digests are
verified through a stamp-keyed cache, so a poll never re-hashes an
unchanged file.

**Policy lineage** is `review_record.policy_lineage(root, run)` (ADR-316):
a run's `policy.sha256` matched against the bytes every run keeps under its
own `train/` (files up to 4 MiB). The holder is the `origin` (`final`,
`checkpoint` with its iteration, or `retained`; the earliest wins, the rest
under `also_retained_by`), beside the record's `source_run` and
`source_agrees`, and `playbacks` lists the other runs whose policy it
holds. `GET /api/policy-origin/<run>` serves it. Every run directory and
file it touches is resolved against the **project root** first (ADR-317,
ADR-318): a `runs/<name>` symlinked out of the project is listed as
unreadable, contributes nothing, and its model and mesh routes answer
`available: false` or 404.

**Collision proxies (ADR-333).** Every model manifest carries a `collision`
block parsed from the MJCF the view already retains at its own identity:
each geom in its component's frame (mm, xyzw, MuJoCo's size meaning), inline
mesh assets as vertices and faces, planes and unknown types listed but not
drawn, contact-free geoms counted as `skipped`. The page has no control that
draws them (ADR-533) and a recording never contains them.

**Retention and copying.** The record and the snapshot are small and are
committed with the run; the trace, bundle and checkpoints fall under the
default ignore rules and stay local. Copy a project whole (`cp -R`, `runs/`
and `review/` included) after its writers finish: references are relative,
so the copy reviews as the original did, and anything it omits is listed
under `problems` rather than resolving elsewhere. Then serve the copy on its
own: `./cadex review --project ~/cadex-projects/biped-copy --port 8766`.
Deleting a run directory deletes its history.

### The project is a codebase (ADR-193)

Every project root carries the documents an engineer keeps beside a model,
created by the CLI on the first visit and never overwritten by it:

| File | What it holds | Who writes it |
|---|---|---|
| `ARCHITECTURE.md` | What the project is, what the script declares and why, how it trains (its `## Training` section), where the domain docs are. | the agent or a person |
| `DECISIONS.md` | The project's own ADR log. Newest last. | the agent or a person |
| `PROGRESS.md` | One row per accepted run: time, command, revision, digest, what, numbers. | **the CLI** |
| `docs/<subject>.md` | Longer notes, one file per subject (`docs/actuators.md`, `docs/sensors.md`, …). | the agent or a person |

The agent reads them before it acts and writes everything but
`PROGRESS.md` itself, with its own file tools. `docs/inventory.md` and
`docs/clearance.md` are the CLI's generated reports, not note subjects.
`params`, `script --set`, `export`, `render`, `section`, `clearance`,
`inventory`, `link`, `asset --put`, `train`, `smoke`, `evaluate`, `walk`,
`revision reject|restore` and an MCP session that accepted a build each land
one row, with `total_reward`, `reward_per_step`, wall time and sha256 when
the run produced them. Read-only commands (`script` with no `--set`, the
store listing, `revision list|backfill`, `review`, `app`, `budgets`,
`style`) get no row and no commit.

**The comparison is one recorded row** (ADR-194). A number an earlier row
also carried is written with its change against that row:

```
| … | script | 506bfc86 | 68530963 | script --set switch9.py | total_reward -293.4 (Δ -421.2 vs 2996fb73 at 127.8) |
```

Each metric is compared against the last row that carried it, read back
from `PROGRESS.md` as written. Train and walk rows also record
`training_seed`, `rollout_seed`, an objective identity and the prior
same-kind row's evidence; missing historical evidence reads `unavailable
(legacy row)`. Objective `v1` is SHA-256 over compact, key-sorted JSON of
the exported task's `schema`, `observations`, `reward`, `termination`,
`episode` and `functions` — it identifies the declared objective, not
experimental equivalence; model, actions, seeds, randomisation and
disturbances are excluded (the separate `actions` hash covers action
metadata). Deltas are descriptive, never evidence of better learning.
Rows replace `PROGRESS.md` only after the write succeeds (ADR-264).

**Project history depends on repository ownership** (ADR-194):

- **Fresh root outside another work tree:** the CLI runs `git init` and
  writes default `.gitignore` rules if that file is absent.
- **Existing project-root repository:** used as is; its ignore rules are
  not touched.
- **Nested beneath another repository, without its own `.git`:** documents
  and rows land, nothing is committed, and the envelope says `inside an
  existing git work tree: not initialised, not committed.`

The default ignore rules exclude `script_artifacts/`, frames, renders and
the project-root `review/`, `*.png`, `*.mp4`, locks, `.cxpolicy` files
outside `assets/`, and `*-trace.json` (ADR-199); stored assets, including
policies under `assets/`, stay versioned. To keep a rehearsal local
(ADR-262), append after `!assets/*.cxpolicy`:

```gitignore
/runs/<name>/
/review/
/assets/<name>.cxpolicy
```

`git check-ignore -v --no-index PATH` names the winning rule. Ignores do not
untrack files already in history; the CLI never silently untracks.

In a project-root repository every accepted run commits **all working
changes** (`git add -A`) with the row's words as the message; `committed
<sha>.` in `notes` confirms it. A missing `git` or a failed commit does not
fail the run. Opening a project re-stages its accepted attempt, so a
read-only visit leaves `script.json` modified until the next accepted run.

**Neither form of `script` asks for the restore pass** (ADR-272): after
`train --put` overwrites an asset the accepted script declares by sha256,
the stored script no longer re-runs, and `script` / `script --set` are what
repair it. Every other command keeps the restore, except `cadex mcp`
(ADR-689). **`cadex script --set` carries the verdicts** (ADR-689): its
envelope's `verdicts` is the brief of §4, printed as `fit`, `sweep`,
`panels`, `mount` and `welds` lines.

### Smoke (ADR-352)

```bash
./cadex smoke --project ./mechanism --out ./mechanism/smoke1 --seconds 2 --json
```

`smoke` copies the retained accepted MJCF, optional task and detached BREP
artifacts into `--out` and holds the project lock through measurement. It
never runs `script.py` or changes accepted state; the receipt pins the
accepted revision and digest. The child is stock MuJoCo, no policy: `hold`
holds each position actuator at its solved joint coordinate (others get
zero), `zero` sends zero everywhere. It checks:

- Finite position, velocity, acceleration, actuator state and controls at
  every solver step, MuJoCo warning counters included.
- Exact BREP common volume for every component pair at every sampled pose,
  limit `--max-common-volume-mm3`. At the first frame, distances and
  volumes must agree with published static clearance to the MJCF's pose
  precision (ADR-584: within 2√3 × 0.01 ≈ 0.035 mm, recorded as
  `initial_pose_tolerance_mm`). A pair whose relative pose is unchanged
  keeps its volume (ADR-582). A bolt threaded into a printed part may share
  up to its thread allowance (ADR-583, `thread_allowance_mm3`); a pair held
  in contact no deeper than `--penetration-mm` may share at most that depth
  times half the common solid's surface (ADR-599, `contact_allowance_mm3`;
  the contacts seen go to `smoke-contacts.json`).
- Floor-proxy penetration no deeper than `--penetration-mm` (0.5), and a
  free base touching the ground at the end (the floor, or a course's
  heightfield, ADR-714), at most `--rest-speed-mm-s` (10) and turned no
  further than `--max-tilt-degrees` (30) from its accepted keyframe
  (ADR-377). In a design with grounded bodies, a free body is a payload
  owed no floor (ADR-599, `checks.support.payloads`).
- The selected task's terminations, without randomisation, disturbances or
  a policy.
- Every loop closure the export wrote (ADR-593) stays within 0.01 mm at
  every step (`checks.closure`, worst first; a failure names
  `suggested_step_s`, ADR-594). With a closure and a position actuator,
  smoke also drives each position actuator through a 2 s sine of 40 % of
  its half-span and measures the closures through it (ADR-599,
  `while_driven`).

Sampling defaults to 50 Hz with the first and last poses; the trace budget
is 15,000 intervals; `--timeout` caps the whole child at 300 s. It is a
sampled check, not continuous collision detection. `smoke-dynamics.json`,
`smoke-trace.json` and `smoke-geometry.json` are the parts; `smoke.json`
combines them. **Exit zero means a complete measurement, not a passing
design**: read `smoke.verdict`. Missing artifacts, model/task disagreement
or a timeout fail the command.

### Evaluate (ADR-457, ADR-459)

```bash
./cadex evaluate --project ./robot --json
./cadex evaluate --project ./robot --film 1101,1105,1110 --detail-start 5 --detail-step 0.04
./cadex evaluate --project ./robot --film-only --film all --no-video
```

A task says what its behaviour must measurably be with `assembly.success`
(`docs/XSCRIPT.md`, ADR-456): predicates on behaviour metrics, frozen
evaluation seeds and the episode's conditions. `cadex evaluate` holds the
accepted policy to it; it takes no behaviour's name.

**What it reads.** The retained accepted attempt, as `smoke` does, under
the project lock. The policy is the one `assembly.policy` declared and the
engine verified; every file is checked against the store's digest, and the
weights against the receipt. `--policy NAME` or `--task NAME` picks among
several. No declared policy, or no success spec, is exit 3.

**A candidate** (ADR-846): `--weights FILE --task NAME --out DIR` holds a
`.cxpolicy` that no script declares -- one trained on a concept or a
training model, on the export's task re-laid by `training/cadex_relay.py` --
to that task's success spec on the accepted model, by the same runner. Its
report's `policy_output` is empty and `weights` is the file's path; it needs
`--out` (the dashboard lists declared policies only) and takes no
`--policy`. Nothing verified it, so it judges a policy and declares none.

**What it runs.** `cli/cadex_cli/evaluate_runner.py` under the engine's
interpreter, calling `CadexDynamics.evaluate_success`: per seed, one
rollout under the spec's horizon, randomisation, reset variation,
disturbances (ADR-458) and goals (ADR-462), one frame per control step,
read by `CadexEvaluation` (ADR-455), the model compiled afresh per seed.
The policy plays under the command filter its `.cxpolicy` header records
(ADR-558). `--timeout` bounds the child (default 1800 s, at most 7200). No
JAX, MJX or trainer.

**What it writes**, into `evaluations/<revision>-<policy>/` (the first
twelve characters of each; `--out DIR` elsewhere, which the dashboard does
not list):

- `evaluation.json` (`cadex-evaluation-v1`), written last and atomically:
  `verdict` (`pass` only when **every seed passes every predicate**), the
  identities, the `spec`, one row per seed (`pass`, `failing`, every
  predicate's value and bounds, `metrics`, `detail`, `episode`, `reward` by
  term — reported, deciding nothing — `drawn`, and `trace`), and a
  `summary` (tallies, termination causes, min/median/max of every metric).
- `seed-<n>-trace.json` per seed (`cadex-assembly-simulation-trace-v1`).
- the film, and on a pass the heroes and the shove video (below).

A seed whose episode raised a solver warning is **void** and has not
passed. A model whose contact is held off its geometry — a geom `margin` or
`gap`, or a model-wide `o_margin` — voids every seed, with the geoms listed
in `contact_offsets` (ADR-470). An evaluation seed that is the policy's
training seed is refused, and so is a model the task bundle did not record.

**Exit zero means a complete measurement, not a passing policy**: read
`evaluation.verdict`. The envelope's `evaluation` carries the verdict,
digests, summary, `report`, `film`, `heroes` and `shove`; the `PROGRESS.md`
row names the verdict and failing predicates.

**The film** (ADR-459), drawn by `cli/cadex_cli/film.py` from the retained
traces and tessellation with the engine's studio renderer on the CPU, on
the dark prototype floor (ADR-444):

- `seed-<n>-overview.png` and `seed-<n>-detail.png`, twelve 256 px frames
  each (1036×776) with the simulation time. The overview spans the
  episode in the hero view in one window; the detail is `--detail-step`
  apart from `--detail-start` (default the first disturbance, or mid-
  episode; 0.2 s apart), 12° above the floor, **side-on, following the
  base** (ADR-460).
- `seed-<n>-rollout.webm`, the first filmed seed at ten frames a second,
  decoded back before it is kept; FFmpeg from `PATH` or the pixi env.
- A point goal (ADR-462) is drawn as a cyan ring at the target in force in
  each frame (ADR-463).
- `--film auto` (default) films the first failing seed, or the first seed
  of a pass; `all`, `none` or a list. The floor is the model's collision
  plane; materials are the design's roles.

The `film` block (`cadex-evaluation-film-v1`) records `state` (`ready`,
`failed`, `skipped`), the renderer, and per seed each file's sha256, frame
times and target. A film that cannot be drawn leaves the measurement and
exits 1. `--film-only` draws from the evaluation on disk and refuses one of
another revision or policy.

**The heroes** (ADR-570): on a pass, `hero.png` (the studio hero) and
`print-bed.png` (every printed part laid flat on 256 mm beds, numbered,
with the parts list and purchased hardware, ADR-569), drawn from the
retained geometry, in a `heroes` block (`cadex-heroes-v1`). A failed
evaluation presents nothing and removes an earlier pass's heroes.

**The shove video** (ADR-571): on a pass, one more episode — the first
spec seed, with each of the task's non-sustained disturbances turned into
three pushes drawn in order from its own window, range and direction (at
most eight disturbances) — filmed by `cli/cadex_cli/shoves.py` as
`shove.webm`, each push marked by an arrow as it lands and `recovered in
<s>` once the design settles (tilt ≤ 10°, speed ≤ one COM height a second,
held 1 s). A design that falls is filmed falling. The `shove` block
(`cadex-shove-film-v1`) carries `pushes`, `outcome`, `caption` and the
spec predicates the shoved episode did not hold (for reading only).

The evaluation directory's `.gitignore` keeps the film, heroes and videos
out of the project's history; `evaluation.json` is committed with the row.

### Section and render

`./cadex section --project ./robot --plane XY --offset-mm 8 --json` writes
`review/section/<accepted-revision>/XY-8/section.svg` and `summary.json`.
XY means z=offset, XZ y=offset, YZ x=offset, in world millimetres. The JSON
carries the accepted revision and digest, solved placements, closed planar
contours, approximation, limits, `offset_source` (`explicit`, or `derived`
as the walk derives it) and timings. It is a cut of the accepted standard
tessellation, filled even-odd; endpoints snap to 1e-6 mm. `status: ok` means
closed contours, `empty` no triangles on the plane, `unsupported`
(`available: false`) a degenerate contact or an open, branched or collapsed
cut — move the plane slightly. All three are successful reports (exit 0);
rebuild, revision, budget and write failures are nonzero.

`./cadex render --project ./robot --json` writes `review/render/front.svg`,
`top.svg`, `right.svg`, `iso.svg`, `hero.png`, `sheet.png` and
`summary.json`, overwritten on success. Front looks along +Y with Z up; top
along -Z with Y up; right along -X; iso from (1,-1,1); the hero is 20°
above the floor and 35° round from the front towards +X
(`docs/DESIGN-LANGUAGE.md` §7). Unposed source outputs and the world
geometry the published fit names (a floor) are left out. The summary
carries identity, bounds, cameras, coverage, limits, timings,
`environment`, `appearance` (each object's role, colour, `source` and
`finish` — `printed`, `purchased`, `hardware` or `board` — from the
catalog row, ADR-603), `palette`, `hero` and `proxies`; a walk's review
carries it whole as `render`.

**Every image is a studio render (ADR-412)**, pure Python on the CPU: a
depth pass at 2×2 subsamples per pixel, key, fill and rim light with a
Blinn highlight per role finish, normals smoothed except over a 40° crease,
on the dashboard's **dark prototype mat** (ADR-444, `CadexStudio.PALETTE`,
ADR-445; 1 m grid at every framing, ADR-604) with a measured contact
shadow. **Materials come from roles**: a declared appearance role (`shell`,
`mechanism`, `accent`, ADR-413) wins, in the declared palette; otherwise
purchased parts are `mechanism` graphite `#2F3237` and printed ones `shell`
bone `#E9E6DF`. Limits are 4,096 display entries, 32 MiB of input, 300,000
vertices per source, 4,000,000 placed vertices, 2,000,000 placed triangles
read and 400,000 drawn — above which vertices are clustered on a grid sized
from the model's extent, recorded as `decimation` (ADR-410, ADR-439) — and
20 million pixel visits per 512 px view, scaled by area. Missing poses,
malformed buffers and empty geometry fail explicitly.

**The design-language proxies** (ADR-414, ADR-415, `docs/probes/ot10/README.md`):
`hardware_silhouette_share` (P1, reported with no bar since ADR-624) and
`material_count` (P3, with its `bar` and `meets`), measured on the hero at
512 px; `sharp_outside_edge_share` (P2), the sharp convex share of printed
components' solid edge length from the inventory's
`source_facts.sharp_edges`, world geometry left out (ADR-424), `null` with a
reason when a printed part lacks the fact. `look` reports all three under
`measures`.

**The concept sheet** (ADR-430): `sheet.png`, 1536×1024
(`CadexStudio.compose`, ADR-445) — the hero on the left; on the right the
project's name, revision, key numbers, a swatch per role, `front`, `right`
and `top` as line drawings and the three proxies. Lettering is Noto Sans
Regular (SIL OFL 1.1, ADR-568), rasterised by the module. `numbers` are
`name`, `mass_kg` (the accepted MJCF's inertials, environment left out),
`servo_count` (inventory family `servo`) and `size_mm`, each with its
source; an unreadable number prints `N/A` and is never estimated.

### The review dashboard (ADR-286, ADR-301)

```bash
./cadex review --project ~/cadex-projects/biped --host "$(tailscale ip -4)" --port 8765
# review: serving biped at http://100.x.y.z:8765/ (read-only; Ctrl-C to stop)
```

**The page — its screen, editors, theme and type — is
[`docs/DASHBOARD.md`](DASHBOARD.md); it writes nothing (ADR-537).** This
section is what the server reads and serves.

One project per server (`cadex app` serves many). `--host` defaults to
`127.0.0.1`; give it a Tailscale or LAN address, or put `tailscale serve`
in front (`docs/DASHBOARD.md` §22). `--port 0` takes a free port, and the
URL is printed on stderr once the socket is bound. The server holds no
state: every request reads the manifest, the records and the retained files
as they stand, so a walk that lands shows up on the page's next poll (two
seconds), and stopping the server changes nothing about the project.

New visits open the current run (ADR-299): the newest running or pending
record with fresh telemetry, otherwise the latest recorded attempt; with no
runs, the accepted view. `review_server.default_run(review)` is that rule.

**Telemetry** (ADR-287) is read from each run's `runs/<name>/train/progress.json`,
else the newest `progress.json` one or two levels below the run (a seed's or
a stage's seed's directory, ADR-835, ADR-837). It carries the trainer's
`driver` and `model` (`tier`, `sha256`, `cad_sha256`, `path`, and in the
detail form `bodies`, each body's CAD bodies; ADR-837), or none from a
trainer older than that.
`GET /api/project` carries every run's telemetry as a bounded **summary**
(state, reason, latest metrics, sample counts, checkpoint counts, `eta_s`,
`wall_time_s`, `best_iteration`, `best_reward_per_step`, `warning`;
ADR-321, ADR-542) and reads no checkpoint bytes; `GET /api/run/<name>`
carries one run's histories and its digest-verified checkpoints. A
starting/training snapshot older than 30 s is stale; `done` and `failed`
do not expire (ADR-288). A playback run's checkpoints resolve in its own
`train/` and then its recorded `source_run`'s, inside the same project
(ADR-309).

**`stage`** in `/api/project` is what the project is doing (ADR-542):
`state` (`evaluating` while an `evaluations/<name>/` without its report is
under 120 s old or the agent's `evaluate` is in flight — the reason never
names the directory, ADR-555; `training`; `stopped`, ADR-559, ADR-574;
`failed` when the newest run failed and nothing was accepted since;
`designing` within 600 s of an accepted revision; else `idle`), `reason`,
`since`, `run`, `runs`, and `training`: that run's telemetry with its
reward, loss, episode-length and action-std histories cut to 128 points
each and the checkpoint `marks` (ADR-606). `stage.panel` (ADR-607) says
whether the project has an agent-authored `status.html` (at most 512 KB, no
symlink). `stage.checkpoints` (ADR-545) is that run's checkpoint rollouts
(the newest 64, oldest first; each `stem`, `tag`, `state`, `iteration`,
`reward_per_step`, `sha256` and, when ready, `duration_s` and `url`), and
`GET /api/checkpoints/<run>` answers the same for any run (ADR-790). Traces
are parsed once per file identity.

`GET /api/films/<run>` (ADR-901) lists the whole episodes something other
than the run's trainer filmed beneath it, as a project's judge writes
`judge-export/best/s3/view/trace.json`: every regular `view/trace.json` whose
`view/` is at most four directories below the run, reached through no
symlink and inside the project, except the closing view the run plays as its
own (`view/` beside its trainer's newest `progress.json`). Each item is
`film` (the run-relative directory holding the `view/`, also its id),
`group` (that directory's parent) and `name` (its last part), in natural
order (`s2` before `s10`); `state` (`ready`, or `failed` with `reason` when
the trace is past the 64 MB read bound or not a trace); `bytes`; `frames`
(its timed frames, counted); `duration_s` and `frames_per_second`; `goto`
and `points` (whether it is a go-to-point episode, ADR-839, and how many
points); `source` (project-relative) and `url`. The first 256 in that
order are listed and `listed_of` counts them all. A listing never parses a
trace: each is read once per file identity, its frames counted in one pass
and its edges parsed, so a warm listing costs a directory walk.
`GET /api/playback/film/<run>/<film>` serves only a film that listing names,
through the same `trace_playback` as a checkpoint, with its `goto`.

`/api/project`'s `revisions` marks each entry `retained` or carries
`retained_reason` (ADR-546). `GET /api/model/revision/<ordinal>` (ADR-547)
is a retained revision's model with `previous`, `changed` (outputs whose
part digest differs) and `compare`; an unretained one is `available: false`
and another revision's geometry is never offered in its place. `GET
/mesh/revision/<sha256>.stl` serves a kept part only while its bytes hash to
it.

`/api/project`'s `presentation` (ADR-430) is read from the render's
`summary.json`: the `revision` it was drawn from and its `relation`, the
`files` offered (`hero`, `sheet`) and the sheet's numbers and palette,
preferring the accepted revision's walk render. `GET
/presentation/{sheet,hero}.png` serve only what it offers. Its
`evaluations` lists every `evaluations/<name>/evaluation.json` as a bounded
summary (verdict, tally, failures, policy and task, `relation`, filmed
seeds, `heroes`, `shove`, a `stamp`); `GET /evaluation/<name>/<file>`
serves only the files that report names.

**Disk use** (ADR-322): `/api/run/<name>` carries `disk`
(`cadex-run-disk-use-v1`) — the regular files under the run directory, each
inode once, no symlink followed, by top-level subdirectory, from `stat`
alone; each recorded reference sized with its status; project-level
references outside the run under `shared_bytes` and `shared_with`, never in
the run's total. One 20,000-entry budget covers it all; past that, `state:
truncated` and the page says **at least**.

**Where each view's model comes from.** The accepted view is the accepted
attempt's own tessellation (`display/*.tess`, matched to outputs by BREP
sha256, ADR-302) placed by its trace's first frame; a staging directory not
under the accepted revision is refused unless the manifest's
`accepted_attempt` pin and the attempt's digest agree (ADR-311). A run is
drawn from its `run.json` and the meshes its rollout exported; before a
rollout, from its retained training view, or the STL parts of its export,
labelled as parts at identity (ADR-290). Historical geometry is never
rebuilt from today's script. Every artifact is labelled `retained`,
`missing`, `not recorded` or `refused: <why>`. Videos are served with byte
ranges and verified through a 256-digest cache keyed on file identity,
serialized per process (ADR-296, ADR-298); a page keeps one poll in flight
(ADR-297). The cold cost is measured in
[`probes/video-history/README.md`](probes/video-history/README.md).

**What it serves is an allowlist, never a path.** Every route names a run
by its directory name, an artifact by its record key, a document by the name
its record lists, a mesh by its output, a video by its index; each is
resolved through the reader's containment check. Anything the records do not
name — `script.json`, a path with `..`, the server's source — is a 404.

**Rollout videos** (ADR-301): `PYTHONPATH=cli pixi run python -m
cadex_cli.video --project P --run RUN` records a run's rollout in the same
locally shipped three.js scene the viewport uses, dark only (ADR-331, style
`cadex-prototype-dark-v1`), with the follow rig (ADR-332,
`docs/DASHBOARD.md` §10) and a timer. It needs headless Chromium
(`CADEX_BROWSER`, PATH, or the Playwright cache) and FFmpeg, no engine.
Python verifies the retained identities and solids (up to 500,000 triangles,
ADR-336), the capture page reports the triangle count it built, which must
match, and the 512×512 VP9 WebM is decoded frame by frame before it is
published. Each video records its style, versions, camera, framing and what
it shows (collision proxies never drawn, ADR-333). The `--style studio`
look and the playback recorder are `docs/DASHBOARD.md`'s.

### The HTTP API (ADR-552)

The dashboard's data is an HTTP API, and this table is its contract: every
`GET /api/...` route a project page answers, and the top-level keys of its
`200` reply. A route is relative to the project page — the root under
`cadex review`, `p/<name>/` under `cadex app` — except `api/projects`, which
is `cadex app`'s own. `<run>`, `<name>`, `<ordinal>` and `<stem>` are one
path segment each. **Always** keys are in every `200` reply; **when they
apply** keys are in some (an unavailable model has no `meshes`, a playback no
`frames`, an unreadable run record few of its own). A `run/<run>` reply is
the run record as `write_run_record` writes it, with the reader's keys added.
A route that names nothing answers `404` with `{"error": "not found", "what":
...}`, and so does any `api/` path not in this table. The server answers GET
and HEAD only (ADR-537).

`ReviewHandler` dispatches from `review_server.API_ROUTES` and nothing else,
and `review_server.API_RESPONSE_KEYS` holds the keys.
`cli/tests/test_http_api.py` fails when this table, those two and the replies
of a fixture biped that reaches every route disagree, in the way
`docs/INTEGRATION.md`'s op table is held to `OP_ARG_SPECS`.

| Route | Answers | Always | When they apply |
|---|---|---|---|
| `GET api/projects` | `cadex app` only: every project under the directory, each with its card (below) | `schema`, `root`, `projects`, `served_at` | |
| `GET api/project` | the page's one poll: accepted identity, runs with telemetry summaries, the stage, revisions, evaluations, exports, sections, drawings, budgets, agent activity, gait references | `schema`, `project`, `accepted`, `docs`, `decisions`, `runs`, `presentation`, `evaluations`, `revisions`, `stage`, `exports`, `sections`, `drawings`, `budgets`, `activity`, `references`, `served_at` | |
| `GET api/run/<run>` | one run's record with full telemetry and disk use | `run`, `status`, `error`, `artifacts`, `project_artifacts`, `videos`, `legs`, `outcome`, `resolved`, `problems`, `relation`, `telemetry`, `disk` | `schema`, `recorded_at`, `mode`, `walk_seconds`, `model`, `params`, `task`, `training`, `policy`, `rollout`, `project_docs`, `policy_store`, `video_render`, `recorded_status` |
| `GET api/policy-origin/<run>` | which run trained the run's policy, and its other playbacks | `schema`, `run`, `policy_sha256`, `origin`, `reason`, `recorded_source_run`, `source_agrees`, `playbacks` | |
| `GET api/evaluation/<name>` | one evaluation report, and what of its film is on disk | `name`, `relation`, `stamp`, `files`, `report` | |
| `GET api/model/accepted` | the accepted attempt's model | `schema`, `view`, `run`, `relation`, `revision`, `digest`, `available`, `reason`, `source`, `placement_source`, `components`, `collision`, `contacts`, `exploded`, `appearance`, `measurements` | `meshes` |
| `GET api/model/revision/<ordinal>` | one retained revision's model, its ghost and changed parts | `view`, `ordinal`, `revision`, `digest`, `available`, `reason`, `components`, `previous`, `changed`, `source` | `compare` |
| `GET api/model/run/<run>` | the model a run retained | `schema`, `view`, `run`, `relation`, `revision`, `digest`, `available`, `reason`, `source`, `placement_source`, `components`, `collision`, `contacts`, `exploded`, `appearance`, `measurements` | `playback`, `meshes`, `tier` |
| `GET api/playback/run/<run>` | the run's rollout trace as playback frames | `available`, `run`, `source` | `reason`, `times_s`, `frames`, `commands`, `channels`, `duration_s`, `frames_per_second`, `joints`, `velocities`, `efforts`, `policy`, `terrain`, `goto` |
| `GET api/playback/checkpoint/<run>/<stem>` | one checkpoint's rollout as playback frames | `available`, `run`, `stem`, `checkpoint`, `source` | `reason`, `times_s`, `frames`, `commands`, `channels`, `duration_s`, `frames_per_second`, `joints`, `velocities`, `efforts`, `policy`, `terrain` |
| `GET api/playback/reference/<task>` | an accepted task's gait reference (ADR-703) as playback frames: its one stride repeated a stride further on each time, for about 4 s | `available`, `task`, `source` | `reason`, `times_s`, `frames`, `commands`, `channels`, `duration_s`, `frames_per_second`, `reference`, `strides` |
| `GET api/checkpoints/<run>` | any run's checkpoint rollouts, as `stage.checkpoints` lists the stage's run (ADR-790) | `run`, `items`, `pending`, `listed_of`, `reason` | |
| `GET api/films/<run>` | the whole episodes filmed under a run by something other than its trainer (ADR-901): each `view/trace.json` at most four directories down but the run's own, by the directory that holds it | `run`, `items`, `listed_of`, `reason` | |
| `GET api/playback/film/<run>/<film>` | one film as playback frames, `<film>` the listed id with its slashes encoded (`judge-export%2Fbest%2Fs3`) | `available`, `run`, `film`, `source` | `reason`, `times_s`, `frames`, `commands`, `channels`, `duration_s`, `frames_per_second`, `joints`, `velocities`, `efforts`, `terrain`, `goto` |
| `GET api/policy/run/<run>` | the run's own policy as the Activations editor runs it (ADR-727): its network, normaliser, input and action names, the weights as base64, each input's kind from the task bundle, the gait clock and the parts each motor moves | `available`, `run`, `source` | `reason`, `label`, `network`, `normaliser`, `observations`, `actions`, `weights`, `inputs`, `clock`, `parts` |
| `GET api/policy/checkpoint/<run>/<stem>` | one checkpoint's policy, the same way | `available`, `run`, `stem`, `source` | `reason`, `label`, `network`, `normaliser`, `observations`, `actions`, `weights`, `inputs`, `clock`, `parts` |

The files the replies point to — `mesh/...`, `artifact/...`, `video/...`,
`doc/...`, `evaluation/...`, `presentation/...`, `export/...`,
`blueprint/...`, `section/...`, `status/panel.html` — are served only when a reply offers them,
and are not part of this table. `status/panel.html` (ADR-607) is the
project's own `status.html`, a regular file at its root and no symlink, at
most 512 KB, served as `text/html` with `Content-Security-Policy: sandbox
allow-scripts; default-src 'none'; script-src 'unsafe-inline'; style-src
'unsafe-inline'; img-src data:; font-src data:`, `X-Content-Type-Options:
nosniff` and `Referrer-Policy: no-referrer`: an opaque origin that runs its
own inline script and fetches nothing. Absent or refused, it is a 404.

**Each project in `api/projects`** (ADR-605) is `name`, `url` (`p/<name>/`),
`accepted` and `runs` (how many run directories), and its card: `revisions`
and `evaluations` (how many), `latest_evaluation` (`name`, `verdict`,
`passed`, `seeds`, `task_label`, `evaluated_at`, `relation` and the first
three `failing`, or `null`), `thumbnail` (`{url, source, relation}`, the
`url` relative to the index: `source` is `render` for the presentation
hero, `evaluation` for the newest passing evaluation's hero, `film` for the
newest filmed seed's detail sheet with `tile: [columns, rows]` so the page
shows its first frame, `sheet` for the concept sheet; `null` when there is
none), `stage` (as `api/project`'s, read from the newest run alone:
`state`, `reason`, `since`, `run`, `iteration`, `total`, `reward_per_step`,
`best_reward_per_step`, `eta_s`, `training_state`) and `active_at` (the
newest time any of those records, or `null`). A card is reused while the
files it reads keep their stat and it is younger than 10 s, so a directory
of hundreds of projects lists in tens of milliseconds; a project that cannot
be read gets a card that says so rather than failing the listing.

**Each accepted component's look** (ADR-522, ADR-603). Every entry of
`api/model/accepted`'s `components` carries `role`, `color`,
`role_source`, `supplier` and `printable`, and the finish the viewport
paints: `finish` (`printed`, `purchased`, `hardware` or `board`, from the
catalog family), `catalog` (`{family, part_number}` the output came off,
or `null`) and `board` — `null`, or on a catalog board whose mesh is the
catalog's, `{width_mm, length_mm, thickness_mm, chip: {origin, size},
pads: [{origin, dia_mm}], frame}` in the part's own mesh frame in
millimetres (`dia_mm` is the tinned ring's outer diameter; `frame` is the
quarter turns about +Z and the shift the mesh was moved by). For hardware
and boards `color` is the finish's base colour, whatever the role; the
model's `appearance.finishes` lists the classes and those colours. With no
assembly every one of these is `null`.

**What the browser keeps.** The page keeps no project state of its own:
everything it shows is read from these routes on each poll. What it keeps in
`localStorage` is per-viewer conveniences — `cadex.theme` (dark, light
or system), `cadex.layout.v7` (the screen's areas), `cadex.render` (the
viewport's render style, shaded or wireframe; a stored `hairline` is read as
wireframe), `cadex.meshlines` and `cadex.meshlines.strength` (the wireframe's
mesh lines, on or off, and their strength), `cadex.reflections` (the shaded
solids' reflection strength), `cadex.look`, `cadex.occlusion` and
`cadex.detail` (the shaded look's lighting setup or matcap, its ambient
occlusion and its surface detail, ADR-676), and `cadex.outliner.group` and
`cadex.outliner.folded` (how the Outliner groups the parts, and which groups
are folded), and `cadex.follow` (whether the viewport follows a playing
design, ADR-693), `cadex.heat` (the heat colours Settings picks, ADR-728),
`cadex.activations.views` (which Activations and Network views are on,
ADR-728), `cadex.trail` and `cadex.gizmo` (the first 3D viewport's trail
style and whether its axes gizmo is shown, ADR-770), `cadex.trail.colours`
(the trail's colour, or its colours by age, that Settings picks, ADR-770) and
`cadex.training.cards` (how the Training cards are arranged: their order,
which are pinned or hidden, and their sizes, ADR-770) and `cadex.primitives`
(whether the first 3D viewport outlines a training model's primitives over its
CAD, ADR-901) — and `cli/tests/test_http_api.py` fails if the page stores any
other key, or this list names one it does not. A picked
checkpoint or film, a scrubbed revision, a selected run, and the parts hidden or
selected in the Outliner last only as long as the page.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Fine. |
| 1 | The engine, the trainer or a walk leg failed. |
| 2 | The command was wrong. |
| 3 | The engine refused the script. |

Three is separate from one because a pipeline handles them differently: a
refused script is a modelling problem to feed back to the agent, a failed
engine is an infrastructure problem to retry or abort on. A walk leg killed
by `--leg-timeout` reports 124 inside the walk's envelope.

### Streams

Progress goes to **stderr**; the report goes to **stdout**. `--json` is
always safe to pipe. `cadex script` with no `--set` prints the script and
nothing else, so `cadex script > model.py` works.

## 3. The `--json` envelope

```json
{
  "schema": "cadex-cli-v1",
  "ok": true,
  "project_root": "/home/you/impeller",
  "revision": "3c09b36e…",
  "accepted_revision": "3c09b36e…",
  "digest": "08b623e1…",
  "params": {"blade_angle": 12.0, "hub_diameter": 40.0},
  "outputs": [
    {"name": "impeller", "kind": "brep",
     "files": {"step": "/…/impeller.step", "stl": "/…/impeller.stl"}},
    {"name": "balance_task", "kind": "assembly_training_task_json",
     "files": {"json": "/…/balance_task-task.json"}},
    {"name": "model", "kind": "assembly_mjcf_xml",
     "files": {"xml": "/…/model-model.xml"}},
    {"name": "hinge", "kind": "none", "files": {},
     "skipped": "no staged artifact"}
  ],
  "engine": {"source": "dev-tree", "freecadcmd": "…", "module_dir": "…"},
  "out_dir": "/…/out",
  "notes": ["…what the run did…"]
}
```

`error` is present, beside any `notes`, when `ok` is false. Commands add
their own block, described with the command: `training_plan`, `walk`,
`smoke`, `evaluation`, `revisions`, `budgets`, `style`, and `verdicts`
(§4). `stdout` is what the script printed on that run, accepted or refused
(ADR-620); the prose report prints it under the error, one `  | ` line each.
A run that accepted a build adds `fit` (the measured-fit block that build's
reply carried, with `sweep` inside it; every row, uncut) and `inventory`
(the catalog-identity block, with `catalog_by_component`, `appearance` and
`palette`), each printed as a line with one line per failing pair or
uncatalogued source. An `asset` run adds `assets`, `[{"name", "bytes",
"sha256"}, …]` sorted by name. A `train` run adds `training`, the trainer's
receipt exactly as it printed it on its last stdout line — `out`, `bytes`,
`sha256`, `reward_per_step`, `wall_time_s`, `device`, `task_sha256`, the
witness margin — never re-derived (ADR-093), and with `--put` the stored
policy's `assets` row.

**BREP outputs are converted; every other staged output is copied.** A BREP
is written under the output's name in each `--format`. A mesh's `.ply`, an
MJCF model's `.xml`, a training task's, a policy receipt's and a rollout
trace's `.json` are copied **under the filename the engine staged them
with** (`model-model.xml`, `balance_task-task.json`,
`assembly-simulation-trace.json`), because the task bundle references its
model by that name: the `--out` directory *is* the training bundle. Only an
output with nothing staged — an assembly component placing another output's
geometry, a solve diagnostic — is `skipped`.

**Compare `digest`, never the files.** `digest` is the engine's content hash
of the model: same script and same parameters, same digest, on any machine.
STEP is not comparable — AP214 writes a wall-clock timestamp into
`FILE_NAME`, so two exports of an identical model differ byte for byte
across a second boundary. `revision` is the guard the *next* write needs, if
you are driving the protocol yourself.

## 4. How it is put together

```
cadex                  repo-root shim: picks an interpreter, hands over
cli/cadex_cli/
  __main__.py          argparse; subcommands; exit codes
  engine.py            --engine / CADEX_ENGINE_ROOT / dev tree -> an Engine
  protocol.py          loads THAT engine's own CadexdProtocol
  client.py            spawn cadexd, ready banner, request, cancel, shutdown
  session.py           agent.json (the engine budgets, the style) and the project lockfile
  tools.py             the tool surface, generated from OP_ARG_SPECS
  bridge.py            runs a tool call against cadexd; injects what the agent
                       is never asked for; records every call
  mcp.py               `cadex mcp`'s wire: JSON-RPC over stdio, idle callback
  activity.py          the project activity log every `cadex mcp` tool call
                       appends to, bounded; read into /api/project (ADR-549)
  guidance.py          the guidance an agent is given (ADR-538)
  hero.py              `cadex hero` and `cadex hero-grid`: the presentation
                       folder, drawn by the page's scene (ADR-677)
  export.py            STEP/STL/BREP out of the display block; the rest copied
  render.py            `cadex render` as a job: rebuild, read fit/inventory, write the files
  clearance.py         inspect scope=clearance -> docs/clearance.md; read-time thresholds;
                       the verdict brief (the fit block itself is the engine's
                       CadexFitReport, ADR-447)
  inventory.py         inspect scope=inventory -> the project's docs/inventory.md
  studio.py            loads THAT engine's CadexStudio and CadexFitReport (ADR-445, ADR-447)
  train.py             the offboard trainer as a subprocess, local or remote
  loop.py              the training loop's run registry and its detached
                       supervisor (ADR-464): register, launch, read, stop
  checkpoints.py       each checkpoint rolled out while the run trains
                       (ADR-544); checkpoint_runner.py is its child
  walk.py              the lifecycle walk's leg plan (ADR-199)
  section.py           `cadex section`: named world-plane cuts of the accepted tessellation
  smoke.py             `cadex smoke` (ADR-352); smoke_runner.py and
                       smoke_geometry.py are its children
  evaluate.py          `cadex evaluate` (ADR-457); evaluate_runner.py is its
                       child, film.py its filmstrip and video (ADR-459)
  video.py             a retained, engine-verified rollout drawn without an engine
  revisions.py         `cadex revision`: the trail and going back (ADR-506)
  revision_meshes.py   each accepted revision's model kept by part digest (ADR-546)
  shoves.py            the shove video of a passed evaluation (ADR-571)
  review_record.py     the run record and the project review reader (ADR-285)
  review_server.py     the read-only dashboard server (ADR-286, ADR-537),
                       with review_static/ the page
  browser.py           headless Chromium over its DevTools pipe, for capture and tests
  project_docs.py      the project's own docs, PROGRESS.md rows and repo
  report.py            the envelope and the prose
cli/tests/             the suite (§7)
```

**`inspect` is bounded and a CLI is not.** `inspect scope="script"`
returns a *page* — mappings 50 keys at a time, any value over 1 KiB a stub
naming its path — so every read in `session.py` that must print a whole
file follows the pointer paths and the `next_offset` chain to the end.

### Process topology

```
  your agent ──spawns──> cadex mcp ──owns, while busy──> cadexd (FreeCADCmd)
       │                                   ▲
       └── runs ──> cadex render/export/train … --wait ──┘  (when the server is idle)
```

The agent's MCP client spawns `cadex mcp` as its own child (ADR-538). Every
call goes through the bridge in-process, so **the server sees every tool
call**: it prints a line per call on stderr, knows the session's last
accepted build, and lands it as one row and one commit when it lets the
engine go. Stdout is the protocol's alone: the server writes to a private
copy of the descriptor and points descriptor 1 at stderr.

### `expected_revision` and `display` are injected, not asked for

The protocol guards every mutation with the revision the caller believes is
current. A session holding the project lock has exactly one writer, so the
bridge tracks the revision from each reply — **including refusals**, because
a rejected candidate still becomes the working revision — and fills it in;
every tool result carries `expected_revision_used`. `display` is the
constant standard request (`quality: standard`, no edges) on every modelling
op, so the accepted attempt the dashboard draws always retains tessellation
(ADR-312). Both are removed from the schemas, anything the model supplies is
overruled, and the reply's `display` block is dropped before the model sees
it.

### Tool names are op names

`describe_api`, `write_script`, `edit_script`, `set_params`, `rebuild`,
`inspect`, `link_part`, `put_asset` — and six tools no engine op backs,
answered by the bridge (`BRIDGE_TOOLS`): `look`, `draw_blueprint`,
`train_start`, `train_status`, `train_stop` and `evaluate`. The op tools'
input schemas are **generated from `OP_ARG_SPECS`**, so they cannot drift
from the protocol; only the prose is hand-written. The surface is pinned by
`src/Mod/cadex/cadex_tests/test_project_tool_surface.py`.

`describe_api` reaches the model one page at a time (ADR-359, ADR-360).
Without arguments the reply is the **index**: everything above the domains,
and each domain and the library listing their exports by name. With
`section=<domain>` or `section=library` it is that section: notes, globals,
output types, and every export's full signature and first documentation
paragraph. `section=library_parts` (ADR-619) is the classes the `lib`
generators return (`QddPart`, `ServoPart`, `BoardPart`, …) with
`returned_by`, attributes and methods. An unknown section is
`NO_SUCH_SECTION` with the list, decided after the engine answers: the
`section` argument never reaches the engine, and is the one schema property
`OP_ARG_SPECS` does not carry (`VIEW_ARGS` in `cadex_cli.tools`). The
harness refuses a tool result over its own token cap, so each page is held
under `API_VIEW_CHAR_BUDGET` (21,500 characters, measured); measure again
after growing the contract.

### A refusal reaches the model with its diagnosis first (ADR-618)

The model's view of a refused call keeps every envelope key but bounds the
bulk inside `observed` (`bridge.refusal_view`): OCCT's progress meter is
dropped from `stderr`; `stderr` and `traceback` keep their last 3,000
characters; `details.component_placements` becomes `{count, note}`;
`details.native.joints` keeps only unsatisfied joints with
`satisfied_joint_count`; long `joint_outputs` are cut the ADR-435 way.
`stdout` stays whole (the engine bounds it at 16,000 characters). The engine
reply and the session row are untouched.

### Training refuses inputs the robot cannot read (ADR-408)

`cadex train` and `cadex walk` read the exported task before the trainer
starts and refuse when a policy channel names no `api.sensor` that measures
it, listing both ways out: declare the sensor, or mark a simulation-only
channel `role="privileged"`. `--allow-ungrounded` trains anyway and says so.
`--stop-on-collapse` (ADR-410) stops a run whose mean episode has collapsed;
`cadex walk` and `train_start` always pass it.

### Each checkpoint is rolled out while the run trains (ADR-544)

`cadex train --checkpoint-every N`, `cadex walk --checkpoint-every N` and
`train_start`'s `checkpoint_every` pass the trainer's flag. For a **local**
trainer a watcher (`checkpoints.py`) rolls each numbered checkpoint
`<out>.<tag>.cxpolicy` out through the engine on the CPU while training goes
on, polled by `cadex train` and by the loop's supervisor alike:

- The child, `checkpoint_runner.py`, runs `nice`d with the GPU hidden and
  plays one **nominal** episode (no seed, randomisation or shove) at the
  largest frame rate dividing the control rate, at most 30.
- It writes `<out>.<tag>.rollout-trace.json`, whose `checkpoint` block gives
  the file, tag, iteration, reward per step (from the `progress.json` row
  with the file's digest, `null` if unlisted) and sha256; a checkpoint that
  cannot be played leaves `<out>.<tag>.rollout-failed.json`. A rollout past
  five minutes is `rollout_timeout`. A failing watcher is switched off with
  a note; it never stops the trainer.
- One child at a time, newest first; `best` and the final policy are not
  rolled out. After the trainer exits the rest are rolled out with the slot
  released. A `--remote` trainer's checkpoints stay on the box.

### `look`: the agent sees its design (ADR-406)

`look` renders the last accepted modelling reply's display block with the
`cadex render` studio renderer — no rebuild — and returns one text block of
facts and one 768×768 PNG `image` block per view. Views are `hero`, `iso`,
`iso_back`, `front`, `right` and `top` (default `iso` and `iso_back`, at
most five); `focus` names components or outputs to frame. World geometry
is left out, and parts are coloured by their declared role, else `shell`
bone for printed and `mechanism` graphite for purchased (ADR-412, ADR-413).
The reply's `colours` and `measures` facts give the role colours and the
proxies (P1, P3, measured on the hero), and `measures.anatomy` the anatomy
verdict. A session that opens with `look` draws the attempt the store
retained, with its fit and inventory, and rebuilds only when none was
retained (ADR-689).

### The drawing sheet: `draw_blueprint` (ADR-516)

A dimensioned multi-view drawing of the accepted design, stored with the
project. It takes `name` (identity and title) and optionally `views` (1 to
4 of `front`, `right`, `top`, `iso`, `iso_back`; default `top`, `iso`,
`front`, `right`, third-angle), `callouts`, `dimensions` (default true) and
`notes`. `CadexStudio.blueprint_report` draws it from the reply `look` uses:
line views on one scale, overall extents dimensioned, every declared
`part.measurement(...)` drawn once, numbered balloons keyed to a parts list,
and a title block. The bridge stores it with `put_blueprint`, versioned by
name in `blueprints/` with the recipe in `meta`; drawing again under a name
stores the next version and takes any key left out from that recipe. The
model gets the facts and the sheet as an image; `GET /api/project` lists
every version.

### The training loop: `train_start`, `train_status`, `train_stop`, `evaluate` (ADR-464)

The agent runs the whole loop — design a task, train a policy, evaluate it
against the task's success spec, revise — and it is **one loop for every
behaviour**: no tool, registry entry or guidance paragraph names one.

| tool | what it does |
|---|---|
| `train_start` | Pre-registers one bounded run on the task **as accepted now** and launches it. Takes `run` (a new name), `budget_s` (wall clock, required), `reason` (the measurement that motivated the run) and optional `task` and `settings`. Returns at once. |
| `train_status` | Reads a run: its state, progress (iteration, reward per step, mean episode length, exploration sigma, a thinned curve), its checkpoints, and when finished the policy's path and sha256. It names the run's `task_bundle`, the file a warm start passes as `init_from_parent_task`. `wait_s` (at most 900) blocks until the run ends. Without `run`: every run and the loop's ledger. |
| `train_stop` | Asks a live run's supervisor to stop it, with the reason. Checkpoints already written stay. `run.json` lands `stopped` and the stage reads **stopped**, never failed (ADR-559). |
| `evaluate` | `cadex evaluate` for the agent: the verdict, per seed and per predicate, the metrics, the reward by term and how each episode ended in one bounded text block, then the overview and detail filmstrips of up to two filmed seeds as images. |

**A run is a directory**, `runs/<run>/`:

- `registration.json` (`cadex-training-registration-v1`), written before
  anything launches: the accepted revision and digest, the task and its
  digest, the settings and seed, the budget, the stop rule, the reason and
  the exact trainer command.
- `train/`: the task bundle and model copied from the retained accepted
  attempt (never rebuilt), the trainer's `progress.json`, log,
  checkpoints and policy.
- `training-status.json` (`cadex-training-status-v1`): `finished` (the
  policy hashes to the receipt, which names the registered task),
  `collapsed`, `failed`, `stopped`, `budget_exhausted`, `interrupted` or
  `refused`, with the reason, wall time and iterations.
- `run.json`, mode `loop`, at registration and at the end.

**The supervisor outlives the session**: `python -m cadex_cli.loop
RUN_DIR`, in a process session of its own. It stops the trainer at the
budget, on a stop request (a file it polls; no pid is ever signalled), or
when terminated. It holds the run's lock — a status saying `running` under a
lock nobody holds reads `interrupted`, an interruption and not an attempt —
and the machine's training slot (§5), so a second run is refused, and
`cadex train` and `cadex walk` are refused while it trains (ADR-543).

**Registration refuses**, each with a sentence the agent can act on: a
missing, zero or over-six-hour budget; a reason too short to name a
measurement; a used run name; a live run on this project or machine; a
training seed that is one of the task's evaluation seeds; a setting the
loop does not know; and a task whose policy reads a channel no sensor
measures (ADR-408, no override).

**The settings** (`loop.SETTING_NAMES`, by the trainer's own flag names):
`iterations`, `envs`, `seed`, `label`, `hidden`, `unroll`, `epochs`,
`learning_rate`, `discount`, `gae_lambda`, `clip`, `entropy`,
`value_weight`, `initial_std`, `action_filter_alpha`, `command_slew_deg`,
`goal_pool`, `checkpoint_every`, `critic_warmup` (ADR-740: train only the
critic for the first N iterations of a warm start), the warm start
`init_from` with `init_from_parent_task` and `init_from_task_change`,
`init_from_base` (ADR-755: with `init_from`, the reason for a warm start
onto another robot of its family, which the trainer requires
`critic_warmup` for) and `family` (ADR-759: the other built variants' task
bundles, copied into `train/family/` with their models). A warm start with
no `initial_std` continues at its source's exploration width (ADR-471). The
trainer's `--minibatches`, `--max-grad-norm`, `--reward-floor`,
`--reward-scaling`, `--activation`, `--value-hidden`, `--teacher`,
`--teacher-goal` and `--distill-weight` are **not** settings: a run that
needs them runs `training/cadex_train.py` directly. No test checks this
list against the trainer since ADR-725; rename a flag in both places.

**`loop-ledger.jsonl`**, in the project root, gets one line per thing the
loop did — a run registered (with its reason), a stop requested, a run
ended (state, policy digest), an evaluation measured (verdict, failing
predicates, and `trained_by_run`: every run whose final policy or any
checkpoint file has the evaluated digest). It is what `train_status` hands
a new session.

Storing and declaring the policy stay the tools they were: `put_asset` the
path `train_status` reports, then `assembly.policy(task, weights=…,
sha256=…)` by `edit_script`, where the engine verifies it. The loop trains
on this machine only; `--remote` is `cadex train` and `cadex walk`.
`evaluate` blocks for as long as the rollouts and film take; an MCP call
through Claude Code held for 900 s (`docs/probes/ot11/runner/block_probe.py`).
`cadex walk` stays the scripted single pass; the loop never reads its
`gait` block.

### Every build reply carries the measured fit (ADR-346)

After a successful `write_script`, `edit_script`, `set_params` or `rebuild`,
the bridge reads `inspect scope=clearance` — the engine's pair
measurements of the accepted assembly's exact solids at the solved pose —
and adds a `fit` block beside the script's `stdout`:

```json
"fit": {
  "verdict": "fail",
  "source": "engine measurements of the exact solids at the solved pose, …",
  "revision": "…", "assembly": "asm",
  "pose": "initial solved pose (not swept motion)",
  "thresholds": {"minimum_clearance_mm": 0.1, "maximum_common_volume_mm3": 1e-06},
  "pairs_checked": 3,
  "counts": {"clear": 2, "intersection": 1, "below clearance": 0, "unknown": 0},
  "failing_count": 1,
  "failing": [{"first": "a", "second": "b", "status": "intersection",
               "distance_mm": 0.0, "common_volume_mm3": 100.0}]
}
```

`verdict` is `pass` only when every pair was measured and is clear; `fail`
names the pairs that are not, **worst first** (unmeasured and world-geometry
rows, then the largest common volume, then the smallest distance).
`unavailable` means nothing was checked — no placed components, or a read
error — and never means pass. **A failing fit is reported, never refused.**
The block comes from the published measurements, never from `stdout`. Every
page of `inspect scope=clearance` is read before a verdict; a page that
cannot be read makes the whole block `unavailable`. The engine joins the
scope once per accepted report and serves later pages from that join
(ADR-630).

The rules the fit applies — declared `contacts=` and `clearances=` (ADR-347),
the implied `attached` intent of a fixed joint (ADR-372, ADR-380), the
1e-9 mm slack (ADR-353), world geometry (ADR-420, ADR-427, ADR-623) and the
`attachments` report (ADR-370) — are the xscript's, in
[`XSCRIPT.md` "Measured assembly fit"](XSCRIPT.md#measured-assembly-fit-adr-347).
CLI threshold overrides apply to undeclared gaps and common volume only; a
pair a fixed joint welds takes no minimum, even an overridden one.

### A build reply fits one tool result (ADR-435)

The harness refuses an MCP result past its own cap (measured near 21,700
characters) and writes it where the agent cannot read it. The engine reply
is unchanged; the **model's view** of a successful build is bounded:

- `outputs` becomes `{count, by_kind, names?, not_live, detail, note}`
  (`names` only for 40 outputs or fewer); `live_outputs` is dropped; one
  output's row is `inspect scope=output target=<name>`.
- `fit.failing`, `fit.world_geometry_contacts`, `fit.sweep.failing`,
  `fit.sweep.world_geometry` and `fit.attachments.reported` are worst first,
  at most `BUILD_VIEW_LIST_LIMIT` (12) rows, with `<list>_omitted` and
  `<list>_rest` (the `inspect` path) when cut. `fit.sweep.joints` lists only
  joints not swept to completion.
- `inventory.appearance` becomes a count per role and
  `inventory.catalog_by_component` is left out; `printed_edges` keeps its
  totals and the `sharpest` parts; `uncatalogued_sources` and
  `derived_catalog_sources` are cut the same way.

Every verdict, count and threshold is the whole block's; the envelope's
`fit` keeps every row.

### Every build reply carries a verdict brief (ADR-689)

Beside the bounded `fit`, a successful build reply carries `verdicts`, and
`cadex script --set`'s envelope the same (`clearance.verdict_brief`): every
verdict and count of the fit block and the worst rows of each check as one
line each, at most `VERDICT_BRIEF_LIMIT` (8) failing and 4 advisory rows a
list, with `<list>_more` counting the rest.

```json
"verdicts": {
  "revision": "aaaaaaaaaaaa", "fit": "fail", "pairs_checked": 2, "failing_pairs": 1,
  "pairs": ["board ∩ rub: intersection 12 mm³"],
  "sweep": {"verdict": "fail", "joints_swept": 1, "joints_limited": 2, "failing_pairs": 1,
            "unswept": ["knee: incomplete, runtime budget exceeded"],
            "pairs": ["leg ∩ rub through hip: intersection 40 mm³"]},
  "panels": {"verdict": "fail", "panel_count": 3, "failing": 3, "advisory": 0,
             "failing_panels": [
               "rub: colliding, colliding in motion -- it overlaps board; it is struck through the motion by leg (hip).",
               "egg: floating -- its inner face's p90 gap is 31.3 mm, past 8.0 mm.",
               "loose: unmounted -- no bolt through it threads into a non-panel part and no fixed joint welds it to one it touches."]},
  "mounting": {"verdict": "unknown", "purchased": 1, "held": 0,
               "not_held": ["motor: unknown -- No solved placement was published for this component."]},
  "attachments": {"verdict": "touching", "welded_pairs": 2, "not_touching": 0},
  "rest": "Every row: inspect scope=clearance path=/pairs, /panels (each row carries its verdict and findings), …"
}
```

`fit: unavailable` carries `reason` and nothing else; `rest` appears only
when the brief names a row. **A panel row says its verdict**: `inspect
scope=clearance path=/panels` (or `/panels/N`) through `cadex mcp` returns
each published panel row with `CadexFitReport.panel_summary`'s judgement
joined on — `verdict` (`fail`, `reported`, `pass`), `findings`, `detail`,
`mounted`, `held_by`, `floating_at_mm` and the in-motion collisions —
because the service never imports the fit report (ADR-445).

### The same reply carries the swept fit (ADR-366)

`fit.sweep` is the swept half, read from the `clearance_sweep` the same
`inspect scope=clearance` value carries:

```json
"sweep": {
  "verdict": "fail",
  "coverage": "incomplete",
  "step_degrees": 5, "step_mm": null,
  "joints_checked": 2, "joints_complete": 1,
  "joints": [
    {"joint": "rail", "kind": "slider", "unit": "mm", "status": "incomplete",
     "pairs_measured": 0, "pairs_moving": 0,
     "reason": "sweep_step_mm is not declared on the assembly, so this limited slider joint was not swept"}
  ],
  "failing_count": 2,
  "failing": [{"joint": "knee", "first": "thigh", "second": "shin", "status": "intersection",
               "minimum_distance_mm": 0.0, "maximum_common_volume_mm3": 42.5,
               "first_contact_degrees": -55.0}]
}
```

`verdict` is `pass` only when every limited joint was swept to completion
and no pair the joint moves interpenetrates or closes below its own minimum
anywhere in its range (ADR-378). Swept findings against world geometry are
advisory (ADR-420); passive loop joints are counted, not judged (ADR-621);
suppressed joints are `skipped` (ADR-371); a joint with no limits is
missing coverage (ADR-375); and `unavailable` covers both a revision from an
engine that published no sweep and an assembly with no limited joint, told
apart by `coverage` and `reason` (ADR-368). Each joint is swept by its own
child, up to four at once, each child's budget `max(90 s, total/3)` within
the run's wall budget (ADR-622, ADR-820). What the engine measures, and the
declarations it reads (`sweep_step_degrees`, `sweep_step_mm`), are
[`XSCRIPT.md` "Sampled hinge and slider fit"](XSCRIPT.md#sampled-hinge-and-slider-fit-adr-349-adr-351).
`inspect scope=clearance path=/clearance_sweep` reads the published sweep
unchanged, and `cadex clearance --sweep` writes it to
`docs/clearance-sweep.md`; complete coverage means measurements exist, not
that fit passes. The prose report prints a `sweep` line under `fit`.

### What holds each purchased part (ADR-486)

The clearance scope publishes `components` — catalog rows with
`mount_axes` (hole centres and axes, or a bolt's own axis) and printed rows
cut with a part's `.bay()` with `houses` — and build replies carry
`fit.mounting`: one row per purchased part (catalog parts less fasteners
and printed gear/rack generators), `held` by `screws` (a placed `lib.bolt`
within 0.5 mm and 5° of a hole axis, touching the part and a printed part),
`bay`, `press fit` (bearings, bushings, spherical joints touching a printed
part), `output` (a horn or wheel touching a held servo or motor) or `rim` (a
tyre on a held wheel, ADR-489), or reported as `contact only`, `inside
shell` or `held by nothing`. The verdict is `pass`, `reported`, `unknown`,
`none` or `unavailable`; it refuses nothing and is not a strength check.

- A bolt counts only if it fits the hole (ADR-488): a tapped hole
  (`thread_dia_mm`, e.g. the N20's M1.6 face) takes only its thread, a
  clearance hole (`hole_dia_mm`) any bolt no larger. A misfit is listed in
  `misfits` and holds nothing.
- A bolt that fits counts only if its shank threads into something
  (ADR-492): a printed part it shares at least 0.1 mm³ with, the held
  part's own tapped hole, the held part, a nut or a heat-set insert. A head
  resting on a printed part with the shank in a cavity is `unthreaded`.
- The static fit allows that thread: a `lib.bolt` and printed part sharing
  no more than `π/4 (d² − minor²) L` are `clear`, counted in
  `fit.threaded_count`; more still fails. `cadex clearance` writes such a
  row as `threaded`.

### Every build reply carries the published catalog identity (ADR-362)

Beside `fit`, the same replies carry `inventory`, read from `inspect
scope=inventory` under the same lock: `component_count`,
`catalogued_count`, `uncatalogued_count`, `catalog_counts`,
`uncatalogued_sources` (the distinct outputs no `lib.*` generator built
as-is) and `derived_catalog_sources` (ADR-381): `{"source_output",
"family", "part_number"}` for each uncatalogued output whose definition's
**base operand** spine reaches a catalog body — a purchased part the script
cut, which has lost its catalog identity. A catalog body used only as a
cutter is listed nowhere. **Absence is unknown provenance, not proof of a
printed part** (ADR-382): a catalog body fused in as a second operand is not
named. The block is advisory, computed from the published inventory, never
from `stdout`; `available: false` carries the reason and refuses nothing.

### Every build reply carries the creature's moving anatomy (ADR-614)

The same replies carry `anatomy`, from `inspect scope=anatomy`: the bounded
view (`CadexAnatomy.anatomy_view`) of the regions the script declared with
`assembly.anatomy` (`docs/XSCRIPT.md` "Anatomy"), computed from the accepted
joint graph — `verdict`, `actuated_dof`, `joint_dof`, `mobile_joints`,
`actuated_joints`, `rigid_bodies`, `root_component`, per-region `status`
and `joints` (each joint `actuated`, `loop`, or `catalog drive: <part>` when
a catalog actuator welded to one side drives it), and the
`rigid_appendages` each weld cluster sticks out with `acknowledged`. It is
advisory; `undeclared` still carries the totals, and an unreadable block is
`unavailable` with the error.

### What the agent is told

One text (`guidance.py`, ADR-538), printed by `cadex guidance`. `cadex mcp`
sends a brief of it as the server's `instructions` and the brief tells the
agent to run `cadex guidance` first. A client that reads instructions from
a file can take the printed text into an `AGENTS.md` or a skill instead.
**It never states the xscript API**: the agent asks the engine with
`describe_api`, which keeps one contract from becoming two.

Most of it is the engine's `Mod/cadex/CadexAgentGuidance.md` (ADR-446),
read from the engine the CLI resolved, with the tool names filled in: the
domain-neutral **base** (ADR-560) — the design loop, measured-not-guessed,
the build reply's blocks as floors, and saying what is unfinished — written
as principles with a reason and a check, not fixed taste numbers (ADR-651).
A line that is wholly an HTML comment is dropped (ADR-654). A **style** is a
named `Mod/cadex/CadexAgentStyle.<name>.md` beside it — `printed-legged-robot`,
`creature`, `gantry-machine`, `vehicle` and `product` (ADR-653) — of which a
project chooses at most one with `cadex style`; none is on by default. The
overlay around it tells the agent how to choose one, and covers the
situation: the person watches the read-only dashboard, *build it
parametric*, `look` to see and facts to prove (ADR-406), design it rather
than only fit it (`docs/DESIGN-LANGUAGE.md`, ADR-479), the `fit` and
`inventory` blocks as evidence over the script's printout (ADR-346,
ADR-362), `put_asset` and the training loop (ADR-464), the CLI for the legs
the tools do not cover (with `--wait`, never an invented flag), the project
documents (ADR-193), asking only when the answer would change the design,
and that revision guards are handled.

## 5. Sessions, locks and state

`<project_root>/agent.json` is the CLI's own file, holding the project's
engine budgets (ADR-517) and its design style (ADR-560):

```json
{"schema": "cadex-cli-agent-v1", "updated_at": "2026-10-04T12:36:31Z",
 "budgets": {"timeout_seconds": 900.0}, "style": "printed-legged-robot"}
```

It is a **sibling** of the engine's `script.json`, never a replacement: the
CLI reads engine state through `inspect` and writes only its own. A file an
older CLI wrote with a stored conversation is read for its budgets, and the
conversation is dropped on the next write.

`<project_root>/.cadex-cli.lock` is an advisory `flock`, because `cadexd` is
one process per project and a sweep runs several commands at once. The
kernel releases it on process death, so there is no stale-lock heuristic. A
second run is refused with a readable message; `--wait` blocks instead. A
command holds it for its one run and releases it before the `PROGRESS.md`
row and the commit; `cadex mcp` holds it while it has the engine open.

The machine's **training slot** (`~/.cache/cadex/training.lock`, or
`$CADEX_TRAIN_LOCK`) is a second `flock`, one per machine (ADR-543). A
`train_start` supervisor holds it while it lives, and `cadex train` while
its local trainer runs. While another run holds it, `cadex train` and
`cadex walk` exit 3 before doing anything, so a refused walk has not moved
the accepted revision. `--remote`, `train --dry-run` and `walk --complete`
take no slot. There is no `--wait` for it.

## 6. Which engine

In order: `--engine`, then `CADEX_ENGINE_ROOT`, then the development tree
(`.pixi/envs/default/bin/FreeCADCmd` or `build/release/bin/FreeCADCmd`, plus
`src/Mod/cadex`). The first two name a **staged payload root**, read through
its `cadex-engine.json` manifest (ADR-020) — the same resolution
`test_cadexd_lifecycle.py` uses. Resolution rejects a manifest `protocol`
that differs from the module's `CadexdProtocol.PROTOCOL_SCHEMA`; agreement
proves neither worker completeness nor shared provenance. The envelope
names the resolved engine.

Every reply is shape-checked against **that engine's own**
`OP_RESPONSE_SPECS`, and a violation is an error rather than a warning.

## 7. Running the suite

```bash
CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests
```

It holds contracts, not coverage (ADR-725): 53 tests in about 40 seconds
(2026-10-27). Behaviour is verified by running the command.

| File | What it holds |
|---|---|
| `test_mcp_protocol.py` | `cadex mcp`'s wire (§2a): `initialize`'s version handling, JSON-RPC errors, `tools/list` relaying the generated surface and its schemas against `OP_ARG_SPECS`, the injected `expected_revision` and `display`, the build reply's `fit` and `inventory` blocks, and an unknown tool refused before any engine; against `fake_cadexd.py`, no engine needed. |
| `test_http_api.py` | The HTTP API contract (ADR-552): the "HTTP API" table above, `API_ROUTES` and `API_RESPONSE_KEYS` agree; the router dispatches from the table alone; every route's replies on a fixture biped carry their always-keys and nothing unlisted; and the page stores only the `localStorage` keys "What the browser keeps" lists. |
| `test_dashboard_read_only.py` | The read-only dashboard (ADR-537): every method but GET and HEAD refused under `cadex review` and `cadex app` with the project unchanged; in Chromium, an open page following a `cadex params` run outside it (**skips** without an engine or a Chromium); and the loopback defaults `docs/DASHBOARD.md` §22 relies on. |
| `test_dashboard_ground.py` | The ground the page draws (ADR-742–ADR-746): the design always stands over drawn ground with the follow camera on or off, a served course is drawn as one mesh ending at the mat's plane, and the drawn height agrees with MuJoCo's ray onto the engine's placed courses within 5 mm. |

`review_helpers.py` holds the shared fixtures, `cdp_browser.py` drives
headless Chromium over its DevTools pipe (`CADEX_BROWSER` names one), and
`fixtures/orun3-biped/` is the fixture biped's model and task.
`fake_cadexd.py` is a scripted engine whose replies go through the same
`validate_response` path production uses, so a drifted fixture fails there.

Everything that needs an engine **skips** without one, so a green run on a
bare checkout proves less than it looks like. Hide the GPU while a training
job runs (`CUDA_VISIBLE_DEVICES=`).

CI runs the suite in both jobs of `.github/workflows/cadex-app.yml`, after
the engine build; the Linux job runs it against the build tree and again
against the staged payload, because a source tree that passes proves
nothing about a payload (ADR-023). Both jobs have been green since
2026-10-16 (`docs/cadex-release-packaging.md`, "Building and releasing").

## 8. Limits

- **Linux and macOS.** The lockfiles are POSIX `flock`. Windows is not
  supported.
- **No `inspect scope=image` and no `resolve_pin` in the model bridge**:
  both need a viewport this client does not have. The agent's picture is
  `look`; its shell runs `cadex render` for the files. Blueprint sheets are
  stored (ADR-150, ADR-516) through `draw_blueprint`; `put_blueprint`
  itself is not a model tool, because a path to an arbitrary PNG is not one.
- **Export converts BREP and copies the rest** (§3). It runs as a short
  `FreeCADCmd` job rather than a protocol op; `export.py` is the one seam
  that would become an `export_model` op.
- **The CLI does not ship in the engine payload.** It runs from the
  repository, and so does `train`'s trainer, under a venv the engine's
  environment deliberately lacks (ADR-084). No venv, no `train`.
  `--remote` finds `training/remote_train.sh` the same way; the box is
  `training/.remote.env`'s (ADR-089).
- One `--set` per parameter, and parameters are numeric — that is what
  `num(...)` declares. A switch is a `num` with `min=0, max=1, step=1`
  and a `>= 0.5` test in the script (ADR-192).
- `cadex train` and `train_start` pass a subset of the trainer's flags
  (§2, §4); the rest need `training/cadex_train.py` directly.
