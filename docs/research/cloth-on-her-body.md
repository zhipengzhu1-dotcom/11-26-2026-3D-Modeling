# Cloth on her body

Research done 2026-11-28 against Blender 5.2 LTS, MMD Tools v4.5.14, MMD Tools Append v4.5.14, Newton v1.8.0 and the ZOZO contact solver (release of 2026-11-28). It builds on `docs/research/secondary-physics-no-clipping.md` (branch `research/secondary-physics-no-clipping`), called "the earlier study" below. Nothing in this file is derived from the model.

**Question.** Her Secondary Physics now reuses the model's own MMD rigid bodies and joints. Her skirt is strips of rigid pieces on joints: the strips swing but do not drape. At an Eye Check the human said her clothes are rigid, do not fall, and do not combine with her body. Against her shipped body shapes her skirt still goes up to 32 mm into her thigh. How can her skirt and sleeves be made to fall, drape and rest on her body, colliding with it the way cloth does? What have others done for MMD and anime characters, and what should we try first?

## Answer

1. **On the Mac, first: Blender's classic Cloth on a low-poly proxy of the skirt, colliding with a collision copy of her drawn hips and legs, driving the Visible Mesh through Surface Deform. All of it is built and baked by a headless script.** This is the earlier study's fallback, and it still holds. One change is that we should build the proxy ourselves rather than rely on the MMD Tools Append converter as it ships. The converter only makes cloth *faces* where the skirt's rigid bodies are joined sideways into closed quads. Where the chains are joined only top to bottom, it makes thin ribbons that drive bones with *Stretch To* instead of a draping surface. It also sets no collision on her body and does not turn on self-collision [S3]. Read its source as the pattern to follow, and as a quick check of what her joints allow.
   - The collider should be her **drawn** hips and legs, deformed by the same armature. Her Simulation Body's solids should not be the collider: they are deliberately bulkier than her drawn body [ADR 0004], so the skirt would rest visibly off her legs (浮空).
   - The settings that matter for fast dancing are Quality Steps, collision Quality, a small object and self-collision Distance, a collider Thickness Outer of a few millimetres, Single Sided on the collider, and a second of rest-pose pre-roll. All of them are verified in the manual [S6][S7][S8].
   - Blender's cloth moves the collider and the pinned vertices smoothly between frames on every substep, as its source shows [S9]. Raising Quality Steps therefore really does help against her fast limbs.
2. **On the PC, if that falls short: the ZOZO contact solver ("ppf-contact-solver"), driven from her Blender on the Mac through its Python API, with the solver running on the RTX 5090 over the home network.** It is open (Apache-2.0) and maintained daily. It takes armature-deformed colliders and armature-driven pins through "Capture Deformation", and it guarantees that every step it completes is free of intersections [S11][S12][S13]. It is also the only maintained open cloth solver found that is already integrated with Blender. Its weak points: its author calls it "not production ready" and "not the fastest", and it cannot resolve a body animation that intersects itself [S11][S14].
   - **Newton's VBD and Style3D cloth solvers are the other PC route,** and the better one to carry into the Live Session. They take bodies whose poses are written from outside (one-way coupling), and Newton's own example dresses a humanoid robot whose pose is set each frame. They run headless from plain Python [S15][S16][S17]. They need more of our own plumbing: piecewise-rigid colliders, writing pinned vertices ourselves, and a PC2 file back to Blender.
