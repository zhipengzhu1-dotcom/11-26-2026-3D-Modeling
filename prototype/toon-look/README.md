# Toon look prototype (PROTOTYPE, throwaway)

Question: **what should she look like?** This prototype builds a bright anime look for her in Blender and compares it with gosari ごさり's fan videos.

- **First pass** (`review/look/20261126-gosari/`): five rounds of colour matching against one private reference video (render, measure by region in CIELAB, adjust), then three looks for an Eye Check: A soft, B cel, C stage. B's direction was chosen.
- **Second pass** (`review/look/20261126-gosari-channel/`): a survey of ten other gosari videos turned into a style sheet; rounds 6 to 11 on B, each measured on the same regions and checked against the style sheet's measured ranges; then five sub-variants of the best round.

It is throwaway code: no tests and no polish. Fold whatever the Eye Check picks into the real Build, then drop this folder.

Rerun everything, both passes (about three minutes of headless Blender):

```
python3 prototype/toon-look/run.py
```

Only the second pass: `python3 prototype/toon-look/run.py --run-id 20261126-gosari-channel`. Only some looks: add their names, for example `round11 subB2`. Only rebuild the report and viewer: `viewer`.

- `params/round0..5.json`, `params/variantA..C.json`: the first pass. `params/round6..11.json`, `params/subB1..5.json`: the second. One look per file. `change` says what was changed going into that look.
- `look.py`: the Blender side. It imports with MMD Tools, poses her from the stage 1 dance and sets face shape keys (her smile). It builds toon materials, including ambient occlusion into the ramp, a teal colour key, and a softened hair-shine layer. It sets up lights and a compositor (stage plate made by code, contact shadow, bloom, diffusion), and renders stills plus a material-ID pass.
- `measure.py`: the region colour comparison and the style checks against the survey ranges.
- `survey.py`: crops and measures the survey frames.
- `run.py`: runs it all and writes the run folders (git-ignored): stills, `table.json` per look, `report.md` and a single-file `index.html` viewer.

Nothing from YouTube is fetched by the scripts. The reference frames (`reference/ref1..6.png`) and the survey screenshots (`survey/raw/*.jpg`, with `survey/videos.json`) are put in the run folder by hand. How they were taken is in that run's report. They are someone else's videos: never commit or publish them, or anything rendered from the model (docs/adr/0002).

Credits: model 【原神】沃雅妮莎 by miHoYo, converted by 观海; motion 時よ止まれ by Kei (@Kei_MMD_), traced from @ellendance, song by ILLIT; style reference: gosari ごさり's videos, used privately.
