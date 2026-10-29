#!/usr/bin/env bash
# S1's closing measure: the two representative iterations, spec change to
# judged policy, each stage timed (orun21 ITERATION.md §9). Runs on lab copies
# only. Usage: s1_iteration.sh LAB_DIR
#   concept: leon V's frozen spec, the chest raised to the CAD's mass ->
#            concept -> relay the export's trot task -> train -> judge
#   cad:     one script param edited -> accept (build) -> export -> compare
#            -> cut (with its fidelity check) -> relay -> train -> judge
set -u
LAB=${1:?lab dir}; OUT=$LAB/s1-iter; mkdir -p "$OUT"
REPO=$(cd "$(dirname "$0")/../../.." && pwd)
PY=$HOME/cadex-train-venv/bin/python; TR=$REPO/training; CX=$REPO/cadex
SRC=$LAB/leon-v; C=$OUT/leonv-cad
TIMES=$OUT/times.txt

stage() {  # stage NAME COMMAND... : time one stage into times.txt
  local name=$1; shift
  local t0; t0=$(date +%s.%N)
  "$@" > "$OUT/$name.out" 2> "$OUT/$name.err"; local rc=$?
  local t1; t1=$(date +%s.%N)
  printf '%s\t%s\t%.1f\trc=%s\n' "$name" "$(date -Is)" "$(echo "$t1 - $t0" | bc)" "$rc" | tee -a "$TIMES"
  return $rc
}
built() { ( ulimit -v 16000000; "$@" ); }  # FreeCADCmd under 16 GB
# The judge is not under ulimit -v: its film's headless browser reserves more
# address space than that; its engine workers keep the project's 6 GB budget.
gpu() { systemd-run --user --scope -q -p MemoryMax=30G "$@"; }
train() {  # train DIR [--cad-model XML]
  local d=$1; shift
  gpu "$PY" "$TR/cadex_train.py" "$d"/outputs/trot-task.json "$@" \
    --out "$d"/screen/policy.cxpolicy --seed 0 --envs 8192 --iterations 300 \
    --checkpoint-every 100 --label "s1-$(basename "$d")"
}
staging() { python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['accepted_attempt']['staging'])" "$C/script.json"; }

# The CAD project starts as an accepted leon V with warm caches; this
# engine's part-cache fingerprint changed at ADR-850, so warm it first.
# Not part of either iteration.
[ -d "$C" ] || cp -a "$SRC" "$C"
stage cad-0-warmup built "$CX" export --project "$C" --format brep --rebuild --out "$OUT/warmup-export" --json
TASK=$C/$(staging)/outputs/trot-task.json

# Concept route.
K=$OUT/concept; mkdir -p "$K"
stage concept-1-spec "$PY" "$TR/cadex_concept.py" "$SRC/concept/leon-v-frozen.json" \
  --set trunk.0.boxes.0.mass=10.72 --out "$K/concept.xml" --report "$K/concept.json"
stage concept-2-relay "$PY" "$TR/cadex_relay.py" "$TASK" "$K/concept.xml" --out "$K/relay"
stage concept-3-train train "$K/relay"
stage concept-4-judge "$CX" evaluate --project "$C" --task trot \
  --weights "$K/relay/screen/policy.best.cxpolicy" --out "$K/judged" --json

# CAD route.
D=$OUT/cad; mkdir -p "$D"
sed -i 's/panel_gap=num(3.0,/panel_gap=num(3.5,/' "$C/script.py"
grep -q 'panel_gap=num(3.5,' "$C/script.py" || { echo "edit did not apply" >&2; exit 2; }
stage cad-1-accept built "$CX" script --project "$C" --set "$C/script.py" --json || exit 3
EXP=$C/$(staging)/outputs/cadex_quad_model-model.xml
TASK=$C/$(staging)/outputs/trot-task.json
stage cad-2-export built "$CX" export --project "$C" --format brep --out "$D/export" --json
stage cad-3-compare "$PY" "$TR/cadex_cad_vs_concept.py" "$K/concept.xml" "$EXP"
stage cad-4-cut "$PY" "$TR/cadex_training_model.py" cut --project "$C" --out "$D/cut.xml" --json "$D/cut.json"
stage cad-5-relay "$PY" "$TR/cadex_relay.py" "$TASK" "$D/cut.xml" --out "$D/relay"
stage cad-6-train train "$D/relay" --cad-model "$EXP"
stage cad-7-judge "$CX" evaluate --project "$C" --task trot \
  --weights "$D/relay/screen/policy.best.cxpolicy" --out "$D/judged" --json
