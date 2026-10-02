---
node_id: e1f470c9-9853-5170-8684-f583a367a82e
slug: mild-horizon-5182
title: 'ot11 P2: cadex evaluate films its seeds on the dark floor and the dashboard shows the report; both negatives filmed on the judged seeds (ADR-459)'
created_at: '2026-09-30T12:04:07+00:00'
parents:
- glad-fjord-0764
summary: ''
---
## What

`cadex evaluate` now films what it measured, and the review dashboard shows the evaluation report (ADR-459). This is the rest of P2.

- **The film.** New module `cli/cadex_cli/film.py`. For each filmed seed it draws two PNG sheets of twelve 256 px frames (1036×776) from the seed's kept trace, on the dark prototype floor (ADR-444), with the engine's studio renderer on the CPU:
  - an *overview*, evenly spaced over the episode, in the hero view, in one window on the whole path;
  - a *detail*, consecutive moments a step apart, side-on to the direction the design travelled, the window following it.
  - Every frame carries its simulation time and nothing else. The first filmed seed also gets the studio video (`.webm`, 10 fps).
- **The command.** `cadex evaluate` gained `--film SEEDS` (`auto`, `all`, `none`, or seed numbers), `--no-video`, `--detail-start`, `--detail-step` and `--film-only`. The report gains a `film` block (`cadex-evaluation-film-v1`).
- **The dashboard.** A fifth stage tab, *Evaluation*: the verdict line, each predicate's tally and spread, each seed's verdict, ending and per-predicate values, the behaviour metrics, the reward by term, and the film. Three new routes: the summary list in `/api/project`, `/api/evaluation/<name>`, and `/evaluation/<name>/<file>`.
- **The two known negatives were filmed** from the traces ADR-458 left, with `--film-only` and no new rollout, on the contract's judged seeds 1101, 1105 and 1110. Seed 1101's two sheets of each are committed under `docs/probes/ot11/`.
- **Docs.** `docs/CLI.md` (the film, the flags, the routes), `docs/REVIEW-DESIGN.md` §17 and the hierarchy table, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md` ADR-459, and the measured section of `docs/probes/ot11/README.md`.

## Why

Target: frontier node `damp-flame-5523` (P2), with `rough-shore-6557` (P1) for the filmed negatives. The critic's message named this unit: the video, the filmstrip and the dashboard view, whole, with tests.

**One thing the critic asked for was not done: the reconcile.** The message said "Then reconcile, because that record makes three unreconciled." A work iteration is forbidden from reconciling, so I recorded and stopped. The tail is three records after this one (`misty-timber-4175`, `glad-fjord-0764`, this one); a reconcile is due.

Everything else in the message was done as asked: only the `064d8d7cd34c-7a4e8c233214` and `3a42fdec8b94-ef71f370a2f1` directories were filmed; the committed PNGs are each under 300 KB; no video and no trace is committed; `docs/REVIEW-DESIGN.md` moved with the page.

## Method

- **Reused the studio video's drawing.** `video._studio_frames` and the encode-and-decode-back step were split out of `video._render` so the evaluation's video is drawn by the same code a run's is. `_studio_frames` now takes the materials and an optional floor height as arguments; a run's video draws what it drew before (`test_video.py` passes unchanged apart from the encoder-missing case below).
- **The solids come from the accepted attempt's own tessellation**, read through `CadexStudio.snapshot` (the reader `cadex render` uses). An evaluation has no rollout leg's STLs. I checked the frame convention by drawing: a trace pose applied to the source solid's tessellation gives an assembled robot.
- **Materials without a rebuild.** `inspect scope=inventory` answers with no restore in 0.1 s and carries each component's declared role. `evaluate` still never restores, rebuilds or accepts.
- **Nothing names a behaviour.** The detail starts at the seed's first drawn disturbance, or the middle of an episode with none, 0.2 s apart. The contract's walk window (5.0 s, 0.04 s) is two flags. `test_film.py` refuses the behaviour words in the module.
- **Frame size was chosen by measurement.** 320 px, then 288, then 256. At 288 the w2 seed-1101 detail sheet was 304,531 bytes, over the 300 KB cap.
- **Three defects found by running it for real, each fixed with a test:**
  - `./cadex` runs the pixi environment's Python without the environment on `PATH`, so the first real run drew 150 s of frames and then could not find FFmpeg. `video.ffmpeg()` now also looks beside the interpreter, and the film checks before drawing the video.
  - A failed video threw away the sheets. The sheets are now drawn first and kept; the block says `failed` with the reason.
  - The project's own repository committed the video (its `.gitignore` ignores `*.png`, not `*.webm`). The evaluation directory now gets a `.gitignore` naming the three film patterns. I untracked the film files already committed in the two `ot11-*` negative copies.
- **Dashboard tests use the real failing fixture**: ot10's `w2-2` shuffle, from the committed receipt. A passing fixture is written in the test. The page half runs in headless Chromium at 1400×900 and 400×850.
- Looked at the rendered sheets and at desk and phone screenshots of the tab before committing.

## Result

True now:

- **P2's listed parts all exist.** One command evaluates the accepted policy on its frozen seeds and writes a report with per-seed and per-predicate verdicts, the reward by term, termination causes, behaviour metrics, and the video and a filmstrip on the dark floor. The dashboard shows the report. Tests pin it on passing and failing fixtures, with the w2-2 shuffle as a failing one. **I believe P2's criteria are met; the owner and critic decide.**
- **Both negatives are filmed**, state `ready`, in the design's own materials, floor at the model's collision plane:

| | `w2-2` (`ot11-w2-negative`) | Robin (`ot11-robin-negative`) |
|---|---|---|
| sheets, three seeds | 63.8 s | 54.1 s |
| video, seed 1101 | 101 frames, 179.4 s, 386 KB | 92 frames (fell at 9.08 s), 154.8 s, 231 KB |
| sheet sizes | 149 KB to 258 KB | 107 KB to 182 KB |
| detail window | 5.00 s to 5.44 s, all three | 1101 from 2.22 s, 1105 from 2.40 s, 1110 from 2.06 s |

  - The two were drawn at the same time on one machine, so the times are upper readings.
  - Robin's seed 1110 fell at 4.26 s, before twelve moments from its 2.88 s shove; the window slid back to end at the fall, and the block records both starts.
  - **Sheets are repeatable**: two separate draws gave byte-identical sheets for all twelve. The encoded video is not (same size, different digest).
- The receipts `docs/probes/ot11/retained/p2-*.json` gained their `film` block and nothing else; every other key is unchanged from ADR-458.
- The measurement never waits on the film: `evaluation.json` is written complete, then again with its film. A film that cannot be drawn exits 1 and leaves the measurement.

Evidence, at commit `7cf3f906`:

```
pixi run test-engine
  2439 passed, 53 skipped in 505.34s (0:08:25)
