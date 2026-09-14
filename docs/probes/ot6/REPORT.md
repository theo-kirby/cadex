# ot6 closing report — real models, reference-grade review

Verified against source: 2026-09-14. [Cadex-new]

This is D10 of the ot6 charter (ADR-328, `.ouroboros/goal.md`): one page
linking the evidence for D1–D9, saying what each measured and what remains
open. Every claim below is carried by a record node in `.hypergraph/graph/record/`
(named `[rec: slug]`), a committed receipt under this directory or
`docs/review-design/`, or an ADR in `docs/DECISIONS.md`. Full telemetry,
traces, frame sets and logs stay in the operator's `cadex-projects` directory
outside the repository; each receipt cites them by path and digest. The run
is branch `ouroboros/ot6`, from the run start commit `63874b3d` to the D9
commit `130abd29`. The owner ticks the checkboxes; the records say only that
the evidence exists.

## D1. The dashboard is one designed page

**Evidence.** The spec `docs/REVIEW-DESIGN.md` (purpose, six-region hierarchy,
one type scale of 12/14/17/22 px, dark-only palette tokens, spacing,
breakpoints, §10 one palette across chrome and viewport, §11 what the viewport
shows). Before and after screenshots at both charter widths beside it:
`docs/review-design/before-1400.png`, `before-400x850.png`, `after-1400.png`,
`after-400x850.png`, with the receipts [design/before.json](design/before.json)
and [design/after.json](design/after.json). The browser half of
`cli/tests/test_review_design.py` asserts the palette tokens by computed style,
the type sizes, zero horizontal overflow and the canvas fill at 1400×900 and
400×850. ADR-329, ADR-331, ADR-333.
[rec: ancient-field-7584] [rec: royal-road-2298] [rec: keen-water-3378] [rec: windy-rock-4850].

**Measured.** Before: at 400 px the fixed 280 px sidebar plus min-content
tables widened the layout viewport to 868 px and left a 34 px canvas. After:
layout viewport 1400 / 400 px, overflow 0 px, on the operator URL serving the
active project.

## D2. The dashboard works on a phone

**Evidence.** The phone test in `cli/tests/test_review_design.py` at 400×850
under touch emulation: one-finger orbit without page scroll, two-finger pinch,
Fit by tap, legible stacked curves, playback from the page's own Play control,
download by tap with the recorded SHA-256, on a real FFmpeg-encoded fixture.
Seven region screenshots `docs/review-design/phone-*.png` and
[design/phone.json](design/phone.json), taken by
[design/capture_page.py](design/capture_page.py) on the operator URL.
ADR-330 (pointer events, `[data-video-play]`).
[rec: royal-road-2298] [rec: plain-arrow-4971].

**Caveat.** The device is headless Chromium's touch emulation, not a phone;
its gesture recogniser drops a tap within a few hundred milliseconds of a
drag's end, which the capture script waits out.

## D3. Viewport and videos match the neural-whoop reference

**Evidence.** `cli/cadex_cli/review_static/environment.js` exports one dark
`PALETTE` and no theme setter; the light palette is deleted (ADR-331). Every
new recording carries the style `cadex-prototype-dark-v1`. The follow camera
(ADR-332): `review_scene.js` `follow(track, options)` holds the subject's
standing height at a declared **0.22** of frame height, Hann-smoothed, with a
drift limiter, and `setClock` draws the timer pill inside the WebGL frame.
[look/README.md](look/README.md) holds the written assessment (floor/grid,
horizon/fog, palette, lighting/shadows, materials, framing, camera) beside the
reference's shipped clips: [look/side-by-side.png](look/side-by-side.png),
[look/follow-side-by-side.png](look/follow-side-by-side.png), receipts
[look/look.json](look/look.json) and [look/follow.json](look/follow.json).
[rec: keen-water-3378] [rec: brave-wave-1488].

