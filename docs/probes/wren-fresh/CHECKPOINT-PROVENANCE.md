# Checkpoint provenance on playback runs (iteration 67, ADR-309)

Verified against source: 2026-09-13. [Cadex-new]

The final-policy playback `wren66-final` copied the trainer's progress snapshot
beside its rollout, so its telemetry listed all twelve `wren66` checkpoints as
`missing`: the files live under `runs/wren66/train`, which the playback record
names as `training.requested.source_run`. The review server now resolves a
checkpoint in the run's own `train/` first, then through that recorded training
run inside the same project, and the page names the provenance state
(`none`, `resolved`, `missing`, `refused`) and where each checkpoint was found
(`docs/CLI.md`, ADR-309).

`checkpoints.py` checks one run on the persistent server without starting or
stopping anything:

```bash
URL="http://$(tailscale ip -4):8765/"; P="$HOME/cadex-projects/ot5-wren-copy54"
for r in wren66-final wren66-checkpoint20 wren57-retry; do
  PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/checkpoints.py "$URL" "$P" $r checkpoint67
done
```

The service was restarted once beforehand (`systemctl --user restart
cadex-operator-review`), with no trainer running, to load the change; the port
answered within one second. [`checkpoint67-evidence.json`](checkpoint67-evidence.json)
is the compact receipt; the full per-run JSON and screenshots are project-local
under `evidence/`.

| run | relation | telemetry | provenance | checkpoints |
|---|---|---|---|---|
| `wren66-final` (default) | CURRENT, `de9692bd4ee5…` | done, iteration 239 | resolved via `wren66` | 12 retained, all from `wren66` |
| `wren66-checkpoint20` | HISTORICAL, `d4a0e73df567…` | stale (frozen snapshot at iteration 18) | resolved via `wren66` | none listed in that snapshot |
| `wren57-retry` | HISTORICAL, `79f86c69bfc3…` | done, iteration 11 | none (trained in place) | 1 retained, own run |

Each check returned to `RUN wren66-final`. Limits: same-machine private-address
observation; the checkpoint-20 playback's snapshot was copied before the trainer
wrote its first checkpoint entry, so its empty list and `stale` label describe
that retained file truthfully — the page does not borrow the training run's
later snapshot. Copy isolation and the refused/missing states are covered by
`cli/tests/test_review_server.py` on fixtures, not on this project.
