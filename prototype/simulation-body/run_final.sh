#!/usr/bin/env bash
# PROTOTYPE (throwaway). The "final" body and simulations of the first look, from the changes the human accepted:
# round 2's fit without trims, head = skull and face only, simple shoes, elbows 15 deg past straight; soft =
# epoch 2's soft with firm ankles and no feed-forward, stiff = epoch 4's stiff, 5 ms contacts, five carried clips.
# Needs build/first-look/round1_snapshot (joints, gains' inertia) and build/first-look/epochs/final/tuning.json.
# Writes build/first-look/epochs/final/ and review/first-look/final/.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$HERE/../.." && pwd)
E="$REPO/build/first-look/epochs/final"; V="$REPO/review/first-look/final"; SNAP="$REPO/build/first-look/round1_snapshot"
PY=(uv run --with mujoco --with numpy --with scipy --with pillow python)
mkdir -p "$E" "$V"; cd "$E"
FIRSTLOOK_DIR="$E" FREEZE_JOINTS="$SNAP/body_info.json" HEAD_SKULL_ONLY=1 SHOE_SIMPLE=1 ELBOW_PAST_DEG=15 \
  "${PY[@]}" "$HERE/body.py" | cut -c1-160
NO_PINNED=1 FIRSTLOOK_DIR="$E" TUNING="$E/tuning.json" FREEZE_INERTIA="$SNAP/sim_info.json" \
  "${PY[@]}" "$HERE/simulate.py" | grep -v "^WARNING\|^$"
uv run --with numpy --with scipy python "$HERE/score.py" "$E" "$V"
FIRSTLOOK_DIR="$E" "${PY[@]}" "$HERE/body_alone_clip.py" final > "$E/render.log"
FIRSTLOOK_DIR="$E" python3 "$HERE/body_numbers.py" final > /dev/null
for c in dance cute_peace; do
  ffmpeg -y -loglevel error -i "$V/body_alone_$c.mp4" -vf "select='not(mod(n\,10))',scale=480:270,tile=6x4" \
    -frames:v 1 "$V/sheet_$c.png"
done
echo "final done"
