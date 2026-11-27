#!/usr/bin/env bash
# PROTOTYPE (throwaway). Runs the Simulation Body half of the first look:
#   extract (headless Blender) -> body.py -> simulate.py -> body_alone_clip.py -> body_numbers.py
# Usage: run_body.sh <round>        (SKIP_EXTRACT=1 reuses build/first-look/extract/;
#        FREEZE_FROM=<dir> keeps the joints, ranges and gains of the round saved in <dir>, e.g.
#        FREEZE_FROM=build/first-look/round1_snapshot for round 2, so only the solids change)
# Writes only under build/first-look/ and review/first-look/<round>/ (both git-ignored).
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
ROUND=${1:?usage: run_body.sh <round>}
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../.." && pwd)
BL=/Applications/Blender.app/Contents/MacOS/Blender
EX="$REPO/build/first-look/extract"
PY=(uv run --with mujoco --with numpy --with scipy --with pillow python)
mkdir -p "$EX"
cd "$REPO"
if [ "${SKIP_EXTRACT:-0}" != 1 ]; then
  echo "== extract: rest pose and surface"
  "$BL" -b --python "$HERE/extract.py" -- rest "$EX" > "$EX/rest.log" 2>&1
  grep "REST DONE" "$EX/rest.log"
  echo "== extract: motions (5 Blender jobs in parallel)"
  python3 "$HERE/motions.py" "$EX" 5
  rm -rf "$EX/motion"
  pids=()
  for i in 0 1 2 3 4; do
    "$BL" -b --python "$HERE/extract.py" -- motion "$EX" "$EX/batch_$i.json" > "$EX/batch_$i.log" 2>&1 &
    pids+=($!)
  done
  for p in "${pids[@]}"; do wait "$p"; done
  echo "motions extracted: $(grep -h -c 'MOTION DONE' "$EX"/batch_*.log | paste -sd+ - | bc)"
  grep -h "MOTION FAILED" "$EX"/batch_*.log || true
fi
if [ -n "${FREEZE_FROM:-}" ]; then
  FREEZE_FROM=$(cd "$REPO" && cd "$FREEZE_FROM" && pwd)
  export FREEZE_JOINTS="$FREEZE_FROM/body_info.json" FREEZE_INERTIA="$FREEZE_FROM/sim_info.json"
fi
cd "$REPO/build/first-look"  # MuJoCo writes MUJOCO_LOG.TXT into the working folder on warnings
echo "== body"
"${PY[@]}" "$HERE/body.py"
echo "== simulate"
"${PY[@]}" "$HERE/simulate.py" 2>&1 | grep -v "^WARNING\|^$" || true
echo "== body-alone clips"
"${PY[@]}" "$HERE/body_alone_clip.py" "$ROUND"
echo "== numbers"
python3 "$HERE/body_numbers.py" "$ROUND"
