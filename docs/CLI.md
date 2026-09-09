# CLI.md — Cadex, headless

Verified against source: 2026-09-08. Provenance: [Cadex-new] (ADR-061).

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
| `cadex section --plane XY [--offset-mm 8]` | Cut accepted tessellation through a world plane; revision-bearing SVG and JSON under `review/section/` (ADR-240). **`--offset-mm` is optional**: omitted, the offset is derived from the accepted bounds the way the walk derives it — every candidate is cut and the one covering the most objects wins (ADR-273, ADR-275). The note reports the offset, whether it was `explicit` or `derived`, and how many of the model's objects the cut reached. | no |
| `cadex render` | Rebuild accepted display and write front/top/right/iso SVG previews plus `review/render/summary.json`, bearing the full accepted revision (ADR-239). CPU only; no graphics runtime. | no |
| `cadex clearance` | Write `docs/clearance.md` naming every component pair, labels and catalog ids, minimum distance (mm), common volume (mm³) and verdict. Reads published measurements at the initial solved pose with no rebuild or tokens; not a swept-motion check (ADR-237). Missing measurements remain unknown. Exit 0 means the report was written, not that all pairs are clear. | no |
| `cadex inventory` | List the parts of the accepted assembly with catalog ids: one row per component with the output it places, its catalog family and part number where a `lib.*` generator built it, and the pose the solver settled on. Writes `docs/inventory.md` in the project (ADR-236). Reads the pinned accepted attempt — no rebuild. Resolves all inspection pages and previews, including catalog totals, uncatalogued names and large component rows. | no |
| `cadex link --from DIR` | Bring a part in from another project, or refresh one. | no |
| `cadex asset --put FILE` | Copy a file into the project store — a trained `.cxpolicy` coming home, its `.json`/`.xml` provenance, a mesh, a `.cxpart`. With no `--put`, list the store. | no |
| `cadex train --out DIR` | Rebuild, export the training bundle into `--out`, run the offboard trainer on it from its venv, and report the receipt. With `--put`, store the policy and report its sha256. With `--remote`, the trainer runs on the box through `training/remote_train.sh`; the artifacts do not move. With `--dry-run`, report the plan — the files the leg would touch and the steps it would take, in either mode — and train nothing. | no |
| `cadex walk --out DIR` | The lifecycle walk as one command: optional design turns (`--prompt`, repeatable), an optional change (`--set`), train and store (locally, or on the box with `--remote`), re-declare the policy in the script, verify and roll out, review. Every leg is a child `cadex` command, each bounded by `--leg-timeout` (default 3600 s); `review.json` lands in `--out`. Spends tokens only for `--prompt`. | only with `--prompt` |

Flags, valid on either side of the subcommand:

| Flag | Meaning |
|---|---|
| `--project DIR` | Project root; **created if absent**. Default `./.cadex`, or `$CADEX_PROJECT`. |
| `--out DIR` | Write exported files here. Omit and nothing is written. |
| `--format step,stl` | Any of `step`, `stl`, `brep`. Default `step,stl`. |
| `--offset-mm N` | `section`: where along the plane normal to cut. **Omit it** to derive the offset from the accepted bounds (ADR-275); the old default was the constant 0.0, which on a mechanism standing off that plane draws an empty page and calls it `empty`. |
| `--min-clearance-mm N` | `clearance`: flag distances strictly below N (default 0.1 mm). |
| `--max-common-volume-mm3 N` | `clearance`: flag volumes strictly above N (default 0.000001 mm³). Thresholds must be finite and nonnegative; changing them does not rebuild. |
| `--assembly OUTPUT` | `inventory` and `clearance`: the assembly output to inventory. A project publishes at most one, so this is only ever a check that you are looking at it. |
| `--blueprints` | `export` only: also copy the project's stored blueprint sheets into `--out`, store filenames kept (ADR-150) — which since ADR-157 means `0007-gearbox-overview-v1.png` for a **named** sheet rather than a revision prefix. Read-only — the shell renders them; this only reaches the store through `inspect scope=blueprint`. |
| `--engine ROOT` | A staged engine payload. Default: `$CADEX_ENGINE_ROOT`, then the dev tree. |
| `--json` | Emit the machine-readable envelope on stdout. |
| `--wait` | Block for the project lock instead of failing. |