pixi run python -m pytest cli/tests -q
  1191 passed, 1 skipped in 1037.48s (0:17:17)      (1147 before; 44 new: 32 film, 10 dashboard, 1 contract, 1 command)
```

- No engine source, protocol or payload changed (`src/` is untouched), so the packaged lifecycle gate was not run. No `shell/` change, so `pixi run gate` was not run.
- An earlier full CLI run on this unit had one failure, in my own new test: the fixture read the receipt, which had just gained a real `film` block. The fixture now states its own. The figures above are from the run after that fix.

Concerns and assumptions for the next iteration:

- **The unreconciled tail is three records. Reconcile first.**
- **The judge has still not run.** Its runner is the next unit after the reconcile. The sheets it needs are in the two projects (all three judged seeds); only seed 1101's are committed.
- **"Side-on, following the base" is not literal.** The product names no base: the window follows the whole design's centre, and side-on is the direction from the design's start to where it was farthest away (the front view under 5 % of its size). On Robin's seed 1110 the early detail frames show the wheels three-quarter on rather than along the axle. This is stated in the ot11 README. The judge unit should decide whether it needs a recorded contract decision.
- **A reach frame shows no target marker.** No trace carries a goal until P3.
- Each `--film-only` run adds an `evaluate` row to the project's `PROGRESS.md`. Both negative copies now have several identical rows from this iteration's draws at three frame sizes.
- The first films of this iteration were committed to the two project copies' own git histories before the `.gitignore` fix. They are untracked now, but the blobs remain in those histories.
- Default `cadex evaluate` now takes about 3.5 minutes longer on a sixty-part robot (one seed's sheets and video). `--no-video` cuts that to about 21 s; `--film none` to nothing. P4's agent loop should probably use `--no-video`.
- Evaluations written with `--out` outside `evaluations/` are not on the dashboard. Nothing prunes old evaluation directories.
- The `assembly` API page still has 89 characters of budget; trimming it remains due before P3 (carried from ADR-458). Nothing in this unit touched it.

No new dependency (FFmpeg is the encoder `video.py` already used). No protocol change. Nothing removed.

Dispatch closed: 1 unit — cadex evaluate films its seeds on the dark floor and the dashboard shows the report (ADR-459); both negatives filmed on the judged seeds; reconcile not done because a work iteration may not

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 7cf3f906978895d88031427a118b7e203ef551ff

## State Impact

- target: damp-flame-5523 — P2's listed parts all exist; the actor believes the criterion is met and does not tick it. cadex evaluate draws, from each filmed seed's kept trace and the accepted attempt's retained tessellation, an overview sheet and a detail sheet of twelve 256 px frames on the dark prototype floor, each frame carrying its simulation time, plus a studio video of the first filmed seed (cli/cadex_cli/film.py, ADR-459, commit 7cf3f906). Flags: --film (auto/all/none/seeds), --no-video, --detail-start, --detail-step, --film-only. The report gains a film block (cadex-evaluation-film-v1); the measurement is written before anything is drawn, and a film that cannot be drawn exits 1 and leaves it. The review dashboard has an Evaluation tab (REVIEW-DESIGN.md section 17) over /api/project's evaluations list, /api/evaluation/<name> and /evaluation/<name>/<file>, pinned in headless Chromium on the w2-2 shuffle as the failing fixture and a passing one. Sheets are byte-repeatable across draws; the encoded video is not. FFmpeg is found beside the interpreter; the evaluation directory ignores its own film. Limits: a reach frame shows no target marker until P3 puts a goal in the trace; the detail follows the whole design's centre, not a named base; default evaluate is about 3.5 min longer on a sixty-part robot (21 s with --no-video). Both suites green: engine 2439 passed 53 skipped, CLI 1191 passed 1 skipped. No engine, protocol or payload change.
- target: rough-shore-6557 — no status change. Both known negatives are filmed on the contract's judged seeds 1101, 1105 and 1110 from ADR-458's traces with no new rollout: w2-2 on the walk window (5.0 s, 0.04 s), Robin from each seed's first shove onset at 0.2 s (seed 1110's window slid back to end at its 4.26 s fall). Receipts docs/probes/ot11/retained/p2-*.json gained a film block and nothing else; seed 1101's four sheets are committed under docs/probes/ot11/ (107 KB to 258 KB). The blind video judge has still not run; its runner is next. The product's side-on view follows the design's centre rather than a named base, which the judge unit should rule on as a contract decision or not.
