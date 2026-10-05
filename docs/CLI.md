# CLI.md — Cadex, headless

Verified against source: 2026-10-05. Provenance: [Cadex-new] (ADR-061).

`cli/` is **the client of the cadexd protocol** — the only one since the
Blender shell was deleted (ADR-498), and it owed that shell nothing: no
display, no `bpy` imports, no shell code. No project needs Blender:
`mesh.blender` is retired (ADR-496).
It is how an agent, a person at a terminal and a pipeline drive a project.
**Cadex has no agent of its own** (ADR-538): the agent is the person's —
Claude Code, Codex, Pi, any MCP client — and it reaches the engine through
`cadex mcp`, which serves the tools and the guidance over MCP stdio, and
through the commands below.

```bash
claude mcp add cadex -- "$PWD/cadex" mcp --project "$PWD/bracket"   # once, per project
./cadex guidance                                       # what the agent is told
./cadex params --set fin_angle=12 --out ./sweep/12     # no AI in the loop
```

## 1. Why it exists

The engine was never the part that needed a screen. It is a headless NDJSON
service, and as of ADR-060 it builds, tests, packages and models on a
headless Linux box. Everything that needed a display was the shell.

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

| Command | What it does | Spends tokens |
|---|---|---|
| `cadex mcp [--idle S]` | Serve the project's tools to an agent over MCP stdio (ADR-538; §2a below). The engine opens on the first tool call and closes after `--idle` quiet seconds (default 30; 0 holds it), releasing the project for the agent's own `cadex … --wait` commands; a session that accepted a build lands one `PROGRESS.md` row and one project commit as it closes. | no (the agent's own) |
| `cadex guidance` | Print the whole guidance an agent driving Cadex follows. `cadex mcp`'s `instructions` are a short brief that tells the agent to run this (§2a). No engine. | no |
| `cadex params --set k=v` | Set declared parameters and rebuild. | no |
| `cadex script` | Print the project script. | no |
| `cadex script --set FILE` | Replace the script from a file and rebuild. | no |
| `cadex export` | Rebuild the accepted script and write its outputs. | no |
| `cadex section --plane XY [--offset-mm 8]` | Cut accepted tessellation through a world plane; revision-bearing SVG and JSON under `review/section/` (ADR-240). **`--offset-mm` is optional**: omitted, the offset is derived from the accepted bounds the way the walk derives it — every candidate is cut and the one covering the most objects wins (ADR-273, ADR-275). The note reports the offset, whether it was `explicit` or `derived`, and how many of the model's objects the cut reached. | no |
| `cadex render` | Rebuild accepted display and write front/top/right/iso SVG previews, a 1024 px studio `hero.png` (ADR-412), the concept sheet `sheet.png` (ADR-430) and `review/render/summary.json`, bearing the full accepted revision (ADR-239). CPU only; no graphics runtime. | no |
| `cadex clearance` | Write `docs/clearance.md` naming every component pair, labels and catalog ids, minimum distance (mm), common volume (mm³) and verdict. Reads published measurements at the initial solved pose with no rebuild or tokens; not a swept-motion check (ADR-237). Missing measurements remain unknown. Exit 0 means the report was written, not that all pairs are clear. The same rows reach the agent as `inspect scope=clearance` and, summarised, as the `fit` block on every build reply (ADR-346), whose `sweep` half carries the published joint sweeps (ADR-366). | no |
| `cadex inventory` | List the parts of the accepted assembly with catalog ids: one row per component with the output it places, its catalog family and part number where a `lib.*` generator built it, the appearance role it declares (ADR-413), and the pose the solver settled on; a declared palette is listed under the table. Writes `docs/inventory.md` in the project (ADR-236). Reads the pinned accepted attempt — no rebuild. Resolves all inspection pages and previews, including catalog totals, uncatalogued names and large component rows. | no |
| `cadex link --from DIR` | Bring a part in from another project, or refresh one. | no |
| `cadex asset --put FILE` | Copy a file into the project store — a trained `.cxpolicy` coming home, its `.json`/`.xml` provenance, a mesh, a `.cxpart`. With no `--put`, list the store. | no |
| `cadex train --out DIR` | Rebuild, export the training bundle into `--out`, run the offboard trainer on it from its venv, and report the receipt. With `--put`, store the policy and report its sha256. With `--remote`, the trainer runs on the box through `training/remote_train.sh`; the artifacts do not move. With `--dry-run`, report the plan — the files the leg would touch and the steps it would take, in either mode — and train nothing. | no |
| `cadex smoke --out DIR` | Simulate retained accepted artifacts with zero action or held position actuators, check finite state, exact component overlaps and floor support, and write `smoke.json` (ADR-352; details below). No rebuild or acceptance. | no |
| `cadex evaluate` | Hold the accepted policy against its task's success spec (`assembly.success`, ADR-456): one rollout per frozen seed under the spec's conditions, then pass or fail per seed and per predicate, the behaviour metrics, the reward by term and how each episode ended, written to `evaluations/<revision>-<policy>/evaluation.json` in the project, with a filmstrip and a rollout video drawn from the seeds' traces on the dark prototype floor (ADR-457, ADR-459; details below). No rebuild or acceptance, and no trainer. | no |
| `cadex walk --out DIR` | The lifecycle walk as one command: an optional change (`--set`), train and store (locally, or on the box with `--remote`), re-declare the policy in the script, verify and roll out, review. Every leg is a child `cadex` command, each bounded by `--leg-timeout` (default 3600 s); `review.json` lands in `--out`. | no |
| `cadex review --host ADDR --port N` | Serve **this one project's** dashboard to a browser, read-only (ADR-286): the model in an orbit/zoom WebGL viewport — the accepted attempt's tessellation, or a run's own rollout meshes at its own revision — its drawings, documents and training plots in a 2D viewport, and the revision trail in the menu bar (ADR-539); its `GET /api/...` routes also serve every recorded run labelled current/historical, its parameters and specs as recorded, rollout figures and retained artifacts. Opens no engine, rebuilds nothing and writes nothing: it answers GET and HEAD only, and follows what the agent changes (ADR-537, `docs/DASHBOARD.md` §18). Default `127.0.0.1:8765`; `--host` the machine's Tailscale address to reach it from another device. Ctrl-C stops it. How the page is laid out, typed and coloured is `docs/DASHBOARD.md`. | no |
| `cadex budgets [--set NAME=VALUE ...]` | The project's engine budgets (ADR-517): `timeout_seconds`, the wall-clock seconds one engine script run may take (at most 3600), and `memory_limit_mb`, its memory ceiling (at most 131072). Stored in the project's `agent.json`; every later run — an MCP session, a `params`, a revision, each leg of a walk — sends them as `open_project`'s `budgets`, and the engine fills one that is not set from its own default (300 s and 6144 MB unless its preferences say otherwise). `--set NAME=0` unsets one. With no `--set` it reports. The envelope's `budgets.stored` is what is stored. `--engine-timeout` / `--engine-memory` override them for one call. `GET /api/project` carries them read-only. No engine, no row, no commit. | no |
| `cadex revision list\|reject\|restore [SELECTOR]` | Going back through the revisions (ADR-506). `list`: the stored trail (`script_history/`, ADR-045), oldest first, with the values and digest each was accepted with — no engine, no row, no commit. `reject`: put back the revision accepted before the current one; `restore SELECTOR` (an ordinal or a revision prefix): put back that one. Both write the stored source through `write_script` with `replace` (going back may drop outputs on purpose), then its recorded values through `set_params`; each is a run with its row and commit. The envelope's `revisions` says the `target`, where it came `from`, what was `accepted`, whether that is `exact`ly the target, and whether it is the `same_geometry` — a parameter the target left at its default cannot be unset once stored, so it is set to the default and the revision id differs. A selector that is not the accepted revision is a usage error for `reject`. | no |
| `cadex app [--projects DIR] [--host ADDR] [--port N]` | Serve the dashboard over a **directory of projects** (orun2 D1, ADR-502): `/` lists every subdirectory holding a `script.json` — re-read on each request, so a project made while the page is open appears — with when it was last accepted (`/api/projects` also carries its revision and run count), and each project's review page (the one `cadex review` serves) is under `/p/<name>/`. **A bare `cadex`, with no subcommand, is this command** (`cadex -h` is the help), and so is `pixi run app`. The directory is `--projects`, then `CADEX_PROJECTS`, then `~/cadex-projects`, created if absent. Default `127.0.0.1:8765`; for another device put `tailscale serve` in front of it. Read-only, as `cadex review` is (ADR-537). From a fresh clone: `pixi run setup-engine && pixi run build-engine && pixi run app`. | no |

Flags, valid on either side of the subcommand:

| Flag | Meaning |
|---|---|
| `--project DIR` | Project root; **created if absent**. Default `./.cadex`, or `$CADEX_PROJECT`. |
| `--out DIR` | Write exported files here. Omit and nothing is written. |
| `--format step,stl` | Any of `step`, `stl`, `brep`. Default `step,stl`. |
| `--offset-mm N` | `section`: where along the plane normal to cut. **Omit it** to derive the offset from the accepted bounds (ADR-275); the old default was the constant 0.0, which on a mechanism standing off that plane draws an empty page and calls it `empty`. |
| `--sweep` | `clearance`: write published joint sweep coverage and measurements to `docs/clearance-sweep.md`, without rebuilding (ADR-350). |
| `--seconds S`, `--mode hold\|zero`, `--penetration-mm N`, `--rest-speed-mm-s N`, `--max-tilt-degrees N`, `--fps N`, `--timeout S` | `smoke` (ADR-352): the simulated duration (default 2 s), the command (hold the solved pose, or zero action), the deepest floor-proxy penetration (default 0.5 mm), the speed under which a free base counts as resting at the end (default 10 mm/s), how far a free base may turn from its accepted pose before it counts as fallen over (default 30°, ADR-377), the samples per simulated second at which the checks look (default 50), and the wall-time bound (default and maximum 300 s). `--model NAME` and `--task NAME` pick among several exported models or tasks. |
| `--policy NAME`, `--task NAME`, `--timeout S` | `evaluate` (ADR-457): which declared policy output, or the policy declared against which task output, when the script declares more than one; and the wall-time bound on the child (default 1800 s, at most 7200). `--out DIR` moves the report out of `evaluations/`. |
| `--film SEEDS`, `--no-video`, `--detail-start S`, `--detail-step S`, `--film-only` | `evaluate` (ADR-459): which seeds are drawn as a filmstrip — `auto` (the default: the first failing seed, or the first seed of a pass), `all`, `none`, or seed numbers separated by commas; the first one is also drawn as a video unless `--no-video`. `--detail-start` and `--detail-step` place the detail sheet's twelve frames (default: from the seed's first disturbance, or the middle of an episode with none, 0.2 s apart). `--film-only` measures nothing and draws the film of the evaluation already in the directory. |
| `--min-clearance-mm N` | `clearance`: flag distances strictly below N (default 0.1 mm). |
| `--max-common-volume-mm3 N` | `clearance` and `smoke`: flag volumes strictly above N (default 0.000001 mm³). Thresholds must be finite and nonnegative; changing them does not rebuild. |
| `--assembly OUTPUT` | `inventory` and `clearance`: the assembly output to inventory. A project publishes at most one, so this is only ever a check that you are looking at it. |
| `--blueprints` | `export` only: also copy the project's stored blueprint sheets into `--out`, store filenames kept (ADR-150) — which since ADR-157 means `0007-gearbox-overview-v1.png` for a **named** sheet rather than a revision prefix. Read-only — the agent's `draw_blueprint` draws them (ADR-516); this only reaches the store through `inspect scope=blueprint`. |
| `--engine ROOT` | A staged engine payload. Default: `$CADEX_ENGINE_ROOT`, then the dev tree. |
| `--engine-timeout S`, `--engine-memory MB` | The engine budgets for this call only (ADR-517), each over the project's stored one (`cadex budgets`); `walk` hands them to every leg. Out of range is a usage error before an engine starts. Every engine run's envelope carries `budgets`: `in_force` (what the engine resolved), `stored`, and each one's `source` — `override`, `project` or `engine`. |
| `--json` | Emit the machine-readable envelope on stdout. |
| `--wait` | Block for the project lock instead of failing. |

`script --set` also takes `--replace`, which is you saying you mean to drop
an output the accepted revision declares — without it such a script is
refused, because `write_script` replaces *the whole* script and losing an
output by accident is easy (ADR-045).

### 2a. Driving a project with your agent: `cadex mcp` (ADR-538)

Cadex has no agent of its own. Register `cadex mcp --project DIR` with the
agent you already use, once per project, and talk to the agent; open the
dashboard beside it to watch.

```bash
# Claude Code
claude mcp add cadex -- /path/to/cadex/cadex mcp --project /path/to/bracket
# Codex (~/.codex/config.toml)
#   [mcp_servers.cadex]
#   command = "/path/to/cadex/cadex"
#   args = ["mcp", "--project", "/path/to/bracket"]
# any other MCP client: a stdio server, that command and those arguments
./cadex app            # the read-only dashboard, http://127.0.0.1:8765/
```

The server answers `initialize` with a **brief** as its `instructions`, a
paragraph under 2,000 characters that names the project and tells the agent
to run `<repo>/cadex guidance` in its shell before its first tool call.
Claude Code cuts a server's instructions at 2,048 characters unless
`CLAUDE_CODE_MAX_MCP_DESCRIPTION_LENGTH` says otherwise, and the whole
guidance is about 34,000, so it travels through the agent's shell, which
every agent this serves has. `tools/list` answers with the tool
surface — `describe_api`, `write_script`, `edit_script`, `set_params`,
`rebuild`, `inspect`, `link_part`, `put_asset`, `look`, `draw_blueprint`,
`train_start`, `train_status`, `train_stop`, `evaluate` — neither of which
opens an engine. The first tool call takes the project lock (waiting for a
`cadex` command that holds it) and opens the engine; the server lets both
go after `--idle` seconds with no call (default 30, `0` to hold them until
the client goes) and opens them again on the next call. So the agent's own
`cadex render`, `export`, `section`, `train` or `walk` on the same project
runs between bursts of tool calls, with `--wait`; the guidance tells it so.
A reopen costs one restore pass, the same as any `cadex params`.

Each tool call prints one line on stderr (` · write_script  plate
(8eeaaa38…)  fit …`), which an MCP client keeps in its server log. When the
server lets the engine go after a session that accepted a build, it lands
what a CLI run lands: one `PROGRESS.md` row, `mcp: write_script, set_params
×2`, with the accepted revision and digest, and one commit in the project's
own repository with that message. A session that only read lands nothing.
Stdout carries nothing but the protocol. Measured on a one-box plate:
`initialize` 0.05 s, a cold `write_script` 0.4 s, a `set_params` after an
idle close 0.5 s.

`link` takes `--from DIR` (the other project's root, read and never
changed), `--output NAME` (which of its declared outputs to pull; omit it
and the refusal lists what it declares), and `--name FILE` (what to store it
under, default `<output>.cxpart`). **There is no separate refresh command,
because there is no separate operation** (ADR-138): the op overwrites the
stored container, and overwriting an asset is re-import, so running the same
command again is the whole of refreshing. A run that finds the other project
moved rebuilds this one behind it — so the new geometry lands as one normal
accepted revision — and a run that finds nothing moved rebuilds nothing,
because a no-op that re-accepted the model would put a meaningless revision
in the history every time somebody checked. A rebuild that then fails
against the new shape exits `3` and says what broke.

`asset` takes `--put FILE`, repeatable, and `--name NAME` for a single
`--put` (same suffix; re-using a stored name replaces the file). It is the
headless door for a trained policy (ADR-190): the offboard trainer's
`.cxpolicy` and the task `.json` it travels with go in through `put_asset`
— the path a mesh already travels, and the one write to the store that is
not the script's — and the envelope's `assets` rows carry each stored
file's `sha256`, which is the digest `assembly.policy(weights=…, sha256=…)`
requires. **It never rebuilds**: a stored file changes nothing until a
script names it, and that change is `cadex script --set` or the agent's
`edit_script`. A file the store does not hold (`.txt`, a `--name` that
changes the suffix) is the engine's refusal, exit `3`, and nothing is
written; a `--put` that does not exist is a usage error before the engine
runs. With no `--put` it lists the store, which is how a pipeline learns a
digest it did not store itself.

