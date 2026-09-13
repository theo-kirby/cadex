# Lark engine kill and restart during real training

Verified against source: 2026-09-13. [Cadex-new] Iteration 109, D6/D10 (ADR-325).

This fills the one D6 gap [RESTART96.md](RESTART96.md) left open: restart the
*engine* during a bounded real GPU run. Cadex has no engine daemon. `cadexd`
is one process per `./cadex` invocation, started, driven over stdio and
stopped by the CLI; the trainer is offboard and reads an exported task bundle;
the dashboard opens no engine. So, through the public CLI alone, the
experiment is one `cadex export` whose engine is SIGKILLed while it is
working, then another `cadex export` that starts a fresh engine — both while
the trainer runs and the persistent page is open. The dashboard service is
not restarted here.

From the checkout, with no trainer or pytest running on the machine:

```bash
PYTHONPATH=cli:cli/tests pixi run python docs/probes/lark-fresh/engine_restart.py \
  "$HOME/cadex-projects/ot5-lark-copy85" "http://$(tailscale ip -4):8765/" lark109-engine2
```

Use a new run name for a repeat. The driver refuses an existing run directory,
exports the model/task, retains the training view, launches 100 PPO updates
(1,024 environments, seed 0) in `MemoryMax=20G` under a 900-second TERM
timeout with 20-second kill grace, and runs the exclusion guard from
[interruption.py](interruption.py) throughout. No dependency was added.

## What was observed (`lark109-engine2`)

The [receipt](engine109-evidence.json) is pinned by
`cli/tests/test_lark_fresh_evidence.py`.

- **Kill.** At page iteration 4 the driver ran `cadex export`; its engine
  child (PID 444248) appeared 0.047 s after the CLI started and had one
  resident worker under it. SIGKILL at 0.455 s. The CLI exited **1** at
  0.463 s with `ok: false`, no outputs, and
  `error: "The engine closed its protocol stream. (exit status -9)"`. Two
  seconds later no `FreeCADCmd` or `CadexGeometryWorker` process remained:
  the resident workers die with their engine.
- **Restart.** The next `cadex export` started engine PID 444342 (different
  start ticks), exited **0** in 1.518 s with 28 staged outputs, reported the
  accepted revision `6f826037044a…` and digest `c039961cd41d…`, and its
  model XML and task bundle were byte-identical to the ones the trainer was
  started from.
- **Trainer.** PID 439475, start ticks 103546924, identical before the kill,
  after the restart and at every one of the guard's 4,959 scans (maximum gap
  0.067 s, no other trainer, no violation). Training completed all 100
  updates on the GPU, exit 0, sampled peak host memory 5,489,143,808 bytes
  under the enforced 21,474,836,480-byte cap; policy
  `9c166417c633…` saved.
- **Open page.** No navigation. Seven newer committed updates (iterations 8
  to 16) appeared 0.197–1.388 s after commit, with reward, loss and
  episode-length histories growing together, freshness `live` throughout.
  A fresh visit during training and after completion selected
  `RUN lark109-engine2`; the completed page read `completed` / `done`.
- **Project.** All 561 earlier files under `runs/` are byte-identical; the
  accepted revision and digest are unchanged; the dashboard unit stayed
  `active` on the same MainPID 428532 throughout.

Two facts recorded rather than hidden. The manifest's `latest_candidate` and
`updated_at` move on every engine open — including the killed one, whose
restore had already rewritten them before the SIGKILL — so `script.json` is
not byte-identical across the experiment; the accepted identity is. And the
run record names `assets/lark109-engine2.cxpolicy`, which this bounded
driver, like the dashboard-restart one, never puts as an asset: the policy
lives under `runs/lark109-engine2/train/` and the panel shows the asset as
missing.

## The first attempt and what it cost

`lark109-engine` ran first on the CLI before this iteration's fix, when the
killed call still reported `(exit status None)` because the client read EOF
before the child was reaped; the client now waits for the exit status
(`cli/tests/test_client.py` pins `-9`). That attempt's kill, restart and
telemetry phases passed, and its training completed, but its receipt was
lost: a pytest subset run on this machine during the completion wait tripped
the driver's own exclusion guard, and the driver re-raised before saving. The
driver now writes its receipt whatever the guard concludes. The run record is
kept as `failed` with that explanation and its saved policy; the driver log
is retained beside it.

## Limits

Same-machine headless Chromium over the private address; no second device.
The "engine restart" is the only one the architecture admits — a killed CLI
call and the next one — and nothing here restarts the dashboard or resumes a
checkpoint. Verification: `pixi run python -m pytest cli/tests` on final
source, **472 passed, 1 skipped in 473.96 s, exit 0**.
