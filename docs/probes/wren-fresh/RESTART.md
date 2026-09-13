# Wren save/reopen and persistent dashboard restart

Verified against source: 2026-09-13. [Cadex-new]

The current saved working copy, `ot5-wren-copy54`, survives two in-place
engine reopens and a real restart of `cadex-operator-review` on its persistent
private-network port 8765. [The receipt](restart69-evidence.json) records the
accepted revision `de9692bd4ee57…`, digest `cd99e3be1555…`, accepted artifact
locator, and every one of its 15 run identities. Fresh visits before and after
select `wren66-final`, with 90 mm feet and 240 points in each reward, loss and
episode-estimate history.

Run with training stopped and the named service already serving this project:

```bash
PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/restart.py \
  "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-wren-copy54" \
  restart69-final > /tmp/restart-evidence.json
```

The helper inventories project files, visits the accepted view and every run
in headless Chromium, restores the saved project through two fresh cadexd
processes, then invokes `systemctl --user restart cadex-operator-review`.
It checks the still-open page recovers without navigation and preserves its
selected run and playing video element. A fresh page revisits all views and
compares their displayed identities, parameters, components, telemetry curves,
checkpoint counts and video descriptions. API comparisons additionally cover
specs, project decisions and all recorded review fields. Current and historical
checkpoint videos play and download with matching SHA-256 identities; both
contain eight seconds of simulation encoded as 8.1 seconds of video.

The final measured restart answered after **1.05 seconds**. The open page
showed stale at 0.13 seconds and recovered; 2,004 inventoried project files
were checked, excluding this probe's own evidence directory.

The engine's normal restore updates the manifest timestamp and rotates unpinned
candidate attempts: 42 files added and 42 pruned. The accepted revision, digest,
contract, accepted attempt and its bytes remain unchanged, as do all other
project files. The subsequent dashboard restart changes no project file.
The full receipt and screenshots remain under `evidence/restart69-final/` in
the project. Keep those alongside the retained runs and assets when copying it.

This is the headless save contract: accepted scripts and review outputs are
already saved in the project directory by their producing CLI operations.
This probe reopens those existing saved bytes; it performs no new design edit,
acceptance, desktop save operation or training run. Both trainer process lists
are empty. Same-machine private-address evidence does not establish access
from a second device or restart safety during a real GPU run. The automated
lifecycle test separately exercises restart while an independent synthetic
telemetry producer keeps advancing; it now also pins the fresh-visit default
and every run's revision, digest, outcome and video identities across restart.
The service remains running on the working copy afterward.

The subsequent [real-training restart proof](RESTART-TRAINING.md) supplies
the concurrency evidence this retained-artifact check deliberately excluded.