Prompt-only flags: `--resume` (continue this project's conversation),
`--model`, `--claude` (path to the CLI). Model resolution for prompts and
walk design turns is: explicit `--model`, nonblank `$CADEX_MODEL`, the
project's `agent.json.model`, then `claude-fable-5` (ADR-249, ADR-276).
The recorded model applies with or without `--resume`; that flag controls
conversation continuity. A machine can override project choices once through
its environment, and an explicit flag wins over both.
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

1. `cadex -p PROMPT` for each `--prompt`, in order (the first starts or,
   with `--resume`, continues the conversation; the rest continue it) —
   the design turns, and the only leg that spends tokens. None is fine:
   a project whose script already declares its task walks from there.
   The design instructions and new-project `ARCHITECTURE.md` scaffold teach
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
   contract in `cli/cadex_cli/agent.py` now teaches both the switch and
   the two inline literals, and `test_walk.py` rewrites the example it
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
   the design turn's to decide. Before ADR-260 no walk row carried a delta
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
   the next design turn — which reads the notes back in its prompt — never
   a walk failure, and the CLI never writes the note itself: what drives a
   joint and what a sensor measures are the design turn's to say. A run
   that exported no model declares nothing and reports nothing. The walk's
   `PROGRESS.md` row carries the same finding, as `docs notes N, none
   missing` or `docs notes N, no <subjects>`.

   The same review session rebuilds standard display once and snapshots it
   before inspection requests. The `render` block carries availability,
   accepted revision and digest, front/top/right/iso views, approximation and
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
   it did not reach as about what it shows. A plane that reaches every part
   of a spread-out mechanism may not exist; the count is how a reader sees
   that rather than reading `ok` and assuming the drawing is complete. A constant
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
`DIR = runs/<name>`). This table applies to headless local training,
GUI-attached terminal use, and `--remote`; only the training location changes.
The scaffold's `## Training` section carries this same path convention.

| Leg | Artifact in every mode |
|---|---|
| Design / assembly | `script.py`, `ARCHITECTURE.md`, `DECISIONS.md`, `docs/<subject>.md` |
| MJCF / task / training | `runs/<name>/train/` (model, task bundle, returned policy) |
| Store / declare | `assets/<name>.cxpolicy`, `runs/<name>/script.py` |
| Verify / rollout | `runs/<name>/rollout/` (including the simulation trace) |
| Review | `docs/inventory.md`, `docs/clearance.md`, `runs/<name>/review.json` (inventory, clearance and motion summaries with project-relative report paths), `review/render/<accepted-revision>/{front,top,right,iso}.svg` and `summary.json`, `review/section/<accepted-revision>/XZ-<derived-offset>/{section.svg,summary.json}`, `PROGRESS.md` (numbers; remote training rows marked `(remote)`) |

`cli/tests/test_walk.py` checks local/remote artifact parity through policy
verification and rollout using a local CPU stand-in for the dispatcher.
It runs no remote command. GUI attachment remains documented, not exercised;
its sequential-use and refresh requirements are below.

