# orun15 P2: which paw fails `no_tap`

Verified against source: 2026-10-21. Frozen evidence (orun15, iteration 11).
Asked by the critic after `k8-sole.md`: `no_tap` fails 0/10 on k8-sole-50
with a touchdown-rate ratio of 1.96. Which paw steps twice, and which lever
acts on it?

## What the predicate counts

`no_tap` bounds `touchdown_rate_ratio_max` at 1.1 (ADR-774): each paw's
**landings** per settled second (`feet[..]["landings_s"]`, every return
within 1 mm of the floor after any lift) over LH's stride rate, the worst
paw. A **step** is a landing after a lift of at least 0.10 s that advanced
at least 0.15 hip heights (68 mm); a **tap** is any other landing. The
ratio is the worst paw's, so one paw fails it for all four.

`fore_tap.py` (this directory) reads each paw's taps from the traces as
the engine reads them (`CadexEvaluation.foot_series` on the paw's
collision geoms): the lift in frames, its peak height, its plan advance,
its phase in the paw's own step cycle (0 the step's landing, 1 the next),
and, on a fore paw, the shoulder, elbow and wrist drive angles at the
tap's lift against at the steps' lift.

```
E=~/cadex-projects/leo/evaluations
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun15/fore_tap.py \
    ~/cadex-projects/leo/runs/k8-sole/train/cat_model-model.xml \
    $E/k8-sole-50 $E/sf-sole-50 $E/hl-sole-50 $E/tr-sole-50
```

## The fast policies at 50 (10 seeds each)

Engine ratio median (max) and taps per step (median seed), per paw:

| evaluation | LF | RF | LH | RH | LF's tap: lift frames, peak mm, advance mm, phase |
|---|---|---|---|---|---|
| tr-sole-50 (v03, unsprung) | 1.25 (1.49), 0.22 | 1.03, 0.00 | 1.07, 0.00 | **2.08 (2.33), 0.37** | 3, 9.6, 25, 0.21 |
| sf-sole-50 (v04) | **1.91 (2.01), 0.93** | 1.21, 0.04 | 1.04, 0.02 | 1.07, 0.06 | 3, 6.6, 106, 0.24 |
| hl-sole-50 (v04, `hind_lag`) | 1.21 (1.40), 0.19 | 1.05, 0.00 | 1.07, 0.07 | 1.23, 0.00 | 3, 8.9, 80, 0.22 |
| **k8-sole-50 (v04.2)** | **1.96 (2.01), 0.77** | 1.70 (1.96), 0.21 | 1.05, 0.05 | 1.07, 0.05 | 3, 19.7, 195, 0.29 |

- **On v04 and v04.2 it is the left fore, not RH.** RH's double step was
  orun14's on the unsprung pin (tr-sole-50, ratio 2.08, `rh-mirror.md`);
  on every v04 policy RH lands once a stride (1.07, 1.23). On k8-sole-50
  LF taps on 0.77 of its steps (186 taps on 237 steps), and RF on 0.21
  (62 on 302) is the second paw over 1.1.
- **The tap is a skip inside the fore stance.** LF lands its step, lifts
  for 3 frames (60 ms) about 20 mm, moves forward 195 mm, and lands again
  at 0.29 of its own cycle, just past its stance share (duty 0.26), then
  lifts into its swing. The elbow at the tap's lift is −11° against −33°
  at the step's lift: the paw is lifted and re-placed with the leg still
  half under the body, not pushed off. RF's taps on k8-sole-50 are the
  same shape (4 frames, 23 mm, 199 mm, phase 0.24).
- **The hinds do not tap** on any fast v04 policy: LH's few taps are a
  1-frame, 1–3 mm bounce at 0.10 of its cycle; RH's 0.05 a step.
- **The fore pair's order moves it.** hl-sole-50, the one fast policy with
  its fore pair closed to a tie (fore lag 0.030 a step, `fore-lag.md`) and
  its hinds split, taps LF on 0.19 of its steps; sf-sole-50 and
  k8-sole-50, whose LF leads RF (by 120 and 20 ms at the median,
  `k8-sole.md`), on 0.93 and 0.77. Three policies show a direction, not
  a cause. The clip asks LF 62 ms ahead of RF with a fore stance of 0.19
  of the stride (80 ms, the bundle's `reference.contact`); the policies
  hold each fore down for 0.25–0.28, so the lead fore lands early, short
  of where the clip puts it, and skips forward.
- Cold policies at 25 (hl-sole-25, k8-sole-25, hlk8-sole-25) tap on all
  four paws (0.3–1.8 taps a step, 4–15 mm high): a shuffle, not this
  skip. Read `no_tap` on a fast policy.

## The lever, and the screen that asks it

- `fore_tap` (w −8) charges a fore paw down **outside** the clip's stance,
  so a skip that keeps both contacts near the window costs little; no term
  counts landings, and per O7 none should be added before a clip change is
  tried.
- **First lever: the fore pair's timing**, which fl-sole changes
  (`fore_sync` off, `fore_lag` w10, `fore-lag.md`). Its judged 25 and 50
  read LF's and RF's taps per step with `fore_tap.py` against
  hlk8-sole's at the same checkpoint, beside its keep rule.
- **Next lever: the clip's fore stance.** The clip's fore duty (0.19,
  four frames at 2.4 Hz) is shorter than any fast policy holds a fore
  down (0.25–0.28). A clip whose fore stance is as long as the policy's
  would pay the one long contact the policy already makes, in place of a
  short one the lead fore re-places to reach.
