# Build from the local model copy

One command makes a Build of her from the model and Reference Motion files on this machine, with no Blender window and no hand edits, and leaves it in the scratch folder for the clip and the scan. Today it is the stand-in Build: the Reference Motion played back on the imported model, with the model's physics deleted.

## Sub-features

- `build-launch` makes one Build for a run id from an empty `build/` folder.
- `build-contract` leaves `build.json` (Visible Mesh, armature, frame range, fps, kind, trailing bones) and a work `.blend`.
- `build-record` copies the Build facts, without local paths, to `review/verify/<run-id>/build.json`.
- `build-missing-model` stops in Doctor with what to download and where to put it when the model or motion is absent.
- `build-standin-label` marks every output of a stand-in run as STAND-IN.

## How to get to it (user POV)

- Run `$V build --run-id "$RUN_ID"` (the Launch step of `../SKILL.md`).
- Run `$V doctor --run-id "$RUN_ID"` to see which Build a run holds.

## Driving it with scripts/verify

Preconditions:

- `$V doctor` prints `DOCTOR OK`.
- `build/verify/<run-id>/` does not exist yet.

- **Launch.** Run `$V build --run-id "$RUN_ID"`. Exit 0; the last line is `READY stand-in Build for run <run-id>: frames 1..1066 at 30 fps`; about 4 s.
- **Contract.** Run `python3 -m json.tool build/verify/$RUN_ID/build/build.json`. It shows `"kind": "stand-in"`, `"vertices": 62015`, `"triangles": 76764`, `"bones": 665`, `frame_start` 1, `frame_end` 1066 and 459 `trailing_bones`.
- **Record.** Run `python3 -m json.tool review/verify/$RUN_ID/build.json`. Same facts, without the `blend` path.
- **Run state.** Run `$V doctor --run-id "$RUN_ID"`. The line `[ok] Build for this run: stand-in Build, frames 1..1066, 62015 vertices` appears.
- **Missing model.** Run `VODYANITSA_MODEL=missing/沃雅妮莎.pmx $V doctor`. Exit 1; the model line reads `MISSING. Download the 【原神】沃雅妮莎 (Vodyanitsa) MMD model ...` and names `沃雅妮莎_by_原神_<download id>/沃雅妮莎.pmx`; the summary is `DOCTOR FAILED: model (local copy)`.
- **Missing model at Launch.** Run `VODYANITSA_MODEL=missing/沃雅妮莎.pmx $V build --run-id "$RUN_ID-x"`, then `$V cleanup --run-id "$RUN_ID-x"`. Exit 1 with `VERIFY-ERROR: model not found ...`; nothing is imported.

## Gotchas

- MMD Tools numbers the Reference Motion from Blender frame 1, not 0: VMD frame 0 is Blender frame 1.
- The stand-in deletes every rigid body and joint. The bones those rigid bodies moved are recorded first as `trailing_bones`; the scan needs that list. A real Build must provide the same list.
- The model's own chest bones (`胸*`) are dynamic in the model, but the scan treats them as body.
- Replacing the stand-in is a change to `launch_build()` in `scripts/verify` only. Do not edit the clip or scan to suit a new Build; meet the contract in `scripts/blender/common.py` instead.
- The motion was made for a taller model, so her feet can miss targets in the stand-in. That is expected and not a Build fault.
