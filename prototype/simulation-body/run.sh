#!/bin/bash
# PROTOTYPE (throwaway). Every step of the first look at her Simulation Body.
#   ./prototype/simulation-body/run.sh <round>
# 1. run_body.sh <round>    (the Simulation Body, MuJoCo, numbers: build/first-look/{body.json,clips.json,sim/})
# 2. run_picture.sh <round> (stills, clips, review/first-look/<round>/index.html)
set -euo pipefail
ROUND="${1:?usage: run.sh <round>}"
D="$(cd "$(dirname "$0")" && pwd)"
"$D/run_body.sh" "$ROUND"
"$D/run_picture.sh" "$ROUND"
echo "Open: $(cd "$D/../.." && pwd)/review/first-look/$ROUND/index.html"
