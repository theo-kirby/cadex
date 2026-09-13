# Wren product-agent revision attempt

Verified against source: 2026-09-13. [Cadex-new]

## Current attempt and review fix: iteration 61

One bounded product-agent turn again returned the provider session-limit error
before authoring. Wren's product-agent revision gap remains open. Following the
critic's fallback, this iteration fixes a demonstrated review defect instead:
live polls closed an open design document every two seconds (ADR-306).

Headless-browser regressions fail on the old code for both accepted and
historical documents. Loaded documents now remain visible across polls, identify
their explicit refresh behavior, and clear when the selected view/revision
changes. Opening one preserves deliberate reading when a newer run arrives;
return-to-current resumes following. Superseded document fetches cannot replace
a newer document. Live telemetry continues polling.

The persistent private-network server on port 8765 remains on
**ot5-wren-copy54**, default **wren57-retry**, accepted/playback revision
`79f86c69bfc3…`. Browser checks read current, accepted and historical
`wren2-final` decisions through 6.5 seconds of automatic polling each, then
returned to current. The retry video also played across three polls, downloaded
with its recorded hash, and decoded to 81 frames at 10 fps (8.1 encoded seconds,
eight simulation seconds). All 465 prior run/asset files remain byte-identical.
No new geometry, training or gait claim accompanies the provider refusal.
These are same-machine private-address checks, not a second-device test.

[document61-evidence.json](document61-evidence.json) retains compact evidence.
The full prompt, refusal envelope, original file inventory, browser probe,
screenshots and suite logs remain project-local in `evidence/agentrev61/`.
Retain them with the whole project. No new dependency or build was needed;
this unit changes the CLI dashboard only.

Verification: `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run python -m
pytest cli/tests` passed **400 tests, one skipped** in 381.31 s. The final
three document regressions passed in 4.12 s after adding the delayed-response
case. The sequential `pixi run test-engine` with the same thread bounds passed
**2110 tests, 53 skipped** in 253.28 s. No experiment training overlapped them.

## Historical attempt: working copy, iteration 58

The product-agent revision remains blocked by provider capacity. One real
`cadex -p` turn on **`ot5-wren-copy54`**, using its stored `claude-sonnet-5`
preference, exited 1: “You've hit your session limit · resets 10:40pm
(America/New_York)”. This is the provider's reported reset time, not a promise
that another attempt will succeed. No accepted revision or outputs were
returned. No fallback was attempted: the earlier attempt below already found
the same limit on both stored and fallback models. No training was started.

The prompt supplied the retained comparison report: original final-policy
falls in two of five seeds, revised final survival in all five eight-second
episodes, small displacement and standing poses. It asked the product agent
to inspect the current effective parameters, choose and accept **one** geometry
change, explain its hypothesis and tradeoff, keep `policy_on=0`, preserve task
settings and history, and return its own `DECISION:` and `NOTE design-specs:`.
The 110 mm working-copy foot length was explicitly identified as an isolation
test. The caller did not choose a replacement dimension after the refusal.

[agent58-evidence.json](agent58-evidence.json) records the refusal, prompt
hash and successful preservation/browser checks. All **434 run and asset
files** match the pre-attempt inventory. Accepted revision `5b61ef31ff13…`,
digest `b04439061b02…`, effective parameters, declared specs, script text and
project decisions/progress are unchanged. Reopen metadata is not asserted
byte-identical. The complete prompt, CLI envelope, stderr, inventory, verifier,
screenshots and test logs stay in the copy's `evidence/agentrev58/` directory.
Retain that directory with the whole project.

The persistent private-network URL on port 8765 still serves the copy and
selects **`wren57-retry`** for a new visit. ACCEPTED NOW loads eight components,
110 mm feet and disabled policy, without substituting an older video. All four
historical checkpoint/final models retain their own revision and digest;
their videos play through three polls and download with matching SHA-256.
Accepted browsing survives polling, and return-to-current selects
`wren57-retry`. The accepted/current screenshots were inspected. The server
remains running. These are same-machine private-address browser checks, not a
second-device test, new training, new video or a new visual-style comparison.

Reproduce the read-only checks while this accepted identity remains current:

```bash
PYTHONPATH=cli:cli/tests pixi run python \
  "$HOME/cadex-projects/ot5-wren-copy54/evidence/agentrev58/verify.py" \
  "http://$(tailscale ip -4):8765/"
```

A future design attempt should use a fresh evidence directory and inventory,
and the public prompt command shown below with the working-copy project path.
Do not overwrite this failed attempt or train an unchanged design under an
agent-authored revision claim. Wren's D9 authorship gap remains open.

Verification: `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run python -m pytest cli/tests` passed 397 tests, 1 skipped in 372.33 s. Then the same environment with `pixi run test-engine` passed 2110 tests, 53 skipped in 253.65 s. Both suites ran sequentially after the refused design turn; no experiment trainer was launched. Full logs and their hashes are retained with the compact receipt. Persistent browser checks and git diff --check pass; hypergraph export/check runs before commit.

## Historical attempt: original project, iteration 53

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
