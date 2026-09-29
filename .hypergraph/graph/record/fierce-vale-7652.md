---
node_id: f242c9f8-579f-51fc-8559-e210b81db88b
slug: fierce-vale-7652
title: 'ot10: hexapod attempt 10 meets the A5 bar at 14/21; attempt 9 was a harness kill'
created_at: '2026-09-28T13:19:52+00:00'
parents:
- brisk-lodge-6248
summary: ''
---
## What
A5 hexapod attempt 10 ran on the new project `ot10-hexapod-10`. It used the frozen hexapod prompt from `contract.json` `a5.prompts.hexapod`, word for word, with the same argv, `claude-opus-5-5`, `CADEX_EFFORT=medium`, design-only and no continuation. It launched at revision `9f13d33d` (after ADR-429). It was rendered by A2 from a `/tmp` copy, judged blind under the frozen A1 procedure (three calls) and published in `docs/probes/ot10/README.md` with a score file, six renders (all under 300 KB) and a contract test (commit `edbc2502`).

## Why
The critic asked for the next hexapod attempt under the frozen conditions after ADR-429. It serves A5 (`loyal-fountain-8709`). I did what was asked, with one deviation in numbering. Attempt 9 was already started on `ot10-hexapod-9` at 12:13:49Z by the previous session. Its process died about four minutes in, when that session ended: no exit file and no accepted revision. That is a harness interruption, not an attempt. So the fresh run went to a new project, `ot10-hexapod-10`, launched with `setsid nohup` so it would outlive this session. `ot10-hexapod-9` is kept read-only as the receipt.

## Method
- Turn: 2026-09-28T12:25:51Z to 13:09:33Z (44 min), exit 0, `ok: true`, accepted revision `e8a82deb1a06…`, digest `1e0f233588da…`.
- `cadex render`: 3 min 47 s in all (108.7 s acquisition, 9.0 s drawing, 2.7 s for the 1024 px hero, 162,427 triangles).
- The look views were drawn with `ot10-notes/look_views.py`; `runner/judge.py` judged the hero plus five views.
- Refusals were counted with `ot10-notes/refusals.py` from session `3f61a367…`.
- The fit, sweep and inventory were read from the turn JSON; the proxies from `review/render/summary.json`.
- Notes are under `~/cadex-projects/ot10-notes/hexapod-10/`, outside git.

## Result
**Meets the A5 bar on every item. It is the first hexapod in the run to do so.**
- Judged total 14/21 (the bar is ≥14). All three calls gave the same scores: T1 2, T2 2, T3 1, T4 2, T5 2, T6 3, T7 2. No trait is 0, and 14 is above hex3's 2.
- P1 0.0026, P2 0.1415, P3 3, and every component declares its appearance role.
- Static fit: 1,326 pairs, 1,320 clear, 0 intersections. The only failing row is the floor's advisory world-geometry row, the same treatment the passing biped-1 and quadruped-3 received.
- Swept fit: complete and passing on 12/12 joints at 10° steps.
- Electronics: ESP32, PCA9685, BNO085, D36V50F6, 2S LiPo and 12 × MG90S. MJCF and a walking task were also accepted.

**A5 status:** with `ot10-biped-1` (15) and `ot10-quadruped-3` (15), each of the three body plans now has a design that meets the bar. The earlier failed attempts are all published. Whether the "one failing design fails this criterion" clause counts those misses is the owner's call, and this record does not tick anything.

A4: none of the four refusal classes recurred. There were 15 refusals:
- 6 CPU-limit;
- 3 sandbox or source-policy;
- 3 guessed JSON pointers;
- 1 `api.fuse`;
- 1 `api.cut` refine;
- 1 `edit_script` zero-match.

CPU-limit refusals are still the largest class. The agent escaped them by swapping loft bodies for filleted boxes, which is the ADR-428 advice.

The judge's weakest trait, and so the next hexapod gain, is T3: bare hip pins, and shell-coloured servo boxes hanging under the body. After that comes T5: the visor is a generic slot.

`test_ot10_contract.py` passes 21/21. The full suites were not re-run, because no product code changed.

**Next (my recommendation for the critic):** A5 now has evidence for all three plans. The highest-ranked criterion with no evidence is A6, the concept sheet. After that come W1 and W2, and W2 can use `ot10-hexapod-10` or `ot10-quadruped-3`. The tail is at 3 unreconciled records, so a reconcile is due.

Dispatch closed: 1 unit — hexapod attempt 10 meets the A5 bar at 14/21 with clean fit, complete sweep and electronics; attempt 9 was a harness kill and is not counted.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: edbc250217bdfc91f2c799df3275df05ed5c4346

## State Impact

- target: loyal-fountain-8709 — hexapod attempt 10 (ot10-hexapod-10) meets every A5 bar item: 14/21 with no zero trait, P1 0.0026 / P2 0.1415 / P3 3, 0 static intersections, complete passing 12/12 sweep, full electronics; with biped-1 and quadruped-3 every body plan now has a passing design (earlier misses published); ot10-hexapod-9 was a harness kill, not an attempt
