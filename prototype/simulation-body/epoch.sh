#!/usr/bin/env bash
# PROTOTYPE (throwaway). One scored tuning epoch of the stiff and soft figures.
# Usage: epoch.sh <N> <tuning.json> [<body source dir> | rebuild]
#   The body (solids) is copied from <body source dir> (default: the previous epoch), or rebuilt with body.py
#   when the third argument is "rebuild" (env such as TRIM=1 passes through). Joints, ranges and gains' inertia
#   are always round 1's (build/first-look/round1_snapshot).
# Writes build/first-look/epochs/epoch<N>/ (contract files + tuning.json + sim_diag) and
# review/first-look/epochs/epoch<N>/ (scorecard, numbers, body-alone clips, contact sheets).
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
N=${1:?epoch number}; TUNE=${2:?tuning json}; SRC=${3:-}
HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$HERE/../.." && pwd)
SNAP="$REPO/build/first-look/round1_snapshot"
E="$REPO/build/first-look/epochs/epoch$N"; R="$REPO/review/first-look/epochs/epoch$N"
PY=(uv run --with mujoco --with numpy --with scipy --with pillow python)
mkdir -p "$E" "$R"
TUNE=$(cd "$(dirname "$TUNE")" && pwd)/$(basename "$TUNE")
cp "$TUNE" "$E/tuning.json.new"; mv "$E/tuning.json.new" "$E/tuning.json"
cd "$E"   # MuJoCo writes MUJOCO_LOG.TXT into the working folder on warnings
if [ "$SRC" = rebuild ]; then
  FIRSTLOOK_DIR="$E" FREEZE_JOINTS="$SNAP/body_info.json" "${PY[@]}" "$HERE/body.py" | grep -v "^head as" | cut -c1-120
else
  [ -z "$SRC" ] && SRC="$REPO/build/first-look/epochs/epoch$((N - 1))"
  for f in body.xml body.json body_info.json; do cp "$SRC/$f" "$E/$f"; done
fi
FIRSTLOOK_DIR="$E" TUNING="$E/tuning.json" FREEZE_INERTIA="$SNAP/sim_info.json" "${PY[@]}" "$HERE/simulate.py" | grep -v "^WARNING\|^$" | tail -1
uv run --with numpy --with scipy python "$HERE/score.py" "$E" "$R"
FIRSTLOOK_DIR="$E" "${PY[@]}" "$HERE/body_alone_clip.py" "epochs/epoch$N" > "$E/render.log"
FIRSTLOOK_DIR="$E" python3 "$HERE/body_numbers.py" "epochs/epoch$N" > /dev/null
for c in dance cute_peace; do
  ffmpeg -y -loglevel error -i "$R/body_alone_$c.mp4" -vf "select='not(mod(n\,10))',scale=480:270,tile=6x4" \
    -frames:v 1 "$R/sheet_$c.png"
done
echo "epoch $N done"
