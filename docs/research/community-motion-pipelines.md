# Community motion pipelines: should we adopt someone else's code for her movement?

Research for the map's movement side. Checked on **2026-11-28** against primary sources: repository source and official docs read through the GitHub API, and papers read on arXiv. Licences, last-push dates, star counts and open-issue counts come from the GitHub API on that day. Nothing was installed or run. Nothing derived from her model is in this file.

**Question.** Are there public, well-supported repositories that already do what our own code does for her movement, and do it better? The movement side means two things: turning a Reference Motion into a Fitted Motion her body can perform, and training her Controller to perform it. If one is better for her, should we adopt it in place of ours?

What we compare against:

- **Fitting.** The throwaway prototype on `prototype/fitted-motion` (`fit.py`, `check.py`, README). It has had five rounds.
- **Training plan.** Decision records `0001`, `0004`, `0005`, `0008` and `0009`.
  - `0008` and `0009` are on the branch `docs/glossary-and-decision-records` and are not yet on `main`.
- **Earlier studies.** Four, two days old: `reference-motion-tracking`, `simulator-and-training-hardware`, `isaac-on-the-5090` and `similar-projects`.

Tags used below:

- **[src]**: read in source code.
- **[doc]**: read in official docs or a README.
- **[paper]**: rests on a paper's own claims.
- **[inf]**: my inference.

## Answer first

