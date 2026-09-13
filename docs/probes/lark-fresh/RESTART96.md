# Lark dashboard restart during real training

Verified against source: 2026-09-13. [Cadex-new] Iteration 96, D6/D10.

This experiment fills the Lark-specific D6 gap identified in
[LIFECYCLE.md](LIFECYCLE.md): restart the persistent dashboard during a bounded
real GPU run, while retaining a historical video in an already-open page.
It uses the accepted 90 mm-foot working copy and its public export, with no
script change, checkpoint import or design experiment.

From the checkout:

```bash
PYTHONPATH=cli:cli/tests pixi run python docs/probes/lark-fresh/restart_training.py \
  "$HOME/cadex-projects/ot5-lark-copy85" "http://$(tailscale ip -4):8765/" \
  lark96-restart lark2-final
```

Use a new run name for a repeat. The driver refuses an existing output directory,
retains the model/task, script, specs and training view, and launches 100 PPO
iterations, 1,024 environments, seed 0, in `MemoryMax=20G` with a 900-second
TERM timeout and 20-second kill grace. The existing exclusion guard samples
Python trainers and pytest processes every 50 ms; the CLI suite runs afterward.
No dependency was added.

The existing project-agnostic [restart observer](../wren-fresh/restart_training.py)
waits for real update 4, opens live and historical pages through the stable
private-network URL, then runs:

```bash
systemctl --user restart cadex-operator-review
```

Only the dashboard restarts. The observer records its old/new PID and the
trainer PID plus Linux process start ticks, asserts increasing telemetry and
seven new page updates, checks fresh-visit identity before/after restart, and
preserves the historical video element, revision and playing state without
navigation. Downloaded historical bytes must match the retained video digest.
The return-to-current route must select the active attempt. The supervisor
then waits for training completion, publishes its terminal run record, verifies
completion on a fresh page, and checks all earlier run files and the accepted
manifest for byte equality. Raw logs, screenshots and receipts remain under
`ot5-lark-copy85/evidence/lark96-restart*`; retained run inputs and the final
policy are under `runs/lark96-restart/`.

This is a same-machine headless Chromium check over the private address,
not a second-device claim. This unit renders no new video; it tests continuity
of a previously verified recording. The newest training attempt remains the
fresh default, with video absence visible, rather than selecting an older video.
The existing creation/copy engine-restore receipts supply D6's save/reopen half;
this experiment does not restart the engine during training; [ENGINE109.md](ENGINE109.md) does.

## Observed restart and the failed first observation

The first observer used `lark86-retry-video`, whose revision equals the current
accepted revision. It failed its HISTORICAL assertion **before restarting** the
service. Training continued. The failed receipt was preserved and the same
observer was repeated during the same trainer using `lark2-final`. That passed.
The driver now checks this historical-revision precondition before creating a
run or launching training. This was an observation setup correction, not a
second training attempt or a dashboard defect.

Dashboard PID changed **4073466 → 4173669**; restart returned in **0.164 s**.
Trainer PID **4168235**, start ticks **102226219**, stayed identical while
telemetry advanced **24 → 34**. The first newer page update appeared **0.585 s**
after restart began. Seven observed updates arrived **0.400–1.324 s** after
commit, with reward/loss/episode-history points increasing together. Neither
page navigated again. Historical `lark2-final` retained its revision and video
element, kept playing, and downloaded with digest
`af610491bedf8ed8d13b8bbc7c05c94954747d95f86514b387256148c84cf826`.
Fresh visits and return-to-current selected `lark96-restart`, revision
`7f6c23913d55184241d0b31ca0fdfddf17d3c613d0c25e17d5943af57c75661b`.

The initial supervisor retains its observer-exit failure even though training
succeeded. A separate completion collection joins that failure and the passing
second observer in [restart96-evidence.json](restart96-evidence.json); it does
not rewrite the raw failure. Because the supervisor stopped before its final
inventory assertions, this run does **not** claim a full before/after file
inventory pass. The retained browser/download checks establish historical
playback continuity; earlier copy evidence supplies broader preservation checks.

## Completion and handoff

Training exited **0**, completed all **100** updates on GPU, and saved policy
`f7a152ff9c545716a37ee2a740c25895e154d9efaf2dbf3d3e155fcbe339b980`.
The exclusion guard made **4,944** scans (maximum gap **0.0593 s**), observed
only trainer PID 4168235, and recorded no violation. Sampled peak host memory
was **5,491,826,688 bytes**, below the enforced **21,474,836,480-byte** cap.
The final fresh browser showed the accepted revision, `RUN lark96-restart`,
`completed`, `done` telemetry, and `videos: none recorded for this run`.
Accepted revision/digest still match the retained run; the service remains active.

D6 now has the missing Lark real-training restart evidence alongside the linked
save/reopen receipts. The checkbox remains owner-controlled. The next bet is
**D4**: inject a real renderer failure during a bounded Lark run, prove training
continues, then produce a verified recording. That Lark-specific gap still
relies on Wren evidence; do not repeat the completed D8 audit or this restart.

Verification on final source: `pixi run python -m pytest cli/tests` passed
**446 tests, 1 skipped in 435.57 s**. This includes the headless browser
lifecycle, review-server and video tests. The real restart observer and separate
completion browser collection passed. The new historical preflight was directly
checked to refuse before creating a run. `git diff --check` passed. No engine,
payload or shell behavior changed, so no build, engine suite or packaged gate
was run. The retained trainer log includes optional Warp-import diagnostics;
MJX GPU training and final witness validation still succeeded.
