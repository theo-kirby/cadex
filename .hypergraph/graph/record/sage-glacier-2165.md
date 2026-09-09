---
node_id: 50541d7d-cdb2-5dc1-8c04-6400cdde8ed2
slug: sage-glacier-2165
title: One uninterrupted walk, and the silence that had been ending them
created_at: '2026-09-09T00:05:52+00:00'
parents:
- rising-rain-0117
summary: ''
---
## What

**The lifecycle walk ran clean, end to end, in one uninterrupted invocation**
— `runs/uninterrupted-46` on `ot4-quill`: exit 0, design 80.48 s, train
19.62 s, declare 0.60 s, rollout 1.07 s, walk 103.245 s (1:43.29 external
wall, peak RSS 1,947,408 KB), no leg run by hand, no kill, no retry. And the
defect that had cost the three attempts before it is fixed: a design turn that
reaches the engine **not once** is now asked once more in the same
conversation (ADR-274, commit `8717f8ed`).

Advances the open charter criterion **"The walk exists and is tested
headlessly"** (`crisp-reef-5607`), which is the frontier the horizon ladder
names as leading this run.

## Why

The overseer's steer: *"Re-run the live walk, one uninterrupted invocation,
with a prompt matched to the project. Exit 3 was your prompt asking for a
swing arm `ot4-quill` doesn't have."* That is plan unit 1 of
`young-crane-9546`, and the rung says to attempt it before anything else.

The first attempt this pass took the steer and still failed. The prompt was
read off the project's own record this time — `docs/swept-envelope.md` ends
with two findings the last turn left for a later one, about the bore mouth and
the bore clearance — and the turn engaged with both, on its own parts. It
ended at exit 3 anyway, at 84.3 s, `stop_reason: end_turn`, 6,228 output
tokens of which **5,893 were thinking** and ~335 prose: the model reasoned to
"*Finding 2 I believe is wrong… **Finding 1 I believe and am taking.***" and
ended the turn before acting on it. Nothing refused, nothing offered, project
byte-for-byte unchanged.

That is a product defect, not a prompt defect, and it is the third instance in
one evening. ADR-247 made the cause *legible* — which is how it was diagnosed
from an envelope — but legibility is not recovery, and a loop with nobody
watching gets one design turn per invocation. So: fix it, then re-run.

## Method

**The fix (`cli/cadex_cli/__main__.py` only).** After the first turn,
`command_prompt` asks once more with a fixed `NUDGE_PROMPT` — the project is
unchanged, make the change now, or answer `NO CHANGE:` — inside the same still
open bridge and conversation. Narrow by construction: it fires only when the
turn ended **well**, made **no** tool call, had **nothing** accepted and left a
resumable session id; a turn the engine refused was told why and is not asked
again. One follow-up, never two. Best effort — a follow-up that itself fails
leaves the run with the rejection it already had rather than a harder failure,
so it can improve an outcome and cannot worsen one. Both turns' prose is
folded, so a closing `DECISION:` or `NOTE <subject>:` line from either still
lands in the project's documents.

Three regressions in `cli/tests/test_turn_loop.py`; **two fail on the old
source** (verified by stashing the source change: `assert 1 == 2` on the turn
count), and the third pins the narrowness — a refused turn is asked nothing —
so it passes either way by design.

Gate for the zone: `JAX_PLATFORMS=cpu pixi run python -m pytest cli/tests` —
**268 passed, 0 skipped, 213.92 s**, including `test_walk.py`'s two real
engine-and-trainer walks, which skip without a training venv and did not skip.

**Then the live walk**, one command, `PYTHONPATH` / `CADEX_ENGINE_ROOT` /
`CADEX_MODULE_DIR` unset, `/usr/bin/time -v` around the whole tree:
`CADEX_MODEL=claude-opus-5 JAX_PLATFORMS=cpu ./cadex walk --project
~/cadex-projects/ot4-quill --out …/runs/uninterrupted-46 --resume --prompt …
--iterations 5 --envs 16 --seed 0 --timeout 600 --leg-timeout 1800 --json`.
One sentence was added to the prompt telling the turn to act in the same turn.

## Result

