#!/bin/bash
# orun21 M0: a cold and a warm rebuild of one lab project, timed.
#   m0_build.sh PROJECT NAME [reaccept]   (PROJECT under ~/cadex-projects/orun21-lab/)
# reaccept: first re-accept the project's own script.py (`cadex script --set`),
# for a project whose stored digest the current engine no longer reproduces.
# Copies the project to m0-build/NAME, drops its part and fit caches (cold),
# runs `cadex export` on the accepted script, then runs it again on the caches
# the first run left (warm). Each FreeCADCmd under ulimit -v 16000000.
repo=$(cd "$(dirname "$0")/../../.." && pwd)
lab=~/cadex-projects/orun21-lab
src=$lab/$1; out=$lab/m0-build/$2
rm -rf "$out"; mkdir -p "$lab/m0-build"; cp -a "$src" "$out"
rm -rf "$out/script_artifacts/part-cache" "$out/script_artifacts/fit-cache"
ulimit -v 16000000
if [ "$3" = reaccept ]; then
  cp "$out/script.py" "$out/m0-script.py"
  s=$(date +%s.%N)
  "$repo/cadex" script --set "$out/m0-script.py" --project "$out" --json --wait > "$out/m0-reaccept.json" 2> "$out/m0-reaccept.err"
  rc=$?; e=$(date +%s.%N)
  echo "$2 reaccept rc=$rc wall_s=$(echo "$e - $s" | bc)" | tee -a "$lab/m0-build/times.txt"
  rm -rf "$out/script_artifacts/part-cache" "$out/script_artifacts/fit-cache"
fi
for pass in cold warm; do
  s=$(date +%s.%N)
  "$repo/cadex" export --project "$out" --out "$out/m0-export-$pass" --format brep --json --wait > "$out/m0-$pass.json" 2> "$out/m0-$pass.err"
  rc=$?; e=$(date +%s.%N)
  echo "$2 $pass rc=$rc wall_s=$(echo "$e - $s" | bc)" | tee -a "$lab/m0-build/times.txt"
done
