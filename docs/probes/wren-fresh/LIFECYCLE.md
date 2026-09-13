# Wren: the recorded headless lifecycle

Verified against source: 2026-09-13. [Cadex-new] Iteration 72.

Wren has completed a fresh-project lifecycle through creation, reopen, GPU
training, recorded review, independent copy, interruption/retry, product-agent
revision, retraining and historical review. This report indexes the evidence
and its limits; it does not change the owner's D1–D11 checkboxes. Reed's earlier
[lifecycle report](../reed-lifecycle/README.md) remains separate historical evidence.

The persistent private-network dashboard serves **ot5-wren-copy54**, with
**wren71-final** selected for a new visit: 90 mm feet, playback revision
`e9dee22bc90c428942562eeadf150ef4bcd4ab03d8e9ed96e0f959272cfa22bb`.
It is an inspection client; authoring and training remain CLI operations.
The server is still running, with 18 retained runs and no experiment trainer.
The current run is a restart-reliability repeat, not the common-seed comparison.

## Open the saved work

The existing operator URL is `http://<tailscale-ip>:8765/`; obtain this machine's
address with `tailscale ip -4`. The documented one-project server command is:

```bash
./cadex review --project "$HOME/cadex-projects/ot5-wren-copy54" \
  --host "$(tailscale ip -4)" --port 8765
```

The persistent `cadex-operator-review` user service already owns that port;
opening its URL needs no new server or desktop session. Service setup and
working-copy switching are recorded in [COPY.md](COPY.md). Do not replace a
running service just to read this report.

Select a named run in the browser to see its recorded model, parameters,
document snapshots, curves and videos. Earlier runs are marked HISTORICAL.
The current-run button returns to the latest attempt. Deliberate historical
browsing and playback survive polling. Missing/stale recordings remain labelled;
the browser does not rebuild history from today's script.

## Design and experiment history

1. **Fresh creation, 85 mm feet.** The product agent created `ot5-wren` without
   importing Reed or mg-legs mechanisms, policies or history. Creation reached
   acceptance but ended on a provider session limit, so that exit alone was
   not a completed documentation turn. [Creation/reopen evidence](README.md)
   records the accepted eight components (seven biped solids plus authored
   ground), 12 declared parameters and the later restore-preservation fix.
   `wren1` trained 240 updates; checkpoint 20 survived seed 0, while its final
   fell at 0.46 s. Both have saved, decoded, browser-tested videos.
2. **Caller-authored 105 mm revision.** Review of the backward fall motivated
   increasing heel support through `cadex params`. `wren2` retrained for 240
   updates. [COMPARISON.md](COMPARISON.md) compares both designs on seeds 0–4;
   the revised final fell 0/5 times versus 2/5 for the original. This edit was
   not authored by the product agent. All 114 original run files survived.
3. **Independent 110 mm working copy.** [COPY.md](COPY.md) records the complete
   copy and persistent-server switch to `ot5-wren-copy54`, then the copy-only
   CLI foot edit, engine reopens and review while the original path was
   unavailable. [INTERRUPTION.md](INTERRUPTION.md) records controlled real GPU
   interruption followed by `wren57-retry`, a successful **12-update** attempt.
   Its verified final video was [published afterward](RETRY-VIDEO.md). Earlier
   attempts and four inherited videos remain history; the original is preserved.
4. **Product-agent 110→90 mm revision.** The agent accepted `foot_len=90` and
   `policy_on=0` in iteration 65 (revision `03077ee9eb82…`). Iteration 66
   completed its interrupted documentation turn with six inspections and
   its own project ADR-002 plus `docs/design-specs.md`. Its hypothesis was
   that the longer feet supported standing for reward rather than walking;
   90 mm reduced that support while retaining a margin over 85 mm. The final
   documentation turn exited 3 because it accepted no additional script;
   acceptance belongs to the preceding turn. [REVISION66.md](REVISION66.md)
   records authorship, the bounded `wren66` retraining, verified checkpoint
   publication during training, final recording and common-seed comparison.
   All 465 pre-revision run/asset files matched their inventory afterward.
