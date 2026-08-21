---
node_id: f1338263-fcf8-508f-a5a8-9b5b7857dd57
slug: gilded-wind-5121
title: A print tick is a view setting, not project state (ADR-158)
created_at: '2026-08-21T10:38:42+00:00'
parents:
- still-wave-6655
summary: ''
---
## What

**The printable tick stops being project state.** ADR-158, one slice after
ADR-156 built it the other way.

Deleted: the `set_printable` protocol op (19 ops → 18), the
`print_specs` / `print_values` pair in `script.json`, the harvest-and-prune
block in `validate_project_result`, and three store-shaped helpers in
`CadexPrintables.py` (`declared_printables`, `prune_printable_rows`,
`effective_printables`). Changed: `export_printable` now takes `printable`,
the list of output names to write, and the roster it validates against is
derived from the **accepted worker report** rather than read out of a cache
in the store — the same read `inspect scope="output"` beside it already
does. Shell: `cadex_print.py` keeps the ticks in one scene ID property
(`cadex_printable`), so they save with the `.blend`; `cadex_backend`
names the job on the export call and loses `set_printable`.

## Why

The user asked for the toggle to be "only a UI thing — it doesn't need to be
in the script at all", and they were right about the shape rather than only
about the cost.

ADR-156 had already won the argument about the **revision** — a mark must
not enter `project_script_revision`, because a checkbox that costs a rebuild
is not a checkbox — and then, having won it, kept the mark in `script.json`
anyway as a sixth spec/value pair with an op to write it. But the reason a
mark does not belong in the content hash is the same reason it does not
belong in project state at all: **a tick says what somebody means to do with
a run's output, not what the model is.** It is a selection, a camera, a
visibility flag: a property of the view, and the view already has a file of
its own.

What that shape cost while it lasted: one protocol op, one store pair, a
defaults-merge entry, a block on every accepted rebuild, a roster cache that
had to be kept in step with the report it was copied from, and a subprocess
round trip for every tick of a checkbox — on a control whose entire job is
to be flipped idly while deciding what to print.

## Method

Engine, in dependency order:

1. `CadexPrintables.py` rewritten around what the engine actually needs:
   `printable_roster(outputs) -> {name: artifact_kind}`, plus the unchanged
   `canonical_printable_rows`, `stl_file_name`, `allocate_file_name`. The
   three store-shaped helpers are gone.
2. `CadexScriptStore.default_state()` loses both keys. No migration is
   needed in either direction: `read_state` merges only the keys the default
   declares, so an ADR-156 store's dead keys are dropped at its next write,
   and `write` refuses an undeclared field, which is what stops anything
   putting them back.
3. `CadexScriptedRuntime.validate_project_result` loses the harvest/prune
   block (the `store = CadexProjectScriptStore(...)` line it happened to own
   stays — `store.write` below needs it).
4. `CadexInspection._script_printable(root, state)` reads the accepted
   worker report through `accepted_attempt_dir` + `load_worker_report` and
   returns `{"outputs": [{name, artifact_kind}]}` — no `printable` flag,
   because the engine has no opinion about one. Any `OSError`/`ValueError`
   (no accepted revision, unreadable report) reads as an empty roster: a read
   path may not take `inspect` down with it.
5. `cadexd._op_set_printable` deleted (~70 lines). `_op_export_printable`
   validates `args["printable"]`, refuses an empty job
   (`NOTHING_MARKED_PRINTABLE`) and an unknown name
   (`UNKNOWN_PRINTABLE_OUTPUT`, roster attached), and drops two checks in
   the plan loop that the roster has already proved — the name is in the
   report and the kind is exportable, both by construction.
6. `CadexdProtocol`: `set_printable` out of `MODELING_OPS`, `OP_ARG_SPECS`
   and `OP_RESPONSE_SPECS`; `export_printable` gains required `printable`.
   `response_schemas/set_printable.json` deleted.

Shell: `cadex_print.py` keeps `_ROSTER` (the cache) and adds `_stored` /
`_store` over one scene ID property, newline-joined because an ID-property
array holds numbers and a canonical output name may not carry a control
character. `toggle` checks the name against the roster and flips it in the
scene; `marked` filters the stored ticks against the roster so a stale tick
cannot turn a whole job into one refusal; `is_marked` is what the panel
draws its icon from; `invalidate` is deleted (its only caller was the
failed-push path). `adopt` prunes ticks against the new roster — ADR-039's
silent drop-on-drift, now on this side of the boundary. The loud half stays
in the engine, where it guards a write.

