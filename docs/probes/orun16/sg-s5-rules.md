# orun16 SG: sg-s5's rules, written before it was launched

Verified against source: 2026-10-22. Frozen evidence (orun16, iteration 12).
Written at 13:18, before sg-s5 was registered (launched 13:19:14, `~/orun16-queue/sg-s5.log`); the judgement of sg-s4 at 50
is `sg-s4-50.md`.

**sg-s5**: sg-s4's task with `heel_tail` replaced by `heel_sched` (D 30,
W 30, w 6; `heel-sched.md`), `overrun` kept; leo revision `839a3378`
(`cadex script --set ~/orun16-queue/orun16-sg5.py`, leo commit `34aaaff`,
reward only: "kept revision 53's model, 0 new bytes"), no tag (O1 tags model
changes only). Warm from sg-s4's final policy (`gallop_sg.cxpolicy`,
`c94393a4`) across the task change, critic warm-up 5, lr 1e-4, seed 1, 4,096
envs, 50 iterations, a checkpoint every 25, `budget_s` 5,000.

**The question:** does a heel target tied to the command schedule the heel,
on its toes slow and down fast?

**Rule at 25** (`sg_judge.py` at 1000 / 1700 / 2400, then `legs.py`,
`p2_lag.py`): keep running to 50 only if, on **both** hind legs (`legs.py`'s
heel share of stance), the heel is down for **at most 0.15 at 1000** and
**at least 0.25 at 2400**, and **1000's hind pair lag is at least 40 ms**
(`p2_lag.py`'s median hind lag share times the 2.0 Hz stride, over all
strides). Otherwise stop it as a dead end for its question and record which
clause failed.

**Rule at 50:** SG's schedule moving means both legs' heel share rises from
1000 to 2400 by at least 0.15, with 1000 at most 0.1 (SG's slow end) on
both legs; extend warm (O8) only if so, with rotary on 8/10 at every
command.
