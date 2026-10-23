# orun17 RL: the `fore_lag` fallback bundle, sgt-5 (built, not launched)

Verified against source: 2026-10-23. CPU work while sgt-4 trains to 120
(iteration 55 at 03:09, ~04:40–05:00 to finish). The critic asked for the
fallback ready so the GPU does not idle if sgt-4-120 still doubles the slow
fores; it is launched only on that trigger.

## What was built

`~/orun17-queue/orun17-sgt5.py` is `orun17-sgt4.py` with one term appended
to `SG_REWARD`, after `hind_scuff`:

```
fore_lag  w 10
abs(ref_lf_down - ref_rf_down) * (1 - abs((cfl_down - cfr_down) - (ref_lf_down - ref_rf_down)))
```

orun15's term, unchanged, `hind_lag`'s form on the fore pair, priced on
sgt-4's clip in `fore-lag-sgt4.md` (single strike over double, 0.137 a step
at 700).

```
systemd-run --user --scope -p MemoryMax=30G ./cadex script --project ~/cadex-projects/leo \
    --set ~/orun17-queue/orun17-sgt5.py --json      # ~/orun17-queue/sgt-5-build.log
```

- **Accepted** 03:13:57 (fit and part caches, ~3 min) as leo revision
  **`89b5bb40`** (digest `b5b0ef61`, project commit `3b0942b`).
- **Clearance at baseline:** 14 static pairs, sweep 12 pairs, mounting
  passes; the verdict block is sgt-4's line for line but the revision.
- **The bundle against sgt-4's** (`runs/sgt-4/train/gallop_sg-task.json`):
  only `reward` differs. Its first 18 terms equal sgt-4's 18; the 19th is
  `fore_lag` (cap 32). Observations, actions, reference, reference
  schedule, tracking, goal, success and model (`59bc5407…`) are the same, so
  sgt-5 reads and emits what sgt-4 does; it still trains cold (O8: a changed
  task trains cold).
- `fore_sync` (w 10 in sgt-4) stays: it is gated on the command and pays
  nothing at the 700 end where `fore_lag` matters most; the two compete only
  at the top, where the clip's fore lag is smallest.

## The launch, if the trigger is met

Trigger (sgt-4's rule, `sgt-3b-50.md`): at 120 the slow fores (700) strike
more than 1.2 a stride on either paw (seed median) or more than 0.2 of fore
touchdowns fall within 40 ms. Then, as soon as sgt-4 ends:

```
systemd-run --user --scope -p MemoryMax=30G env PYTHONPATH=cli pixi run python \
    docs/probes/orun13/queue_run.py ~/cadex-projects/leo sgt-5 11100 120 \
    "sgt-4's 18 terms + fore_lag w10, cold: slow fores still double at sgt-4-120" \
    --expect-revision 89b5bb40 --seed 1 --task gallop_sg --envs 4096
```

(sgt-4's sizing: ~83 s an iteration + 20 %.) Its keep rule is in
`fore-lag-sgt4.md`: at 120 the fores at 700 at most 1.2 strikes a stride
with at most 0.2 within 40 ms, the hinds' within-40 share no worse than
sgt-4-120's + 0.05, the heel shares per leg no worse than sgt-4-120's − 0.05
at each command.

**If sgt-4 passes instead** (warm extend to 300 on sgt-4's own bundle), the
project's head is now sgt-5's revision: `queue_run.py --expect-revision`
reads the project's accepted revision, so re-set `orun17-sgt4.py` first
(from the caches in minutes; check the revision it accepts is b09a23b5 or bundle-identical to sgt-4's) and extend with
`--init-from` sgt-4-120 `--critic-warmup` as O8 says.