`train` is the training leg as one command (ADR-191): it rebuilds, exports
the accepted script's outputs into `--out` (required — the bundle and the
policy land there), finds the one exported training task (or the one
`--task NAME` picks), runs `training/cadex_train.py` on it under the
training venv's interpreter, and puts the trainer's receipt in the
envelope as `training`. Training stays offboard (ADR-084): the CLI spawns
the trainer as a subprocess and the engine is never in the room while it
runs — the project lock is held for the rebuild and, with `--put`, again
for the store write, and released between them. The trainer's flags are
carried by name so that nobody guesses them: `--iterations N` (200),
`--envs N` (256 — drop it hard on CPU, `training/SETUP.md`), `--seed N`,
`--label TEXT`, `--init-from POLICY` (warm start, same task digest),
`--init-from-parent-task BUNDLE` with `--init-from-task-change REASON`
(warm start **across** a task change — the curriculum pair, ADR-161; the
three travel together or it is a usage error, and the trainer owns the
rule about which task keys may move), `--name NAME.cxpolicy` (the
policy's filename in `--out`, default `<task>.cxpolicy`), `--timeout
SECONDS` (stop the trainer; 0 is no limit). The interpreter is `--trainer-python PATH`, then
`$CADEX_TRAIN_PYTHON`, then `<repo>/.venv/bin/python`, then
`~/cadex-train-venv/bin/python` — the two places `training/SETUP.md`
names — and **nothing creates a venv**: none found is exit 1 with the
list of places tried. `--put` copies the policy into the store through
`put_asset` and reports it as an `assets` row, whose `sha256` is the
digest `assembly.policy` names. **It never rebuilds after training**, for
the same reason `asset` does not: the policy is real when a script names
it, which is `cadex script --set` or the agent's `edit_script`. A project
whose accepted revision exports no training task is exit 3 before the
trainer runs; a trainer that exits non-zero or hits `--timeout` is exit 1
with its stderr already on ours.

**Iterating — change the mechanism or the task, retrain, compare** is
four commands and one digest edit, with no new flag on `params`
(ADR-192) — and since ADR-199 the four and the edit are one command,
`cadex walk`, below. A sweep that moves the task digest is refused at exit 3 while
a policy is declared against that task, correctly: the policy no longer
fits, and the refusal writes nothing, so it cannot export the bundle a
retrain would need. The convention is a **numeric switch parameter** in
front of the policy:

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

`set_params` never refuses a dropped output (only `write_script` does,
ADR-045), so blanking the switch is an ordinary accepted revision that
declares no policy and exports the task with its new digest. A stored
parameter value outlives a script write, which is why the last step is a
`params` call and not part of the `script --set`. The comparison is the
`policy` block of the two exported traces (`total_reward` and the
per-term `reward_totals`), and the CLI records it: the second run's
`PROGRESS.md` row carries its `total_reward` **with the change against the
last row that had one** (ADR-194, below).

**Build the engine before you walk.** The walk resolves the installed
engine and reports Python-file differences (ADR-251), but does not rebuild
or refuse them. A Python change under
`src/Mod/cadex/` that has not been through `pixi run build-engine` runs the
*previous* runtime and the walk still exits 0. On a fresh checkout, or after
any engine edit, build first.

For a toy CPU walk, follow [training setup §b](../training/SETUP.md#b-cpu-only):
select `JAX_PLATFORMS=cpu` even in a CUDA-capable trainer venv.

**The walk is one command** (ADR-199). `cadex walk --out DIR` runs the
legs above in order, each as a **child `cadex` command** — so each lands
the `PROGRESS.md` row and the project commit it always lands, writes the
artifacts the documented command writes, and the walk adds no second way
of doing any of them:

1. Nothing to design: the walk starts from the project as the agent left
   it, whose script declares its task (ADR-538; before it, `--prompt` ran
   design turns here). The guidance and new-project `ARCHITECTURE.md` scaffold teach
   purchased hardware placement: publish catalog bodies and place purchased
   instances as separate `assembly.component` values, separate from printed
   solids. Transformed catalog bodies may serve as clearance cutters without
   implying another purchased part. Review the script alongside placed inventory;
   totals cannot identify hardware fused into other solids (ADR-243). This is
   authoring guidance, not evidence that an agent followed it. Existing project
   documents remain owned by the project and are never overwritten by scaffolding.
2. With `--set NAME=VALUE`: `cadex params --set policy_on=0 --set …
   --out DIR/sweep` — the iterate step, the switch blanked so the change
   is accepted and the bundle exported at its new digest.
3. `cadex train --out DIR/train --put` with the trainer's flags carried by
   name (`--iterations`, `--envs`, `--seed`, `--label`, `--name`,
   `--task`, `--timeout` (the trainer's own bound, not the walk's — see
   `--leg-timeout` below), `--trainer-python`, and the warm-start triple
   `--init-from`, `--init-from-parent-task`, `--init-from-task-change`) —
   and `--remote` / `--allow-cpu`, which go to this leg and nowhere else.
4. **The digest edit**, which was the one leg that was a person's: the
   walk reads the script (`cadex script`), rewrites the two string
   literals of its one `assembly.policy(task, weights="…", sha256="…")`
   call to the stored policy's name and sha256 — nothing else in the
   script changes — writes it to `DIR/script.py` and lands it with
   `cadex script --set`. A script without the iterate convention is
   refused at exit 3 with the convention named, on any of **three**
   counts — no `policy_on=num(...)` parameter, not exactly one
   `assembly.policy` call, or that call not carrying `weights=` **and**
   `sha256=` as inline string literals. The third is the one an
   agent-authored script fails by accident: factoring the two strings out
   into module constants (`weights=POLICY_WEIGHTS`) reads better and is
   refused, because the edit is a literal rewrite and the walk does not
   guess where a policy belongs in a script it did not write. Measured on
   nt3 against a script the design turn wrote unprompted; the authoring
   contract in the guidance (`cli/cadex_cli/guidance.py`, ADR-538) now
   teaches both the switch and the two inline literals, and `test_walk.py` rewrites the example it
   teaches to keep the two halves agreeing.
5. `cadex params --set policy_on=1 --out DIR/rollout` — the verify and
   the rollout, the trace exported.
6. The review: the trace's `policy` block — `total_reward`, the per-term
   `reward_totals`, the policy's sha256 — in the envelope under
   `walk.review`, and as **`DIR/review.json`** (`cadex-walk-review-v1`:
   the same numbers, the trainer's receipt figures, the parameters the
   rollout ran at, and the legs with their exit codes and timings, paths
   relative to `DIR`). Run the walk **under the project** — `--out
   <project>/runs/<name>` — and the review is in the project: the walk's
   own commit includes that file, `docs/inventory.md` and `docs/clearance.md`, after the legs' commits.
   The `gait` block (ADR-409) judges a model with a free-floating body on
   what total reward cannot show: the body's tilt from its starting
   attitude (tipped at 45°), its unwrapped heading (turned at 90°), a
   termination in the rollout, and the median of the trainer's mean
   episode length over the last 50 iterations against the horizon (under
   90% is "ended early"; ADR-433 — the last iteration alone can close on a
   horizon boundary and count every time-limit truncation). Any finding makes
   `walked` false; the walk still succeeds, and its last note and the
   dashboard's `rollout gait` row say the robot did not walk. Planar travel
   and speed are reported, never judged. A model with no free body, or
   several and no single observed one, is declined with the reason.
   The `inventory` block saves `available`, `component_count`, `catalogued_count`
   and a project-relative `path` to the **latest** `docs/inventory.md`.
   Later inventory calls overwrite that report's revision and named rows;
   the old inventory block retains counts but no named rows or revision.
   Read the report at the walk's Git commit for its historical inventory.
   Unavailable assemblies have zero counts; inspection errors fail the command.

   Clearance reuses the accepted pair reader without another rebuild (ADR-238).
   Its `clearance` block records availability, revision, initial-solved-pose
   scope, thresholds (0.1 mm minimum distance, 1e-6 mm³ maximum volume),
   pairs checked, offending pairs with labels/catalog ids, unknown pairs and
   their errors, counts, and project-relative `docs/clearance.md` path.
   Unavailable counts are null; unknown measurements remain null with their
   errors, never clear. An offending pair is a finding, not a walk failure;
   inspection failures fail the command. A walk-specific `PROGRESS.md` row
   records comparable offending/unknown/checked counts at these thresholds,
   the offending count **with the change against the last walk row that
   carried one** (ADR-271) — the number a geometry iterate answering a
   clearance finding turns. Unknown and checked counts stay plain: they say
   what the check could reach, not what it found.

   The block also carries `bounds_check` (ADR-248): the same pairs re-read
   against the render snapshot's independently placed world bounds, two
   inequalities per measured pair — a distance is at least the boxes' axis
   separation, and a common volume fits inside the box overlap. It reports
   `pass`, `fail` or `unavailable` with the comparison and failure counts at a
   1e-3 mm box padding, and a `fail` is said in the run notes without failing
   the walk: a disagreement is the review contradicting itself, not a design
   finding. It is agreement between two paths, **not** validation of either.
   Its output label, shared with the project commit subject, is relative to
   the project when `--out` lies inside it, otherwise just the output basename
   (ADR-246). Absolute machine paths do not enter that label; the project
   architecture scaffold documents this convention.
   This is neither swept-motion coverage nor large-assembly qualification.

   The `motion` block says whether the mechanism actually moved, in **two
   channels** (ADR-259). Per component, from the same rollout trace the
   numbers came from: the per-axis `position_range_mm`, the
   `max_displacement_mm` from the reference pose, and the
   `max_rotation_deg` swing — `2·acos(|q₀·q|)` — away from the reference
   orientation. The reference is the **first solved frame**, and only
   solved frames are counted: frame 0 of an assembly trace is the pose the
   solver was *given* (`frame_kind: "input"`, `nominal_time_s: null`), so
   both documented examples report 26 counted frames out of 27 raw ones,
   with `frames_counted`, `frames_excluded` and `excluded_frame_kind`
   saying so. Placements are absolute world poses, not offsets, so every
   figure is a difference against that first solved pose.

   Both channels every time, because one alone is a wrong answer rather
   than a partial one: `examples/lifecycle/hinged-arm` travels **0.0000 mm
   and rotates 178.8334°**, and a millimetre-only report would call a
   working revolute rig motionless, while `linear-carriage` travels
   **4739.3783 mm and rotates 0°**. The block names `largest_translation`
   (in millimetres) and `largest_rotation` (in degrees) and **declines to
   rank them against each other** — its `ranking` field says so — because
   millimetres and degrees do not compare, and a scale that made them
   compare would put a carriage free-falling on an ideal guide above a
   swing arm doing its job. Travel is a fact about one rollout, never a
   score, and two projects' travels compare no better than their rewards
   do. A trace whose frames are all identical reports **zero** travel, not
   unavailable; a trace with no frames, no solved frames or no placements
   is `available: false` with a `reason`. The walk's `PROGRESS.md` row and
   run notes carry both figures, in one spelling — `motion travel_mm N on
   <component>, travel_deg N on <component> over N solved frame(s)`. The
   unit lives in the label rather than after the number because that is
   the shape `previous_numbers` reads back off a row (ADR-260): a later
   walk of the same project writes each channel with its change against
   the last walk that carried it, `travel_mm 103.7 (Δ +0.419 vs 4b0a1c2d
   at 103.3) on carriage`. The change is measured against the row **as
   written**, four significant figures and all, because the row is the
   record; the raw float is in the run's `review.json`. **A delta is not a verdict.** The carriage
   iterate held its travel at 103 mm while its `total_reward` fell from
   3.296 to 2.760, and the row now says both; which of the two mattered is
   the agent's to decide. Before ADR-260 no walk row carried a delta
   for any figure — `_record_progress` never passed `previous` on the walk
   branch — so the reward deltas on a walk's **train** leg row and the
   travel figure on its **walk** row could not be read together.

   The `documentation` block reads the note convention back (ADR-256). The
   walk parses the MJCF it trained on — `DIR/train/<name>-model.xml` — and
   takes each declared section as a note subject: an `<actuator>` section
   with children asks the project for `docs/actuators.md`, a `<sensor>`
   section for `docs/sensors.md`. It carries the project's agent-authored
   notes (`notes`, the CLI's own generated reports excluded), the subjects
   the model declares (`expected`), the ones with no note (`missing`), and
   the `model` it read, relative to `DIR`. A missing note is a finding for
   the agent's next session, never a walk failure, and the CLI never
   writes the note itself: what drives a joint and what a sensor measures
   are the agent's to say. A run
   that exported no model declares nothing and reports nothing. The walk's
   `PROGRESS.md` row carries the same finding, as `docs notes N, none
   missing` or `docs notes N, no <subjects>`.

   The same review session rebuilds standard display once and snapshots it
   before inspection requests. The `render` block carries availability,
   accepted revision and digest, front/top/right/iso views and the hero, approximation and
   limits, acquisition/render seconds, and project-relative image/summary paths
   under `review/render/<accepted-revision>/`. These SVG previews (embedded lossless CPU images) stay local under the
   default ignore rules; the walk commits the review and project docs.
   Rendering or revision mismatch failures fail the walk; retained files from
   an older run are never reported as current success. `walk_seconds` measures
   the whole entry point through review, excluding its final progress/commit.
   The `section` block uses the same accepted snapshot for a world XZ cut
   whose offset is **derived from that snapshot's own bounds** (ADR-267),
   not fixed: the candidates are each object's bounding-box centre on the
   cut axis plus the whole geometry's, **each with two quarter-span
   siblings** (ADR-270). **Every candidate is cut, and the one that cuts
   the most objects is the one written** (ADR-273): an available cut beats
   an unavailable one whatever the count, and the bounds ordering — most
   objects' bounds crossed, then centres before siblings, then nearness to
   the overall centre — survives only as the tiebreak and as the order the
   sibling planes are dropped in when an assembly has more of them than the
   work bound allows. **No object's own centre plane is ever dropped**: on
   `ot4-swing2` a dense mount cluster filled all eight places the old bound
   allowed and the four planes cutting the moving arm were never cut at all.
   `offset_mm` is the chosen plane, `offset_source` is `derived`,
   `offset_candidates_mm` is the ordered list it came from, and
   `objects_cut` is how many of them came back with contours — which the
   SVG label also carries, because a section is as much a claim about what
   it did not reach as about what it shows. The walk adds `section.missed_objects`
   (ADR-277): keyed by published object identity, each uncut object carries its
   section status and `moved` (true, false, or null for unknown). Exact matches
   to rollout component identities carry translation in mm and rotation in
   degrees; either nonzero channel means movement. Labels and shared source
   shapes never substitute for instance identity. Missing traces, unmatched
   identities and incomplete travel remain unknown with a reason. This join
   lives in the walk review only; the standalone section summary stays geometric.
   A plane reaching every part of a spread-out mechanism may not exist. A constant
   offset cuts whatever happens to lie on it and reports `ok` while a part
   is missing from the drawing — and a centre alone is not enough, because a
   centre is the plane a part is most likely to be symmetric about and a
   tessellation puts a seam exactly there: the best-coverage candidate is
   systematically the one the plane-contact refusal rejects. The siblings
   are what turn that seam into a few millimetres of offset rather than a
   missing part. `cadex section --plane XZ` derives the same
   way when `--offset-mm` is omitted (ADR-275); given one, it cuts there and reports
   `offset_source: explicit`. It carries
   status, availability, revision/digest, plane/offset/units, approximation,
   limits, acquisition/section timings and project-relative `path` (SVG) and
   `summary_path` (JSON). Empty cuts remain available with no contours;
   unsupported cuts remain unavailable with reasons. Section errors and
   rollout revision/digest mismatches fail the walk, preserving old files
   without reporting them as current success. These are initial-pose
   tessellation cuts; they do not prove motion clearance. Acquisition timing
   is shared with rendering (count it once); section timing covers contour
   generation, excluding SVG serialization and writes.

Before the first leg, the JSON envelope's `walk.engine_source_comparison`
and stderr report `match`, `different`, or `unavailable` (ADR-251). This
compares top-level Python file bytes against `src/Mod/cadex`: for a dev
engine, the comparison directory is `Mod/cadex` beside the binary's `bin`
directory; for an explicit/environment payload it is the manifest's module
directory. Counts cover all compared names; changed, missing and extra name
lists each stop at ten. Missing directories, empty sets or unreadable files
mean unavailable evidence. Differences do not establish which copy is newer,
and matching Python does not certify binary or loaded-module provenance.
The report does not refuse, rebuild, or change engine selection.

**Shared mode artifacts** (paths relative to the project, with
`DIR = runs/<name>`). This table applies to headless local training
and `--remote`; only the training location changes.
The scaffold's `## Training` section carries this same path convention.

| Leg | Artifact in every mode |
|---|---|
| Design / assembly | `script.py`, `ARCHITECTURE.md`, `DECISIONS.md`, `docs/<subject>.md` |
| MJCF / task / training | `runs/<name>/train/` (model, task bundle, returned policy) |
| Store / declare | `assets/<name>.cxpolicy`, `runs/<name>/script.py` |
| Verify / rollout | `runs/<name>/rollout/` (including the simulation trace) |
| Review | `docs/inventory.md`, `docs/clearance.md`, `runs/<name>/review.json` (inventory, clearance and motion summaries with project-relative report paths), `review/render/<accepted-revision>/{front,top,right,iso}.svg`, `hero.png` and `summary.json`, `review/section/<accepted-revision>/XZ-<derived-offset>/{section.svg,summary.json}`, `PROGRESS.md` (numbers; remote training rows marked `(remote)`) |
| Record | `runs/<name>/run.json` (the run record, below) and `runs/<name>/project-docs/` (the project documents as they stood when the run was recorded) |

### The run record (ADR-285)

`review.json` carries a walk's numbers; **`run.json`** carries its
identities, so a reader who arrives later — a person, or a review client
with no engine — can tell *which* model, parameters, task and policy a run
belongs to without rebuilding anything. Schema `cadex-run-record-v1`,
written by `cadex walk` as `running` when the walk starts, so a walk that
is killed leaves a file saying it never finished; as `running` again before
the train leg when the sweep has moved the accepted revision;
then `ok`, `failed` (with the leg and its error) or `pending` (a detached
train leg launched, nothing collected) when it ends. Each write replaces
the file. Before training starts, the walk freezes the accepted assembled view,
parameter values/specs and project documents in `training-view.json`,
`training-view/*.stl` and `project-docs/` (ADR-291). Subsequent status writes
reuse these documents and specs; design changes do not replace them. Retain
and copy these files with the entire run directory. If another design is
accepted between retention and the train leg, training refuses and asks for
a new walk. Runs that failed before
reaching training retain the documents from their last status write.

`cadex params` requests standard tessellation as part of parameter acceptance
(ADR-293). This includes the sweep in `cadex walk --set`: its accepted assembled
model is available to the snapshot reader before training starts, without an
extra render or rebuild. Previously recorded missing snapshots remain missing;
later geometry is never used to backfill them.

What it carries, all from what the manifest and the legs reported and
nothing re-derived:

- `model`: the `accepted_revision` and `digest` the run is tied to, and
  `identity_source` saying where they came from. At walk start they are
  read from the project manifest (`project manifest (script.json) at walk
  start`), so the record names the model being trained **before the first
  telemetry sample lands**; every later leg that reports an identity
  replaces it (`sweep leg envelope`, `train leg
  envelope` — the revision the trainer was given — `declare leg envelope`,
  `rollout leg envelope`). A run that fails keeps the last identity it
  learned, so a failed or interrupted run is still the run *of* a revision.
  `not reached` appears only when there was no manifest and no leg spoke.
- `params`: the `values` the rollout ran at, and the `specs`: from the
  manifest at walk start (and again before the train leg, when the
  sweep moved it), then read with `inspect scope=script` **at the
  accepted revision** while the engine held it during the review, with
  `specs_source` saying which, or saying `unavailable: …`. A historical
  run is never re-run to learn what its parameters meant.
- `task` (bundle, sha256, model XML), `training` (`requested`: the flags
  the walk was given; `receipt`: the trainer's named figures), `policy`
  (name, sha256, `asset`), `rollout` (trace, seed, total reward),
  `legs` (as `review.json`, without argv), and `videos` — an empty list
  until a policy video is recorded; empty means *none recorded*, not
  missing. **`policy.asset` (and `project_artifacts.policy`) is
  `assets/<name>` only when the project store held that file, with the
  recorded digest, when the record was written** (ADR-326); a walk that
  failed between training and its `--put`, or a bounded driver that never
  ran `cadex asset --put`, records `null` there. The trainer's own copy is
  `artifacts.policy` (`train/<name>`, run-relative) when it is on disk. A
  named locator is a fact about the disk at record time, never an intention.
- `artifacts` (run-relative) and `project_artifacts` (project-relative):
  every retained file the run refers to. **Every path is relative** to the
  run directory or the project root; a file outside both is recorded as
  `null`, never as an absolute path, so the record reads the same from a
  copy of the project.
- `project_docs`: `ARCHITECTURE.md`, `DECISIONS.md`, `PROGRESS.md` and
  `docs/*.md` copied into `runs/<name>/project-docs/` with their sha256s,
  bounded at 32 files of 256 KB (anything past that is listed under
  `skipped`), so the specs and decisions a run was made under stay
  readable after the design moves on. `PROGRESS.md` is copied before this
  run's own row lands.

The deleted shell's Training editor had a second, smaller reader of the same files (ADR-450); it went with the shell (ADR-498), and this reader is the only one.

**The reader** is `cadex_cli.review_record.read_project_review(root)`: the
project's accepted identity now (read-only, from the manifest, and
`available: false` with a reason when there is none), its documents and
decision headings, and every directory under `runs/` — oldest recorded
first — with each reference resolved against the disk. It **only reads**:
no engine, no rebuild, no re-acceptance. Each run carries `relation`
(`current` when its recorded revision is the accepted one now,
`historical` otherwise, `unknown` when either side is unavailable),
`outcome` in words (a `running` record reads `started and never finished:
still running, or interrupted`, because the reader cannot tell which), and
`problems`: references that are recorded but missing, snapshot pages whose
digest no longer matches, references that **escape their base** by
`..`, by an absolute path or by a symlink — those are reported and never
opened, which is what lets a review client serve a project's permitted
artifacts and nothing else — and, for an `ok` run, a policy the trainer
retained under the run's `train/` that the project store does not hold,
with the one command that stores it (ADR-327): a completed run whose only
policy copy is the trainer's is a retention gap, not a finished run, and it
stays listed until `cadex asset --put` has run — with no record rewrite. A
`failed` run in the same state is not listed; its policy-store row carries
the advice and the failure is the problem. A run from before records existed is read from
its `review.json` and labelled `unrecorded`, with its identity taken from
the rollout leg's envelope fields and nothing inferred beyond that.

Each run also carries **`policy_store`** (ADR-326): where its policy bytes
are *now*, read on every poll rather than from the record's locator.
`state` is `stored` (the store holds `assets/<name>` with the recorded
digest — a `cadex asset --put` run after the record counts, with no record
rewrite), `digest mismatch` (the store holds other bytes under that name),
`unstored` (no store copy; when the record named one that is gone,
`problems` also says `project_artifacts.policy: missing`), `refused` (the
recorded locator escapes the project) or `none` (no policy recorded).
`retained` is the run-relative path of the trainer's copy when it is on
disk — for records older than ADR-326, which name no `artifacts.policy`, the
reader resolves it at the trainer's one fixed place, `train/<name>`, only
when it exists — and `next_action` is the command: `cadex asset --project
<project-dir> --put <project-dir>/runs/<run>/train/<name>` to keep it, or a
new `cadex walk --out runs/<new-name>` when nothing is retained;
`store_command` is that store command alone (with `--name <other>.cxpolicy`
on a digest mismatch), `null` once the policy is stored or when nothing is
retained, and is what the `problems` entry above carries. The command
names the project directory twice on purpose: `--put` resolves against the
working directory and `--project` defaults to `./.cadex`, so a bare `cadex
asset --put runs/…` run *inside* the project directory creates a nested
project there instead of storing into it (the first live probe of ADR-326
did exactly that). Store digests
are verified on files up to 4 MiB through a stamp-keyed cache of their own,
so a polled page never re-hashes an unchanged file and never waits behind a
cold video verification.

**Policy lineage** is `cadex_cli.review_record.policy_lineage(root, run)`
(ADR-316): where a run's policy came from and which other runs play it, from
retained identities and never from run names. A run's recorded
`policy.sha256` is matched against the bytes every run keeps under its own
`train/` (files up to 4 MiB inside `runs/<run>/train`); the run holding them
is the `origin`, `final` when its own record carries that digest as its
policy, `checkpoint` with the iteration
when its telemetry lists it, `retained` when neither says so, and the
earliest recorded holder wins with the others under `also_retained_by`. The
record's `training.requested.source_run` is reported beside it with
`source_agrees` (`None` when no source was recorded, `False` when the record
names one run and carries another's policy — shown, not reconciled), and
`playbacks` lists every other run whose policy the same origin retains, with
its kind, relation, status and video count in record order. It hashes
`runs/*/train` once per call. The dashboard's `GET /api/policy-origin/<run>`
uses this reader on selection, recorded policy/training/status changes, or
**Check again**, never on ordinary telemetry polls (ADR-319). Its run-panel
snapshot shows the byte-resolved run, kind and checkpoint iteration, the
declared source, and a highlighted **SOURCE-NAME DISAGREEMENT** when they
conflict. Unresolved and failed checks are labelled; Check again retries or
re-reads changed retained files. Selecting another view discards late replies.
The checkpoint list still describes where its declared telemetry references
resolve, separately from this policy identity check. Every run directory, `train/`, policy file and `progress.json`
it touches is resolved against the **project root** before it is read or
hashed (ADR-317): a `runs/<name>` that is itself a symlink out of the
project would pass a check anchored at that already-escaped directory, so
it is listed as unreadable with `run: directory escapes the project
directory`, contributes no bytes to the index and has no telemetry read —
and the same anchor applies to every run record the reader lists or the
dashboard serves. The dashboard's model and mesh routes apply it too
(ADR-318): a run whose directory escapes the project answers
`/api/model/run/<name>` with `available: false` and reason `run directory
escapes the project directory` before its retained training view or
rollout is opened, and `/mesh/run/<name>/<part>.stl` serves only a file
that resolves inside the project root. The video checker beside the fresh-project probes uses
the lineage to find a video's training run and an older sibling without a
naming convention.

**Collision proxies (ADR-333).** Every model manifest carries a `collision`
block: the proxies the simulation collides with, parsed from the MJCF the
view already retains at its own identity — a run's recorded `model_xml`
export (refused with `digest mismatch` when the rollout trace's policy
receipt names another model), the accepted attempt's `assembly.mjcf` output,
or nothing with the reason. Each geom is listed in its component's frame in
mm and xyzw with MuJoCo's size meaning (half-sizes for a box, radius and
half-length for a capsule or cylinder), inline mesh assets as vertices and
faces, planes and unknown types listed but not drawn, and contact-free geoms
counted as `skipped`. The page draws them only while **show collision
geometry** is on (`#show-collision`, disabled with the reason when none are
retained), as outlines over the solids that follow the solids' poses; the
model status line ends `· showing: tessellated solids` or `… with collision
proxies` (`data-showing`), and each component's line says what it has
(`collision: 1 box`). A recording never contains them.

A project whose first design never landed (as when a `walk --prompt` design
turn was refused, before ADR-538) has scaffold documents and no accepted
manifest or run record. The dashboard shows missing geometry and a next CLI
action.
See the [fresh biped evidence and retry procedure](HEADLESS-BIPED-REVIEW.md).
The whole recorded lifecycle of that biped — its D1–D8 evidence index, every
retained run identity and the common-seed comparison of its designs — is
[`docs/probes/reed-lifecycle/README.md`](probes/reed-lifecycle/README.md).

**Retention and copying.** The record and the snapshot are small and are
committed with the run when `runs/<name>/` is inside the project's own
repository; the trace, bundle and checkpoints beside them fall under the
default ignore rules (below) and stay local. Copy a project with
`cp -r`/`rsync` of the whole directory, `runs/` and `review/` included: the
record's references are relative, so the copy reviews as the original did,
and a copy that omits `runs/<name>/rollout/` or `review/render/<revision>/`
reviews with those references listed under `problems` rather than silently
resolving to another project's files. Deleting a run directory is deleting
its history; nothing rebuilds it.

For a consistent headless copy, first let CLI authoring, training and video
rendering finish; copying a directory while its writers commit files is not an
atomic snapshot. With the destination absent, copy the entire project (including
hidden files and ignored artifacts), then serve that copy independently:

```bash
cp -R ~/cadex-projects/biped ~/cadex-projects/biped-copy
./cadex review --project ~/cadex-projects/biped-copy --port 8766
```

The [real Wren copy lifecycle](probes/wren-fresh/COPY.md) supplies an executable
engine/browser check with the original path unavailable throughout a copy-only
parameter edit and two restores, plus retained model/curve/video checks on the
then-persistent operator URL and a second server.
The [Lark copy lifecycle](probes/lark-fresh/COPY85.md) repeats it on the third
fresh project with the same driver made project-agnostic: the default run and
the parameter changes are arguments (`docs/probes/lark-fresh/copy_lifecycle.py`).
The [Lark interruption probe](probes/lark-fresh/INTERRUPTION86.md) then retrains
the copy (an interrupted attempt, a completed one and its video) with the same
project-agnostic treatment (`docs/probes/lark-fresh/interruption.py`) and checks
the original's inventory again afterwards.

The copy test in `cli/tests/test_review_lifecycle.py` exercises this command,
opens both projects in headless Chromium, changes the copy's accepted fixture,
and verifies the source stays byte-identical. With the original path unavailable,
a fresh page still reads the copy's historical model, parameters, three metric
histories and playable/downloadable video. It checks retained artifact hashes.
This test uses synthetic fixtures. The separate
[real Reed copy lifecycle](HEADLESS-BIPED-REVIEW.md#independent-real-project-copy-d7)
records a whole-project copy, physical revision and bounded GPU retraining,
then engine reopen and three-design browser/video review with the original
path unavailable and every original file unchanged. Copying an active project
and external symlink targets are not covered by this procedure; project artifacts must be retained within the project directory.

`cli/tests/test_walk.py` checks local/remote artifact parity through policy
verification and rollout using a local CPU stand-in for the dispatcher.
It runs no remote command.

A leg that fails stops the walk there, with the leg's name and its error
in `error` and the legs that ran under `walk.legs`; the exit code is the
leg's for a usage error or a refusal, `1` otherwise. Child legs record reward/delta rows
(ADR-194); a successful walk adds the clearance review row described above
(ADR-238). A failed leg leaves earlier rows intact but adds no walk review row.

**Every leg is bounded in wall clock** (ADR-261). `--leg-timeout SECONDS`
(default 3600, `0` for no limit) stops any one leg that runs longer and
fails the walk there, through the same path a refusing leg does: the leg
reports exit **124**, `error` names the leg and the flag, and the walk's
exit is `1`. The stop is a **subtree kill** — the leg runs in a session of
its own and is sent `SIGTERM`, then `SIGKILL` to the group five seconds
later **whether or not the direct child died on the term** — because the
thing that hangs is usually not the child `cadex` but the trainer under
it, and a grandchild that ignores `SIGTERM` outlives its
parent. The full five-second cleanup grace remains even when the direct
child exits immediately. The group id is read while the child is alive, so it stays
addressable after the child is reaped, and the walk waits at most ten
seconds to drain the stopped leg's stdout: a pipe still held open past that
is abandoned rather than allowed to hang the walk the bound was there to
save. `SIGINT` and `SIGTERM` to the walk are relayed to the running leg's
session, so Ctrl-C still reaches it. The envelope carries
`walk.leg_timeout_s` and `walk.train_leg_timeout_s`.

`--timeout` and `--leg-timeout` are **not** the same bound. `--timeout` is
the *trainer's* internal limit, forwarded into the train leg's argv and no
further; `--leg-timeout` bounds the child commands the walk itself runs. The
train leg gets `max(--leg-timeout, --timeout + 300 s)`, so a long training
run asked for by name is never shot by the walk's default.

**Retry after failed retraining.** The accepted sweep stays applied with
`policy_on=0`. Previous policies, run artifacts and progress rows survive;
partial trainer output is not stored or declared. Use a fresh `--out` and
policy `--name`, warm-start from the last successful policy and parent task,
and declare any task change. Do not pass `--set policy_on=…`: the walk owns it.
The real-engine regression in `cli/tests/test_walk.py` runs two successful
CPU walks, injects trainer exit 7, then retries the retained `lift_weight=0.0003`
sweep with this command (`P` is the test project):

```bash
JAX_PLATFORMS=cpu ./cadex --project "$P" walk --out "$P/runs/walk-recovered" \
  --name job3.cxpolicy --init-from "$P/runs/walk-2/train/job2.cxpolicy" \
  --init-from-parent-task "$P/runs/walk-2/train/job-task.json" \
  --init-from-task-change "lift weight increased from 0.0002 to retained 0.0003" \
  --iterations 1 --envs 4 --timeout 600 --json
```

The test pins preserved artifacts/history, verified policy, all four reviews and
last-success comparison references. The [measured rehearsal](../.hypergraph/graph/record/dusty-vale-2809.md)
reported reward −83.7819 versus −55.3476 under changed weights: recovery, not improvement.

The same entry point also runs the vertical linear carriage in
`examples/lifecycle/` (ADR-203), with a real slide joint and a force motor.
That directory gives reproduction commands and both projects' `PROGRESS.md`
numbers at 1 iteration × 4 environments. Rollout reward/step is the verified
trace's `total_reward / step_count`; the trainer's final batch mean is a
separate metric. Force and torque effort penalties have different units,
so these baselines prove coverage, not a ranking of mechanism quality.

**Model-free carriage iterate rehearsal (2026-09-08).** On the durable
`ot4-carriage` project, the unchanged public entry point ran:

```bash
JAX_PLATFORMS=cpu ./cadex walk --project "$PROJECT" \
  --out "$PROJECT/runs/iterate-1" --set carriage_wid=80 \
  --name lift_iterate1.cxpolicy --iterations 5 --envs 16 --seed 0 \
  --timeout 600 --json
```

Width increased from 70 to 80 mm; task bundles differed only in `model`,
keeping the objective, episode, observations and randomisation fixed.
Both verified rollouts used seed 7 and 200 steps (4 s): reward
**3.296298 → 2.760187** (delta **-0.536111**), with the comparison written
into `PROGRESS.md`. All 21 baseline files, including the policy, retained
their bytes. All four legs and review passed; the four review eyes check
only the initial pose, not swept motion or printable fit. One cold training
seed at toy scale does not establish a general design ranking.

See [ADR-251](DECISIONS.md#adr-251--the-walk-reports-enginesource-differences-before-its-first-leg-2026-09-08)
and the [immutable rehearsal record](../.hypergraph/graph/record/mellow-quartz-8093.md)
for timings, policy witness, component volumes and project commit evidence.

**A third mechanism, and what its second coordinate measured (2026-09-08).**
The unchanged entry point also ran a *quill lift* rig on the durable
`ot4-quill` project: one **cylindrical** joint — a slide and a hinge on the
same axis — driven by a **position servo on its linear coordinate**, which
is the fourth and last `(kind, motion)` pair the engine derives an action
range for. A **velocity** actuator cannot be the third variable: the engine
refuses one at `action_range_underivable`, because a joint states position
limits and nothing in an assembly states a speed. Exit 0 in 10:53 at 5
iterations x 16 envs, seed 0, `total_reward` -74.79 over 200 steps. The
motion block read **`travel_mm 20.28`, `travel_deg 0` on the same
component**: the joint offers both channels and the rollout used one, since
gravity exerts no torque about a vertical axis. A zero in a channel is a
fact about that rollout, not a missing measurement, which is why both are
always written. No delta rendered on that row, correctly — a project's
first walk has no previous row carrying either label. The clearance eye
returned its first offending pair on an agent-authored design: `housing`
against `quill`, verdict `intersection`, 960 mm3 of common volume. That one
is deliberate and the project says so itself — its ADR-005 records that the
shaft is modelled inside a solid bore cylinder and that the joint, not
contact, constrains the quill — so the report is a known choice read back
rather than a defect found. The walk still exits 0, as the table above says
it should: the report was written, and reading it is the next design turn's
job.

**Quill parameter-only iterate (2026-09-08).** With `PROJECT` pointing at
that same project, the bounded, unchanged entry point ran:

```bash
JAX_PLATFORMS=cpu ./cadex walk --project "$PROJECT" \
  --out "$PROJECT/runs/stroke60-iterate29" --set stroke=60 \
  --name quill_stroke60_29.cxpolicy --iterations 5 --envs 16 --seed 0 \
  --timeout 600 --leg-timeout 120 --json
```

Exit 0 in 24.61 s, peak process-tree RSS 1.98 GB (0.2 s monitoring;
2.9 GB / 850 s external cutoffs). All four legs and four review calls
succeeded; the 56-file engine/source comparison matched. Actual parameters
differ only in stroke, 40 → 60 mm. Exported task JSON differs only in model
metadata and the action upper bound, 40 → 60 mm: reward expressions and
weights, observation units, termination, randomisation, disturbance and
4 s / 200-step horizon are identical. Both verified rollouts use seed 7.

| Measurement | Baseline | Stroke 60 | Exact delta |
|---|---:|---:|---:|
| Rollout total reward | -74.791975 | 175.487211 | +250.279186 |
| Quill travel mm | 20.283552 | 30.078469 | +9.794917 |
| Quill travel degrees | 0 | 0 | 0 |

The reward delta lands in the rollout's `params` row; both travel deltas
land in the `walk` row of `PROGRESS.md`. Its displayed **+9.798 mm** uses
the baseline row's rounded **20.28**, not the full-precision review value.
Trainer reward/step fell from -0.579622 to -1.019691; it measures a different
batch. The target remains 30 mm, now the midpoint of the action range, so
near-zero normalized actions already command it. Geometry and action scaling
changed together; this cold single-seed toy run cannot establish significance
or better control. The housing/quill intersection remains 960 mm³ in the
initial pose; the XZ section misses the quill. All 19 baseline run files
retained their bytes. New generated artifacts remain local after a forward
project commit removed outputs that the CLI had automatically staged.

**Fixed-geometry quill seed reference (2026-09-08).** The same project,
already at stroke 60, ran the command above without `--set`, using fresh
`runs/stroke60-seed0-33` and `quill_stroke60_seed0_33.cxpolicy` names.
CPU 5 × 16, training seed 0, rollout seed 7, trainer timeout 600 s and
leg timeout 120 s; the same external 0.2 s watchdog retained its
2.9 GB / 850 s cutoffs. Exit 0, 24.835810 s wall (24.685678 s reported
walk), peak tree RSS 1,986,134,016 bytes. Trainer time 3.773088 s,
reward/step -1.019690990448, witness error 2.092e-08.

The reference total reward is **175.487211145051**, travel
**30.078469436328 mm / 0 degrees**, over 200 steps / 4 s.
Parameters, exported MJCF bytes and full task JSON match the stroke-60
iterate; only policy filename and digest changed in the script. Recomputed
comparison hashes match: objective `v1:ddee1f6a0bae7c4753c06a17fa09dd3db9799de30d823c4e4586e41868a937dc`,
actions `770b4e2f0899853fed23b8727ea08f607ceef3c383189357f27c02179cc30882`.
Both seeds and identities are recorded in project `PROGRESS.md`; prior-row
identity remains `unavailable (legacy row)`.

All four render views exist; the XZ section still misses the quill;
inventory lists two uncatalogued components; clearance names the same
960 mm³ housing/quill intersection. The engine/source comparison matches
56 Python files. All 48 earlier run files retain their bytes. Explicit
root exclusions after the policy negation kept every new run, stored policy
and review output out of project commits; historical tracked output stays
untouched. This is the seed reference, with the 30 mm action-midpoint
confound unchanged, not evidence of learned improvement. Seeds 1–3 were
the selected continuation, measured below.

**Fixed-geometry seed continuation (2026-09-08).** Seeds 1, 2 and 3 each
completed all three walk legs and four review calls. The command is the
reference command with `--seed N`, `--out "$PROJECT/runs/stroke60-seedN-34"`
and `--name quill_stroke60_seedN_34.cxpolicy`, substituting N = 1, 2, 3.
CPU 5 iterations × 16 environments, rollout seed 7, trainer timeout 600 s,
leg timeout 120 s and the 0.2 s tree-RSS watchdog (2.9 GB / 850 s) were fixed.

| Training seed | Total reward | Travel mm | Travel deg | Wall s | Peak tree RSS bytes |
|---:|---:|---:|---:|---:|---:|
| 0 | 175.487211145051 | 30.078469436328 | 0 | 24.835810 | 1986134016 |
| 1 | 175.935971673601 | 31.421759939733 | 0 | 23.783088 | 1994547200 |
| 2 | 170.952826823611 | 31.360988060147 | 0 | 24.625217 | 1986662400 |
| 3 | 172.081298535925 | 31.085486620484 | 0 | 25.470796 | 1997832192 |

Comparison references are `runs/stroke60-seed0-33/review.json` and
`runs/stroke60-seed{1,2,3}-34/review.json` in the same quill project.
Across these four seeds, reward ranges **170.952826823611–175.935971673601**
(span 4.983144849990), translational travel **30.078469436328–31.421759939733 mm**
(span 1.343290503405 mm), and angular travel stays **0 degrees**.
These are descriptive ranges, not significance, a winner or learned
improvement: the 30 mm target remains the action midpoint, which near-zero
normalized actions already command. No further seeds follow this measurement.

Every exported MJCF and full task JSON is byte-identical to seed 0; the
full parameter map, objective and actions match the reference hashes above.
Both training and review comparison metadata carry the requested training
seed, and review carries rollout seed 7. Script changes are confined to
policy filename/digest. Project PROGRESS rows retain explicit previous
comparison identities; rounded row deltas are not the full-precision ranges.
Trainer durations for seeds 1/2/3 were 3.628307/3.878131/3.883964 s;
reward/step -1.016377091408/-1.313315391541/-1.432229399681 and witness
errors 2.700e-08/2.926e-08/3.163e-08. These training batch rewards differ
from the verified 200-step, 4 s rollout totals in the table.

All named render files and section/inventory/clearance outputs exist locally.
The XZ section at 3.125 mm still misses the quill -- the measurement that
ADR-267 later answered by deriving the offset -- inventory has two
uncatalogued components, and initial-pose clearance still reports the
960 mm³ housing/quill intersection with no unknown pairs. Each run verified
all preceding run files unchanged (75/102/129 files respectively); prior
policy hashes, script history and unrelated tracked content are preserved.
Fresh root output and policy exclusions follow the default policy negation;
new run/policy/review paths are absent from the index and committed trees.
This is additional evidence for the existing headless walk and review
criteria, with no runtime, entry-point or project-scaffold behavior change.

*The four dated runs below (`ot4-crank48`, `ot4-mix52`, `ot4-mix55`,
`ot4-cart`) began with a design leg, `walk --prompt`, that ADR-538 removed:
today the person's own agent designs through `cadex mcp` and the walk starts
from the project it left. They stay as evidence of what was measured, not as
commands to run.*

**Fresh crank-slider attempt (2026-09-08, iteration 48).** A new
`ot4-crank48` project (only output exclusions existed before invocation)
was prompted for a grounded frame, position-servo revolute crank, coupler
and prismatic slider, with masses, task, policy switch and domain notes.
`ot4-crank` already existed, so this attempt used a distinct root and no
`--resume`. The command was `CADEX_MODEL=claude-opus-5 JAX_PLATFORMS=cpu
./cadex walk --project "$PROJECT" --prompt "$PROMPT" --out
"$PROJECT/runs/fresh48" --name fresh48.cxpolicy --iterations 5 --envs 16
--seed 0 --timeout 600 --leg-timeout 1800 --json`.

| Leg or measurement | Result |
|---|---|
| Design (`claude-opus-5`) | Exit 1, 1.94 s; provider reported “You've hit your session limit” |
| Train / declare / rollout | Not reached |
| Render / section / inventory / clearance | Not reached; review block empty |
| Total reward / witness error | Unavailable; no training or rollout |
| Whole invocation | Exit 1, 2.003486 s |
| Peak process-tree RSS | 382,861,312 bytes, sampled every 0.2 s |

No watchdog intervention occurred (2.9 GiB memory guard; trainer bounded
by 600 s). The source comparison reported one differing file out of 56,
`cadex_assembly_worker.py`, from pre-existing uncommitted edits; this
attempt neither changed nor built the engine. The refusal preceded geometry,
so it provides no evidence about crank-slider solver support. The project
has scaffold documents but no accepted revision or progress row. Its local
`runs/fresh48/` retains the envelope, stderr and monitor receipt, excluded
from Git along with policy and review output. This leaves the fresh
mixed-joint walk unevidenced; the model refusal is the observed stopping
point, with no retry scheduled against a clock. Runtime and scaffold
behavior are unchanged.

**Measured fresh crank-slider walk, `ot4-mix52` (2026-09-08).** The same
invocation into an empty project, with `--iterations 5 --envs 16 --seed 0
--timeout 600 --leg-timeout 1800`, reached geometry this time.

| Leg | Result |
|---|---|
| Design (`claude-opus-5`) | **Exit 0, 1135.85 s**; accepted revision `3892e8cd…`, digest `df4ee45f…` |
| Train | Exit 1, 2.27 s; `mjx.put_model` raised `NotImplementedError: (mjGEOM_CYLINDER, mjGEOM_BOX) collisions not implemented` |
| Declare / rollout | Not reached |
| Render / section / inventory / clearance | Not reached; review block empty |
| Total reward / witness error | Unavailable; training produced no policy |
| Whole invocation | Exit 1, 1138.30 s |
| Peak process-tree RSS | 729,931,776 bytes, sampled every 0.2 s |

No watchdog intervention (2.9 GiB guard). The engine source comparison
reported `match` across 56 files against a freshly built and installed
engine. The design turn produced a four-body closed-loop slider-crank —
grounded frame with a round guide rail, an 11.3 g crank on a revolute
driven by a 250 N·mm position servo, a 25.7 g coupler and a 38.3 g slider
block on a prismatic joint — mobility 1, one MuJoCo `connect` closure,
worst closure residual 0.0015 mm over a 2 s driven run, peak servo effort
17.3 N·mm unsaturated. It refused the all-revolute version as redundant and
spent the three surplus 3D constraints on a cylindrical crank pin and a
ball wrist pin rather than disconnecting anything, which is what the prompt
asked for. Four `DECISION:` lines and three notes (`linkage-geometry`,
`actuators`, `sensors`) landed in the project.

**MJX does not implement every MuJoCo geom pair, and that bounds what a
design turn may author.** The cylinder used for the guide rail against the
box bodies is one such pair, so the exported model is valid MuJoCo and
untrainable under MJX. The four pairs MJX has no contact function for are
box/cylinder, cylinder/mesh, box/ellipsoid and ellipsoid/mesh; a design
turn that wants a trainable mechanism prefers box, capsule or sphere
collision geometry. **The engine now refuses the task rather than letting
the trainer discover it** (ADR-281): `assembly.task` enumerates the
exported model's candidate collision pairs and names the offending geoms,
bodies and kinds at the moment the task is declared, which is where the
author still has the collision shape in front of them. `assembly.mjcf`,
`assembly.rollout` and the simulation trace are untouched — a cylinder is
still a legal collision shape on a model nobody trains. **And when a
trainer does fail, the envelope names it** (ADR-280): before that fix,
`walk.json` quoted two benign `Failed to import warp` lines off stdout and
the `NotImplementedError` reached only the inherited terminal, so a
`--json` caller could not tell why the leg died. Local evidence is in
`runs/fresh52/{walk.json,walk.stderr,monitor.json}`, excluded from Git.
This leaves the fresh mixed-joint walk **evidenced through design and
stopped at train**, with the stop moved forward into the design turn that
can act on it.

**The same fresh walk, end to end, `ot4-mix55` (2026-09-09).** The identical
prompt into a second empty project, same flags, against a freshly built and
installed engine (source comparison `match` across 56 files), **completed every
leg**.

| Leg | Result |
|---|---|
| Design (`claude-opus-5`) | Exit 0, 1649.63 s; accepted revision `70fd2a53…`, digest `ee279ea9…` |
| Train (CPU, 5 it × 16 envs, seed 0) | Exit 0, 26.71 s; reward/step −0.4055 at best iteration 4, 4,609 parameters, 5.20 s trainer wall time |
| Policy verify | Witness error 1.14e-08 against a 1e-04 tolerance over 32 samples |
| Declare | Exit 0, 0.81 s |
| Rollout (`policy_on=1`) | Exit 0, 1.53 s; total reward −19.85 over seed 1 |
| Render | Four views (front, iso, right, top), 4,756 triangles, 0.90 s |
| Section | Plane XZ at 0.0 mm, 4 of 4 objects cut, status `ok` |
| Inventory | 4 components, 0 catalogued |
| Clearance | 6 pairs checked, 0 unknown, **1 intersection**: frame ∩ slider, 648.0 mm³ |
| Whole invocation | **Exit 0, 1680.78 s** |
| Peak process-tree RSS | 2,312,118,272 bytes, sampled every 0.2 s |

No watchdog intervention (2.9 GiB guard; trainer bounded by 600 s). The design
turn again refused the four-revolute-plus-prismatic loop as over-constrained by
three rows, and again spent those constraints on real hardware freedoms — a ball
rod end at the crank pin and a keyed cylindrical bushing at the rail — rather
than disconnecting anything. Six project `ADR-` entries and five domain notes
(`actuators`, `architecture`, `linkage-geometry`, `rejected`, `sensors`) landed,
with `PROGRESS.md` rows for the prompt, train, script, params and walk runs.

**The MJX geom-pair constraint held without the refusal having to fire.** Every
collision shape the design turn authored is a box or a capsule, in contact group
1 against an empty group 0, with the comment that the loop is carried by its
joints and the shapes exist only to be visible in a viewer. ADR-281's check
therefore never raised, and `train` ran. That is one run, not a guarantee that
the guidance always steers an unaided turn.

**Clearance reports; it does not gate.** The frame and slider intersect by
648.0 mm³ at the initial solved pose — the carriage groove clears the rail bar,
but the two solids still share volume elsewhere — and the walk exited 0 anyway.
The eyes name the offending pair for the next design turn to act on; nothing in
the walk refuses a model over it. Local evidence is in
`runs/fresh55/{walk.json,walk.stderr,monitor.json}`, excluded from Git along
with the policy, the trace and the review output.

**A second mechanism through the same entry point, `ot4-cart` (2026-09-09).**
A different prompt — an inverted-pendulum cart: grounded frame and rail, a cart
on a **prismatic** joint driven by a bounded **force motor**, and a slender pole
on a **passive revolute** joint nothing drives — into a third empty project,
with the same flags, the same bounds and **no code change of any kind**. It
**completed every leg**, and it is the first ot4 walk whose mechanism carries an
unactuated degree of freedom and whose task declares a termination the rollout
actually reaches.

| Leg | `ot4-mix55` (crank-slider) | `ot4-cart` (cart-pole) |
|---|---|---|
| Design (`claude-opus-5`) | Exit 0, 1649.63 s; revision `70fd2a53…` | Exit 0, 1196.04 s; revision `0aa617e2…`, digest `b3b699e6…` |
| Train (CPU, 5 it × 16 envs, seed 0) | Exit 0, 26.71 s; reward/step −0.4055 | Exit 0, 20.27 s; reward/step 0.6936, best 0.7013 at iteration 0, 4,609 parameters, 3.95 s trainer wall time |
| Policy verify | Witness error 1.14e-08 | Witness error 6.34e-09 against 1e-04 over 32 samples |
| Declare | Exit 0, 0.81 s | Exit 0, 0.65 s |
| Rollout (`policy_on=1`) | Exit 0, 1.53 s; total reward −19.85, seed 1 | Exit 0, 1.21 s; total reward 28.756, seed 7, **31 of 200 steps** |
| Render | 4 views, 4,756 triangles | 4 views, 5,002 triangles, 3.19 s |
| Section | XZ at 0.0 mm, 4 of 4 objects cut | XZ at **−15.0 mm** (derived), **2 of 3** objects cut, status `ok` |
| Inventory | 4 components, 0 catalogued | 3 components, 0 catalogued |
| Clearance | 6 pairs, 1 intersection (648.0 mm³) | 3 pairs, 0 unknown, **0 offending**; bounds check `pass` |
| Documentation | 5 notes, none missing | 3 notes (`actuators`, `rejected`, `sensors`), none missing |
| Whole invocation | Exit 0, 1680.78 s | **Exit 0, 1222.22 s** (`walk_seconds` 1222.11) |
| Peak process-tree RSS | 2,312,118,272 bytes | 1,997,844,480 bytes |

Both at `--iterations 5 --envs 16 --seed 0 --timeout 600 --leg-timeout 1800`
under `JAX_PLATFORMS=cpu`, both sampled every 0.2 s under the same 2.9 GiB
guard, neither stopped by it. The two `total_reward` columns are **different
objectives in different units over different episode lengths** and do not rank
the mechanisms; the columns and their definitions are what is comparable, and
both projects' `PROGRESS.md` carry the same rows for prompt, train, script,
params and walk, committed by the walk's own child commands (five commits in
`ot4-cart`, ending `fac73fc`).

Two findings the run produced that are worth reading as findings rather than
failures:

- **The rollout ended on the task's own termination, not on the horizon.**
  `termination: pole_fell` fired at step 30, so the verified rollout is 31
  steps of a 200-step, 4 s episode and `total_reward 28.756` is a sum over
  those 31. Training's mean episode was 16.8 steps. Five PPO iterations is a
  smoke test of the loop; nothing here claims the policy balances a pendulum.
- **The derived section offset cut 2 of 3 objects, and named the one it
  missed.** Of the candidates `[0.0, −2.0, 2.0, −8.5, 8.5, −15.0, 15.0]` the
  most-coverage rule (ADR-273, ADR-275) chose −15.0 mm; the pole came back
  `empty` and the review's `section.missed_objects` reports it as
  `moved: true` — the object carrying all 35.75° of the mechanism's rotation.
  On a rig whose moving part is a slender rod near the centre plane, maximum
  object coverage and maximum *interest* are not the same plane. The eye
  reported that itself rather than leaving a reader to infer it from a
  drawing they cannot see.

Local evidence is in `runs/cart1/{walk.json,walk.stderr,monitor.json}` and
`runs/cart1/review.json` in that project, excluded from this repository along
with the policy, the trace and the review output.

**Training on a remote machine is the same walk with one flag** (ADR-200).
`cadex train --remote` and `cadex walk --remote` run the train leg through
`training/remote_train.sh train` (ADR-089, `training/SETUP.md` §d) instead
of the venv's interpreter on this machine, and *nothing else changes*: the
bundle and the model are exported into `DIR/train` as before, the script
copies them to the box named by `training/.remote.env`, runs the box's own
trainer with **the same flags after `--`** (`--iterations`, `--envs`,
`--seed`, `--label` — pinned byte-for-byte against the local command), and
copies the policy back to `DIR/train/<name>.cxpolicy`, the very path the
local trainer would have written. The receipt is the same last JSON line;
the CLI then **verifies the returned file hashes to the receipt's sha256**
(a wrong file at the right path is otherwise a policy refusal with no
obvious cause), records the box's path under `training.trainer_out` and
puts the local path in `training.out`. The store, the digest edit, the
verified rollout and `review.json` never learn where the trainer ran, so
a remote walk's `PROGRESS.md` rows and `review.json` are comparable with a
local walk's line for line. What the flag changes and what it refuses:

- **Plan the leg before you walk it** (ADR-255). `cadex train --remote
  --dry-run` rebuilds, exports the bundle, and then reports what the leg
  *would* do instead of doing it: `training_plan` in the envelope names
  the files it touches (`bundle`, `model`, `policy`, `stored_asset` — the
  same four in both modes) and the ordered `steps` that touch them, with
  `executed: false`. The local mode's steps are `export → train → verify
  → store`; the remote mode's are those with `copy-out` and `copy-back`
  around the trainer, which is the whole difference between the modes.
  It runs no trainer, stores nothing, and reaches no box, so it is the
  preflight for `cadex walk --remote`, whose remote leg would otherwise
  fail only after the legs before it have already run. It is a
  `train` flag; `walk` has none, because a half-run walk is not a
  preflight.
- **Run `training/remote_train.sh check` first.** A dry run proves the
  shape of the leg, never that the box is reachable — that is `check`,
  and it is the one that does ssh. The CLI adds no
  configuration and reads no `.remote.env`; an unreachable or stale box
  is the script's `FAIL:` line, which reaches the envelope's `error`
  (exit 1) together with the last lines the script printed.
- **A run the box reports as `device: cpu` fails** — the dispatcher's own
  rule — unless `--allow-cpu` is given. `--allow-cpu` without `--remote`
  is a usage error: it is the dispatcher's flag.
- **A warm start travels** (ADR-268). `remote_train.sh` carries four
  files out for one: the bundle, the model, and — lifted out of the flags
  after `--` — `--init-from`'s policy and `--init-from-parent-task`'s
  bundle, into a `warm/` subdirectory of the run directory, with the two
  flags re-pointed at the copies. The flags this CLI builds are the local
  trainer's, byte for byte, in both modes; the rewriting is transport and
  belongs to the dispatcher (ADR-089). So an iterate has the same shape
  in both modes. The dispatcher refuses loudly, before it copies
  anything, when a warm file is missing, when the joined `--init-from=PATH`
  form is used (its path would not be rewritten), or when the two warm
  files share a basename and would collide in one flat `warm/`.
  `--trainer-python` with `--remote` is a usage error: the box's venv is
  `CADEX_TRAIN_VENV`.
- **Detached launch is pending, not a trained policy** (ADR-278).
  `cadex train --remote --detach --project P --out P/runs/new/train --json`
  returns exit 0 with `training.state: "pending"`, the dispatcher's `run_id`,
  `target`, `remote_dir`, `pid` and `policy_name`. The same object lands in
  `--out/training-receipt.json`, with its local `destination` and
  `receipt_path`. Use a fresh output directory under the project.
  No policy is verified, stored (even with `--put`), declared or rolled out;
  an older policy at the destination is untouched. PROGRESS records pending
  without reward or digest claims. Use the same remote configuration with
  `training/remote_train.sh watch RUN_ID FRESH_DEST` or `pull RUN_ID FRESH_DEST`.
  Inspect the returned progress and policy before `cadex asset --put` and
  `cadex script --set`. Pending proves launch acknowledgement, not continued
  execution, device choice, training success or a verified policy.
  `--detach` needs `--remote` and rejects `--dry-run`.
- **The walk detaches in two halves** (ADR-282). `cadex walk --remote
  --detach` runs the iterate change as usual, launches
  the train leg detached, and **stops at pending**: it writes
  `--out/walk-pending.json` (`cadex-walk-pending-v1` — the dispatcher's
  locator, the exported bundle and its sha256, the seed the launch used, the
  legs that ran, and the two commands that finish the run) and verifies,
  stores, declares and rolls out nothing. Its `PROGRESS.md` row reads
  `pending; no policy verified` and carries no comparison, exactly as the
  detached `train` row does. Bring the run home with the dispatcher —
  `training/remote_train.sh watch RUN_ID DEST` or `pull RUN_ID DEST`, where
  `DEST` is the receipt's `destination` — and then `cadex walk --complete
  --project P --out DIR` runs the second half: `collect` (the returned
  policy through `cadex asset --put`, the store write the blocking leg does
  inside itself), then the same `declare`, `rollout` and review legs, with
  the same artifacts. `--complete` runs no trainer, and
  refuses `--set`, `--remote`, `--allow-cpu` and `--detach`
  rather than ignoring them.
- **Completion refuses what it cannot honestly declare.** It reads only
  files the dispatcher brought back: `training-progress.json` must say
  `done` (a `running` run says watch it, a `failed` one quotes its error and
  names `train.log`); `train.log`'s last JSON line is the trainer's own
  receipt, and the returned policy must hash to the `sha256` in it; the
  receipt's `task_sha256` must be the bundle this walk exported, and that
  bundle must still hash to what the launch recorded. So a stale policy left
  in the destination, another run's checkpoint, or a script that moved under
  the run are each a named refusal at `EXIT_REJECTED` rather than a declared
  digest. Warm-start provenance is untouched: nothing retrains, and the
  provenance lives in the policy header the box wrote (ADR-268).
  `cli/tests/test_walk.py` runs both halves against a stand-in dispatcher and
  a local run destination — no ssh, no box, no `.remote.env`.
- **`--timeout` is local.** It ends the local dispatcher/SSH process, not
  remote training. `--leg-timeout` has the same limit. Use the detached run
  ID with `remote_train.sh stop` to stop training on the box.
- **The project's docs say which mode it trains in.** The
  `ARCHITECTURE.md` scaffold carries a `## Training` section for the
  agent to fill in — local venv or `--remote`, and why — that states the
  shared artifact paths and the cold-run limit above, and every `train
  --remote` run's `PROGRESS.md` row ends in `(remote)`, so a reader of the
  numbers knows where each came from. `cli/tests/test_project_docs.py`
  holds this paragraph and that section together.
- **Nothing here dispatches in a test.** `cli/tests/test_train.py` pins
  the command against `remote_train.sh`'s own usage line and runs the leg
  end to end — real engine, real export, real store — against a stand-in
  dispatcher with the same argv contract and the same printed shape
  (`warp` noise before the receipt, `==>` trailer after), including the
  three refusals: wrong bytes, nothing returned, CPU fallback. The
  warm-start transport is tested against the **real** script instead, with
  stand-in `ssh` and `rsync` that make this filesystem the box: the two
  files land in `warm/`, byte-identical, the re-pointed flags are what the
  trainer is handed, and the three refusals above exit before the trainer
  is reached. No network, no box, no `.remote.env`.

**There is no GUI-attached mode any more** (ADR-495). ADR-201's third
mode — the same walk from a terminal beside an open Blender file — retired
with the shell it attached to. The review dashboard (`cadex review`, below)
is the UI, and it reads the project directory the walk writes; it holds no
second copy of the model that a command could make stale.

**The project is a codebase** (ADR-193). Every project root carries the
documents an engineer keeps beside a model, created by the CLI on the
first visit and never overwritten by it:

| File | What it holds | Who writes it |
|---|---|---|
| `ARCHITECTURE.md` | What the project is, what the script declares and why, how it trains, where the domain docs are. | the agent or a person |
| `DECISIONS.md` | The project's own ADR log — what was chosen, over what, why. Newest last. | the agent or a person |
| `PROGRESS.md` | One row per accepted run: time, command, revision, digest, what, numbers. | **the CLI**, after every accepted run |
| `docs/<subject>.md` | Longer notes, one file per subject: `docs/gear-ratios.md`, `docs/sensors.md`, `docs/actuators.md`, `docs/rejected.md`. | the agent or a person |

The agent reads all three before it acts and writes `DECISIONS.md`,
`ARCHITECTURE.md` and its notes itself, with its own file tools; the
guidance asks for `docs/actuators.md` and `docs/sensors.md` from any
mechanism that has actuators or sensors, which the walk then checks
(ADR-256). Before ADR-538 the CLI's own agent had no file tools, so the
documents were pasted into its prompt, bounded, and a closing `DECISION:`
or `NOTE <subject>:` line was landed for it. `docs/inventory.md` and
`docs/clearance.md` are the CLI's own generated reports and are not note
subjects — a note never appends to a measurement. `PROGRESS.md` is the CLI's, so it records
what happened rather than what a model said would: `params`, `script
--set`, `export`, `link`, `asset --put`, `train` and an MCP session that
accepted a build each land one row, with the exported trace's `total_reward` and the trainer's
`reward_per_step`, wall time and sha256 in the numbers column when the
run produced them. Printing the script and listing the store change
nothing and get no row.

**The comparison is one recorded row** (ADR-194). A number an earlier
row also carried is written with its change against that row — the
delta, the digest of the run compared against, and that run's value:

```
| … | script | 506bfc86 | 68530963 | script --set switch9.py | total_reward -293.4 (Δ -421.2 vs 2996fb73 at 127.8) |
```

`total_reward` and `reward/step` are compared; each against the last row
that carried it, so a `train` row between two rollouts does not break the
chain. The rows are read back from `PROGRESS.md` as written, which means
a row a person adds by hand counts too.

Training `--seed` is a bounded unsigned 32-bit integer (default 0); it does
not change the rollout seed declared in the xscript. Train and walk rows record
`training_seed`, `rollout_seed` (unavailable for training alone), an objective
identity and the prior same-kind row's evidence. Missing historical evidence is
marked `unavailable (legacy row)`; no seed or objective is inferred retroactively.
A trace seed of `None` means an explicitly unseeded rollout, not missing evidence.

`training.comparison` and the walk's `review.json` comparison block retain the
objective metadata and full action rows. Objective `v1` is SHA-256 over compact,
key-sorted JSON of the exported task's `schema`, `observations` (including units),
`reward`, `termination`, `episode` and `functions`. List order and expression text
are significant. Model identity, actions, seeds, reset variation, randomisation,
disturbances and runtime versions are excluded; this identifies the declared
objective, not experimental equivalence or mathematical equivalence of formulas.
The separate `actions` hash in progress rows covers full action metadata; inspect
`comparison.actions` for physical bounds and units. The quill's 40 mm and 60 mm
action bounds have different scaling despite matching rewards and objectives.
Deltas remain descriptive, never evidence of improved learning or equal control
difficulty. Prior evidence refers to the previous train/walk row of that kind;
metric deltas still refer to the last row carrying each metric, which may differ.
Standalone rollout rows retain their existing numeric format.

Progress rows replace `PROGRESS.md` only after writing succeeds (ADR-264;
the CLI writes no decisions or notes since ADR-538). A failed write or replacement preserves the previous
document and removes the temporary file on ordinary exception cleanup. Existing
file permissions and document symlinks are preserved. This is per-file protection,
not a transaction across documents or a power-loss guarantee; a killed process
may leave a hidden temporary file.

**Project history depends on repository ownership** (ADR-194).

- **Fresh root outside another work tree:** the CLI runs `git init` and
  creates default `.gitignore` rules only if that file is absent.
- **Existing project-root repository:** the CLI uses it and leaves its
  ignore configuration unchanged; it does not install default rules.
- **Project nested beneath another repository root, without its own `.git`:**
  documents and progress rows still land, but there is no initialization or
  commit. The parent index is untouched, and the envelope reports
  `inside an existing git work tree: not initialised, not committed.`

The default ignore rules exclude rebuildable `script_artifacts/`, frames,
renders (including the project-root `review/` directory), `*.png` and
`*.mp4` files, locks, `.cxpolicy` files outside `assets/`, and
`*-trace.json` rollouts (ADR-199). Existing ignore files are preserved even
when initializing a fresh root; check their rules before generating
checkpoints and traces. The defaults retain stored assets, including policies
under `assets/`, while `review.json` and `PROGRESS.md` keep the numbers.

**Keeping a rehearsal local (ADR-262).** Before running the walk, append these
rules to the project-root `.gitignore`, **after** `!assets/*.cxpolicy`, using
the actual output directory and policy name:

```gitignore
/runs/<name>/
/review/
/assets/<name>.cxpolicy
```

The stored policy remains on disk for verification and replay, while project
source, `PROGRESS.md` and domain notes remain versioned. A clone needs those
excluded weights supplied separately. `.git/info/exclude` can exclude the run
directory, but its policy exclusion loses to the higher-priority root
`!assets/*.cxpolicy` rule; the CLI does not force-add policies. `git check-ignore
-v --no-index PATH` identifies the winning rule (a `!` rule means inclusion).
Fresh scaffolds now exclude `/review/`; existing repositories are not migrated,
so add it explicitly there. `review.json` inside a non-excluded run remains
versioned by default, along with stored policy assets.

Ignores do not untrack files already in history or undo explicit staging.
Inspect `git ls-files` and `git diff --cached --name-only` before a run. If you
choose to stop tracking an existing output, use `git rm --cached -- PATH` and
commit that removal before the walk; the file stays locally and prior history
is preserved. The CLI never silently untracks user files.

In a project-root repository, every accepted run attempts to commit **all
working changes** (`git add -A`), including unrelated edits and the current
working version of previously staged files. The message uses the
`PROGRESS.md` row's words; `committed <sha>.` in the envelope's `notes`
confirms success. A row alone does not prove a commit: missing Git or a
failed commit does not fail the accepted run. Without `git` on `PATH`,
there is no automatic history.

Opening a project re-stages its accepted attempt under a new id, so a
read-only visit (`cadex script` with no `--set`) leaves the engine's
`script.json` modified until the next accepted run commits it.

**Neither form of `script` asks for the restore pass** (ADR-272). The read
reads the stored source, not the model; the write replaces that source and
re-accepts it, so replaying the old one first is wasted work. It also is the
one pass that fails exactly when these two commands are needed: after
`train --put` overwrites the asset the accepted script declares by sha256,
the stored script no longer re-runs, and the walk's digest edit — a `cadex
script` read followed by a `cadex script --set` — is what repairs it. Every
other command keeps the restore.

### The review dashboard (ADR-286, ADR-301)

```bash
./cadex review --project ~/cadex-projects/biped --host "$(tailscale ip -4)" --port 8765
# review: serving biped at http://100.x.y.z:8765/ (read-only; Ctrl-C to stop)
```

The page's layout, type and colour follow `docs/DASHBOARD.md`: a dark
theme by default and a light one, one type scale. **Since ADR-534 the
project page is the app**: a screen tiled by resizable, movable areas after
Blender's, each showing one editor — the 3D viewport and the 2D viewport — and one
editor at a time, picked from a tab bar, on a phone; since ADR-539 the
settings are a File, Revisions and View menu bar and the default screen is
one 3D viewport. ADR-533 had cut what it shows to the accepted model, a design turn, the
parameter sliders and the revisions; ADR-534 adds back run models and
playback, drawings, images, documents and training plots, all read from
routes that were already served. **Since ADR-537 it writes nothing**: the
design turn, the sliders and the revision verdicts are gone, the server
answers GET and HEAD only, and the page follows what the agent's CLI and
`cadex mcp` calls change.
`cli/tests/test_review_design.py` reads the spec back from the rendered page
at 1400×900 and 400×850.

**What follows describes what the server reads and serves.** Every route
below still answers. Where a paragraph names a panel, a tab, a button or a
run selector, that page element was removed by ADR-533 and is not on the
page; the data it drew is still in the `GET /api/...` reply the paragraph
names, for the CLI, the agent, or a panel added back later.

**The page leads with the design (ADR-430).** When the project has a
concept sheet, the desk stage opens on its **Concept** tab and the phone
column reads it before the model. `GET /api/project` carries a
`presentation` block, read from the render's `summary.json`: `available`,
the `revision` and `digest` it was drawn from, its `relation` to the
accepted revision now (`current`, `historical`, `unknown`), the `source`
directory, the `files` offered (`hero`, `sheet`) and the sheet's `numbers`
and `palette`. It prefers the accepted revision's walk render
(`review/render/<revision>/`) when that one drew a sheet, else the last
`cadex render` (`review/render/`). A project with no render, or a render
from before the sheet, says so and names `cadex render` as the fix.
`GET /presentation/sheet.png` and `/presentation/hero.png` serve only what
that block offers; every other name under `/presentation/` is a 404.

One project per server, inspection only. The page is for a person, on
another device, with no display session on the machine that serves it:
`--host` defaults to `127.0.0.1` (this machine only); give it the
machine's Tailscale or LAN address to reach it across the private network,
or `0.0.0.0` for every interface. `--port 0` takes a free port; the URL is
printed on stderr the moment the socket is bound, which is what a script
waits for. The server holds no state: every request reads the manifest,
the records and the retained files as they stand, so a walk that lands
while the page is open shows up on its next poll (two seconds), and
stopping or restarting the server — Ctrl-C, SIGTERM — changes nothing
about the project and neither stops nor duplicates a walk or a training
run in progress. Browser state is not project state; authoring and
training stay on the CLI.

New visits open the current run (ADR-299): newest running/pending record with
fresh starting/training telemetry first, otherwise the latest recorded attempt,
including failed or interrupted work. Record time orders runs, with run name
breaking ties. With no runs, the accepted view opens.
`cadex_cli.review_server.default_run(review)` is that rule in Python
(ADR-316), so a checker asks it what a fresh visit will select rather than
reading a run's name. An untouched page follows
current work on polls; selecting a view or playing a video preserves that view.
Opening a document also preserves the selected view. Its loaded text stays open
across polls; click its link again to refresh it. Changing the selected view or
its recorded revision clears the document, so another model cannot inherit the
previous view's specs or decisions (ADR-306).
When the selected model revision or digest changes, polling reloads its geometry
as well as its identity and parameters (ADR-307). This includes the first
acceptance in an already-open empty view. Unchanged polls preserve the camera;
selecting a historical run keeps its retained geometry.
The **Current run** button names the current attempt and returns to following it.
Missing/stale output stays labelled; an older success is never substituted for
a newer failure. The frozen [operator review record](probes/operator-review/README.md)
describes the shared Reed server and its browser verification as they
were; that operator tooling was removed (ADR-536).

Training telemetry (ADR-287) is read from each selected run's
`runs/<name>/train/progress.json`, including before the initial running record
has observed that file. Local `cadex walk` training writes there automatically.
The browser polls every two seconds and plots retained reward, loss and episode
length histories (at most 512 samples each), alongside iteration, total and
checkpoint availability. Checkpoint bytes must match the reported sha256 to
appear as retained; this is integrity evidence, not engine policy verification.
The cost of that poll is bounded per run, however long the history (ADR-321):
`GET /api/project` carries every run's telemetry as a **summary** — state,
reason, latest metrics, the sample count of each history, the number of
checkpoints reported and the checkpoint-source state — and reads no
checkpoint bytes; `GET /api/run/<name>` carries the one selected run's
histories and its digest-verified checkpoint list. The summary also carries
the trainer's `eta_s`, `wall_time_s`, `best_iteration`,
`best_reward_per_step` and `warning` (ADR-542). `GET /api/project`'s
**`stage`** is what the project is doing, for the 3D viewport's overlay
(ADR-542): `state` (`evaluating` when an `evaluations/<name>/` without its
report was written in the last 120 s, `training` when the run read is
`running`/`pending` with telemetry `starting`, `training` or `stale`,
`failed` when the newest run failed and no revision was accepted after it,
`designing` within 600 s of an accepted revision, else `idle`), `reason`,
`since`, `run` (the newest run training, else the run a fresh visit opens),
`runs` (how many), and `training`: that run's telemetry with `spark`, its
reward and loss histories cut to at most 64 points each, or `null` when no
run has telemetry. It is one bounded block whatever the history. `stage`
also carries **`checkpoints`** (ADR-545): that run's numbered checkpoints
rolled out by ADR-544's watcher, at most the newest 64 (`listed_of` says
how many), oldest first. Each item is its `stem` (`walk.000040`), `tag`,
`state` (`ready`, or `failed` from its `.rollout-failed.json` or an
unplayable trace), `iteration`, `reward_per_step`, `sha256`, `reason` and
`error`, and for a ready one `duration_s` and `url`,
`/api/playback/checkpoint/<run>/<stem>`: that trace through the same
`trace_playback` as a run's own rollout, with the trace's `checkpoint`
block. `pending` counts checkpoints with neither file yet. Only regular
files in the run's own `train/` are read, and each trace is parsed once
per file identity, so an idle poll reparses nothing; `null` when there is
no run. The page
has no telemetry panel (ADR-533 removed it): the 3D viewport's stage overlay
(ADR-542) is drawn from `/api/project`'s `stage` alone, on the page's existing
poll, and is rebuilt only when that block changes, so the overlay reads the
stage, the iteration, the ETA, the sparklines and the warning from one
snapshot. The page fetches `/api/run/<name>` only when the 2D viewport
plots one of a run's curves, never for the overlay, so an idle poll adds a
constant number of DOM nodes whatever the run count. `window.cadexReview.lastPoll()` reports the last
poll's list bytes, detail bytes and wall time. The `test_review_history_scale.py`
suite pins this over sixty-three runs with 512-sample histories and three
checkpoints each, then grows the history by twenty runs under a deliberately
selected historical run whose video keeps playing.
The snapshots and checkpoints belong to the run: retain and copy its whole
`train/` directory with the project. No server or browser is needed to retain
them. Older trainers may lack loss/episode histories; the page labels these
missing rather than inferring them from final metrics.

**Disk use per run (ADR-322)** travels with the same detail, never with the
list: `/api/run/<name>` carries `disk` (`cadex-run-disk-use-v1`), what that
run keeps under `runs/<name>/` counted from its permitted project-local
files only — every regular file that resolves inside the run directory,
each inode once (a hard-linked pair is one file and one
`hardlinked_entries`), nothing followed through a symlink (linked entries
are listed under `skipped` with the reason), split by the run's top-level
subdirectories in `by_dir`, as apparent sizes from `stat` with no bytes read
and nothing hashed. `references` sizes each reference the record names with
the reader's own status words: `retained` with its bytes, `missing` with
none, `refused` and never opened, `not recorded`. Directory references that
exhaust the traversal budget have `status: truncated` and `lower_bound: true`;
their byte/file counts are partial, including zero when no allowance remains.
Skipped entries also make a directory reference a lower bound. The browser
labels these sizes **at least**, and labels truncated references explicitly.
One 20,000-entry budget covers the run walk and **all** directory references
combined; scans consume entries lazily without sorting whole directories.
`entries_visited` reports the aggregate consumption. Reaching the limit exactly
is conservatively reported as truncated. Direct file references use a stat,
not a directory traversal. A project-level reference
(`project_artifacts`) that resolves outside the run — the policy asset a
training run and its playback run both cite, a render directory two runs
at one revision share — is **not** in the run's total: it is sized under
`shared_bytes` (`shared_lower_bound` flags a partial sum) and `shared_with` names the other runs whose records cite
the same path, so one file is counted once however many runs share it.
`state` is `counted`, `truncated` (the walk stopped at
`DISK_USE_ENTRY_LIMIT` entries and the totals are a floor) or `unreadable`
(the run directory is missing or escapes the project, and nothing under it
was stat'ed). This state describes the run walk; a complete run total can
coexist with truncated directory-reference sizes. The Artifacts card shows the total, the per-directory split,
the skipped links, the shared references with the runs that share them,
and a size column on the artifact table that says `missing — nothing on
disk` and `refused — not read` where the reader did; the accepted view has
no run to count and says so. Video size labels update in place when the
selected detail arrives; receiving a size never replaces or pauses the player.

A playback run — a rollout of a checkpoint or final policy whose record names
the training run it came from as `training.requested.source_run` — copies the
training snapshot beside its own rollout but not the checkpoint files. Its
checkpoints resolve in its own `train/` first, then through that recorded
training run's `train/` inside the same project (ADR-309); each entry says
where it was found. The page's checkpoint line names the provenance state:
`none` (no training run recorded), `resolved`, `missing` (the named training
run is not in this project, as after a copy that left it behind) or `refused`
(the recorded name is not a bare run name, or `runs/<name>` escapes the
project, including by symlink). A copy never reaches the original project's
checkpoints; it says the training run is missing and names the next command.

Missing, invalid, failed and stale telemetry are explicit. A starting/training
snapshot older than 30 seconds is stale even when the server is reachable;
this includes slow compilation and does not establish that the process died.
Terminal `done` and `failed` snapshots do not expire. Failures caught during
training or final policy validation/saving preserve the last metrics and
checkpoint references and report the error (ADR-288). Final policy publication
must succeed before telemetry reports `done`. A hard kill or an unwritable
progress file can leave a stale snapshot;
inspect CLI output and start a new named walk if training stopped. Remote
mirrors named `training-progress.json` are not observed by this local path.
The synthetic browser test spans committed updates without reloading and
requires each to appear within five seconds on the test machine. One real
observation exists: the fresh biped's first GPU probe, seven iterations shown
within 0.21–1.4 s of their commit on the page's own poll, with the run's
revision still unrecorded while it trained (`docs/HEADLESS-BIPED-REVIEW.md`).

What the page shows, and where each thing comes from:

- **Accepted now**: the revision, digest and parameter specs from the
  project manifest, the current documents and decision headings, and the
  model from the **accepted attempt's own tessellation** — the
  `display/*.tess` files under the staging directory the manifest names,
  each linked to its output by the BREP's sha256 — every output whose
  BREP bytes match keeps that tessellation, so a mirrored pair of limbs
  shows both sides (ADR-302) — placed where the attempt's own simulation
  trace put each component at its first frame.
  This is the second and last read the review client makes of the
  project store's layout (ADR-285 documented the first, `script.json`);
  a staging directory that does not lie under the accepted revision is
  refused rather than shown as the accepted model — **unless** the
  manifest's `accepted_attempt` pin names the accepted revision *and* the
  attempt's own `result.json` carries the accepted digest (ADR-311). That
  is the shape of every project's **first** accepted script: the engine
  stages an attempt under the revision it can compute before the worker
  runs, over an empty parameter-spec cache, and records the revision
  recomputed with the collected specs as the accepted one. The agent's
  modelling calls and `cadex script --set` carry the same standard
  tessellation request `cadex params` makes (ADR-312), so a project
  straight out of an agent's first `write_script` has a model to show; `accepted attempt
  retained no tessellation` now names a project accepted before ADR-312,
  or through a `restore` replay alone, and a public rebuild with display —
  `cadex render`, `cadex params` — republishes the accepted attempt. The
  review client never rebuilds anything itself.
- **A run**: everything from its `run.json` (ADR-285) — identity, params
  and specs *as recorded*, training request and receipt, rollout seed and
  reward, artifacts with each one's status, the document snapshot — and
  the model from the **meshes its rollout leg exported beside its trace**,
  placed by that trace's first frame, with component-to-output links from
  the run's render summary. A historical run is labelled `HISTORICAL —
  recorded at <its revision>, accepted now is <today's>` and drawn from its
  own files only; nothing is rebuilt from today's script. A `running`
  record is labelled as started and never finished, with the next CLI
  action; a legacy run reads `unrecorded`. A `failed` record whose
  telemetry reads `done` is explained rather than left as a contradiction
  (ADR-326): the note says training itself finished, at which iteration of
  how many and which policy the trainer saved, and that the failure came
  after it — in the run's observation or recording, not in the trainer —
  above the run's own error. The identity card's **policy store** row shows
  `policy_store` for every selected run: its state, the reason, the
  retained trainer copy and the next CLI action; a store write the operator
  makes afterwards flips it to `stored` on the next poll, with the run's
  status and history untouched. A `completed` run whose policy is retained
  only under its own `train/` is also listed under the run's problems with
  that store command (ADR-327), and the entry leaves on the poll after the
  store write.
  Before a rollout, new walks show their retained assembled training view,
  including component identities and the recorded placement source (a trace's
  first frame or declared placements, explicitly labelled). Missing snapshot
  meshes remain missing. Older runs are not backfilled from current state.
  Without this snapshot, a run with recorded revision/digest and `model_xml`
  can show the STL parts retained beside that training export (ADR-290).
  These are explicitly labelled **individual parts at identity, not a
  solved pose**: the export does not retain component placements. This
  works after the accepted revision changes or staging is pruned. Missing
  or refused recorded exports show the reason. With neither a trace nor a
  training export recorded, current tessellation can be borrowed only
  when both revision and digest match; historical geometry is never rebuilt.
- **Labels, never guesses**: an artifact is `retained` (linked, with a
  download), `missing`, `not recorded` or `refused: <why>`; a run with no
  recorded trace whose file is missing has *no model to show* and says
  which file is missing; the header
  reads `live: updated <time>` while the server answers and `stale: server
  unreachable, last update <time>` when it stops, with the last good view
  left on screen. Retained videos with a recorded SHA-256 are verified before
  playback or download; a mismatch is refused and labelled with a CLI retry
  action. Restoring the matching artifact recovers on the next poll. Older
  entries without a digest retain existence-only checks. The video list leads with current file
  availability and a retained/recorded count; missing or refused files show
  unavailable (or partly available when other recordings remain). The separately
  labelled recorded render outcome is historical: `ready` does not mean its
  output still exists or passes verification. Restoring the original bytes
  recovers playback on the next poll. Videos are the D4 slot: a recorded video plays inline
  from the page's own Play control or the native controls (byte ranges are
  served, so seeking works) and downloads, identified by policy digest, seed
  and simulated seconds; none recorded says so. The model orbits by mouse or
  finger and pinch-zooms (ADR-330).
  Downloads preserve Unicode filenames through an encoded UTF-8 name and an
  ASCII fallback in the response header (ADR-323).
  A download the browser cancels mid-transfer is the client's decision: the
  server logs one line naming the bytes sent, prints no traceback, and the
  next whole or byte-range request serves the file (ADR-324).

Video verification retains at most 256 digests in process memory (ADR-296).
Each read still checks containment and file identity, size, and nanosecond
modification/change times; changed files are hashed again, including same-size
edits whose modification time was restored. Restarting clears this cache.
First reads, changed files and histories exceeding the cache can still require
reading all recorded video bytes. This is not a five-second latency guarantee
for arbitrary histories. The [64-file measurement](probes/video-history/README.md)
records both the cold-read cost and subsequent browser polling latency.
Each browser page keeps at most one project poll in flight (ADR-297): timer
ticks and explicit refreshes share the pending request, including initial
verification after a server restart. Initial loading remains labelled until
verification completes; slow reads do not multiply requests from that page.
Within one server process, video cache lookup and hashing are serialized
(ADR-298): concurrent clients reuse a completed digest instead of duplicating
the same cold read. An unrelated cold video can wait behind that verification;
separate server processes do not share this lock or cache. The cache remains
bounded at 256 entries, and failures release the lock for subsequent requests.

What it serves is an allowlist, never a path. Every route names a run by
its directory name, an artifact by its record key, a document by the name
its record lists, a mesh by the output it belongs to, a video by its
index; each is looked up in what the reader returned and resolved through
the reader's containment check. A reference that escapes its base is
listed under the run's problems and answered `404`, as is anything the
records do not name — the project's own `script.json`, a path with `..`,
the server's source. `cli/tests/test_review_server.py` pins the refusals
and, in a headless Chromium driven over its DevTools pipe
(`cli/tests/cdp_browser.py`, no Playwright), the labels, the historical
view, real mouse orbit and zoom on the canvas, the stale label and
reachability over a private address (`CADEX_REVIEW_HOST`).
`cli/tests/test_video.py` adds the D4 half in the same browser: a
rendered rollout plays, keeps playing across freshness polls, and
downloads — the harness saves the download where that Chromium can
write (a snap's `/tmp` is private to it, and it may not write hidden
paths under `$HOME`), waits on the browser's own download-progress events,
and compares the bytes it wrote with the retained file's digest.

Reproduce the private-address smoke on the serving machine, without a desktop:

```bash
CADEX_REVIEW_HOST="$(tailscale ip -4)" pixi run python -m pytest cli/tests/test_review_server.py -q -s
```

This starts a temporary fixture server, opens its private-address URL in
headless Chromium, checks the displayed project and accepted revision, and
stops the server. It is a same-machine private-address check, not evidence
of access from a second device or of the fresh biped lifecycle. The browser
suite also narrows a loaded model view from 1280 to 1000 pixels and checks
that the canvas stays within the page before exercising orbit and zoom.

**Restarting the dashboard is not an event for the project or its training**
(D6, fixture half). `cli/tests/test_review_lifecycle.py` runs the real
`cadex review` command, opens the page, selects a run whose telemetry a
separate producer process — one the server never spawned and never learns
about — commits every 0.3 s in the trainer's snapshot format, stops the
command with SIGINT, checks the open page reads `stale` with its last
identities and its video element intact, restarts the command on the same
port, and checks the same page returns to `live` on its own poll without
reloading: same selected run, same recorded revision, the loss history one
point longer than the iteration it now shows, the same video element still
decodable, and the served video byte-identical to the retained file. A
second page opened afresh against the restarted server reads the accepted
revision, the same run list, the historical label, the recorded parameters,
telemetry still advancing and a playable, downloadable video. Throughout,
the producer is the same PID, its iteration sequence never resets, and on
Linux exactly one process carries its marker; every file in the project other
than the producer's own snapshot has the same digest afterwards as before.
No engine runs anywhere in this test — the reader opens none, which is why
restarting an engine cannot change what the dashboard shows — but this is
fixture evidence: D6's required pass on the fresh biped with real training
artifacts, and save/reopen of a project a real walk wrote, remain separate.
The [Wren working-copy restart proof](probes/wren-fresh/RESTART.md) supplies
that retained-artifact check on the persistent private URL: two engine
reopens, all 15 run views compared, current/historical video downloads and
an open playing page preserved across a service restart. No trainer was
running during that real-project check. The subsequent
[real-training restart proof](probes/wren-fresh/RESTART-TRAINING.md) restarted
the same persistent service during Wren GPU training: one unchanged trainer,
automatic telemetry recovery within five seconds, historical playback and
download preserved, and a fresh page selecting the active attempt.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Fine. |
| 1 | The engine, the trainer or a walk leg failed. |
| 2 | The command was wrong. |
| 3 | The engine refused the script. |

Three is separate from one because a pipeline handles them differently: a
refused script is a modelling problem to feed back to the agent, a
failed engine is an infrastructure problem to retry or abort on.

### Streams

Progress goes to **stderr**; the report goes to **stdout**. `--json` is
always safe to pipe. `cadex script` with no `--set` prints the script and
nothing else, so `cadex script > model.py` works.


### Named-plane section review

`./cadex section --project ./robot --plane XY --offset-mm 8 --json`
writes `review/section/<accepted-revision>/XY-8/section.svg` and
`summary.json`, and commits a PROGRESS row. These generated files stay local
under default ignore rules. XY means z=offset,
XZ means y=offset, YZ means x=offset, in world millimetres. The JSON carries
accepted revision/digest, solved object placements, closed planar contours,
units, approximation, limits, `offset_source: explicit` and separate
acquisition/section timings. The walk's own cut derives its offset instead
(ADR-267, above); this command does not.

This is a cut of the accepted standard tessellation, not an exact BREP section
or a projected silhouette. SVG fills each object's contours using even-odd
parity so interior cavities remain holes; objects are not boolean-unioned.
Endpoints snap to a 1e-6 mm grid. `status: ok` means closed cut contours;
`empty` means no triangles meet the plane; `unsupported` (`available: false`)
means a vertex/edge/face contact within tolerance or an open, branched,
duplicate or collapsed cut. Per-object reasons remain in JSON. Move the plane
slightly for a degenerate contact. This does not certify solid validity or
absence of self-intersections. Unsupported reports can show other objects'
valid cuts and are visibly labeled unsupported, never complete geometry.

All three statuses are successful *reports* (exit 0); inspect `status` before
using geometry. Rebuild, revision, malformed input, work-budget and write
failures return nonzero and never reinterpret old artifacts as current success.
The renderer's accepted-buffer/triangle/placement budgets apply. An absent
model is an error, distinct from an empty cut of a model. The walk shares its
preview snapshot for XZ at a derived Y (above) and produces these same local artifacts
and reports their statuses in every mode (ADR-240 follow-up, ADR-262).

### Named-angle review

`./cadex render --project ./robot --json` writes `review/render/front.svg`,
`top.svg`, `right.svg`, `iso.svg`, the studio hero `hero.png`, the concept
sheet `sheet.png` and `summary.json`. These generated files
are overwritten on success and stay local under default ignore rules; the
ordinary project commit records the PROGRESS row.
The JSON envelope and each SVG name the accepted revision; the summary also
records digest, component/source names, colors, transformed bounds in mm,
camera bases, projected bounds, coverage, limits and acquisition/render timing,
plus `environment` (world geometry left out), `appearance` (each drawn
object's role, colour and `source` — `declared` by the script, `supplier`
from the inventory, or `index` with no inventory), `palette` (the colour in
effect for each role), `hero` (its path, size and seconds) and `proxies`
(below). A walk's review carries the whole summary as its `render` block, so
the roles and the proxies reach `review.json` with it, and both commands add
a `measures:` note.
A failed command must not be treated as a fresh report: old successful files
can remain, and their revision identifies what they describe.

Front looks along +Y with Z up; top along -Z with Y up; right along -X with
Z up; iso views from (1,-1,1) with Z upright; the hero is a low three-quarter
view, 20° above the floor and 35° round from the front (-Y) towards +X
(`docs/DESIGN-LANGUAGE.md` §7). Each orthographic view fits its own extent.
Solved component matrices are applied once; unposed source outputs used by
components are excluded, and so is world geometry the published fit names (a
floor). Other published triangle outputs are included. The protocol carries
no visibility toggles or transparency. These are initial-pose geometry
previews, not the dashboard's scene.

**Every image is a studio render (ADR-412)**, pure Python on the CPU with no
new dependency. A depth pass keeps the nearest triangle per subsample at
2×2 subsamples per pixel; only visible subsamples are shaded, and the box
filter down to the image size antialiases edges. Shading is a key, a fill
and a rim light with a Blinn highlight per role finish, on normals smoothed
across each object's shared vertices except over a 40° crease, so a fillet
reads as a curve and a box keeps its edges. The design stands on the review
viewport's **dark prototype mat** (ADR-444, `docs/DASHBOARD.md` §16):
the colours are the engine's `CadexStudio.PALETTE` (ADR-445), which the
viewport's own `environment.js` and `review.css` are test-held equal to, the grid pitch is the viewport's for the
framed span, anchored at the world origin and antialiased, and the mat fades
into the `#141414` background with distance; a level view draws the
background alone. A **contact shadow** is measured from the
geometry: a top-down map of how high the lowest surface over each cell sits
above the lowest point of the design, turned into a tight contact term and a
wide soft term, each blurred, and applied to the floor wherever the camera is
above it (not in `front` or `right`). **Materials come from roles**
(`render.materials`): an object's declared appearance role (`shell`,
`mechanism`, `accent`; `assembly.component(..., appearance=)`, ADR-413) wins,
in the assembly's declared `palette` where it recolours a role; an undeclared
one is `mechanism` graphite `#2F3237` when purchased and `shell` bone
`#E9E6DF` when printed, from the published inventory; with no readable
inventory every object keeps its index colour. Standard tessellation
approximates curves. Thin/subpixel features can disappear; no dimensions,
analytic edges, transparency or engineering-drawing accuracy is promised.
Limits are 4,096 display entries, 32 MiB total binary/sidecar input, 4 MiB per
sidecar, 300,000 vertices per source, 4,000,000 placed vertices, 2,000,000
placed triangles read, 400,000 drawn, and 20 million bounding-box pixel visits
**per 512 px view** (scaled by image area for `look`'s 768 px and the 1024 px
hero), counted in subsamples actually visited, including overdraw. Excessive, missing or malformed buffers, missing solved poses and
empty geometry fail explicitly. Above 400,000 triangles the snapshot clusters
vertices on a grid, starting at a quarter pixel of the 512 px view over the
model's largest extent and doubling until it fits; the summary's
`decimation` names the input count, the cell, the `extent_mm` it was sized
from and the world geometry that extent leaves out (ADR-410, ADR-439). A
declared floor is left out of that extent, named by the accepted fit as world
geometry, and is still clustered on the robot's grid; a fit that cannot be
read leaves every part in it. hex2 (110,688
triangles) was refused at the old 100,000 cap, and hex3 (589,268, filleted
brackets) at ADR-406's 400,000, which lost both the agent's `look` and the
walk's review. hex3 now draws as 106,326 triangles at a 0.24 mm cell; its
four studio views and the 1024 px hero take 6.5 s together, the hero 2.2 s
(ADR-412), after a 207 s rebuild to acquire the tessellation. A render that still fails in a walk's review is recorded as
`render.available: false` with the reason, and the rest of the review stands.

**The design-language proxies (ADR-414, ADR-415).** `summary.proxies` measures two of
A1's frozen proxies (`docs/probes/ot10/README.md`) from the drawn design in
the hero view: `hardware_silhouette_share` (P1), of the subsamples the design
covers, the fraction whose front-most surface is a purchased component, and
`material_count` (P3), the distinct colours of the objects visible there,
with the list. Each carries its frozen `bar` and whether it `meets` it. The
hero is measured by a depth pass alone at 512 px and 2×2 subsamples
(`render.PROXY_SIZE`), whatever size it is drawn at, so `render`, `look` and
review agree. Environment geometry is left out as in the image. With no
readable inventory nothing says what was purchased, and P1's `value` and
`meets` are `null` with a `reason`. The third, `sharp_outside_edge_share`
(P2), is a BREP measure read from the inventory rather than the image: the
engine reports each output's solid edge length and the sharp convex part of
it (`source_facts.sharp_edges`), and the CLI sums both over the printed
components, once per placement, and divides. The fit's world geometry (a
floor) is uncatalogued but not printed, so it is left out here too and
named under `left_out_as_environment` (ADR-424). A printed part with no such fact
(a mesh, or a revision accepted before ADR-415) makes P2 `null` with a
`reason` naming it rather than a false zero; with no printed edges it is 0.
The agent's `look` reports all three under `measures`, and each report adds
one `measures:` line.

**The concept sheet (ADR-430).** `sheet.png` is one 1536×1024 PNG
(`CadexStudio.compose`, ADR-445): the 1024 px hero, pixel for pixel, on the left; on
the right the project's name, the revision, the key numbers, a swatch per
appearance role the design uses in the colour in effect, the `front`,
`right` and `top` views as **line drawings**, and A1's three proxies. A line
view is the renderer's own depth pass at 204 px and 2×2 subsamples, keyed by
object and flat face normal: a subsample is ink where the nearest surface
changes object, meets the backdrop (drawn on both sides, so the silhouette
reads heavier), or turns by more than 35° within one object, and the box
filter turns coverage to grey. Lettering is a 5×7 bitmap face in the same
module; no font or image library. `summary.sheet` records its path, size,
revision, digest, views, seconds and `numbers`: `name` (the project
directory), `mass_kg` (the sum of the accepted MJCF output's per-component
inertials, the environment left out, read from the pinned accepted
attempt's `result.json` only when it is the revision drawn and carries the
accepted digest), `servo_count` (the inventory's `catalog_counts` in family
`servo`, horns not counted) and `size_mm` (X, Y, Z extent of the drawn
solids), each with its source. A number that cannot be read is `null` with
`mass_reason` or `servo_reason`, and the sheet prints `N/A`; it is never
estimated. The sheet adds about 1 s to a render (1.2 s on `ot10-biped-1`).

The CLI snapshots buffers while holding its project lock, before any further
engine request can invalidate attempt paths. Read failures
are refusals, never a fallback to guessed poses. `cadex walk` reuses this renderer in its review session, checks the rollout
revision and commits views under a revision directory. The same snapshot supplies the named-plane section described above.

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

`error` is present instead of `notes` when `ok` is false. `outputs` entries
that produced no file carry `skipped` with the reason. A run that accepted
a build adds `fit`, the measured-fit block that build's reply carried (§4, ADR-346) — `verdict`, counts and every failing
pair by name, with the swept `sweep` half inside it (ADR-366) — and the
prose report prints it as a `fit` line with one line per failing pair,
followed by a `sweep` line with one line per unswept joint and per
failing pair, each carrying its status. The same run adds `inventory`,
the catalog-identity block that reply carried (ADR-362) — `component_count`,
`catalogued_count`, `uncatalogued_count`, the `catalog_counts` roll-up and
every `uncatalogued_sources` name, with `derived_catalog_sources` naming
the ones cut from a catalog body (ADR-381), plus `appearance` (component →
declared role) and `palette` (ADR-413) — printed as an `inventory` line
with one line per uncatalogued source. An `asset` run adds
`assets`, the store's listing as `[{"name", "bytes", "sha256"}, …]`, sorted
by name — the same rows `put_asset` and `inspect scope=assets` return. A
`train` run adds `training`, the offboard trainer's receipt exactly as it
printed it on its last stdout line — `out`, `bytes`, `sha256`,
`reward_per_step`, `wall_time_s`, `device`, `task_sha256`, the witness
margin — and, with `--put`, the `assets` row the stored policy makes. The
receipt is not re-derived here: a number taken off a stream is a number
something else can write into (ADR-093), so this is the one the trainer
meant as data.

**BREP outputs are converted; every other staged output is copied.** A
BREP is written under the output's name in each `--format`. A mesh's
`.ply`, an MJCF model's `.xml`, a training task's, a policy receipt's and a
rollout trace's `.json` are copied **under the filename the engine staged
them with** (`model-model.xml`, `balance_task-task.json`,
`assembly-simulation-trace.json`) and named in `files` under their suffix.
The staged name is kept because the task bundle references its model by
it and `training/cadex_train.py` resolves the model beside the task by it:
the `--out` directory *is* the training bundle, and the trace's `policy`
block *is* the rollout review, with no staging path read by anyone
(`docs/MUJOCO.md` §7c, rows 3 and 7). Only an output with nothing staged —
an assembly component placing another output's geometry, a solve
diagnostic — is `skipped`.

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
  session.py           agent.json (the engine budgets) and the project lockfile
  tools.py             the tool surface, generated from OP_ARG_SPECS
  bridge.py            runs a tool call against cadexd; injects what the agent
                       is never asked for; records every call
  mcp.py               `cadex mcp`'s wire: JSON-RPC over stdio, idle callback
  guidance.py          the guidance an agent is given (ADR-538)
  export.py            STEP/STL/BREP out of the display block; the rest copied
  render.py            `cadex render` as a job: rebuild, read fit/inventory, write the files
  clearance.py         inspect scope=clearance -> docs/clearance.md; read-time thresholds;
                       reads the value the `fit` block is built from (the block
                       itself is the engine's CadexFitReport, ADR-447)
  inventory.py         inspect scope=inventory -> the project's docs/inventory.md;
                       the inventory block is CadexFitReport's too
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
  review_record.py     the run record and the project review reader (ADR-285)
  review_server.py     the read-only dashboard server (ADR-286, ADR-537),
                       with review_static/ the page
  browser.py           headless Chromium over its DevTools pipe, for capture and tests
  project_docs.py      the project's own docs, PROGRESS.md rows and repo
  report.py            the envelope and the prose
cli/tests/             the suite (§7)
```

One thing to know before reading `session.py`: **`inspect` is bounded and a
CLI is not.** `open_project` hands back the whole `script` block, but
`inspect scope="script"` returns a *page* — mappings 50 keys at a time, and
any value over 1 KiB replaced by a stub naming the path to fetch it from.
That is right for an agent reading a page at a time and wrong for
`cadex script`, which has to print the file. So every read there follows the
pointer paths and the `next_offset` chain to the end.

### Process topology

```
  your agent ──spawns──> cadex mcp ──owns, while busy──> cadexd (FreeCADCmd)
       │                                   ▲
       └── runs ──> cadex render/export/train … --wait ──┘  (when the server is idle)
```

The agent's MCP client spawns `cadex mcp` as its own child (ADR-538). The
server answers `tools/list` and the guidance with no engine; the first tool
call takes the project lock and opens the engine, and the server lets both
go after `--idle` quiet seconds so the agent's own `cadex` commands — which
take the same lock — get their turn, waiting with `--wait`. Every call goes
through the bridge in-process, so **the server sees every tool call**: it
prints a progress line per call on stderr, knows the session's last accepted
build, and lands that as one `PROGRESS.md` row and one project commit when
it lets the engine go. Stdout is the protocol's alone: the server writes to
a private copy of the descriptor and points descriptor 1 at stderr.

Until ADR-538 the CLI ran `claude -p` itself, with this server as a relay
shim that reached the engine over a unix socket in the parent; the shim,
the socket and the turn loop are gone.

### `expected_revision` is injected, not asked for

The protocol guards every mutation with the revision the caller believes is
current. That guard exists for concurrent writers, and a session holding the
project lock has exactly one. So the bridge tracks the revision from each reply — **including
refusals**, because a rejected candidate still becomes the working revision
— and fills it in. The value used comes back in every tool result as
`expected_revision_used`, so the model can still see drift; it just cannot
fail on it.

### Tool names are op names

`describe_api`, `write_script`, `edit_script`, `set_params`, `rebuild`,
`inspect`, `link_part`, `put_asset` — and then the six tools no engine op
backs (below): `look`, `draw_blueprint`, and the training loop's
`train_start`, `train_status`, `train_stop` and `evaluate` (ADR-464). The
deleted shell invented friendlier names because it had Blender's
vocabulary to reconcile; a second vocabulary would be a second thing to
keep in sync. The input schemas are **generated from `OP_ARG_SPECS`**, so they
cannot drift from the protocol — only the prose is hand-written, and the
one bridge-owned argument below.

`describe_api` reaches the model one page at a time (ADR-359, ADR-360).
The engine's reply is untouched and the op takes no argument; the bridge
offers a `section` argument of its own, consumes it, and cuts the view.
Without it the reply is the **index**: everything above the domains, and
each domain and the library listing their exports by name, with a
`sections` line saying where the signatures are. With `section=<domain>` or
`section=library` it is that **section**: the block's notes, globals and
output types, every export's name, full signature and the first paragraph
of its documentation, the whole catalog for the library, and a
`descriptions` line naming the `inspect scope=api` path that holds the rest
of any docstring. A section the contract lacks is refused with
`NO_SUCH_SECTION` and the list of sections. That refusal is decided
**after** the engine has answered: the bridge sends the argument-free
request first, because the section names come from the reply, and only
the `section` argument itself never reaches the engine.
The harness refuses an MCP tool result over its own token cap and writes
it to a file the product agent has no tool to read; the cap is not
published in characters, so the bridge's `API_VIEW_CHAR_BUDGET` (21,500
characters) is a measurement — on `ot7-heron-c` the harness refused
163,200 characters, then the ADR-359 view at 82,523, and accepted every
result up to 21,742. A live-engine test in `cli/tests/test_client.py` holds
the index and every section under the budget (13,239 and 3,337–20,502 on
2026-09-16) and checks that the sections between them carry every
signature, so the contract cannot grow past a size the harness has been
seen to accept without a test saying so. `section` is the one schema
property `OP_ARG_SPECS` does not carry; `VIEW_ARGS` in `cadex_cli.tools`
is the allowlist the drift test reads.

`display` and `expected_revision` are removed from the schemas: both are
injected by the bridge, never asked of the model. The revision comes from
the last reply; `display` is the constant standard request (`quality:
standard`, no edges) on every modelling op, so the accepted attempt the
review dashboard draws always retains tessellation (ADR-312). Anything the
model supplies for either is overruled, and the reply's `display` block is
dropped before the model sees it.

### Training refuses inputs the robot cannot read (ADR-408)

`cadex train` and `cadex walk` read the exported task before the trainer
starts, and refuse when a policy channel names no `api.sensor` that
measures it on the robot, listing the channels and both ways out: declare
the sensor, or mark a simulation-only channel `role="privileged"`.
`--allow-ungrounded` trains anyway and says so in the envelope's notes.

`cadex train --stop-on-collapse` passes the trainer's flag of that name
(ADR-410): the run stops, with the reason, once its mean episode has
collapsed, meaning the policy is ending its own episodes. `cadex walk`
always passes it, so an unattended walk fails at iteration ~60 rather than
spending hours on a policy that has learned to fall over.
The build is not where this bites: a task written before ADR-408 still
builds, and the policies trained on it still verify.

### Each checkpoint is rolled out while the run trains (ADR-544)

`cadex train --checkpoint-every N` and `cadex walk --checkpoint-every N`
pass the trainer's flag of that name, and a `train_start` run does the
same with the `checkpoint_every` setting. For a **local** trainer, a
watcher (`cli/cadex_cli/checkpoints.py`) then rolls each numbered
checkpoint `<out>.<tag>.cxpolicy` out through the engine, on the CPU, while
training goes on. The watcher is the same object in both places: `cadex
train` polls it from `run_trainer`'s wait, and the supervisor polls it from
its own loop.

- The child is `checkpoint_runner.py`, run by path under the engine's
  interpreter, `nice`d, with the GPU hidden. It plays one **nominal**
  episode (no seed: no randomisation, reset variation or shove), so every
  checkpoint of a run plays the same episode, at the largest frame rate
  that divides the control rate and is at most 30.
- It writes `<out>.<tag>.rollout-trace.json`, a
  `cadex-assembly-simulation-trace-v1` document whose `checkpoint` block
  gives the file, tag, iteration, reward per step and sha256. The iteration
  and reward come from the `progress.json` row whose digest is the file's.
  If the trainer has ended without listing it, the tag names the
  iteration and the reward is `null`.
- A checkpoint that cannot be played leaves
  `<out>.<tag>.rollout-failed.json` (`cadex-checkpoint-rollout-failure-v1`)
  with the reason, and no trace. A rollout past five minutes is killed and
  recorded as `rollout_timeout`. A watcher that fails is switched off with
  its reason in the envelope's notes. It never stops the trainer.
- One child runs at a time, newest pending checkpoint first. `best` (it is
  rewritten in place) and the final policy are not rolled out.
- After the trainer exits, the remaining checkpoints are rolled out with
  the machine's slot already released. The envelope's notes count the
  traces and the failures. An interrupted supervisor stops its child and
  rolls out nothing more.
- The traces end in `-trace.json`, which a project repository ignores.
  They are run outputs.
- A `--remote` trainer's checkpoints stay on the box, and nothing is
  rolled out for them here.

### `look`: the agent sees its design (ADR-406)

`look` is listed after the op-named tools and is answered by the bridge
itself (`BRIDGE_TOOLS` in `cadex_cli.tools`); no request reaches the engine
for it unless the session has not built yet. It renders the last accepted
modelling reply's display block with the `cadex render` studio renderer —
so it costs no rebuild — and returns MCP `image` content blocks, one 768×768
PNG per view, after one text block of facts. Views are `hero`, `iso`,
`iso_back`, `front`, `right` and `top` (default `iso` and `iso_back`, at
most five);
`focus` names components or outputs to frame a close-up on. Components the
`fit` block reports as `world geometry` (a floor) are left out, and the
`inventory` block colours parts: a component that declares an appearance
role is drawn in that role, in the assembly's palette (ADR-413); an
undeclared one is drawn as printed, in the `shell` bone, when its output is
in `uncatalogued_sources`, and as purchased, in the `mechanism` graphite,
otherwise (ADR-412; before it, filament orange and dark grey). The reply's
`colours` fact names each role's colour and how many components declared one,
and its `measures` fact gives the two image proxies above (P1 and P3, each
`value`, `bar`, `meets`), measured on the hero whatever views were asked for. A session that opens with `look` rebuilds once and reads the fit and
inventory a modelling reply would have carried, so the first look is drawn
the same way. hex2's four views take about 7 s.

Before ADR-406 the agent had no picture at all: its whole design
verification was `inspect` and the fit block, and hex2 (2026-09-25) passed
every check as a plate of bars and boxes. A live turn against a copy of hex2
confirmed an MCP client hands the images to the model: it described the
orange bars and the ball feet it had not been told about.

### The drawing sheet: `draw_blueprint` (ADR-516)

A dimensioned multi-view drawing of the accepted design, stored with the
project. `draw_blueprint` takes `name` (the sheet's identity and title) and
optionally `views` (1 to 4 of `front`, `right`, `top`, `iso`, `iso_back`;
default `top`, `iso`, `front`, `right`, the third-angle arrangement),
`callouts` (true, false or part names), `dimensions` (default true) and
`notes`. The engine's `CadexStudio.blueprint_report` draws it from the same
accepted reply `look` uses: line views on one shared scale, each
orthographic view dimensioned with the overall extents measured on the
tessellation, every declared `part.measurement(...)` drawn once in the
first orthographic view where it reads (listed instead when the design
places components, since its points are in a part's frame), numbered
balloons on the first three-quarter view keyed in a parts list, and a title
block with the sheet's name and version, the project, revision, digest,
date, scale and units. The bridge stores it with `put_blueprint`, whose
store versions it by name in `blueprints/` with the recipe in `meta`;
drawing again under a stored name stores the next version and takes any
key left out from that recipe. The model gets the facts and the sheet as an
image; `GET /api/project` lists every version (the page's **Drawings** panel
was removed by ADR-533).

### The training loop: `train_start`, `train_status`, `train_stop`, `evaluate` (ADR-464)

The agent driving the project runs the whole loop — design a task, train a policy on
it, evaluate the policy against the task's success spec, revise — and it is
**one loop for every behaviour**. None of the four tools, the registry
behind them or the paragraph that tells the agent about them names a
behaviour; `test_loop.py` refuses the words. All four are answered by the
bridge (`BRIDGE_TOOLS`), need no protocol op, and are listed by `tools/list`
beside the op-named tools.

| tool | what it does |
|---|---|
| `train_start` | Pre-registers one bounded run on the task **as accepted now** and launches it. Takes `run` (a new name), `budget_s` (wall clock, required — a run with no budget is not started), `reason` (the measurement that motivated the run) and optional `task` and `settings`. Returns at once. |
| `train_status` | Reads a run: its state, the trainer's progress (iteration, reward per step, mean episode length, exploration sigma, a thinned curve), its checkpoints, and when it finished the policy's path and sha256. It names the run's `task_bundle` (path and sha256), the file a warm start passes as `init_from_parent_task`, and says how to warm-start once there is a policy or a checkpoint. `wait_s` (at most 900) blocks until the run ends. Without `run`: every run of the project and the loop's ledger. |
| `train_stop` | Asks a live run's supervisor to stop it, with the reason. Checkpoints already written stay, and each is a complete policy. |
| `evaluate` | `cadex evaluate` for the agent: the accepted policy on every frozen seed, then the verdict, pass or fail per seed and per predicate, the behaviour metrics, the reward by term and how each episode ended in one bounded text block, followed by the overview and detail filmstrips of up to two filmed seeds as `image` blocks. The full report is the same `evaluation.json`, with its video, in `evaluations/`. |

**A run is a directory**, `runs/<run>/` in the project, where the review
dashboard already looks:

- `registration.json` (`cadex-training-registration-v1`) is written before
  anything is launched: the accepted revision and digest, the task and its
  digest, the settings and seed, the budget, the stop rule, the reason and
  the exact trainer command. `--stop-on-collapse` is always in it.
- `train/` holds the task bundle and the model, copied from the accepted
  attempt the store retained (never rebuilt), the trainer's own
  `progress.json`, its log, its checkpoints and the policy.
- `training-status.json` (`cadex-training-status-v1`) is the supervisor's:
  `finished` (the policy hashes to the trainer's receipt, and the receipt
  names the registered task), `collapsed`, `failed`, `stopped`,
  `budget_exhausted`, `interrupted` or `refused`, with the reason, the wall
  time and the iterations run.
- `run.json` is the dashboard's record, mode `loop`, written at
  registration and again at the end.

**The supervisor outlives the session.** It is `python -m cadex_cli.loop
RUN_DIR`, started in a process session of its own, so the agent, `cadex
mcp` and the terminal can all end while it trains; the next session reads the run with
`train_status`. It stops the trainer at the budget, on a stop request (a
file it polls — no process is ever signalled by pid), or when it is itself
told to terminate. It holds two advisory locks while it lives. The run's
lock is how a reader tells a live run from one whose supervisor was killed:
a status still saying `running` under a lock nobody holds is reported
`interrupted`, **an interruption and not an attempt**. The machine's lock
(`~/.cache/cadex/training.lock`, or `$CADEX_TRAIN_LOCK`) is the one
training slot: a second run is refused at registration, and again by the
supervisor if two were registered at once. `cadex train` holds the same slot
around a local trainer, so `cadex walk`'s train leg is refused while a
`train_start` run trains, and the other way round (ADR-543).

**What registration refuses**, each with a sentence the agent can act on: a
missing, zero or over-long budget (six hours is the bound on a typo); a
reason too short to name a measurement; a run name already used; a live
run on this project or on this machine; a training seed that is one of the
task's evaluation seeds; a setting the trainer does not have; and a task
whose policy reads a channel no declared sensor measures (ADR-408 — the
loop offers no override).

**The settings are the trainer's own flags**: `iterations`, `envs`, `seed`,
`label`, `hidden`, `unroll`, `epochs`, `learning_rate`, `discount`,
`gae_lambda`, `clip`, `entropy`, `value_weight`, `initial_std`,
`action_filter_alpha`, `command_slew_deg`, `goal_pool`, `checkpoint_every`,
and the warm start `init_from` with `init_from_parent_task` and
`init_from_task_change`. A test reads them back out of
`training/cadex_train.py`. A warm start with no `initial_std` continues at
the exploration width its source policy ended at; setting `initial_std`
overrides that (ADR-471).

**`loop-ledger.jsonl`**, in the project root, gets one line per thing the
loop did: a run registered (with its reason), a stop requested, a run
ended (with its state and the policy's digest), an evaluation measured
(with its verdict, its failing predicates and the run that trained the
policy). It is what `train_status` hands a new session, and what a report
reads the rounds back from.

Storing and declaring the policy stay the tools they were: `put_asset` the
path `train_status` reports, then `assembly.policy(task, weights=…,
sha256=…)` by `edit_script`. The engine verifies it there, so `evaluate`
measures a policy the engine accepted.

**`cadex walk` is one use of the same legs, not the loop.** It stays as the
scripted single pass — an optional change, train, declare, verify,
review — that
a caller drives with one command. Its `gait` block (ADR-409) knows one
behaviour, so the review now carries `behaviour`: for a task that declares
a success spec the authority is the spec, through `cadex evaluate`, and the
gait reading is advisory; for a task with no spec the gait reading is the
only one. The loop never reads either.

**Limits.** The loop trains on this machine only; `--remote` dispatch is
still `cadex train` and `cadex walk`.
`evaluate` blocks for as long as the rollouts and the film take: 189.8 s
for Robin's ten seeds and its film. A tool call is allowed to block that
long: an MCP tool call through Claude Code held for 900 s, `train_status`'s ceiling
(`docs/probes/ot11/runner/block_probe.py`, 2026-09-30).
`trained_by_run` in the ledger names every run whose final policy or any
checkpoint has the evaluated digest. Checkpoints are read from the files in
`runs/<run>/train/`, each with its own digest, because the trainer writes a
checkpoint before it rewrites `progress.json` and a run stopped between the
two leaves its last checkpoint unlisted there; `train_status` lists them the
same way. A ledger row written before this fix (2026-09-30) is not rewritten.
A warm start needs the parent run's task bundle, `runs/<run>/train/<task>-task.json`,
as `init_from_parent_task`. `train_status` names it as `task_bundle` (and the
listing without `run` gives each run's path); a path that does not exist is
refused with every run's bundle in the refusal. Before this (ot11 `reach-r3`)
the agent guessed five paths, was refused each time, and trained from scratch.

### Every build reply carries the measured fit (ADR-346)

After a successful `write_script`, `edit_script`, `set_params` or `rebuild`,
the bridge reads `inspect scope=clearance` — the engine's own pair
measurements of the accepted assembly's exact solids at the solved pose,
published with the revision the build just accepted — and adds a `fit`
block to the reply the model sees, beside the script's `stdout`:

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

`verdict` is `pass` only when every pair was measured and every pair is
clear at the `cadex clearance` defaults; `fail` names the pairs that are
not — an intersection, a distance below the minimum, or a pair the engine
could not measure, with its reason — **worst first**: unmeasured and
world-geometry rows, then the largest common volume, then the smallest
distance. `failing_count` and `counts` are always the whole block. The
model's view carries at most `BUILD_VIEW_LIST_LIMIT` (12) rows; past that it
adds `failing_omitted` (how many were cut) and `failing_rest` (the `inspect
scope=clearance` path that lists them). The run report and the envelope's
`fit` keep every row. See "A build reply fits one tool result" below for
why (ADR-435, amending ADR-346's never-cut-short rule). `unavailable` means the revision places no assembly
components, so nothing was checked; it never means pass. A measurement the
bridge cannot read is also `unavailable`, with the error, and the build is
still accepted: **a failing fit is reported, never refused.** The block is
computed from the published measurements and never from `stdout` — a
script that prints "no overlap" over two solids that share 100 mm³ is
handed both, and the guidance tells the model which one is the claim.
`clearance` is an `inspect` scope on the model's surface for the same
reason, and the last accepted build's block is the envelope's `fit`.

The bridge resolves all inspection pages before reporting fit. A later page
can contain an intersection, a missed declared contact or an unmeasured pair
even when the first page is clear; world-geometry findings are included too.
If any later page cannot be read, the whole fit block is `unavailable` with
the read error, rather than a verdict on the readable prefix. The successful
build and its accepted revision still reach the agent. The paged build-reply
fixture in `cli/tests/test_clearance.py` pins both outcomes.

### A build reply fits one tool result (ADR-435)

The agent harness refuses an MCP result past its own cap (measured near
21,700 characters, ADR-359) and writes it to a file the product agent
cannot read. On `ot10-biped-3` (2026-09-28, 215 outputs) a `rebuild` reply
came to 85,954 characters. Of those, 60,669 were `outputs` and
`live_outputs`, two echoes of every declared name. The agent then read its
fit by paging `inspect scope=clearance`. The engine reply is unchanged;
the **model's view** of a successful `write_script`, `edit_script`,
`set_params` or `rebuild` is bounded:

- `outputs` becomes `{count, by_kind, names?, not_live, detail, note}`.
  `by_kind` counts outputs by `domain type`. `names` is listed only for 40
  outputs or fewer. `not_live` names any declared output with no live
  object. `detail` keeps any output row carrying facts or diagnostics.
  `live_outputs` is dropped; one output's full row is `inspect
  scope=output target=<name>`.
- `fit.failing`, `fit.world_geometry_contacts`, `fit.sweep.failing`,
  `fit.sweep.world_geometry` and `fit.attachments.reported` are worst
  first, at most 12 rows, with `<list>_omitted` and `<list>_rest` when cut.
  `fit.sweep.joints` lists only joints not swept to completion.
- `inventory.appearance` becomes a count per role.
  `inventory.printed_edges` keeps its totals and `measured_count`, plus
  `sharpest`: the printed parts with the most sharp convex edge.
  `uncatalogued_sources` and `derived_catalog_sources` are cut the same
  way. Every row is `inspect scope=inventory path=/components`.

Every verdict, count and threshold is the whole block's. Nothing is
re-judged. The same two revisions measured: `ot10-biped-3` falls from
85,954 to 12,163 characters and `ot10-hexapod-11` from 82,981 to 13,758.
`cli/tests/test_build_view.py` holds a 215-output reply under
`API_VIEW_CHAR_BUDGET` and fails on the old view.

### The same reply carries the swept fit (ADR-366)

The `fit` block's `verdict` is the solved pose and stays that. Inside it,
`fit.sweep` is the swept half, read from the `clearance_sweep` the same
`inspect scope=clearance` value already carries — no second engine call:

```json
"sweep": {
  "verdict": "fail",
  "source": "engine measurements of the exact solids at poses across each limited joint's declared range, …",
  "coverage": "incomplete",
  "step_degrees": 5, "step_mm": null,
  "joints_checked": 2, "joints_complete": 1,
  "joints": [
    {"joint": "knee", "kind": "revolute", "unit": "degrees", "status": "complete",
     "pairs_measured": 3, "step": 5, "sample_count": 23, "range_degrees": [-90, 20],
     "initial_degrees": 0, "pairs_moving": 3,
     "minimum_distance_mm": 0.0, "maximum_common_volume_mm3": 42.5,
     "first_contact": {"value": -70.0, "unit": "degrees", "pair": ["shin", "foot"]}},
    {"joint": "rail", "kind": "slider", "unit": "mm", "status": "incomplete",
     "pairs_measured": 0, "pairs_moving": 0,
     "minimum_distance_mm": null, "maximum_common_volume_mm3": null,
     "reason": "sweep_step_mm is not declared on the assembly, so this limited slider joint was not swept"}
  ],
  "failing_count": 2,
  "failing": [{"joint": "knee", "first": "thigh", "second": "shin", "status": "intersection",
               "minimum_distance_mm": 0.0, "maximum_common_volume_mm3": 42.5,
               "first_contact_degrees": -55.0},
              {"joint": "knee", "first": "thigh", "second": "cover", "status": "below clearance",
               "minimum_distance_mm": 0.04, "maximum_common_volume_mm3": 0.0,
               "minimum_mm": 0.1, "distance_mm": 10.75, "first_contact_degrees": null}]
}
```

`verdict` is `pass` only when every limited joint was swept to completion,
no pair interpenetrates anywhere in its range **and no pair closes below its
minimum there** (ADR-378). `fail` names the failing pairs, with the joint
each is through and the joint value it first touched at, worst first and
cut on the same terms as the static list (ADR-435). It does not hide
missing coverage: in the model's view `joints` lists every joint **not**
swept to completion, with its reason, and `joints_complete` counts the
rest, whose rows are `inspect scope=clearance path=/clearance_sweep/joints`.

A `below clearance` row is a gap the motion closed: the pair's own minimum —
its declared `clearances=` value, or `minimum_clearance_mm` for a pair with
nothing declared — not met somewhere in the range, with `distance_mm` beside
it saying what the solved pose measured. Before ADR-378 the block held the
minimum it measured against nothing, so a hinge that took two parts from
10.75 mm apart to 0.04 mm — a quarter of the gap the static block holds the
same undeclared pair to — printed that 0.04 mm beside `verdict: pass`. The
rule is the narrowest one that closes it, so the swept block stays strictly
additive to the static one: only a pair **this joint moves** is judged, only
a pair the static block calls **clear** is judged (one that already fails at
the solved pose is named there, once), and a pair declared `contact` or
carrying a fixed joint's implied `attached` intent (ADR-372) is exempt here
exactly as it is there. On every ot7 receipt retained before this change the
new rule adds no failure.
`incomplete` means a joint the engine could not sweep, carrying the engine's
own reason. `unavailable` is the verdict when there is no joint row to judge
at all, and it covers **two** different facts that `coverage` beside it tells
apart (ADR-368): `coverage: unavailable` is a revision accepted by an older
engine, which published no sweep — the only thing the *raw* published
`clearance_sweep.status` ever means since ADR-367 — while `coverage:
complete` with no joint row is a current revision whose assembly declares no
limited joint. `reason` says which in words, and the one-line progress phrase
reads `sweep unavailable: no published sweep` or `sweep unavailable: no
limited joint` rather than a bare `sweep unavailable`.
A joint row's `minimum_distance_mm`, `maximum_common_volume_mm3` and
`first_contact` are read over the pairs **that joint actually moves**, and
`pairs_moving` says how many of `pairs_measured` those were (ADR-374). A pair
with both sides on the same side of the joint — a horn welded to the link it
turns with, two parts of one swept subtree — is rigid for this sweep and
repeats its solved-pose measurement at every sample. Rolling it in would pin
the joint's minimum at the weld's 0.0 mm and name first contact at the bottom
of the range, where the sweep merely started, which is the weld and not the
motion; the gap under a weld is the `attachments` block's fact, measured at
the pose where it means something. `failing` spans every pair that
overlaps, because an overlap is an overlap. A pair row from a revision
accepted before ADR-374 carries no `relative_motion` flag and counts as
moving, so an older receipt reads as it always did — including under
ADR-378, whose three narrowing rules are what keep a flagless rigid row from
failing: it repeats a solved-pose number the static block already judged.

A swept finding against **world geometry** — a pair one side of which the
static block names `world geometry`, such as a declared floor — is published
in `world_geometry` (with `world_geometry_count` and a `world_geometry_note`)
and never in `failing`, so it moves neither `failing_count` nor the verdict
(ADR-420). Each joint is swept with the rest of the body held at the solved
pose, so a standing leg's knee drives its foot into the floor by
construction: that is the stance, not a fit between two parts. Each finding
carries the engine's reason as `world_geometry: {component, reason}`; the
joint row's own extrema still include it, and the progress line reads
`sweep pass: 12 joint(s) swept; 12 against world geometry (advisory)`. A
printed or purchased pair still fails as above.

The static block applies the narrower half of the same rule (ADR-427). A
solved-pose pair against world geometry whose only finding is `below
clearance` -- a foot standing on the floor at 0.0 mm with no common volume --
is published in `world_geometry_contacts` (with
`world_geometry_contact_count`, a `world_geometry_note`, and
`counts["world geometry contact"]`), carries `world_geometry: {component,
reason}`, and is never in `failing`. An intersection with world geometry at
the solved pose is the pose the simulation starts from, so it still fails,
and so does an unmeasured pair. The progress line appends `; 6 resting on
world geometry (advisory)`. The world geometry's own row stays in `failing`
as it was.

None of these is a pass: a joint that was not swept has been checked at one pose
only. The block is advisory like the static one — a failing swept fit is
reported, never refused — and the prose report prints it as a `sweep` line
under the `fit` line.

A joint row that declares **no limits** is a joint that can still move and
was never bounded (ADR-375): a wheel, a free spinner, a loop-closure hinge.
It reads `incomplete` with the declaration to add named per kind, it counts
as missing coverage rather than as `joints_skipped`, and the line says so
(`sweep incomplete: 2 of 3 joint(s) unswept`). Before this the engine dropped
it before it reached a row, so a chassis whose one limited hinge swept clean
read `sweep pass: 1 joint(s) swept` while the two parts that turn against it
had been measured at the solved pose and nowhere else. A weld and a
suppressed unlimited joint stay out of the report: neither holds a range, and
a weld's pair is the attachment block's fact (ADR-370).

A joint row whose `status` is `skipped` is a **suppressed** joint (ADR-371):
the solver ignores it, so it holds no range to sweep and its absence is not
missing coverage. It is counted in `joints_skipped`, apart from
`joints_complete`, the verdict is judged over the joints that are left, and
the progress phrase says both without saying either in the other's words
(`sweep pass: 1 joint(s) swept; 1 suppressed`). An assembly whose limited
joints are *all* suppressed has rows and judges none: that is the third fact
wearing `unavailable`, reading `sweep unavailable: every limited joint
suppressed (N)` with its own reason. Before this the engine handed a
suppressed joint to the sweep child anyway, the child refused it, and one
suppressed joint held the whole block at `incomplete` — telling the agent to
declare a step it had already declared.

An assembly that declares **neither** step is the case ot7's F5 create turn
measured, and since ADR-367 it is `incomplete` rather than `unavailable`:
the engine publishes coverage either way, so every limited joint is named
with the declaration it is missing (`sweep incomplete: 2 of 2 joint(s)
unswept`) instead of the reply saying only that a sweep is absent. It costs
no measurement — with no step to sweep at, no geometry is touched. An
assembly with no limited joint at all reports complete coverage of an empty
set, which the block reads as `unavailable` with its own reason: there is no
motion to check, and that is a different statement from a swept mechanism.

### Every build reply carries the published catalog identity (ADR-362)

Beside `fit`, the same four replies carry an `inventory` block, read from
`inspect scope=inventory` under the same lock, so it describes the
revision the reply accepted:

```json
"inventory": {
  "available": true,
  "source": "the published inventory of the accepted revision (inspect scope=inventory) …",
  "revision": "…", "assembly": "asm",
  "component_count": 6, "catalogued_count": 3, "uncatalogued_count": 3,
  "catalog_counts": {"bearing/MR128": 2, "horn/SG-25T-1": 1},
  "uncatalogued_sources": ["base_plate", "servo_drilled"],
  "derived_catalog_sources": [
    {"source_output": "servo_drilled", "family": "servo", "part_number": "MG90S"}
  ],
  "note": "Each name under uncatalogued_sources is a placed output no lib.* generator built as-is. … derived_catalog_sources names the ones the engine can prove are exactly that: servo_drilled (cut from servo/MG90S). …"
}
```

`catalogued_count` counts placed components whose output is what a `lib.*`
generator built; `uncatalogued_count` is the rest, per component;
`uncatalogued_sources` names the distinct outputs behind them, so one
drilled servo body placed twice is two uncatalogued components and one
name. **The block is advisory.** It has no verdict and names no failure: a
printed bracket is expected there, and the build is accepted whatever it
lists. What it carries is the one fact ot7's F5 showed the agent cannot
otherwise see — over four turns the agent's closing message said every
purchased part was a catalog part while the published inventory listed
both servos and both horns as uncatalogued, because the script had cut a
bore into the servo bodies and re-clocked the horns, and a cut catalog body
is no longer the catalog part. The block is computed from the published
inventory and never from `stdout`.

`derived_catalog_sources` (ADR-381) says **which** of those names is that
defect. An uncatalogued source is one of two very different things — a
printed part, which belongs there, or a purchased part the script modified,
which does not — and the bare list cannot tell them apart. The engine
resolves catalog identity by exact definition, so it can also follow the
*base operand* of a definition down (`part.cut(base, tools)` puts the body
being modified first) and name the nearest catalog body it came off. A row
is `{"source_output", "family", "part_number"}`, sorted by source; a catalog
body used only as a **cutter** appears on no base spine and is listed
nowhere, which is the distinction between hardware and a clearance tool.
**Absence is unknown provenance, not proof of a printed part** (ADR-382):
the spine is the only path followed, so a catalog body fused into a printed
solid as a *second* operand is a purchase this list cannot name, exactly as
ADR-243's boundary and ADR-381's own limits say. The guidance says the
same, and tells the agent to read the script that built an unlisted name
rather than read the silence as a pass.
The list is empty rather than missing when nothing derives, and the block's
`note` repeats each row in words. Every component row of `inspect
scope=inventory` carries the same fact as `catalog_derived_from` beside the
absent `catalog`, and `cadex inventory`'s table prints it as *cut from
servo `MG90S`*. Still advisory: nothing here is a check and nothing is
refused.

`available` is false, with the reason,
when the revision places no assembly components or the inventory could
not be read; neither refuses the build. `inventory` is an `inspect` scope
on the model's surface for the same reason, and the last accepted build's
block is the envelope's `inventory`.

### What the agent is told

One text (`guidance.py`, ADR-538), printed by `cadex guidance`. `cadex mcp`
sends a brief of it as the server's `instructions` in its `initialize`
reply, which an MCP client puts in the model's context, and the brief tells
the agent to run `cadex guidance` first: a client's cap on instructions
(2,048 characters in Claude Code by default) would cut the whole text. A
client that reads instructions from a file can take the printed text into
an `AGENTS.md` or a skill instead.
**It never states the xscript API.** The agent asks the engine for it with
`describe_api`, whose index carries the live `instructions`,
`program_schema`, `source_globals`, `result_contract`, `revision_rule` and
parameter prose — which is what keeps one contract from becoming two.

Most of the text -- from *you see your work with `look`* through *when a
call is refused* -- is the engine's agent guidance,
`Mod/cadex/CadexAgentGuidance.md` (ADR-446), read from the engine the CLI
resolved, with the tool names filled in. Around it is the situation: the
person watches the read-only dashboard and talks to the agent directly,
*build it parametric*, purchased hardware, `describe_api` first, the CLI
for the legs the tools do not cover (with `--wait`), assets and policies,
the project docs, revision guards and when to stop.

The overlay says:

- **Build it parametric**, because the cheap sweep only exists if the
  expensive turn made one possible.
- **You see your work with `look`, and prove it with facts** (ADR-406).
  Until ADR-406 this said the agent could not see; it now renders the
  accepted design for itself, and `inspect scope=output` and the fit block
  remain the evidence for numbers.
- **Design it; do not only make it fit** (ADR-406, ADR-479). The
  design language of `docs/DESIGN-LANGUAGE.md`, taught from the inside out
  as six steps in order: a **concept** before any geometry (what the
  machine is, its palette, and its finish, an exposed mechanism or a
  panelled hard surface, recorded in the project's `DECISIONS.md`); the **parts**, each
  purchased part and the cable path chosen from the catalog; **placing**
  them and checking their fit alone; the **structure that carries them**
  (hold every part by something named, nothing stuck on, mirror what has
  sides, one joint cap per axis, load-carrying limbs with designed feet,
  printable); the **finish** (not the mascot box, no face, hardware that
  shows is ordered, detail is real, finished edges, two materials and one
  small functional accent by appearance role); and **refinement with
  `look`**, which reads the `measures` first, then names the crudest
  thing, fixes it and looks again. Tests hold the order, hold that no face
  or hidden-hardware rule comes back (ADR-480 to ADR-483), hold that the
  overlay quotes no owner rating, sweep id or judge text, and hold that
  every paragraph and bullet is a finished sentence.
- **Fit is measured, not printed** (ADR-346). The `fit` block on every
  build reply is the evidence that parts fit; the script's `stdout` is a
  claim the script makes about itself, and a `fit` naming a failing pair
  overrules any printout that says otherwise. The guidance no longer tells
  the agent to verify by printing.
- **Catalog identity is measured too** (ADR-362). The `inventory` block on
  every build reply says which placed components are catalog parts and
  names every output no `lib.*` generator built as-is; it is advisory,
  printed parts belong there, but a purchased part listed there has lost
  its catalog identity whatever the script prints, and the agent is told
  to read it before it says hardware comes from the catalog.
- **A file comes in by path, and you train and evaluate yourself.**
  `put_asset` is how a trained policy, its provenance or a mesh enters the
  project, and its reply's `sha256` is the digest the script names. Since
  ADR-464 the agent is no longer told it cannot train: one paragraph gives
  it the loop — design the task and, separately, its success spec; train
  with `train_start`; evaluate with `evaluate`; revise from that
  evaluation and say in the next run's `reason` which measurement
  motivated the change — and says a reward curve is never evidence.
- **The CLI covers what the tools do not**: `render`, `section`,
  `export`, `clearance`, `inventory`, `revision`, the dynamics legs, each
  with `--wait` because the server holds the project while it is busy, and
  never an invented flag (ADR-190 — the audit caught it doing exactly that).
- **The project is a codebase.** The agent reads `ARCHITECTURE.md`,
  `DECISIONS.md` and `PROGRESS.md` before acting (ADR-193), records each
  decision in `DECISIONS.md` itself and its longer notes under `docs/`;
  the CLI writes `PROGRESS.md`. Before ADR-538 the CLI pasted the documents
  into the prompt and scraped `DECISION:` and `NOTE` lines out of the
  turn's closing text, because its agent had no file tools.
- **Ask when the answer would change the design**; otherwise carry on with
  the most reversible assumption and say which.
- **Revision guards are handled for you.**

## 5. Sessions, locks and state

`<project_root>/agent.json` is the CLI's own file, holding the project's
engine budgets (ADR-517):

```json
{"schema": "cadex-cli-agent-v1", "updated_at": "2026-10-04T12:36:31Z",
 "budgets": {"timeout_seconds": 900.0}}
```

It is a **sibling** of the engine's `script.json`, never a replacement: the
CLI reads engine state through `inspect` and writes only its own. Before
ADR-538 it also kept the Claude Code session the CLI's own turns resumed; a
file an older CLI wrote is read for its budgets, and its conversation is
dropped on the next write. The conversation is the agent's business now.
Opening a project may refresh accepted restore attempt metadata in
`script.json`; a refused walk does not roll that bookkeeping back or create
a failure commit.

`<project_root>/.cadex-cli.lock` is an advisory `flock`, because `cadexd` is
one process per project and a sweep will run several of these at once. The
kernel releases it on process death, so there is no stale-lock heuristic to
get wrong. A second run is refused with a readable message; `--wait` blocks
instead. A command holds it for its one run and releases it before the
`PROGRESS.md` row and the commit; `cadex mcp` holds it while it has the
engine open, lands its row and commit, then releases it, and opens again
waiting for it (§4).

The machine's **training slot** (`~/.cache/cadex/training.lock`, or
`$CADEX_TRAIN_LOCK`) is a second advisory `flock`, one per machine rather
than per project: one training run at a time (ADR-543). A `train_start`
supervisor holds it while it lives (§4), and `cadex train` holds it while
its local trainer runs, not during the rebuild or the `put`. While another
run holds it, `cadex train` and `cadex walk` exit 3 before doing anything:
`train` before its rebuild, and `walk` before its first leg, so a refused
iterate walk has not moved the accepted revision. `--remote` trains on the
box and takes no slot here, and neither does `train --dry-run` or
`walk --complete`. There is no `--wait` for the slot.

## 6. Which engine

In order: `--engine`, then `CADEX_ENGINE_ROOT`, then the development tree
(`.pixi/envs/default/bin/FreeCADCmd` or `build/release/bin/FreeCADCmd`, plus
`src/Mod/cadex`). The first two name a **staged payload root** and are read
through its `cadex-engine.json` manifest, which is the payload's discovery
contract (ADR-020) — the same resolution
`test_cadexd_lifecycle.py` uses.

Resolution rejects unequal, nonempty manifest `protocol` and module
`CadexdProtocol.PROTOCOL_SCHEMA` strings. Agreement proves neither worker
completeness nor shared source provenance. The envelope identifies the resolved
engine.

Every reply is shape-checked against **that engine's own**
`OP_RESPONSE_SPECS`, and a violation is an error rather than a warning. A
client that quietly tolerates an undeclared key is a client the protocol
has stopped being a contract for.

## 7. Running the suite

```bash
pixi run python -m pytest cli/tests
```

Fast, and honest about what it did not run.

| File | What it drives |
|---|---|
| `test_engine_resolution.py` | Hand-built payload directories; no engine needed. |
| `test_mcp_protocol.py` | `cadex mcp`'s wire, the stdio loop and its idle callback, and the bridge against `fake_cadexd.py`; no engine needed. |
| `test_agent_guidance.py` | The guidance: the engine's text carried verbatim, nothing left from the CLI's own turns, and `cadex guidance` printing exactly what `cadex mcp` sends. |
| `test_dashboard_read_only.py` | The read-only dashboard (ADR-537): every former write route refused for every method with the project unchanged, and in Chromium an open page following a `cadex params` run outside it. |
| `test_client.py` | A real `cadexd`. **Skips** without a built engine. |
| `test_export.py` | Plan-building directly; conversion against a real engine. |
| `test_commands.py` | `main()` end to end against a real engine. |
| `test_walk.py` | `cadex walk` against a fake `cadex` (leg order, flags, refusals; no engine), and the toy through two real walks with the real engine and trainer — **skips** the latter without the training venv. |
| `test_review_server.py` | The review dashboard (ADR-286): the API, the allowlist and its refusals, the CLI command, and the page in a headless Chromium over its DevTools pipe (`cdp_browser.py`) — **skips** the browser half without a Chromium (`CADEX_BROWSER` names one); the private-address smoke runs only with `CADEX_REVIEW_HOST` set. |
| `test_review_lifecycle.py` | The dashboard across restart and copy (D6/D7): the real `cadex review` command stopped and restarted on the same port while an independent telemetry producer keeps writing; the open page recovers without reloading, a fresh page reads the same project, the producer is neither stopped nor duplicated, and no project file changes. Whole-directory copy coverage checks independent accepted fixtures and historical model/curves/video access with the original path unavailable. **Skips** without a Chromium or FFmpeg. Fixture coverage, not the required fresh-biped pass. |
| `test_review_history_scale.py` | Bounded operation over a long run history (ADR-321): sixty-three runs with 512-sample histories and three verified checkpoints each. Over HTTP, the run list carries a telemetry summary under 1.5 KB per run with no histories and no checkpoint hashing, the per-run detail carries both, and missing/invalid/mismatched states survive the summary. In the browser, a deliberately selected historical run keeps its selection, histories and playing video while twenty runs are added and the newest run's telemetry grows; an idle poll adds no more DOM nodes after the growth than before; a fresh visit selects the training run and the current-run button reaches it with its growing history within five seconds. **Skips** the browser half without a Chromium or FFmpeg. |
| `test_evaluate.py` | `cadex evaluate` (ADR-457) in three layers: what it reads from a hand-built retained attempt (no engine); the child run for real on the engine suite's own fixtures, which needs `mujoco` here and **skips** without it; and the command against a script a live engine accepted with a policy it verified — **skips** without a built engine. |
| `test_loop.py` | The training loop (ADR-464) in three layers: the registry and the supervisor against a hand-built retained attempt and a fake trainer, with the supervisor really detached — registration whole before launch and each refusal, a run outliving the process that started it, stop, budget, collapse against crash, SIGTERM and SIGKILL as interruptions, one run at a time per project and per machine; the four tools through `Bridge.call`; and whole rounds through the `cadex mcp` session host against a live engine — a run started in one session, its policy declared and evaluated in the next — which **skip** without a built engine, the real-trainer round also without the training venv. It also refuses behaviour words in the loop, its tools and its guidance paragraph. |
| `test_film.py` | The evaluation's film (ADR-459) on a hand-built retained attempt and hand-written traces, with no engine: which seeds `--film` picks; the solids read from the attempt's own tessellation and refused outside it; materials from the inventory; both sheets' frame times, views, floor and dark backdrop read back from the PNGs; the detail window centred on the evaluation's base while a part is left behind, fixed for a mechanism with no floating base, and refused for a base that is not drawn (ADR-460); the early-ending and no-disturbance windows; the target marker (ADR-463): a ring read back from both sheets' pixels at the projected target of each frame's own time, hollow, drawn over the solids, jumping where the target does, held in a fixed window and in the video's, absent from a trace with no point goal, and refused for a point goal the trace cannot place; the trace digest check; the report rewritten with its film; `--film-only`'s refusals. The video tests need FFmpeg and **skip** without it. |
| `test_review_evaluation.py` | The dashboard's view of an evaluation (ADR-459; its page panel was removed by ADR-533, the API still serves it). The failing fixture is ot10's `w2-2` shuffle, from the receipt under `docs/probes/ot11/retained/`; a passing one is written in the test. Over HTTP: the bounded summary list, the whole report, the file allowlist and its refusals, one parse per file identity. In headless Chromium at 1400×900 and 400×850: every predicate's tally, every seed's verdict, ending and per-predicate values, the metrics and reward tables, the film, the reader's pick. The page half **skips** without a Chromium. |
| `test_video.py` | Rollout video rendering (D4) on synthetic fixtures: decoded frames and timing, retained identity, the failed-rerender record, and in the same headless Chromium inline playback across polls and a download the browser wrote, checked byte for byte. **Skips** rendering/playback without both Chromium and FFmpeg. Fixture coverage, not fresh-biped evidence. |

`tests/fake_cadexd.py` is a scripted engine, not a loose mock: its replies
go through the same `validate_response` path production uses, so a fixture
that has drifted from `OP_RESPONSE_SPECS` fails there rather than passing
there and failing live.

Everything that needs an engine **skips** without one, so a green run on a
bare checkout proves less than it looks like.

CI runs the suite in both jobs of `.github/workflows/cadex-app.yml`, after
the engine build for that reason. The Linux job runs it twice — once against
the build tree and once against the staged payload — on the same argument
the packaged engine gate rests on: a source tree that passes proves nothing
about a payload (ADR-023).

## 8. Limits

- **Linux and macOS.** The lockfiles are POSIX `flock`. Windows is not
  supported.
- **No `inspect scope=image` and no `resolve_pin` in the model bridge**
  (§4): both need a viewport this client does not have. The agent's
  picture is `look` (ADR-406), drawn from the accepted reply, and its shell
  runs `cadex render` for the files. Blueprint *sheets* are stored too (ADR-150, ADR-516): the bridge's
  `draw_blueprint` composes one and stores it through `put_blueprint`,
  `inspect scope=blueprint` lists them and `export --blueprints` copies
  them out, because a stored deliverable is not a render. `put_blueprint`
  itself is not a model tool: a path to an arbitrary PNG is not one.
- **Export converts BREP and copies the rest.** Only BREP outputs are
  converted (STEP, STL, BREP); every other staged artifact is copied as
  staged (§3), and outputs with nothing staged — assembly components and
  solve diagnostics — are reported as `skipped` with a reason rather than
  silently dropped. Export runs as a short `FreeCADCmd` job rather than a
  protocol op; promoting it to `export_model` is its own PR, and
  `export.py` is one seam so that it can be.
- **The CLI does not ship in the engine payload.** It runs from the
  repository — and so does `train`'s trainer, which it finds by path from
  the repository root and runs under a venv the engine's environment
  deliberately lacks (ADR-084). No venv, no `train`; it does not build one.
  `--remote` finds `training/remote_train.sh` the same way and configures
  nothing: the box, its venv and its scratch directory are
  `training/.remote.env`'s (ADR-089); a warm start travels with the
  bundle (ADR-268).
- One `--set` per parameter, and parameters are numeric — that is what
  `num(...)` declares. A switch is a `num` with `min=0, max=1, step=1`
  and a `>= 0.5` test in the script (ADR-192).


### Shared review scene and rollout recording (ADR-301)

```bash
PYTHONPATH=cli pixi run python -m cadex_cli.video --project ~/cadex-projects/biped --run RUN
```

The viewport and newly recorded videos use the same locally shipped Three.js
r160 scene, **dark only** (ADR-331): the near-black prototype-grid mat with
its PROTOTYPE / pitch labels and a subdivision chosen from the framing, sky
gradient, distance-scaled fog, ACES exposure 0.95, rough component materials
and a fitted 2048² shadow map. The style a video records is
`cadex-prototype-dark-v1`; earlier `cadex-prototype-light-v1` recordings stay
retained and labelled with their own style. The environment is adapted from
the MIT neural-whoop reference; the dark look is compared with it frame by
frame in [docs/probes/ot6/look](probes/ot6/look/README.md) and the earlier
light comparison stays in [docs/probes/review-style](probes/review-style/README.md).
CAD geometry stays in millimetres with unchanged poses; the renderer applies
one uniform conversion to metres. The environmental floor sits just below the
model bounds, and is front-sided so below-floor CAD inspection remains possible.
The finite model ground slab remains geometry, with its own edges and identity.

Recording requires headless Chromium (`CADEX_BROWSER`, PATH, or the existing
Playwright browser cache) and FFmpeg. It needs no desktop, Python browser package,
engine, trainer or internet. The existing DevTools pipe driver is now product
code, shared with the tests. A loopback server serves only the configured
project and shipped static allowlist while capture runs; it closes afterward,
and a dashboard already serving the project is unaffected.

Python verifies retained model/policy/task/seed identities and solved poses
and validates every retained solid (up to 500 000 triangles in all — a real
model such as Finch is 95 212, ADR-336); the capture page then fetches each
of those solids over the loopback server and reports the triangle count it
built, which must equal the validated file's. The trajectory bounds and the
subject's centre track are computed in the scene, exactly, over every vertex
at every solved pose (`boundsOver`), not in Python — which is what the
earlier 20 000-triangle cap had paid for. Python sends exact solved samples
at 10 fps plus the final pose to the common scene, which frames each one
with the **follow rig** (ADR-332, `docs/DASHBOARD.md` §10): the subject's standing height fills a declared 0.22 of the frame
height at one standoff, the orientation is fixed, the anchor is a
Hann-smoothed copy of the track with a soft drift limit, and a **timer** pill
bottom-left shows simulation seconds. It encodes
512×512 VP9 WebM and decodes every frame before publication. The per-project
render lock and 300-second frame-production budget remain; encoding and decode
each have a separate 60-second timeout. Render failures report their own status
and preserve prior videos without touching training.

Each new video records style version/digest, Three.js and Chromium versions,
resolution, projection, the first frame's camera, the rig's declared and
measured framing (`framing`: fraction, standing height, standoff, drift and
apparent-size extremes), the overlay, **what it shows** (`showing`: the
tessellated solids of the accepted revision, collision proxies not drawn;
`proxies.retained` counts the run's proxies that were *not* drawn — the
renderer never hands them to the capture and refuses to publish if the
capture reports anything else, ADR-333), and trajectory bounds alongside
revision, policy, seed, trace digest and simulation time. New recordings appear first;
earlier entries and content-addressed files remain retained and downloadable.
Identical video bytes are deduplicated. Old entries lacking a style are labelled
“historical legacy style”. Copy the full project directory to retain all of them.

### Declared fit intent (ADR-347)

The published clearance scope includes each pair's `intent` and `fit_failures`,
plus `world_geometry` findings by component name. Build-reply fit summaries and
`cadex clearance` respect declared contacts (0.001 mm tolerance) and declared
minimum clearances; undeclared pairs use the default 0.1 mm — except a pair an
unsuppressed `fixed` joint welds, which the engine publishes with the implied
intent `{"kind": "attached", "minimum_mm": 0.0, "joints": [...]}` and which no
minimum applies to (ADR-372), including a `--min-clearance-mm` override. Its
verdict is `clear` unless it interpenetrates or could not be measured, and
`cadex clearance` writes `welded by <joint names>` as its detail.

An explicit `contacts=` or `clearances=` entry on a welded pair still wins,
and a `clearances=` one is judged by the minimum it declares exactly as an
unwelded pair's is (ADR-380, withdrawing ADR-379): a fixed joint fixes a
relative pose without requiring the solids to touch, and a declared minimum
is a floor on a distance rather than a claim that the pair moves, so
"rigidly held, and at least 0.5 mm apart" is one coherent design. Such a row
carries the welding joints beside its declared minimum, and `cadex
clearance` writes `declared minimum <n> mm, and welded by <joint names>` as
the detail — a fact to join, not a verdict. ADR-379 briefly made that pair a
failing check of its own, `clearance under weld`, on the reading that a weld
and a gap contradict each other; that status no longer exists. What names a
weld whose solids do not meet — F4's Heron horn, 0.2 mm off its link through
all four repair turns — is the `attachments` report, beside the four checks
and never one of them.

A clearance
deficit must exceed an absolute 1e-9 mm comparison slack to fail (ADR-353),
including when `--min-clearance-mm` overrides the default. Published measurements remain
unrounded. Swept reports publish raw extrema without threshold verdicts; the
same slack applies when comparing their minima. Overlap above
1e-6 mm³ still fails even for a declared contact. A missing contact has status
`missed contact`; environment geometry has status `world geometry`. Counts of
those statuses appear when present, and every finding reaches the reply.
CLI threshold overrides apply to undeclared gaps and common volume; they do
not replace a script's declared minimum or contact tolerance. Engine row
`fit_failures` always describes the engine defaults. See XSCRIPT's measured-fit
section for declaration syntax and the precise world-geometry detection rule.

### What the fixed joints hold (ADR-370)

The clearance scope also publishes `attachments`: one row per component pair
joined by an unsuppressed `fixed` joint, carrying the joint names, the measured
distance and common volume, and `touching`, `not touching` or `unknown`. Build
replies carry it as `fit.attachments` with its own verdict — `touching`,
`reported`, `unknown`, `none` (the assembly welds nothing) or `unavailable` (a
revision accepted before ADR-370 published no report) — and the progress line
ends `welded: N of M pair(s) not touching` whenever the assembly has a fixed
joint. `cadex clearance` writes the same rows under the pair table. None of it
is counted among the fit failures and none of it refuses anything: a gap under
a weld is a measured fact and a question for the design, since a standoff or a
shim between two welded parts is legitimate. What it removes is the design
whose every declared check passes while nothing holds two parts together.

### What holds each purchased part (ADR-486)

The clearance scope also publishes `components`, the inventory rows of the
accepted assembly, each catalog row carrying `mount_axes` (its mounting-hole
centres and axes, or a bolt's own axis, in its source output's coordinates;
an empty list for a part with no holes) and each printed row that was cut
with a part's `.bay()` carrying `houses`. Build replies carry
`fit.mounting`: one row per purchased part (catalog parts less fasteners and
printed gear/rack generators), `held` by `screws` (a placed `lib.bolt` whose
axis lies within 0.5 mm and 5° of one of the part's hole axes, touching the
part and a printed part, contact being 0.5 mm), `bay`, `press fit` (bearings,
bushings, spherical joints touching a printed part), `output` (a horn or
wheel touching a held servo or motor) or `rim` (a tyre touching a held
wheel, ADR-489), or reported as `contact only`,
`inside shell` (touching nothing, its centre within a printed part's bounds)
or `held by nothing`. Its verdict is `pass`, `reported`, `unknown`, `none`
or `unavailable` — the last for a revision accepted before ADR-486, which
has no facts to judge. Like `attachments` it refuses nothing and counts
among no fit failure. It is not a strength check: one bolt on one hole
counts the part as screwed.

A bolt on a hole's axis counts only if it fits the hole (ADR-488). Each
`mount_axes` row carries one size fact: a bolt's `bolt_dia_mm`, a tapped
hole's `thread_dia_mm` (a part whose spec names a `mount_thread`, such as the
N20's M1.6 face or the STS3215's M2 self-tapping holes) or a clearance hole's
`hole_dia_mm`. A tapped hole takes only its own thread; a clearance hole any
bolt no larger than itself. A bolt that does not fit is listed in the part's
`misfits` (`"bolt0: an M2 bolt in an M1.6 tapped hole"`) and holds nothing.
A row with no size fact, from a revision accepted before ADR-488, is judged
by its axis alone until it is rebuilt.

A bolt that fits counts only if its shank threads into something (ADR-492):
a printed part it shares at least 0.1 mm³ with (its tap-drill hole), or —
clamping the printed part under its head — the held part's own tapped hole
(a hole with `thread_dia_mm`, modelled as an open bore, so reaching it is
enough), the held part itself, a nut or a heat-set insert it shares that
volume with. A head resting within 0.5 mm of a printed part while the
shank hangs in a cavity is listed in the part's `unthreaded` and holds
nothing. `thresholds.thread_engagement_mm3` publishes the volume.

The static fit allows that thread (ADR-492). A pair of a `lib.bolt` and a
printed part whose common volume is no more than the ring the thread can
cut, `π/4 (d² − minor²) L` from the bolt's part number and the ISO minor
diameter, is counted `clear` and in `fit.threaded_count`, not as an
intersection; more than that (a bolt through solid, or a pilot finer than
the minor diameter) still fails. The sweep keeps the allowance only for a
pair already threaded at the solved pose, and `cadex clearance` writes such
a row as `threaded`.


### Published joint sweeps (ADR-350, ADR-351, 2026-09-14)

`inspect scope=clearance path=/clearance_sweep` reads the accepted assembly's
published sweep unchanged: coverage status, the declared steps (`step_degrees`
for hinges, `step_mm` for sliders, either null when undeclared) and runtime
bounds, per-joint timings, pair minimum distances (mm), maximum common volumes
(mm³), and first-contact values in each joint's own `unit`: a revolute joint
reports `range_degrees`, `initial_degrees` and `first_contact_degrees`; a
slider reports `range_mm`, `initial_mm` and `first_contact_mm`. First contact
is the first sample from the lower limit within 0.001 mm; other joints stay at
their solved pose. Missing data returns `status: unavailable` with a reason;
unsupported joints, a limited joint whose step is undeclared, and budget
exhaustion retain `status: incomplete` and their reasons.
Complete coverage means measurements exist, **not** that fit passes.

`cadex clearance --sweep` writes these facts and the accepted revision to
`docs/clearance-sweep.md`. Exit 0 means the report was written, including when
coverage is missing or incomplete. Static threshold flags do not reinterpret
sweep extrema as fit-intent verdicts. Inspection never rebuilds or re-accepts.
To acquire measurements, explicitly build a script declaring
`assembly.assembly(..., sweep_step_degrees=...)` and/or
`assembly.assembly(..., sweep_step_mm=...)`. Legacy projects keep their
accepted identity. The existing inspect arguments and generic paged response
contract are unchanged; clients continue to pass the scope value through.

## Bounded smoke rollout (ADR-352)

```bash
./cadex smoke --project ./mechanism --out ./mechanism/smoke1 --seconds 2 --json
```

`smoke` copies the retained accepted MJCF, optional task and detached BREP
artifacts into the output directory and holds the project lock through measurement. It never runs
`script.py`, restores the working script, or changes accepted state. The
receipt pins the accepted revision and digest. Model/task hashes are checked
when present in the retained report; tasks must match the selected model.
The child uses stock MuJoCo, without a policy or trainer. `hold` holds each
position actuator at its solved joint coordinate; other actuators receive
zero. `zero` sends zero to every actuator.

The command checks:

- Finite position, velocity, acceleration, actuator state and controls, at
  every solver step, with MuJoCo warning counters retained across resets.
- Exact BREP common volume for every component pair at every sampled pose,
  including pairs excluded from physics contact and parts with no collision
  proxy. The default limit is `--max-common-volume-mm3 0.000001`. Each pair's
  maximum volume and its time are retained. At the first frame, distances
  and common volumes must agree with published static clearance; a missing
  solid or disagreement is a measurement error, never a pass.
- Floor-proxy penetration no deeper than `--penetration-mm 0.5`, and a free
  base whose design is touching the environment floor at the end, whose linear
  speed is at most `--rest-speed-mm-s 10`, and which has turned no further
  than `--max-tilt-degrees 30` from the attitude its accepted keyframe gave it
  (ADR-377: a design that toppled and settled meets the first two and is not
  standing; the angle is read against the keyframe, so a base modelled lying
  down and holding that pose reads zero). Grounded bodies hold by
  construction. Floor support uses the model's collision proxies; component
  fit uses exact solids.
- Any termination conditions in the selected task, without applying task
  randomisation, disturbances or a trained policy.

Sampling defaults to 50 Hz, always includes the initial and final poses, and
records actual solver times. Duration rounds up by less than one solver step.
The trace budget is 15,000 requested intervals. This is a sampled check, not
continuous collision detection. `--timeout` shares a wall-time budget across
simulation and exact geometry measurement, capped at 300 seconds; a timed-out
child is killed and no complete smoke receipt is claimed.

`smoke-dynamics.json` is the intermediate physics result, not a complete smoke.
`smoke-trace.json` holds the numeric component poses; `smoke-geometry.json`
holds exact pair measurements; `smoke.json` combines all checks and identifies
the accepted design. Reusing an output directory overwrites these artifacts.
The CLI envelope and the project's `PROGRESS.md` carry the verdict and failing
checks. Exit zero means a complete measurement, **not a passing design**: read
`smoke.verdict`. A measured failure never changes acceptance. Missing artifacts,
missing geometry, model/task disagreement or timeout make the command fail.
No STEP/STL conversion, new dependency, or protocol op is involved.

## Evaluating a policy against its success spec (ADR-457, ADR-459)

```bash
./cadex evaluate --project ./robot --json
```

A task says what its behaviour must measurably be with `assembly.success`
(`docs/XSCRIPT.md`, ADR-456): predicates on behaviour metrics, the frozen
evaluation seeds, and the conditions an evaluation episode runs under.
`cadex evaluate` is the one command that holds a policy to it. It takes no
behaviour's name and has no flag for one: the spec names the metrics, the
engine reads the metric families the mechanism has (a floating base, named
feet, a tip), and a walk, a reach and a balance are three specs through the
same path.

**What it reads.** The retained accepted attempt, the way `smoke` does: it
never runs `script.py`, restores the working script or changes accepted
state, and it holds the project lock through the measurement. The policy is
the one the accepted script declared with `assembly.policy` and the engine
verified; its receipt names the task and the weights. Every file is checked
against the digest the store recorded, and the weights must hash to what
the receipt says was verified. With several declared policies, `--policy
NAME` or `--task NAME` picks one. No declared policy, or a task with no
success spec, is exit 3 with what to declare.

**What it runs.** `cli/cadex_cli/evaluate_runner.py`, by path, under the
engine's own interpreter. It calls `CadexDynamics.evaluate_success`: for
each seed in the spec, one rollout of the policy in the engine's episode
loop under the spec's horizon, randomisation, reset variation,
disturbances (ADR-458) and goals (ADR-462), at one frame per control step,
read by `CadexEvaluation` (ADR-455). A commanded speed and a reach target
are the episode's own goal draws: the command takes neither as an argument,
and each seed's `drawn.goal` in the report says what was asked and when.
The model is
compiled afresh for every seed, because a seeded episode writes its
randomisation draws into the compiled model; each seed's row is the row it
gets evaluated alone. Training stays offboard: nothing here imports JAX,
MJX or the trainer.

**What it writes**, into `evaluations/<revision>-<policy>/` in the project
(the first twelve characters of the accepted revision and of the policy's
sha256; `--out DIR` names another place):

- `evaluation.json` (`cadex-evaluation-v1`), written last and atomically:
  - `verdict`, `pass` or `fail`. **Every seed must pass every predicate.**
    Nothing is averaged into a verdict.
  - the identity: accepted revision and digest, the policy, task and model
    digests, the task's semantic digest, the engine.
  - `spec`: the predicates, seeds, conditions and scale that were held.
  - `seeds`, one row each: `pass`, `failing`, every predicate with its
    value, bounds and the reason it failed; `metrics`, the flat table a
    predicate may bound; `detail`, each foot's and each shove's own figures;
    `episode`, with its steps, duration, termination cause and solver
    warnings; `reward`, the total and each term, which is reported and
    decides nothing; `drawn`, every value the seed drew for its
    randomisation, reset and shoves; and `trace`, the file below with its
    sha256.
  - `summary`: the seeds that passed and failed, each predicate's tally and
    failing seeds with the spread of its value, the termination causes, the
    reward and every metric as min, median and max over the seeds that
    measured it.
- `seed-<n>-trace.json`, one per seed: the rollout's frames as a
  `cadex-assembly-simulation-trace-v1`, the schema a rollout already
  writes. The project's own `.gitignore` keeps `*-trace.json` out of its
  history; the report is committed with the run's `PROGRESS.md` row.
- the **film** (ADR-459, below): `seed-<n>-overview.png` and
  `seed-<n>-detail.png` for each filmed seed and `seed-<n>-rollout.webm`
  for the first, named with their digests in the report's `film` block.

**A void seed.** MuJoCo answers a bad acceleration by resetting the state
and counting a warning, so the frames after it are finite and are not the
mechanism. A seed whose episode raised a solver warning is `void`, is listed
in `summary.void`, and has not passed whatever its predicates read.

**A model whose contact is held off its geometry** (ADR-470) voids every
seed the same way. A contact geom with a `margin` or a `gap`, or a
model-wide `o_margin` under the override flag, moves the surface contact
acts at while the trace still reports the geometry, so a foot's height,
stance and slip are read against a surface the physics did not use. The
episodes are played and measured, the report lists the geoms with their
margin and gap in millimetres in `contact_offsets`, every seed's `void`
names them, and the progress cell, the prose and the agent's view lead with
them.

**Refusals.** A spec seed that is the policy's own training seed is refused:
evaluation seeds are never training seeds. A model that is not the one the
task bundle recorded is refused before any rollout.

Exit zero means a complete measurement on every seed, **not a passing
policy**: read `evaluation.verdict`. The envelope's `evaluation` block
carries the verdict, the digests, the summary, `report`, the path of the
full file, and `film`, the state of the film with the path of each sheet
and video drawn; the per-seed rows stay in the file. The `PROGRESS.md` row names
the verdict and the failing predicates, which is how a failed evaluation
reaches the agent's next session.

### The film: a filmstrip and a video of what the seeds did (ADR-459)

```bash
./cadex evaluate --project ./robot                       # measure, then film one seed
./cadex evaluate --project ./robot --film 1101,1105,1110 --detail-start 5 --detail-step 0.04
./cadex evaluate --project ./robot --film-only --film all --no-video
```

Numbers can be met by a motion nobody would call the behaviour, so the
evaluation also draws what its seeds did. `cli/cadex_cli/film.py` reads the
traces the evaluation kept and the tessellation the accepted attempt
retained, and draws with the engine's studio renderer (`CadexStudio`,
ADR-445) on the CPU: no engine is opened, nothing is rebuilt, and there is
no browser. Every image stands on the dark prototype floor (ADR-444).

- **The filmstrip**, two PNG sheets of twelve 256 px frames (1036×776) for
  each filmed seed. Every frame carries its simulation time, bottom left,
  and, in an episode that was given one, its target marker (below). Nothing
  else: no seed number, no metric.
  - `seed-<n>-overview.png`: evenly spaced from 0 s to the episode's end,
    in the hero three-quarter view, in one fixed window that frames the
    whole path.
  - `seed-<n>-detail.png`: consecutive moments `--detail-step` apart from
    `--detail-start`, 12° above the floor, **side-on, following the base**
    (ADR-460). The base is the one the evaluation measured tilt, heading
    and drift on (`rig.base`, the mechanism's single floating body). The
    window is centred on the middle of that component's bounds in every
    frame, and is wide enough to hold the whole design in each. Side-on is
    measured from the trace: the camera's right is the plan direction from
    where the base started to where it was farthest away (the front view
    when it stayed within 5 % of the design's size). The window never moves
    up or down. A mechanism with no floating base has a fixed one, so its
    window is fixed on everything the shown moments cover. The block's
    `follows` names the base, or is `null`. With no start given, the detail
    begins at the seed's
    first drawn disturbance, or at the middle of an episode that has none.
    An episode that ended before the last moment is shown to its end: the
    window slides back, and the block records both `requested_start_s` and
    `start_s`.
- **The video**, `seed-<n>-rollout.webm`, of the first filmed seed: the
  studio video a run gets (ADR-431), ten frames a second with a timer, and
  decoded back frame for frame before it is kept. FFmpeg is found on `PATH`
  or beside the interpreter, which is where the pixi environment has it.
- **The target marker** (ADR-463). A task that states a point goal
  (`assembly.goal(kind='point')`, ADR-462) leaves the target in every frame
  of the trace. The film draws a ring centred on the target in force at
  each frame's own time: cyan `#6FF0F0` inside a dark rim, 9 px in radius
  on a 256 px frame. It is drawn over the solids and is hollow, so a tip
  that arrives neither hides it nor is hidden by it, and it jumps in the
  frame where the target changes. The overview's window and the video's
  hold every target beside the path. So does the detail's when there is no
  floating base. A detail that follows a base stays the design's size and
  marks the target only while it is inside. The film asks for no
  behaviour's name: a trace with a point goal is marked and any other
  trace is drawn exactly as before. A seed whose report says it drew a
  point goal and whose trace carries none is refused, not drawn unmarked.
- **Which seeds.** `--film auto` films the first seed that failed (the one
  a diagnosis starts from), or the first seed of an evaluation that passed.
  `--film none` draws nothing and records `skipped`.
- **The floor** is the model's collision plane, the height the evaluation
  measured clearance against (`rig.floor_mm`); without one, the top of the
  world geometry the assembly declares; without that, the lowest point the
  drawn solids' bounds reach. World geometry itself is not drawn.
- **The materials** are the design's: the role each component declared,
  else mechanism for a catalogued part and shell for a printed one, read
  from the accepted attempt's inventory with no rebuild. Without an
  inventory at the accepted revision every part is drawn as shell, and the
  block says so.

The report's `film` block (`cadex-evaluation-film-v1`) carries `state`
(`ready`, `failed` or `skipped`), the renderer and its identity, the
materials and geometry drawn, and one row per filmed seed: the trace's
sha256, the floor and where it came from, and for `overview`, `detail` and
`video` the file, its sha256 and size, the times of its frames and the
view. A row's `target` is `null`, or the goal's name, its channels and each
place it held with the time it began (`positions`); each of the three
carries `marked_frames`, the frames whose target is inside them; and the
block's `marker` says what the ring is. The trace filmed is the trace measured: a trace whose digest is not
the one the seed's row recorded is refused.

`evaluation.json` is written complete before anything is drawn and again
with the film. A film that cannot be drawn leaves the measurement intact,
records `failed` with the reason, and the command exits 1 saying the
evaluation was measured; a video that cannot be encoded leaves the sheets.
One seed's two sheets take about 21 s on a sixty-part quadruped, and its
ten-second video about 180 s (measured on `ot11-w2-negative`, 78,303
triangles).

`--film-only` draws from an evaluation already on disk, for looking at
another seed without rolling anything out again. It refuses an evaluation
of another revision or policy than the accepted one.

The film is not the record. The evaluation's directory gets a `.gitignore`
naming the three film patterns, so the project's own repository (ADR-194)
commits `evaluation.json` with the run's `PROGRESS.md` row and leaves the
sheets and the video on disk, where `--film-only` can draw them again.

**The dashboard shows it.** `cadex review` lists every
`evaluations/<name>/evaluation.json` in `GET /api/project` under
`evaluations` as a bounded summary: verdict, seed tally, what failed, the
policy and task, `relation` to the accepted revision now, which seeds were
filmed, and a `stamp` that changes when the file does. Reports are parsed
once per file identity. `GET /api/evaluation/<name>` carries one report
whole, with `files` saying which of its film is on disk.
`GET /evaluation/<name>/<file>` serves `evaluation.json` and the film files
that report names, and nothing else in the directory: a trace, an unnamed
file or a link out of the evaluation is a 404. The page's **Evaluation**
tab was removed by ADR-533. Only evaluations under `evaluations/`
are listed; one written elsewhere with `--out` is not.
