# orun16 SG: sg-s7's rules, written before it was launched

Verified against source: 2026-10-22. Frozen evidence (orun16, iteration 15).
Written before sg-s7 was registered; sg-s6's judgement at 25 and the gate
scoring this screen rests on are `sg-s6-25.md`.

**sg-s7**: sg-s6's task with `heel_sched` gated on the paw's own contact
(`chl_down` / `chr_down`) in place of the clip's stance flag
(`ref_lh_down` / `ref_rh_down`); the same target, half-width and weight (w 6),
`hind_scuff` (w −8) and `overrun` (w −10) kept, nothing else changed.
`~/orun16-queue/orun16-sg7.py` differs from `orun16-sg6.py` in that one
line (and its comment). Built with `cadex script --set` (reward only, so the
model and its clearance are unchanged); no tag (O1 tags model changes only).
Warm from **sg-s6-25** (`517f75c1`) across the one-line task change, critic
warm-up 5, lr 1e-4, seed 1, 4096 envs, 50 iterations, a checkpoint every
25, `budget_s` 5,000 (sg-s6 ran ~60 s an iteration). The build's revision,
the launch time and the log are in `~/orun16-queue/sg-s7.log`.

**The question:** gated on contact, does `heel_sched` schedule both heels,
on the toes at 1.0 m/s and down at 2.4, where the clip-gated one paid RH's
early heel up at speed (`heel_gate.py`: +1.00 as built, −1.35 gated on
contact, at 2400)?

**Rule at 25** (`sg_judge.py` at 1000 / 1700 / 2400, then `legs.py`,
`paw_floor.py`, `p2_lag.py`, `hind_rhythm.py`, `heel_gate.py`): run on to 50
only if, on **both** hind legs (`legs.py`'s heel share of stance), the heel
is down for **at most 0.15 at 1000** and **at least 0.3 at 2400**, with
rotary 8/10 at every command and 2400's median top 2 s speed at least
2.4 m/s. Otherwise stop it as a dead end for its question and record which
clause failed. Report the heel per leg at every command, and LH's taps and
the 1000 hind lag (taps counted and not), either way.

**Rule at 50:** SG's schedule moves if both legs' heel share rises from
1000 to 2400 by at least 0.15, with 1000 at most 0.1 (SG's slow end) on
both legs; RL's direction holds if, at every command, rotary is 8/10 with
each pair's lag at least 40 ms (taps counted) and the fore and hind lag
shares fall from 1000 to 2400. Extend warm (O8) only if SG's holds; the tap
lever (`hind_scuff` stronger, scored separately) is the next screen if RL's
alone fails.
