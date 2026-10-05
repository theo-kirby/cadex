# orun3 — closing report

Verified against source: 2026-10-05, at `0b1e5264` (the orun3 run branch).
Charter: `.ouroboros/goal.md`, "Watch the design and the training as they
happen". Every number below was measured on sb1x (linux-64, RTX 5090) on
copies of the biped `ot5-biped` named `orun3-biped*`. The owner ticks the
criteria; this report claims none of them.

## Where each criterion stands

| criterion | where the evidence stands | evidence | records |
|---|---|---|---|
| V1 stage overlay | evidence recorded | ADR-542, ADR-550; `test_review_overlay.py` rewrites a fixture `progress.json` under Chromium; at 390 px the expanded overlay is 16.95% of the viewport, 20.8% with the activity list (bar 25%) | `snowy-lodge-1033`, `early-crow-5889` |
| V2 checkpoints as motion | evidence recorded | ADR-543, ADR-544, ADR-545; cost and disk in §1; `test_checkpoint_rollouts.py`, and `test_review_checkpoints.py` whose browser half runs a real engine | `forest-jasper-1180`, `nimble-moss-4028`, `snowy-water-3502`, `forest-mist-3382` |
| V3 design history | evidence recorded | ADR-546, ADR-547, ADR-548; bytes per revision in §2; `test_revision_meshes.py` (real engine), `test_review_revisions.py` (browser scrubber across revisions) | `honest-jasper-7877`, `scarlet-wood-2990`, `brisk-dune-8872` |
| V4 agent activity | evidence recorded | ADR-549, ADR-550, ADR-553; `test_activity.py` pins the 64 KiB bound and reads a real `cadex mcp` call back from `/api/project`; `test_project_tool_surface.py` unchanged | `forest-walrus-2370`, `early-crow-5889`, `tiny-bloom-2937` |
| P1 portability | evidence recorded | ADR-551, ADR-552; `test_dashboard_prefix.py` loads a project through a rewriting-free proxy under `/some/prefix/`; `test_http_api.py` holds `docs/CLI.md`'s route table equal to the router's | `sunny-oak-9772`, `little-cloud-9989` |
| W1 watchable lifecycle | evidence recorded | §3 and the ten `w1-*.png` below | `solemn-fox-1118`, `tiny-bloom-2937`, `soft-comet-8840` |
| C1 this report | this file; done claimed for critic review (§6) | §1–§5 | the record that adds this file |

## 1. V2 — what a checkpoint rollout costs

**Training cost** (ADR-544). This was measured on `orun3-biped/runs/probe3`'s
`reed_walk` bundle on the 5090: 60 iterations, 256 envs, seed 7, a checkpoint
every 5 iterations, so 11 checkpoints per run. The runs alternated off, on,
off, on, all under the machine slot. Iteration wall time is taken from the
trainer's stderr, from iteration 2 on (57 iterations per run).

| run | rollouts | mean s/it | median s/it | trainer wall s |
|---|---|---|---|---|
| off-1 | off | 9.435 | 0.9166 | 657.0 |
| on-1 | on | 9.045 | 0.9176 | 634.8 |
| off-2 | off | 9.061 | 0.9170 | 635.7 |
| on-2 | on | 9.068 | 0.9169 | 636.3 |

The adjacent pair off-2/on-2 differs by **+0.08% in the mean** and −0.01%
in the median. That is under 0.1%, and inside the charter's 5% bar. All 22
rollouts were written, and none failed. Same-seed GPU runs did not give
byte-identical policies, so "same seed" here means the same task and the
same settings.

**Disk** (ADR-544). The size of a trace follows the length of its episode:

- range: 38.7–329.5 KB per trace;
- a full 8 s horizon at 25 fps: 329.5 KB;
- mean: 224.7 KB per checkpoint, 2.47 MB for the run's 11;
- W1's run (§3): four 8 s traces of 327–328 KB, and a 32 KB one.

The traces are run outputs, ignored by `*-trace.json`, and never committed.

**Page cost** (ADR-545). The `stage.checkpoints` block for 11 real traces
is 3,357 bytes. Listing them takes 10.2 ms the first time, and an unchanged
poll does not parse them again.

## 2. V3 — bytes per revision

This was measured on `orun3-biped`'s thirteen stored revisions after
`cadex revision backfill` (ADR-548), in one 12 s pass. The biped is 8
outputs and 4 distinct part buffers, so one full copy of a revision's
tessellation is about 11,400 bytes.

| | bytes |
|---|---|
| first revision kept (13, from disk) | 5,704 of blobs |
| revision 1 rebuilt (its foot differs) | +1,422 of blobs |
| revisions 2, 4, 5, 8, 11, 12 rebuilt; 7 copied as 5's id | +0 of blobs each |
| index row per revision | ≈2,906–2,909 |
| **9 kept revisions, total** | **7,126 of blobs + 28,201 of index = 35,327** |
| nine full copies | 102,612 |
| **per kept revision** | **≈792 of blobs, ≈3,925 with its index row**, against ≈11,400 for a copy |

