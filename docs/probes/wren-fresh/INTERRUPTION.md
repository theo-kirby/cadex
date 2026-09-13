# Wren working-copy interruption and retry

Verified against source: 2026-09-13. [Cadex-new]

This probe exercises D8 and D10 on the persistent private-network server,
using the independent 110 mm-foot working copy. It runs two sequential GPU
attempts with the existing offboard environment, seed 0 and 1024 environments.
Each has a 900-second timeout, a 20-second forced-stop grace and a systemd
`MemoryMax=20G` host-memory limit. The first requests 60 iterations but receives
SIGINT after at least iteration 5 and three browser-observed updates. The
second requests 12 iterations and must finish with a saved policy. These are
lifecycle probes, not a trained-gait comparison or verified rollout claim.

```bash
PYTHONPATH=cli:cli/tests OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  pixi run python docs/probes/wren-fresh/interruption.py \
  "$HOME/cadex-projects/ot5-wren-copy54" \
  "http://$(tailscale ip -4):8765/" wren57
```

Use a new prefix to repeat; existing evidence and run directories are refused.
The selected project must have Wren's accepted 110 mm feet and disabled policy,
and already be served on the persistent URL. The probe never launches or stops
the server. Public `cadex export` supplies the model/task bundle, and the
existing run recorder freezes model/spec/document identity before each launch.
It never edits telemetry: `KeyboardInterrupt` reaches the trainer's own failure
publisher, and the supervisor records the deliberate interruption in `run.json`.
The browser must show the failure and CLI retry guidance, never success or an
older video as that attempt's output.

At each start/completion, headless Chromium checks selected run, model revision,
110 mm parameter and eight loaded components on the persistent private URL.
After both outcomes, all four retained older videos are decoded, played through
polls and downloaded with matching hashes. Historical interruption remains
selectable after recovery, and return-to-current selects the retry. All prior
run files and the original Wren project are inventoried and compared afterward.
The original inventory excludes `.git`; artifact retention includes all files
under `runs/`. Keep the entire copy, including both new runs and
`evidence/<prefix>/`, which holds logs, screenshots, signal evidence and receipts.

The guard (ADR-305) refuses an existing Python trainer or pytest process before
launch. It scans `/proc` in a background thread with a requested 50 ms interval,
including during browser calls and the final process wait. Trainer argv is
matched regardless of CPU/GPU options; only the experiment's systemd scope may
contain a trainer, and at most one. Pytest is conservatively excluded because
some tests invoke training in-process. An overlap or scan error is latched,
stops the experiment scope, marks the attempt failed and prevents retry. Each
attempt retains scan count, observed PIDs, maximum trainer count, maximum scan
gap and any violation in `<run>-exclusion.json`. Other processes are never
signalled. Run the CLI and engine suites to completion **before** launching the
probe; the guard is sampled observation, not a host-wide scheduler lock, and
cannot rule out processes shorter than the recorded sampling gap.

Guard regression command (fake processes, no training):

```bash
PYTHONPATH=cli:cli/tests pixi run python -m pytest \
  docs/probes/wren-fresh/test_interruption.py -q
```

## Guarded repeat (iteration 57 — current evidence)

[interruption57-evidence.json](interruption57-evidence.json) supersedes the
previous experiment's exclusion evidence. Both suites finished before either
new trainer started: CLI **397 passed, 1 skipped**, 373.40 s, finished
01:36:24 UTC; engine **2110 passed, 53 skipped**, 253.73 s, finished
01:40:38 UTC on September 13. Guard regressions: **5 passed**. Logs remain
under `evidence/guard57/`; no suite ran during the experiment.

| Attempt | Outcome | Curve samples each | Process scans | Maximum trainers | Maximum scan gap |
|---|---|---:|---:|---:|---:|
| `wren57-interrupt` | SIGINT, exit −2, failed at iteration 5 | 6 | 1,639 | 1 | 59.33 ms |
| `wren57-retry` | exit 0, done at iteration 11 | 12 | 2,789 | 1 | 58.87 ms |

Both preflight checks passed with no existing trainer/test runner; both monitors
reported no violation and observed exactly their own trainer PID. The first
trainer started at 01:41:24 UTC and exited before the retry started at
01:43:02 UTC. Launch-to-browser completion took 88.740 / 150.793 s;
sampled peak host memory was 4,998,832,128 / 5,483,139,072 bytes. Both used
the enforced 20 GiB cap and 900-second timeout. The final policy is 49,095
bytes, SHA-256 `a232fec18df3ed7621e13f966302adeeab23259039cb0ab4a6ea2d09f09d9814`.
It passed the trainer-local witness check; no new engine verification, rollout,
video or gait-quality claim is made. The known JAX cast warning remains.

