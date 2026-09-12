# Fresh biped review evidence

Verified against source: 2026-09-12. [Cadex-new]

The project is `ot5-biped` under the operator's `cadex-projects` directory,
outside this checkout, with its own Git history. Nothing was imported from
any older project, mechanism, checkpoint or policy.

## Creation

Three product-agent attempts (`evidence/create.*`, `retry-7.*`, `retry-8.*`)
were refused before authoring: `claude-fable-5` reported "You've hit your
session limit", quoting a reset at 2:30pm America/New_York. The CLI's
documented correction for an unavailable default model is `--model` or
`$CADEX_MODEL` (§2); it was **not needed**. A one-word probe of the default
model succeeded at 12:54 local, before the quoted reset, and the ninth
attempt — the same documented command, no `--resume`, no model override,
prompt retained in `evidence/attempt-9.prompt.txt` — authored the biped:

```bash
timeout --signal=TERM --kill-after=20s 1500 ./cadex --project "$PROJECT" --json \
  -p "$(cat "$PROJECT/evidence/attempt-9.prompt.txt")"
```

Envelope: `ok: true`, accepted revision `23c6fe93f47a…`, digest
`850acf23a05a…`, 37 tool calls, one `write_script`. The script declares
fourteen parameters (`torso_w/d/h`, `thigh_len`, `shin_len`, `limb_w`,
`foot_len/w/t`, `hip_spacing`, `printed_density`, `servo_torque`,
`fall_height`, `episode_s`), seven solids plus a ground plate, revolute hips
(±60°) and one-way knees (0–110°), fixed ankles, a free torso root, box
collisions, four 200 N·mm torque motors, the MJCF `reed_model` and one
training task `reed_walk` (400 steps at 50 Hz, forward axis world +X, fall
below 120 mm ends the episode, reset tilt/lift/stumble variation). The
agent's closing lines landed as ADR-002/003 in the project's `DECISIONS.md`
and `docs/design-specs.md`, `actuators.md`, `sensors.md`: standing height
238 mm, mass 0.651 kg at 1250 kg/m³, success measured as forward
displacement, survival and falls over seeds 0–9. A refused prompt leaves no
progress row; the accepted one is the first row in `PROGRESS.md`.

## The first bounded training probe

```bash
XLA_PYTHON_CLIENT_MEM_FRACTION=0.5 /usr/bin/time -v ./cadex walk --project "$PROJECT" \
  --out "$PROJECT/runs/probe1" --name probe1.cxpolicy --iterations 40 --envs 1024 \
  --seed 0 --timeout 1800 --leg-timeout 2400 --json
```

The train leg ran on the local RTX 5090 from `~/cadex-train-venv`: 40 PPO
iterations × 1024 environments in 89.5 s of training (182 s for the leg
with export and compile), final reward/step 1.211, policy `probe1.cxpolicy`
stored as sha256 `01865c8e06aa…`, `probe1.best.cxpolicy` beside it. Peak
host RSS 5.7 GB, GPU memory 16.7 GB, sampled every 5 s
(`evidence/probe1-memory.log`) — inside the 20 GB bound. The walk then
**exited 3 at its declare leg**: "the script declares no `policy_on=num(...)`
parameter: the walk needs the iterate convention (§2, ADR-192)". The system
prompt asks for the switch only *when a script declares a policy*; the fresh
script declared none, so the first walk on an agent-authored project cannot
finish. `runs/probe1/run.json` is retained as `status: failed` with that
error, the stored policy and the two legs; no rollout, review or video
exists, and `PROGRESS.md` carries the train row only. Next action: one
design turn adding the switch (a placeholder `assembly.policy` behind
`policy_on=0`), then `cadex walk --out runs/<new-name>`.

## Live observation of the real training (D3)

`evidence/probe1_observe.py` started the real `cadex review` command on the
machine's Tailscale address, opened it in headless Chromium, selected
`probe1` while the trainer was iterating and, at 0.25 s, read the trainer's
committed `progress.json` iteration beside the page's. Over 12 s the page
moved 13 → 23 through seven distinct iterations on its own 2 s poll, with no
reload (`performance` navigation count 1); each shown iteration appeared
between 0.21 s and 1.4 s after the trainer's `updated_at`. Reward, loss,
episode length and the reward/loss histories (14 → 24 retained samples)
updated with it; telemetry state `training`, freshness `live`. Results in
`evidence/probe1-observe.json` and a screenshot beside it.

The same observation exposed a review defect, since fixed (ADR-289): **a
run in progress had no model identity.** `run.json` was written at walk
start with `identity_source: "not reached"` and null revision/digest, and
the failed record kept them null although the train leg reported both. The
page therefore showed `RELATION UNKNOWN — no revision recorded for this
run` and `no model to show` for the run being trained, and for the failed
run afterwards, while the accepted-now view showed the biped. Now the walk
records the manifest's revision, digest and specs before its first leg and
each leg's reported identity after it, a failed run keeps the last one it
learned, and a run with no rollout of its own is drawn from the accepted
attempt when — and only when — its recorded revision *and* digest are the
accepted ones now, labelled as borrowed. `probe1`'s record is left exactly
as it was written: records are what the walk said at the time, and the fix
is proven by `cli/tests/test_walk.py` (the record as the train leg saw it,
and after a refusal at train and at declare) and by a headless-browser test
that follows a training run into failure
(`cli/tests/test_review_server.py`). The next real walk on this project is
what ticks the fixture evidence over to real-artifact evidence.

D2's orbit/zoom check on the fresh biped, D4's videos, D5–D9 remain open.
A quota reset time is a provider report, not proof a subsequent attempt
will succeed.
