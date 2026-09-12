# Persistent Reed operator review

Verified against source: 2026-09-12. [Cadex-new]

The shared private-network dashboard on port 8765 now serves `ot5-wren`,
the second fresh agent-authored biped, at accepted revision `5309bebc6597…`.
It has no runs: a fresh visit selects ACCEPTED NOW, with twelve declared
parameter defaults and eight drawn components (seven biped solids plus ground). No training is active.
[Iteration 46 receipt](../wren-fresh/README.md) verifies this working-project
switch; Reed's retained results remain in their original project directories.

Keep the server running between iterations. On this Linux host, from the
checkout, the detached command is:

```bash
systemd-run --user --unit=cadex-operator-review --property=Restart=on-failure \
  --working-directory="$PWD" "$PWD/cadex" review \
  --project "$HOME/cadex-projects/ot5-wren" \
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

For the current run-less Wren page, use the [Wren probe](../wren-fresh/README.md), not the historical run/video probe above.
