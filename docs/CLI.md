# CLI.md — Cadex, headless

Verified against source: 2026-09-06. Provenance: [Cadex-new] (ADR-061).

`cli/` is a **third client of the cadexd protocol**, peer to the Blender
shell and owing it nothing: no display, no `bpy` imports, no shell code.
Ordinary projects need no Blender. A project declaring `mesh.blender` uses
an optional external geometry runtime: set `CADEX_BLENDER_EXECUTABLE` to an
absolute Blender/Cadex executable path before running the CLI, including
parameter sweeps and reopen. The recipe stays in xscript and follows the
same engine protocol; see `docs/BLENDER-RECIPES.md` (ADR-185).
It is the front end for people at a terminal and for pipelines.

```bash
./cadex -p "a mounting bracket for a NEMA17, 4 mm wall" --out ./out
./cadex -p "make the fins 20% thinner" --resume
./cadex params --set fin_angle=12 --out ./sweep/12     # no AI in the loop
```

## 1. Why it exists

The engine was never the part that needed a screen. It is a headless NDJSON
service, and as of ADR-060 it builds, tests, packages and models on a
headless Linux box. Everything that needed a display was the shell.

What the CLI unlocks is not "the same thing without a window". It is a
**cost asymmetry**: an expensive model turn authors a *parametric* script
once, and after that a cheap loop sweeps its parameters and re-exports with
no model in the loop at all. An external simulator — airflow, FEA,
print-time — feeds its numbers back, and the expensive call happens only
when the *shape* has to change.

```bash
./cadex -p "an impeller with 7 blades, 40 mm hub" --project ./impeller
for angle in 8 10 12 14 16; do
    ./cadex params --project ./impeller --set blade_angle=$angle \
                   --out ./sweep/$angle --json > ./sweep/$angle.json
    simulate ./sweep/$angle/impeller.step >> results.txt
done
./cadex -p "the 14° case stalls at the tip — thicken the tip chord" \
        --project ./impeller --resume
```

The first and last lines cost tokens. The loop between them does not.

## 2. Commands

| Command | What it does | Spends tokens |
|---|---|---|
| `cadex -p "<prompt>"` | One AI turn: the model writes or edits the project script. | **yes** |
| `cadex params --set k=v` | Set declared parameters and rebuild. | no |
| `cadex script` | Print the project script. | no |
| `cadex script --set FILE` | Replace the script from a file and rebuild. | no |
| `cadex export` | Rebuild the accepted script and write its outputs. | no |
| `cadex link --from DIR` | Bring a part in from another project, or refresh one. | no |
| `cadex asset --put FILE` | Copy a file into the project store — a trained `.cxpolicy` coming home, its `.json`/`.xml` provenance, a mesh, a `.cxpart`. With no `--put`, list the store. | no |
| `cadex train --out DIR` | Rebuild, export the training bundle into `--out`, run the offboard trainer on it from its venv, and report the receipt. With `--put`, store the policy and report its sha256. | no |

Flags, valid on either side of the subcommand:

| Flag | Meaning |
|---|---|
| `--project DIR` | Project root; **created if absent**. Default `./.cadex`, or `$CADEX_PROJECT`. |
| `--out DIR` | Write exported files here. Omit and nothing is written. |
| `--format step,stl` | Any of `step`, `stl`, `brep`. Default `step,stl`. |
| `--blueprints` | `export` only: also copy the project's stored blueprint sheets into `--out`, store filenames kept (ADR-150) — which since ADR-157 means `0007-gearbox-overview-v1.png` for a **named** sheet rather than a revision prefix. Read-only — the shell renders them; this only reaches the store through `inspect scope=blueprint`. |
| `--engine ROOT` | A staged engine payload. Default: `$CADEX_ENGINE_ROOT`, then the dev tree. |
| `--json` | Emit the machine-readable envelope on stdout. |
| `--wait` | Block for the project lock instead of failing. |

