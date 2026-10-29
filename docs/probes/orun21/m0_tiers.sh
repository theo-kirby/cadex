#!/bin/bash
# orun21 M0: env steps/s of each model tier in MJX, zero policy, 8192 envs, 100 control steps.
# Uses leon V's tools/train_bench.py from the lab copy (P1 ports it into training/).
lab=~/cadex-projects/orun21-lab; out=$lab/m0-tiers; mkdir -p $out
bench="$HOME/cadex-train-venv/bin/python -I $lab/leon-v/tools/train_bench.py"
run() { # name model
  systemd-run --user --scope -q -p MemoryMax=30G $bench "$2" --envs 2048,8192 --steps 100 --json $out/$1.json > $out/$1.log 2>&1
  echo "$1 rc=$?"
}
run go1 $lab/go1/outputs/go1-model.xml
run leonv-concept $lab/leon-v/runs/concept-d1/outputs/train-model.xml
run leonv-training $lab/leon-v/runs/t0/train-model.xml
run leonv-engine $lab/leon-v/script_artifacts/67b2a28c2f7189a5e2d3e43e35ea9e25ede6d403f059b8436db736c85ebfc2e1/attempt-1793214536907-9ae605683747/outputs/cadex_quad_model-model.xml
run biped-engine $lab/orun9-biped/script_artifacts/18080849bf4949760db64f909b35a2d8999cec7d2cac91c91d839818e4918411/attempt-1792253234383-f6a696cd5605/outputs/model-model.xml
