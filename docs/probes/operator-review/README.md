# Persistent operator review

Verified against source: 2026-09-13. [Cadex-new]

The [Wren lifecycle report](../wren-fresh/LIFECYCLE.md) links D1–D11 evidence, the design
comparisons and their limits, and the current persistent-browser check.

The shared private-network dashboard on port 8765 serves **`ot5-wren-copy54`**,
with **`wren71-final` selected by default**, playback revision **`e9dee22bc90c…`**
and the product agent's 90 mm feet. Iteration 71 completed a 240-update GPU
repeat and restarted this persistent service during training: one unchanged
trainer, telemetry recovery in 0.957 s, and historical `wren66-final` playback
and download preserved. Checkpoint and final videos are verified, saved,
playable and downloadable; a fresh completion visit confirmed the final default.
No experiment trainer remains active. The service stays running.
[Real-training restart proof and receipts](../wren-fresh/RESTART-TRAINING.md).
The earlier [seed 0–4 comparison](../wren-fresh/REVISION66.md) remains historical.

Iteration 72 rechecked this persistent URL without restarting it or training:
six current/historical playback views expose their own eight-component models,
retained documents, curves and hash-matching video downloads. All 703 run/asset
files stayed unchanged. Fresh default remains `wren71-final` among 18 runs;
historical playback and return-to-current passed.
[Current browser receipt](../wren-fresh/lifecycle72-evidence.json).

