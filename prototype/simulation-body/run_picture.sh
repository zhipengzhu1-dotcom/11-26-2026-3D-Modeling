#!/bin/bash
# PROTOTYPE (throwaway). The picture half of the first look: stills, clips, review page.
#   ./prototype/simulation-body/run_picture.sh <round>
# Inputs (override with env for test data): BODY=build/first-look/body.json CLIPS=build/first-look/clips.json
# Optional: ONLY="dance walk" to render just those clips; RES=100 (percent of 1920x1080); SKIP_STILLS=1; SKIP_CLIPS=1
# Outputs: review/first-look/<round>/{stills/,clips/,index.html}; frames and logs under build/first-look/.
set -euo pipefail
ROUND="${1:?usage: run_picture.sh <round>}"
D="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$D/../.." && pwd)"
B=/Applications/Blender.app/Contents/MacOS/Blender
BUILD="$REPO/build/first-look"
REVIEW="$REPO/review/first-look/$ROUND"
BODY="${BODY:-$BUILD/body.json}"
CLIPS="${CLIPS:-$BUILD/clips.json}"
RES="${RES:-100}"
CHUNK=120          # frames per Blender job: about a minute at 1080p, far under the ten-minute limit
LOGS="$BUILD/logs/$ROUND"
mkdir -p "$REVIEW/stills" "$REVIEW/clips" "$LOGS"

if [ -z "${SKIP_STILLS:-}" ]; then
  if [ -f "$BODY" ]; then
    echo "== stills from $BODY"
    "$B" -b --python "$D/stills.py" -- "$BODY" "$REVIEW/stills" >"$LOGS/stills.log" 2>&1 || { tail -30 "$LOGS/stills.log"; exit 1; }
    grep -E "^STILL" "$LOGS/stills.log"
  else
    echo "== no $BODY: stills skipped"
  fi
fi

if [ -z "${SKIP_CLIPS:-}" ] && [ -f "$CLIPS" ]; then
  # one line per job: name lo hi (T read from each npz without numpy)
  JOBS="$(python3 - "$CLIPS" "$BUILD" "$REPO" "${ONLY:-}" <<'EOF'
import ast, json, os, sys, zipfile
clips_json, build, repo, only = sys.argv[1:5]
only = only.split()
cdir = os.path.dirname(os.path.abspath(clips_json))
for c in json.load(open(clips_json)):
    if only and c["name"] not in only and not (c["name"].startswith("cute") and "cute" in only):
        continue
    npz = next((p for p in (c["npz"], os.path.join(cdir, c["npz"]), os.path.join(repo, c["npz"]),
                            os.path.join(build, "sim", c["name"] + ".npz")) if os.path.exists(p)), None)
    if npz is None:
        print("MISSING", c["name"], file=sys.stderr)
        continue
    with zipfile.ZipFile(npz) as z, z.open("src_frame.npy") as f:
        f.read(8)
        hl = int.from_bytes(f.read(2), "little")  # npy v1 header
        T = ast.literal_eval(f.read(hl).decode("latin1"))["shape"][0]
    for lo in range(0, T, 120):
        print(c["name"], lo, min(T, lo + 120) - 1, T)
EOF
)"
  echo "== clip jobs:"; echo "$JOBS"
  # render chunks, two Blender processes at a time
  echo "$JOBS" | while read -r name lo hi T; do
    rm -rf "$BUILD/frames/$ROUND/$name" 2>/dev/null || true
  done
  echo "$JOBS" | while read -r name lo hi T; do
    printf '%s\0' render "$CLIPS" "$name" "$BUILD/frames/$ROUND/$name" "$lo" "$hi" "$RES" "$LOGS/timing_${name}_${lo}.json"
  done | LOGS_DIR="$LOGS" xargs -0 -n 8 -P 2 sh -c '
      B="$0"; PY="$1"; shift; log="$LOGS_DIR/clip_$3_$5.log"
      # two Blenders starting in the same second race on Blender'"'"'s shared add-on library folder: stagger them
      [ $(( ($5 / 120) % 2 )) -eq 1 ] && sleep 6
      "$B" -b --python "$PY" -- "$@" >"$log" 2>&1 || { echo "FAILED $3 $5"; tail -20 "$log"; }
      grep -E "CLIP DONE|Error" "$log" || true' "$B" "$D/clips.py" || true
  for name in $(echo "$JOBS" | awk '{print $1}' | uniq); do
    fd="$BUILD/frames/$ROUND/$name"
    n=$(ls "$fd"/f_*.png 2>/dev/null | wc -l | tr -d ' ')
    T=$(echo "$JOBS" | awk -v n="$name" '$1==n{print $4; exit}')
    if [ "$n" != "$T" ]; then echo "!! $name: $n of $T frames rendered; see $LOGS"; continue; fi
    case "$name" in cute_*) out="$BUILD/parts/$ROUND/$name.mp4"; mkdir -p "$BUILD/parts/$ROUND";; *) out="$REVIEW/clips/$name.mp4";; esac
    ffmpeg -y -loglevel error -framerate 30 -i "$fd/f_%06d.png" -c:v libx264 -pix_fmt yuv420p -crf 18 -movflags +faststart "$out"
    echo "== $out"
  done
  if [ -f "$BUILD/parts/$ROUND/cute_heart.mp4" ] && [ -f "$BUILD/parts/$ROUND/cute_peace.mp4" ]; then
    printf "file '%s'\nfile '%s'\n" "$BUILD/parts/$ROUND/cute_heart.mp4" "$BUILD/parts/$ROUND/cute_peace.mp4" > "$BUILD/parts/$ROUND/cute.txt"
    ffmpeg -y -loglevel error -f concat -safe 0 -i "$BUILD/parts/$ROUND/cute.txt" -c copy -movflags +faststart "$REVIEW/clips/cute.mp4"
    echo "== $REVIEW/clips/cute.mp4"
  fi
fi

python3 "$D/page.py" "$ROUND" "$CLIPS" "$BODY"
