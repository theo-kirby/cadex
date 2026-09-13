---
node_id: 10274f0d-67ed-530c-aa60-294093bcd219
slug: lucid-journey-6875
title: 'Fresh biped authored and probed: creation on the default model, first GPU walk, live dashboard observation'
created_at: '2026-09-12T17:09:06+00:00'
parents:
- shady-bay-0771
summary: ''
---
## What

The fresh biped exists and trained once. After three session-quota refusals,
the product agent authored `ot5-biped` (Reed) on the CLI's default model
with no override, and a bounded 40 × 1024 PPO walk trained on the local GPU,
stored its policy and then failed at the walk's declare leg. The live
dashboard was observed in headless Chromium over the Tailscale address
while that training ran. Evidence is in the project's own history
(`~/cadex-projects/ot5-biped`, commits `04d355a`, `100dfae`, `4e68224`)
and summarised in `docs/HEADLESS-BIPED-REVIEW.md` (commit `d1170dee`).

## Why

The critic's message: first the missing D6 handoff record (done as
`shady-bay-0771`, commit `62626e3e`), then resolve the fresh project's
pre-authoring refusal through the smallest supported CLI correction, create
the biped through the product agent, and start one bounded training probe.
The supported correction is `--model`/`$CADEX_MODEL` (`cli/cadex_cli/agent.py`,
`docs/CLI.md` §2). It was not applied: a one-word probe showed all three
models answering at 12:54 local, before the quoted 2:30pm reset, so the
smallest change was no change, and the default model authored the biped.
Advances D9 (`silent-river-6649`) and gives D3 (`dawn-delta-4361`) its first
real observation. The D3 observation was taken during the probe because the
training was running anyway; it is evidence, not a second unit.

## Method

- Probe: `claude -p "Reply with exactly the word OK." --model <m>` for
  `claude-fable-5`, `claude-opus-5`, `claude-sonnet-5`: all `is_error: false`.
- Creation: `timeout 1500 ./cadex --project "$P" --json -p "$(cat
  $P/evidence/attempt-9.prompt.txt)"`. The prompt asks for a fresh 4-DOF
  sagittal biped in analytic geometry with declared parameters, posed joint
  frames, mid-limb component frames, torque actuators, box collisions, free
  root, ground, a forward task with reset variation, `DECISION:`/`NOTE`
  lines, and forbids imports and training. Exit 0, `ok: true`, accepted
  revision `23c6fe93f47a…`, digest `850acf23a05a…`, 37 tool calls, one
  `write_script`, 164-line script with 42 `assembly.` calls; the agent
  reported zero pose residual and feet on the ground at the keyframe.
- Probe: `XLA_PYTHON_CLIENT_MEM_FRACTION=0.5 /usr/bin/time -v ./cadex walk
  --out runs/probe1 --name probe1.cxpolicy --iterations 40 --envs 1024
  --seed 0 --timeout 1800 --leg-timeout 2400 --json`, with a 5 s sampler of
  trainer/engine RSS and GPU memory. Train leg exit 0 in 182 s (89.5 s of
  training), reward/step 1.211, policy sha256 `01865c8e06aa…` stored, peak
  RSS 5.7 GB, GPU 16.7 GB. Walk exit 3 at declare: no `policy_on` switch.
- Observation: `evidence/probe1_observe.py` ran the real `cadex review
  --host <tailscale> --port 0`, selected `probe1` mid-training, sampled file
  vs page iteration at 0.25 s. Seven page updates (13 → 23) in 12 s on the
  page's own poll, 0.21–1.4 s after each commit, no reload, histories
  growing 14 → 24, state `training`, freshness `live`. Screenshot retained.
- No product code changed; no dependency added. Docs: the evidence doc
  rewritten, one D3 sentence in `docs/CLI.md`, one roadmap entry.
  `git diff --check` clean; doc-pinning tests 62 passed; full CLI suite
  earlier this iteration 353 passed, 1 skipped.

## Result

True now: the fresh biped has an accepted revision, documented specs and
decisions, one stored GPU-trained policy and one failed run record; the
dashboard was seen updating from real training within 1.4 s per commit.
Two defects this lifecycle exposed, both open and both product work for
the next units:

1. **A first walk on an agent-authored project cannot finish.** The system
   prompt asks for the `policy_on` switch only "when a script declares a
   policy"; the fresh script declared none, and the walk's declare leg
   refuses without it. Fix candidates: one design turn adding the switch and
   a placeholder policy, then `cadex walk --out runs/<new>`; or make the
   prompt/walk agree so a fresh project needs no such turn.
2. **A running or failed run has no model identity on the dashboard.**
   `run.json` starts with `identity_source: "not reached"` and null
   revision/digest and keeps them on failure although the train leg
   reported both; the page shows `RELATION UNKNOWN` and no model for the
   run being trained. D3/D5 need the revision recorded from the first leg.

Also noted, not investigated: the trainer's `episode_steps` telemetry
reached 890, 1861 and 10240 on a 400-step task during early iterations.
Assumption recorded: skipping `--resume` on the refused session was
correct, since that session had authored nothing. No rollout, review or
video exists yet, so D2's orbit test, D4, D5–D8 and D9's comparison remain
open. The unreconciled tail is now three records past the checker's mark.

Dispatch closed: 1 unit — fresh biped authored on the default model, first GPU probe run and observed live; two lifecycle defects recorded.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: d1170deefd60c2fc5fcbb9b5c21825372f4a4192

## State Impact

- target: silent-river-6649 — ot5-biped now exists: the product agent authored Reed on the default claude-fable-5 with no model override after three quota refusals (accepted revision 23c6fe93f47a…, digest 850acf23a05a…, 14 parameters, one task reed_walk, ADR-002/003 and design-specs notes in the project). A 40 × 1024 PPO walk trained on the local GPU in 90 s (peak RSS 5.7 GB, GPU 16.7 GB) and stored probe1.cxpolicy (01865c8e…), then failed at declare because the fresh script has no policy_on switch, which the system prompt only asks for once a policy exists. No rollout, review, video or design change yet; retains open.
- target: dawn-delta-4361 — First real observation: during the biped's GPU probe the dashboard, served on the Tailscale address by the real cadex review command, showed seven successive iterations 0.21–1.4 s after each committed progress.json update on its own poll, no reload, histories growing, state training / freshness live (evidence/probe1-observe.json, docs/HEADLESS-BIPED-REVIEW.md). Defect exposed: the run being trained shows RELATION UNKNOWN and no model because run.json starts with null identity. Retains open until the identity defect is fixed and a longer observation exists.
- target: sharp-union-6036 — Demonstrated defect on a real run: runs/probe1/run.json keeps identity_source 'not reached' and null revision/digest after the train leg reported both, so a failed run cannot be tied to its revision on the dashboard.
- target: cool-gate-3332 — One real failed biped run exists: probe1 (walk exit 3 at declare, status failed, error retained, stored policy retained, no rollout); the page labels it 'started and never finished' and names the next CLI action. The controlled interruption and successful new attempt remain untested.
