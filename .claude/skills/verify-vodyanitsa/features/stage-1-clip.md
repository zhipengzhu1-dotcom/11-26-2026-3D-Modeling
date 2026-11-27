# Stage 1 clip

A video of her dancing the whole Reference Motion (35.5 s) from a review camera that follows her around a checkered floor, stamped with the Blender frame and the Build kind, so a human can make an Eye Check of the Build. It has no audio.

## Sub-features

- `clip-preview` renders every second frame at 960x540 and still plays in real time.
- `clip-full` renders all 1066 frames at 1920x1080.
- `clip-range` renders part of the motion with `--start` and `--end`.
- `clip-stamp` shows the Blender frame, a timecode and `STAND-IN BUILD - not the real Build` in every frame.
- `clip-facts` writes `clip.json` with render seconds per frame, settings, camera and ffprobe facts.

## How to get to it (user POV)

- Run `$V clip --run-id "$RUN_ID" --frame-step 2 --res-pct 50` for the preview.
- Run `$V clip --run-id "$RUN_ID"` for full quality.
- Open `review/verify/<run-id>/clip.mp4` in any video player (the human does this; agents probe it and look at frames).

## Driving it with scripts/verify

Preconditions:

- Launch is done for `$RUN_ID` (`READY stand-in Build ...`).
- No other step of the same run is running.

- **Preview clip.** Run `$V clip --run-id "$RUN_ID" --frame-step 2 --res-pct 50`. The last line is `CLIP READY review/verify/<run-id>/clip.mp4: 533 frames, 35.5 s, 960x540, <s>/frame render`.
- **Probe.** Run `ffprobe -v error -show_entries stream=codec_name,width,height,nb_frames,avg_frame_rate -show_entries format=duration review/verify/$RUN_ID/clip.mp4`. It shows `h264`, 960x540, 533 frames, `15/1`, about 35.5 s.
- **Look.** Run `ffmpeg -v error -ss 13.3 -i review/verify/$RUN_ID/clip.mp4 -frames:v 1 build/verify/$RUN_ID/look.png` and open that image. She is mid-dance (at 13.3 s she is crouching), the stamp reads `STAND-IN BUILD - not the real Build`, and the floor is visible.
- **Facts.** Run `python3 -m json.tool review/verify/$RUN_ID/clip.json`. It holds `seconds_per_frame_mean`, `res_pct`, `frame_step` and the ffprobe facts.
- **Full quality.** Run `$V clip --run-id "$RUN_ID"`. `CLIP READY ...: 1066 frames, 35.5 s, 1920x1080`.

## Gotchas

- Lowering `--res-pct` barely speeds EEVEE up: most of the 0.6 to 0.9 s per frame is per-frame overhead. `--frame-step` is the setting that saves time.
- Running `clip` again for the same run replaces `clip.mp4` and `clip.json`.
- The camera follows her smoothed centre and is computed from the whole motion, so it is identical whatever `--start`, `--end` or `--frame-step` you pass; the scan's stills use the same camera.
- The stamped timecode is Blender's (frame / 30, so frame 1066 reads 00:00:35:16), one frame ahead of the clip time. Use the stamped Blender frame number and `(frame - 1) / 30` for the clip time; the scan's times use the same formula.
- The clip uses the imported MMD materials, not the toon look. Judge motion and 穿模 from it, not the look.
- Hair and skirt passing through her body and the floor are expected in the stand-in (no Secondary Physics).
