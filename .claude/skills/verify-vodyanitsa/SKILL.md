---
name: verify-vodyanitsa
description: "Verify the Vodyanitsa (沃雅妮莎) character Build end to end in headless Blender: run one Build from the local model copy, render the stage 1 clip of her dancing the Reference Motion, run the 穿模 scan (a Measured Check of Overlaps), and keep the clip, the ten worst moments and the numbers in the git-ignored review/ folder. Reach for it after any change to how she is built, before asking the human for an Eye Check, or when you need proof that a Build still works and that nothing derived from the model entered git."
---

# Verify the Vodyanitsa Build

Surface: there is no app window. A Build is made in headless Blender, and its output is what a human looks at: a clip and stills, plus numbers. This skill drives that whole path with one helper, `scripts/verify`, and leaves the evidence in `review/verify/<run-id>/`.

Use the words of `GLOSSARY.md`: Build, Simulated Character, Simulation Body, Visible Mesh, Secondary Physics, Reference Motion, Eye Check, Measured Check, 穿模, Overlap.

## Read this first: today it drives a STAND-IN Build

The repo has no real Build yet. The Launch step therefore runs a stand-in (`scripts/blender/standin_build.py`): it imports her model from the local copy, deletes every rigid body and joint, and plays the Reference Motion back on the armature as keyframes. Everything after Launch (clip, scan, evidence, cleanup) is the real verification and will not change.

The stand-in does these things the real Build will not:

- plays the Reference Motion back exactly, instead of a trained controller trying to follow it with a Simulation Body under gravity;
- has no Simulation Body at all; the scan measures the Visible Mesh only;
- deletes the model's own physics, so hair, skirt, ribbons and pendants are carried rigidly by their bones and pass through her body and the floor a lot (expected; it shows the scan sees faults);
- uses the imported MMD materials under a plain sun, not the toon look; it does switch the face overlays `颜2` and `照れ` to Blended to avoid a dark lace patch on the face.

These stay unverified until a run on a real Build covers them: the Simulation Body; the trained controller; staying upright; drift from the Reference Motion; the toon look; Secondary Physics for hair and dress; Overlaps between collision shapes. Every stand-in report says so in its "What this stand-in run does not prove" section.

The 穿模 scan, version 1, measures only kind 2 (trailing parts through her body), kind 3 (forearm and hand, or shank and foot, through the rest of her body) and kind 5 (anything through the floor). It does NOT measure kind 1 (body through clothing), kind 4 (one trailing family through another, such as hair through skirt), collision-shape Overlaps, or upper arm into torso and thigh into thigh. Never report its output as full coverage, and never as a pass: it points at moments for an Eye Check, and the Eye Check wins.

## Launch

Run every command from the repo root. Pick one run id and keep it for the whole run:

```bash
V=.claude/skills/verify-vodyanitsa/scripts/verify
RUN_ID=$(date +%Y%m%d-%H%M%S)
$V build --run-id "$RUN_ID"
```

Ready means the last line reads `READY stand-in Build for run <run-id>: frames 1..1066 at 30 fps`. That Build is a work `.blend` plus `build.json` under `build/verify/<run-id>/build/` (scratch). It takes about 5 s from an empty `build/` folder; there is nothing to seed and no server to keep alive. Each later step starts its own headless Blender, waits for it, and writes its pid to `build/verify/<run-id>/blender.pid` only while it runs. Teardown is Cleanup.

Inputs come from environment variables with repo-relative defaults:

| Variable | Default |
| --- | --- |
| `VODYANITSA_MODEL` | first match of `沃雅妮莎_by_*/沃雅妮莎.pmx` at the repo root |
| `VODYANITSA_MOTION` | `assets/motion/toki-yo-tomare/時よ止まれ.vmd` |
| `VODYANITSA_REVIEW_DIR` | `review/verify` (evidence; must be git-ignored or outside the checkout) |
| `VODYANITSA_SCRATCH_DIR` | `build/verify` (scratch; same rule) |
| `BLENDER` | `/Applications/Blender.app/Contents/MacOS/Blender` |
| `FFMPEG`, `FFPROBE` | found on `PATH` |