A leg that fails stops the walk there, with the leg's name and its error
in `error` and the legs that ran under `walk.legs`; the exit code is the
leg's for a usage error or a refusal, `1` otherwise. A **design** leg that
ends at exit 3 says which of the two exit-3 turns it was: either the last
thing the engine refused (the op, its failure code and its message) or
`the engine refused nothing` with the tool calls the agent did make, and
in both cases the agent's own closing words, clipped. The walk copies that
string verbatim, so a run with nobody watching records the cause rather
than "the turn finished without the engine accepting a script" — which was
true of both and told nt3 nothing. **A turn that reaches the engine not
once is asked once more** before either of those is written (ADR-274): the
engine, the bridge and the model's reading of the project are all still
standing, so `cadex -p` — and so the walk's design leg — continues the same
conversation with one fixed follow-up and takes a script if one comes. It
fires only when the turn ended well and made *no* tool call; a turn the
engine refused is not asked again. The follow-up is best effort and can
only improve the outcome: if it fails, the run reports the rejection it
already had. Both turns' prose reaches the project's documents, so a
closing `DECISION:` or `NOTE` line from either lands, and `notes` says the
follow-up was asked. Child legs record reward/delta rows
(ADR-194); a successful walk adds the clearance review row described above
(ADR-238). A failed leg leaves earlier rows intact but adds no walk review row.

**Every leg is bounded in wall clock** (ADR-261). `--leg-timeout SECONDS`
(default 3600, `0` for no limit) stops any one leg that runs longer and
fails the walk there, through the same path a refusing leg does: the leg
reports exit **124**, `error` names the leg and the flag, and the walk's
exit is `1`. The stop is a **subtree kill** — the leg runs in a session of
its own and is sent `SIGTERM`, then `SIGKILL` to the group five seconds
later **whether or not the direct child died on the term** — because the
thing that hangs is usually not the child `cadex` but the agent CLI or the
trainer under it, and a grandchild that ignores `SIGTERM` outlives its
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
  fail only after the design and assembly legs have already run. It is a
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
- **`--timeout` is local.** It ends the ssh that holds the run, not the
  run; a long run belongs to `remote_train.sh train --detach` and
  `pull`, outside the walk, which then continues from `cadex asset --put`
  and `cadex script --set` (§2 above). `--leg-timeout` is local in the
  same way and for the same reason: it kills the train leg's session
  here, including the ssh, and the box keeps computing.
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

**With the GUI attached, it is the same walk from a terminal beside the
open file** (ADR-201). The shell is a client of the same store: a saved
`.blend` names `<dir>/<stem>.cadex/` as its engine project — derived from
the file name on every call, never cached (`cadex_backend.project_root`)
— and that directory is the `--project` every command above takes. No
GUI was launched to write this; every sentence is the client code, and
the doc yields to the code where they differ. What the two clients own,
and when:

- **Ownership is by time, and the lock is the CLI's.** A headless run
  takes the advisory `flock` on `.cadex-cli.lock` for **one command**
  (`_engine_session`: lock, spawn, open, unwind) and releases it when the
  engine session ends — *before* the `PROGRESS.md` row and the project
  commit, which guard nothing and need no engine. `cadex walk` takes no
  lock of its own: each leg is a child `cadex` command that takes and
  releases it, so between legs the project is nobody's. **The shell takes
  no lock.** Its `cadexd` child is spawned on the first engine request
  after a file opens and lives until a different file becomes current
  (`on_file_changed` → `close_all`, on open and on Save-As) or the
  application quits. So a person with the file open and a walk in a
  terminal are two engines on one store, and nothing today refuses
  that; `session.py`'s own docstring says what two engines do to a store
  (each restores, each rebuilds, each writes `script.json`). The
  contract is therefore **sequential by convention**: do the design
  turns in the GUI, then run the walk while no rebuild is in flight —
  the shell's engine is idle between operations. Shared session locking
  remains unimplemented; concurrent rebuilds are not guarded.
- **Stale mutations require an explicit refresh (ADR-204).** The engine
  reads `script.json` on guarded writes and refuses a stale
  `expected_revision` as `STALE_PROGRAM_REVISION`. The shell returns that
  refusal without adopting its revision or replaying the source or values.
  Repeating the edit remains refused. Run **Rebuild Model or reopen before
  the next GUI edit**, review the refreshed script and values, then retry.
  Current engine stale precondition failures omit `model_state`, so the
  old shell retry did not activate in the two-engine regression. ADR-201's
  claimed silent overwrite was not reproduced and is corrected here.
  The dormant branch would replay if a stale response carried a newer
  `model_state`; ADR-204 removes it and tests that response synthetically.
  This guards stale mutations, not simultaneous acceptance by two engines.
