# Turning an MMD model into a Simulation Body

Research for issue #5. Researched 2026-11-26 against tool repositories, format specifications and simulator documentation. Sibling tickets cover how the controller is trained (#3) and which simulator and hardware to use (#4). Whether the Simulation Body keeps her proportions or is adjusted for balance is decided in #12. This note covers the pipeline and the facts those decisions need.

## Answer in brief

- **No off-the-shelf tool turns a PMX model into an MJCF Simulation Body.** The workable pipeline is:
  1. Import the PMX and VMD into Blender with **MMD Tools**, which is maintained and supports Blender 4.2 to 5.2.
  2. Use a short `bpy` script to read the evaluated skeleton: joint centres, the rest pose, and the per-frame world transforms of about 15 key bones.
  3. Build the MJCF with **MuJoCo's Python `MjSpec` API**, using the 15-body MimicKit humanoid as the template for shapes, joint ranges, gains and torque limits.
- **Building the Simulation Body from her own skeleton, in her own rest pose, mostly removes the retargeting problem.** VMD rotations are local to her bones, so after collapsing the extra MMD bones (centre, groove, waist, twist, D and cancel bones) they become joint angles directly.
- **Read the evaluated pose, not the VMD keys.** Legs are driven by IK targets, and the bones the mesh actually follows are the D bones. Use an IK-based retargeter (GMR or mink) only if #12 changes her proportions.
- **Anime proportions break three assumptions:** mass taken from volume (her head is too big), thin-limb stability, and small feet.
- **Carrying simulated motion back onto the full rig is the same mapping run in reverse.** Write the simulated rotations onto the MMD bones with IK off, and layer the original VMD's fingers and face on top. No packaged tool does this; it needs a small script.

## 1. Import: MMD Tools in Blender