Swapping in the real Build later is a change to `launch_build()` in `scripts/verify` only. It must leave a `build.json` that meets the contract at the top of `scripts/blender/common.py`: the `.blend` path, the Visible Mesh and armature object names, the frame range and fps, `kind`, and `trailing_bones` (the bones its Secondary Physics moves; the scan uses them to tell trailing parts from body). When it does, also delete the stand-in paragraphs above.

## Doctor

```bash
$V doctor                     # machine and checkout
$V doctor --run-id "$RUN_ID"  # plus: does this run have a Build, is a Blender job of ours still running
```

Read-only. It checks Blender 5.x, that MMD Tools enables headless, ffmpeg and ffprobe, the model and the Reference Motion files, that the review and scratch folders are git-ignored, and that git (tracked or untracked, not ignored) sees no model-derived file: no model, motion, `.blend`, image, video or array file, nothing under `review/`, `build/`, `renders/`, `assets/` or the model folder, and no `numbers.json`, `build.json`, `clip.json` or `moment_*` file. It prints `DOCTOR OK` and exits 0, or `DOCTOR FAILED: <names>` and exits 1. On a fresh clone without the model, it fails with exactly what to download and where to put it. Run it first, and again whenever anything looks off. Do not drive while it fails.

## Drive

Two drives follow the Build. Both use the same review camera: it follows her around the floor from the front, slightly above, and every frame carries a stamp with the Blender frame number and the words `STAND-IN BUILD - not the real Build`. Clip time of a Blender frame is `(frame - 1) / 30` s.

The stage 1 clip, the whole Reference Motion (Blender frames 1 to 1066, 35.5 s):

```bash
$V clip --run-id "$RUN_ID" --frame-step 2 --res-pct 50   # preview: 533 frames at 960x540, about 5 min
$V clip --run-id "$RUN_ID"                               # full quality: 1066 frames at 1920x1080, about 13 min
```

`--frame-step N` renders every Nth frame and encodes at 30/N fps, so the clip still plays in real time. `--start` and `--end` (Blender frames) cut a part. It ends with `CLIP READY review/verify/<run-id>/clip.mp4: ...` and the measured seconds per frame.

The 穿模 scan:

```bash
$V scan --run-id "$RUN_ID"                   # every frame, ten stills at 1920x1080, about 2 min
$V scan --run-id "$RUN_ID" --frame-step 2    # quicker preview
```

Defaults are the agreed acceptance bar: Overlap is depth beyond her rest pose; anything under `--noise-mm 2` is noise; an event is flagged when its deepest Overlap the camera can see is at least `--min-depth-mm 10` or it lasts longer than `--min-duration-s 0.1`; `--top 10` worst get stills. It ends with `SCAN READY ...` and `REPORT READY review/verify/<run-id>/report.md`. `$V report --run-id "$RUN_ID"` rewrites the report from the evidence alone.

How the scan measures, so you can judge its numbers:

- Each Visible Mesh vertex takes its dominant bone. It is trailing if that bone, or an ancestor before a body anchor bone, is in `trailing_bones` (the chest bones `胸*` count as body). Otherwise it gets a body region: head, torso, upper arm, forearm and hand, thigh, shank and foot, left and right. Trailing parts are named by material: hair (`髮`), skirt (`裙`), other (ribbons, pendants, plumes).
- The surface things pass through is the solid body: triangles of materials `颜 肌 体 足 鞋 袖` whose vertices are all body. A vertex is inside when its nearest surface point's interpolated normal faces away from it and a ray heading further in leaves through the back of a face. Depth is the distance to that point, minus the same vertex's depth in the rest pose.
- Kind 2 tests trailing vertices against the whole solid body. Kind 3 tests forearm-and-hand vertices against the body without that arm, and shank-and-foot vertices against the body without that leg. Kind 5 tests every vertex against the floor at z = 0.
- An Overlap counts as seen when the clip's camera ray reaches its crossing point within 3 cm and the point is in frame. Unseen Overlaps are kept in `per_frame` numbers but never flagged.

## Evidence

Everything lands in `review/verify/<run-id>/`, which is git-ignored and survives Cleanup:

| File | What it proves |
| --- | --- |
| `clip.mp4` | the stage 1 clip; check it with `ffprobe` and an Eye Check |
| `clip.json` | render settings, seconds per frame, camera, ffprobe facts |
| `moments/moment_NN_t<seconds>s_kind<k>_<part>-<through>.png` | one still per flagged moment, worst first, from the clip's camera at that frame; a magenta ring marks where the deepest visible Overlap crosses |
| `numbers.json` | the Measured Check: frames scanned, every event, flagged events by kind, the ten worst, everything beyond ten, per-frame worst depth per kind, timing, what is not measured |
| `report.md` | the short human-readable account, with the credits, the not-measured list and the stand-in gaps |
| `build.json` | which Build was verified (`kind: stand-in` today), its frame range and size |

Proof standards for a run:

- Exercise the real path: Launch, then clip, then scan, all through `scripts/verify`. Do not call the Blender scripts by hand for a proof.
- Look at the result, not only the exit code: `ffprobe` the clip, and open two or three stills to confirm she is mid-dance (not an empty frame, not her A-pose) and the ring sits on a real crossing.
- Check the side effect that matters most here: after the run, `git status --porcelain --untracked-files=all` must show no file derived from the model, and `$V doctor` must still print `DOCTOR OK`.
- Every output made from the model carries the credits in `report.md`: model by miHoYo, converted by 观海; motion by Kei (@Kei_MMD_); choreography traced from @ellendance; song ILLIT '時よ止まれ (Toki Yo Tomare)'. The clip has no audio.
- Report the stand-in gaps and the not-measured kinds with the numbers, every time.

## Cleanup

```bash
$V cleanup --run-id "$RUN_ID"
```

It stops the Blender job named in `build/verify/<run-id>/blender.pid` only if that pid is still a Blender running one of this skill's scripts, then deletes `build/verify/<run-id>/` (work `.blend`, frame images, logs) and `build/verify/` if empty. It never touches `review/`. It ends with `CLEANUP DONE ... evidence kept in review/verify/<run-id>: ...`. Run it after every run, including failed ones. Never kill Blender by name; other Blender windows may belong to the human.

Old evidence is the human's to delete: `review/verify/<run-id>/` stays until someone removes it.

## Helpers

All in `.claude/skills/verify-vodyanitsa/scripts/`:

- `verify doctor [--run-id ID]`: read-only health check, described above.
- `verify build --run-id ID`: Launch; runs `blender/standin_build.py` today.
- `verify clip --run-id ID [--frame-step N] [--res-pct P] [--start F] [--end F]`: runs `blender/clip.py`, then ffmpeg.
- `verify scan --run-id ID [--frame-step N] [--start F] [--end F] [--top K] [--noise-mm X] [--min-depth-mm X] [--min-duration-s X] [--still-res-pct P]`: runs `blender/scan.py`, then writes `report.md`.
- `verify report --run-id ID`: rewrites `report.md` from `review/verify/<run-id>/`.
- `verify cleanup --run-id ID`: described above.
- `verify guard PATH`: prints `GUARD ALLOWED` or `GUARD REFUSED <reason>` and exits 3 when refused. Every write of model-derived output goes through the same check: a path inside the checkout must be git-ignored. For example `$V guard docs/x.png` is refused and `$V guard review/verify/x.png` is allowed. Pointing `VODYANITSA_REVIEW_DIR` at a tracked folder makes `clip`, `scan` and `build` stop with `GUARD REFUSED` before anything is written.

Blender logs for each step are in `build/verify/<run-id>/logs/<step>.log` until Cleanup; a failed step names its log. The feature map in `features/README.md` lists each user-facing feature with its journey and gotchas.

Measured on an M4 Max (Apple Silicon): Build 3.6 s; clip render 0.53 s per frame at 960x540 and about 0.75 s per frame at 1920x1080 (EEVEE time is mostly per-frame overhead, so `--frame-step` saves far more than `--res-pct`); scan 0.12 s per frame plus 0.9 s per still at 1920x1080. On the stage 1 dance (1066 frames, 35.5 s): Build 4 s, preview clip of 533 frames 4 min 50 s, scan of every frame about 2 min 15 s, so a preview run takes about 7 minutes. A full-quality run (1066 clip frames at 1920x1080) should take about 15 minutes.
