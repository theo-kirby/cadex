---
node_id: 8c639120-3207-58ee-bbd4-7ac4dc84e956
slug: rustic-ivy-4753
title: 'ot10: ADR-422 face size and contrast rules; hexapod attempt 4 lifts T5 to 2 but judged 12/21 (accent and caps lost to CPU budget)'
created_at: '2026-09-28T03:57:39+00:00'
parents:
- tiny-dusk-3648
summary: ''
---
## What
ADR-422 (commit `c3abb3ab`), a design-language and overlay change, plus the probe that measures it: A5 hexapod attempt 4 on the new project `ot10-hexapod-4` (commit after it).
- `docs/DESIGN-LANGUAGE.md` §4 has three new rules, each citing core references by filename only:
  - the face, seen from +X, spans at least half the body's width and a quarter of its height there;
  - it contrasts with its surround: graphite in a shell-coloured front, the accent when the front around it is graphite;
  - it is checked from its own side before the design is accepted.
- The CLI overlay's A FACE bullet carries the size and contrast rules. Step 4 adds `look` at `right` (the view from +X) and a face check before accepting.
- New test `test_the_face_is_sized_contrasted_and_checked_from_its_own_side` in `cli/tests/test_turn_loop.py`. It fails on the old overlay and passes on the new one.
- Attempt 4 is published in `docs/probes/ot10/README.md`: six PNGs, each ≤ 143 KB, and `ot10-hexapod-4-score.json`. It is pinned by `test_a5_hexapod_attempt_4_is_published_with_its_score`.

## Why
The critic's message named this unit. Attempt 3's diagnosis (tiny-dusk-3648) found T5 = 1: a graphite slot on a graphite tub, far under §4's proportion. It asked for a checkable face size, a contrast rule for either surround, and an overlay step to `look` at the face from its own side. No judge wording was copied. The rubric, proxies, bar and judge are unchanged.

I did everything the critic asked, with one deviation. The critic asked for a record of the language change and then attempt 4. I recorded both in this single node, because the iteration allows one record and the probe is the measurement of the change. This follows the same fix-plus-measurement shape as pale-ledge-0992.

## Method
- Read `reference/images/1-core/` 07, 14 and 43 to cite the face rules honestly. Nothing was copied.
- Edited §4, the overlay (`cli/cadex_cli/agent.py`), the test and ADR-422.
- Ran `pixi run python -m pytest cli/tests`: 1001 passed, 1 skipped. No engine file changed, so the engine suite and the packaged gate were not rerun.
- Launched the turn detached, with the frozen argv:
  - `CADEX_EFFORT=medium ./cadex --project ~/cadex-projects/ot10-hexapod-4 --model claude-opus-5-5 -p "<frozen hexapod prompt>" --json`;
  - the prompt was read from the README table and matches `contract.json` `a5`;
  - it started at 2026-09-28T03:07:21Z at `c3abb3ab`, with no continuation.
- The turn ended on its own at 03:48Z (41 min) with `ok: true`, at revision `f0b98de47b17…`.
- Ran the notes' `pipeline.sh`, the same as attempt 3's: `cadex render` (3 min 23 s, 102.1 s of acquisition), the five `look` views, and `judge.py` (3 calls, claude-opus-5-5, same rubric sha).
- Counted refusals with `refusals.py`. Transcripts and logs stayed outside git.

## Result
**Attempt 4 misses the A5 bar on one count: judged 12 of 21 against the frozen 14.** Medians: T1 2, T2 2, T3 1, T4 1, T5 2, T6 2, T7 2. The calls were 12, 12 and 10.

Everything else passes:
- static fit: 1,035 pairs clear, with only the floor's advisory world-geometry row;
- swept fit: complete and passing, 12 of 12 joints at 15°;
- 32 welds touching;
- P1 0.013, P2 0.114 and P3 2;
- full electronics.

A4: none of the four refusal classes recurred. The turn had 14 refusals: 8 CPU-limit, 3 sandbox, 1 multi-solid boolean, 1 missing `old` text and 1 guessed pointer.

What the change did: **the face now meets the new §4 rule, and T5 rose from 1 to 2 in all three calls.** The face is a graphite visor band on the bone front, 76 × 13 mm, about 55% of the body's width and 36% of its height in `right`. The agent looked at `right` twice, both times on earlier revisions, not on the accepted one. The judges still read the face as a generic slot.

What lost points: T2 fell from 3 to 2 and T3 from 2 to 1. The agent says why in its own summary. It merged its separate accent feet into the links to fit the 300 CPU-second limit, which left no accent. The hip joints got no caps. It hit the CPU limit 8 times (attempt 3: 4). Its own experiment located the cost in the assembly measurement, not in the geometry. T4 stays 1: a rounded slab with box pods on top.

Four hexapod attempts have scored 13, 14, 13 and 12. **Diagnosis: the binding limit is now the CPU budget, not an untaught rule.** Each attempt spends the budget on a different trait.
- **Recommended next unit:** measure where the accepted `ot10-hexapod-4` build spends its CPU seconds (per stage, per component count), read-only on the project, before any further prompt or language change.
- **Second open concern:** the hero camera (`render.HERO`, 35° round from −Y) sees a +X face nearly edge-on. This is noted in ADR-422 as *Not taken*.

Tail: tiny-dusk-3648 and this node are unreconciled. The critic asked for them to be folded, but a work iteration is forbidden to reconcile, so the next reconcile pass takes both.

Dispatch closed: 1 unit — ADR-422 face size/contrast/look-from-+X rules, measured by hexapod attempt 4 (T5 1→2, total 12/21, misses bar; CPU budget diagnosed as the binding limit)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 5bcf13e07deddf5c1e914b7cf074d3ce3c4fcb3d

## State Impact

- target: loyal-fountain-8709 — hexapod attempt 4 (ot10-hexapod-4) passes every fit gate and judges 12/21, missing the frozen 14; ADR-422 face rule moved T5 1→2, but the accent and joint caps were dropped for the 300 CPU-second limit; hexapod scores so far 13, 14, 13, 12
- target: odd-tree-6681 — ADR-422: overlay teaches a checkable face size, a contrast rule for either surround, and a look at right from +X before accepting (regression test); attempt 4 transcript shows none of the four refusal classes