- **Maintenance:** MMD Tools now lives at [MMD-Blender/blender_mmd_tools](https://github.com/MMD-Blender/blender_mmd_tools). The old UuuNyaa URL redirects there, and the much older `powroupi` fork stopped in 2022. The latest release is v4.5.14 (2026-09-02), and the last commit was 2026-11-19.
- **Blender support:** The README lists **Blender 4.2 to 5.2** for MMD Tools v4.x. You install it from Blender's *Get Extensions* panel ([README](https://github.com/MMD-Blender/blender_mmd_tools/blob/b0ba6ae12fcf4e827f679f2a858875f0a0a4905a/README.md)). Its manifest sets `blender_version_min = "4.2.0"` and no maximum.
  - Blender 5.3.0 is already on download.blender.org, but MMD Tools does not list it as supported, and its issue tracker has nothing about 5.3.
  - **Stay on 5.2 LTS.** This Mac has Blender 5.2.2 LTS, and there is a `macos-arm64` build of every 5.x release ([release index](https://download.blender.org/release/)).
- **What it imports:** `.pmx`, `.pmd`, `.vmd` and `.vpd`, and it can export `.pmx`, `.vmd` and `.vpd` (README).
  - The default import scale is **0.08** Blender units per MMD unit ([`operators/fileio.py`](https://github.com/MMD-Blender/blender_mmd_tools/blob/b0ba6ae12fcf4e827f679f2a858875f0a0a4905a/mmd_tools/operators/fileio.py), `default=0.08`). That makes metres directly usable in MuJoCo. Check her height after import.
  - Scene setup sets 30 fps ([`auto_scene_setup.py`](https://github.com/MMD-Blender/blender_mmd_tools/blob/b0ba6ae12fcf4e827f679f2a858875f0a0a4905a/mmd_tools/auto_scene_setup.py)). The Reference Motion therefore arrives at 30 Hz and has to be resampled to the control rate.
  - Vertex and bone positions are converted from MMD's Y-up frame by swapping axes (`Vector(...).xzy * scale` in [`core/pmx/importer.py`](https://github.com/MMD-Blender/blender_mmd_tools/blob/b0ba6ae12fcf4e827f679f2a858875f0a0a4905a/mmd_tools/core/pmx/importer.py)). Blender and MuJoCo are both right-handed and Z-up, with MuJoCo's gravity along −z by default. So reading **world matrices from Blender** needs no further axis conversion beyond choosing a forward direction.
- **How the MMD rig mechanics come across:**
  - **IK:** Becomes Blender IK constraints. PMX per-link angle limits are converted to Blender IK limits (`convertIKLimitAngles`, same file).
  - **Inherited ("append" or 付与) rotation and translation:** Becomes constraints on hidden shadow bones (`apply_additional_transformation` in [`core/bone.py`](https://github.com/MMD-Blender/blender_mmd_tools/blob/b0ba6ae12fcf4e827f679f2a858875f0a0a4905a/mmd_tools/core/bone.py)).
  - **Twist bones:** Get automatic local axes (`AUTO_LOCAL_AXIS_SEMI_STANDARD_ARMS = ("左腕捩", "左手捩", "左肩P", ... )`, same file).
  - **VMD IK on/off property keys:** Become an animated `mmd_ik_toggle` per IK bone ([`core/vmd/importer.py`](https://github.com/MMD-Blender/blender_mmd_tools/blob/b0ba6ae12fcf4e827f679f2a858875f0a0a4905a/mmd_tools/core/vmd/importer.py)).
- **Interpolation does not exactly match MMD.** The importer notes that it uses quaternion Nlerp in Blender, while MMD uses Slerp with a Bézier time warp ("MMD Tools chooses to use Quaternion + Nlerp…", `core/vmd/importer.py` around line 507). The difference is small and sits well inside "recognisably the same dance".
- **Its physics is not usable for the Simulation Body.** The README says Blender's rigid bodies cannot reproduce PMX physics, because MMD uses Bullet 2.75 with soft constraints. It recommends [MMDBridge](https://github.com/rintrint/mmdbridge) for MMD physics. That matters for Secondary Physics (#7), not here. Bake or disable the Rigid Body World while extracting the skeleton.

Other tools checked and rejected:

- **Phobos** ([dfki-ric/phobos](https://github.com/dfki-ric/phobos)) is a Blender robot-model editor that exports URDF/SDF. Its README still targets Blender **3.3 LTS**.
- **blender-mjcf** ([Balint-H/blender-mjcf](https://github.com/Balint-H/blender-mjcf), last pushed 2026-06) exports parented **mesh** objects and Empty-marked joints. It does not read armatures, and primitive geoms are still on its to-do list. A script is less work than either.

## 2. The MMD skeleton and what each part becomes

### Format facts that matter

- **PMX bones** ([PMX 2.0/2.1 spec](https://gist.github.com/felixjones/f8a06bd48f9da9a4539f)):
  - The flags include IK (bit 5), inherit rotation (bit 8) and translation (bit 9) with a parent index and influence, fixed axis (bit 10, a single axis vector), and local coordinate (bit 11).
  - IK links can carry min/max Euler limits in radians.
- **PMX rigid bodies** (same spec):
  - Each has a related bone, a shape (0 sphere, 1 box, 2 capsule), a size, position, rotation and mass.
  - Each has a physics mode: 0 follows the bone, 1 is physics, 2 is physics pivoted to the bone.
- **VMD bone keys** ([`core/vmd/__init__.py`](https://github.com/MMD-Blender/blender_mmd_tools/blob/b0ba6ae12fcf4e827f679f2a858875f0a0a4905a/mmd_tools/core/vmd/__init__.py)):
  - Each key holds a bone **name** (cp932, at most 15 bytes), a frame number, a location vec3, a rotation quaternion and 64 bytes of Bézier interpolation.
  - VMD binds to bones **by name**. Names longer than 15 bytes are truncated and fail to bind ([babylon-mmd, VMD/VPD](https://noname0310.github.io/babylon-mmd/docs/reference/understanding-mmd-behaviour/introduction-to-vmd-and-vpd/)).
  - IK on/off is stored in separate property keyframes, not in the bone keys (same source).
- **Semi-standard bones use append transforms in two places** ([babylon-mmd, PMX/PMD](https://noname0310.github.io/babylon-mmd/docs/reference/understanding-mmd-behaviour/introduction-to-pmx-and-pmd)):
  - Shoulder cancel bones (肩P/肩C) undo the shoulder's rotation so it does not carry into the arm.
  - Leg **D bones** (足D, ひざD, 足首D) apply FK offsets *on top of the IK result*.
  - Almost all MMD models solve the legs by IK, and evaluation order follows the bone order and the transform-order field.

### Mapping onto a 15-body Simulation Body

The template is MimicKit's humanoid, the 15-body DeepMimic-lineage character ([MimicKit `data/assets/humanoid/humanoid.xml`](https://github.com/xbpeng/MimicKit/blob/a2c41528c2a34b638611f6c618e4a59f0e151179/data/assets/humanoid/humanoid.xml); repo last pushed 2026-11-18).

- **Bodies:** pelvis, torso, head, and for each side upper arm, lower arm, hand, thigh, shin and foot.
- **Joints:** 3 hinges for each of the abdomen, neck, shoulders, hips and ankles, and 1 hinge for each elbow and knee.
- **Physical parameters it sets:**
  - `range` on every joint.
  - `stiffness`, `damping` and `armature` on every joint (`armature` 0.01 to 0.02).
  - `actuatorfrcrange` limits from ±50 N·m (neck) to ±200 N·m (hips and abdomen).
  - A tuned `density` for each geom.

Read each MMD source bone below **after Blender evaluates the frame**:

| Simulation Body part | MMD source (evaluated) | What to fold in |
|---|---|---|
| root (free joint) and pelvis | world transform of **下半身** (lower body) | 全ての親 (root), センター (centre, horizontal and turn), グルーブ (groove, vertical) and 腰 (waist) are all upstream. Do not map them separately; their combined effect is already in 下半身's world transform. |
| torso | 上半身, plus 上半身2 (and 上半身3 if present) | Either merge them into one 3-DoF abdomen, or spend 1 to 2 extra bodies to give her a spine (a 16 to 17 body variant). |
| head | 頭, with 首 | Merge the neck into the head joint, or add a neck body. |
| upper arm | 腕 + 腕捩 (arm twist) | 腕捩 rotates about the arm's own axis. Add it to the shoulder's twist hinge. |
| lower arm | ひじ + 手捩 (wrist twist) | The elbow is a single hinge. 手捩 (forearm pronation) has no joint in the 15-body template: drop it, or add a forearm twist hinge. |
| hand | 手首 | Fingers are not simulated. They stay as Visible Mesh animation. |
| thigh / shin / foot | **足D, ひざD, 足首D** (and 足先EX) | **Not 足/ひざ/足首, and not the VMD keys.** The IK bones (足ＩＫ, つま先ＩＫ) store target positions; the leg angles only exist after IK is solved, and the mesh follows the D bones. |
| (optional) clavicles | 肩 | Ignore 肩P/肩C: they exist to cancel 肩's rotation for the arm. Optional bodies push the count toward 17 to 20. |

Two consequences shape the whole approach:

1. **Extract by evaluating the rig, not by parsing the VMD.** For every frame:
   1. Set the frame in Blender with the MMD Tools rig active, so IK, append transforms and the D bones are all solved.
   2. Record `pose_bone.matrix` (armature space) for the bones in the table.
   3. Convert the result to MuJoCo `qpos`:
      - Root position and orientation from 下半身.
      - Each joint's local rotation as `parent⁻¹ · child`, relative to the rest pose, split into the template's hinge axes (or kept as a quaternion for a ball joint).

   Blender's IK solver is not MMD's, so legs can differ slightly from MMD playback. A short side-by-side render is the check.
2. **The A-pose problem disappears if the Simulation Body uses her rest pose as its reference configuration.**
   - VMD rotations are relative to each bone's rest orientation. If the MJCF bodies are placed at her PMX rest joint centres and orientations, with `qpos0` equal to that rest pose, the evaluated local rotations are the joint angles.
   - The catch is that joint limits from a template are written for the template's own rest pose. MimicKit's upper arms lie along ±y, a T-pose: see `fromto="0 -0.03 0 0 -0.23 0"`. So shoulder ranges must be re-expressed relative to her arm angle (measured in #8), or her rest pose must be rotated to a T-pose before building.
   - Either way, check every limit against the motion: compute each joint's angle range across the whole dance, and widen any limit the Reference Motion exceeds.

### If #12 changes her proportions

- Local angles no longer reproduce foot placement once limb lengths change. Use keypoint IK instead:
  - **GMR** ([YanjieZe/GMR](https://github.com/YanjieZe/GMR), MIT, pushed 2026-10-22) retargets SMPL-X, BVH and FBX motion onto any MJCF robot. You supply an IK config mapping robot bodies to source bodies, with position and rotation weights and offsets ([DOC.md](https://github.com/YanjieZe/GMR/blob/main/DOC.md)).
  - GMR is built on **mink** ([kevinzakka/mink](https://github.com/kevinzakka/mink), pushed 2026-11-19), a MuJoCo differential-IK library with frame tasks, joint limits and equality constraints such as feet flat on the floor.
- VMD is not one of GMR's input formats. Either export the evaluated MMD skeleton as BVH from Blender (Blender has a built-in BVH exporter) and add a format config, or call mink directly with the same frame targets.
- MimicKit can ingest GMR output (`tools/gmr_to_mimickit`) and SMPL (`tools/smpl_to_mimickit`).

## 3. Shapes, masses, joints and motors

- **Shapes:**
  - Use capsules for limbs, spheres or capsules for the head and torso, and boxes for feet, as MimicKit does. MuJoCo collides these cheaply.
  - Size each geom to her mesh: capsule radius from the limb cross-section, length from joint centre to joint centre.
  - **The PMX very likely already contains bone-following rigid bodies** (mode 0) on her head, torso and limbs. Many models include them as colliders for hair and skirt physics, but #8 must confirm hers does. Their shape, size and position (PMX spec above) are designed seeds for these geoms and for the Secondary Physics colliders in #7. Read them in Blender as the `mmd_tools` rigid-body objects, then fit the MJCF geoms.
  - Exclude the dress, hair and ribbons from the Simulation Body entirely. They are Secondary Physics.
- **Masses: do not let volume decide.**
  - MuJoCo computes mass from geom volume at `density` 1000 kg/m³ unless a geom sets `mass` ([XML reference, `geom/density`](https://mujoco.readthedocs.io/en/stable/XMLreference.html#body-geom-density)). Her oversized head would come out far too heavy relative to her thin limbs.
  - Instead, choose a plausible total mass and distribute it by **segment mass fractions** from de Leva (1996), *Adjustments to Zatsiorsky–Seluyanov's segment inertia parameters*, J. Biomech. 29(9):1223–1230, [doi:10.1016/0021-9290(95)00178-6](https://doi.org/10.1016/0021-9290(95)00178-6).
  - Female values: head 6.68 %, trunk 42.57 %, thigh 14.78 % ([verified via Visual3D's reproduction](https://wiki.has-motion.com/Adjusted_Zatsiorsky-Seluyanov%27s_segment_inertia_parameters)). Take the remaining segments from the paper's table.
  - Set `mass` per geom, or set a per-geom `density` the way MimicKit does, and let MuJoCo derive inertia from the shape.
- **Joints:**
  - Use three hinges rather than a `ball` where per-axis limits matter. A MuJoCo ball joint limits only the *total* rotation angle, as a cone: only the second `range` value is used ([`joint/range`](https://mujoco.readthedocs.io/en/stable/XMLreference.html#body-joint-range)).
  - Add `armature` on every joint ([`joint/armature`](https://mujoco.readthedocs.io/en/stable/XMLreference.html#body-joint-armature)). It is the standard stabiliser for light, thin segments, which is exactly the anime-limb case.
  - Contacts between a parent and a child body are filtered by default ([`flag/filterparent`](https://mujoco.readthedocs.io/en/stable/XMLreference.html#option-flag-filterparent)). Thigh-to-thigh and arm-to-torso contacts are not filtered: with slim legs set close together, decide on explicit `<exclude>` pairs.
- **Motors:**
  - Start from MimicKit's torque limits and gains, then scale them. Holding torque against gravity scales roughly with segment mass × lever length, so scale by (her mass × her limb length) / (template mass × template limb length) per joint.
  - Then let training (#3) reveal joints that saturate.
  - Position actuators in MuJoCo take `kp` and `kv` ([`actuator/position`](https://mujoco.readthedocs.io/en/stable/XMLreference.html#actuator-position-kp)).
  - Which actuator form to use (torque or PD target) belongs to #3.
- **Export:** Build the model in Python with `mujoco.MjSpec()`, then `spec.worldbody.add_body(...)` and `body.add_geom(...)`, and write it with `spec.to_xml()` ([MuJoCo Python docs, model editing](https://mujoco.readthedocs.io/en/stable/python.html), [`MjSpec` overview](https://mujoco.readthedocs.io/en/stable/programming/modeledit.html)).
  - Run this outside Blender from a JSON dump of the skeleton. That avoids installing `mujoco` into Blender's bundled Python.
  - MuJoCo is at 4.0.1 (released 2026-11-11).
  - The generated MJCF is derived from the model's proportions. Under the licence and the map's standing note, keep it **out of git**: commit the scripts only.

## 4. What goes wrong with anime proportions

- **Large head means a high centre of mass and an overweight head.** Fix it with mass fractions (above), not volume. The head geom can stay large for collision while carrying realistic mass.
- **Thin limbs mean small inertia and stiff, jittery joints.**
  - Use `armature`, set a minimum capsule radius for *collision* (wider than the visible limb is fine, because the Visible Mesh does not take part), and keep `kv` damping.
  - Thin limbs pass through each other more easily, so check self-collision exclusions.
- **Small feet mean a small support polygon,** and dances with turns and one-leg poses become hard to balance.
  - The foot box can be made slightly longer or wider than the visible foot without visible cost. That counts as "adjusted for balance" and belongs to #12.
  - If she wears heels, the box should represent the sole contact, not the shoe's outline. #8 should check.
- **VMDs authored for another model:** A VMD stores absolute センター/グルーブ and IK-target positions in model units. On a model with different leg length, the knees bend more or lock straight, and feet slide or sink.
  - This follows from the format rather than from a source that measured it.
  - Check the chosen dance for this before training. Many MMD motion distributors ship height-specific variants (#15).
- **Rest pose:** Her rest pose (A-pose versus T-pose, and the elbow bend) has to match `qpos0`, or every joint limit must be re-based (section 2).

## 5. Back from the simulator onto the full MMD rig (brief)

Nothing packaged does this. The known pieces are:

- **The inverse of the extraction mapping.** For each frame:
  1. Take the MuJoCo body orientations.
  2. Convert them to local rotations relative to the rest pose.
  3. Write them to the corresponding MMD bones in Blender: 下半身 world transform from the root, 上半身, 首/頭, 腕, ひじ, 手首, 足/ひざ/足首.
  4. Turn the leg IK off by keying `mmd_ik_toggle` false, so the FK values are what the mesh follows.

  Rotations that were folded together come apart again:
  - Split the shoulder twist back into 腕 and 腕捩.
  - Put any forearm twist on 手捩.
  - Leave the D-bone offsets at zero.
- **Layering un-simulated parts:** Fingers, face morphs, eyes (両目) and any bones the Simulation Body never had can be copied from the original VMD, because they do not affect balance. Hair, skirt and ribbons are then Secondary Physics at render time (#7).
- **Optional VMD round trip:** MMD Tools exports VMD, including IK on/off states ([`core/vmd/exporter.py`](https://github.com/MMD-Blender/blender_mmd_tools/blob/b0ba6ae12fcf4e827f679f2a858875f0a0a4905a/mmd_tools/core/vmd/exporter.py)). The simulated dance can therefore be saved as a VMD for MMD-side tools such as MMDBridge physics baking. Remember the 15-byte bone-name limit.
- **Open issue:** Where the simulation drifts from the Reference Motion, the hands may no longer meet the body or props the way the original did. Finger and face layers are unaffected. Fixing contact after simulation would be a later step and is not researched here.

## Not determined here

- Whether her PMX has bone-following body rigid bodies, her exact rest-pose arm angle, her height at scale 0.08, and whether her shoes have heels. All of these depend on inspecting the model (#8).
- Whether MMD Tools works on Blender **5.3**. It is declared for 4.2 to 5.2 and untested here, so use 5.2 LTS.
- How closely Blender's IK solve of the legs matches MMD's own playback for the chosen dance. That needs a side-by-side check once a VMD is chosen.
- The de Leva female mass fractions beyond head, trunk and thigh were not read from the paper itself. Take them from its Table 4.
