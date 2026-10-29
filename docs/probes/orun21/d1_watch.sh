#!/bin/bash
# orun21 D1: one bare cadex_train.py run started from a shell, watched in the
# dashboard at launch, mid-run and end (d1_shot.py, 127.0.0.1 only).
#   d1_watch.sh PROJECT RUN NAME TASK [trainer args...]
# Trains TASK into PROJECT/runs/RUN/seed0/ under a 30 GB scope and writes
# docs/probes/orun21/d1-NAME-{launch,mid,end}.png, each shot's page status in
# d1-NAME-*.json beside the run. Launch is shot while the run still compiles
# (state starting, iteration 0 not yet reached); the mid shot starts at MID_PCT
# (default 50) per cent of its iterations: a page loading many CAD parts takes
# a minute, so a fast run wants it earlier.
here=$(cd "$(dirname "$0")" && pwd); repo=$(cd "$here/../../.." && pwd)
project=$1; run=$2; name=$3; task=$4; shift 4
seed=$project/runs/$run/seed0; mkdir -p "$seed"
cd "$project" || exit 1
CUDA_VISIBLE_DEVICES=0 systemd-run --user --scope -q -p MemoryMax=30G \
  ~/cadex-train-venv/bin/python "$repo/training/cadex_train.py" "$task" \
  --out "$seed/policy.cxpolicy" --label "$run" "$@" > "$seed/train.log" 2>&1 &
pid=$!
field() { python3 -c "import json,sys
try: p=json.load(open('$seed/progress.json')); print(p.get('$1',''))
except Exception: print('')"; }
shot() {
  echo "$name $1 shot starts at $(date +%T): iteration=$(field iteration)"
  (cd "$repo" && pixi run -q python docs/probes/orun21/d1_shot.py "$project" "$run" \
     "$here/d1-$name-$1.png" --size 1280x720 --settle 3 $seek) > "$seed/d1-$name-$1.json" 2>&1
  echo "$name $1 at $(date +%T): state=$(field state) iteration=$(field iteration)/$(field total)"
}
until [ -f "$seed/progress.json" ] || ! kill -0 $pid 2>/dev/null; do sleep 2; done
shot launch
total=$(field total)
until [ "$(field iteration)" -ge $((total * ${MID_PCT:-50} / 100)) ] 2>/dev/null || ! kill -0 $pid 2>/dev/null; do sleep 2; done
shot mid
wait $pid; echo "$name trainer rc=$?"
seek="--seek 3"; shot end
