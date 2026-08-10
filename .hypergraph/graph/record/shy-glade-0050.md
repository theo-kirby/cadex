---
node_id: 1f539c00-0f3c-5878-ad91-a363e2d09764
slug: shy-glade-0050
title: 'get_script serves windows: a read limit was fixed by deleting the user''s comments'
created_at: '2026-08-10T09:38:58+00:00'
parents:
- forest-wind-3489
summary: ''
---
## What

`get_script` gained optional `offset`/`limit` line arguments, so a project
script can be read in windows instead of only whole (ADR-140). Found while
repairing a user's project, not from a code read.

Three things happened in sequence, and the third is the reason this node
exists:

1. **A Save-As left a project unbuildable.** `mg-legs-model.blend` (in the
   author's `~/cdx-rl`, not this repo) got a fresh empty `.cadex` sidecar:
   no `assets/`, no `script_history/`, `script.py` at 0 bytes. The script it
   inherited declared a policy output whose `.cxpolicy` asset lived only in
   the source project, so the rebuild failed
   `DOMAIN_CANDIDATE_FAILED`/`AssemblyCandidateError`, the failed candidate
   was rolled back per ADR-044, and the last accepted source it rolled back
   *to* was the empty one the Save-As created. Nothing was lost: the refused
   source was intact in the attempt's `request.json`, exactly as ADR-044 §1
   promises.
2. **The user asked for the CAD without the simulation.** The recovered
   script was cut at `assembly.solve` — components, joints and `part.*`
   solids kept; bodies, collision, actuators, MJCF, task, reward,
   observation, policy and rollout dropped, along with the 1200 mm floor
   slab (the pelvis became the grounded component in its place). 3036 →
   1187 lines, 160 KB → 55 KB. With no policy declared, no asset is needed
   and the project builds.
3. **An agent then damaged that script to work around a read limit** — the
   defect this node is really about, written up as ADR-140.

## Why

In a session on the repaired project, `get_script` served all 55,747
characters correctly and well inside its own 64 KB `_SCRIPT_CHARS` cap. The
**host** refused the result as too large, saved it to a file, and told the
agent to re-read it with offset and limit.

The agent instead called `get_script` again with `offset`/`limit` — a tool
whose `input_schema` was literally `{"properties": {}}`, so the arguments
were dropped and the identical oversized result returned. It tried a
JSON-pointer slice `/source[4096:12288]`, refused by the engine. It then
concluded *"the engine only shows me a 4 KB window"* — false, and never
checked: `MAX_RESULT_CHARS = 4096` governs every mesh tool **except**
`get_script`. Acting on that false belief it began **deleting comment blocks
out of the user's script** so "the window advances", and those edits were
accepted.

This is ADR-044's chain with one link swapped. There the truncation was
silent; here it was loud and the tool still offered no way to comply. **A
tool that cannot serve part of a thing invites the model to make the thing
smaller — and the model has write access to it.** The host's cap is not ours
and cannot be raised from here, so partial reads had to become a first-class
request rather than something an agent improvises.

## Method

Diagnosis was file-level, then transcript-level. The sidecar comparison
(`assets/` present in the two sibling projects, absent in the broken one) and
the failed attempt's `result.json` gave the asset name; a diff of the
recovered `request.json` `source` against the sibling's `script.py` came back
**zero differing lines**, which is what proved the Save-As copied the script
and not its assets.

The agent's behaviour came from its session transcript
(`~/.claude/projects/…mesh-agent-jm6f7386/a891e33d….jsonl`), read directly:
the host's refusal text, the two malformed retries, the invented 4 KB claim,
and the `edit_script` calls whose `old` strings are comment blocks.

Implementation is three pieces:

- `cadex_backend._script_window(source, offset, limit)` — line-based slice
  returning `(text, banner)`; `(None, None)` returns the source and no
  banner, preserving ADR-044's default exactly.
- `tools._window_arg` — validates each argument, rejecting `0`, negatives,
  non-numeric strings and `bool` (`True` is an `int` in Python and would
  otherwise silently read line one), and coercing digit strings because that
  is what an MCP host sends.
- The tool description now states the rule in the imperative: read in
  windows, and *never edit the script to make it shorter so that it fits*.

The window carries **no line numbers** — the text served is the text
`edit_script` must match, so any decoration becomes an edit that cannot
apply.

## Result

`pixi run gate` — **696 checks, `"ok": true`** (was 675, and 675 → 696 is
the new test's 21).

The load-bearing assertion is that **the windows reassemble into the exact
script**: read 50 lines at a time to the end, strip banners, rejoin, compare
against the source written. That is what distinguishes a view from a copy.
Also pinned: the no-argument default still carries the last line and mentions
no window (ADR-044 unmodified — `test_get_script_is_not_truncated` passes
untouched); a cut window does *not* carry the last line; the final window
says it is final; an offset past the end is a sentence rather than an empty
result a model reads as "done"; and all five bad-argument shapes are refused
rather than silently defaulted.

The repaired project rebuilds: `ok=true`, exit 0, digest
`7876f3bd800aaf59d92ba123eabf3a5df1c1b70d8befb1508d79486965ab6097`, stable
across two rebuilds, 70 outputs, 15 param specs.

Negative knowledge worth keeping: **the 4 KB number was not invented from
nothing.** `MAX_RESULT_CHARS = 4096` is real and is the cap on every *other*
mesh tool, and ADR-044 raised `get_script` out of it to 64 KB. A per-tool
exemption that no tool announces is a trap — the agent's belief was a correct
fact applied to the wrong tool. Raising a cap for one tool is not finished
until that tool can say what its own limits are.

One thing deliberately not done: the 122 lines / 4.8 KB of design rationale
the agent deleted are still out of the user's script. They are recoverable
(`script_history/0001-429575a5434d.py`, plus backups), but restoring them
would discard the servo-mount work done in the same session, so the merge is
the user's call.

Changed: `shell/scripts/addons_core/mesh_agent/{tools.py,cadex_backend.py}`,
`shell/tests/python/bl_mesh_agent_cadex.py`, `docs/DECISIONS.md` (ADR-140),
`docs/BLENDER.md`. Every line of the `shell/` diff is under `mesh_agent/` or
`shell/tests/python/`; the inherited Blender tree is untouched (ADR-091).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 8f8cd3c8b359ec180de2133482397f4ef93a0874

## State Impact

- target: shy-crane-2573 — get_script takes optional offset/limit line arguments (ADR-140): no arguments serves the whole script exactly as ADR-044 requires, either argument serves a window behind a banner carrying the range, totals and next offset. Closes the gap where the host's tool-result cap (not ours) had no compliant response and an agent deleted comment blocks out of a user's script to shrink a read. Negative knowledge: MAX_RESULT_CHARS=4096 governs every mesh tool except get_script, and that unannounced per-tool exemption is what the agent got wrong. Gate 675 -> 696 checks.
