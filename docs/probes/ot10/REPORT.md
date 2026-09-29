# ot10 — closing report: a look of Cadex's own

Verified against source: 2026-09-29. [Cadex-new]

**Result.** A5 is **not met** by its letter. The charter gives each body
plan one design-only turn and says one failing design fails the
criterion. Eighteen turns were counted in the end, and eleven missed the
bar, so A5 fails. The highest bar reached is **7 of 18** counted turns
meeting it, with at least one on every body plan. The rest of this
paragraph tells it in order. The first twelve counted turns had nine
misses, and three met the bar, one per body plan: `ot10-biped-1` scores
15 of 21, `ot10-quadruped-3` 15, and `ot10-hexapod-10` 14. hex3's
baseline scores 2. Each of those three
passes every proxy and every fit gate and carries its electronics. All
nine misses are published below with their scores. A pre-registered
confirmation round then started, one more turn per body plan (see
[`README.md`](README.md)). Its first turn, `ot10-hexapod-11`, meets the
bar at 14. Its second, `ot10-quadruped-4`, meets it at 16, the highest
total of any counted design. Its third, `ot10-biped-2`, misses at 2: a
refused publish left its half-built assembly in the live document, no
later write could publish, and the accepted revision is a servo probe.
That is a measured product defect, not a design verdict, and it is still
a counted miss. The round ends 2 of 3, adds turns, and does not undo the
nine misses, so A5 stays not met by its letter, now with ten misses. A
further biped turn was pre-registered after the defect's fix (ADR-434)
and ran on a new project: `ot10-biped-3` meets the bar at 14. It adds a
counted design and re-scores nothing, so the ten misses stand. ADR-435
then bounded the build reply the model sees, and ADR-436 to ADR-438 cut
the static fit's CPU cost. One more hexapod turn was pre-registered on
that engine: `ot10-hexapod-12` misses at 12, on its total alone, with no
CPU-limit refusal (0 of 8, against `ot10-hexapod-10`'s 6 of 15). That is
an eleventh miss. ADR-439 then sized the render grid from the drawn
parts, and ADR-440 put the joint cap over the horn. A last hexapod turn
was pre-registered on that engine: `ot10-hexapod-13` meets the bar at 15.
It adds a counted design and re-scores nothing, so the eleven misses
stand. One W2 run, `w2-2` on `ot10-quadruped-3`, has
`walked = true` under the unchanged thresholds. It went 1.44 m forward in
10 s, upright the whole time. The run before it, `w2-1`, did not walk.

**The owner's verdict on `w2-2`: it shuffles; it does not walk.** The gait
check's `walked = true` is a false positive for gait quality, and this
report does not present W2 as a walking robot. What the check can and
cannot see is under [*What the gait check cannot see*](#what-the-gait-check-cannot-see).

**Where each criterion stands.** The owner ticks the boxes, so this list
reports and does not tick. By the owner's exhaustion decision
(2026-09-29), ot10 ends after A8, and done is judged on A1–A4, A6, A8, W1,
W2 and C1.

- **A5 is the owner's to judge** from the counted and confirmation turns
  below. By the letter of its "one failing design" clause it is not met.
  It does not block done.
- **A7 is open and carried forward** (see [A7](#a7-open-carried-forward)).
  No A7 confirmation turn ran, and no design reached 17 of 21 or T4 at 3.
- **A8 landed** (ADR-444). Every presented image is drawn on the
  viewport's dark prototype floor, from one palette source.
- **W2 is an honest measured result**: `walked = true` under the unchanged
  thresholds, plus the owner's verdict that the robot shuffles.

This page summarises. The evidence is the contract and its probe log,
[`README.md`](README.md), with every raw judge reply in the `*-score.json`
files beside it. `cli/tests/test_ot10_report.py` holds this page's score
and proxy tables equal to those files and that log. It also checks that
every image linked here is committed and 300 KB or less. The owner ticks
the criteria. This report does not.

## The instrument (A1)

[`docs/DESIGN-LANGUAGE.md`](../../DESIGN-LANGUAGE.md) is the language
(ADR-411). The rubric, the proxies, the A5 bar and the blind judging
procedure are frozen in [`README.md`](README.md) and
[`contract.json`](contract.json). The rubric has seven traits, T1–T7,
each scored 0–3, with its sha256 pinned. The judge is `claude-opus-5-5` at
`high` effort, three isolated calls per candidate, and the median per
trait. The bar is a total of at least 14 of 21, no trait at 0, a total
above hex3's, P1 ≤ 0.20, P2 ≤ 0.25, P3 of 2 or 3, and the fit gates.

One frozen value changed after the freeze, as a recorded decision.
ADR-424 left world geometry out of P2, as P1 already did, and re-scored
every earlier probe. No verdict changed, and the judge never sees P2. The
rubric, the bar and the procedure never changed.

## Before and after, against hex3

| | hex3 (baseline) | best after |
|---|---|---|
| judged total | **2** of 21 | **16** (`ot10-quadruped-2`, `ot10-hexapod-5`, and `ot10-quadruped-4`, which meets the bar); **16**, **15** and **14** for the seven that meet the bar |
| T1 shell | 0 | 2 on every design except hexapod 8 and biped 2 |
| T5 face | 0 | 2 on every counted design but `ot10-biped-3`, which scores 3 |
| P1 hardware silhouette | 0.373, over its bar | 0.0001 to 0.078 over the seventeen attempts it was measured on (biped 2 published no inventory) |
| P2 sharp printed edges | 0.189 | 0.040 to 0.508 (hexapod 1 is the only one over the bar; biped 2 unmeasured) |
| P3 materials | 2 | 3 on fifteen attempts, 2 on two, 4 on biped 2 (no roles declared) |
| render | flat, orthographic | studio hero, 1024 px |

| view | before | after |
|---|---|---|
| hex3, iso | [`hex3-look_iso.png`](hex3-look_iso.png) (ADR-406, flat) | [`hex3-studio_iso.png`](hex3-studio_iso.png) (ADR-412, studio) |
| hex3, hero | none, no hero view existed | [`hex3-studio_hero.png`](hex3-studio_hero.png) |
| an A5 hexapod, hero | [`hex3-studio_hero.png`](hex3-studio_hero.png) | [`ot10-hexapod-10-hero.png`](ot10-hexapod-10-hero.png) |

## Every A5 attempt

Every attempt is the frozen prompt for its body plan, word for word. Each
was one design-only turn with `claude-opus-5-5`, `CADEX_EFFORT=medium`
and no continuation, on a new `ot10-*` project. The scores are the
medians of three blind calls. *Static* is the static fit as it ran. The
floor's own advisory row is not a failure. *Swept* is whether the swept
fit was complete and passing.

<!-- attempts:start -->
| project | status | T1 | T2 | T3 | T4 | T5 | T6 | T7 | total | P1 | P2 | P3 | static | swept | electronics | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `hex3` | baseline | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2 | 0.373 | 0.189 | 2 | — | — | — | baseline |
| `ot10-hexapod-1` | failed | 2 | 3 | 1 | 1 | 2 | 2 | 2 | 13 | 0.078 | 0.508 | 3 | yes | no | yes | misses: total, P2, swept |
| `ot10-hexapod-2` | failed | 2 | 3 | 1 | 2 | 2 | 2 | 2 | 14 | 0.022 | 0.134 | 3 | yes | no | yes | misses: swept |
| `ot10-quadruped-2` | failed | 2 | 3 | 3 | 1 | 2 | 3 | 2 | 16 | 0.004 | 0.040 | 3 | yes | no | yes | misses: swept |
| `ot10-biped-1` | counted | 2 | 3 | 3 | 1 | 2 | 2 | 2 | 15 | 0.002 | 0.103 | 3 | yes | yes | yes | **meets the bar** |
| `ot10-hexapod-3` | failed | 2 | 3 | 2 | 1 | 1 | 2 | 2 | 13 | 0.007 | 0.048 | 3 | yes | yes | yes | misses: total |
| `ot10-hexapod-4` | failed | 2 | 2 | 1 | 1 | 2 | 2 | 2 | 12 | 0.013 | 0.220 | 2 | yes | yes | yes | misses: total |
| `ot10-quadruped-3` | counted | 2 | 3 | 2 | 2 | 2 | 2 | 2 | 15 | 0.0001 | 0.116 | 3 | yes | yes | yes | **meets the bar** |
| `ot10-hexapod-5` | failed | 2 | 3 | 3 | 2 | 2 | 2 | 2 | 16 | 0.013 | 0.168 | 3 | yes | no | yes | misses: swept |
| `ot10-hexapod-6` | failed | 2 | 3 | 2 | 2 | 2 | 2 | 2 | 15 | 0.009 | 0.198 | 3 | no | no | yes | misses: static, swept |
| `ot10-hexapod-7` | failed | 2 | 3 | 1 | 1 | 2 | 2 | 2 | 13 | 0.033 | 0.247 | 3 | yes | yes | yes | misses: total |
| `ot10-hexapod-8` | failed | 1 | 1 | 2 | 1 | 0 | 1 | 2 | 8 | 0.020 | 0.097 | 2 | yes | no | no | misses: total, T5, swept, electronics |
| `ot10-hexapod-10` | counted | 2 | 2 | 1 | 2 | 2 | 3 | 2 | 14 | 0.0026 | 0.1415 | 3 | yes | yes | yes | **meets the bar** |
| `ot10-hexapod-11` | counted | 2 | 3 | 1 | 2 | 2 | 2 | 2 | 14 | 0.0186 | 0.2285 | 3 | yes | yes | yes | **meets the bar** |
| `ot10-quadruped-4` | counted | 2 | 3 | 3 | 1 | 2 | 3 | 2 | 16 | 0.0022 | 0.1624 | 3 | yes | yes | yes | **meets the bar** |
| `ot10-biped-2` | failed | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2 | unmeasured | unmeasured | 4 | no | no | no | misses: total, T1, T3, T4, T5, T6, P1, P2, P3, static, swept, electronics |
| `ot10-biped-3` | counted | 2 | 2 | 2 | 1 | 3 | 2 | 2 | 14 | 0.0035 | 0.2214 | 3 | yes | yes | yes | **meets the bar** |
| `ot10-hexapod-12` | failed | 2 | 2 | 1 | 1 | 2 | 2 | 2 | 12 | 0.0038 | 0.1844 | 3 | yes | yes | yes | misses: total |
| `ot10-hexapod-13` | counted | 2 | 3 | 2 | 2 | 2 | 2 | 2 | 15 | 0.0031 | 0.214 | 3 | yes | yes | yes | **meets the bar** |
<!-- attempts:end -->

Two turns started and are not attempts: `ot10-quadruped-1` and
`ot10-hexapod-9`. Each was killed when the loop session that launched it
ended, before it wrote an accepted revision. Each is kept read-only as the
receipt, and neither is scored.

**What the failures measured, and what each one changed.**

- **Incomplete sweeps**: hexapods 1, 2, 5 and 6, and quadruped 2. These
  were engine limits, not design choices. At first no sweep step was
  declared. Then the sweep hit the CPU cap and the pair budget. ADR-418,
  ADR-419, ADR-420, ADR-423, ADR-425 and ADR-426 bounded the far pairs,
  made world-geometry contacts advisory, and counted only the pairs a
  joint moves.
- **Feet resting on the floor failed the static fit**: hexapod 6. ADR-427
  now reports a world-geometry contact rather than failing it. The
  verdict still counts the turn as it ran.
- **Totals under 14**: hexapods 1, 3, 4 and 7. The judges read servo
  cradles as exposed servos, legs of constant section, and uneven joint
  treatments (T3 and T4). ADR-422 and ADR-428 answered this in the
  language's terms, never in the judge's words.
- **An unfinished design**: hexapod 8. Its full builds ran past the CPU
  limit. After the agent renamed its assembly output, the live document
  wedged, and no later write could publish. The accepted revision is the
  agent's leg probe, with no electronics. ADR-429 fixed the wedge with a
  regression test before the next attempt.
- **A second wedge, on the general path**: biped 2. A publish refused
  after the assembly pass had started (`No native publisher exists for
  output type 'actuator'`) left 43 objects in the live document, and
  every later write was refused. The daemon's document runs with
  `UndoMode 0`, so `abortTransaction` restores nothing. ADR-429 recorded
  that as a known gap. It is the next unit, with a regression test,
  before any prompt or tool change.

**A5 is not met, and what the clause means.** The charter gives each
body plan one design-only turn and says "one failing design fails this
criterion". Read plainly, the clause is about every counted attempt, not
the best one per body plan. Eighteen turns were counted on the frozen
prompts, and eleven of them missed the bar: hexapods 1 to 8, quadruped 2,
biped 2 and hexapod 12. Any one of those eleven fails A5 on its own, and a later turn that
meets the bar does not reverse it. Nothing in this report re-scores a
miss, retires one, or counts only the latest turn per body plan.

What the run did reach, stated as the highest bar and not as success:

- **Every body plan has at least one design that meets the bar.** Seven
  do: `ot10-biped-1` (15), `ot10-quadruped-3` (15), `ot10-hexapod-10`
  (14), `ot10-hexapod-11` (14), `ot10-quadruped-4` (16),
  `ot10-biped-3` (14) and `ot10-hexapod-13` (15). Each scores above hex3's 2, passes every proxy and
  both fit gates, and carries its electronics.
- **The pre-registered confirmation round was 2 of 3.** Its turns were
  `ot10-hexapod-11` (meets), `ot10-quadruped-4` (meets) and
  `ot10-biped-2` (misses at 2 on the publication defect). `ot10-biped-3`
  is not part of that round. It was pre-registered separately after
  ADR-434 fixed the defect, and ran on the fixed engine. `ot10-hexapod-12` then missed and `ot10-hexapod-13` met the
  bar, so the latest turn on each body plan meets it. The round as
  registered did not.
- **The last tool changes have one counted turn behind them.** ADR-434 (a
  refused publish rolls back) landed before `ot10-biped-3`. ADR-435 (a
  build reply the model sees is bounded) and ADR-436 to ADR-438 (the
  static fit's CPU cost) landed after it. `ot10-hexapod-12` is the one
  turn run on them. It had no CPU-limit refusal and misses on its total.
  ADR-439 (the render grid) and ADR-440 (the joint cap over the horn)
  came next, and `ot10-hexapod-13` is the one turn run on them. It meets
  the bar at 15, with T3 at 2 against hexapod-12's 1. One turn is not a
  rate, so this report claims no effect beyond those turns.

## The renders, sheets and videos

| what | criterion | files |
|---|---|---|
| hero and five `look` views for each attempt | A2, A5 | `ot10-<project>-hero.png`, `ot10-<project>-look_<view>.png`, one set per row above |
| hex3 in the studio renderer | A2 | [`hex3-studio_hero.png`](hex3-studio_hero.png), [`hex3-studio_iso.png`](hex3-studio_iso.png) |
| concept sheets of the seven designs that meet the bar | A6 | [`ot10-biped-1-sheet.png`](ot10-biped-1-sheet.png), [`ot10-quadruped-3-sheet.png`](ot10-quadruped-3-sheet.png), [`ot10-hexapod-10-sheet.png`](ot10-hexapod-10-sheet.png), [`ot10-hexapod-11-sheet.png`](ot10-hexapod-11-sheet.png), [`ot10-quadruped-4-sheet.png`](ot10-quadruped-4-sheet.png), [`ot10-biped-3-sheet.png`](ot10-biped-3-sheet.png), [`ot10-hexapod-13-sheet.png`](ot10-hexapod-13-sheet.png) |
| concept sheets of the two later misses | A6 | [`ot10-biped-2-sheet.png`](ot10-biped-2-sheet.png), [`ot10-hexapod-12-sheet.png`](ot10-hexapod-12-sheet.png) |
| `ot10-hexapod-12` hero after the render-grid fix | A2 | [`ot10-hexapod-12-hero-grid-after.png`](ot10-hexapod-12-hero-grid-after.png) (ADR-439; the counted score stands) |
| Finch rollout, before and after the studio look | W1 | [`w1-finch-rollout-scene.png`](w1-finch-rollout-scene.png), [`w1-finch-rollout-studio.png`](w1-finch-rollout-studio.png) |
| `w2-1` rollout, floor fixed | W1 | [`w1-quadruped-rollout-reach-floor.png`](w1-quadruped-rollout-reach-floor.png), [`w1-quadruped-rollout-studio.png`](w1-quadruped-rollout-studio.png) |
| `w2-2` rollout | W1, W2 | [`w2-2-quadruped-rollout-studio.png`](w2-2-quadruped-rollout-studio.png) |
| `ot10-quadruped-3` hero and sheet, before and after the dark prototype floor | A8 | before: [`ot10-quadruped-3-hero.png`](ot10-quadruped-3-hero.png), [`ot10-quadruped-3-sheet.png`](ot10-quadruped-3-sheet.png); after: [`a8-quadruped-3-hero-dark.png`](a8-quadruped-3-hero-dark.png), [`a8-quadruped-3-sheet-dark.png`](a8-quadruped-3-sheet-dark.png) (ADR-444) |
| `w2-2` rollout on the dark prototype floor | A8, W1 | before: [`w2-2-quadruped-rollout-studio.png`](w2-2-quadruped-rollout-studio.png); after: [`a8-w2-2-rollout-dark.png`](a8-w2-2-rollout-dark.png) (ADR-444) |

**A2's time bound.** For hex3's accepted design, the four 512 px views
and the 1024 px hero took 6.5 s, the hero alone 2.2 s. That is against a
60 s bar, on the CPU, headless. Acquiring the tessellation took 207 s
more. That is the engine's rebuild, which the charter reports separately.
Drawing each A5 design's sheet took 1.1–1.9 s, and its render 7.0–9.3 s.

**W1's bound.** Rollout videos render headless under a stated 300 s bound:
Finch in 117.5 s, `w2-1` in 72.8 s and `w2-2` in 153.9 s. Each webm stays
in its project copy's `runs/`, never in git. The dashboard's Chromium
playback check ran on `w2-1`'s video. It was not repeated for `w2-2`'s.
The dark-floor re-render of `w2-2` (ADR-444) took 189.0 s for 101 frames
against the same 300 s bound. It was rendered on a scratch copy. The
dashboard's Chromium playback check was then run on that copy's webm
(`3fb52b44…`): it loaded at 512×512 with a 10.1 s duration, played past
1.1 s, kept playing across three polls, and downloaded as the same file,
byte for byte (438,625 bytes, SHA-256 matched). A decoded frame's corners
read `#161616`–`#181818`, which is the `#141414` scene after VP9.

## The training runs (W2)

Both runs were on `ot10-quadruped-3-w2`, a copy at the accepted revision.
The original project stays read-only. Settings and stop rules were
committed before each run started. Each run was 1,000 iterations × 2,048
envs with `--stop-on-collapse`, on the ADR-410 task the agent declared,
with the gait thresholds unchanged.

| run | start | train s | best reward/step | rollout | survival, ADR-433 | verdict |
|---|---|---|---|---|---|---|
| `w2-1` | cold | 1,944.8 | 2.654 | tipped at 4.36 s; 19 mm forward | 0.975 | `walked = false` |
| `w2-2` | warm, from `w2-1` on a byte-identical task bundle | 1,866.3 | 2.697 | 501 frames upright, max tilt 15.9°; 1,443.8 mm forward | 1.00 | **`walked = true`** |

`w2-2` first reviewed as `walked = false`. Its only failing finding was
training survival. That finding read the trainer's last iteration, which
always closes on a horizon boundary and counts time-limit truncations as
endings. ADR-433 reads a trailing-window median instead, capped at the
horizon, with the 0.90 bar unchanged. Both runs were re-reviewed from
their stored inputs. The training curves are in [`README.md`](README.md)
under *W2*.

**The owner's verdict: `w2-2` shuffles; it does not walk.** The owner
reviewed the run and found that it shuffles. `walked = true` is therefore
a false positive for gait quality, and W2 stands as a measured result, not
as a walking robot. The gait thresholds were not weakened to pass it, and
no new training ran to fix it. The owner has made the policy design and
evaluation loop the next charter. The probe log's line for `w2-2`, "the
feet step rather than slide", is withdrawn by this verdict. It rested on
the foot solid's centre crossing a 3 mm lift line: 48 and 52 times for the
front feet and 100 and 124 times for the rear, in 10 s. Those counts are
what a foot that chatters or drags in small hops also produces. No contact
was read, so no stance was measured.

### What the gait check cannot see

`gait_from_trace` (`cli/cadex_cli/walk.py`, ADR-409, ADR-433) reads one
thing from the rollout: the placement of the free-floating base body in
each solved frame. Its verdict is `walked = not findings`, and there are
four findings:

- the base tipped past 45°;
- its heading swung past 90°;
- the episode terminated early;
- training episodes lasted under 0.90 of the horizon over a trailing
  window.

Travel and speed are reported but never judged. A robot that stood still,
upright and facing forward, for the whole episode would pass. Nothing in
the check reads a leg, a foot or a contact, so it cannot see any of these:

- **Stepping.** It cannot tell whether each foot leaves the ground, lands
  and bears weight in turn. A body carried forward by feet that never lift
  looks the same as one carried by a stride.
- **Foot clearance.** It cannot tell how high a swinging foot rises above
  the floor, or whether it rises at all. A lift threshold on the foot
  solid's centre, as used in the probe log, counts chatter as steps.
- **Slip.** It cannot tell whether a foot in stance stays put on the floor
  or slides along it. Forward travel made by sliding feet reads as
  progress.
- **Duty factor.** It cannot see the share of each cycle a foot spends on
  the ground, or the phase between feet. Those are what separate a walk, a
  trot and a shuffle, and give a gait its regular, repeated shape.

Each needs per-foot contact from the rollout. MuJoCo computes it, but the
trace does not carry it. The trace does carry each component's placement,
so a foot's position is already there. Measuring these four is
the next charter's work, together with the policy loop they would judge.
This run does not add them.

## A4: refusals

None of the four hex refusal classes recurred: 0 of 231 refused calls,
across all 20 ot10 transcripts. The count is mechanical, and
[`refusals.json`](refusals.json) pins it.

## A7: open, carried forward

The owner added A7 mid-run and then deferred it. The owner's exhaustion
decision (2026-09-29) ends the run after A8, and A7 does not block done.
Its bar is 17 or more of 21 and T4 (form) at 3, on the latest
pre-registered confirmation turn for each body plan. It is open, and it
carries forward to the next charter.

- **No A7 confirmation turn was pre-registered or run.** The last product
  turns (`ot10-hexapod-12` and `ot10-hexapod-13`) were registered for A5.
- **The measured distance to the bar.** The highest judged total is 16:
  `ot10-quadruped-2`, `ot10-hexapod-5` and `ot10-quadruped-4`. No design
  scores 3 on T4, and the best reached is 2. ADR-443 records the gap the
  judges named on all three 16/21 designs: a rounded box on legs, with
  servo cases hanging outside the shell.
- **Product changes aimed at that gap, with no judged turn behind them:**
  - the joint cap over the horn, sized from the horn (ADR-440);
  - housed parts carry their own bay (ADR-442);
  - a servo carries its own bay, and the overlay tells a limb to wrap it
    (ADR-443).

  Read-only on the 16/21 designs, printed material fills 0.198 and 0.390
  of a 2 mm wall around the quadrupeds' hip servos. Every knee, and
  `ot10-hexapod-5`'s hips, measure 0.714–0.848. No turn has used `.bay()` yet, so no score shows its effect.
- **A dark-floor judged probe needs a decision first.** Since ADR-444, a
  judged probe would see dark renders, and A1's frozen procedure was
  scored on light ones. Running one is a recorded decision that re-scores
  every earlier probe, hex3 included.

## A8: the dark prototype floor

`cli/cadex_cli/scene.py` is the one palette source (ADR-444). It reads
the scene background `#141414` and the mat's `#1c1c1c` / `#232323` tiles
and `#3a3a3a` major line from the viewport's own `environment.js`, and the
chrome's tokens from `review.css`. The studio hero, `look`, the concept
sheet and the rollout video all draw from it, and the light backdrop is
deleted. `cli/tests/test_scene_palette.py` fails if the renderer and the
viewport drift apart.

- **Measured on `ot10-quadruped-3`.** The four views and the 1024 px hero
  took 15.2 s, inside A2's 60 s. The proxies were unchanged. The contact
  shadow takes the floor at the feet from tiles of 28–35 down to 6 of 255.
- **The `w2-2` video** re-rendered in 189.0 s, against its 300 s bound.
- **Before and after images** are in the renders table above, all 300 KB
  or less.
- **Nothing was re-scored.** This is a presentation change. The frozen
  rubric's anchor still says "seamless backdrop" and was not edited.
- **The dashboard plays the dark video.** Chromium loaded, played and
  downloaded it byte for byte, as in W1's bound above.

## Remaining defects

Each of these is measured. Only the first has had engine changes since
the report was written, and none is closed.

1. **The worker's CPU limit is the largest cost left.** It accounts for
   44 of the 231 refusals, with 6 of them in `ot10-hexapod-10`. ADR-428
   showed that the sweep is not what spends the CPU. ADR-436 re-ran
   hexapod-10's first refused build. Geometry took 119 CPU-s, and the static
   fit spent the rest: `common` on two lofted shells 2.4 mm apart ran past
   137 CPU-s. The fit now skips `common` on a pair measured apart, and a
   CPU refusal names its stage and costliest stages. ADR-437 then made the
   static fit search a housing's faces best first against the part's box.
   On that build's shapes the static fit fell from 1,143 to 702 CPU-s
   (tub/pca9685 from 157 to 1.3), and on the accepted build from 120 to
   112. No row changed. ADR-438 then ran a touching pair's `common` on
   the solids cut to where they can meet, and kept only a zero from the
   cut. On the same shapes that took the static fit from 702 to 600 CPU-s
   (tub/visor 103 to 33). The accepted build went from 112 to 117–121,
   and no row changed. The build is still over the limit: it is refused
   at 292 CPU-s in dome/pca9685, with geometry (`output tub` 73) and
   deck/dome 25 the costliest stages. Two A5 turns have run since:
   `ot10-hexapod-12` had 0 CPU-limit refusals out of 8 and
   `ot10-hexapod-13` 0 out of 10, against hexapod-10's 6 of 15. Each is
   one turn with a different design, so this is not a measured rate.
2. **Sandbox refusals**: 41. The agent reaches for `dir`, `getattr`,
   `hasattr`, `type`, undefined names, imports and private attributes, and each refusal costs a
   turn.
3. **Guessed JSON pointers**: 31 refusals where the agent guessed a
   pointer into a result.
4. **`w2-1` did not walk.** It stood, drifted sideways and tipped at
   4.36 s. Its task pays about twice as much for surviving as for
   progress. `w2-2` needed a second 1,000 iterations to find the gait. The
   reward stays the agent's, and changing it is a new design turn.
5. **The rollout seed is `null`** in the script and the trace, for both
   runs. The review records it as it found it.
6. **The weakest traits are joints and form** (T3, T4). Both counted
   hexapods score 1 on T3, and so does `ot10-hexapod-12`, whose judges
   read its splined horns as bare in all three calls. Its caps sat on the
   servo's far face and beside the hub, not over the horn. The overlay now
   says where the cap goes and sizes it from the horn's
   `.spec["arm_reach_mm"]` (ADR-440). One turn has run on it:
   `ot10-hexapod-13` puts 17.6 mm caps over its horns and scores 2 on T3
   in all three calls. Its judges still read the dark hip caps and the
   cream knee discs as two styles. Both counted bipeds and `ot10-quadruped-4` score 1 on T4:
   the quadruped's legs are constant-thickness plates on a filleted box, even
   though it is the first counted design to score 3 on T3. No design scores
   3 on T1, so every design still shows some hardware.
7. **The long-term ladder has started.** The `hip_pitch` gap is closed
   (ADR-441). hex2's refusal at 48 mm, inside the parameter's own range,
   was the MJCF export check reading 7.1e-18 m of round-off, which the
   writer zeroes, as a drift of 1.0. Electronics bays now have a product
   surface (ADR-442): `lib.battery(...)` and `lib.board(...)` carry
   `.bay()`, the part's extents plus clearance and lead room, and the
   overlay says to cut it. Measured read-only on `ot10-quadruped-4`, all
   five housed parts pass the fit checks, and every one of their bays is
   intruded: the battery pocket leaves 0.4 mm where the bay asks 1 mm
   (2,884 mm³ of chassis inside the bay without lead room), and the four
   boards sit straight on the deck with no room under them for their solder
   joints (2,044–5,059 mm³ each). The servo now has one too (ADR-443), and
   the overlay tells a limb to wrap it. Read-only on the three 16/21
   designs, printed material fills 0.198 of a 2 mm wall around each hip
   servo on `ot10-quadruped-2` and 0.390 on `ot10-quadruped-4`, against
   0.714–0.848 on every knee and on `ot10-hexapod-5`'s hips: the quadrupeds'
   hip cases hang beside the body. No A5 turn has used `.bay()` yet. Still
   open: a Cadex signature that holds across body plans, and stalls.
8. **The floor set the robot's render resolution (fixed, ADR-439).**
   `cadex render` sized its vertex-clustering grid from the extent of
   every loaded part, the world floor included, and dropped the floor from
   the drawing only afterwards. `ot10-hexapod-12` declared a 3,000 mm floor plane, so its
   robot drew on a 1.46 mm grid as 52,303 of 970,004 triangles. The other
   hexapods drew on 0.39–0.59 mm grids. All three judge calls named
   faceted or lumpy legs, and T4 was 1 in two of them. The score stands
   as taken. The grid is now sized from the drawn parts: the same
   revision draws on a 0.271 mm cell as 352,317 triangles, in 14.5 s
   ([before](ot10-hexapod-12-hero.png),
   [after](ot10-hexapod-12-hero-grid-after.png)). Every earlier decimated
   render, hex3's baseline included, had a floor wider than its robot and
   would now draw finer; that is a finding, and nothing is re-scored.
9. **A fillet can crash the worker without naming itself.** Three
   `edit_script` calls in `ot10-hexapod-11` ended in
   `DOMAIN_WORKER_NO_RESULT`. The agent traced them to OCCT's fillet kernel
   on small fillets over every edge after the boolean cuts, and got past
   them by filleting first. The refusal said only that the worker exited.
10. **A refused publish can leak into the live document.** The daemon's
   document runs with `UndoMode 0`, so a publish that raises after it has
   created objects leaves them behind while the refusal reports
   `accepted_live_state_preserved: true`. It ended `ot10-biped-2`. The
   validator also accepts an output type no publisher can write, which is
   what raised mid-publish there. *Fixed after the round, by ADR-434:* the
   project publish now rolls back, and an argument value in `result` is
   refused at validation with the fix named. `ot10-biped-2`'s score stands,
   because it was taken on the source it ran against.
11. **A build reply could overflow the model's tool limit.** On
    `ot10-biped-3` (215 outputs) a `rebuild` reply measured 85,954
    characters, over the 21,500 budget of ADR-359, so its agent read the
    fit by paging `inspect scope=clearance`. *Fixed after the last counted
    turn, by ADR-435:* the reply the model sees summarises outputs and
    lists fit results worst first, 12,163 characters on the same
    revision. It amends ADR-346: failing pairs are counted whole and
    listed worst first, twelve at a time. The engine reply is unchanged.
    No counted turn ran on it.

## Regressions (C1)

These were run at `31de992c`, the head before this report, on
2026-09-28:

| suite | result |
|---|---|
| `pixi run test-engine` | 2,242 passed, **53 skipped**, 0 failed (399 s) |
| `pixi run python -m pytest cli/tests` | 1,055 passed, **1 skipped**, 0 failed (788 s) |
| packaged lifecycle gate, `CADEX_ENGINE_ROOT=<staged payload>` | 23 passed, 0 skipped |

The skips are skips, not passes. Both suites were re-run with `-rs` at
`3879f1e2`, the head after this report: engine 2,242 passed and 53
skipped (301 s), CLI 1,061 passed and 1 skipped (737 s; the six extra
passes are this report's own test). Every skip has one of four causes,
and none of them is a failure hidden as a skip:

| suite | skips | reason |
|---|---|---|
| engine | 47 | JAX and MJX are absent from the engine environment by design (ADR-084). They are the offboard trainer's dependencies, so these run from a venv built from `training/requirements.txt`. The files are `test_dynamics_action_filter.py`, `test_dynamics_command_slew.py`, `test_dynamics_mjx_agreement.py`, `test_dynamics_mjx_geom_pairs.py`, `test_dynamics_policy_live.py`, `test_dynamics_policy_measured.py` and `test_dynamics_policy_trainer.py`. |
| engine | 5 | `test_blender_recipe.py` needs `CADEX_BLENDER_EXECUTABLE` to run the real OS-sandboxed recipe worker (ADR-185). No Blender runtime is set on this headless run. |
| engine | 1 | `test_licensing_compliance.py` has one packaged-gate test that needs `CADEX_ENGINE_ROOT`. It is covered by the packaged gate row above. |
| CLI | 1 | `test_review_server.py` has one test that needs `CADEX_REVIEW_HOST` set to a private-network address. It is skipped so that no hostname is committed. |

The final re-run was at `18eb0a70`, the head before this page's A5
verdict. The edit changed only prose in this report: engine 2,242 passed
and 53 skipped (397 s), CLI 1,061 passed and 1 skipped (785 s), with the
same skip reasons as above. `test_ot10_report.py` and
`test_ot10_contract.py` pass on the edited page (41 of 41). No engine or
payload file changed, so the packaged gate was not re-run.

**Final run, at `c758db3a` with this page's closing edit on top**
(2026-09-28). This comes after ADR-434, an engine change, and ADR-435, a
CLI-only change:

| suite | result |
|---|---|
| `pixi run test-engine` | 2,247 passed, **53 skipped**, 0 failed (395 s) |
| `pixi run python -m pytest cli/tests` | 1,068 passed, **1 skipped**, 0 failed (782 s) |
| packaged lifecycle gate, `CADEX_ENGINE_ROOT=<staged payload>` | 23 passed, 0 skipped |

The skips have the same four causes as the table above. No engine or
package file changed after ADR-434's commit, whose own record carries a
packaged gate run (23 passed). The gate was run again here all
the same.

`hypergraph check` must be given the project config:
`hypergraph check --record .hypergraph/cache/record.json --state
.hypergraph/cache/state.json --config .hypergraph/config.yml`. That run
reports 0 violations. Without `--config`, the checker does not know about
the `plan` view (`.hypergraph/config.yml`, `views.plan`), so it reports
270 I2 violations. Those are the plan-view impacts in the record graph
since the view was added. That count is an artifact of how the checker
was invoked, not a defect in the graph. The checker's hint to run
`hypergraph views add plan` would be wrong here, because the view
already exists.

The staged payload matched the engine
source file for file on all 57 files, so it was not rebuilt. This report's
own test, `cli/tests/test_ot10_report.py`, was added after those runs. It
passes (6 of 6), and so does `test_ot10_contract.py` beside it (35 of
35).

**Closing run, at `f2b97e01` with this page's closing edit on top**
(2026-09-29). It comes after ADR-436 to ADR-440, the last changes of the
run. The engine suite and the CLI suite ran on the source at that head.
The staged payload matched the engine source file for file on all 57
files, so it was not rebuilt, and the gate ran against it:

| suite | result |
|---|---|
| `pixi run test-engine` | 2,263 passed, **53 skipped**, 0 failed (307 s) |
| `pixi run python -m pytest cli/tests` | 1,075 passed, **1 skipped**, 0 failed (736 s) |
| packaged lifecycle gate, `CADEX_ENGINE_ROOT=<staged payload>` | 23 passed, 0 skipped |

The skip counts are the same as above, and so are their causes. This
report claims done for review with A5 **not met**: 7 of 18 counted turns
meet the bar and 11 miss. It ticks no box.

**Reconcile before done (2026-09-29, history: both records named here
have since been folded).** C1 says to reconcile, then claim
done. At this revision `hypergraph check` exits 0 with 0 violations and
0 warnings. Two records are still unfolded: `morning-tooth-4242` (hexapod
13) and `rich-path-1948` (the closing run above). Their impacts are pending
on `loyal-fountain-8709` and `southern-prairie-3683`. When they are folded,
`loyal-fountain-8709` must read 18 counted turns: 7 meet the bar and 11
miss. A work iteration is not allowed to fold them, so a housekeeping pass
has to do it. Until then, the done claim stands for review on the
evidence above, with A5 **not met**. No further A5 turn will run, because
none can change a criterion that has already failed.

**Final run after A8, at `fc279bfe` with this page's closing edit on top**
(2026-09-29). This is the run's last revision. It comes after ADR-441 to
ADR-443, which changed the engine, and ADR-444, which changed only `cli/`.
The staged payload matched the engine source file for file on all 57
files, so it was not rebuilt, and the gate ran against it:

| suite | result |
|---|---|
| `pixi run test-engine` | 2,282 passed, **53 skipped**, 0 failed (425 s) |
| `pixi run python -m pytest cli/tests` | 1,085 passed, **1 skipped**, 0 failed (885 s) |
| packaged lifecycle gate, `CADEX_ENGINE_ROOT=<staged payload>` | 23 passed, 0 skipped |

The skips have the same four causes as the first table. This page's own
tests, `test_ot10_report.py` and `test_ot10_contract.py`, pass on the
edited page (48 of 48). The run claims done for critic review on A1–A4,
A6, A8, W1, W2 and C1, as the owner's exhaustion decision directs. A5 is
the owner's to judge. A7 is open and carried forward. W2 is a measured
result with the owner's verdict that `w2-2` shuffles. No box is ticked.
The last reconcile must fold `keen-comet-6140` (A8), `glad-oak-4897`
(this report) and the record of the dark-video playback check. A work
iteration may not do that, so it falls to the reconcile pass; done is
re-claimed once `STATE.md` shows them folded and `hypergraph check`
exits 0.