**Measured.** Viewport and capture byte-identical at the same pose and camera;
the decoded video frame within 1.10/255 mean absolute RGB of the viewport
(1.16–1.24/255 at 0, 4 and 8 s with the follow camera); the reference's own
unmodified dark modules over the same solids match in mean luminance to 0.1;
measured framing 0.2198–0.2201 against the declared 0.22; the floor outruns
the fog at close, framed and wide framings and through an orbit.

**Caveat.** The rig's smoothing and drift limiter were proven on the fixture's
synthetic walk and whip; Lark barely moved. Robin (1.8 m of travel) was the
first real travelling subject and rendered under the same rig.

## D4. The viewer shows the real model, and says so

**Evidence.** Each model manifest carries a `collision` block parsed from the
MJCF the view already retains at its own identity; the page draws proxies as
outlines only under the checkbox **show collision geometry**, off by default;
the status line ends `showing: tessellated solids[ with collision proxies …]`;
the recorder refuses proxies and writes `showing` into the video's identity
strip (ADR-333). Browser toggle test and decoded-frame check on a fixture whose
proxies differ from its solids, in `cli/tests/test_review_design.py` and
`test_video.py`. On the real biped: [finch/operator-solids.png](finch/operator-solids.png)
and [finch/operator-proxies.png](finch/operator-proxies.png),
[finch/operator.json](finch/operator.json) (ADR-334).
[rec: windy-rock-4850] [rec: sleepy-rain-9945].

**Measured.** Finch on the operator URL: 20 outlines, model pixel count
61 665 → 62 492, the pelvis outline spanning its open bay. Lark could not show
the difference (its box proxies coincide with its box parts: 47 354 → 47 383).

## D5. The biped is a buildable mechanism

**Evidence.** Finch, in the fresh external project `ot6-finch`: four catalog
MG90S from `lib.servo`, catalog horns, MR128 bearings and M2 screws, five
modelled printed parts. `docs/INVENTORY.md` and `docs/FIT.md` in the project
are generated by [finch/fit_check.py](finch/fit_check.py); the receipt is
[finch/fit.json](finch/fit.json); [finch/README.md](finch/README.md) describes
the joint module; `operator-*.png` show recognisable hardware. ADR-334; the
free-base engine unit ADR-335 removed the grounded pelvis so nothing in the
design is world geometry ([finch/free_base.json](finch/free_base.json)).
[rec: sleepy-rain-9945] [rec: loyal-canyon-4623].

**Measured.** 29 solids, 243.5 g (177.5 printed, 65.9 purchased); servo
windows 0.3 mm per side, horn slots 0.2 mm per side, bearing stubs 0.05 mm
radial; 87 fit checks passing at the ungrounded revision `bcce40a82d57…`;
only the two soles rest on `world` at t = 0.

**Caveat.** Fit is a solved-pose check; knee flexion past about 60° can bring
the sole toward the thigh cheeks.

## D6. The real biped trains, is measured and is recorded in the new look

**Evidence.** Run `finch1` on the stand task (400 steps at 50 Hz, fall below
84.0 mm, seeds 0–9): [finch/training.json](finch/training.json),
[finch/train.py](finch/train.py), [finch/evaluate.py](finch/evaluate.py),
decoded frames [finch/video-finch1-checkpoint20.png](finch/video-finch1-checkpoint20.png)
and [finch/video-finch1-final.png](finch/video-finch1-final.png), pinned by
the Finch receipt test. ADR-336. [rec: tiny-tooth-8197].

**Measured.** 240 PPO updates on 1024 environments in 2048.7 s, exit 0, host
peak 9.72 GB, GPU peak 15 695 MiB under `MemoryMax=20G` and a 3600 s timeout.
Checkpoint 20 fell on 10/10 seeds at 0.20–0.34 s; the final policy stood the
full 8 s on 10/10 and shuffled +361.1 mm mean (319–433).

**Caveats.** The shuffle is stand-task behaviour, not walking. The trainer's
running episode estimate (211/400) and the ten CLI rollouts (400/400) are
distinct measurements. The checkpoint video was rendered by hand after the
driver's old triangle cap refused it. No run record preceded `finch1`
(`preserved_records: {}`).