Prompt-only flags: `--resume` (continue this project's conversation),
`--model` (default `claude-fable-5`), `--claude` (path to the CLI).
`script --set` also takes `--replace`, which is you saying you mean to drop
an output the accepted revision declares — without it such a script is
refused, because `write_script` replaces *the whole* script and losing an
output by accident is easy (ADR-045).

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
script names it, and that change is `cadex script --set` or a turn's
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
it, which is `cadex script --set` or a turn's `edit_script`. A project
whose accepted revision exports no training task is exit 3 before the
trainer runs; a trainer that exits non-zero or hits `--timeout` is exit 1
with its stderr already on ours.

**Iterating — change the mechanism or the task, retrain, compare** is
four commands and one digest edit, with no new flag on `params`
(ADR-192). A sweep that moves the task digest is refused at exit 3 while
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
per-term `reward_totals`); recording it is the lifecycle walk's next leg
(`docs/MUJOCO.md` §7c, row 9).

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Fine. |
| 1 | The engine or the agent failed. |
| 2 | The command was wrong. |
| 3 | The engine refused the script. |

Three is separate from one because a pipeline handles them differently: a
refused script is a modelling problem to feed back to the next turn, a
failed engine is an infrastructure problem to retry or abort on.

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
  "session_id": "96e5d6ce-…",
  "model": "claude-fable-5",
  "engine": {"source": "dev-tree", "freecadcmd": "…", "module_dir": "…"},
  "out_dir": "/…/out",
  "notes": ["…the turn's closing summary…"]
}
```

`error` is present instead of `notes` when `ok` is false. `outputs` entries
that produced no file carry `skipped` with the reason. An `asset` run adds
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
  session.py           agent.json and the project lockfile
  tools.py             the tool surface, generated from OP_ARG_SPECS
  bridge.py            unix-socket server in the parent, in front of cadexd
  mcp.py               the MCP stdio server `claude` spawns
  agent.py             one `claude -p` turn; the system prompt
  export.py            STEP/STL/BREP out of the display block; the rest copied
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
  cadex (parent) ──owns──> cadexd (FreeCADCmd)
        │
        ├─ unix socket (private dir + token)
        │        ▲
        └─ claude -p  ──spawns──>  mcp.py  ──relays──┘
```

`claude` spawns MCP servers as its own children, so some IPC is unavoidable.
The parent keeps the engine and the socket; the shim relays. That shape is
the shell's, minus the reason the shell needed it (`bpy` thread-affinity).
Here it earns its keep differently: **the parent observes every tool call**,
which is what lets it print progress, know the final revision without asking,
and hold the display block the export reads.

### `expected_revision` is injected, not asked for

The protocol guards every mutation with the revision the caller believes is
current. That guard exists for concurrent writers, and a CLI run has exactly
one. So the bridge tracks the revision from each reply — **including
refusals**, because a rejected candidate still becomes the working revision
— and fills it in. The value used comes back in every tool result as
`expected_revision_used`, so the model can still see drift; it just cannot
fail on it.

### Tool names are op names

`describe_api`, `write_script`, `edit_script`, `set_params`, `rebuild`,
`inspect`, `link_part`, `put_asset`. The shell invented friendlier names because it had Blender's
vocabulary to reconcile; a third vocabulary would be a third thing to keep
in sync. The input schemas are **generated from `OP_ARG_SPECS`**, so they
cannot drift from the protocol — only the prose is hand-written.

`display` and `expected_revision` are removed from the schemas: the first
asks for tessellation nothing here draws, the second is injected.

### What the agent is told

The system prompt is the CLI's own overlay plus `describe_api`'s live
`instructions`, `program_schema`, `source_globals`, `result_contract`,
`revision_rule` and parameter prose. **The CLI never states the xscript
API.** Both front ends ask the engine for it, which is what keeps one
contract from becoming two.

The overlay says three things the engine does not:

- **Build it parametric**, because the cheap sweep only exists if the
  expensive turn made one possible.
- **You cannot see your work.** No viewport, no screenshot, no render, no
  pin — the agent verifies through `inspect scope=output` facts and the
  script's own `stdout`, and is told so rather than discovering it by
  failing.
- **You cannot train, and a file comes in by path.** `put_asset` is how a
  trained policy, its provenance or a mesh enters the project, and its
  reply's `sha256` is the digest the script names; asked to train, the
  agent says so and names the caller's one command, `cadex train --out
  DIR --put` (ADR-191), or its three — `cadex export`, the trainer,
  `cadex asset --put` — instead of inventing flags (ADR-190 — the audit
  caught it doing exactly that).
- **Revision guards are handled for you.**

## 5. Sessions, locks and state

`<project_root>/agent.json` is the CLI's own file:

```json
{"schema": "cadex-cli-agent-v1", "session_id": "…", "model": "…",
 "updated_at": "2026-07-31T12:36:31Z"}
