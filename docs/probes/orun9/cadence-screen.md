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
