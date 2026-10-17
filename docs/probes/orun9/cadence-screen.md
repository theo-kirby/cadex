# orun9 C1: the trot clock's cadence exponent (c1-c6)

Verified against source: 2026-10-17. Frozen evidence (orun9, iteration 10).

**Why.** c1-sp2 (`sprint-screen.md`) ran its two 3 m/s segments at
2.20–2.35 and 1.66–2.16 m/s, and every drive stayed within rated (worst
0.91). So the rated price is not what holds the cat back. Another
constraint is the gait clock, which the policy reads (`ref_sin`/`ref_cos`).
On ADR-752's speed cadence the clock turns `(|cmd| / 1000 mm/s) ** 0.4` of
the clip's turn, and the trot clip has a 0.58 s period, a 0.58 m stride per
cycle at 1 m/s. At 0.4 a 2.3 m/s command turns it at 2.40 Hz, so the cat must
cover 0.96 m a cycle; at 3 m/s it turns at 2.67 Hz, 1.12 m a cycle. The speed
the cat reached therefore matches a stride near 0.96 m. Exponent 0.6 asks
3.32 Hz and 0.90 m a cycle at 3 m/s. The exponent may go up to 1.0
(`api.task`).

**c1-c6.** The cat's script takes a `cadence_exp` parameter
(`~/orun9-progress/c1c6/c6-script.py`, set to 0.6). The project accepts it
at revision `08d86153`. The cat's first build after the engine change took
about 80 min, against 6 min for the previous reward-only rebuilds; the
engine digest changed, so no memoised geometry was reused. c1-c6 is a
100-iteration warm start from c1-sp2 at iteration 50 (run 713 mm/s RMS
within rated, turn2 10/10, shove 10/10), with `--critic-warmup 10`. The
trainer accepted it as a curriculum step that changes `tracking.cadence`
alone (ADR-752), carrying the source's normaliser (49,152,000 samples) and
σ 0.571. The first 13 iterations follow c1-sp2's to within 0.25 reward a
step (4.22 → 5.77 against 4.43 → 5.81). It is registered with the dashboard
view retained, in the scope `orun9-c1-c6`. Not judged yet: judge 50 and 100
on all six specs with `~/orun9-progress/c1c6/judge_c6.sh`.

## Judged (iteration 11)

c1-c6 finished 100 iterations (exit 0; wall time 1,599 s, 16.0 s an
iteration; the witness agrees to 2.0e-7). Both checkpoints were judged on
the six specs on the 10 frozen seeds (`judge_c6.sh`, `judge2.py
--reward-may-differ`, CPU only, 51 s a checkpoint). The source column is
c1-sp2 at iteration 50, the checkpoint c1-c6 warm-started from.

| spec | source (sp2 @50) | it 50 | it 100 | failing predicate, median (it 100) |
|---|---|---|---|---|
| run | 0/10, 713 mm/s | 0/10, 690 mm/s | 0/10 | tracks_speed 597 mm/s RMS (575–643); within_rated passes, worst drive 0.82–0.88 |
| stand | 0/10, 532 mm | 1/10, 284 mm | 0/10 | still 389 mm (261–510) |
| shove | 10/10 | 10/10 | 9/10 | one seed tipped (upright 32° max) |
| turn2 | 10/10 | 7/10 | 6/10 | tail_clear 6/10; tracks_yaw passes |
| reverse | 0/10, 64° | 0/10, 73° | 0/10 | reverses 68°; tail_clear 6/10 |
| points | 0/10 | 0/10 | 0/10 | reaches 0, close 6337 mm |

**Speed per command segment** on `run` (commands 0.5, 3.0, 1.5, 0.5 and
3.0 m/s, 2.4 s each; `segspeed.py`, mm/s across the 10 seeds):

| checkpoint | 0.5 | 3.0 | 1.5 | 0.5 | 3.0 |
|---|---|---|---|---|---|
| c1-sp2 @100 (cadence 0.4) | 540–630 | 2200–2350 | 2040–2170 | 650–760 | 1660–2160 |
| c1-c6 @50 | 483–573 | 2204–2311 | 2012–2154 | 575–721 | 1982–2246 |
| c1-c6 @100 | 467–581 | 2364–2445 | 1813–1990 | 573–706 | 2079–2394 |

