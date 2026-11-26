# Secondary Physics without 穿模

Research for issue #7. Researched 2026-11-26, against Blender 5.3 (released 2026-11-10) and Blender 5.2 LTS (released 2026-07-14) [R1].

**Question.** The body's motion comes from a simulator and is baked onto the armature. How should hair, skirt tiers, ribbons, sleeves and fin ears be simulated in Blender so they do not pass through the body or through each other? The candidates are the model's own MMD rigid bodies and joints, Blender cloth and hair, and bone-chain physics add-ons. What are the standard remedies for 穿模, and what does each cost?

## Answer

1. **Use the model's own MMD rigid bodies and joints as the main Simulation Body for Secondary Physics.** Import and run them with MMD Tools, then fix them up: add or enlarge the body-side colliders, set the collision groups properly, and stiffen the joints. This is the only approach where the same data (PMX rigid bodies and joints) also runs in a real-time viewer later, through Bullet-based MMD runtimes [S1][S9]. That keeps the stage-1 work for stage 2.
2. **Move the layered skirt tiers, and possibly the sleeves, to Blender's classic Cloth simulation on a low-poly proxy only if the rigid bodies still cause 穿模.** The proxy collides with the body and with itself, and it drives the Visible Mesh through Surface Deform. MMD Tools Append already has a "Rigid Body to Cloth" converter that builds exactly this proxy from the existing rigid bodies [S3][S4]. This is offline-only.
3. **Do not use bone-chain add-ons as the main tool.** Wiggle 2 has not had a commit since April 2024, and its open issues report broken collisions and no Blender 5.0 support [S6]. Spring Bones is updated for Blender 5.x, but its author calls it "not production ready" [S7]. Also do not use the new Geometry Nodes Hair/Cloth Dynamics yet. It is experimental, the cloth version has no self-collision, and the hair version only works on Curves hair, not on the mesh-and-bone hair an MMD model has [S12][S13][S14].
4. **Fix whatever 穿模 remains with cheap remedies, in this order:**
   - smooth the simulator's jitter out of the body motion before Secondary Physics runs;
   - give colliders a thickness margin and use more substeps;
   - hide body faces that are always covered (Mask modifier);
   - fix weights and enable Preserve Volume;
   - push clothing out of the body with Shrinkwrap "Outside";
   - add corrective shape keys only for specific poses;
   - as a last resort, edit the cached result by hand.

   Costs are in [Remedies](#remedies-for-穿模-and-their-cost).

## Constraints that shape the answer

- The model ships MMD rigid bodies and joints. By the PMX format, every rigid body is a sphere, box or capsule. Each one has a collision group, a 16-bit "non-collision" mask, and a mode: *follow bone* (moved by the skeleton), *physics*, or *physics + bone*. Joints are spring-6DOF, with position and rotation limits plus position and rotation springs [S2]. *Follow bone* bodies on the torso, head and limbs are the body-side colliders. The *physics* chains are the hair, skirt and ribbons.
- Body motion arrives already baked onto the armature from MuJoCo. Secondary Physics is therefore one-way: it reads the body and never pushes back. This fits the project definition, and it also means Secondary Physics cannot fix limbs passing through each other (see [Limbs through limbs](#limbs-through-limbs-is-not-secondary-physics)).
- Simulated motion may jitter. Any physics driven by a bone inherits that bone's accelerations. High-frequency jitter at the root of a hair or skirt chain becomes flicker or a sudden jump at the tips, and fast movement also makes tunnelling through thin colliders more likely [S5][S13].
- Apple Silicon Mac. Blender ended Intel Mac support in 5.0, so Apple Silicon is the only macOS target [R1]. Every Blender option below is CPU-side Blender Python or core Blender, with nothing tied to Windows or CUDA.

## The options

### A. Reuse the MMD rigid bodies and joints (MMD Tools)

- **Status.** MMD Tools is maintained by the MMD-Blender organisation: last push 2026-11-19, latest release v4.5.14 on 2026-09-02. It installs from Blender's Extensions platform. The README lists support for **Blender 4.2–5.2** [S1]. The manifest sets `blender_version_min = "4.2.0"` and no maximum [S1]. **Blender 5.3 is not yet listed as supported, so use 5.2 LTS for this pipeline** until the README catches up.
- **How it works.** On import, rigid bodies become Blender rigid-body objects and joints become Rigid Body Constraints in the scene's Rigid Body World, simulated by Bullet. Substeps and solver iterations are set per world, and the result is baked into the rigid-body cache [S10]. Constraints have a *Disable Collisions* toggle and per-constraint solver iterations [S11].
- **Known limitations, from the maintainers' own README** [S1]:
  - Blender's rigid-body system "is prone to crashes and has worse performance compared to MMD".
  - Blender has no collision masks, so MMD Tools imitates the PMX non-collision mask with "numerous rigid body constraints". This "further degrades performance".
  - MMD uses Bullet 2.75 with "soft" constraints, while Blender's newer Bullet has "hard" constraints, so "MMD Tools cannot reproduce PMX physics exactly as they behave in MMD".
  - Their recommended workaround is **MMDBridge**, which bakes physics inside MikuMikuDance itself. That needs Windows, the Visual C++ runtime and DirectX [S8], so **it does not work on this Mac**.
- **What 穿模 looks like here.** Rigid bodies only collide with other rigid bodies, so the Visible Mesh is protected only as well as the capsules approximate it. Gaps between skirt capsules, thin or missing thigh colliders, and wrong group masks all show up as skirt-through-leg or hair-through-shoulder. Fixing them means editing the rigid bodies, which the licence allows ("improving the physics"). Approach A is mostly that fixing work.
- **Good for:** hair strands and side locks, bangs, ribbons and fin tails, fin ears (nearly *follow bone*, or very stiff springs), and sleeves. These are all bone chains already rigged by the model author.
- **Cost.** Low setup, because the data already exists. Moderate tuning, because colliders are added and edited one at a time. Simulation is fast compared with cloth, but the Blender rigid-body world can be unstable [S1].

### B. Blender Cloth on a proxy (classic cloth modifier)

- **How it works.** A low-poly proxy mesh gets the Cloth modifier. Its top edge is pinned to the armature through a *Pin Group* [S16]. The body mesh gets a Collision modifier, which must sit *after* the Armature modifier so the cloth sees the deformed body [S15]. The detailed Visible Mesh follows the proxy through a **Surface Deform** modifier. The manual names "a proxy mesh for cloth simulation" as the main use of Surface Deform. The proxy must have no edges shared by more than two faces, no concave faces, no doubled vertices and no collinear edges [S19].
- **Anti-穿模 controls** [S15][S17]:
  - Collider *Thickness Outer/Inner* and *Single Sided*. Single Sided pushes intersecting cloth out along the collider normal.
  - Cloth object-collision *Distance*, *Impulse Clamping* and a *Collision Collection*.
  - **Self-collision**, with its own distance. The manual says a close-up "blouse on a character should have this enabled". This is what keeps the ruffled tiers out of each other.
  - Collision *Quality* and simulation *Quality Steps*.
- **The manual's own troubleshooting order** [S17]: raise collision Distance (fastest, but looks like the cloth "is resting on air"), then raise Quality, then edit the cached result in Edit Mode. It also warns that a cloth which starts inside a collider makes the simulation unstable [S18].
- **Ready-made converter.** MMD Tools Append (maintained: v4.5.14 released 2026-11-13; README lists support for **Blender 4.2–5.3** [S3]) has *Append Physics → Rigid Body to Cloth* [S3]. Its source shows what it does [S4]:
  - builds a cloth mesh with one vertex per selected rigid body and edges taken from the joints, then extends and fills faces;
  - pins it with a `physics_cloth_pin` group and an Armature modifier;
  - adds Subdivision and Corrective Smooth;
  - drives the MMD mesh either through **Surface Deform** or by giving the physics bones *Stretch To* constraints aimed at the cloth vertices.

  The second mode matters: the bones still move, so the result can be baked back onto bones.
- **Good for:** the off-shoulder dress's layered ruffled tiers, and possibly the puffy sleeves. These are surfaces where tier-through-tier and skirt-through-leg are the main risk, and where capsule chains are poor approximations.
- **Cost.** Moderate setup: proxy, pinning, Surface Deform bind. Slow simulation on the CPU, especially with self-collision, which the manual says "adds to the simulation's compute time" [S17]. It must be re-baked whenever the body motion changes. It does **not** carry over to real time, unless you use the Stretch To bone mode and bake the bones.

### C. Geometry Nodes Hair Dynamics and Cloth Dynamics (Blender 5.2+, experimental)

- **What it is.** Blender 5.2 added Geometry Nodes systems for hair and cloth, built on a new XPBD Solver node. The release notes say they are experimental because "it's hard to lock in the design without more widespread testing first" [S12].
- **Why not now:**
  - **Cloth Dynamics** says "Some features are currently missing, such as self-collision" [S13]. That rules it out for layered tiers.
  - **Hair Dynamics** simulates *Curves* hair attached to a surface [S14]. The model's hair is mesh driven by bone chains, so using it would need custom guide curves feeding back into bones.
  - Both only support **closed (manifold) colliders**. Open collider edges "can lead to sudden jumping", and thin colliders allow tunnelling [S13][S14].
  - The manual advises keeping substeps under 20 and raising constraint iterations instead. A *Residual Error* output shows the solution quality (ideally ≤ 1) [S14].
- **Worth revisiting** once self-collision lands and the design is stable.

### D. Bone-chain physics add-ons

| Add-on | Maintenance (checked 2026-11-26) | Verdict |
|---|---|---|
| Wiggle 2 (shteeve3d) | Last commit 2024-04-18; last release v2.2.3 (2023-08). Open issues: "Blender 5.0 compatibility" (#117), "Not installing Blender 4.5" (#110), "Collisions are broken in Blender 4.0" (#102), "Hasn't been updated in over 2 years – Alternatives?" (#112) [S6] | Not maintained, and collisions are broken. Avoid. |
| Spring Bones (artellblender) | Last commit 2026-03-29, "Updated to Blender 5x". README: "alpha-proof of concept … not production ready … mainly a toy" [S7] | Works, but its author disowns production use. Fine for quick previews only. |

Neither adds anything the MMD rigid bodies don't already provide, because the model already has authored chains and colliders. The real-time equivalent of this idea is the VRM spring bone, covered in [Carry-over to real time](#carry-over-to-real-time).

## Recommended per-part plan

| Part | Simulation | Body-side colliders that matter |
|---|---|---|
| Long back hair, side locks | MMD rigid-body chains (A) | Head, neck, shoulder and upper-back capsules; chest |
| Bangs over one eye | MMD chain, stiff and short, or mostly *physics + bone* | Head/face sphere, so the bangs don't sink into the face |
| Fin-like ears | *Follow bone*, or a very stiff spring joint (A) | None needed |
| Detached puffy sleeves | MMD chain (A); cloth proxy (B) if they clip the arm | Upper and forearm capsules |
| Gradient ribbons / fin tails at the front | MMD chains (A) | Thigh and shin capsules, pelvis |
| Off-shoulder layered dress tiers | MMD skirt chains first (A); if tiers clip each other or the legs, Rigid Body to Cloth → Cloth with self-collision (B) | Pelvis, thighs and knees as a closed collision mesh |

## Remedies for 穿模 and their cost

| Remedy | What it fixes | Cost | Real-time? |
|---|---|---|---|
| **Smooth the body motion before Secondary Physics.** Graph Editor *Key → Smooth → Butterworth Smooth* on the baked bones. The manual calls it "ideal for smoothing large amounts of data because it preserves the peaks", but it "can introduce a ripple effect" [S20]. | Flicker and tunnelling caused by simulator jitter | Minutes; a small fidelity loss to the Reference Motion | Yes, as a filter on live motion |
| **Rest-pose pre-roll.** Start the cache a second or so before the dance, in rest pose, so nothing starts inside a collider [S18]. | Explosions on the first frame | Trivial | Yes (warm-up) |
| **Better colliders.** Enlarge or add capsules (A), or raise collider Thickness Outer, cloth Distance and Single Sided (B) [S15][S17]. | Trailing parts through the body | Per-collider tuning. Too thick looks like floating [S17] | Yes for capsules |
| **More substeps and iterations.** Rigid Body World substeps and solver iterations [S10]; cloth Quality and collision Quality [S16][S17]. | Fast-motion tunnelling | Bake time grows roughly with the step count | Partly; there is a frame budget |
| **Hide the body under clothing.** A Mask modifier with a vertex group hides vertices that are not in the group (or are in it, with *Invert*) [S21]. | Body poking through tight clothing that never moves away (bodice, tops of sleeves) | Very cheap, and needs no change to body proportions | Yes (delete the faces at export) |
| **Weight fixes and Preserve Volume.** Repaint weights; the Armature modifier's *Preserve Volume* uses quaternion skinning so joints don't collapse [S22]. Licence explicitly allows weight fixes. | Clothing-through-body at shoulders, elbows and hips caused by skinning, not physics | Hours of weight painting; Preserve Volume is one checkbox | Yes |
| **Corrective Smooth** after the Armature modifier: "reduce highly distorted areas … where distortion around joints may be hard to avoid, even with careful weight painting" [S23]. | Pinching and folds that push one layer through another | Cheap; may lose volume (it has a Scale option) [S23] | Mostly no (Blender modifier) |
| **Shrinkwrap with snap mode *Outside*.** Leaves vertices already outside the target untouched and pushes the rest out, with an Offset margin. The manual calls it "very crude collision detection", unstable near sharp angles [S24]. | Last-mile cloth-through-body after the sim | Cheap; per-garment vertex group | No |
| **Corrective shape keys.** Relative shape keys for "corrective poses", driven by bone rotation [S25]. | Specific poses that always clip (deep bends, arms raised) | High: hand-sculpted per pose | Yes (blend shapes export) |
| **Edit the cache by hand**, frame by frame in Edit Mode [S17]. | A few remaining frames | Very high per frame; cannot be repeated if the motion changes | No |

## Limbs through limbs is not Secondary Physics

Arm-through-torso and leg-through-leg come from the body motion itself. Because Secondary Physics never drives the body, it cannot fix them. The fix belongs in the MuJoCo model: give limbs collision geoms that are allowed to touch each other (`contype`/`conaffinity`) so the learned controller cannot produce those poses [S26]. Then, on the Visible Mesh, use weight fixes and Preserve Volume as above.

## Carry-over to real time

- **MMD rigid bodies and joints (A): carry over.** They are PMX data that MMD Tools can export [S1], and Bullet-based web runtimes simulate them directly. For example, babylon-mmd ships a "WASM based runtime for threaded bullet physics" (maintained, pushed 2026-10-28) [S9]. Collider fixes made for stage 1 apply unchanged.
- **Spring bone with sphere/capsule colliders: the real-time equivalent of D.** The VRM `VRMC_springBone` spec defines spring chains that collide with sphere and capsule colliders [S5]. It is a likely target if the viewer is not MMD-based, and the MMD capsules map onto it fairly directly.
- **Classic Cloth (B), GN Dynamics (C), Shrinkwrap and Corrective Smooth: do not carry over.** They are Blender-only evaluation. The Stretch To bone mode of the converter can be baked to bones, so a baked dance can still play back, but it won't respond to new motion.
- **Mask, weight fixes, corrective shape keys and motion smoothing carry over.**

## What could not be determined

- How good the model's shipped rigid bodies actually are, which ones are missing, and whether the skirt tiers are rigged as separate chains. That needs the model opened locally, and per the repo rules it is never committed. Inspecting it is the first step of building.
- Whether MMD Tools v4.5.14 runs cleanly on Blender **5.3**. Its README stops at 5.2 and nothing was tested here; 5.2 LTS is the safe choice.
- Actual bake times for cloth with self-collision on an M4 Max for a full dance. No benchmark exists in the sources; measure it.
- How stable Blender's rigid-body world is with this model's joint count. The MMD Tools maintainers warn of crashes in general [S1], but give no figures.

## Sources

Primary sources were read on 2026-11-26. Blender manual pages were read from the manual's source repository (`blender-manual`, branch `main`), which builds docs.blender.org/manual/en/latest.

- [R1] Blender release notes index and 5.0/5.2/5.3 pages: https://developer.blender.org/docs/release_notes/ (5.0 released 2025-11-18, drops Intel Mac; 5.2 LTS released 2026-07-14; 5.3 released 2026-11-10)
- [S1] MMD Tools repository and README (compatibility table, Known Issues → Rigid Body Physics Limitations), `mmd_tools/blender_manifest.toml`, releases: https://github.com/MMD-Blender/blender_mmd_tools
- [S2] PMX format description (English), rigid body and joint sections: https://gist.github.com/felixjones/f8a06bd48f9da9a4539f
- [S3] MMD Tools Append README and wiki ("Physics Converter", credit to 小威廉伯爵 / Miku_Miku_Rig): https://github.com/MMD-Blender/blender_mmd_tools_append, https://github.com/MMD-Blender/blender_mmd_tools_append/wiki/Home
- [S4] MMD Tools Append source, `mmd_tools_append/converters/physics/rigid_body_to_cloth.py`: https://github.com/MMD-Blender/blender_mmd_tools_append/blob/main/mmd_tools_append/converters/physics/rigid_body_to_cloth.py
- [S5] VRM `VRMC_springBone-1.0` specification: https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_springBone-1.0/README.md
- [S6] Wiggle 2 repository, commits, releases and issues #102, #110, #112, #117: https://github.com/shteeve3d/blender-wiggle-2
- [S7] Spring Bones repository and README: https://github.com/artellblender/springbones
- [S8] MMDBridge README (system requirements): https://github.com/rintrint/mmdbridge
- [S9] babylon-mmd README (physics runtime): https://github.com/noname0310/babylon-mmd
- [S10] Blender Manual, Rigid Body World: https://docs.blender.org/manual/en/latest/physics/rigid_body/world.html
- [S11] Blender Manual, Rigid Body Constraints introduction: https://docs.blender.org/manual/en/latest/physics/rigid_body/constraints/introduction.html
- [S12] Blender 5.2 release notes, Physics (Geometry Nodes Hair/Cloth Dynamics, XPBD Solver, colliders): https://developer.blender.org/docs/release_notes/5.2/physics/
- [S13] Blender Manual, Geometry Nodes Cloth Dynamics: https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/simulation/cloth_dynamics.html
- [S14] Blender Manual, Geometry Nodes Hair Dynamics: https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/simulation/hair_dynamics.html
- [S15] Blender Manual, Collision (soft body and cloth, modifier order, thickness, single sided): https://docs.blender.org/manual/en/latest/physics/collision.html
- [S16] Blender Manual, Cloth Settings (Quality Steps) and Cloth Shape (Pin Group, Dynamic Mesh): https://docs.blender.org/manual/en/latest/physics/cloth/settings/index.html, https://docs.blender.org/manual/en/latest/physics/cloth/settings/shape.html
- [S17] Blender Manual, Cloth Collisions (object/self collision, troubleshooting): https://docs.blender.org/manual/en/latest/physics/cloth/settings/collisions.html
- [S18] Blender Manual, Cloth Introduction (workflow; "make sure that the cloth object does not penetrate any of the Collision objects"): https://docs.blender.org/manual/en/latest/physics/cloth/introduction.html
- [S19] Blender Manual, Surface Deform Modifier: https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/surface_deform.html
- [S20] Blender Manual, Graph Editor F-Curve editing, Butterworth Smooth: https://docs.blender.org/manual/en/latest/editors/graph_editor/fcurves/editing.html
- [S21] Blender Manual, Mask Modifier: https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/mask.html
- [S22] Blender Manual, Armature Modifier (Preserve Volume): https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/armature.html
- [S23] Blender Manual, Smooth Corrective Modifier: https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/corrective_smooth.html
- [S24] Blender Manual, Shrinkwrap Modifier (snap modes, "very crude collision detection"): https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/shrinkwrap.html
- [S25] Blender Manual, Shape Keys introduction (relative keys for corrective poses): https://docs.blender.org/manual/en/latest/animation/shape_keys/introduction.html
- [S26] MuJoCo XML reference, geom `contype` / `conaffinity`: https://mujoco.readthedocs.io/en/stable/XMLreference.html#body-geom-contype
