# cadex-nt3-i19-carriage — Architecture

Read on every visit; keep it true. Maintained by the agent and the
`cadex` CLI (ADR-193 in the Cadex repository).

## What this project is

(One paragraph: the part or mechanism, and what it is for.)

## The script

`script.py` is the whole model — one parametric xscript program. The
parameters it declares and why each exists:

| Parameter | Unit | Why it exists |
|---|---|---|

## Outputs

| Output | Kind | Who consumes it |
|---|---|---|

## Training

**Mode:** (`local` — the trainer runs from its venv on this machine, or
`remote` — `cadex train --remote` / `cadex walk --remote` run the same
leg on the box `training/remote_train.sh` names.) Fill in which, and
why; `PROGRESS.md` marks each remote row `(remote)`.

The shared mode artifacts table in `docs/CLI.md` is the walk contract.
The artifacts are the same project-relative paths in both modes: the
bundle and the policy under `runs/<name>/train/`, the verified rollout
under `runs/<name>/rollout/`, the numbers in `runs/<name>/review.json`
and the generated `docs/inventory.md` component report (also summarized
in the review's `inventory` block), plus `docs/clearance.md` and the
review's `clearance` block. Named front/top/right/iso previews and their
summary live in `review/render/<accepted-revision>/`; the `render` block
carries project-relative paths, revision/digest, approximation, limits and
acquisition/render timings. The walk refuses rendering failures or a revision
that differs from the rollout; old files are never a successful fallback.
`walk_seconds` measures the entry point through review (before final commit).
The `section` block carries the shared snapshot cut at world XZ, Y = 3.125 mm,
under `review/section/<accepted-revision>/XZ-3.125/` (SVG and JSON). It
retains status, availability, revision/digest, plane, units, approximation,
limits and acquisition/section timings. This interior plane cuts both reference
mechanisms without dispatch by mechanism. Empty cuts are available with no
contours; unsupported cuts are unavailable with per-object reasons. Section
errors and rollout digest mismatches fail the walk; retained old artifacts
never imply current success. Clearance covers only the initial solved pose,
at 0.1 mm minimum distance and 1e-6 mm³ maximum common volume. Its own
`PROGRESS.md` row carries offending, unknown and checked pair counts;
unavailable measurements stay unavailable. Training and rollout rows
retain their numbers, so rows
from either mode compare line for line. **Remote runs are cold runs only:** the dispatcher carries the
bundle and the model out and nothing else, so a warm start
(`--init-from`) trains locally. With the GUI attached the same commands
run from a terminal beside the open file, one at a time while no rebuild
is in flight; the shell's own agent cannot run them, and it sees an
accepted run on the next Rebuild Model or reopen. Rebuild Model or
reopen **before the next GUI edit** once a command has accepted a
script: stale mutations are refused without replay or revision adoption.
Review the refreshed source and values before retrying. Simultaneous
acceptance and concurrent rebuilds still require sequential use.

## Domain docs

Longer notes go under `docs/`, one file per subject, named by the
subject — `docs/gear-ratios.md`, `docs/sensors.md`,
`docs/actuators.md`, `docs/rejected.md` — and are linked from here.
