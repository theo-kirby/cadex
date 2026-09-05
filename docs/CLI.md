# CLI.md — Cadex, headless

Verified against source: 2026-08-31. Provenance: [Cadex-new] (ADR-061).

`cli/` is a **third client of the cadexd protocol**, peer to the Blender
shell and owing it nothing: no Blender, no display, no `bpy`, no shell code.
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
     "files": {"step": "/…/impeller.step", "stl": "/…/impeller.stl"}}
  ],
  "session_id": "96e5d6ce-…",
  "model": "claude-fable-5",
  "engine": {"source": "dev-tree", "freecadcmd": "…", "module_dir": "…"},
  "out_dir": "/…/out",
  "notes": ["…the turn's closing summary…"]
}
```

`error` is present instead of `notes` when `ok` is false. `outputs` entries
that produced no file carry `skipped` with the reason.

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
  export.py            STEP/STL/BREP out of the display block
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
`inspect`. The shell invented friendlier names because it had Blender's
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
- **Export is BREP-only.** Mesh outputs (`.ply`), assembly components and
  solve diagnostics are reported as `skipped` with a reason rather than
  silently dropped. Export runs as a short `FreeCADCmd` job rather than a
  protocol op; promoting it to `export_model` is its own PR, and
  `export.py` is one seam so that it can be.
- **The CLI does not ship in the engine payload.** It runs from the
  repository.
- One `--set` per parameter, and parameters are numeric — that is what
  `num(...)` declares.