3. **The smallest tests on her.** Run each route on the same two clips: her skirt on a 5-second held pose, then on the 50-second dance with its turns and its high leg (detail [below](#the-smallest-tests)). A route passes when:
   - the skirt visibly falls and comes to rest on her legs at the Eye Check;
   - the 穿模 scan's worst skirt-into-thigh Overlap drops from 32 mm to a few millimetres;
   - no frame shows tiers passing through each other, an explosion, or a cloth that stays caught on a limb;
   - its bake time on the Mac (or the PC) is recorded.
4. **Leave her hair on the rigid bodies.** None of the cloth routes here serves hair to her ankles well. Fix hair against her hands by adding hand and forearm colliders to the hair's collision groups, as the earlier study planned ([Hair](#her-hair)).
5. **Honest caveat.** I found **no public example of anyone doing layered anime skirt tiers with cloth on a fast dance and getting a clean result.**
   - The public posts show single skirts, with some 穿模 left over. One author fixed knee 穿模 by hand with Hook bones, and the ankle still went through [P1].
   - Another tool's documented fix for arms passing through a skirt is to delete the arms from the collider [P2].
   - Several Bilibili videos with tens of thousands of views show the MikuMikuRig rigid-body-to-cloth conversion on MMD models, but only as video, so their settings could not be read [P4][P5].

   Expect to tune, and expect the tiers to be the hard part.

## Constraints that decide what is usable

- **Words.** In this file "proxy" always means the low-poly cloth mesh that stands in for the drawn skirt, and "leg collider" means a mesh cut from her drawn legs. Neither is her Simulation Body; GLOSSARY lists "proxy" under Avoid as a name for it. "Penetration-free" is the tools' own term; in this project's words, it means no Overlap.
- **Made by code** [ADR 0003]. Every route must run from a headless Blender script or the command line. That rules out two of the remedies in the public posts:
  - the manual's own last resort for collisions, which is to edit the cached result by hand in Edit Mode [S7];
  - Hook bones placed by hand to keep a knee out of the skirt [P1].

  Either could only come back as a recorded Guided Hand Fix.
- **One-way.** Secondary Physics is driven by her body's motion and never pushes back. Her body's motion arrives as per-frame rotations of her 19-part Simulation Body, written back onto her MMD rig. Every route below therefore uses a collider that is *moved* (kinematic), and none needs two-way coupling.
- **Her Visible Mesh is one mesh of 77k triangles.** The skirt is layered tiers with inner and outer surfaces as separate materials, alongside bell sleeves, ribbons and ankle-length hair. A cloth solver should not run on the drawn skirt directly: it is too dense, and its two surfaces would collide with each other. Run it on a proxy and carry the result back to the drawn surface.
- **Machines.** The Mac (M4 Max, 36 GB, Blender 5.2 LTS) builds and films her. The Windows PC with an RTX 5090 is reserved for Isaac Lab, Newton and MuJoCo Warp. Nothing is rented, which rules out the ZOZO solver's suggestion to rent remote GPUs [S11].
- **Live Session later.** For each route, the [Real-time counterparts](#real-time-counterparts) section says whether there is a real-time path.
- **Licences.** The model's licence allows improving its physics. MMD Tools and MMD Tools Append are GPL-3.0 [S1][S2]. Calling them from our scripts is fine. Copying their code into this repo would bring the GPL with it, so reimplement the pattern rather than paste it.

## 1. Cloth in Blender against her moving body

### What the converters actually build (read from source)

The study read MMD Tools Append's `converters/physics/rigid_body_to_cloth.py` at v4.5.14 [S3] and its ancestor in MikuMikuRig, `mmr_operators/physics.py` [S4]. The code credits 小威廉伯爵 (MikuMikuRig) and UuuNyaa, and the Append wiki says the feature was ported with his permission [S2]. The old "UuuNyaa tools" repository is now the same project: `UuuNyaa/blender_mmd_uuunyaa_tools` redirects to MMD Tools Append [S2].

Step by step, `RigidBodyToClothConverter.convert` does the following [S3]:

1. **One vertex per selected rigid body**, at the rigid body's location. Edges are added only for joints whose two ends are both among the selected rigid bodies. The joint objects are then deleted.
2. **Faces only from closed four-sided loops.** It runs `bmesh.ops.holes_fill(..., sides=4)` and then removes every edge that is not a joint edge. A face appears only where four rigid bodies are linked into a quad by two vertical joints and two horizontal (side) joints.
   - If her skirt's strips are joined only down each strip, no faces appear. Every vertex is then a "wire" vertex, which the code calls a *ribbon* vertex.
3. **Edges extended upward to the parent bone's head and downward to the last bone's tail,** then filled into faces, so the cloth reaches the waist and the hem. Side edges are extended outward. Ribbon vertices get a second vertex 0.01 away in Y so they form a thin strip.
4. **Pinning.** A `physics_cloth_pin` vertex group holds the top-row vertices that the side joints connect to non-cloth rigid bodies. Each of these vertices is also weighted to the bone of the body it was joined to. An **Armature modifier** limited to that group carries the pinned row with her hips. Ribbon vertices get a pin weight equal to *Ribbon Stiffness* (default 0.2).
5. **Modifiers on the cloth object:**
   - a Subdivision Surface, default level **0**;
   - the Armature modifier;
   - a Cloth modifier whose only setting is `vertex_group_mass = physics_cloth_pin`. Everything else stays at Blender's defaults: **no self-collision is enabled**;
   - a Corrective Smooth, bound at creation.
6. **How the drawn mesh follows**, chosen by *Physics Mode* (default **Auto**):
   - *Surface Deform*: the vertex weights of the converted bones are merged into a `physics_cloth_deform` group on the MMD mesh, those bones' groups are removed, and a Surface Deform modifier is bound to the cloth.
   - *Bone Constraint*: each physics bone gets a **Stretch To** constraint aimed at a one-vertex group on the cloth. The bones still move, so the result can be baked back to bones.
   - *Auto* uses Stretch To for ribbon vertices and Surface Deform for the rest.
7. **The rigid bodies are deleted.**

Things it does **not** do:

- It adds no Collision modifier to anything. Blender's cloth collides only with objects that have Collision physics [S7]. The separate "Collision Adjuster" panel offers one preset, *Thin Smooth*: Thickness Outer 0.001, Inner 0.2, friction 0, damping 0 [S3a].
- It adds no self-collision and no tier-to-tier handling.
- It only touches the Quality settings when a person uses the "Cloth Adjuster" panel. The cloth presets there are *Cotton* (mass 0.3, stiffness 15, bending 0.5, damping 5) and *Silk* (mass 0.15, stiffness 5, bending 0.05, damping 0) [S3b].
- The MikuMikuRig original sets compression and shear stiffness to 0 [S4]. The Append port leaves them at their defaults.

**Can it run headless?**

- The operator gets its rigid bodies and meshes from the selection and opens a dialog in `invoke` [S3b]. A script can skip both by calling `RigidBodyToClothConverter.convert(...)` directly with explicit lists.
- Inside, `convert` calls `bpy.ops.object.mode_set`, `correctivesmooth_bind` and `surfacedeform_bind`, which need an active object in the view layer.
- Whether this runs cleanly under `blender -b` was **not tested**, because this was reading only.

**What this means for her.** Whether the converter gives her a draping surface or only stiff ribbons depends on whether her skirt's rigid bodies have **side joints** between neighbouring strips. A Build script can count those from the PMX joints without opening a window. If the side joints are missing, or join only some strips, build our own proxy the same way:

- a ring grid with one row per chain level and one column per strip, closed around her;
- the top row pinned to her lower-body bone;
- each tier as rows of the same proxy or as its own ring.

Either way, set the cloth and collision settings explicitly. The defaults are not tuned for a dancer.

### The proxy and how it drives the drawn surface

- **Surface Deform** is the manual's own named use for "a proxy mesh for cloth simulation". The proxy must have no edges shared by more than two faces, no concave faces, no doubled vertices and no collinear edges [S19 of the earlier study].
  - Restrict it with a vertex group to the skirt's vertices. Both the inner and the outer skirt surfaces then bind to the same proxy and keep their spacing.
  - The proxy must be bound in rest pose.
- **Keep the proxy coarse but not too coarse.** Two public reports pull in opposite directions:
  - A 2018 Blender Artists thread found a low-poly skirt reacting "as if strong wind" when a leg rose, and subdividing it twice mostly fixed that [P6].
  - In 2024, Nakao Sora put a cloth skirt on an anime character dancing an MMD motion. She found that subdividing the proxy against 穿模 made the ruffles messy, and kept it coarse [P1].
  - Start with about one vertex per drawn ruffle, and measure.
- **Scale.** Blender's cloth depends on real size. Nakao Sora ran her proxy and its collision copy scaled up 20× inside a Geometry Nodes sandwich, and says she does not know the best value [P1]. That is a tuning trick resting on one post, not documentation. First check that her imported size is roughly real-world, then tune mass and Quality.

### Pinning at the waist

- Pinned vertices follow their Armature modifier, which must sit above the Cloth modifier. The Pin Group is set under Shape, with a Pin Stiffness [S8].
- In the solver, pinned vertices move smoothly from their old to their new position across the substeps of each frame (`cloth.cc`, the `xold`/`xconst` interpolation) [S9]. Fast hip rotations therefore do not jerk the waist row.
- *Dynamic Mesh* lets the rest shape follow the armature every frame [S8]. It is worth trying for a waistband that should stretch with her hips rather than slide.

### Her body as the collider, and its shape

- **Make it a separate mesh** cut from her Visible Mesh by the vertex weights of her hip and leg bones. Deform it with the same Armature modifier and put the **Collision modifier after the Armature** [S7]. Hide it in renders.
- **Use hips and legs only to start.** The Blender-Vmd-Retargeting add-on's documented fix for arms passing through a skirt is to delete the arm vertices from the collision proxy [P2]. The cloth then cannot be caught on a passing arm. Add hands back only if the Eye Check shows hands passing through the skirt.
- **Not her Simulation Body's solids.** ADR 0004 makes them follow her clothed outline and run bulkier than her drawn body. Against them the skirt would rest visibly off her thighs. The earlier work already measured that hair sinks into her more often against those solids.
- **Settings, from the manual** [S7][S6]:
  - Collision *Thickness Outer* is a padding the cloth comes to rest at.
  - *Single Sided* treats the collider as a solid and "ejects intersecting cloth in the direction of its normal", which helps with a leg that has already got inside the skirt. It only works if the leg's normals face outward.
  - Use a small cloth object-collision *Distance*. Too large looks like the cloth "is resting on air".
  - Put the collider in a *Collision Collection* so the cloth ignores everything else.
- **Closed meshes are not required** by classic Cloth, but they are required by the Geometry Nodes cloth [S10]. A closed, slightly shrunk leg mesh is the safe choice for both.

### Self-collision and the layered tiers

- The manual says a close-up "cape or blouse on a character should have this enabled". It adds compute time, and it has its own Distance and Impulse Clamping [S7]. A vertex group can exclude faces from self-collision [S7], which is useful for the waistband rows, where tiers are sewn together.
- How to arrange the tiers is a judgement call; neither option is documented for this case:
  - **One proxy holding all the tiers**, joined at the waist, with self-collision on. Tier-against-tier is then plain self-collision inside one solve, so there is no question of which cloth object is solved first.
  - **A separate cloth object per tier,** where the inner tier also carries a Collision modifier for the outer one. This is the other option, but it is one-way per frame.
- Start with one proxy.

### Fast dance moves: quality and distance

From the manual's troubleshooting [S7], in its own order:

1. raise Distance (fastest, least accurate);
2. raise Quality Steps, so the solver takes smaller steps and catches fast collisions [S6];
3. raise collision Quality;
4. edit the cache by hand, which ADR 0003 rules out.

Verified in Blender 5.2's source: the collider mesh is moved from its previous to its current position *inside* each substep (`collision_move_object(collmd, step + dt, step, false)` in `collision.cc`) [S9]. More Quality Steps therefore really thin out the gap a fast thigh can jump through.

Practical order for her:

- smooth the jitter out of her body motion (earlier study);
- add a one-second rest-pose pre-roll so nothing starts inside the collider. The manual warns that a cloth starting inside a collider makes the simulation unstable (earlier study [S18]);
- start at Quality Steps about 10 and collision Quality about 4, then double them for the turns and the high leg, and measure the bake time.

### Known failures and the remedies people report

| Failure | Remedy reported | Source |
|---|---|---|
| Leg passes through the skirt like a noren curtain (rigid-body skirts) | Add horizontal joints around the hem and leg colliders; separate leg and skirt bodies at rest | Rigid-body post [P3] |
| Low-poly cloth skirt flaps "as if strong wind" when a leg rises | Subdivide the cloth twice; lowering damping or raising the speed multiplier did not help | Forum thread [P6] |
| Knee and ankle go through a cloth skirt on an MMD dance | Hook bones placed by hand (not usable under ADR 0003); ankle still went through | [P1] |
| Arms pass through and catch the skirt | Delete the arms from the collision proxy | [P2] |
| The body cannot be used as a collider at all | Use a simple proxy such as a cylinder | Artist quoted by 80.lv [P7] |
| Cloth explodes in tight collisions | Impulse Clamping, object and self | Manual [S7] |
| Cloth starts inside the collider | Start from a pose where it is outside, with pre-roll | Manual (earlier study [S18]) |

### Baking headless

- The cache is per frame and saved with the blend file [S7].
- For a headless Build, step the frames in order from Python, or call the point-cache bake operator. Then export the baked proxy as Alembic, or keep the Surface Deform result in the Build's own blend file.
- Neither path was run here.

## 2. Cloth outside Blender

| Tool | Licence | Mac (Apple Silicon) | PC (RTX 5090) | Last release / commit | Animated-body collider | Back into Blender | Used for a character's clothes? |
|---|---|---|---|---|---|---|---|
| **ZOZO contact solver** (st-tech/ppf-contact-solver) | Apache-2.0 | Yes: native Metal and CPU backends, which the author calls "slow … for small examples" [S11] | Yes: CUDA, "RTX 4090 / 5090 for large scenes" [S11] | Release 2026-11-28 | Yes: an armature or shape-key-deformed collider is recorded with *Capture Deformation*; armature-driven pins likewise [S12][S13] | Its own Blender add-on fetches frames as `MESH_CACHE` modifiers; USD and Alembic export pages [S12a] | It drapes cloth over mannequins and colliders driven by a body rig [S12]. No anime-dance example found |
| **Newton** VBD and Style3D solvers | Apache-2.0 | CPU only on macOS [S15] | Yes, CUDA, with CUDA graphs | v1.8.0, 2026-11-11 | Yes: `integrate_with_external_rigid_solver=True` gives one-way rigid-to-cloth contact; the `cloth_h1` example sets a robot's pose each frame and runs the Style3D cloth against it [S16][S17] | Nothing built in. Write the particle positions per frame to PC2 or MDD (Blender's Mesh Cache reads both) [S18], or use Newton's USD viewer | `cloth_h1`: a humanoid in a jacket (a "cake skirt" garment is also named in the code) [S17] |
| NVIDIA **Warp** on its own | Apache-2.0 | CPU wheels only, no Metal [S19] | Yes | v1.19.0, 2026-11-02 | `warp.sim` was removed and "superseded by the Newton library" [S19] | — | Use Newton instead |
| **HOOD**, **ContourCraft** (neural garments) | MIT code; needs SMPL body models from the SMPL site | PyTorch CUDA | Yes | Last commits 2025-05 and 2025-08 | Can run from "arbitrary mesh sequence" notebooks [S20] | Mesh sequences | Trained on realistic garments on SMPL bodies. Research code; not a fit for frilled anime tiers, and not tried |
| Codim-IPC | Apache-2.0 | — | — | Last commit 2022-11 | — | — | Unmaintained; skip |
| Marvelous Designer, Houdini Vellum | Commercial | — | — | — | Yes | Alembic | Widely used, but closed and paid. Houdini can run headless through `hython`; Marvelous Designer's scripting runs inside its window. Not verified here; out of scope because nothing is rented or bought |

**What the ZOZO solver asks of her.**

- **Inputs must start apart.** It promises that every step it completes is free of intersections, using continuous collision detection with a cubic barrier [S11]. Its own criticism list records a cloth "trapped in a self-intersecting character animation, which the solver cannot resolve" [S14]. So her collider must not pass through itself: no thigh through thigh at a deep bend. Her skirt tiers must not overlap each other in rest pose.
- **Script control is partial.**
  - Its Blender Python API (`solver.create_group(..., type="STATIC")`, `create_pin`, and so on) drives the whole pipeline from a script, and an MCP server can drive it too [S11][S12].
  - **Whether that API runs under `blender -b` is not documented.**
  - Each Capture Deformation is a snapshot that must be re-captured when the motion changes, and it aborts if a modifier that changes the vertex count, such as Subdivision, sits in the stack [S13].
- **Network setup.** The solver is a separate server. On Windows it starts from `start.bat` or Docker, and the Blender add-on connects over SSH or a port [S11]. That matches this setup: Blender on the Mac, the solver on the PC.

**What Newton asks of her.**

- **Colliders.** Her colliders become rigid shapes on bodies whose `body_q` we write each frame from her Simulation Body's 19 rotations. A leg mesh cut per bone works as a piecewise-rigid collider; it has no skinning at the joints.
- **Pins.** The pinned waist row would be zero-mass particles whose positions we write. VBD's one-way mode does not support *attachments* [S16].
- **No Blender tooling.** The rest is ours to write: the proxy in, positions out as PC2.

In exchange, it is the same engine family as her training stack on the PC. It also has a documented penetration-free option for self-contact and rigid-to-cloth contact (DAT truncation), with tuning guides for tunnelling and fast motion [S16].

## 3. What MMD and anime-character makers actually do

- **Most MMD skirts stay on rigid bodies.** Two how-to posts deal with the leg coming through the skirt by tuning rigid bodies, not by switching to cloth:
  - りこぴん's 2022 note.com series adds horizontal joints around the hem and leg rigid bodies [P3].
  - LearnMMD's PMDE Q&A says that where the skirt is too tight for colliders, you delete the physics and weight the skirt to the legs (in search results; not opened).
- **The rigid-body-to-cloth conversion is the community's cloth route for MMD.** MikuMikuRig (by 小威廉伯爵; last commit 2023-02; no licence file; v0.56 from 2022) builds cloth from the MMD rigid bodies, with Surface Deform and bone-constraint modes [S4]. Bilibili tutorials show it, including:
  - 鹞猫's "十分钟学会在Blender中对MMD模型服装的实时布料模拟" (2022, about 50k views) [P4];
  - TedNE's 2018 conversion of a qipao's rigid bodies to cloth [P5].

  Their pages give no written settings, so this study could not check what they showed beyond their titles. A translated Derxx Animations tutorial (about 48k views on Bilibili) is likewise video only [P8].
- **The anime character with a cloth skirt on an MMD dance:** Nakao Sora, note.com, 2024-12-28 [P1]. This is the closest public match. Her setup, all read from her post:
  - a coarse proxy;
  - Armature at 100% on the waist bone;
  - a pin group with a gradient from the root;
  - Surface Deform onto the drawn skirt, plus Solidify;
  - a collision copy of the legs;
  - the ×20 scale trick, and Hooks placed by hand for the knee.

  She reports some 穿模 left over, and the ankle still going through.
- **Proxies for speed.** Blender-Vmd-Retargeting's documented "Create Proxy" workflow decimates the body and the garment. It sets body-proxy Thickness Outer to 0.002, pins with the garment's existing pin group, and deletes the arms from the body proxy [P2].
- **Not found:** any Japanese primary write-up of the rigid-body-to-cloth converter, or any public result with *layered* tiers.

## 4. Real-time counterparts

| Route today | Real-time counterpart |
|---|---|
| MMD rigid bodies (current) | Bullet MMD runtimes such as babylon-mmd (MIT, last commit 2026-10-28) [S21]; VRM spring bones (earlier study) |
| Blender classic Cloth on a proxy | None inside Blender. The *proxy, pin row and leg collider* all carry over to a real-time cloth system: Newton VBD or Style3D on the PC GPU, Unity Magica Cloth 2, or Unreal Chaos Cloth. In bone mode the converter's Stretch To bones can be baked, but they replay without responding to new motion |
| ZOZO contact solver | Offline only: "Not real time" by its author's own account [S14] |
| Newton VBD / Style3D | The same code could run live on the RTX 5090 if her Live Session runs there. No real-time timings for a garment of her size were found |

How common real-time systems handle the body:

- **Magica Cloth 2** (Unity, paid asset): MeshCloth and BoneCloth, sphere, capsule and plane colliders, self- and mutual collision, and a normal-based "Backstop" against penetration [S22].
- **Unreal Chaos Cloth:** collides with simple shapes. Forum reports say spheres and capsules work reliably and convex shapes do not. Self-collision is set by per-vertex spheres [S23].

So in real time, body collision means capsules and spheres, plus a backstop. Today's leg collider should therefore also be kept as capsules, so it can carry over.

## 5. Her hair

**Keep her hair on the rigid bodies.**

- Classic Cloth is for surfaces. Ankle-length strands as cloth would need ribbon proxies and their own collisions, which is the converter's weak "ribbon" path [S3].
- Blender's Geometry Nodes Hair Dynamics works only on Curves hair [S10 of the earlier study]. Its Cloth Dynamics still lacks self-collision in the current manual [S10]. Blender 5.3's release notes have no physics page.
- Newton has rods and cables in VBD [S16], but nothing for anime hair was found.

Fix the hair-into-hands problem where it lives:

- add her hand and forearm follow-bone bodies to the hair chains' collision groups;
- tune those groups' non-collision masks.

ADR 0004 already leaves hands-through-hair to Secondary Physics. If her long back hair is drawn as a broad sheet rather than strands, that one sheet could later go on the same proxy route as the skirt.

## The smallest tests

**Mac test (Blender Cloth), Build-script only:**

1. Count the side joints between her skirt chains from the PMX data, and record the count in the Build log, not in git. Run the converter in Surface Deform mode on one tier as a quick look, then build our own ring proxy for all the tiers.
2. Set up the cloth:
   - Pin the top row to her lower-body bone.
   - Cut a collider of her drawn hips and legs and give it Collision after the Armature, Thickness Outer about 3 mm, and Single Sided.
   - On the cloth: Quality Steps 10, collision Quality 4, Distance about 3 mm, self-collision on with Distance about 2 mm, and Impulse Clamping set.
   - Add a one-second rest-pose pre-roll.
3. **5-second held pose.** Pass if the skirt falls and settles on her legs at the Eye Check, and the 穿模 scan's skirt-into-thigh Overlap is under about 3 mm.
4. **50-second dance.** Pass if there is no explosion, the high-leg and turn frames show no tier-through-tier or leg-through-skirt in the ten worst moments, the worst Overlap is a few millimetres, and the bake time is noted. If it fails, double Quality Steps once and re-measure before changing anything else.

**PC test, run only if the Mac test fails on penetration or tangling:**

1. Start the ZOZO solver on the PC with its Windows build.
2. From Blender on the Mac, script the same proxy as a SHELL group, the leg collider as STATIC with Capture Deformation, and the waist row as a captured pin. First check that neither the collider nor the tiers intersect in rest pose.
3. Run the same 5-second and 50-second clips and apply the same pass marks.
4. Separately, as the route towards the Live Session: a Newton script that loads the proxy and the per-bone leg shapes, writes `body_q` from her rotations, steps VBD with self-contact on, and writes PC2 for Blender's Mesh Cache.

## What is verified, what rests on posts, what is missing

- **Verified by reading source code:**
  - what the MMD Tools Append and MikuMikuRig converters build [S3][S4];
  - Blender cloth's per-substep collider and pin interpolation [S9];
  - Newton's kinematic-body cloth example [S17].
- **Verified in official documentation:**
  - Blender's cloth, collision and Mesh Cache settings [S6][S7][S8][S18];
  - the Geometry Nodes cloth limits [S10];
  - Newton's VBD coupling modes and platforms [S15][S16];
  - the ZOZO solver's platforms, guarantee, deformation capture and pins [S11][S12][S13];
  - Warp's removal of `warp.sim` [S19].
- **Rests on someone's post:**
  - the scale-up trick, coarse versus fine proxy, Hooks for the knee [P1];
  - deleting the arms from the collider [P2];
  - rigid-body skirt fixes [P3];
  - the subdivision fix [P6];
  - the proxy cylinder [P7];
  - Chaos Cloth's collider behaviour [S23];
  - the ZOZO solver's real-world problems [S14].
- **Could not find or verify:**
  - any layered anime skirt done well with cloth on a fast dance;
  - the content of the Bilibili and YouTube video tutorials [P4][P5][P8];
  - whether the converter and the ZOZO Blender API run under `blender -b`;
  - bake times on the M4 Max for any route;
  - the ZOZO solver's speed on Metal for a garment of her size;
  - Newton cloth timings for a garment of her size on the RTX 5090;
  - whether her skirt's rigid bodies have side joints. That needs the model, which stays out of git.

## Against the earlier study and the decision records

- The earlier study describes the converter as building a cloth mesh from the rigid bodies and joints and then "fill[ing] faces". That is accurate, but it misses that faces form **only where side joints close quads**. Without them the converter falls back to bone-driven ribbons. It also does not mention that the converter sets **no collision and no self-collision**. Its claim that this converter "builds exactly this proxy" therefore holds only if her skirt has side joints.
- Its claim that Classic Cloth "does not carry over to real time" still holds for Blender's solver. However, the *setup* (proxy, pins, leg collider) carries over to Newton's GPU cloth on the PC, so choosing cloth now is not a dead end for the Live Session.
- Its versions still hold:
  - MMD Tools v4.5.14 lists Blender 4.2–5.2 [S1];
  - MMD Tools Append v4.5.14 (2026-11-13) lists 4.2–5.3 [S2];
  - the Geometry Nodes cloth still lacks self-collision [S10].
- No conflict with ADR 0003, provided that hand edits to the cache and Hooks placed by hand are not used.
- Consistent with ADR 0004: the skirt collider should be her drawn legs, *not* her bulky Simulation Body solids.

## Repos examined

| Repo | Licence | Last commit | Good for |
|---|---|---|---|
| MMD-Blender/blender_mmd_tools | GPL-3.0 | 2026-11-19 | Import, rigid bodies (current Secondary Physics) |
| MMD-Blender/blender_mmd_tools_append (formerly UuuNyaa tools) | GPL-3.0 | 2026-11-13 | Rigid Body to Cloth converter; the pattern for our proxy builder |
| 958261649/Miku_Miku_Rig | none stated | 2023-02-03 | The original converter; reference only |
| st-tech/ppf-contact-solver | Apache-2.0 | 2026-11-28 | Penetration-free offline cloth, Blender add-on, Metal and CUDA |
| newton-physics/newton | Apache-2.0 | 2026-11-27 | GPU cloth (VBD, Style3D) with kinematic bodies; the Live Session path |
| NVIDIA/warp | Apache-2.0 | 2026-11-28 | Base of Newton; `warp.sim` removed |
| Dolorousrtur/HOOD, Dolorousrtur/ContourCraft | MIT (+ SMPL licence) | 2025-05-20, 2025-08-02 | Neural garment research; not a fit |
| ipc-sim/Codim-IPC | Apache-2.0 | 2022-11-01 | Unmaintained |
| noname0310/babylon-mmd | MIT | 2026-10-28 | Real-time MMD rigid bodies |
| butaixianran/Blender-Vmd-Retargeting | (not checked) | (not checked) | Its README's cloth-proxy workflow [P2] |

## Sources

Read 2026-11-28. GitHub sources were read through the GitHub API at their default branch. Blender manual and source pages were read from projects.blender.org.

- [ADR 0003] `docs/adr/0003-made-by-code-never-by-hand.md`; [ADR 0004] `docs/adr/0004-simulation-body-follows-clothed-outline.md`
- [S1] MMD Tools README (Blender 4.2–5.2), releases: https://github.com/MMD-Blender/blender_mmd_tools
- [S2] MMD Tools Append README (Blender 4.2–5.3), release v4.5.14, wiki "Physics Converter": https://github.com/MMD-Blender/blender_mmd_tools_append, https://github.com/MMD-Blender/blender_mmd_tools_append/wiki/Home
- [S3] `mmd_tools_append/converters/physics/rigid_body_to_cloth.py`; [S3a] `converters/physics/collision.py`; [S3b] `converters/physics/cloth.py` (presets, `ConvertRigidBodyToClothOperator`), and `editors/meshes.py`: https://github.com/MMD-Blender/blender_mmd_tools_append/tree/main/mmd_tools_append/converters/physics
- [S4] MikuMikuRig `MikuMikuRig/mmr_operators/physics.py`: https://github.com/958261649/Miku_Miku_Rig
- [S6] Blender Manual, Cloth Settings (Quality Steps, Speed Multiplier): https://projects.blender.org/blender/blender-manual/src/branch/main/manual/physics/cloth/settings/index.rst
- [S7] Blender Manual, Cloth Collisions (object and self collision, Distance, Impulse Clamping, Collision Collection, troubleshooting) and Collision (modifier after the Armature, Thickness, Single Sided): https://projects.blender.org/blender/blender-manual/src/branch/main/manual/physics/cloth/settings/collisions.rst, https://projects.blender.org/blender/blender-manual/src/branch/main/manual/physics/collision.rst
- [S8] Blender Manual, Cloth Shape (Pin Group, Sewing, Shrinking, Dynamic Mesh): https://projects.blender.org/blender/blender-manual/src/branch/main/manual/physics/cloth/settings/shape.rst
- [S9] Blender source, branch `blender-v5.2-release`: `source/blender/blenkernel/intern/collision.cc` (line 1598, `collision_move_object(collmd, step + dt, step, false)`), `source/blender/simulation/intern/SIM_mass_spring.cc` (substep loop, pinned-vertex interpolation): https://projects.blender.org/blender/blender
- [S10] Blender Manual, Geometry Nodes Cloth Dynamics ("Some features are currently missing, such as self-collision"; closed colliders only; tunnelling): https://projects.blender.org/blender/blender-manual/src/branch/main/manual/modeling/geometry_nodes/simulation/cloth_dynamics.rst; Blender 5.3 release notes index (no physics page): https://projects.blender.org/blender/blender-developer-docs/src/branch/main/docs/release_notes/5.3
- [S11] ZOZO contact solver README (limitations, requirements table, penetration-free guarantee, Python scripting, MCP): https://github.com/st-tech/ppf-contact-solver
- [S12] ZOZO solver Blender add-on docs, Python API: https://st-tech.github.io/ppf-contact-solver/blender_addon/integrations/python_api.html; Static Objects: https://st-tech.github.io/ppf-contact-solver/blender_addon/workflow/scene/static_objects.html; [S12a] docs index (baking, exporting): https://st-tech.github.io/ppf-contact-solver/blender_addon/
- [S13] ZOZO solver Pins (Capture Deformation, Pull): https://st-tech.github.io/ppf-contact-solver/blender_addon/workflow/constraints/pins.html
- [S14] ZOZO solver, "Criticism for Fairness": https://github.com/st-tech/ppf-contact-solver/blob/main/articles/criticism.md
- [S15] Newton README (macOS CPU only; cloth examples): https://github.com/newton-physics/newton
- [S16] Newton docs, VBD solver (experimental; coupling modes; `integrate_with_external_rigid_solver`; DAT truncation) and VBD tuning: `docs/solvers/vbd.rst`, `docs/concepts/simulation_tuning_vbd.rst` in https://github.com/newton-physics/newton
- [S17] Newton `newton/examples/cloth/example_cloth_h1.py` (Style3D cloth on a humanoid posed each frame) and `example_cloth_franka.py` (VBD with an external rigid solver): https://github.com/newton-physics/newton/tree/main/newton/examples/cloth
- [S18] Blender Manual, Mesh Cache modifier (`.mdd`, `.pc2`): https://projects.blender.org/blender/blender-manual/src/branch/main/manual/modeling/modifiers/modify/mesh_cache.rst
- [S19] Warp README (macOS CPU wheels, no Metal) and CHANGELOG ("Remove `warp.sim` … superseded by the Newton library"): https://github.com/NVIDIA/warp
- [S20] HOOD and ContourCraft READMEs: https://github.com/Dolorousrtur/HOOD, https://github.com/Dolorousrtur/ContourCraft
- [S21] babylon-mmd: https://github.com/noname0310/babylon-mmd
- [S22] Magica Cloth 2 overview: https://magicasoft.jp/en/mc2_about/
- [S23] Unreal Chaos Cloth: Dataflow node docs (SimulationCollisionConfig, SimulationSelfCollisionSpheresConfig), https://dev.epicgames.com/documentation/unreal-engine/node-reference/Dataflow/SimulationCollisionConfig; forum, "Cloth Not Colliding with Convex Hulls in Physics Assets", https://forums.unrealengine.com/t/cloth-not-colliding-with-convex-hulls-in-physics-assets-tab/448025

Public posts (claims resting on their authors):

- [P1] 中尾そら (Nakao Sora), "Rigging a Skirt in Blender Part 2", note.com, 2024-12-28: https://note.com/nakao_sora/n/n84d7af9b2d6a
- [P2] Blender-Vmd-Retargeting, README (Chinese), proxy section: https://github.com/butaixianran/Blender-Vmd-Retargeting/blob/main/Readme.cn.md
- [P3] りこぴん, "Blender and MMD: P4. PMX File Settings – S3. Physics Settings (Clothing)", note.com, 2022-03-15: https://note.com/lycopene07/n/n0feedd1eb087
- [P4] 鹞猫, "十分钟学会在Blender中对MMD模型服装的实时布料模拟", Bilibili, 2022-02-07: https://www.bilibili.com/video/BV1F5411o7T5/
- [P5] TedNE, "在blender中把mmd旗袍模型的的刚体物理改为布料", Bilibili, 2018-09-06: https://www.bilibili.com/video/BV12W411Z7Kv/
- [P6] "Creating a skirt rig with cloth sim.. getting freaky results when moving leg", Blender Artists, 2018-01: https://blenderartists.org/t/creating-a-skirt-rig-with-cloth-sim-getting-freaky-results-when-moving-leg/701618
- [P7] 80.lv, "Fluffy Skirt Simulation That's So Satisfying to Watch", 2025-10-29: https://80.lv/articles/fluffy-skirt-simulation-that-s-so-satisfying-to-watch
- [P8] 墨了个影 (translated repost of Derxx Animations, "How to make realistic cloth physics to your MMD models in blender 2.9X"), Bilibili, 2021-04-01: https://www.bilibili.com/video/BV1TK4y1m7QB/