Iteration 73 compared the current 90 mm viewport and decoded final video with
identified neural-whoop references at matched pose/camera and close/wide
framing. Lossless viewport/capture parity and RGB codec error 1.50058/255;
pointer orbit, current and historical playback/download/polling passed.
No renderer defect was demonstrated. Service, project and default remain
unchanged; no training or restart occurred.
[Current visual assessment](../review-style/README.md#current-90-mm-wren-comparison--iteration-73).

Iteration 69 verified two engine reopens and restarted the persistent service
with the saved working project intact: all 15 run views matched, the open
page kept playing, and fresh visits still selected `wren66-final`. Current
and historical video downloads matched their recorded hashes. No trainer
was running; the service remains up. [D6 proof](../wren-fresh/RESTART.md).

Iteration 67 restarted this same service once, with no trainer running, to
load ADR-309: a playback run's checkpoints now resolve through the training
run its record names. On the persistent URL, `wren66-final` (default, CURRENT)
lists twelve checkpoints `retained · from training run wren66` where the
previous page said `missing`; `wren66-checkpoint20` (HISTORICAL) resolves the
same provenance but its frozen snapshot, copied at iteration 18, lists no
checkpoints and is labelled `stale` rather than invented; `wren57-retry`
(HISTORICAL, trained in place) keeps its own-run checkpoint. Each check
returned to the current run. Project, default run and identity above are
unchanged; no experiment started and no project switch occurred.
[Probe and evidence](../wren-fresh/CHECKPOINT-PROVENANCE.md).

Before iteration 66 the page selected **`wren57-retry`**, accepted playback
revision **`79f86c69bfc3…`** and 110 mm feet. Its guarded GPU retry completed
12 updates. Iteration 60 engine-verified its saved
policy and published an 8-second seed-0 rollout video on that attempt.
All four older videos remain selectable, playable and downloadable. Historical
playback survived the new video arriving; the current video fully decoded,
played through polling and downloaded with a matching hash. The original
training revision `5b61ef31ff13…` and inputs are explicitly retained.
[Publication evidence and commands](../wren-fresh/RETRY-VIDEO.md).

Iteration 62 verified this same persistent URL after fixing accepted-model
refresh (ADR-307): a changed accepted revision now reloads geometry during
polling, including first acceptance in an empty view. Current/accepted/historical
document checks and retry playback/download passed. No authoring attempt or
training was launched; the unit was selected before the provider's reported
22:40 reset. Wren's product-agent revision remains outstanding.
[Refresh regression and persistent evidence](../wren-fresh/MODEL-REFRESH.md).

The preceding **`wren57-interrupt`** retains its six real updates, failed status,
`KeyboardInterrupt` and controlled-interruption/retry guidance. Both attempts
ran after the required suites, with at most one trainer observed and no
exclusion violation. [Experiment and limitations](../wren-fresh/INTERRUPTION.md).

Iteration 58's product-agent revision turn on this copy was refused by the
provider session limit before authoring. Accepted identity/specs and all 434
run/asset files remained unchanged during that attempt. Persistent-browser
checks verified the current default, accepted view, all four historical video playbacks/downloads
and return-to-current. The service remains running. The foot revision is still
caller-authored; Wren's D9 authorship gap remains open.
[Attempt and evidence](../wren-fresh/AGENT-REVISION.md#current-attempt-working-copy-iteration-58).

Previous experiment status (before the copy switch):

The shared private-network dashboard on port 8765 serves `ot5-wren`, with
**`wren2-final` selected by default**, revision **`26332a5955e3…`**, 105 mm feet.
Iteration 52 completed 240 GPU iterations; no training remains active.
The verified checkpoint and final videos both play/download, as do the original
85 mm recordings. Historical playback survives polling and returns to current.
The service was not restarted and stays running.

Iteration 53's requested product-agent design turn was refused by both Fable
and Sonnet at their provider session limit. No geometry revision or training
attempt was created. The accepted/current identity above is unchanged; all
228 retained run files and all four browser-playable/downloadable reviews
were verified intact. [Attempt, retry instructions and browser evidence](../wren-fresh/AGENT-REVISION.md).
The explicit fallback leaves Sonnet as the project's stored model preference.

At experiment start, the browser selected active `wren2` at revision
`a90b84033ced…`. Seven real training updates reached the page within
0.50–1.53 seconds, and the checkpoint video was played while training remained
active. At completion, the browser verified the revised final identity and
video. These are same-machine private-network checks, not second-device
observations. The original Wren was product-agent authored; the foot revision
was a public CLI parameter edit, not a product-agent design turn.

The revised final policy survived five of five eight-second episodes, versus
three of five for the original final policy. Small displacement and standing
poses do not establish walking. See [the comparative lifecycle report](../wren-fresh/COMPARISON.md)
and its compact training, playback/download and per-seed receipts.

Keep the server running between iterations. On this Linux host, from the
checkout, the detached command is:

```bash
systemd-run --user --unit=cadex-operator-review --property=Restart=on-failure \
  --working-directory="$PWD" "$PWD/cadex" review \
  --project "$HOME/cadex-projects/ot5-wren-copy54" \
  --host "$(tailscale ip -4)" --port 8765
```

For a deliberate working-project switch, stop `cadex-operator-review` with
`systemctl --user stop cadex-operator-review`, start the command with the new
project, and verify the same URL. This transient user service survives actor
exit and tests; it is not a reboot installation. Do not restart Ouroboros or
training. Update this published status on experiment start/completion and
project switches.

The following historical Reed read-only probe uses the existing persistent server; it never launches or
stops a test server:

```bash
PYTHONPATH=cli:cli/tests pixi run python docs/probes/operator-review/verify.py \
  "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-biped-copy29" copy100
```

The committed `evidence.json` records the observed project/run/model identity,
real saved-video playback and matching download digest, preserved playback on
poll, historical `probe3-final` selection and return to current. This was a
headless Chromium observation through this machine's private-network address,
not a second-device test or an observation during new GPU training. D10 still
needs the persistent URL observed across a real experiment start/completion.

Iteration 39 reverified this same persistent URL without restarting it. The
[visual baseline](../review-style/README.md) records its current appearance;
[operator results](../review-style/operator.json) again pass current identity,
playback/download and polling/history preservation. The requested D11 environment
is not yet implemented. No new experiment or working-project switch occurred.


Iteration 40 restarted this same service to load the shared scene and kept its
project/run unchanged. [D11 implementation evidence](../review-style/implementation.json)
now records the persistent viewport, new final/checkpoint recordings, actual
light reference and same-pose/camera parity. Playback/download, polling and
historical selection pass at the private URL. Current published status remains
`ot5-biped-copy29 / copy100`; there is no new training attempt. The service stays
running. D10's real experiment-spanning observation is still open.

Iteration 41 spanned a real experiment on this same URL: `shin55` appeared as
`running` before its first iteration, a fresh visit selected it by default,
seven live iterations showed within 0.26–1.69 s, the checkpoint 20 video was
published and played here while training continued, and after the trainer
exited a fresh visit selected `shin55-final` with its video, playback across a
poll, historical `probe3-final` and return to current. The service was then
restarted once, after training, to load ADR-302 (all eight accepted meshes now
retained) and the same check passed again. Evidence:
[reed-agentrev](../reed-agentrev/README.md). Published status is now
`ot5-biped-copy29 / shin55-final`; the service stays running.

Iteration 43 reverified this same URL without restarting it, while assembling
the [lifecycle report](../reed-lifecycle/README.md): a fresh visit selected
`shin55-final` by default at the accepted revision, played and downloaded its
video with the recorded digest, kept playing across a poll, showed
`probe3-final` as HISTORICAL and returned to current. No training was active,
no experiment started and no project switch occurred; published status stays
`ot5-biped-copy29 / shin55-final` and the service keeps running.

Iteration 44 reverified this same URL without restarting it, through the
[shin55-final visual comparison](../review-style/README.md#repeat-on-shin55-final--iteration-44):
`shin55-final` selected by default at the accepted revision, its viewport
byte-identical to the capture page at the video's camera and within 1.67/255 of
the decoded clip, a real drag/zoom orbit on the canvas, `shin55-checkpoint20`
played, downloaded with the recorded digest and preserved across a poll,
labelled HISTORICAL, and return to current. No training was active, no
experiment started and no project switch occurred; published status stays
`ot5-biped-copy29 / shin55-final` and the service keeps running.

Iteration 46 first put the run-less `ot5-wren` project on this URL at revision
`5309bebc6597…`; [its retained receipt](../wren-fresh/evidence.json) remains
historical evidence of that switch. Iteration 48 then verified in-place restore
preservation at that revision. For current Wren training/video checks, use the
[Wren experiment probes](../wren-fresh/README.md#first-bounded-wren-gpu-experiment-iteration-49).