5. **Saved restart and current repeat.** [RESTART.md](RESTART.md) proves two
   in-place engine reopens and a persistent-service restart with retained real
   artifacts. [RESTART-TRAINING.md](RESTART-TRAINING.md) adds the real GPU
   concurrency proof: `wren71` continued with the same trainer while the
   dashboard restarted and historical `wren66-final` kept playing. This repeat
   finished 240 updates and has checkpoint/final videos. It changed the policy
   asset and whole-script identity, not the 90 mm design. Its seed-0 final
   moved +61.241 mm and survived eight seconds; **wren71 has no five-seed
   comparison in this report**.

## Same-seed results and retained identities

Evaluation used each policy's own retained model, script and task in fresh
scratch projects: seeds **0–4**, **8 s**, **50 Hz**, maximum **400 steps**.
Every evaluated seed-zero trace reproduced the saved trace exactly. Torso X
is final minus initial position, including reset/falling motion, not distance
walked. Survival is simulated duration; falls mean crossing the declared torso
height threshold. The dashboard's batch episode estimate is not survival time.

| Policy | Feet mm | Mean torso X mm | Mean / minimum survival s | Falls / 5 | Playback revision prefix |
|---|---:|---:|---:|---:|---|
| wren1-final | 85 | −10.357 | 4.98 / 0.44 | 2 | `a8073874ab76` |
| wren2-final | 105 | +52.647 | 8 / 8 | 0 | `26332a5955e3` |
| wren57-retry | 110 | +40.137 | 8 / 8 | 0 | `79f86c69bfc3` |
| wren66-checkpoint20 | 90 | +42.724 | 8 / 8 | 0 | `d4a0e73df567` |
| wren66-final | 90 | +55.147 | 8 / 8 | 0 | `de9692bd4ee5` |

The first two rows come from [comparison-evidence.json](comparison-evidence.json);
the last three from [revision66-evidence.json](revision66-evidence.json).
Both receipts include per-seed model/task/policy/trace hashes. The latter's
`protocol.training_iterations=240` describes the revised experiment, **not
wren57-retry**, whose retained training request and 12-point curves establish
12 updates. Thus the 110→90 comparison has unequal training budgets as well
as one training seed per design. Mean total rewards are 214.882, 213.622 and
144.877 for the last three rows. More torso displacement and less reward do
not demonstrate a causal improvement or alternating gait; inspected poses
show standing/shuffling. Poor gait does not invalidate the file lifecycle.

## D1–D11 evidence index

