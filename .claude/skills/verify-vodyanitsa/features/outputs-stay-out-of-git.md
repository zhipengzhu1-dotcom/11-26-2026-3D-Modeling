# Model-derived files stay out of git

The model forbids redistribution and the repo is public (docs/adr/0002), so nothing made from the model or the motion may land where git could track it. The helper refuses such writes, Doctor fails if git sees such a file, and Cleanup removes scratch while keeping the evidence in the git-ignored `review/` folder.

## Sub-features

- `guard-refuse` refuses to write model-derived output to any path inside the checkout that is not git-ignored.
- `guard-allow` allows git-ignored paths (`review/`, `build/`, `renders/`, `assets/`) and paths outside the checkout.
- `doctor-leaks` fails Doctor when git (tracked or untracked, not ignored) sees a model, motion, `.blend`, image, video or array file, or anything under the derived folders.
- `cleanup-keeps-evidence` deletes `build/verify/<run-id>/` and stops only our own Blender job, never touching `review/verify/<run-id>/`.

## How to get to it (user POV)

- Run `$V guard <path>` to ask whether a path may hold model-derived output.
- Set `VODYANITSA_REVIEW_DIR` or `VODYANITSA_SCRATCH_DIR`; every step checks them before writing.
- Run `$V doctor` for the leak check and `$V cleanup --run-id "$RUN_ID"` at the end of a run.

## Driving it with scripts/verify

Preconditions:

- `.gitignore` contains `/review/`, `/build/`, `/assets/` and the model folder pattern.

- **Refuse a tracked path.** Run `$V guard docs/verify-out/clip.mp4`. Exit 3 and `GUARD REFUSED docs/verify-out/clip.mp4: 'docs/verify-out/clip.mp4' is not git-ignored ...`.
- **Allow the review folder.** Run `$V guard review/verify/x/clip.mp4`. Exit 0 and `GUARD ALLOWED`.
- **Refuse a whole step.** Run `VODYANITSA_REVIEW_DIR=docs/verify-out $V clip --run-id "$RUN_ID"`. Exit 3 with `VERIFY-ERROR: GUARD REFUSED to write model-derived output: 'docs/verify-out/<run-id>' is not git-ignored ...`; `ls docs/verify-out` fails because nothing was created.
- **Leak check.** Run `$V doctor`. The line `[ok] git sees no model-derived file: clean`. If it fails it lists the files; remove them from git, never commit them.
- **Cleanup keeps evidence.** Run `$V cleanup --run-id "$RUN_ID"`. `CLEANUP DONE removed build/verify/<run-id>; evidence kept in review/verify/<run-id>: build.json, clip.json, clip.mp4, moments, numbers.json, report.md`. Then `ls build/verify/$RUN_ID` fails and `ls review/verify/$RUN_ID/moments` lists the stills.
- **Repo state.** Run `git status --porcelain --untracked-files=all`. Only code and docs paths appear; no file from `review/`, `build/` or `assets/`.

## Gotchas

- The leak check flags every tracked image or video. If a hand-drawn diagram ever needs tracking, add an explicit exception in `leaks()` in `scripts/verify`; do not loosen the extension list.
- `git check-ignore` reports a tracked file as not ignored even when a pattern matches it, so a tracked file inside `review/` is refused. That is the intended behavior.
- Cleanup recognises our Blender job by the pid in `build/verify/<run-id>/blender.pid` and a command line naming this skill's scripts. It never kills by name; a human's Blender window is safe.
- Evidence is never deleted by the skill. Remove old `review/verify/<run-id>/` folders by hand when they are no longer needed.
