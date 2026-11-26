# How a Simulated Character learns to follow a Reference Motion

Research for issue #3. Checked against primary sources on 2026-11-26. Repository status (licence, last push) was read from the GitHub API that day.

## Answer in brief

- **Stage 1 method: per-frame motion tracking.** This is the DeepMimic reward family as refined by BeyondMimic: PPO, a reward made of Gaussian per-body tracking terms, reference-state initialisation, early termination on falls, and adaptive sampling of hard segments.
  - ADD is the newer option. It removes hand-tuned reward weights.
  - AMP is the wrong tool for stage 1, because it does not hold the character to one specific clip.
- **Mac: (a) and (b).** Every maintained framework treats an NVIDIA GPU as the training device and macOS as CPU-only, evaluation-grade, or not supported.
  - Plain CPU MuJoCo is fast on this Mac. A humanoid measured 0.57 M physics steps/s across 14 processes.
  - One short, mostly upper-body clip is therefore plausibly trainable locally in hours to about a day. That figure is an **estimate** and needs a benchmark spike.
  - The fallback is the *same* MuJoCo task on a rented GPU through MuJoCo Playground or mjlab.
- **Stage 2: (c).** Tracking is the method that scales.
  - The 2025–26 state of the art trains one tracking policy on many clips: GMT, ProtoMotions' general tracker, SONIC, Metatron, LocoMuJoCo's SuperMimic.
  - A generative layer sits on top: MaskedMimic, or BeyondMimic's guided diffusion, or a text-to-motion model such as Kimodo that produces the kinematic reference.
  - Stage 1's Simulation Body, retargeting, reward and observation code, and policy weights all carry into stage 2. Nothing gets thrown away.

## 1. The method families