## D7. A two-wheeled balancing robot goes through the lifecycle

**Evidence.** Robin, in the fresh external project `ot6-robin`, designed by the
product agent from [robin/create.prompt.txt](robin/create.prompt.txt). The
lifecycle is five receipts in order: [robin/README.md](robin/README.md) (the
failed first attempt), [robin/MODEL-RECOVERY.md](robin/MODEL-RECOVERY.md)
(three provider-refused recoveries), [robin/ACCEPTED.md](robin/ACCEPTED.md)
(accepted after the reset-lift repair, ADR-337),
[robin/RESTORE.md](robin/RESTORE.md) (the restore digest failure isolated to
`part.offset` on the catalog D-shaft), [robin/BORE.md](robin/BORE.md) (the
analytic D-prism correction; three fresh-process reopens pass), and
[robin/TRAINING.md](robin/TRAINING.md) with
[robin/training.json](robin/training.json) (ADR-338). Inventory and fits in
[robin/fit.json](robin/fit.json) and [robin/bore-fit.json](robin/bore-fit.json).
[rec: wise-brook-4842] [rec: copper-haven-4303] [rec: northern-trail-4014]
[rec: salty-fox-4449] [rec: kind-reef-3852] [rec: odd-orchard-4978]
[rec: candid-delta-9314].

**Measured.** 24 solids (5 printable, 19 catalog), 139.601 g, 84/84 fit checks,
pocket gaps 0.30 mm, shaft/hub 0.05 mm per side, no design floor. Two bounded
runs at 400 steps, 50 Hz, fall below 46.2 mm, seeds 0–9: **`robin1` at the
default learning rate diverged** to non-finite reward at update 128 and is
kept on the dashboard as a failed run with its checkpoint-20 video; `robin2`
at 1e-4 completed 240 updates in 620.8 s (host 7.41 GB, GPU 15 139 MiB).
Checkpoint 20 fell 10/10 at 0.40–0.58 s; the final policy survived 8 s on
10/10 by holding an +11° lean and driving 1.8 m backward.

**Caveats.** That meets the task's bar and is not upright-and-still. The
first accepted revision `71709063d6af…` never passed its restore check and its
bytes were never recovered; the trained revision `5ad94d65e61a…` is a design
correction. The 1e-4 rate is the trainer's suggestion, not a diagnosis. The
dashboard claim in [robin/TRAINING.md](robin/TRAINING.md) is historical: the
service moved to Heron under the one-project-per-server rule, and Robin's runs
remain retrievable by pointing it back.

## D8. A single servo arm goes through the lifecycle

**Evidence.** Heron, a two-DoF MG90S arm in the fresh external project
`ot6-heron`, designed by the product agent from one prompt and corrected three
times against retained measurements (a floor plane in the design, 248.2 mm³
of servo/cheek common volume, a 0.2 mm horn/child gap): [heron/README.md](heron/README.md),
[heron/design.json](heron/design.json), [heron/fit.json](heron/fit.json),
[heron/reopen.json](heron/reopen.json), [heron/operator.json](heron/operator.json),
`operator-1400.png`, `operator-400.png` (ADR-339). Training:
[heron/TRAINING.md](heron/TRAINING.md), [heron/training.json](heron/training.json),
decoded frames `video-heron1-checkpoint20.png`, `video-heron1-final.png`,
[heron/servo-view.json](heron/servo-view.json) (ADR-340). Both pinned by the
Heron receipt tests. [rec: narrow-quill-3259] [rec: mild-hill-0753].

**Measured.** 15 components, 55/55 fit rules on 105 measured pairs plus three
section cuts, printed 86.6 g, purchased 33.0 g; five fresh-process reopens at
one digest `f9be3985bc55…` (the same script digest the training receipt
carries; the served revision differs only by playback parameter values).
`heron1`: 240 updates in 619.6 s, exit 0, host 7.08 GB, GPU 15 137 MiB.
Checkpoint 20 reached on **0/10** seeds; the final policy on **10/10** (within
10 mm by 0.1 s, ends 2.96–5.19 mm from the target, no termination). The
checkpoint render cost the live page nothing measurable (median 1.072 s during
against 1.071 s before).

