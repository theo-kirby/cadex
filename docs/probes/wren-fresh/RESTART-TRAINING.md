# Wren dashboard restart during real GPU training

Verified against source: 2026-09-13. [Cadex-new] Iteration 71, D6/D10.

The persistent dashboard restarted during **`wren71`**, a real GPU repeat of
the product agent's 90 mm Wren design on `ot5-wren-copy54`. The same trainer
continued; two already-open browser pages recovered through ordinary polling,
with historical `wren66-final` still playing. This supplies the real-training
concurrency evidence explicitly excluded by [the saved-project proof](RESTART.md).
It does not repeat that proof's engine reopen while a trainer is active.

Run the existing experiment from the checkout, then the observer alongside it:

```bash
PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/train.py \
  "$HOME/cadex-projects/ot5-wren-copy54" wren71 "http://$(tailscale ip -4):8765/" \
  'product-agent-authored 90 mm Wren revision; repeat for real-training dashboard restart proof'
# In a second terminal while the experiment runs:
PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/restart_training.py \
  "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-wren-copy54" \
  wren71 wren66-final
```

Use a new run name for another attempt: the experiment refuses an existing
training directory. One trainer, 240 PPO updates, 1,024 environments, seed 0,
checkpoint every 20, 1,800-second timeout and systemd `MemoryMax=20G`.
The observer waits for update 4, checks live model identity, plays history,
and runs `systemctl --user restart cadex-operator-review`. It never signals
the trainer or writes its telemetry. Browser failure leaves that independently
bounded training running and writes a failure receipt.

## Restart observations

[restart71-evidence.json](restart71-evidence.json) retains the measured receipt.
Dashboard PID **3255404 → 3308131**; the restart command returned in **0.114 s**.
Trainer PID **3303026**, process start tick **100242161**, was the only
`cadex_train.py` interpreter before and after restart and in every subsequent
observer sample. Its committed updates advanced from **4 to 14**.
The first newer update appeared automatically **0.957 s** after restart began.
Seven observed updates (6, 7, 8, 10, 11, 13, 14) arrived **0.240–1.423 s**
after their committed timestamps; each had matching reward, loss and episode
history lengths. This measures polling under these conditions, not every
training iteration or a universal latency guarantee.

The historical page kept the same video element, revision and selection;
playback time advanced after restart, and its downloaded bytes matched
`802baa759c98e52ba1067cab1f39e28dc72d3fee7c82b073b285bffe0a82470a`.
Both pages had one navigation. A fresh visit selected `RUN wren71` at training
revision `062e927c0196cc06ef7250010c40dbb6069cad4f2a7d1bef113d0845db4207b9`;
the historical page's return-to-current button selected the same live attempt.
The training revision differs from iteration 66 because the retained script
names a different policy asset; model/task hashes are the geometry comparison,
not equality of whole-script playback revisions.

The fixture browser regression in `cli/tests/test_review_lifecycle.py` now
requires advancing, unpaused playback after the service restarts and a newer
telemetry update within five seconds. It retains the producer identity,
no-duplication, historical selection, download and project-byte assertions.
The real receipt has a separate consistency guard in
`cli/tests/test_wren_fresh_evidence.py`.

All raw logs, screenshots, progress, policies, traces and videos remain under
the working project's `evidence/wren71-*`, `runs/wren71*` and `assets/`.
Retain the whole project. Evidence uses headless Chromium on this machine
through its private address; no second-device or new D11 visual comparison
is claimed. The renderer uses the existing shared style. No new dependency,
protocol, payload or shell change was needed.

## Lifecycle coverage and verification

This repeat advances D6 with **real training during dashboard restart** and
D10 with the persistent active-run default and deliberate historical browsing.
It complements the prior in-place engine reopens and saved-byte checks rather
than treating one as a substitute for the other. The active checkpoint and
final recordings exercise D3/D4 on the same attempt; this is a lifecycle
reliability repeat, not a new design comparison or gait-quality claim.

Required suites passed with `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1`:
`pixi run test-engine` — **2,110 passed, 53 skipped**, 268.14 s;
`pixi run python -m pytest cli/tests -q` — **415 passed, one skipped**, 414.17 s.
The focused browser lifecycle suite passed both tests in 13.64 s.
These suites overlapped the trainer and checkpoint render, so render-window
throughput is an uncontrolled observation including competing test work;
it cannot isolate renderer overhead. No build was needed for probes,
documentation and CLI tests; neither protocol nor payload changed.

## Completed attempt and retained recordings

`wren71` finished with exit **0**, 240 points in each history, GPU device,
**729.671 s** total experiment trainer wall time, final reward/step **0.317777**,
loss **0.168609** and estimated episode length **353.103 steps**.
Sampled scope memory peaked at **7,395,639,296 bytes**, below the 20 GiB cap.
The whole-GPU memory query peaked at **31,525 MiB**, including concurrent
browser/test work; that number is not attributable to the trainer alone.
The trainer's optional Warp import diagnostics did not prevent MJX training or
policy verification. No trainer process remained at the completion check.

[training71-evidence.json](training71-evidence.json) is the compact experiment
receipt, generated with `summarize_training.py PROJECT wren71` and augmented
with the completion/late-active `current.py` receipts, final history lengths
and the memory-scope/test-overlap labels. The experiment preserved all **15**
previous run records and retained matching model/task inputs in both new
playback runs. Checkpoint render wall time was **14.039 s** (updates 23→33),
and publication/playback finished at update **35**, with training still active.
Ordinary iteration medians before/during/after the render were
**1.435 / 1.356 / 1.304 s**; the concurrent suites prevent attributing differences
to rendering. Final render wall time was **12.682 s**.

| Seed 0 recording | Checkpoint 20 | Final policy |
|---|---:|---:|
| Engine witness error (tolerance 0.0001) | 2.80e-08 | 7.88e-08 |
| Simulation / encoded duration | 8 / 8.1 s | 8 / 8.1 s |
| Fully decoded frames at 10 fps | 81 | 81 |
| Torso X displacement | +49.094 mm | +61.241 mm |
| Threshold falls | 0 | 0 |
| Total reward | 216.020 | 146.746 |

The two videos played and downloaded through port 8765 with their recorded
policy, revision, seed and simulation-time labels. SHA-256 identities:

- Checkpoint video: `3fef14c9cde01bffb632c500a7bde061bd00c72e18a0fe550989fde802c53d37`.
- Final video: `a2fde70a223941d18096dc08d3559ab2cae8e0b834ad3b2cc6920487074bdcc5`.

These are one-seed rollout observations, not the multi-seed design comparison
or evidence of alternating gait. Full policy/model/task/trace/style identities
are in the receipt and retained run records; older videos are unchanged history.

A fresh browser at update 234 still selected **`wren71`**, despite checkpoint
playback having changed the accepted script. After completion, `current.py`
and the final-video browser check both selected **`wren71-final`**, revision
`e9dee22bc90c428942562eeadf150ef4bcd4ab03d8e9ed96e0f959272cfa22bb`, 90 mm feet.
The browser selected the checkpoint as HISTORICAL and returned to the final
current run. Port 8765 remains serving the working copy with **18** retained
runs. Published operator status now reflects this result. The final added
completion-receipt guard also passed in the focused evidence suite.
