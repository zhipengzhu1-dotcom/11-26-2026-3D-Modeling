# 穿模 scan

A Measured Check that finds Overlaps on her Visible Mesh frame by frame, keeps only those the clip's camera could see, groups them into events, and hands a human the ten worst moments with a still of each, ranked, plus every other flagged moment as a list. It never declares a pass; the Eye Check wins. Version 1 measures kinds 2, 3 and 5 only.

## Sub-features

- `scan-kind2` trailing parts (hair, skirt, other) inside her solid body surface.
- `scan-kind3` forearm and hand inside the body without that arm; shank and foot inside the body without that leg.
- `scan-kind5` any part below the floor at z = 0.
- `scan-rest-baseline` subtracts each vertex's rest-pose depth, so contact already in her rest pose is exempt.
- `scan-visibility` drops Overlaps the clip's camera cannot see.
- `scan-flag` flags an event at 10 mm deepest visible Overlap or longer than 0.1 s; ranks by depth (cm) x (1 + duration s).
- `scan-stills` renders the ten worst moments from the clip's camera with a magenta ring at the crossing.
- `scan-report` writes `numbers.json` and `report.md` with credits, the not-measured list and the stand-in gaps.
- Not measured, by design of version 1: kind 1 (body through clothing), kind 4 (one trailing family through another), collision-shape Overlaps, upper arm into torso, thigh into thigh.

## How to get to it (user POV)

- Run `$V scan --run-id "$RUN_ID"` after Launch (and usually after the clip).
- Read `review/verify/<run-id>/report.md`, then open the stills in `review/verify/<run-id>/moments/`.

## Driving it with scripts/verify

Preconditions:

- Launch is done for `$RUN_ID`. The clip is optional but `report.md` describes it when present.
- No other step of the same run is running.

- **Scan every frame.** Run `$V scan --run-id "$RUN_ID"`. Lines `SCAN frame ...` show progress; it ends with `SCAN DONE frames 1066 events <n> flagged <m> by kind {...}`, `SCAN READY review/verify/<run-id>/numbers.json` and `REPORT READY review/verify/<run-id>/report.md`.
- **Numbers.** Run `python3 -c "import json;d=json.load(open('review/verify/$RUN_ID/numbers.json'));print(d['frames_scanned'],d['flagged_by_kind']);[print(e['rank'],e['peak_time_s'],e['kind'],e['part'],e['other'],e['peak_visible_depth_mm']) for e in d['worst']]"`. It prints 1066, the flagged count per kind, and ten ranked rows.
- **Stills.** Run `ls review/verify/$RUN_ID/moments`. Ten files `moment_01_t<seconds>s_kind<k>_<part>-<through>.png` to `moment_10_...`. Open two or three: she is mid-dance, and the ring sits where a trailing part, a limb or the floor crossing is visible.
- **Report.** Open `review/verify/$RUN_ID/report.md`. It has the ten-row table, the list beyond ten, `Not measured (coverage is partial)`, `What this stand-in run does not prove`, and `Credits`.
- **Thresholds.** Run `$V scan --run-id "$RUN_ID" --frame-step 2 --min-depth-mm 20`. Fewer events are flagged; `numbers.json` `settings` records the values used. Run the default scan again before reporting.

## Gotchas

- With the stand-in, most flagged events are kind 2 and kind 5 from hair and skirt with no Secondary Physics. That is expected; do not tune thresholds to make it look clean.
- The inside test needs a closed-ish surface. Only materials `颜 肌 体 足 鞋 袖` form the surface; ornaments, beads, gems, eyes, face overlays and the microphone are never the thing passed through. A fault through those is missed.
- A trailing vertex is classified by its dominant bone. Hair roots weighted to the head count as head, not hair, so they are never tested as trailing.
- `--frame-step 2` halves the time but also coarsens durations to 1/15 s steps; a two-sample event already counts as longer than 0.1 s.
- Visibility is an estimate: a crossing counts as seen when the camera ray first meets her within 3 cm of it. Crossings hidden behind a thin layer of hair may still count as seen.
- Depth is to the nearest surface point. A part that has gone right through a thin limb can read shallower than it looks.
