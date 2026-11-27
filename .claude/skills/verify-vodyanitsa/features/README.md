# Vodyanitsa verification map

This directory is the maintained source for verifying what a human gets from a Build of Vodyanitsa (沃雅妮莎): a Build made from the local model copy, a clip of her dancing the Reference Motion, the 穿模 scan that points at moments for an Eye Check, and a repo that never holds anything derived from the model. Read this index before driving, then use the matching feature file as the recipe.

## Baseline preconditions

- Work from the repo root. Set `V=.claude/skills/verify-vodyanitsa/scripts/verify` and one `RUN_ID=$(date +%Y%m%d-%H%M%S)` per run.
- The local model copy is at `沃雅妮莎_by_*/沃雅妮莎.pmx` (or `VODYANITSA_MODEL`), and the Reference Motion at `assets/motion/toki-yo-tomare/時よ止まれ.vmd` (or `VODYANITSA_MOTION`). Both are git-ignored.
- `$V doctor` prints `DOCTOR OK`. Do not drive while it fails.
- Run only one step of a run at a time: each step owns `build/verify/<run-id>/blender.pid` while it runs.
- Today the Build is the STAND-IN described in `../SKILL.md`. Every proof says so.

## Driving conventions

- Start every recipe from a fresh run id with Launch done (`$V build --run-id "$RUN_ID"`), unless its preconditions say otherwise.
- Use the stable handles the helper prints: the `READY`, `CLIP READY`, `SCAN READY`, `REPORT READY`, `CLEANUP DONE`, `DOCTOR OK` and `GUARD REFUSED` lines, and the file names under `review/verify/<run-id>/`.
- Frame numbers are Blender frames 1 to 1066; clip time is `(frame - 1) / 30` s.
- End every run with `$V cleanup --run-id "$RUN_ID"`, including failed runs. Cleanup never removes evidence.

## Proof and skip reporting

- A proof names the run id, the commands and options used (preview or full quality), and the evidence paths.
- Clip proof: `ffprobe` facts of `clip.mp4` and an Eye Check of at least two stills or frames.
- Scan proof: the numbers from `numbers.json` (frames scanned, flagged events per kind, the ten worst with time, kind, parts and depth), plus an Eye Check of two or three stills.
- Repo proof: `git status --porcelain --untracked-files=all` after Cleanup, and `$V doctor` still `DOCTOR OK`.
- Always list what was not measured (kinds 1 and 4, collision shapes) and what the stand-in does not prove. Never report partial coverage as full coverage, and never report the scan as a pass.
- A step that could not run is reported with its command and the unmet precondition, not proved through another path.

## Feature entry contract

Each feature file starts with an H1 title and one paragraph describing the behavior a human relies on. It then uses exactly four H2 sections in this order: `Sub-features`, `How to get to it (user POV)`, `Driving it with scripts/verify`, `Gotchas`. The driving section starts with `Preconditions:` and pairs each action with an exact command and the observable result.

## Features

- [Build from the local model copy](./build-from-local-copy.md) covers Launch, the Build contract and the missing-model failure.
- [Stage 1 clip](./stage-1-clip.md) covers the preview and full-quality clip of the whole Reference Motion.
- [穿模 scan](./chuanmo-scan.md) covers the Measured Check of Overlaps, the ten worst moments and their stills.
- [Model-derived files stay out of git](./outputs-stay-out-of-git.md) covers the guard, the doctor leak check and Cleanup keeping evidence.