| Criterion | Evidence and scope |
|---|---|
| **D1 — reachable dashboard** | [Fresh browser/reopen receipt](evidence.json), [one-project command](../../CLI.md), and the [current persistent review](lifecycle72-evidence.json). Headless Chromium on this machine through its private address; no second-device test. |
| **D2 — model/spec identity** | [Model refresh proof](MODEL-REFRESH.md), [copy model/spec isolation](COPY.md), and the current receipt: six selected playback models, eight components each, exact revision/digest, foot parameters, retained document text/hash checks and real pointer orbit/zoom. |
| **D3 — live training** | [wren66 observation](REVISION66.md) saw seven real updates within 1.25 s; [wren71 restart receipt](restart71-evidence.json) saw seven within 0.240–1.423 s after commit. Reward/loss/episode histories matched; this is measured polling latency, not a universal guarantee. |
| **D4 — headless policy video** | [wren66](REVISION66.md) and [wren71](RESTART-TRAINING.md) retain engine witness checks, full frame decode/timing, policy/revision/seed/time labels, intermediate playback/download while training remained active, and final recordings. [Video fault tests](../../../cli/tests/test_video.py) inject policy/time/pose/path/encoder failures while an independent heartbeat process continues; this is synthetic concurrency evidence, not a new real-GPU render failure. |
| **D5 — retained design history** | [Common-seed comparison](revision66-evidence.json): 465 old run/asset files unchanged through revision/retraining. The current receipt plays/downloads 85, 105, 110 and 90 mm recordings, compares their own document snapshots and history lengths, and preserves selection through polls. |
| **D6 — save/reopen/restart** | [restart69-evidence.json](restart69-evidence.json): two fresh engine restores, 2,004-file inventory, all 15 then-existing runs and videos. [restart71-evidence.json](restart71-evidence.json): same real trainer PID/start tick, updates 4→14, first newer page update 0.957 s after restart, uninterrupted historical playback. Engine reopen was not tested during training. |
| **D7 — independent copy** | [copy-evidence.json](copy-evidence.json): original unavailable during copy edit/reopen/two-server browser review, complete original inventory unchanged. [interruption57-evidence.json](interruption57-evidence.json) adds copy training/retry with original preservation. Keep the entire project, not just its script. |
| **D8 — interruption/failure clarity** | [INTERRUPTION.md](INTERRUPTION.md): real controlled interruption, failed status with KeyboardInterrupt and next CLI action, then successful retry; older results survived. [Reed missing/partial recovery](../reed-copy/video-recovery.json) and [browser fault regression](../../../cli/tests/test_review_lifecycle.py) are shared-product evidence; missing/partial video injection was not independently repeated on Wren here. |
| **D9 — agent lifecycle** | Creation and ordered steps above; [agent revision](REVISION66.md), retained project ADR-002/design specs, real retraining, both saved videos and the same-seed comparison. The authoring/session-limit and unequal-budget qualifications above are part of this evidence. |
| **D10 — persistent current work** | [Copy switch](COPY.md), [real experiment start/completion](RESTART-TRAINING.md), [operator status](../operator-review/README.md), and current receipt: default wren71-final, 18 runs, historical playback preserved and return-to-current works. Server stays running. |
| **D11 — reference appearance** | [Wren side-by-side assessment](../review-style/README.md#repeat-on-wren-wren57-retry--iteration-64) and [wren.json](../review-style/wren.json): actual reference frame plus light reference renderer, floor/grid, fog/horizon, palette, materials, lighting/contact shadows, fit/close/wide/orbit, and same-pose/camera viewport/video comparison (RGB MAE 1.5044/255). Current recordings retain the same shared style identity. This is the historical **110 mm** comparison, not a new equivalent-framing assessment of the current 90 mm pose. |

## Current browser proof and preservation

Run the read-only probe against the persistent server:

```bash
PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/report.py \
  "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-wren-copy54" lifecycle72-final
```

Use a new evidence name for a repeat; existing evidence directories are refused.
[report.py](report.py) starts neither a trainer nor a server. The committed
[lifecycle72-evidence.json](lifecycle72-evidence.json) records the current default
and the five historical selections in the table, full policy/revision/video
identities, retained document hashes, three curve lengths, download checks,
orbit/zoom and playback/selection preservation across three refreshes per view.
All **703** run/asset files stayed byte-identical across the check. The retry
has 12 points per curve, checkpoint20 has its frozen 19-point snapshot
labelled stale, and
the four final reviews each have 240. The 110 mm snapshot has architecture,
decisions and progress; the 90 mm snapshots also retain the agent's explicit
`docs/design-specs.md`. Missing historical domain documents are not supplied
from today's project. Screenshots and the raw receipt stay in the working project's
`evidence/lifecycle72-final/`. The report's evidence guard checks its numbers against
the committed per-seed rows and browser receipt.

Retain the entire project including hidden history, accepted artifacts,
`assets/`, all `runs/` inputs, progress, checkpoints, policy receipts, traces,
video metadata/files and `evidence/`. Copy only with writers stopped, using
[COPY.md](COPY.md); a filename or this compact report cannot replace its bytes.
Opening historical results is read-only. New browser evidence does not re-accept
geometry or rewrite the saved recordings.

## Remaining acceptance limits

The lifecycle claims have evidence; the owner judges acceptance. A stricter
Wren-only acceptance of missing/partial-video fault injection still needs that
specific repeat; the report currently cites the shared product's real Reed
fault test. D11's full visual comparison is historical at 110 mm, while the
current 90 mm recordings reuse that verified renderer/style; this iteration
checks access and identity, not a fresh side-by-side similarity assessment.
Neither gap calls for another training repeat. No second-device reachability,
equal-budget causal design study, five-seed wren71 result or walking gait is
claimed. No new dependency or product behavior was introduced.

## Verification of this report

The persistent browser probe passed for all six views. The report guard passed
3 tests; the full CLI suite passed **419 tests, one skipped** in 412.96 s,
and the engine suite passed **2,110 tests, 53 skipped** in 262.33 s. Both ran
with `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1`. The first engine invocation
ended with signal 15 at the lifecycle-test stage without a pytest failure
report; an isolated `setsid env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run test-engine` rerun passed. Its termination cause was
not established. Logs are retained in `evidence/lifecycle72-final/`. No build
was needed for this documentation/probe/test unit.
