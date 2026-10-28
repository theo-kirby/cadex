#!/bin/bash
# orun21 M0: the closing view's cost alone. run1's Go1 command, 100 iterations, --view-seconds $1.
repo=$(cd "$(dirname "$0")/../../.." && pwd)
cd ~/cadex-projects/orun21-lab/go1
v=$1; out=m0-view/v$v-$2
mkdir -p $out
s=$(date +%s.%N)
timeout 30m flock -n ~/.cache/cadex/training.lock ~/cadex-train-venv/bin/python -I \
  "$repo/training/cadex_train.py" outputs/go1_joystick-task.json --out $out/go1.cxpolicy \
  --iterations 100 --envs 8192 --unroll 20 --epochs 4 --minibatches 32 --hidden 512 256 128 \
  --discount 0.97 --learning-rate 3e-4 --entropy 0.01 --clip 0.3 --max-grad-norm 1.0 \
  --reward-floor 0 --checkpoint-every 0 --seed 1 --view-seconds $v --label "orun21 M0: view $v" \
  2>&1 | while IFS= read -r l; do printf '%.3f %s\n' "$(echo "$(date +%s.%N) - $s" | bc)" "$l"; done > $out/train.log
e=$(date +%s.%N); echo "end_to_end_s $(echo "$e - $s" | bc)" > $out/end.txt
