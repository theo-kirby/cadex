#!/bin/bash
# D1 measurement: a fresh clone of BRANCH, the engine built with no compiler
# cache, and the dashboard's first page fetched. Run it for "before" and
# again for "after"; it prints the numbers docs/probes/orun2/D1-BEFORE.md
# records. Usage: measure_d1.sh <repo-path-or-url> <branch> <scratch-dir>
set -u
SRC=$1; BRANCH=$2; W=$3
D=$W/clone; LOG=$W/d1.log
rm -rf "$D"; mkdir -p "$W"; : > "$LOG"
t0=$(date +%s); stamp(){ echo "$(($(date +%s)-t0))s $*" >> "$LOG"; }
export CCACHE_DISABLE=1
case $SRC in /*) SRC=file://$SRC ;; esac  # force a pack transfer, no hardlinks
stamp start
git clone -q --no-hardlinks --branch "$BRANCH" "$SRC" "$D" >>"$LOG" 2>&1; stamp "clone rc=$?"
cd "$D"
pixi install >>"$LOG" 2>&1; stamp "pixi install rc=$?"
pixi run setup-engine >>"$LOG" 2>&1; stamp "setup-engine rc=$?"
pixi run build-engine >"$W/build.log" 2>&1; stamp "build-engine rc=$?"
mkdir -p "$W/proj"
# After ADR-498 the documented route is `./cadex app` over a projects
# directory; the "before" tree only had the one-project review page.
if ./cadex app --help >/dev/null 2>&1; then
  ./cadex app --projects "$W/proj" --port 8799 >"$W/review.log" 2>&1 &
else
  ./cadex review --project "$W/proj" --port 8799 >"$W/review.log" 2>&1 &
fi
pid=$!
for i in $(seq 1 300); do
  code=$(curl -s -o "$W/first.html" -w '%{http_code}' http://127.0.0.1:8799/ 2>/dev/null)
  [ "$code" = 200 ] && break; sleep 1; done
stamp "first page http=$code bytes=$(wc -c <"$W/first.html" 2>/dev/null)"
kill $pid 2>/dev/null
echo "tracked=$(git ls-files | wc -l)" >> "$LOG"
echo "blob_bytes=$(git ls-tree -r -l HEAD | awk '{s+=$4} END {print s}')" >> "$LOG"
echo "lfs_rules=$(git ls-files | grep gitattributes | xargs -r grep -l "filter=lfs" | wc -l)" >> "$LOG"
echo "compiles=$(grep -c 'Building CXX' "$W/build.log")" >> "$LOG"
du -sb --exclude=.git --exclude=.pixi --exclude=build . | sed 's/^/worktree_bytes=/' >> "$LOG"
du -sb .git .pixi build/release 2>/dev/null >> "$LOG"
stamp done
cat "$LOG"