| Piece of ours | Best community counterpart | Better for her? | Verdict |
|---|---|---|---|
| **Fitting: the per-frame solve** (`fit.py` step 6: damped least squares plus hand-written caps and rules) | **mink** [1] (Apache-2.0, MuJoCo's own IK library, release 1.4.0 on 2026-11-01). Runner-up: the OmniRetarget solver inside **holosoma** [2] (Apache-2.0). | **Yes, for the solve itself.** Both turn our rules into hard limits inside one quadratic program per frame: joint ranges, speed limits, and minimum distances between named pairs of her solids. mink reads her MJCF as it is and measures distances with MuJoCo's own shape tests, so it handles all 107 of her capsules, boxes and spheres. Neither knows about heels, planted footprints, leg-length travel or the Standing Pose; those stay ours. | **Adopt in part.** Swap the solver in step 6 for mink and keep steps 1–5 and 7 of `fit.py`. |
| **Fitting: everything around the solve** (finding planted feet from the maker's foot IK targets, shrinking travel by leg length, two-point heel planting, lowering the hips, Standing Pose bookends, bringing meeting hands to touching) | GMR [3], PyRoki as used by ProtoMotions [4][5], OmniRetarget [2][6]. In the MMD world, `vmd_sizing` [7]. | **No.** No tool models a shoe that touches the floor at a pad and a stiletto tip. None takes MMD foot-IK targets. The robot tools all assume a human source of different shape (SMPL, BVH), which hers is not. `vmd_sizing` does arm-to-body clearance and hand-to-hand meeting, as ours does, but it is a Windows GUI last pushed in 2023. | **Keep ours.** |
| **The feasibility check** (`check.py`, seven lines) | holosoma's `eval_retargeting.py` [2]: penetration fraction and depth, contact precision. The GMR paper's table [8]. | **No.** Theirs measure ground and object contact only. None has her joint ranges at their ends, weight over her feet (ZMP), legs locked straight, effort, or single-frame jumps all in one place. | **Keep ours.** Add their two units (fraction of frames with an Overlap or a slide, and the worst depth or speed) so our numbers can be read beside published tables. |
| **Training recipe on the Mac** (planned: our own per-frame tracking loop in CPU MuJoCo, copying Isaac Lab's task) | **UniLab** [9] (Apache-2.0, release v1.6.4 on 2026-11-27). It has a BeyondMimic-style G1 motion-tracking task, marked "Tested" on its CPU MuJoCo backend. That backend is documented for Apple Silicon and pinned to MuJoCo 4.0.1, the Mac's version. | **Probably yes.** It is the one maintained stack that trains tracking on the Mac's CPU MuJoCo. That is exactly the loop we were going to write. It already takes a *list* of motion files with adaptive sampling. It does not show the next moments of the motion (`0008`), and its Mac speed is unpublished. | **Adopt in part, subject to the trial below.** Use it as the Mac training harness instead of writing one. Our observation of the next moments, her springs and the Sprung Motion go on top. |
| **Training recipe on the RTX 5090** (planned: Isaac Lab's `Isaac-Motion-Tracking-G1` on Newton / MuJoCo Warp, adapted to show the next moments) | The same task [10]. Alternatives: **MimicKit** [11] and **ProtoMotions** [5]. Both already train one Controller on many clips and show it future frames. | **No change.** Isaac Lab's task is still one clip per run and shows only the current moment [10][src]. MimicKit's MJCF loader would reject her two-hinge elbows as written. ProtoMotions' Newton path is pinned to Newton 1.0.0 / MuJoCo 3.5. | **Keep the plan.** Hold MimicKit as the named fallback. |
| **Simulator choice** (CPU MuJoCo on the Mac; Newton with the MuJoCo Warp solver on the PC) | Every strong project is on MuJoCo, MuJoCo Warp or Newton. | Same thing. | **Keep.** |

**What the strongest projects do about a reference that is not physically clean.** Most do **not** remove every Overlap. They split the problem:

- **Hard-constrained in the reference:**
  - ground contact and footing: planted feet stay planted, nothing sinks into the floor, nothing hangs above it;
  - joint ranges.
- **Left to training:** an Overlap of the body with itself.
  - ProtoMotions' own fitting sets its self-collision weight to `0.0  # turned off for now` [src][4].
  - holosoma's self-collision constraint is off by default and covers only pairs you list [src][2].
  - GMR has no self-collision term at all [src][3][8].
  - BeyondMimic's recipe, as kept in mjlab, instead adds a reward penalty of −10 for each body whose self-contact force exceeds 10 N [src][12].
- **The measured cost of leaving it unclean is real but bounded:**
  - GMR's own paper: a ProtoMotions fit whose legs passed through each other fell to **26%** tracking success on one clip, against 100% for clean fits [paper][8].
  - Fits sunk into the floor scored **0%** on two dances [paper][8].
  - Sudden joint jumps took one clip to **51%** [paper][8].
  - Cleaning self-contact and foot contact afterwards lifted BeyondMimic from 89.5% to 96.2% across many motions (RoboForge) [paper][13].

For her, this argues for:

1. Keeping the Overlap removal for **legs and shoes**. They carry her weight, and her shoes can catch each other.
2. Keeping planted shoes, no sinking and joint ranges as hard rules.
3. Downgrading arm and hand clearance from rules to a reported line. Training under real physics, and the Sprung Motion step before it, already push her arms out of her body.

## Constraints that decide what is adoptable

- **Her body.** She is not a robot and not SMPL: 25.5 kg, a head a sixth of her weight, soft springy joints past human range, stiletto heels whose shoe touches the floor at two places.
  - She is in MJCF: 19 parts, 48 hinges. Each ball-like joint is three hinges on axes chosen from her motions, knees have one hinge, and elbows have two (flex and twist). This is read from `prototype/simulation-body/body.py` [src].
  - 107 primitive collision solids follow her clothed outline (`0004`).
  - A tool that works only for a fixed robot list, or only for SMPL, counts only if adding a custom body is a documented path.
- **Machines.** An M4 Max Mac (36 GB) where she is built and first trained. A Windows RTX 5090 PC for complete training. Nothing is rented.
- **Headless.** All code, run headless. Her model and anything derived from it stay out of a public repo. No commercial use.
- **Input.** VMD, read through Blender. The motion already plays on her own MMD bones, so there is no cross-skeleton mapping to solve.

## 1. Fitting a motion to a body ("retargeting")

### 1.1 The tools, what they actually optimise

| Tool | What it optimises | Planted feet | Overlap of body with itself | Joint ranges | Over time | Custom MJCF body | Input | Sources |
|---|---|---|---|---|---|---|---|---|
| **GMR** (YanjieZe) | Per-frame differential IK through mink, in two passes: end-effector positions plus all key-body orientations, then all key-body positions. Source positions are scaled per body by a height ratio, and the root uniformly, "crucial to avoid … foot sliding". Afterwards the lowest body is moved to the floor. | No constraint. Relies on uniform root scaling. | **None.** No term in the source; the paper names "self-intersections" as a motivation but describes no mechanism. | Yes (`mink.ConfigurationLimit`), plus a velocity limit of 3π rad/s. | Only the velocity limit, and the previous frame as the starting point. | Yes in practice: an `ik_configs/*.json` (body map, weights, scale table) and a registry entry. The README's official path is "send the robot files … or create an issue". | SMPL-X, BVH (LAFAN1, Nokov, Xsens), OptiTrack FBX. | [3][src][doc], [8][paper] |
| **OmniRetarget**, released inside **holosoma** (Amazon FAR) | Per frame, a sequential QP in cvxpy. The cost is "Laplacian deformation" of an interaction mesh over source joints (and objects or terrain), plus smoothness against the last frame. | **Hard constraint** within a tolerance (default 1 mm; the README tells LAFAN users to relax it to 2 cm). Stance is where the source foot moves below 1 cm/s [paper]. Also explicit frame-window foot locks. | **Optional hard constraint** on listed body pairs (`SelfCollisionConfig.enable=False` by default). Ground and object non-penetration are on. The paper admits "minor penetration due to the linearization" that "can be efficiently fixed by RL". | Hard constraint. | Smoothness cost plus a trust region per SQP step. | Documented "add a custom robot" guide: edit `config_types/robot.py` and `data_type.py`, supply an MJCF (for solving) and a URDF (for the viewer). | World joint positions `(T, J, 3)`, so any source after forward kinematics. | [2][src][doc], [6][paper] |
| **PyRoki** (as used by ProtoMotions) | **Whole-trajectory** nonlinear least squares in JAX: local and global keypoint alignment, root and joint smoothness, joint and velocity limits, foot contact, foot tilt. ProtoMotions: "we almost never see … sudden motion flips". | Soft cost (`foot_contact=30.0`, `foot_tilt`), with contact labels taken from the source. | Supported as a cost, but **ProtoMotions sets it to 0.0, "turned off for now"**. Collision shapes are spheres, capsules, half-spaces and height maps only; no boxes. | Soft cost. | **Yes, over the whole clip.** That is its point. | **URDF only**, with revolute, prismatic and fixed joints. Her MJCF would need converting, and her box solids approximating. | Keypoints. | [4][14][src][doc] |
| **mink** (kevinzakka) | A general IK library, not a fitter. Each step solves one QP for joint velocities: weighted tasks (frame pose, centre of mass, posture, relative frames, damping) under **limits** (joint range, joint speed, floating-base speed, `CollisionAvoidanceLimit` between geom groups) and **constraints** (a task held exactly, or `Elastic` to yield through an L1 penalty). | Whatever you write: a foot site can be a hard constraint while planted. | **Yes**, as a hard limit between any geom groups, using MuJoCo's own distance queries. Self-contact works by putting the same group on both sides. The minimum distance is configurable, and a negative value allows a set amount of overlap. | Yes, hard. | Through a speed limit and stepping on from the previous frame. | **Native**: any `mujoco.MjModel`. | Whatever targets you compute. | [1][src][doc] |
| **PHC / SMPLSim** (ZhengyiLuo) | Fits SMPL shape to the robot, then per-frame optimisation. | No. | No. | Partly. | No. | Robot via SMPL shape fit. | SMPL / AMASS. | Earlier study; [8] reports its fits sunk into the floor, with 0% on two dances [paper]. |
| **SPIDER** (facebookresearch) | **Physics-based** fitting: sampling-based control in a parallel simulator, guided by contact, turns a kinematic reference into a dynamically feasible one. | By physics. | By physics. | By physics. | Yes. | Humanoid route on MuJoCo Warp (NVIDIA). The CPU route released 2026-11-17 covers dexterous hands only. | Its own processed datasets. | [15][doc]. Licence **CC BY-NC 4.0**, which fits our non-commercial scope. |
| **ReActor** (Disney Research), **RoboForge**, **PHUMA PhySINK** | ReActor: tunes fitting parameters while training a tracker inside Isaac Sim. RoboForge: diffusion repair of the source, then kinematic repair of foot contact and self-contact, then physics-sampled refinement. PhySINK: physics-constrained fitting on curated SMPL-X. | — | ReActor and RoboForge: yes. | — | — | ReActor: no code found. RoboForge: no code found. PHUMA: code public, Apache-2.0, SMPL-X input. | — | [16][13][17][paper] |
| **vmd_sizing** (miu200521358, the MMD community's tool) | Regenerates a VMD for a target model's proportions. Its arm panel does "接触回避" (avoid contact between wrist or fingertips and chosen bone-following rigid bodies, plus an automatic head sphere) and "位置合わせ" (bring the wrists or fingers together when they come close in the source, optionally against the floor). | Leg sizing through foot IK. | Arms only, against MMD rigid bodies. | — | — | Works on PMX, not MJCF. | VMD and PMX. | [7][src: `ArmPanel.py` strings]. Windows wxPython GUI, last push 2023-11-12. |

### 1.2 Activity and who uses them

- **GMR**
  - 2.8 k stars and 89 open issues. Last commit 2026-10-22: no commits in November.
  - The five newest open issues and pull requests, back to 2026-09-14, have no replies [doc: GitHub API].
  - Used by MimicKit (official converter), TWIST, and a 2026 interaction paper [11][doc].
- **mink**
  - 1.6 k stars, only 11 open issues, release 1.4.0 on 2026-11-01. Its last commit (2026-11-19) fixed `CollisionAvoidanceLimit` [1][doc].
  - GMR is built on it [3][src].
- **holosoma**
  - 1.7 k stars, 95 open issues, commits daily, release holosoma-v0.0.4 on 2026-11-25. Discord support [2][doc].
- **PyRoki**
  - 1.8 k stars. Last commit 2026-04-01, so effectively dormant for seven months [14][doc].
  - ProtoMotions ships it as its fitting step [4].

### 1.3 What this means for our fitting

- **Nobody solves her problem whole.** Every tool assumes a human source of a different shape from the target. They fit by keypoints, have flat or box feet, and have no heel. Ours starts from a motion already playing on her own bones and solves only proportions, heels, bulk and ranges. The robot tools spend most of their code on a step we do not have [inf].
- **The part that has been failing is the solve, and the community has a better one.**
  - Our step 6 is damped least squares with hand-set caps: 12° per leg joint, 3 cm per footprint, 10° and later unlimited for arms, plus a pull to the previous frame. Whatever the caps cannot clear is left for the check to flag (prototype README, rounds 3 and 4) [src].
  - That is why each round has added a rule. The caps trade Overlap against stance by hand.
  - In mink or OmniRetarget the same wishes are written as one problem each frame:
    - hips, torso and head held on their path (high-cost tasks, or hard constraints);
    - each planted shoe's pad and heel tip held on its footprint (a hard constraint, or `Elastic`);
    - every joint pulled toward its authored angle (posture task);
    - joint ranges and joint speeds as hard limits;
    - a minimum distance between named groups of her solids.
  - The solver then finds the least change that satisfies everything, or reports that it cannot [src][1][2].
- **The single-frame snaps.**
  - Per-frame solvers produce them. GMR's own paper traces a fall to 51% to "sudden jumps of the waist roll value" [paper][8].
  - The community's answers are a joint-speed limit inside the solve (mink `VelocityLimit`, GMR's default) or solving the whole clip at once (PyRoki).
  - A speed limit inside the solve is better than smoothing after it. Smoothing after can re-open an Overlap the solve had closed [inf].
- **What a per-frame solver still cannot do.** When the source passes one leg through the other, a solver that steps on from the last frame keeps her legs on whichever side they started. That is the "crossed legs" trap of rounds 1–3 [inf].
  - Only a whole-clip solve, or a footprint plan made before the solve, chooses the side deliberately.
  - Our step 4 already plans footprints per stance, so it is the right place to decide how crossed steps pass. A solver swap does not remove that job.
- **PyRoki is the one whole-clip option, and it does not fit her.** It reads only URDF, so her body would need a converter. Its collision shapes have no boxes, and her outline uses boxes. It has been dormant since April [14][src][doc].
- **GMR does strictly less than ours for her**: no planting, no Overlap term, no heels. Adopting it would lose features [src][3].

## 2. What strong projects do about a reference that is not physically clean

### 2.1 What they do

| Project | Ground contact and footing in the reference | Overlap of the body with itself in the reference | What training does about it |
|---|---|---|---|
| **BeyondMimic → mjlab** (and Isaac Lab's copy) | Trains on the Unitree-made LAFAN1 fits [12][doc]. OmniRetarget measured penetration in 9% of their frames, 3.2 cm at the deepest, and sliding feet in 6% [paper][6]. The paper does not split floor from self. No cleaning step. | Not cleaned. | Reward term `self_collisions` weight **−10**, counting bodies whose self-contact exceeds **10 N**, against tracking terms of weight 0.5–1.0. Also a joint-limit penalty of −10. Termination when the anchor or end effectors stray more than 0.25 m vertically [src][12]. The paper does not attribute any failure to reference quality [paper][18]. |
| **ProtoMotions** | Soft foot-contact and foot-tilt costs in fitting. Then a fixed height correction: lowest body about 2 cm above the floor per frame, and the whole clip lifted to 4 cm. Optional smoothing filter. Contacts are labelled from the *source*, "because the retargeting process can be imperfect" [doc][4]. | **Turned off** in fitting (`self_collision=0.0`) [src][4]. | Self-collisions on in simulation by default (`RobotAssetConfig.self_collisions: bool = True`) [src][5]. |
| **holosoma / OmniRetarget** | **Hard** foot-sticking, ground non-penetration and joint limits [src][2]. | Optional hard constraint on listed pairs, off by default [src][2]. | "Only five reward terms", with weights taken "out of the box without tuning". A binary penalty above 11 N of self-contact. They attribute higher downstream success to the cleaner references: 82–95% against 51–79% for GMR on their interaction tasks [paper][6]. |
| **GMR** | Uniform root scaling, then the lowest body set to the floor [src][3]. | None [src][3]. | Tested with BeyondMimic. Artifacts "do not make a reference motion impossible to track", with named exceptions (below) [paper][8]. |
| **KungfuBot (PBHC)** | Rejects whole clips whose centre of mass strays from the centre of pressure. Shifts height by the lowest mesh vertex during contact, then smooths with an exponential moving average [paper][19]. | Not mentioned [paper][19]. | Adaptive tracking tolerance. |
| **RoboForge** | Kinematic repair of foot contact [paper][13]. | **Kinematic repair of self-collision** [paper][13]. | Leaves the tracker unchanged. Reports BeyondMimic success rising from 89.51% to 96.20% and joint error falling 31.6% [paper][13]. |
| **ReActor** | Fitting adjusted inside the simulator while training [paper][16]. | Reaches zero depth of the body inside itself [paper][16]. | Tracking success 97.5% on G1 against 89.9% for GMR fits and 95.5% for OmniRetarget fits [paper][16]. |

### 2.2 What goes wrong when the reference is left unclean (measured)

From the GMR paper, BeyondMimic tracking, success in sim-to-sim transfer [paper][8]:

- **Into the floor.** PHC's fits of two dances sank deep into the floor, and success was **0%** in every setting.
- **Legs passing through each other.** ProtoMotions' fit of a stop-and-go run had legs that "intersect with each other". It scored **26%**, against 100% for GMR's and Unitree's fits.
- **Sudden joint jumps.** GMR's own fit of one dance scored **51%**, because of jumps in waist roll.
- **Error even on success.** Mean global position error was 77–248 mm across fitters when tracking did succeed.
- **The authors' limit.** Artifacts "do not make a reference motion impossible to track", apart from those cases.

### 2.3 What this decides for her [inf]

- **Leg and shoe Overlaps matter.** The one measured case of the body passing through itself that broke tracking was legs. Her shoes are narrow two-point supports. A Controller asked to put one shoe where the other already is will either trip or learn to stray at exactly the steps the human cares about.
  - Keep removing Overlaps between legs and shoes in the Fitted Motion. Make it a hard limit in the solver, not a cap.
- **Planted shoes, no sinking and no 浮空 are the most damaging faults when left in.** The floor cases went to 0%. Our check already tracks them, and they should stay hard constraints.
- **Arm, hand and torso Overlaps are what the field leaves to training.** The Sprung Motion makes this safer for her than for a robot. The Sprung Motion is the Fitted Motion played by her own soft upper body with her hips carried (`0009`), so it is a physics pass over exactly her arms, head and chest.
  - If that playback has her solids' contacts on, as the first look's hips-carried playback did (its solids "shove her off the motion"), then arm Overlaps are pushed out *before* she trains, by physics rather than by rules.
  - The glossary already allows this: a Fitted Motion is "the record of the choreography asked of her … not the motion she is guaranteed to perform".
  - **Recommendation:** in the fitting, keep arm and hand clearance as a *reported* line plus the hard limits for her head and bodice only. Check whether the Sprung Motion playback resolves the rest before writing any more arm rules.
- **"Meeting hands brought to touching" is worth keeping.** The robot tools have nothing like it. `vmd_sizing` has the same feature (wrist and finger 位置合わせ), which says MMD makers want it [src][7].

## 3. Training to follow a motion

### 3.1 What changed since the earlier studies (two days)

- **UniLab** now runs its G1 motion tracking by default on its **CPU MuJoCo backend**.
  - The PPO task owner exists only for `--sim mujoco`. The support matrix marks `g1_motion_tracking` "Tested" for PPO, APPO, SAC and FlashSAC on `mujoco` [doc][9].
  - That backend pins `mujoco~=4.0.1`, with a native batch engine `mjbatch-uni==0.3.3` that "refuses to import against a different" MuJoCo version [doc][9].
  - On Apple Silicon, `make setup` is "the MuJoCo training path", and Torch uses MPS automatically [doc][9].
  - `motion_file` "accepts one path or a list of paths". It uses adaptive sampling and 1024 environments by default, with BeyondMimic's reward weights, including self-collisions at −10 [src][doc][9].
  - The earlier study described UniLab's tracking example as `--sim mjwarp`; that is now overtaken.
  - Its GPU backends (`mjwarp`, `newton`, `genesis`) are "Linux CUDA only", so not the Windows PC [doc][9].
- **Isaac Lab's** task is unchanged: "Each run trains on one clip". A SuperMimic variant was added on 2026-11-25 [doc][10].
- **mjlab** is still one motion file per run (`MotionLoader(motion_file)`), with the current moment only [src][12].
- **No new Newton release.** 1.8.0 is still the latest. Isaac Lab's release is still v3.0.0 [doc].
- **ProtoMotions v3.3** was released on 2026-11-10. Its Newton backend is still pinned to `newton==1.0.0` and `mujoco==3.5.0`. Its MuJoCo backend is "CPU-only and single-environment" [doc][5].

### 3.2 Against our plan (`0001`, `0008`, `0009`)

| Need from our plan | Isaac Lab task | mjlab | UniLab | MimicKit | ProtoMotions |
|---|---|---|---|---|---|
| Trains on the Mac | No | Evaluation only | **Yes (CPU MuJoCo 4.0.1)** | Only through Newton's CPU path, single world | No (MuJoCo is single-env debug) |
| Trains on the Windows 5090 | **Yes (Newton / MuJoCo Warp)** | No Windows | GPU backends Linux only | Newton is Windows-capable; MimicKit on Windows not documented [inf] | Isaac Lab path Linux only |
| One Controller, many movements | No: one clip | No: one clip | **Yes: list of files** | **Yes: dataset `motion_file`** | **Yes** |
| Shown the next moments | No | No | No (not in the task config) | **Yes: `tar_obs_steps: [1, 2, 3]`** | Yes |
| Custom MJCF body | Through USD conversion | Native | Native, documented "onboard a new robot" | Native, **but** each body may have only 0, 1 or 3 hinges ("Series joints are not supported"), with no joint offsets | Native ("MJCF is the source of truth") |
| Her soft springs, Sprung Motion target | Ours to add | — | Ours to add | Ours to add | Ours to add |
| Sources | [10] | [12] | [9] | [11] | [5] |

Reading the table [inf]:

- **On the Mac, UniLab is the only maintained stack that does what we planned to write.** It already runs a BeyondMimic-style tracking task in CPU MuJoCo of the same version as the Mac. It has the many-clip list and adaptive sampling.
  - What we would still write: her robot entry, a converter from her Sprung Motion to its seven-key NPZ (`fps`, `joint_pos`, `joint_vel`, `body_pos_w`, `body_quat_w`, `body_lin_vel_w`, `body_ang_vel_w`), the observation of the next moments, and her actuator setup.
  - That is less than a training loop, an environment, PPO wiring, sampling and logging.
  - **Two cautions.** UniLab is young (about 1 k stars; releases several times a day). Its learner is its own `unirl` stack, so whether it is the same PPO library as Isaac Lab, as `0008` asks, was not verified.
- **On the PC, nothing beats the plan.** The Isaac Lab task on Newton is the only tracking code that trains on Isaac Lab 3 with MuJoCo Warp, and it is documented on Windows (earlier study).
  - MimicKit is the closest to `0008` out of the box: many clips and future frames. But her elbows (flex plus twist, two hinges) break its loader as written. The adapter would be either writing each elbow as three hinges with one locked, or patching `_parse_joint`.
  - MimicKit is also tested on Newton 1.6.1 (MuJoCo 3.12), far from the Mac's 4.0.1 [src][11].

## 4. The whole chain for a character, not a robot

- **No public project with a community takes an authored character animation to a physically simulated character performing it.** Nothing found does it for an anime body or a dance.
  - **ProtoMotions** is the nearest: digital humans (SMPL, SOMA), a text-to-motion route through Kimodo, general trackers [5].
  - **MimicKit** is a character-first toolkit by DeepMimic's author [11].
  - Both assume human proportions and flat feet, and neither has a fitting step for a character's own authored motion.
- **Isaac-Robot-MMD** [20] is still the only project on an MMD body. Its pushes up to 2026-11-27 extend its G1 robot dance and jump workflows; its anime body still only walks (earlier study). It has 2 stars.
- **Disney's characters** (Olaf, ReActor) are the best published character work. No code was found [16].
- **Conclusion:** our chain is not duplicated anywhere. Adopt pieces, not a whole pipeline.

## 5. The smallest trials

### Trial A: mink as the solver inside `fit.py` (fitting, "adopt in part")

- **Install.** `uv run --with mink --with daqp --with mujoco ...` in the prototype's environment. mink 1.4.0 is on PyPI [1].
- **Feed.**
  - Inputs:
    - her locked Simulation Body as it is, read by `her.py`;
    - the same extracted Reference Motions;
    - the outputs of `fit.py` steps 1–5: passage, planted stances, shrunk travel, footprints, hip envelope.
  - Replace only step 6 with mink, frame by frame, starting from the Standing Pose:
    - **tasks:**
      - `FrameTask`s for hips, waist, chest, neck and head at high cost;
      - a `PostureTask` toward the authored angles;
      - the arms' meeting-hand targets as `RelativeFrameTask`s where they apply;
    - **constraints:** each planted shoe's pad and heel-tip sites as hard (or `Elastic`) frame tasks;
    - **limits:**
      - `ConfigurationLimit`;
      - a `VelocityLimit` sized to the check's 30° per frame;
      - `CollisionAvoidanceLimit` on two groups: shoe and shin solids of the left leg against the right leg, and both hands and forearms against the head and bodice.
  - Leave every other arm-to-body pair to the check.
- **Count as better than round 4**, on ReDreaming Angel, both walks and the stage 1 dance:
  - `check.py` line 2 shows no flagged passage between a leg or shoe and the other leg;
  - line 7 shows no part over 30° in one frame;
  - lines 1 and 3 (ranges; shoes sliding or sinking) are no worse;
  - the departure from the authored hips and torso stays at zero;
  - the human's Eye Check of the close clips of her shoes finds fewer feet colliding;
  - the hand-written caps in `fit.py` (`LEG_CAP_DEG`, `FOOT_CAP`, `ARM_CAP_DEG`) can be deleted.
  - If mink reports `NoSolutionFound` on a frame, that is a finding: the footprints planned in step 4 cannot be met there, which is the crossed-step case. Fix it in step 4, not with a new cap.

### Trial B: UniLab as the Mac training harness (training, "adopt in part")

- **Install.** A source checkout of UniLab v1.6.4 on the Mac, with `make setup`. This pins MuJoCo 4.0.1 [9].
- **Feed.**
  - Her MJCF laid out under `src/unilab/assets/robots/<name>/` per the onboarding guide: robot XML without keyframes, a scene file with floor and Standing Pose keyframe, actuator and joint names.
  - Her double peace sign's Sprung Motion converted to the seven-key NPZ by forward kinematics on her own body. This is a short script of ours, kept out of git like every derived file.
  - The task owner YAML copied from `g1_motion_tracking/base.yaml`, with her body names for the anchor and end effectors.
- **Count as better than writing our own.**
  - **Speed.** First, the training throughput printed on the M4 Max is at least the 10 k policy steps/s that the earlier estimate assumed for our own loop.
  - **Result.** Second, a Controller that finishes the double peace sign in ordinary MuJoCo on the Mac without falling, with her straying from the Sprung Motion measured.
  - **Code.** Third, the adapter (robot entry, NPZ converter, task YAML) is a few hundred lines, against the loop we would otherwise write.
- **If it passes,** add the observation of the next moments (`0008`) as UniLab's one code change and check its PPO settings against Isaac Lab's.

There is no trial for the feasibility check, the PC recipe or the simulator: those stay as planned.

## What contradicts our records or the earlier studies

- **The fitting prototype goes further than our own records ask on arm Overlaps.** The glossary's Fitted Motion is "not the motion she is guaranteed to perform", and `0004` says physical validity outranks matching. Round 4's uncapped arm clearance is the costly part the field leaves to training (§2.3). This is a tension with the prototype, not with a record.
- **`0008` says "everything else copies Isaac Lab's built-in tracking task … with the same learning library".** Adopting UniLab on the Mac would need that checked. Its RL stack is its own `unirl`.
- **Earlier study `reference-motion-tracking`:** "UniLab … tracking example uses `--sim mjwarp`" is overtaken; it is now CPU MuJoCo by default. It also named GMR and PyRoki as the fitting tools that carry into stage 2. GMR has no Overlap handling and is quiet since October. PyRoki reads only URDF, has no box shapes, and has been dormant since April.
- **Earlier study `similar-projects`** recommended `vmd_sizing` as a sizing reference.
  - Confirmed: it does arm contact avoidance against rigid bodies and wrist and finger meeting.
  - It is a Windows GUI last pushed in 2023. The author's newer `mlib_go` was not examined. Not adoptable headless.
- **`0008` and `0009` are not on `main`.** They are on `docs/glossary-and-decision-records`, which was not merged when this was written.

## What could not be verified

- **UniLab:**
  - Mac training speed: no benchmark is checked in ("No benchmark or recommendation metadata is currently checked in").
  - Whether its PPO matches RSL-RL.
  - Whether its MuJoCo backend parallelises across all 14 cores.
- **mink on her body.** Whether its collision limit copes with 107 solids per frame at a useful speed. It has a broadphase, but nothing was run.
- **The Sprung Motion playback.** Whether it has her solids' self-contacts on, so that arm Overlaps really are pushed out there. This is an inference from the first look's notes. Check `simulate.py`'s contact settings before relying on §2.3.
- **ReActor and RoboForge code.** None found. Their numbers are the papers' claims.
- **SPIDER's humanoid route on Windows.** It runs on MuJoCo Warp; Windows was not checked.
- **BeyondMimic's numeric reward weights** come from mjlab's config, not from the paper's supplement, which was not read in full.
- **Whether MimicKit runs on Windows with Newton.** Not documented.

## Repositories examined

| Repository | Licence | Last push | One line |
|---|---|---|---|
| kevinzakka/mink | Apache-2.0 | 2026-11-19 | MuJoCo-native QP inverse kinematics with joint, speed and collision-distance limits; the solver to adopt. |
| amazon-far/holosoma | Apache-2.0 | 2026-11-26 | OmniRetarget fitting (hard foot, ground and limit constraints, optional self-contact pairs) plus G1/T1 tracking training. |
| YanjieZe/GMR | MIT | 2026-10-22 | Per-frame mink IK fitting for many robots; no Overlap or planting; quiet since October. |
| chungmin99/pyroki | MIT | 2026-04-01 | Whole-trajectory JAX kinematic optimisation; URDF only; no box shapes; dormant. |
| NVlabs/ProtoMotions | Apache-2.0 | 2026-11-10 | Many-clip trackers for digital humans and robots; PyRoki fitting with self-collision off. |
| mujocolab/mjlab | Apache-2.0 | 2026-11-28 | BeyondMimic's home; one clip per run; no Windows; Mac evaluation only. |
| isaac-sim/IsaacLab | BSD-3 / mixed | 2026-11-28 | Built-in G1 motion tracking on Newton, one clip per run; our PC plan. |
| Motphys/UniLab | Apache-2.0 | 2026-11-27 | Tracking task "Tested" on CPU MuJoCo 4.0.1 with an Apple Silicon path; the Mac harness to try. |
| xbpeng/MimicKit | Apache-2.0 | 2026-11-18 | DeepMimic/AMP/ADD toolkit; many clips plus future frames; MJCF loader rejects two-hinge joints. |
| robfiras/loco-mujoco | MIT | 2026-11-26 | JAX imitation benchmark with SuperMimic; GPU-oriented (earlier study). |
| google-deepmind/mujoco_playground | Apache-2.0 | 2026-11-28 | Single-clip G1 tracking on MuJoCo Warp (earlier study). |
| HybridRobotics/whole_body_tracking | MIT (archived) | 2026-10-16 | Original BeyondMimic; points to mjlab. |
| facebookresearch/spider | CC BY-NC 4.0 | 2026-11-21 | Physics-based fitting by sampling; humanoid route needs MuJoCo Warp. |
| DAVIAN-Robotics/PHUMA | Apache-2.0 | 2026-09-30 | Physics-filtered SMPL-X dataset and PhySINK fitting; SMPL-X input only. |
| ZhengyiLuo/PHC | BSD-3-Clause-Clear | 2025-08-21 | SMPL-shape fitting and general tracker; Isaac Gym. |
| TeleHuman/PBHC | none | 2026-07-01 | KungfuBot; physics filtering of clips; no licence, so all rights reserved. |
| miu200521358/vmd_sizing | MIT | 2023-11-12 | MMD's own VMD sizing with arm contact avoidance; Windows GUI. |
| Jasy6307/Isaac-Robot-MMD | Apache-2.0 | 2026-11-27 | The one MMD-body physics project; anime body walks, G1 dances. |
| google-deepmind/dm_control | Apache-2.0 | 2026-11-28 | Older MuJoCo mocap-tracking tasks; superseded for this purpose. |

## Sources

All accessed 2026-11-28.

1. mink README and `CollisionAvoidanceLimit` source — https://github.com/kevinzakka/mink , https://github.com/kevinzakka/mink/blob/main/src/mink/limits/collision_avoidance_limit.py
2. holosoma: README; fitting README; "Adding Custom Robot Type"; `interaction_mesh_retargeter.py`; `config_types/retargeter.py`; `evaluation/eval_retargeting.py` — https://github.com/amazon-far/holosoma (paths under `src/holosoma_retargeting/`)
3. GMR README and `general_motion_retargeting/motion_retarget.py` — https://github.com/YanjieZe/GMR
4. ProtoMotions, "Retargeting SMPL motions with PyRoki" and `pyroki/batch_retarget_to_g1_from_keypoints.py` — https://github.com/NVlabs/ProtoMotions/blob/main/docs/source/tutorials/workflows/retargeting_pyroki.rst
5. ProtoMotions: custom robot tutorial, installation guide, `pyproject.toml`, `robot_configs/base.py` — https://github.com/NVlabs/ProtoMotions
6. Yang et al., "OmniRetarget", arXiv:2509.26633 v3 — https://arxiv.org/html/2509.26633
7. vmd_sizing, `src/form/panel/ArmPanel.py` — https://github.com/miu200521358/vmd_sizing
8. Araujo, Ze et al., "Retargeting Matters: General Motion Retargeting for Humanoid Motion Tracking" (GMR), arXiv:2510.02252 — https://arxiv.org/html/2510.02252
9. UniLab: README; docs `2-user_guide/4-tasks/2-motion_tracking.md`, `2-user_guide/3-backends/1-mujoco.md`, `6-how_to/1-onboard_new_robot.md`, `1-getting_started/2-installation.md`; `conf/ppo/task/g1_motion_tracking/*.yaml`; support matrix — https://github.com/Motphys/UniLab , https://unilabsim.github.io/UniLab-doc/en/5-reference/5-support_matrix.html
10. Isaac Lab, "Training a G1 motion-tracking policy" and commit history of `core/motion_tracking` — https://github.com/isaac-sim/IsaacLab/blob/main/docs/source/how-to/train_g1_motion_tracking.rst
11. MimicKit README, `data/envs/deepmimic_humanoid_env.yaml`, `mimickit/anim/mjcf_char_model.py` — https://github.com/xbpeng/MimicKit
12. mjlab: `docs/source/training/motion_imitation.rst`, `tasks/tracking/tracking_env_cfg.py`, `tasks/tracking/mdp/commands.py`; BeyondMimic `whole_body_tracking` README — https://github.com/mujocolab/mjlab , https://github.com/HybridRobotics/whole_body_tracking
13. "RoboForge: Cross-space Motion Refinement for Physically Executable Humanoid Whole-body Tracking", arXiv:2603.17927 — https://arxiv.org/abs/2603.17927
14. PyRoki README and `examples/12_humanoid_retargeting_fancy.py` — https://github.com/chungmin99/pyroki
15. SPIDER README — https://github.com/facebookresearch/spider ; paper arXiv:2511.09484
16. "ReActor: Reinforcement Learning for Physics-Aware Motion Retargeting", arXiv:2605.06593 — https://arxiv.org/html/2605.06593
17. PHUMA README — https://github.com/DAVIAN-Robotics/PHUMA ; paper arXiv:2510.26236
18. Liao et al., "BeyondMimic", arXiv:2508.08241 — https://arxiv.org/html/2508.08241
19. Xie et al., "KungfuBot", arXiv:2506.12851 — https://arxiv.org/html/2506.12851
20. Isaac-Robot-MMD commit history — https://github.com/Jasy6307/Isaac-Robot-MMD