Verification: the engine suite; the packaged lifecycle gate against a
freshly staged payload; `cli/tests`; and `pixi run gate` against a rebuilt
bundle, with the printable case extended by three checks.

## Result

**Green.** `pixi run python -m pytest src/Mod/cadex/cadex_tests`: **1898
passed, 33 skipped** (1899 before; `test_printable.py` rewritten around the
roster, the refusal and the plan). Packaged lifecycle gate with
`CADEX_ENGINE_ROOT` on a staged payload: **14 passed**, the payload carrying
the rewritten `CadexPrintables.py`. `pixi run python -m pytest cli/tests`:
**83 passed**. `pixi run gate`: **`"ok": true`**, `"printable": {"bytes":
684, "files": ["bracket-002.stl", "bracket.stl"], "outputs": ["arm",
"bracket"]}`, slider median **0.538 s** inside the 0.65 s bar.

The three new gate checks are the claim stated as assertions: the tick lands
in `scene["cadex_printable"]`; `script.json` holds no key starting with
`print`; and a rewrite to a one-output script makes the roster follow and
takes the dropped part's tick with it.

**What deriving the roster costs, measured rather than assumed.** One file
read and one JSON parse on `inspect scope="script"`, which the shell issues
on open and after every accepted rebuild — so it is on the slider path.
Against the largest real accepted report on this machine (`actuator-v13`,
1.5 MB, 30 outputs): **12.2 ms**, against a 650 ms parity bar and a ~0.54 s
slider round trip. That is the price of not keeping two lists in step.

**One negative result worth keeping.** An intermediate gate run failed the
slider bar at **1.124 s** — and every number in that run was 2–3× its usual
value (open 3.0 s vs 2.0 s, refine 3.1 s vs 1.4 s, hydrate 20.6 ms vs
9.4 ms) on a machine at load average 13.7. The re-run on a quiet machine
came back at 0.538 s. The gate's latency bar is the one measurement in that
file that cannot be read off a loaded machine, and a failure there should be
re-measured before it is believed.

**What this gives up, stated plainly.** A tick no longer follows the
*project*: open the same project from a different `.blend` and nothing is
ticked. That is correct for a view setting and is what a selection already
does, but it is a real difference from ADR-156. And `./cadex` cannot print
"whatever was ticked" — a headless caller names its parts, which is better
for a headless caller anyway: a script that prints a fixed list is
reproducible, and one that printed a checkbox somebody left set is not.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 39308e3b40359738a9581141790ccb130f77d1e6

## State Impact

- target: forest-wind-0342 — The print surface loses its store half (ADR-158): set_printable is deleted (19 ops -> 18) and print_specs/print_values leave script.json, so the store carries nothing about printing at all. export_printable now takes 'printable', the list of output names to write, and validates it against a roster DERIVED from the accepted worker report rather than cached in the store -- the same read inspect scope=output beside it already does -- so the panel's candidates and what the export accepts are one list by construction. inspect scope=script's printable block is the roster only, with no per-entry tick. CadexPrintables.py loses declared_printables/prune_printable_rows/effective_printables and gains printable_roster; validate_project_result loses its harvest-and-prune block; two now-unreachable checks come out of the export plan loop. No migration either way: read_state keeps only declared keys and write refuses an undeclared field. ADR-039's asymmetry splits -- the LOUD half (UNKNOWN_PRINTABLE_OUTPUT on a requested name) stays here because it guards a write; the silent drop-on-drift is the caller's. Cost of deriving the roster, measured: 12.2 ms on a 1.5 MB / 30-output report, on the slider path.
- target: shy-crane-2573 — The printable ticks are the SHELL's now (cadex ADR-158) and live in one scene ID property, cadex_printable, so they save with the .blend and cost no round trip, no store write and no revision -- a tick is a decision about a view of the model, like a selection. cadex_print.py swaps its set_printable push for scene reads/writes, gains is_marked, loses invalidate, and prunes ticks against the roster in adopt(), which is ADR-039's silent drop-on-drift moving to this side of the boundary. cadex_backend.set_printable is deleted and export_printable names the job from cadex_print.marked(scene), filtered against the roster so a stale tick cannot turn a whole job into one refusal; one line off cadexd_client.MODELING_OPS. Gate extended with three checks: the tick in the scene, script.json holding no print key, and a one-output rewrite taking the dropped part's tick with it. A tick no longer follows the PROJECT -- a different .blend opens with nothing ticked.