```

It is a **sibling** of the engine's `script.json`, never a replacement: the
CLI reads engine state through `inspect` and writes only its own. `--resume`
passes `session_id` to `claude --resume`. A stale id — the project was
copied to another machine, or the local session history was pruned —
degrades to a fresh conversation with a note in the report, not to a dead
run.

Claude Code files a conversation under the directory the turn ran in, so
turns run **in the project root**. A scratch directory per turn would make
every `--resume` look like an expired session.

`<project_root>/.cadex-cli.lock` is an advisory `flock`, because `cadexd` is
one process per project and a sweep will run several of these at once. The
kernel releases it on process death, so there is no stale-lock heuristic to
get wrong. A second run is refused with a readable message; `--wait` blocks
instead.

## 6. Which engine

In order: `--engine`, then `CADEX_ENGINE_ROOT`, then the development tree
(`.pixi/envs/default/bin/FreeCADCmd` or `build/release/bin/FreeCADCmd`, plus
`src/Mod/cadex`). The first two name a **staged payload root** and are read
through its `cadex-engine.json` manifest, which is the payload's discovery
contract (ADR-020) — the same resolution the shell and
`test_cadexd_lifecycle.py` use.

The manifest's declared `protocol` is checked against the module directory's
own `CadexdProtocol.PROTOCOL_SCHEMA`, so a payload assembled out of two trees
fails before a frame is sent. The resolved engine names itself in the
envelope, because two runs against two engines have to be tellable apart in
a log.

Every reply is shape-checked against **that engine's own**
`OP_RESPONSE_SPECS`, and a violation is an error rather than a warning. A
third client that quietly tolerates an undeclared key is a third client the
protocol has stopped being a contract for.

## 7. Running the suite

```bash
pixi run python -m pytest cli/tests
```

Fast, and honest about what it did not run.

| File | What it drives |
|---|---|
| `test_engine_resolution.py` | Hand-built payload directories; no engine needed. |
| `test_mcp_protocol.py` | `fake_cadexd.py` + a real bridge socket; no engine needed. |
| `test_client.py` | A real `cadexd`. **Skips** without a built engine. |
| `test_export.py` | Plan-building directly; conversion against a real engine. |
| `test_turn_loop.py` | `mock_backend.py` + a real engine. |
| `test_commands.py` | `main()` end to end against a real engine. |

`tests/fake_cadexd.py` is a scripted engine, not a loose mock: its replies
go through the same `validate_response` path production uses, so a fixture
that has drifted from `OP_RESPONSE_SPECS` fails there rather than passing
there and failing live.

`tests/mock_backend.py` replays a scripted turn so the whole `cadex -p` path
— lock, revision injection, export, session file, exit codes — is tested
without spending a token. Its tool calls go through the *real* bridge socket;
only the model is faked.

Everything that needs an engine **skips** without one, so a green run on a
bare checkout proves less than it looks like.

CI runs the suite in both jobs of `.github/workflows/cadex-app.yml`, after
the engine build for that reason. The Linux job runs it twice — once against
the build tree and once against the staged payload — on the same argument
the packaged engine gate rests on: a source tree that passes proves nothing
about a payload (ADR-023).

## 8. Limits

- **Linux and macOS.** The lockfile is POSIX `flock` and the bridge is a unix
  socket. Windows is not supported.
- **No pictures.** `inspect scope=image`, `resolve_pin` and offscreen
  rendering are all absent, deliberately (§4). One caveat since ADR-150:
  blueprint *sheets* the shell already rendered and stored are readable —
  `inspect scope=blueprint` lists them and `export --blueprints` copies
  them out — because a stored deliverable is not a render. Making one
  (`put_blueprint`) stays shell-only.
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
- One `--set` per parameter, and parameters are numeric — that is what
  `num(...)` declares. A switch is a `num` with `min=0, max=1, step=1`
  and a `>= 0.5` test in the script (ADR-192).
