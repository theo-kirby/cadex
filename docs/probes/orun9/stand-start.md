# orun9 C1: the stand spec measured both ways (ADR-761)

Verified against source: 2026-10-17. Frozen run evidence: read it, never
cite it as current.

`lawful-ridge-3792`: the stand spec's seeds began inside the trot reference
at a random phase (ADR-709), so the cat started at about 1 m/s. "Drifts less
than 0.2 m in 10 s" therefore counted a stop from 1 m/s as well. The critic
asked for the stand spec measured both ways and the choice made in an ADR,
without weakening it to pass. Scripts and output are in
`~/orun9-progress/standrest/` (outside the repo).

## Way 1: the existing traces, drift after the stop

`aftersplit.py` re-reads every judged stand evaluation (34 of them, c1-t2 to
c1-c11b) with the engine's own `CadexEvaluation.base_series` and the
evaluation's rig. Its as-spec column reproduces `max_drift_mm`. "After the
stop" is the largest plan drift measured from the first frame whose 0.2 s
plan speed is under 50 mm/s. A seed passes after the stop when that drift is
under 200 mm and every other predicate passed on it. The numbers barely move
with the threshold: at 30 mm/s and at 100 mm/s, each of the six checkpoints
re-checked changes by at most one seed.

| checkpoint | spec drift med, pass | brake (med) | after-stop drift med / max, pass |
|---|---|---|---|
| c1-c10 @100 | 241 mm, 1/10 | 0.58 s, 182 mm | 108 / 148 mm, **10/10** |
| c1-c11b @50 | 248 mm, 0/10 | 0.74 s, 231 mm | 146 / 168 mm, **10/10** |
| c1-c9 @50 | 289 mm, 0/10 | 0.88 s, 251 mm | 78 / 192 mm, **10/10** |
| c1-t2 | 348 mm, 1/10 | 0.56 s, 198 mm | 155 / 199 mm, **10/10** |
| c1-c11b @100 | 288 mm, 1/10 | 0.56 s, 188 mm | 125 / 249 mm, 9/10 |
| c1-t8 @300 | 291 mm, 0/10 | 0.72 s, 188 mm | 140 / 278 mm, 8/10 |
| c1-t7 @50 | 185 mm, 3/10 | 0.56 s, 144 mm | 78 / 114 mm, 5/10 (within_rated) |
| c1-t6 @300 | 173 mm, 0/10 | 0.82 s, 111 mm | 106 / 257 mm, 0/10 (within_rated) |

The brake alone takes 111–251 mm (median per checkpoint) of the 200 mm
budget on every checkpoint, so under the old start a pass needed a stop in
under about 120 mm (about 4 m/s²). The full table is `aftersplit.txt`.

## Way 2: the engine's evaluation, from rest

`judge_rest.py` is orun8's `judge2.py` with one change: in the spliced task
the reference starts at phase 0 (the keyframe at zero velocity, then the
task's own reset variation of 0–150 mm/s and 0–10 °/s). Each seed then
starts at 0.06–0.16 m/s (seeds 1001 and 1005, at 0.06 s), not 0.86 m/s. The
episode lasts the full 10 s, the 200 mm threshold is unchanged, and every
other predicate still applies.

| checkpoint | stand from rest | still med | within_rated med | shove from rest |
|---|---|---|---|---|
| c1-c10 @100 | **10/10** | 120 mm | 0.80 | **10/10** |
| c1-c10 @50 | 9/10 | 104 mm | 0.75 | 10/10 |
| c1-c11b @100 | 8/10 | 151 mm | 0.86 | 10/10 |
| c1-c11b @50 | 8/10 | 164 mm | 0.75 | 10/10 |
| c1-t8 @300 | 9/10 | 99 mm | 0.57 | — |
| c1-t8 @50 / @100 | 8/10 / 7/10 | 112 / 134 mm | 0.66 / 0.59 | — |
| c1-t6 @50 | 8/10 | 141 mm | 0.92 | — |
| c1-c9 @50 / @100 | 8/10 / 3/10 | 174 / 196 mm | 0.84 / 1.02 | 10/10 / 9/10 |
| c1-t7 @50 | 2/10 (within_rated 2) | 79 mm | 1.06 | — |
| c1-c8 @100 | 2/10 | 251 mm | 0.61 | — |
| c1-t6 @300 | 0/10 (within_rated 0) | 101 mm | 1.20 | — |

The two ways agree on which checkpoints stand: c1-c10 @100 passes both. The
checkpoints that fail from rest fail on creep (c1-c8, c1-c9 @100) or over
rated (c1-t6, c1-t7), not on the start.

## The decision, and what it does not cover

ADR-761: the stand and shove specs start their seeds at rest. The cat's
script gives `c1_task` a `start` argument, and stand and shove pass
`"phase0"`. Revision `b0ac2154` was rebuilt in 6 min 9 s. Its `run` bundle
is byte-identical to `396afbb7`'s (sha256 `d19e565c…`), so training is
unchanged. `judge2.py --start-may-differ` lets only `reference.start` differ
between the judged task and the trained one. Judged that way on `b0ac2154`,
c1-c10 @100 gives stand 10/10 (still median 120.38 mm) and shove 10/10. This
equals `judge_rest.py` on `396afbb7` to the digit.

The stop from 1 m/s is a transition, so it falls under C1's "smooth changes"
clause ("moves between stand, walk and run without falling"). Under that
clause it is judged by falling, not by drift. Nothing judges a run-to-stand
transition today. `run`'s sequence (500/3000/1500/500/3000 mm/s) covers walk
and run only. The as-spec numbers above stay on record as the brake
measurement.
