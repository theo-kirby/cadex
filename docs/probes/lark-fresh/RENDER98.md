# Lark encoder failure during real training

Verified against source: 2026-09-13. [Cadex-new] Iteration 98, D4/D9/D10.

This experiment closes the last acceptance gap [LIFECYCLE.md](LIFECYCLE.md)
named as resting on Wren: a real renderer failure while an independently
bounded Lark GPU trainer continues, on the persistent private-network
dashboard. It uses the working copy `ot5-lark-copy85` and its accepted
90 mm-foot design with no script change, checkpoint import or design
experiment. No telemetry, run outcome or video receipt is edited to simulate
the failure; the ordinary CLI renderer publishes its own failed receipt.

From the checkout, with a fresh run name, in two shells:

```bash
PYTHONPATH=cli:cli/tests OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  pixi run python docs/probes/lark-fresh/train.py \
  "$HOME/cadex-projects/ot5-lark-copy85" lark98 \
  "http://$(tailscale ip -4):8765/" \
  'product-agent-authored Lark 45 mm revision on the working copy; controlled encoder failure isolation repeat'

PYTHONPATH=cli:cli/tests OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  pixi run python docs/probes/wren-fresh/render_failure.py \
  "$HOME/cadex-projects/ot5-lark-copy85" lark98 \
  "http://$(tailscale ip -4):8765/" lark2-final
```

The [experiment driver](train.py) is unchanged: 240 PPO updates, 1,024
environments, seed 0, checkpoints every 20, `MemoryMax=20G`, an 1,800-second
TERM timeout, a checkpoint-20 video published while training is active and a
final-policy video afterwards. The [failure observer](../wren-fresh/render_failure.py)
is the Wren one with its one Wren name removed: the earlier run whose retained
recording must stay playable during the fault is now its fourth argument
(`lark2-final` here, the previous design revision's final video), so the same
observer serves any fresh project. It waits for the driver's verified
checkpoint publication, re-renders that checkpoint through the ordinary CLI
renderer with a temporary `ffmpeg` that exits 73 on that subprocess's `PATH`
only, then retries with the real encoder. Run the CLI and engine suites
before or after, never alongside: their live tests launch trainers.

## Observed failure and recovery

The [compact receipt](render98-evidence.json) retains the identities below;
raw receipts, screenshots and logs stay in the copy's `evidence/`, hashed there.

| Observation | Value |
|---|---|
| Trainer | one process, PID 19886, start ticks 102341947, identical before the fault and after the history checks |
| Checkpoint published | at update 23, first video `5c68796a96d9…`, 81 frames, render 12.881 s, browser check exit 0 |
| Fault | encoder exits 73; renderer exit 1 after 3.553 s, `ValueError: FFmpeg encoding failed`, receipt state `failed` |
| Page during fault | **Recorded video render: failed — ValueError: FFmpeg encoding failed. Retry the CLI video command after fixing the retained inputs or encoder.** with **Video files: available (1/1 retained)** |
| Retained recording | the first checkpoint video still played and downloaded hash-equal during the fault |
| Live page | updates 37, 38, 39, 40 seen without reload; reward/loss history lengths 38 → 41 |
| Historical video | `lark2-final` (revision `ca88f223b54c…`, policy `b79a63908e94…`) played and downloaded `af610491bedf…` while the fault stood |
| Recovery | real-encoder retry wrote `a2e40b55c0a1…`, receipt `ready`; both WebM files retained; decoded 81 differing frames, 8.1 s for 8.0 s simulated, seed 0 |
| Training after | update 41 after the fault checks, 53 when the recovery check finished, 239 at exit 0, state `done`, device `gpu` |
| Bound | host peak 7,406,166,016 bytes under `MemoryMax` 21,474,836,480; wall 729.568 s under 1,800; whole-GPU peak 15,122 MiB including the browser |
| Final | policy `fca598975089…`, witness error 8.85e-08 under 1e-04; fresh visit selects `RUN lark98-final`, historical `lark98-checkpoint20` selectable and returned to current |

The failure and the availability of the earlier recording are shown as two
separate facts, which is what a re-render failure needs: the page never
substituted an older run's video and never hid the one already verified.

## Observer bookkeeping defect

Every assertion in the observer passed. Its last step then read
`evidence/lark98-checkpoint20-check.json`, a name `check_video.py` stopped
writing when iteration 88 gave `--not-default` checks a `-recheck` suffix,
and raised `FileNotFoundError`. Two consequences, both recorded honestly:

- The recovery check landed under the `-recheck` name and overwrote the
  driver's publication-time check files. The publication-time result (exit 0,
  video `5c68796a96d9…`) survives in `lark98-checkpoint20-publication.json`,
  and the fault-time receipt holds that video's playback.
- The post-recovery trainer sample was taken from the driver's committed
  timeline at the recovery receipt's mtime instead of by the observer.

The observer now runs the recovery check under its own `render-recovery`
label and reads that file; the Wren command in
[RENDER-FAILURE.md](../wren-fresh/RENDER-FAILURE.md) carries the new argument.
This is a probe defect, not a product one: renderer failure publication,
retained access, retry and trainer isolation all worked on the first attempt.

## Scope

Same-machine headless Chromium over the private address; no second-device
test, no gait claim, no new visual-reference comparison and no product,
protocol or payload change. All ten earlier run records are byte-identical,
no file under `runs/`, `assets/` or `evidence/` outside `lark98*` changed,
and the copy's script history gained the two policy declarations the
playback flow makes (`be429f2e567c…` for the checkpoint, `6f826037044a…`
for the final). The persistent service kept its PID and now lists 13 runs.
