# Wren product-agent revision attempt

Verified against source: 2026-09-12 (2026-09-13 UTC). [Cadex-new]

Iteration 53 attempted the outstanding product-agent revision with the actual
CLI. **No new design was authored.** Both `claude-fable-5` (stored preference)
and the `claude-sonnet-5` fallback returned exit 1 with the provider message
“You've hit your session limit”. Neither returned outputs or an accepted
revision. There is no agent design rationale to report. The earlier 85→105 mm
foot edit remains a caller parameter edit, not product-agent authorship.

The prompt supplied the complete [comparison report](COMPARISON.md) and the
four retained `run.json`/`review.json` records, 47,725 characters altogether.
It asked the product agent to choose one geometry change, preserve histories,
disable the old model-bound policy, retain task settings, and return its own
`DECISION:` and `NOTE design-specs:` rationale. The caller did not select a
dimension or write a replacement script after the refusal.

## Invocation and retry

From the checkout, the attempted invocation was:

```bash
timeout --signal=TERM --kill-after=10s 900 ./cadex \
  --project "$HOME/cadex-projects/ot5-wren" \
  --out "$HOME/cadex-projects/ot5-wren/evidence/agentrev53/output" \
  --json -p "$(cat "$HOME/cadex-projects/ot5-wren/evidence/agentrev53/prompt.txt")"
```

The second invocation added `--model claude-sonnet-5` and used
`sonnet-output`. Both full envelopes and stderr logs remain in the same
project-local evidence directory. That explicit selection persists in
`agent.json`; the stored preference is now Sonnet. Specify `--model` explicitly
on a future retry if Fable is wanted. Retry only once provider capacity is
available, with a new evidence directory and a fresh run-file inventory. Do
not train an unchanged design and label it as the requested agent revision.

## Preserved state and persistent browser check

[agent-attempt-evidence.json](agent-attempt-evidence.json) records both failed
CLI envelopes' relevant fields, the prompt digest, and the subsequent browser
checks. The persistent private-network server on port 8765 still serves
`ot5-wren`. A fresh visit selects `wren2-final`, revision `26332a5955e3…`,
accepted digest `4a3642fad859…`. No training is active and no new training
attempt exists to select. The provider refusal is a design-turn failure;
this published status explains it without inventing a training run.

The accepted script, revision, digest, parameter values and project decisions
are unchanged. Engine reopen refreshed `script.json.updated_at` and
`latest_candidate.attempt_id`; the latter still describes the same accepted
revision, digest, output count and status. This is identity preservation,
not a claim that the entire manifest is byte-identical.

All **228 files** under `runs/` match their pre-attempt SHA-256 inventory.
The dashboard retains six entries: two training runs and four policy reviews.
The browser loaded each of the four retained review models with eight
components, its own revision/digest and 85 or 105 mm foot meshes, curves and
video policy identity. All four videos played across three explicit polls and
downloaded with their recorded SHA-256. Older revisions were labelled
HISTORICAL. ACCEPTED NOW showed the unchanged 105 mm feet with `policy_on=1`,
and the current-run link returned to `wren2-final`. The accepted screenshot
and four run screenshots, inventory, verifier and full receipts remain under
`evidence/agentrev53`; keep that directory with the project.

The successful verifier is reproducible against the unchanged project with:

```bash
PYTHONPATH=cli:cli/tests pixi run python \
  "$HOME/cadex-projects/ot5-wren/evidence/agentrev53/verify.py" \
  "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-wren"
```

Its first draft incorrectly demanded byte-identical reopen metadata, and its
second retained an obsolete expected default from the iteration-50 probe.
Both assertions were corrected to the stated identity contract and current
run before the complete passing check. No product defect was inferred from
those probe mistakes. This is same-machine private-address browser evidence,
not a second-device test. The service remains active without a restart.

D9's Wren-specific product-agent revision gap remains open. This attempt
establishes a provider-capacity dead end and preserves D5/D10 evidence; it
supplies neither a new geometry hypothesis nor new gait measurements.

## Verification

`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run test-engine`: **2110
passed, 53 skipped**, 260.89 s. With the same environment bounds,
`pixi run python -m pytest cli/tests`: **397 passed, 1 skipped**, 383.10 s.
Full logs remain under `evidence/agentrev53`. The persistent browser check,
compact-receipt consistency check and `git diff --check` passed. No build
was needed for this experiment/report unit; no product code changed.
