# Fresh Lark: create, save, reopen on the persistent dashboard

Verified against source: 2026-09-13. [Cadex-new]

The exhaustion-policy clean-project repeat (charter `docs/…/goal.md`,
ADR-284): a **third** fresh biped project, `ot5-lark`, created by the product
agent in one `cadex -p` turn from an empty directory, with no import, link,
copy or conversation from Reed, Wren or any earlier mechanism, checkpoint or
policy. This unit is bounded to **creation, save and reopen**; training,
recording, revision and retraining follow in later units and are not claimed.

## What happened (iteration 80)

The product agent created and accepted Lark in one fresh conversation
(session `8357686c-ee1b…`, `claude-fable-5`, exit 0, 05:56:53Z to 06:02:03Z
UTC): a 238 mm, 0.596 kg biped of eight solids (`torso`, `thigh_l/r`,
`shin_l/r`, `foot_l/r`, `ground_plate`), eight component links, six joints,
one MJCF model and exactly one training task, accepted at revision
`753cf0cc4600…`, digest `3b704a3fc1c4…`, with **twenty** declared
parameters (the twelve asked for plus `servo_torque_nmm`, `joint_damping`,
`joint_armature`, `joint_friction`, `fall_frac`, `episode_steps`,
`control_hz` and `rollout_seed`; `policy_on` defaults to 0). It returned two
`DECISION:` lines (the project's ADR-002 and ADR-003) and design-spec,
actuator and sensor notes, which the CLI landed as `docs/design-specs.md`,
`docs/actuators.md` and `docs/sensors.md`. The script names no earlier
project or mechanism; `ot5-wren-copy54` (2,392 files), `ot5-wren` (963) and
`ot5-biped` (582) match their pre-creation inventories byte for byte.

The persistent private-network service on port 8765 was deliberately
switched from `ot5-wren-copy54` to `ot5-lark` and verified: project name,
accepted revision, zero runs. **Two review defects were exposed on the
fresh project** ([pre-fix receipt and screenshot](evidence.json)
`after_creation`):

1. **The dashboard refused the accepted attempt.** The page showed
   identity and twenty specs but `no model to show: accepted attempt's
   staging does not belong to the accepted revision`. The attempt's
   directory was named `91b312a2e73d…` — the revision the engine computes
   before the worker runs, over an empty spec cache — while the accepted
   revision includes the collected specs. The attempt's `result.json`
   carried the accepted digest. **Fixed (ADR-311)**: the reader now
   trusts the manifest's pin plus the attempt's digest over the directory
   name, with a regression in `cli/tests/test_review_server.py` that failed
   on the old reader. The service was restarted once, with no trainer
   running, to load it.
2. **The agent's turn retained no tessellation.** After the fix the page
   said `accepted attempt retained no tessellation`: `write_script` never
   asks for `display`. **Not fixed in this unit.** The documented public
   remedy, `cadex render`, republished the accepted attempt under the
   accepted revision with tessellation at unchanged revision and digest.
   Wren's creation had this same shape and its later rebuild hid it.

Then the create/save/reopen probe passed on the persistent URL: the page
loaded in 0.84 s, drew eight components (96 triangles, 41,840 non-background
pixels, style `cadex-prototype-light-v1`), listed all twenty parameters,
three decision headings and six documents, orbited under real pointer drag
and wheel zoom, and was screenshotted. Two fresh engine processes (PIDs
3654714 and 3654760) then reopened the project **in place** with
`matches_accepted: true`, keeping the accepted revision, digest, attempt and
contract and all 28 retained accepted-attempt files byte-identical. After a
poll of the still-open page and a fresh visit, the components, viewer
statistics, parameters, decisions and documents were identical to the
record, the eight served STL meshes and placements were byte-identical, and
the before/after viewport PNGs have the same hash
(`4ab7045fb646…`). Restore replays staged 36 unpinned candidate-attempt files
and the store pruned older unpinned ones; no source, history, document or
accepted-attempt file changed. This is a same-machine private-address
check, not a second-device test, and no training, video or gait claim.


## Commands

The creation turn, from the checkout, with the prompt retained beside its
receipt (the project directory did not exist before this):

```bash
P="$HOME/cadex-projects/ot5-lark"; mkdir -p "$P/evidence"
# write "$P/evidence/create.prompt.txt" (the retained prompt), then:
date -u +%FT%TZ > "$P/evidence/create.started"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 timeout --signal=TERM --kill-after=30s 3600 \
  ./cadex -p "$(cat "$P/evidence/create.prompt.txt")" --project "$P" --json \
  > "$P/evidence/create.json" 2> "$P/evidence/create.stderr"
echo $? > "$P/evidence/create.exit"; date -u +%FT%TZ > "$P/evidence/create.finished"
```

The deliberate working-project switch of the persistent operator service,
from the Wren copy to Lark (the same private address and port; see
[the operator status](../operator-review/README.md)):

```bash
systemctl --user stop cadex-operator-review
systemd-run --user --unit=cadex-operator-review --property=Restart=on-failure \
  --working-directory="$PWD" "$PWD/cadex" review \
  --project "$HOME/cadex-projects/ot5-lark" \
  --host "$(tailscale ip -4)" --port 8765
```

The create/save/reopen probe, against that persistent server, with
pre-creation SHA-256 inventories of the earlier projects (taken **before** the
creation turn started, `.git` excluded, as `{relative path: sha256}` maps):

```bash
PYTHONPATH=cli:cli/tests pixi run python docs/probes/lark-fresh/create_reopen.py \
  "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-lark" create80 \
  --intact "$HOME/cadex-projects/ot5-wren-copy54=/tmp/ot5-wren-copy54-iteration80.json" \
  --intact "$HOME/cadex-projects/ot5-wren=/tmp/ot5-wren-iteration80.json" \
  --intact "$HOME/cadex-projects/ot5-biped=/tmp/ot5-biped-iteration80.json"
```

It never starts or stops a server. It checks the creation receipt (exit 0,
accepted revision equal to the manifest, no `runs/`, no policy asset, and a
script that names no earlier project or mechanism), records the server's
accepted model (every component's name, output, placement and served STL
bytes) and a headless Chromium view of the page (identity, every declared
parameter, the component list, viewer statistics, drawn pixels, real pointer
orbit and wheel zoom), then reopens the project **in place** through two
fresh engine processes with `restore`, asserting the accepted revision,
digest, attempt and contract unchanged and every retained accepted artifact
byte-identical. The still-open page is then polled and a fresh visit made;
both must show the same components, statistics, parameters, decisions and
documents as before, the served meshes and placements must be byte-identical,
and the earlier projects must match their pre-creation snapshots. The compact
receipt is [`evidence.json`](evidence.json), guarded by
`cli/tests/test_lark_fresh_evidence.py`; screenshots stay in the project's
`evidence/create80/`, with their hashes in the receipt.
