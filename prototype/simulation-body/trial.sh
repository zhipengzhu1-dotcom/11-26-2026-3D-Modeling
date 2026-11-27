#!/usr/bin/env bash
# PROTOTYPE (throwaway). A quick trial inside an epoch: simulate + score only, in a scratch folder.
# Usage: trial.sh <body source dir> <tuning.json> <name>
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$HERE/../.." && pwd)
SRC=$1; TUNE=$(cd "$(dirname "$2")" && pwd)/$(basename "$2"); T="$REPO/build/first-look/epochs/trials/$3"
mkdir -p "$T"; for f in body.xml body.json body_info.json; do cp "$SRC/$f" "$T/$f"; done
cd "$T"
FIRSTLOOK_DIR="$T" TUNING="$TUNE" FREEZE_INERTIA="$REPO/build/first-look/round1_snapshot/sim_info.json" \
  uv run --with mujoco --with numpy --with scipy python "$HERE/simulate.py" > sim.log 2>&1
uv run --with numpy --with scipy python "$HERE/score.py" "$T" "$T/score"