The other four originals (3, 6, 9 and 10) cannot be rebuilt by today's
engine. Each set `policy_on=1` against a task bundle whose digest the engine
no longer produces (ADR-520's stale policy). The timeline says this for each
of them, and shows no other revision's geometry in their place. ADR-546's
own measurement was taken on `orun3-biped-v3meas`: 5,704 bytes for the
first revision, 0 bytes of blobs for an unchanged restore, and 1,419–1,421
bytes for a foot change.

## 3. W1 — one page, never reloaded

The page was a headless Chromium on `cadex app` at 127.0.0.1, at 1280 × 820,
in the dark theme. It was opened on `/p/orun3-biped/` before the first
revision and never reloaded: it had one navigation entry, and the window
marker survived to the last screenshot (`soft-comet-8840`).

| stage | what the page showed | screenshot |
|---|---|---|
| designing | revisions 20 and 21 accepted through `cadex mcp` `set_params`. Timeline at `21/21 · newest`, the feet tinted, revision 20 ghosted. The menu and the timeline agree on 21 rows | `w1-revision-a.png` (245,165 B), `w1-revision-b.png` (271,626 B) |
| training | `cadex walk`, 120 iterations × 1024 envs on the 5090, a checkpoint every 20. Five rollouts (iterations 20, 40, 60, 80, 100) replaced each other in the viewport while it trained | `w1-training-checkpoint-1.png` (270,599 B), `-2` (271,014 B), `-3` (272,576 B) |
| evaluating | the first poll after the `evaluate` call began read `evaluating`, with `evaluate · running 2 s` | `w1-evaluating.png` (272,041 B) |
| result | `evaluate · just now`. Verdict fail (upright 5 of 5 failing), which is expected after 120 iterations | `w1-evaluated.png` (267,165 B) |
| failed | the first attempt's failed run; on the re-run, a refused `set_params` showed as an `error` activity line | `w1-try-failed.png` (238,781 B) |

`w1-try-designing-timeline.png` and `w1-try-training.png` come from the
first attempt (`solemn-fox-1118`), which found the defect ADR-553 fixed.
Every PNG is under 300 KB and on the dark floor.

**Suites, after the walk.**

- `pixi run test-engine`: 2585 passed, 58 skipped.
- `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests`, with the
  engine built: 1172 passed, 1 skipped.

No unit touched the protocol or the payload, so the packaged gate was not
required.

## 4. ADRs added by this run

| ADR | decision |
|---|---|
| ADR-542 | the 3D viewport's stage overlay, the first panel back after ADR-533 |
| ADR-543 | `cadex train` takes the machine's training slot, and so does a walk's train leg |
| ADR-544 | each checkpoint is rolled out through the engine while the run trains |
| ADR-545 | the 3D viewport loops each checkpoint's rollout, with a follow/pin scrubber |
| ADR-546 | each accepted revision's model is kept by content hash per part |
| ADR-547 | the revision timeline, with the previous revision ghosted and changed parts tinted |
| ADR-548 | `cadex revision backfill` rebuilds the models the store never kept, only on their exact revision id |
| ADR-549 | `cadex mcp` writes one bounded line per tool call to `review/activity.jsonl` |
| ADR-550 | the overlay shows the agent's latest call and recent calls, and says idle after 5 minutes |
| ADR-551 | every dashboard URL is relative to the page, so it mounts under a prefix |
| ADR-552 | the HTTP API is one table that the router dispatches from and `docs/CLI.md` lists |
| ADR-553 | a `cadex mcp` call is logged in flight as it starts, so a running `evaluate` reads as evaluating |
| ADR-554 | a run's model is re-read when the walk lands its export or rollout, so a page left open adds the `final policy` stop |
| ADR-555 | the evaluating line names the agent's `evaluate` call, never an evaluation directory's id |

## 5. Remaining defects

1. **The final-policy stop is missing on a never-reloaded page.** After the
   W1 walk exited, the run's scrubber still read `iteration 100 · 5/5 ·
   newest`, with no `final policy` stop (`soft-comet-8840`). On a fresh page
   in `solemn-fox-1118`, the same kind of run did show `final policy ·
   6/6`. **Fixed after this report by ADR-554:** the poll keyed a run's
   model on its name alone, so the manifest carrying the run's own rollout
   was never re-read; it is now keyed on the run's status, trace and export,
   and `test_review_checkpoints.py` watches a never-reloaded page add the
   stop. Not yet re-walked on `orun3-biped`.
2. **The evaluating line names the evaluation directory.** During the W1
   `evaluate`, the stage line read "evaluation dc0af1158165-d3a4… is running
   · 1 s", not ADR-553's "the agent's evaluate call is running"
   (`soft-comet-8840`). The directory-based reason wins once the evaluation
   directory exists. It was sampled only once, at 1 s, in the 74 s call.
   The stage was right; the reason named an internal id the owner cannot
   act on. **Fixed after this report by ADR-555:** an in-flight `evaluate`
   call now wins over the directory, for the whole call, and a directory
   alone reads "an evaluation is running" with no id;
   `test_review_overlay.py` watches the directory appear mid-call with the
   line unchanged. Not yet re-walked on `orun3-biped`.
3. **Progress stalls for 37–39 s before each checkpoint.** Before each
   checkpoint in the W1 walk (at iterations 39, 59, 79 and 99), the
   overlay read "no update 37–39 s" (`soft-comet-8840`). This matches the
   trainer's own stalls (about 460 s per run), which `snowy-water-3502`
   measured with rollouts both on and off. W1 did not measure it with
   rollouts off. §1's cost figure stands.

Also open, though not defects of this run's views:

- **Four of `orun3-biped`'s thirteen original revisions have no model**
  (§2). The engine refuses their stale policy output (ADR-520), and the
  page says so.
- **The long-term rungs were not worked:** phone width and the light
  theme for the overlay and both scrubbers, and binary meshes for the
  timeline. Only V1's 390 px bound was measured.

## 6. Done claim

V1–V4, P1 and W1 each have evidence recorded, and this file is C1. The
done claim is made for critic review. No owner checkbox is ticked. One
thing was still due when this file landed: the reconcile that folds
`tiny-bloom-2937`, `soft-comet-8840` and this report's record, and moves W1
and C1 to working. Work iterations are forbidden to run it.