- **How the shell observes an accepted run.** Three ways, all existing:
  **Rebuild Model** re-runs the script the store holds, read from disk,
  and adopts its source, specs and values into the scene
  (`begin_rebuild_model` → `_refresh_script_state`), so the sliders and
  the script mirror follow the walk's digest edit without reopening.
  **Reopening the file** (File > Open, or Revert) runs `load_post` →
  `queue_open`: the restore-verified `open_project` and the display
  `rebuild`, hydrating the viewport from the engine (ADR-186); a walk's
  accepted revisions restore cleanly, because the CLI accepted them
  through the same ops. The **re-accept box** (ADR-187) appears only
  when the stored script no longer reproduces the accepted digest —
  a hand-edited `script.py`, or a different engine build — and its one
  button sends the store's own source back through `write_script`. A
  completed walk never leaves a project there, but a walk *interrupted
  between its train and declare legs* does: the trained policy has
  already replaced the asset the accepted script names, so the stored
  script will not re-run until the digest edit lands (ADR-272). Running
  the walk again repairs it. Until one of the three happens, the
  viewport shows what the `.blend` baked at its last save.
- **The in-app agent cannot run the walk, and cannot edit the project's
  docs.** The shell starts its CLI with every built-in tool off
  (`--tools ""`) and `--allowedTools` limited to the Mesh tools, from a
  temporary working directory, so it has no shell and no file tool — on
  purpose, so every mutation runs on Blender's main thread. The legs are
  the person's or a pipeline's, at the terminal; `cadex -p` turns run
  their own conversation (`agent.json`, a sibling of the shell's
  transcript in the `.blend`, which carries the shell's own session id)
  and are the one leg that can be done in either window.
- **The two windows resolve the turn model separately**, and this is the
  one place *one shape* is a convention rather than a mechanism. The
  terminal's `cadex -p` takes `--model`, then `$CADEX_MODEL`, then
  `claude-fable-5` (ADR-249). The shell's turn takes its own Blender
  preference, whose default is the **empty string** — meaning whichever
  model the agent CLI itself defaults to — and **the shell reads no
  environment variable**: nothing under `shell/` names `CADEX_MODEL`. So a
  machine that names its model once names it for the terminal legs only,
  and a box whose agent-CLI default is out of usage credit still refuses
  the in-app turn while the walk beside it runs; set the preference to
  match if both windows must spend the same model. Nothing a walk writes
  changes either way — the divergence is in what is spent, not in the
  artifacts — so the `PROGRESS.md` rows still compare line for line.
- **Same steps, same docs, same artifacts.** The legs, their order and
  their refusals are the list above unchanged; `ARCHITECTURE.md`,
  `DECISIONS.md` and `PROGRESS.md` are scaffolded by the first CLI
  visit whichever window came first and written only by the CLI and a
  person; the domain docs are the same `docs/<subject>.md`; and
  `runs/<name>/train/`, `runs/<name>/rollout/`, `review.json` and the
  `PROGRESS.md` row are the same project-relative paths. Nothing a
  walk writes says whether a window was open — which is the point, and
  what makes a GUI walk's `PROGRESS.md` comparable with a headless
  one's line for line. The `ARCHITECTURE.md` scaffold says so in one
  sentence under `## Training` — *with the GUI attached the same
  commands run from a terminal beside the open file* — and
  `cli/tests/test_project_docs.py` holds that sentence and this
  paragraph together.

**Leg by leg, and where the GUI-attached run differs.** The list is read
off `cli/cadex_cli/__main__.py`'s `run_leg` calls and the shell's own
`cadex_backend.py`, `cadexd_client.py` and `__init__.py`, in that order, so
it is the code's list rather than an intended one. The shell **watches
nothing in the project**: it registers four handlers and no more —
`save_pre` and `save_post` (which file this model belongs to, and dropping
the old file's engine child), `load_post` (the open path above), and
`frame_change_post`, which tags the Cadex editors for redraw and writes no
property — and none of them, and no timer, reads the project directory. So
an open window neither sees nor blocks what a leg writes, and the
difference column is empty for every leg but one.

| Leg | The child command | What it lands in the project | With the GUI attached |
|---|---|---|---|
| `design` | `cadex -p PROMPT --project P` (skipped without `--prompt`) | an accepted `script.py` revision, `agent.json`, the turn's `DECISION:` and `NOTE <subject>:` lines, a `PROGRESS.md` row | Artifacts identical. This is the one leg either window can run, and the windows are **not** interchangeable for it: the in-app turn is the shell's transcript in the `.blend` (`history.py`), spends its own model (bullet above), and writes none of the three project documents — `PROGRESS.md` and `DECISIONS.md` are named nowhere under `mesh_agent`. |
| `sweep` | `cadex params --set K=V --out DIR` (only with `--set`) | a new accepted revision, `DIR/` outputs, a `PROGRESS.md` row | No difference. The open scene keeps the values it last read until Rebuild Model or reopen. |
| `train` | `cadex train --out DIR/train`; `--remote` swaps the venv interpreter for `remote_train.sh` and nothing else | `DIR/train/` (bundle, model, returned policy), `assets/<name>.cxpolicy`, a `PROGRESS.md` row marked `(remote)` when the box trained | No difference. The shell runs no trainer — no `mesh_agent` source imports mujoco, and `test_the_shell_never_learns_about_mujoco` pins that for `shell/` as a whole — and it takes no part in this leg in any of the three modes. |
| `script` | `cadex script` | Nothing: the source is read and printed, no revision, no row. | No difference. |
| `declare` | `cadex script --set script.py --json` | the digest edit — the same source accepted at a new revision behind the trained policy | **The one leg whose aftermath a window must be refreshed for.** A GUI edit issued against the pre-walk revision is refused `STALE_PROGRAM_REVISION`, without replay or revision adoption; Rebuild Model or reopen, then edit. |
| `rollout` | `cadex params --set policy_on=1 --out DIR/rollout` | `DIR/rollout/` — the verified policy's simulation trace and outputs — and a `PROGRESS.md` row | No difference. |
| review (no child leg: the walk's own `_engine_session`) | — | `review/render/<accepted-revision>/`, `review/section/<accepted-revision>/`, `docs/inventory.md`, `docs/clearance.md`, `DIR/review.json`, the walk's own `PROGRESS.md` row, and the project commit | No difference. The four eyes render, section, inventory and clearance-check the **accepted revision** through an engine of their own; they never read the viewport, so an open window cannot change what the review says. |

So the honest answer to *where a GUI-attached run differs* is: nowhere in
what the walk writes, once in what the window may do next (`declare`), and
once in what a turn costs (the model bullet). `cli/tests/test_project_docs.py`
holds this table's leg column equal to the walk's `run_leg` names in order —
a new leg fails the doc rather than quietly outdating it — and pins the
four shell facts the difference column rests on.

**The project is a codebase** (ADR-193). Every project root carries the
documents an engineer keeps beside a model, created by the CLI on the
first visit and never overwritten by it:

| File | What it holds | Who writes it |
|---|---|---|
| `ARCHITECTURE.md` | What the project is, what the script declares and why, how it trains, where the domain docs are. | the agent (through its caller) or a person |
| `DECISIONS.md` | The project's own ADR log — what was chosen, over what, why. Newest last. | a turn's closing `DECISION:` lines, or a person |
| `PROGRESS.md` | One row per accepted run: time, command, revision, digest, what, numbers. | **the CLI**, after every accepted run |
| `docs/<subject>.md` | Longer notes, one file per subject: `docs/gear-ratios.md`, `docs/sensors.md`, `docs/actuators.md`, `docs/rejected.md`. | a turn's closing `NOTE <subject>:` lines, or a person |

The agent reads all three on every `cadex -p` turn — they are pasted into
its system prompt, bounded (8,000 characters each: architecture head,
decisions and progress tails; ADR-265), and domain-note tails (2,000 each)
with them. Shortened context carries an omission marker; full files remain
unchanged on disk. This keeps recent decisions available, so a note is worth
writing — and it has no file tool, so what it decides comes back by
convention rather than by a new op: a line of its closing paragraph that
starts `DECISION:` lands in `DECISIONS.md` as the next numbered entry, and
the envelope's `notes` say so. **A longer note lands the same way**
(ADR-245): a closing line `NOTE <subject>: <text>` becomes a dated bullet
in `docs/<subject>.md`, created with a title when the subject is new, and
the envelope names the file. The design instruction asks for
`docs/actuators.md` and `docs/sensors.md` from any mechanism that has
actuators or sensors, which is how the walk exercises the convention
rather than only documenting it. `docs/inventory.md` and
`docs/clearance.md` are the CLI's own generated reports and are not note
subjects — a note never appends to a measurement. `PROGRESS.md` is the CLI's, so it records
what happened rather than what a model said would: `params`, `script
--set`, `export`, `link`, `asset --put`, `train` and a turn each land one
row, with the exported trace's `total_reward` and the trainer's
`reward_per_step`, wall time and sha256 in the numbers column when the
run produced them. Printing the script and listing the store change
nothing and get no row. The shell's own agent has neither a file tool
nor a shell (the Mesh tools are its whole world), so with the GUI
attached the three files are still the CLI's and a person's; the files
are what make the modes one shape.

Fresh and resumed prompt paths are tested without a provider: two scripted
agent turns use the real engine and bridge. The second receives the stored
session id when resumed, the newest decision beyond 8,000 characters and domain
notes, plus architecture, sensor and progress updates made between visits; its new decision and sensor note append to the
existing files. This checks context delivery and persistence, not whether a
real model follows the recorded constraints or sees the omitted older history.

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

Progress rows, decisions and domain-note updates replace their files only after
writing succeeds (ADR-264). A failed write or replacement preserves the previous
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
renders (including the project-root `review/` directory), locks, `.blend1` backups, `.cxpolicy` files outside `assets/`, and
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
`top.svg`, `right.svg`, `iso.svg` and `summary.json`. These generated files
are overwritten on success and stay local under default ignore rules; the
ordinary project commit records the PROGRESS row.
The JSON envelope and each SVG name the accepted revision; the summary also
records digest, component/source names, colors, transformed bounds in mm,
camera bases, projected bounds, coverage, limits and acquisition/render timing.
A failed command must not be treated as a fresh report: old successful files
can remain, and their revision identifies what they describe.

Front looks along +Y with Z up; top along -Z with Y up; right along -X with
Z up; iso views from (1,-1,1) with Z upright. Each orthographic view fits its
own extent. Solved component matrices are applied once; unposed source
outputs used by components are excluded. Other published triangle outputs
are included. The protocol carries no shell-only visibility toggles, materials
or transparency. These are initial-pose geometry previews, not the GUI scene.

SVGs contain lossless 512×512 CPU images with pixel-center depth testing and
flat directional lighting. Crossing triangles occlude per pixel; equal-depth
ties follow sorted output/triangle order. Standard tessellation approximates
curves. Thin/subpixel features can disappear; no dimensions, analytic edges,
transparency, smooth shading or engineering-drawing accuracy is promised.
Limits are 4,096 display entries, 32 MiB total binary/sidecar input, 4 MiB per
sidecar, 300,000 vertices per source, 600,000 placed vertices, 100,000 placed triangles and 20 million
bounding-box pixel visits **per view**, including overdraw. Excessive, missing
or malformed buffers, missing solved poses and empty geometry fail explicitly.
Dense assemblies can exceed the pixel budget even below the triangle cap.

The CLI snapshots buffers while holding its project lock, before any further
engine request can invalidate attempt paths. The shell does not share this
lock: follow the documented GUI-attached coordination rules. Read failures
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
  render.py            accepted tessellation -> depth-tested named-angle SVG previews
  clearance.py         inspect scope=clearance -> docs/clearance.md; read-time thresholds
  inventory.py         inspect scope=inventory -> the project's docs/inventory.md
  train.py             the offboard trainer as a subprocess, local or remote
  walk.py              the lifecycle walk's leg plan (ADR-199)
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
- **The project is a codebase.** Its `ARCHITECTURE.md`, `DECISIONS.md`
  and `PROGRESS.md` are pasted in after the overlay, bounded, on every
  turn (ADR-193); the agent is told to read them before acting and to
  end with `DECISION:` lines for what it decided, which the CLI lands
  in `DECISIONS.md`.
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

`agent.json.updated_at` records a change to the stored session ID or model,
not every attempted turn. An unchanged nonempty session and model leave the
file untouched. A failed turn with the same session ID also preserves the
recorded model, even if another model was requested (ADR-276); a changed
session ID is saved with its requested model even on failure so it can
be resumed. Opening a project may still refresh accepted restore attempt
metadata in `script.json`; a refused walk does not roll that bookkeeping back
or create a failure commit.

Claude Code files a conversation under the directory the turn ran in, so
turns run **in the project root**. A scratch directory per turn would make
every `--resume` look like an expired session.

`<project_root>/.cadex-cli.lock` is an advisory `flock`, because `cadexd` is
one process per project and a sweep will run several of these at once. The
kernel releases it on process death, so there is no stale-lock heuristic to
get wrong. A second run is refused with a readable message; `--wait` blocks
instead. It is held for one command and released before the `PROGRESS.md` row
and the commit. The shell does not take it. Stale shell mutations are
refused without automatic replay (ADR-204); run Rebuild Model or reopen
before the next GUI edit and review the refreshed state. Concurrent
rebuilds and simultaneous acceptance still require sequential use (§2).

## 6. Which engine

In order: `--engine`, then `CADEX_ENGINE_ROOT`, then the development tree
(`.pixi/envs/default/bin/FreeCADCmd` or `build/release/bin/FreeCADCmd`, plus
`src/Mod/cadex`). The first two name a **staged payload root** and are read
through its `cadex-engine.json` manifest, which is the payload's discovery
contract (ADR-020) — the same resolution the shell and
`test_cadexd_lifecycle.py` use.

Resolution rejects unequal, nonempty manifest `protocol` and module
`CadexdProtocol.PROTOCOL_SCHEMA` strings. Agreement proves neither worker
completeness nor shared source provenance. The envelope identifies the resolved
engine.

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
| `test_walk.py` | `cadex walk` against a fake `cadex` (leg order, flags, refusals; no engine), and the toy through two real walks with the real engine and trainer — **skips** the latter without the training venv. |

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
- **No picture tool in the model bridge.** `inspect scope=image` and
  `resolve_pin` remain absent (§4). The caller can use `cadex render` or the
  walk's CPU previews (§2); the model bridge does not expose those commands.
  Since ADR-150:
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
  `--remote` finds `training/remote_train.sh` the same way and configures
  nothing: the box, its venv and its scratch directory are
  `training/.remote.env`'s (ADR-089), and a warm start does not travel.
- One `--set` per parameter, and parameters are numeric — that is what
  `num(...)` declares. A switch is a `num` with `min=0, max=1, step=1`
  and a `>= 0.5` test in the script (ADR-192).
