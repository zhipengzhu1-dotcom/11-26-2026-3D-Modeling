# PROTOTYPE: first look at her Simulation Body (throwaway)

Throwaway code for the map ticket "First look at her Simulation Body" (issue 20). It answers one question for the human's Eye Check:

> Does her 19-part Simulation Body sit right on her, and does it move with Anime Feel?

It is not the Build. Nothing here is merged; the branch `prototype/simulation-body-first-look` is kept only as a primary source. Use the words of `GLOSSARY.md`.

## What it makes

1. **Stills** of the Simulation Body drawn over her in her rest pose: parts, joints, collision solids, shoe contact.
2. **Clips** of her moved by the Simulation Body with her hips carried by an invisible hand (she is not balancing), three figures side by side: as authored (no physics), soft springy joints, stiff joints. Four kinds of movement: a passage of the dance, a walk, cute poses, a singing passage.
3. **Numbers**: the joint ranges all four kinds of movement ask for, how closely the solids hug her drawn surface, her weight per part.

## Hard rules

- The repo is public. The model and anything derived from it never enter git (`docs/adr/0002`). Code computes everything at run time from the local model copy; no vertex data, fitted sizes, MJCF, images or arrays are written to a tracked path or hard-coded.
- Scratch goes to `build/first-look/`, evidence for the human to `review/first-look/<round>/`. Both are git-ignored.
- No single job may occupy the machine for more than ten minutes.
- Her Simulation Body must survive Isaac Lab's import later: no ellipsoid shapes, no `contype`/`conaffinity` filtering, no per-pair contact overrides (`<pair>`). Hinge joints only.

## Tools

- Blender 5.2 LTS, headless: `/Applications/Blender.app/Contents/MacOS/Blender -b --python <script> -- <args>`. MMD Tools is installed; enable it as `.claude/skills/verify-vodyanitsa/scripts/blender/common.py` does. Import idiom (scale 0.08, strip the shipped rigid bodies): `.claude/skills/verify-vodyanitsa/scripts/blender/standin_build.py` and `assets/inspect/motion/dump.py`.
- MuJoCo through uv, no venv in the repo: `uv run --with mujoco --with numpy --with scipy python <script>`.
- Model: first match of `沃雅妮莎_by_*/沃雅妮莎.pmx` at the repo root. Motions: under `assets/motion/`.

## The 19 parts and the MMD bone each one follows

Space: armature space, which equals world (armature at the origin, metres, Z up, she faces -Y). Bone names are as MMD Tools imports them (`.L`/`.R`).

| Part | Parent | Joint sits at the head of | Its rotation is read from |
|---|---|---|---|
| `pelvis` | (carried) | 下半身 | 下半身 |
| `waist` | `pelvis` | 上半身 | 上半身 |
| `chest` | `waist` | 上半身2 | 上半身2 |
| `neck` | `chest` | 首 | 首 |
| `head` | `neck` | 頭 | 頭 |
| `collar_L/R` | `chest` | 肩 | 肩 |
| `upper_arm_L/R` | `collar` | 腕 | 腕捩 (so the upper-arm twist is included) |
| `forearm_L/R` | `upper_arm` | ひじ | 手捩 (so the forearm twist is included) |
| `hand_L/R` | `forearm` | 手首 | 手首 |
| `thigh_L/R` | `pelvis` | 足D | 足D |
| `shin_L/R` | `thigh` | ひざD | ひざD |
| `foot_L/R` | `shin` | 足首D | 足首D |

Part order in every array is exactly: `pelvis, waist, chest, neck, head, collar_L, collar_R, upper_arm_L, upper_arm_R, forearm_L, forearm_R, hand_L, hand_R, thigh_L, thigh_R, shin_L, shin_R, foot_L, foot_R`.

**Rotation delta.** For a part following bone `b`, `D(t) = R_eval(b, t) · R_rest(b)^-1`, where `R_eval` is the rotation of the evaluated `pose_bone.matrix` (after IK, grants and constraints) and `R_rest` the rotation of `bone.matrix_local`. `D` is the identity in her rest pose. Everything exchanged between scripts is a delta, so no script depends on another's frame conventions.

Weight shares of 25.5 kg: head 16.8, neck 1.4, chest 12.8, collar 0.4 each, waist 7.3, pelvis 9.7, thigh 15.2 each, shin 5.9 each, foot 0.9 each, upper arm 2.2 each, forearm 1.2 each, hand 0.3 each (percent).

## Files exchanged (all under `build/first-look/`)

`body.json`, written by the body script:

```
{"parts":  [{"name", "parent", "joint_pos": [x,y,z], "mass", "color": [r,g,b]}],      # rest pose, world
 "joints": [{"name", "part", "pos": [x,y,z], "axis": [x,y,z], "range_deg": [lo,hi]}], # rest pose, world
 "geoms":  [{"part", "type": "capsule|box|sphere", "pos": [x,y,z], "rot": 3x3,
             "size": [...],            # MuJoCo half-sizes: capsule [radius, half-length along local z], box [hx,hy,hz], sphere [r]
             "floor_contact": bool}]}  # true for the shapes meant to touch the floor (front pad, heel tip)
```

`clips.json`, written by the simulate script: a list of
`{"name", "kind": "dance|walk|cute|sing", "title", "npz", "vmd", "framing": "full|bust", "hips": "carried|pinned", "credits"}`.

`sim/<name>.npz`, one per clip, 30 frames a second, `T` frames:

- `parts`: the 19 names in order.
- `src_frame[T]`: for each output frame, the Blender frame of the source VMD as imported with `import_vmd(margin=0)` (face shapes and fingers are taken from there).
- `loop_len`: 0, or the length in frames of the source loop when the clip tiles a loop.
- for each variant `v` in `ref`, `soft`, `stiff`: `pos_<v>[T,19,3]` (world position of each part's joint) and `rot_<v>[T,19,3,3]` (the rotation delta `D` of each part). `ref` is the Reference Motion as it plays on her with no physics.

## Clips of the first round

| Clip | Source | Frames |
|---|---|---|
| `dance` | `assets/motion/toki-yo-tomare/時よ止まれ.vmd` | Blender frames 286 to 525 (the quick turn, the kick, the crossed arms) |
| `dance_pinned` | the same passage with her hips pinned in the air and no floor | the same |
| `walk` | むつごろう `2.歩き10L_乙女_(40f_前移動20).vmd`, tiled four times; fall back to `walk-fuyuneko-aruku/…/歩く.vmd` if the loop seam is not clean | 160 |
| `cute_heart` | グレイ `ターンしてハートモーション.vmd` | whole file |
| `cute_peace` | グレイ `ピスピース_あぴミク.vmd` | whole file |
| `sing` | i7 `Jackie Evancho  Ave Maria.vmd`, the 8 s window with the most arm travel while the mouth is moving | 240, framed from the waist up |

## Run

`./prototype/simulation-body/run.sh round1` runs every step and leaves `review/first-look/round1/index.html`.