**Finding.** A faster gait clock bought speed within rated. The 3 m/s
segments rose by about 0.1–0.2 m/s, and run RMS fell to 597 mm/s, the best
any orun8 or orun9 cat has judged (c1-t8 806, c1-sp2 781). Every drive stayed
within rated (worst 0.88). The clock reads the command, so at a 3 m/s command
it turns at 3.33 Hz, and the cat's 2.36–2.45 m/s is 0.71–0.73 m a cycle,
short of the 0.90 m the clock asks. At cadence 0.4 (2.68 Hz) c1-sp2's
2.20–2.35 m/s was 0.82–0.88 m a cycle. The stride the cat takes shrank less
than the clock's frequency rose, so the speed gain came from the frequency.
At a stride of about 0.72 m, 4.15 Hz would be 3.0 m/s. The cost
is elsewhere: stand drift went back up by iteration 100, shove lost a seed,
and the tail touches in turn2 and reverse on 4 seeds of 10. Under the
critic's rule (speed rose within rated), the next screen is cadence 0.8.
At 3 m/s that clock turns at 4.15 Hz and asks 0.72 m a cycle. c1-c6
passes no clause c1-sp2 did not, but it is the first run since c1-h2 to move
a binding number (run RMS) by more than 10%.

## c1-c7 launched (cadence 0.8)

`~/orun9-progress/c1c7/c7-script.py` is c6's script with `cadence_exp`
0.8. The project accepts it at revision `aa8003ea` (project commit
`0d86bf9`) in 6.5 min, keeping revision 96's model (no new tessellation).
c1-c7 is a 100-iteration warm start from c1-c6 at iteration 100, with the
same settings as c1-c6 (8192 envs, seed 0, unroll 20, slew 15°, checkpoints
every 50, `--critic-warmup 10`). The trainer accepted it as a curriculum
step that changes `tracking.cadence` alone, carrying the normaliser
(65,536,000 samples) and σ 0.570. It is registered with the dashboard view
retained, in the scope `orun9-c1-c7` (MemoryMax 30G). The GPU sat idle for
about 8 min between c1-c6's end and this launch: the judge and the rebuild
had to run first, because `judge2.py` judges against the accepted revision,
which must keep c1-c6's cadence. Judge it with
`~/orun9-progress/c1c7/judge_c7.sh`.

## c1-c7 judged (cadence 0.8; orun9, iteration 12)

c1-c7 was warm-started from c1-c6 at iteration 100 and trained for 100
iterations. Its checkpoints at 50 and 100 were judged on all six specs, 10
frozen seeds each (`judge_c7.sh`). Failing predicates are given with their
pass count and median.

| spec | c1-c6 @100 (0.6) | c1-c7 @50 | c1-c7 @100 |
|---|---|---|---|
| run | 0/10; tracks_speed 597 mm/s | 0/10; tracks_speed 654 | 0/10; tracks_speed 614 |
| stand | 0/10; still 389 mm | 0/10; still 453 | 0/10; still 449 |
| shove | 9/10 | 9/10 | 9/10 (completes, upright, recovers 9/10) |
| turn2 | 6/10; tail_clear 6/10 | **10/10** | 9/10; tail_clear 9/10 |
| reverse | 0/10; 68° | 0/10; 52.5° | 0/10; **48.6°** |
| points | 0/10; closest 6,337 mm | 0/10; 5,430 | 0/10; 4,730 |

`within_rated` passes 10/10 on `run` at both checkpoints (worst drive
0.92 and 0.91 of rated, against 0.88 for c1-c6).

**Speed per command segment** on `run` at c1-c7 @100, in mm/s across the
10 seeds:

| 0.5 | 3.0 | 1.5 | 0.5 | 3.0 |
|---|---|---|---|---|
| 452–531 | 2229–2427 | 1875–2030 | 539–694 | 2154–2366 |

**Finding.** Cadence 0.8 bought no speed. The 3 m/s segments are where
c1-c6 had them (2364–2445 and 2079–2394): at 4.15 Hz the cat shortened
its stride rather than run faster, so above cadence 0.6 the clock no longer
limits top speed. Run RMS did not fall (614 against 597), and stand drift
stayed high (449 mm). What c1-c7 did gain is in the turns: the tail clears
again (turn2 9–10/10, against 6/10), and reverse came within 48.6° of its
heading against 68°. It passes no clause c1-c6 did not. So c1-c6 and
c1-c7 are two consecutive judged cat runs with no new clause, and under O1
the next GPU run is a B run.