**Exit 0, every leg, one invocation.** The design turn read the record,
**rejected** the bore-clearance finding — 0.05 mm radial is a valid precision
sliding fit and the walk's 0.1 mm threshold is a report setting naming a real
proximity, so deleting a sound design point to silence a true report is
backwards — and **took** the bore-mouth one as project ADR-008: the
head-to-bore-mouth clearance is the declared parameter `mouth_gap` (default
5.0, range 2–40) rather than a hard-coded `+ 5.0` in the `bore_z0` derivation.
It checked itself three ways in the same turn: solids bit-identical at the
defaults (housing 236 379.31314 mm³, quill 24 131.68026 mm³), the span held at
2 and 40 with the policy switch down, and the parameter proved to be a
**floor** rather than the gap — 38.00 mm actual against a 2.00 mm floor at
`mouth_gap` 2 / `stroke` 10 — which it wrote into `docs/swept-envelope.md`.

| | `live-iterate-43` (before) | `uninterrupted-46` |
|---|---|---|
| objective digest | `v1:ddee1f6a…` | `v1:ddee1f6a…` unchanged |
| total reward | 175.3771498711709 | 175.3771498711709 (Δ ±0.0) |
| clearance offending / unknown / checked | 0 / 0 / 1 | 0 / 0 / 1 |
| section | derived XZ 0.0, both parts | derived XZ 0.0, both parts |
| inventory | 2 components, 0 catalogued | 2 components, 0 catalogued |
| docs notes | 2, none missing | **3, none missing** |

The reward row is a **real** comparison this time and that is its point: the
objective digest did not move, because the geometry at the defaults is
unchanged by construction, so an identical total is evidence that promoting
the literal cost the rig nothing — not a number reported beside a different
task, which is what the ADR-007 walk had.

**The honest half: the fix was not exercised live.** `asking once more`
appears zero times in the run's stderr — the first turn called tools, partly
because the prompt now says to. So the follow-up's live value is still
untested; what is tested is the offline seam, on a real engine and a real
bridge socket, and the narrowness. A future exit-3-by-silence is the only
thing that can prove it, and it will be visible as the `notes` line the run
writes.

**What the criterion still needs.** `crisp-reef-5607` asks for a documented
entry point taking a mechanism design → assembly → MJCF → task → toy CPU
training → verify → rollout → review with no human step. That is now
*demonstrated* rather than argued: one command, one exit code, artifacts in
the project, numbers in its `PROGRESS.md`. What is missing before it can be
ticked is that the walk begins from an existing project — this run resumed
`ot4-quill`'s conversation and its accepted script — so design-from-nothing
through the same entry point is unevidenced here (`ot4-carriage` and
`ot4-swing2` did it in earlier runs, at 5:59 and 17:43, and that is the
evidence to gather into one place next).

No generated artifact entered the run branch: this repo's diff is
`cli/cadex_cli/__main__.py`, `cli/tests/test_turn_loop.py`, `docs/CLI.md` and
`docs/DECISIONS.md`; the walk's outputs are commits in the project's own
repository at `~/cadex-projects/ot4-quill` (`380b294`, `cb76cee`).

Dispatch closed: 1 unit — the lifecycle walk ran clean in one uninterrupted invocation (`runs/uninterrupted-46`, exit 0, 103.2 s), after fixing the exit-3-by-silence that killed the three attempts before it (ADR-274, 268 CLI tests, two regressions failing on the old source).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 8717f8ed8fac620e6cca9477d739261f8d788699

## State Impact

- target: crisp-reef-5607 — The walk ran end to end in ONE uninterrupted invocation on this machine: runs/uninterrupted-46 on ot4-quill, exit 0, design 80.48 s / train 19.62 s / declare 0.60 s / rollout 1.07 s, walk 103.245 s, peak RSS 1.95 GB, no leg by hand and no retry. The design turn read the project's own record, rejected one recorded finding with reasons and took the other as project ADR-008, verified the change bit-identical at defaults and swept its span; the objective digest did not move, so total reward 175.3771498711709 is an exact comparison against live-iterate-43 rather than a number beside a different task. Still missing before the criterion ticks: this run resumed an existing project, so design-from-nothing through the same entry point is unevidenced in this walk.
- target: chilly-union-8972 — A design turn that reaches the engine not once is asked once more in the same conversation (ADR-274, commit 8717f8ed, cli/cadex_cli/__main__.py). It fires only when the turn ended well, made no tool call, had nothing accepted and left a resumable session id; a turn the engine refused is not asked again; exactly one follow-up; a follow-up that fails leaves the rejection the run already had; both turns' prose is folded so a closing DECISION: or NOTE line from either still lands. 268 CLI tests pass, 0 skipped; three new regressions in test_turn_loop.py, two failing on the old source. Not exercised live yet — the live walk's first turn called tools.
