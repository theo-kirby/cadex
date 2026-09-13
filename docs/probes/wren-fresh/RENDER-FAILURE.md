# Wren encoder failure during real training

Verified against source: 2026-09-13. [Cadex-new] D4/D10, iteration 79.

This probe tests a real renderer failure while an independently bounded GPU
trainer continues. It uses the product agent's accepted 90 mm Wren design and
the persistent private-network dashboard. No telemetry, run outcome or video
receipt is edited to simulate the failure.

**Run the CLI and engine suites before or after this experiment, never alongside
it: their live tests launch additional trainers.**

From the repository, start the existing experiment with a fresh run name:

```bash
PYTHONPATH=cli:cli/tests OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  pixi run python docs/probes/wren-fresh/train.py \
  "$HOME/cadex-projects/ot5-wren-copy54" wren79 \
  "http://$(tailscale ip -4):8765/" \
  'product-agent-authored 90 mm Wren revision; controlled encoder failure isolation repeat'
```

While that experiment is running, launch the failure observer:

```bash
PYTHONPATH=cli:cli/tests OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  pixi run python docs/probes/wren-fresh/render_failure.py \
  "$HOME/cadex-projects/ot5-wren-copy54" wren79 \
  "http://$(tailscale ip -4):8765/" wren71-final
```

The last argument names the earlier run whose retained recording must stay
playable during the fault; it was fixed to `wren71-final` until iteration 98
made the observer project-agnostic for the Lark repeat.

The observer waits for the experiment's verified checkpoint20 publication.
It then runs the ordinary CLI renderer with a temporary `ffmpeg` executable
that exits 73, visible only in that subprocess's PATH. The renderer validates
the retained rollout, renders its frames, fails at encoding, exits 1 and writes
its own failed `video.json`. The temporary executable is removed before retry.
This is a checkpoint **re-render** failure: the already verified recording must
remain playable, with its availability distinct from the failed render outcome.

Two headless browser pages open the persistent server: one follows the active
training run and observes four distinct iterations through automatic polling;
the other selects the checkpoint and checks the encoder error, CLI retry guidance,
and retained playback/download. Linux process identities assert exactly one
unchanged trainer across those observations. An older `wren71-final` recording
also plays and downloads while the checkpoint re-render is failed.

The observer retries the same retained checkpoint through the ordinary renderer
with the real encoder, fully decodes and checks the result, and exercises browser
playback/download. It asserts training remains active afterward. Independently,
`train.py` completes its 240 updates and records, verifies and browser-checks the
final policy video. Failures of the observer do not signal the trainer, whose own
1,800-second timeout and systemd `MemoryMax=20G` remain in force.

Raw receipts and screenshots stay under the working project's `evidence/`;
policies, traces and videos stay under `runs/` and `assets/`. Retain the failure
receipt before retry overwrites the current render outcome. This experiment
proves same-machine access through the private-network address; it does not
claim a second-device test, gait improvement or a new design revision.

## Observed failure and recovery

The successful isolation observation deliberately failed encoding in **4.056 s**,
starting at trainer update **74**. The persistent page showed **Recorded video
render: failed — ValueError: FFmpeg encoding failed** with the CLI retry action,
while **Video files: available (1/1 retained)** correctly described the earlier
recording. Browser updates **78, 80, 82, 84** carried matching reward/loss history
lengths **79, 81, 83, 85**, without a reload. The sole trainer PID **3559899**
and process start tick **100682276** were unchanged; training reached update
**85** after the failure/history checks and **96** after successful recovery.

The recovered checkpoint clip fully decodes to **81 frames**, 10 fps, **8.1 s**
encoded for **8 s** simulation, seed 0. Its policy is
`fdf59bb967773ce39fae259855cd9e7292edc491ebff862eff09dbda97eb334f`,
playback revision
`a81937e7391b28c294a377819bf5d686589469a7d07eedbb5b87d1ee6e56bc4b`,
and browser-verified download
`c981147c51b859f76fb536996a2f7516077e82e95fe83e6a86e86db77b2accdb`.
The shared `cadex-prototype-light-v1` style is retained with its renderer/style
digest; this unit makes no new visual-reference comparison claim.

Two earlier observer attempts are retained and excluded from that pass:

- The first failure observation detected a second trainer from a concurrent
  CLI live test and aborted. This violated the one-trainer experiment boundary.
  Both suites were stopped; only the original GPU trainer remained before
  retry. Full suites are scheduled sequentially after GPU training. The raw
  receipt is `evidence/wren79-checkpoint20-render-failure-overlap.json`.
- The second observer saw updates 58, 60, 62, 64 but incorrectly required the
  first sample to exceed the pre-render sample (58). Checkpoint publication
  can hold that first sample steady. The probe now requires three subsequent
  updates, and the final pass used that assertion. The raw receipt is
  `evidence/wren79-checkpoint20-render-failure-initial-sample.json`.

No product defect was demonstrated: renderer failure publication, retained
recording access, retry and training isolation all worked. The delivered
regression is this reproducible real-training browser probe. Its earlier
execution errors do not qualify as product regression failures or clean
single-trainer evidence for the entire training run.

## Completed attempt

[The compact receipt](render79-evidence.json) retains the start-browser identity,
failure/recovery checks, witness results, resource bound and final browser check.
`wren79` exited **0**, with 240 committed updates and telemetry `done`; wall time
from experiment launch to trainer exit was **718.999 s**. Sampled training-scope
host memory peaked at **7,413,522,432 bytes**, below the 20 GiB limit. The sampled
whole-GPU peak was **15,120 MiB**, which includes the disclosed test overlap and
browser rendering and is not a trainer-only memory measurement.

The final policy witness error was **8.71585e-08**, below **1e-04**. Its final
recording also decoded to 81 differing frames, 8.1 s encoded for an 8 s seed-0
simulation. Browser playback across polling and hash-checked download passed;
a fresh persistent visit selected **wren79-final**, revision
`0d78fae96c2279e94b734225605b3fa6261c8e755794b9c1368fd639f747c0f7`,
policy `d170b78ab1a360c2e6e2e0f6529542841315f615a8b5d66b435898abccd767f2`,
video `9c74f4cba35f6ef350550052ab717435e429d162b93604efa213237a944cc9b8`.
Historical checkpoint selection and return to the current run passed.

All **703** pre-existing run/asset files remain byte-identical. The server now
lists **21** retained runs and continues serving the same working project on
port 8765 without a restart. Earlier model/video identities remain historical.
No gait comparison, new reference-style assessment or second-device test was run.

Validation after the Wren trainer exited, run sequentially with
`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1`: `pixi run python -m pytest cli/tests`
passed **422**, skipped **1** in **413.18 s**; `pixi run test-engine` passed
**2110**, skipped **53** in **252.38 s**. The initial overlapping suites were
interrupted and are not counted as passes. No product/protocol/payload change,
new dependency or full build was needed.