**Caveats.** The hold sits about 3 mm below the target and the tip oscillates
within tolerance; observed, not diagnosed. The engine accepted a script whose
stdout contradicted its retained clearance pairs three times: a fit check must
read the published measurements, never stdout. The reach target is fixed and
per-seed variation is the two forearm pushes only.

## D9. Everything ot5 proved still holds

**Evidence.** [regression/README.md](regression/README.md) maps each ot5
behaviour the criterion names (server and record suites, polling within five
seconds, playback and download, restart during training, copy isolation,
failed-run states, headless operation) to the CLI tests that exercise it and to
retained ot6 lifecycle evidence; [regression/final.json](regression/final.json)
and [regression/final_probe.py](regression/final_probe.py) are pinned by
`test_final_regression_receipt_shows_everything_ot5_proved_still_holds`, which
holds every named test to the tree by name. The first, mid-run pass is kept
beside it as [regression/verification.json](regression/verification.json).
[rec: copper-haven-4303] [rec: bold-arbor-2078].

**Measured.** On commit `aa293fc0`: engine suite 2 114 passed / 53 skipped,
CLI suite 610 passed / 1 skipped, both exit 0; the one CLI skip (the
private-address fixture) run alone with `CADEX_REVIEW_HOST` set and passing.
Fresh visits to the persistent operator URL at 1400×900 and 400×850 (touch)
selected `heron1-final` by themselves, drew 53 620 triangles of real solids,
overflowed 0 px, polled with a longest gap of 2.003 s, played the video to
0.20 s and downloaded it with digest `4f16f9117af6…`.

**Caveat.** Restart during real training rests on the fixture test and ot5's
Lark restart (ADR-325); ot6 restarted no server during Finch's, Robin's or
Heron's runs. The 53 engine skips are the MJX-gated and shell-needing cases and
are not claimed.

## D10. This report

This page is the closing report. It claims nothing a record does not carry;
`test_closing_report_links_every_criterion_to_committed_evidence` in
`cli/tests/test_review_design.py` holds every relative link to an existing
file, every `[rec: …]` to an existing record node, and the page to the 16 KB
receipt cap. The report unit [rec: frosty-path-5235] claimed done; the
critic rejected that claim because the completion impacts were still
unreconciled, the reconcile pass [rec: sharp-cedar-0014] folded them and
claimed again, and **the critic accepted done** on that iteration (verdict
`done_accepted`: "the reconciliation resolves the previous completion blocker,
the checker passes with no unreconciled state records, and the closing report
supports D1–D10"). The verdict lives in the run's loop log, which never leaves
the machine; the record that follows `sharp-cedar-0014` in the record graph
carries it, together with the last dashboard check of the run: the
`cadex-operator-review` user unit still serving `ot6-heron` on port 8765,
accepted revision `0c8c64c92252…`, three runs listed, `heron1-final` current,
the page answering 200 — the same state D9 measured, unchanged by this page.

## What remains open

- **Reward terms on the mechanisms.** Robin is measured against survival, not
  stationary balance; Heron holds 3 mm low. Each is an open design decision in
  its project's `DECISIONS.md`, deliberately not taken in this run.
- **Fit at moving poses.** Every fit check is at the solved pose; Finch's knee
  past about 60° is the known case.
- **`part.offset` on a catalog D-shaft is not byte-reproducible** across fresh
  processes on this engine build ([robin/RESTORE.md](robin/RESTORE.md)); the op was left as is
  and Robin was corrected around it.
- **Physical devices.** Phone evidence is emulated touch; nothing here was
  printed or driven on hardware.
- **Beyond this charter.** Print-ready export, the unattended robot prompt and
  gait at scale are the next legs of the north star and were not started.
