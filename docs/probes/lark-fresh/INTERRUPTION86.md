# Lark working-copy interruption, retry and retry video (D8, D7, D10)

Verified against source: 2026-09-13. [Cadex-new] Iteration 86, ADR-315.

This is Lark's controlled-interruption evidence, run on the working project
`ot5-lark-copy85` (the product agent's 45 mm-torso revision with the
copy-only 90 mm feet, accepted revision `083d086ad980…`, digest
`4c4171abfa4f…`) on the persistent private-network port 8765, which was
neither started nor stopped and stays running. Two sequential real GPU
attempts under the declared bounds (seed 0, 1,024 environments, a
900-second timeout, a 20-second forced-stop grace and a systemd
`MemoryMax=20G` host limit), then a verified rollout video of the retry's
saved policy. The compact receipt is
[`interruption86-evidence.json`](interruption86-evidence.json), guarded by
`cli/tests/test_lark_fresh_evidence.py`; the raw receipts, trainer logs,
exclusion reports, signal record and screenshots are retained in the copy
under `evidence/lark86/` and the gate logs under `evidence/guard86/`.

```bash
PYTHONPATH=cli:cli/tests OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  pixi run python docs/probes/lark-fresh/interruption.py \
  "$HOME/cadex-projects/ot5-lark-copy85" "http://$(tailscale ip -4):8765/" \
  lark86 "$HOME/cadex-projects/ot5-lark" 40
```

The driver is the [Wren interruption driver](../wren-fresh/interruption.py)
with nothing named after a project: the model and task bundle are found by
kind in the public `cadex export` envelope, the browser is held to every
declared parameter value of the accepted manifest, the component count comes
from the frozen training view, every retained run with a video is re-checked
after each outcome, and the source project whose inventory must not change
is an argument. It adds the final-policy playback branch of
[`train.py`](train.py) so the successful attempt ends with a video, and the
retry's iteration count is an argument (40 here; Wren's retry used 12).
Its trainer-exclusion guard (ADR-305) is unchanged: both suites ran to
completion before either trainer started (CLI **437 passed, 1 skipped**,
07:54:00–08:00:54 UTC; engine **2110 passed, 53 skipped**, 08:00:54–08:05:09
UTC), the experiment ran 08:05:21–08:10:40 UTC, and no suite ran during it.
The Wren guard regression (fake processes, no training) runs against this
driver's copy of the guard by resolving `interruption` from this directory:

```bash
PYTHONPATH=docs/probes/lark-fresh:cli:cli/tests pixi run python -m pytest \
  docs/probes/wren-fresh/test_interruption.py -q --import-mode=importlib
```

It passed (**5 passed**) on the committed tree.

| Attempt | Outcome | Curve samples each | Page samples | Process scans | Maximum trainers | Maximum scan gap | Peak host memory |
|---|---|---:|---:|---:|---:|---:|---:|
| `lark86-interrupt` | SIGINT at iteration 5, exit −2, `failed` | 6 | 4 | 1,655 | 1 | 60.4 ms | 5,001,551,872 B |
| `lark86-retry` | exit 0, `done` at iteration 39 of 40 | 40 | 29 | 3,515 | 1 | 59.6 ms | 5,480,005,632 B |

Both attempts recorded the same training identity (revision `083d086ad980…`,
model `ff77fff92a4b…`, task `cc96d21e52e6…`) frozen before launch, ran on
the GPU, and observed exactly their own trainer PID (3904655, then 3910803)
with no violation. Launch-to-browser completion took 90.7 / 190.8 s.

**The interruption.** After iteration 5 and three browser-observed updates
the supervisor sent SIGINT to the one Python trainer in the scope.
`KeyboardInterrupt` reached the trainer's own failure publisher, which left
six retained samples in each curve and no policy file; the supervisor then
recorded the deliberate interruption in `run.json`. Without a reload the
persistent page showed telemetry `failed — KeyboardInterrupt`, the run badge
`failed`, the note `Controlled interruption: SIGINT after real GPU updates;
start a new cadex walk --out runs/<new-name>.`, the guidance `if the run
stopped, start a new cadex walk`, the six-sample curves, no video, and the
run's own model (eight components); a fresh visit selected `RUN
lark86-interrupt`. All four retained older videos then decoded, played
through polls and downloaded hash-equal — none was substituted for the
failed attempt's output.

**The new attempt.** `lark86-retry` requested 40 updates and finished with
exit 0, `done` at iteration 39, 40 samples per curve, and a saved 55,743-byte
policy (`074e22f1070c…`, trainer witness error 8.4e-8 against a 1e-4
tolerance) recorded as the run's policy asset. The page reached `done` /
`completed` without a reload; a fresh visit selected `RUN lark86-retry`; the
four older videos passed again.

**The retry's video.** The policy was declared in the copy's script through
the public CLI (accepted revision `7f6c23913d55…`, digest `7f0d98163e84…`,
`policy_on` 1), rolled out on seed 0 (engine witness error 8.4e-8, trace
policy digest equal to the file's), rendered in 12.3 s to an 81-frame,
8.1-second WebM (`1f53d43d1c18…`, style `cadex-prototype-light-v1`,
simulation time 8.0 s, `time_limit_reached`, no fall recorded on that one
seed, total reward 194.66) and checked on the persistent URL: full decode
(81 frames), playback surviving three polls, download hash-equal, and the
identity line naming revision, policy digest, seed and simulation time. A
fresh visit selects `RUN lark86-retry-video`; the page's checkpoint list
names the retained `lark86-retry.best.cxpolicy` (iteration 17) as belonging
to training run `lark86-retry`. **No gait claim**: one seed, 40 updates.

**History and isolation.** After the video, deliberately selecting
`lark86-interrupt` still showed `failed`, the interruption note and no
video, survived a refresh, and the return-to-current control selected
`RUN lark86-retry-video`. All **246 prior run files** and **4 prior asset
files** in the copy are byte-identical to their pre-experiment inventories.
The original `ot5-lark` — **1,419 files excluding `.git`** (1,852 with it,
the count [COPY85.md](COPY85.md) reports) — is byte-identical to its
pre-experiment inventory, checked by the driver and once more independently
afterwards. This completes D7's retraining-isolation half on Lark: the copy
has now been retrained and re-declared and the original did not change.

**Persistent dashboard.** Port 8765 stayed on `ot5-lark-copy85` throughout,
was not restarted, and a fresh private-address visit after completion
(`evidence/lark86-retry-video-completion86-browser.json` in the copy)
selects `RUN lark86-retry-video` at revision `7f6c23913d55…` with `foot_len`
90 and done telemetry. Same-machine private-address browser checks; not a
second-device test. No product-agent authorship, no new D11 comparison, no
protocol, payload, engine, shell or dependency change.