The persistent browser checked both starts and terminal outcomes, selected
the failed interruption without substituting old output, then selected the
completed retry. All eight old-video checks passed full decode, playback
through polling and download hashes. Deliberate historical selection survived
refresh and returned to current. Start/terminal screenshots were inspected.
All **362 prior run files** (including every earlier attempt) and **963
original Wren files excluding `.git`** remained byte-identical. New artifacts
and raw receipts are retained in `runs/wren57-*` and `evidence/wren57/`.
The previous compact receipt remains unchanged as historical evidence.

Port 8765 remains running on **ot5-wren-copy54**, default **wren57-retry**,
revision `5b61ef31ff134f0f31b079347d9e5d3fd6aec236f12ad9c7b45910640388d7e6`.
A fresh private-address browser check after completion confirmed this identity
and done telemetry. This is a same-machine private-network test.

## Historical iteration 56 (superseded exclusion evidence)

Two first-draft probe failures are retained separately. `wren56-interrupt`
stopped its supervisor at a PID-selection assertion because `/usr/bin/timeout`
also carried the trainer script argument; inspection identified the Python PID
and SIGINT interrupted it at iteration 23. `wren56b-interrupt` correctly sent
SIGINT at iteration 5 but asserted the run note before the next browser poll.
Its later completed-page check showed failure, six retained telemetry samples
and retry guidance. The final probe selects the Python executable explicitly
and waits for the run note independently of telemetry. These were test defects;
no project history or telemetry was patched to hide them.

The initial concurrent CLI-suite run included three small CPU toy-training
invocations (one iteration, four environments) while a GPU attempt was active.
This violated the charter's one-training-at-a-time constraint, despite only one
GPU trainer running. Future iterations must run the CLI suite separately from
live training. No throughput or isolation claim is based on those overlapping
windows. No dependencies, product behavior or visual style changed.


The earlier browser experiment passed; [interruption-evidence.json](interruption-evidence.json)
contains the compact receipt and screenshot hashes. `wren56c-interrupt` exits
on SIGINT (supervisor return −2) at iteration 5, retaining six points in each
of the three curves. Its measured launch-to-browser completion time is 96.717 s,
with sampled peak host memory 5,004,201,984 bytes. `wren56c-retry` exits 0 at
iteration 11, retaining 12 points in each curve; launch-to-browser completion
is 153.874 s and sampled peak host memory 5,488,803,840 bytes. Both report GPU
execution and have enforced 21,474,836,480-byte host caps. Compilation initially
appears as stale telemetry; the page accurately says that stale data does not
prove interruption. The retry then reaches `done` without a page reload.

The saved retry policy is 49,137 bytes, SHA-256
`f96f80229e9c85e7a4f219da992f221d403527026c95922658143b82e7993042`.
The trainer's local witness self-check passed; this probe did not import or
independently verify that policy through an engine rollout, nor produce a new
video. Its final batch reward/step is 0.136326, loss 8.231127 and episode-length
estimate 99.9024 steps, not measured survival. Initialization emitted the known
JAX overflow-cast warning and optional Warp import notices; training exited 0.

The persistent browser fresh visit selects the latest attempt at both failed
and successful boundaries. All eight video checks (four after each outcome)
passed full decode, playback preservation across three refreshes and downloaded
hash verification. Historical interruption selection survives refresh and
returns to the current retry. All **294 pre-existing run files**, including the
two earlier probe attempts, and **963 original-project files excluding `.git`**
remain byte-identical. Port 8765 remains active on the copy, accepted revision
`5b61ef31ff134f0f31b079347d9e5d3fd6aec236f12ad9c7b45910640388d7e6`,
digest `b04439061b0278903fca11079ff0937dac12425a5a8b767e675e24542c7a4ea4`.
Start and completion screenshots were inspected. No new D11 comparison or
product-agent revision authorship is claimed.

Verification: `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run test-engine`
passed **2110 tests, 53 skipped** in 268.29 s; the same environment with
`pixi run python -m pytest cli/tests` passed **397 tests, 1 skipped** in
401.77 s. Full suite logs remain under `evidence/wren56/`; the corrected real
browser lifecycle above passed under `evidence/wren56c/`. No build was needed.

The first retry completion screenshot caught the same publication race: telemetry
was `done` while the run badge still showed its prior `running` record. The
final `check_terminal` helper waits for both the telemetry state and terminal
run badge. It was re-executed on both retained real outcomes: `failed`/`failed`
for interruption and `completed`/`done` for retry, with new terminal-confirmed
screenshots. Both screenshot generations remain retained; the initial one is
transitional, not evidence of the final badge. The compact receipt includes
these explicit terminal browser assertions.