| Family | What the policy is rewarded for | Follows one dance closely? | Extends to a repertoire | Primary source |
|---|---|---|---|---|
| **Single-clip tracking (DeepMimic)** | Matching the reference pose, velocity, end-effectors and centre of mass at each frame. Weights are 0.65 / 0.1 / 0.15 / 0.1. Uses reference-state initialisation (RSI) and early termination (ET). | Yes, the closest of any family. | Multi-clip policies are possible, and the paper demonstrates "multi-skilled agents". | [DeepMimic, arXiv:1804.02717](https://arxiv.org/abs/1804.02717) |
| **Modern tracking (BeyondMimic)** | Gaussian terms `exp(-ē/σ²)` on body position, orientation, linear velocity and angular velocity, measured relative to an anchor body in a yaw-aligned frame, so global drift is allowed. Penalties for joint limits, action rate and self-contact. Adaptive sampling favours segments that fail. | Yes. Adaptive sampling is what makes hard segments converge: without it, three of four motions failed "even after 30k training iterations". | Its diffusion layer composes tracked skills with additive task costs. | [BeyondMimic, arXiv:2508.08241](https://arxiv.org/html/2508.08241) |
| **ADD (adversarial differential discriminator)** | Same tracking errors, but a discriminator turns the raw error vector into the reward, so there are no hand-tuned weights. | Yes. The authors report quality comparable to state-of-the-art tracking. | Same as tracking. | [ADD, arXiv:2505.04961](https://arxiv.org/abs/2505.04961), SIGGRAPH Asia 2025 |
| **AMP (adversarial motion prior)** | Looking like the dataset's style while doing a task, such as steering. | No. Behaviours "need not exactly match any specific motion in the dataset". Tracking "learn[s] faster and achieve[s] lower errors". | Good for a natural idle, walk or turn under steering commands. | [AMP, arXiv:2104.02180](https://arxiv.org/html/2104.02180) |
| **ASE / MaskedMimic (latent skills, inpainting)** | ASE learns a skill embedding. MaskedMimic is trained on tracking data and produces motion from partial goals: "masked keyframes, objects, text descriptions, or any combination thereof". | Not the goal. | This is the stage-2 controller layer. | [MaskedMimic, arXiv:2409.14393](https://arxiv.org/abs/2409.14393) |
| **General motion trackers** (PHC, GMT, SONIC, Metatron, SuperMimic) | Tracking any clip from a large dataset with one network, often as a teacher distilled into a student. | Yes, for any clip, at a high one-time cost. | This is what a repertoire becomes. | Sources in §4 |

The physics bar in the map is "stays upright, recognisably the same dance". Tracking fits it well. The anchor-relative BeyondMimic formulation also suits it, because it lets the character drift in place rather than fall while chasing a root trajectory she cannot reproduce.

## 2. Implementations, licences, status, and whether they train on this Mac

| Implementation | Licence | Last push | Methods | Training on macOS / Apple Silicon |
|---|---|---|---|---|
| [google-deepmind/mujoco_playground](https://github.com/google-deepmind/mujoco_playground): task `G1WholeBodyTracking` | Apache-2.0 | 2026-11-26 | BeyondMimic-style single-clip tracking, RSL-RL PPO | The README has a **"CPU (macOS or Linux)"** install path. The tracking README shows a CPU flag (`--device=cpu --overrides='{"nworld": 1}'`). Runs on MuJoCo Warp, whose CPU path is "for development and debugging" ([MJWarp README](https://github.com/google-deepmind/mujoco_warp)). Mac training speed **unmeasured**. |
| [mujocolab/mjlab](https://github.com/mujocolab/mjlab): task `Mjlab-Tracking-Flat-Unitree-G1` | Apache-2.0 | 2026-11-26 | BeyondMimic tracking with adaptive sampling. The original [HybridRobotics/whole_body_tracking](https://github.com/HybridRobotics/whole_body_tracking) (MIT) is now **archived** and points here. | "mjlab requires an NVIDIA GPU for training. macOS is supported for evaluation only." The FAQ adds: "CPU performance is significantly slower than GPU execution" ([mjlab#112](https://github.com/mujocolab/mjlab/issues/112)). One motion file per policy (`MotionLoader(motion_file)` in `tasks/tracking/mdp/commands.py`). |
| [xbpeng/MimicKit](https://github.com/xbpeng/MimicKit) | Apache-2.0 | 2026-11-18 | DeepMimic, AMP, AWR, ASE, LCP, ADD, SMP. Single clip **or a dataset of clips** through `motion_file`. | Engines: Isaac Gym, Isaac Lab, Newton. Newton supports "macOS (CPU only)" ([Newton README](https://github.com/newton-physics/newton)). MimicKit on Mac is therefore possible in principle but untested and unbenchmarked. Retargeting goes through GMR. |
| [NVlabs/ProtoMotions](https://github.com/NVlabs/ProtoMotions) (v3) | Apache-2.0 code. Pretrained weights under the NVIDIA Open Model License. | 2026-11-10 | General tracker, MaskedMimic, ADD, AMP/ASE, Metatron, Kimodo text-to-motion pipeline | MuJoCo backend is "CPU-only … single environment only (`num_envs=1`) … intended for quick policy validation and debugging". Train on IsaacGym, IsaacLab or Newton (NVIDIA GPU) ([install guide](https://nvlabs.github.io/ProtoMotions/getting_started/installation.html)). Mac use is sim-to-sim checks only. |
| [robfiras/loco-mujoco](https://github.com/robfiras/loco-mujoco) v1.2 | MIT | 2026-11-26 | DeepMimic-style tracking, AMP, GAIL, PPO, SuperMimic (model-based multi-clip tracking), all in JAX | Supports "MuJoCo (single environment) and MJX/MJWarp (parallel)". Installs CPU JAX by default, but the training loop is designed to run "entirely on the GPU" ([training docs](https://loco-mujoco.readthedocs.io/en/latest/training/index.html)). Datasets include LAFAN1 `dance2_subject4`. |
| [Motphys/UniLab](https://github.com/unilabsim/UniLab) | Apache-2.0 | 2026-11-24 | PPO, SAC variants. Has a G1 motion-tracking task. | Documented Apple Silicon macOS path. The design is CPU-batched physics with a separate learner, reporting 3–10× end-to-end speed-ups ([arXiv:2605.30313](https://arxiv.org/abs/2605.30313)). The tracking example uses `--sim mjwarp`. Young project; worth a measured trial. |
| [xbpeng/DeepMimic](https://github.com/xbpeng/DeepMimic) (original) | MIT | 2025-11-27 | DeepMimic | Bullet physics, legacy C++/Python. Superseded by MimicKit. |
| [ZhengyiLuo/PHC](https://github.com/ZhengyiLuo/PHC) | BSD-3-Clause-Clear (SMPL assets carry their own terms) | 2025-08-21 | General tracker | Isaac Gym only. |
| [zixuan417/humanoid-general-motion-tracking](https://github.com/zixuan417/humanoid-general-motion-tracking) (GMT) | Apache-2.0 | 2025-08-08 | General tracker, MoE teacher with student | Isaac Gym training, MuJoCo sim-to-sim. |
| [TeleHuman/PBHC](https://github.com/TeleHuman/PBHC) (KungfuBot) | **none declared** | 2026-07-01 | Single-clip tracking of highly dynamic motion | Isaac Gym. |
| [NVlabs/GR00T-WholeBodyControl](https://github.com/NVlabs/GR00T-WholeBodyControl) (SONIC) | Apache-2.0 code. Weights under the NVIDIA Open Model License. | 2026-11-03 | General tracker ("behavior foundation model") | Isaac Lab, "64+ GPUs for reasonable convergence" ([training guide](https://nvlabs.github.io/GR00T-WholeBodyControl/user_guide/training.html)). G1 robot only. |
| [nv-tlabs/ASE](https://github.com/nv-tlabs/ASE) | NVIDIA License (source-available) | 2025-12-07 | AMP, ASE | Isaac Gym. Superseded by MimicKit/ProtoMotions. |

**Summary for (a).** No maintained framework lists macOS as a *training* platform for parallel simulation.

The repos with an official macOS code path are:

- **MuJoCo Playground**: Warp on CPU.
- **mjlab**: Warp on CPU; "evaluation only" for training purposes.
- **LocoMuJoCo**: CPU JAX or single-env MuJoCo.
- **UniLab**: CPU-batched.
- **MimicKit**: through Newton on CPU, untested.

What does run well on the Mac is **classic CPU MuJoCo**, one environment per core (§3).

All the GPU frameworks above consume the same MJCF, so a Simulation Body written for CPU MuJoCo moves to a rented GPU unchanged.

## 3. Training cost: published figures and what this Mac can do

Published figures, with the source and hardware for each:

| Work | What was trained | Cost | Hardware / simulator |
|---|---|---|---|
| DeepMimic (2018) | One skill per policy | 41 M–191 M samples per skill, "often requiring several days per skill". Policy at 30 Hz, physics at 1.2 kHz. | CPU, Bullet ([arXiv:1804.02717](https://arxiv.org/html/1804.02717v3)) |
| AMP (2021) | One policy per dataset/task | 100–300 M samples, "approximately 30–140 hours on 16 CPU cores" | CPU, Bullet ([arXiv:2104.02180](https://arxiv.org/html/2104.02180)) |
| KungfuBot / PBHC (2025) | One highly dynamic clip per policy, with sim-to-real randomisation | "Each of our models is trained for 27 hours". MaskedMimic baseline: 18 h per policy. | 1× RTX 4090, Isaac Gym ([arXiv:2506.12851](https://arxiv.org/html/2506.12851), App. D) |
| BeyondMimic (2025) | One clip per policy | Up to 30 k PPO iterations (Table S5). An easy motion converges in 2 k iterations with adaptive sampling vs 4 k without. No wall-clock figure published. | Isaac Lab, GPU ([arXiv:2508.08241](https://arxiv.org/html/2508.08241)) |
| LocoMuJoCo SuperMimic (2026) | One policy on all 40 LAFAN1 clips | 1.53 × 10⁸ env steps, "about 50 minutes" | 1× RTX 6000 Ada, 4096 MuJoCo Warp envs ([benchmark](https://loco-mujoco.readthedocs.io/en/latest/training/benchmark.html)) |
| GMT (2025) | General tracker, 8,925 clips (33 h of motion) | About 6.8 B samples. Teacher ≈ 3 days, student ≈ 1 day.¹ | 1× RTX 4090, Isaac Gym, 4096 envs ([arXiv:2506.14770](https://arxiv.org/html/2506.14770)) |
| ProtoMotions | General tracker on all of AMASS (40+ h) | "within 12 hours" | 4× A100 ([README](https://github.com/NVlabs/ProtoMotions)) |
| SONIC | Foundation tracker | 100 k iterations, "64+ GPUs" recommended | Isaac Lab ([training guide](https://nvlabs.github.io/GR00T-WholeBodyControl/user_guide/training.html)) |

¹ The arXiv HTML renders these as "33 days" and "11 day". The same page renders the clip count as "89258925", so digits are being duplicated in the HTML; the true values are almost certainly 3 days and 1 day. Confirm against the PDF before relying on them.

**Measured on this machine.** The benchmark was CPU MuJoCo 4.0.1 on the stock `humanoid.xml` (21 actuators, 5 ms timestep), driven by a Python loop with random controls and resets. The throwaway script was not committed; it loops `mujoco.mj_step` in a `multiprocessing.Pool`.

| Processes | Physics steps/s |
|---|---|
| 1 | 55.8 k |
| 10 | 497 k |
| 14 | 568 k |

This agrees with MuJoCo's own documentation, which gives 650 K steps/s for one humanoid on an M3 Max using `testspeed` ([MJX docs](https://mujoco.readthedocs.io/en/stable/mjx.html)).

**Estimate, not a measurement.** The measured physics rate puts a ceiling on how fast a single clip can train here:

1. At a 50 Hz policy with 4 physics substeps, the physics ceiling is about 140 k policy steps/s.
2. Observation, reward and network inference in Python typically take most of that. Assume 10–30 k policy steps/s end to end.
3. The anime Simulation Body may have more joints and contacts than the stock humanoid, which lowers the rate further.
4. Sample budget: an easy, mostly upper-body clip should need well below DeepMimic's 41–191 M samples. Modern rewards, adaptive sampling and no sim-to-real randomisation all reduce it.
5. Result: **a few hours to about a day of wall clock**.

Treat this as the hypothesis for a one-day benchmark spike. If the spike shows less than 5 k steps/s, rent a single GPU and run the same task in MuJoCo Playground or mjlab.

## 4. Extending to a Movement Repertoire without starting over

Current practice in 2025–26 converges on one architecture with two layers:

1. **A low-level tracking policy** that follows whatever kinematic reference it is given, trained on many clips.
2. **A high-level source of references or goals.** This can be a clip selector, a text-to-motion generator, or a generative policy distilled from the tracker.

Examples of this architecture:

- **SONIC** "uses motion tracking as a scalable training task" and serves "as a foundation for higher-level planning".
- **Metatron** is "a MaskedMimic-style student distilled from a motion-tracking teacher" that also handles steering and recovery ([ProtoMotions README](https://github.com/NVlabs/ProtoMotions)).
- **BeyondMimic** puts guided diffusion on top of tracked skills.
- **ProtoMotions** documents the text route directly: generate a motion with Kimodo text-to-motion, then train a physics policy to perform it.
  - Kimodo code is Apache-2.0; its weights are under the NVIDIA Open Model License ([kimodo](https://github.com/nv-tlabs/kimodo)).
  - Its skeletons are SOMA, SMPL-X and G1, so its output needs retargeting to her body.

### What carries from stage 1 into stage 2

- **The Simulation Body MJCF and the MMD-to-body retargeting.** Retargeting tools for this step are GMR (MIT) and PyRoki (MIT); the sibling ticket covers the conversion itself.
- **The tracking reward, observations and termination code.** Moving from one clip to many is a config change in MimicKit (`motion_file` pointing at a dataset), LocoMuJoCo and ProtoMotions. mjlab and Playground are one clip per policy today.
- **The trained dance policy.** It can serve as a warm start, or as one expert to distil into a multi-clip student. Distillation with DAgger is supported by both [LocoMuJoCo](https://loco-mujoco.readthedocs.io/en/latest/training/index.html) and GMT.

### How the Mind selects a movement

- **Simplest option:** the Mind picks a named clip from the repertoire, and the multi-clip tracker plays it. Transitions come from blended references, or from training on transition clips.
- **Richer option:** the Mind emits text or goals to a MaskedMimic-style policy, or to a text-to-motion generator feeding the tracker.

Both options keep the stage-1 tracker in place.

## 5. Notes specific to this character

- **Anime proportions rule out off-the-shelf pretrained trackers.** Every general tracker found here ships weights for SMPL, SOMA or Unitree robots. Her body needs training from scratch, using the same code. A general tracker would also need a repertoire dataset retargeted to her body.
  - AMASS and BONES-SEED carry their own licences. Check them against the project's non-commercial scope.
- **Arms and the root of an upper-body dance.** Ground contact and balance are what the policy must learn. Anchor-relative tracking lets her hold balance at the cost of small global drift. That matches the map's bar that "physical validity outranks exact matching".
- **Residual root forces are excluded.** Methods that add non-physical "helper" forces at the root are excluded by the glossary definition of a Simulated Character, which is moved only by joint forces. This research did not survey them.

## What this research could not determine

- **Real Mac training speed for any of the frameworks.** No primary source publishes a macOS training benchmark for MuJoCo Playground, mjlab, MimicKit/Newton or UniLab. The local estimate above extrapolates from a raw physics benchmark.
- **A published wall-clock time for a single BeyondMimic or mjlab clip on a GPU.** The paper gives iterations only.
- **GMT's exact training days.** These depend on a garbled HTML render (footnote 1).
- **Licence for PBHC.** The repo declares none, so treat it as all rights reserved.
