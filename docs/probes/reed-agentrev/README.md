# Product-agent shin55 revision: authorship, live experiment, comparison

Verified against source: 2026-09-12. [Cadex-new]

The product agent (`claude-sonnet-5`, the project's stored model) authored
Reed's review-driven revision — `shin_len` 80 → 55 mm with the 100 mm feet
kept — and recorded its reasoning as project ADR-007 and a design-specs
entry. One bounded GPU training (240 × 1024, seed 0, checkpoints every 20)
followed on the working copy `ot5-biped-copy29`, observed on the persistent
operator dashboard, with a checkpoint video published while training was
active and a final video afterwards. Ten seeds were then evaluated in an
independent copy. `docs/HEADLESS-BIPED-REVIEW.md` narrates it; this
directory keeps the compact, path-free evidence.

```bash
COPY="$HOME/cadex-projects/ot5-biped-copy29"; URL="http://$(tailscale ip -4):8765/"
timeout --signal=TERM --kill-after=10s 900 ./cadex --project "$COPY" \
  --out "$COPY/evidence/agentrev" --json -p "$(cat "$COPY/evidence/agentrev.prompt.txt")"
PYTHONPATH=cli:cli/tests pixi run python "$COPY/evidence/shin55-experiment.py" "$COPY" shin55 "$URL"
PYTHONPATH=cli:cli/tests pixi run python docs/probes/operator-review/verify.py "$URL" "$COPY" shin55-final
python3 docs/probes/reed-baseline/evaluate.py "$COPY" "$HOME/cadex-projects/ot5-biped-shin55-seeds" \
  --run shin55-final --evidence-directory shin55-seeds
python3 docs/probes/reed-agentrev/summarize.py "$COPY" "$HOME/cadex-projects/ot5-biped-shin55-seeds" \
  > docs/probes/reed-agentrev/evidence.json
```

[evidence.json](evidence.json) records the agent receipt identities, the
training exit/timing/memory, the persistent-URL observation during training
(fresh-visit default selection, page iterations and commit-to-page delays),
the checkpoint publication with its render-window iteration intervals, both
video digests and browser checks, the after-completion and after-restart
operator checks, and the ten-seed rows. Videos, traces, checkpoints,
screenshots and logs stay project-local under `evidence/` and `runs/`; keep
them with the project.

Result, honestly: 6 of 10 seeds survive 8 s at about 45–50 mm forward, 4
fall within 0.9 s. Survival improved against the 70/90 mm designs on the same
seeds; it is not a repeatable walking gait. The render-window measurement is
one same-machine observation with checkpoint publication excluded, not a
general overhead figure. No second device was used.
