# Similar projects: MMD characters made physical and alive

Research for issue #18. Searched on 2026-11-26.

**Question.** Who has already taken an MMD or other anime character model and (a) made it a physically simulated character that learns to move, dance or balance, or (b) made it "alive": an AI-driven character that talks, decides and moves on its own? Where nothing matches exactly, what are the nearest neighbours, and what does that mean for a 27-second jump-heavy hip-hop dance in high heels and for the three stages on the map?

**Short answer.** One public project matches closely: **Isaac-Robot-MMD** (GitHub `Jasy6307`, Feb–Nov 2026). It converts a PMX anime model (Chihaya Anon) into a 27-body physics humanoid in Isaac Sim / PhysX, trains it with PPO to walk and jog on command, drives the MMD skin from the simulated links, and runs the model's own hair and skirt rigid-body topology as one-way secondary physics with a cel shader. It has **not** trained the anime body to dance under physics. Its dances run as kinematic playback on the anime model, and as RL tracking only on a Unitree G1 robot, where "long VMD sequences" are still listed as unsolved. No one appears to have published a physics-simulated anime character performing a full dance, jumps, or anything in high heels. On the "alive" side, AI companions with MMD or VRM bodies are mature (Project AIRI ships PMX loading, Bullet hair and skirt physics, vowel lip sync onto あいうえお morphs, and VMD gestures picked by emotion), but they all play canned or kinematic clips. The only published system found that puts a language model over a *physics-based* body is a 2025 VR research demo (Artanim / University of Hamburg) with three walking commands.

Legend: **[read]** means read at the linked primary source during this search. **[inferred]** means my reasoning, or a secondary source not confirmed at the primary.

---

## 1. How the search was done

- GitHub repository search (`gh search repos`) for: `pmx mujoco`, `mmd mujoco`, `vmd mujoco`, `pmx urdf`, `pmx mjcf`, `vmd retarget robot`, `mmd humanoid reinforcement`, `vrm mujoco`, `vrm reinforcement learning`, `mmd isaac`, `mikumikudance reinforcement`, `vmd unitree`, `mmd deepmimic`, `vmd humanoid`, `mmd robot dance`. The only real hits were `Jasy6307/Isaac-Robot-MMD`, `EnochxynL/mmd_mujoco_player` and an empty `mayusaki3/SansaVRM-MuJoCo-Adapter` (contains only a LICENSE file) **[read]**.
- Web search in English, Chinese and Japanese: MMD 强化学习 / 物理仿真 / 人形机器人 跳舞 / 极乐净土 机器人; MMD 強化学習 / 物理シミュレーション / VMD ヒューマノイド; Qiita / Zenn / note.com for PMX to MuJoCo; VRM + RL / ML-Agents ragdoll; anime / stylised character + DeepMimic; high heels, skirts, non-human proportions in physics-based animation; LLM + physics-based character; AI VTuber / companion bodies.
- Not done: bilibili, X, YouTube and niconico were reached only through web-search indexes, not browsed directly (the Chrome tools were not used). A creator who posted only a video, with no repository or write-up, could have been missed. The bilibili-targeted searches surfaced nothing beyond the Zhihu, CSDN and GitHub results cited here.

---

## 2. Exact and near-exact matches (anime model, physics, learning)

### 2.1 Isaac-Robot-MMD (Jasy6307), the closest match

- **What and when.** A public, Apache-2.0 repository created 2026-02-26 and last pushed 2026-11-25, with 2 stars **[read: GitHub API, https://github.com/Jasy6307/Isaac-Robot-MMD]**. It has two halves:
  1. a **VMD → Unitree G1** pipeline: retarget, play back, record an H5 reference, train PPO (RSL-RL) leg-residual tracking, evaluate;
  2. a **`source/pmx_prototype/`** branch that turns a PMX anime model into a physics character **[read: README, https://github.com/Jasy6307/Isaac-Robot-MMD/blob/HEAD/README.md and source/pmx_prototype/README.md]**.
- **Model and motion sources.** The model is "Anon Chihaya" PMX (BanG Dream!), credited to Bushiroad Games / BungleScrungle / 海新_ / 小麦弥望. Dances are 《极乐净土》 (motion by Yurie, 6,543 frames, about 218 s), IRIS OUT, and a "Girls" dance. Walking uses the 100STYLE mocap set (CC BY 4.0). **Models, VMDs and music are not in the repo**: "Isaac Sim, Isaac Lab, and MMD motion/audio data are not included and must be obtained separately" **[read: README and pmx_prototype/README.md]**. This is the same licence stance as our project.
- **Simulator and hardware.** Isaac Sim 6.1 / Isaac Lab 3.0 EA, PhysX, Windows 11, validated on an RTX 5090 D **[read: README]**.
- **Simulation Body.** "27 rigid bodies, 23 actuated DOF: waist 3, each leg 6, each arm 4; head and hands fixed". Total mass 50.52 kg, described as an engineering estimate. Capsules for limbs, boxes for pelvis and soles. "Clothes and hair are not load-bearing collision shapes." Self-collision is on, filtered within four joint hops. A later 31-DOF version adds wrists, plus an optional mass profile from Plagenhoef female segment fractions (the same idea our ticket #5 chose). A `SkinBridge` computes the 628 skin bones' poses from the simulated links' world poses, so the Visible Mesh follows the Simulation Body. Leg D-bones are mapped explicitly **[read: source/pmx_prototype/PHYSICAL_CHARACTER.md, https://github.com/Jasy6307/Isaac-Robot-MMD/blob/HEAD/source/pmx_prototype/PHYSICAL_CHARACTER.md]**.
- **What it learned.** PPO on a gait reference plus residual, 120 Hz physics and 30 Hz control, 2,048 to 8,192 GPU environments.
  - v1: walk 0–0.25 m/s, 201 PPO updates (about 19.8 M transitions), 77-second 16-direction acceptance test with 0 falls.
  - Later versions: 0.4 m/s and ±0.6 rad/s turning, 100STYLE mocap pose rewards, foot-slide penalties (sliding cut by 74%), an AMP motion prior, and a **1.2 m/s jog with only about 4.3% flight time**.
  - Training time: the "V6" line totals about 4 hours of GPU training, excluding acceptance runs and video **[read: source/pmx_prototype/ANON_LOCOMOTION.md, https://github.com/Jasy6307/Isaac-Robot-MMD/blob/HEAD/source/pmx_prototype/ANON_LOCOMOTION.md]**.
  - The anime body was **never trained to track a dance** under physics. The doc's own boundary note says that passing static standing "does not mean disturbance rejection"; flat ground only **[read: PHYSICAL_CHARACTER.md, ANON_LOCOMOTION.md]**.
- **Dances.** The anime-model dances are *kinematic*:
  - `load_vmd.py` bakes the VMD with its own two-link leg IK and append-rotation solver, and notes that the source VMD was made for a different model ("しまかぜ"), so "some foot targets may exceed Anon's leg reach" **[read: pmx_prototype/README.md]**.
  - Physics dance tracking is done only on the **G1 robot**. Its listed open problems: "G1 training stability on long VMD sequences", hand retargeting accuracy, toe IK, motion scaling, "too much knee bend" in some poses, kinematic checks that "are not dynamics validation", and no real robot ("暂无实机") **[read: README]**.
  - There are jump-specific G1 env configs (`g1_jump_env_cfg.py`, `g1_auto_jump_env_cfg.py`) **[read: repo tree]**, but no published metrics on how well jumps are tracked.
- **Secondary Physics.**
  - **Offline XPBD version.** It reads the PMX's 484 rigid bodies and 879 joints, extracts the skirt, long-hair, short-hair and accessory chains, and builds 496 particle nodes with 2,253 constraints. Skirt-waist and scalp rows follow the body, and 25 body capsules act as colliders. 120 Hz, 12 iterations. Explicitly "not importing the original MMD Bullet rigid bodies one by one". Proxy penetration fell about 76%, but "no triangle-level self-collision", so some 穿模 remains.
  - **Live PhysX version.** A one-way node network driven by the policy's body pose, which "does not feed contact force back to the body articulation". There are per-model fixes for skirt waist fit and side-hair pinning, and hair/skirt contact is optional.
  - Sources: **[read: pmx_prototype/README.md, PHYSICAL_CHARACTER.md]**. This is the same "simulated after the body, never driving it" rule as our glossary's Secondary Physics.
- **Look.** A custom `cel_studio.mdl` toon material: two-tone shading, per-material shadow colours, bangs shadow, outline shells that skip micro hair strands, face shaping **[read: pmx_prototype/README.md]**.
- **High heels.** Not mentioned anywhere in the docs. The sole is a box with eight corner points used for slip measurement **[read: ANON_LOCOMOTION.md v5 section]**. Whether Anon's model wears heels is not stated.
- **Reusable.** Apache-2.0 code, but Windows and Isaac only. The *ideas* transfer directly: a box sole, segment-fraction masses, a skin bridge from simulated links to the full MMD rig, particle-ised MMD hair and skirt chains with body capsule colliders, slip and contact-ratio acceptance metrics, and fall counts over a fixed scripted test **[inferred]**.

### 2.2 mmd_mujoco_player (EnochxynL)

- Created 2026-11-15, no licence. It writes the PMX bone hierarchy as geometry-free ball joints into a **Unitree G1 MJCF** and plays VMD rotations through `mj_forward`. In its own words: "does not run gravity, collision or dynamics simulation", and "this is not IK retarget" **[read: README, https://github.com/EnochxynL/mmd_mujoco_player]**.
- Useful only as a small example of a Python VMD parser with Bézier interpolation feeding MuJoCo **[inferred]**.

### 2.3 Searches that found nothing

- PMX or VRM → MJCF/URDF converters, VRM + RL, MMD + DeepMimic / MuJoCo / Unity ML-Agents, and Qiita/Zenn/note write-ups of RL on an MMD model all returned nothing. The Japanese searches turned up only kinematic VMD-to-avatar tools for VRChat **[read: search results listed in section 1]**.
- **No one appears to have published:**
  - a physics-simulated anime character (MMD, VRM or other) that dances by RL or motion imitation;
  - one that jumps;
  - any simulated character, anime or not, balancing in high heels.

---

## 3. Near neighbours: motion and physics

| Project | Who and when | What it shows | Relevance |
|---|---|---|---|
| **GMO iREX 2025 G1 dance** | GMO AI & Robotics Trading, show 3–6 Dec 2025, post 15 Dec 2025 | A real G1 performs "Bling-Bang-Bang-Born" (an anime opening) from **professional-dancer mocap** (not MMD). About 4,000 parallel sims, about 5×10⁹ policy steps, about 1 day of GPU time. The choreography was split into segments; rewards for tracking, uprightness and self-collision were hand-balanced. Problems: raw retargets fell; fixing arm collisions shifted the reward balance; worn carpet made the left foot slide. No code **[read: https://developers.gmo.jp/technology/78173/]** | An anime-song hip-hop-ish dance is doable on a robot, at about 1 GPU-day with a pro mocap source |
| **BeyondMimic** | HybridRobotics, 2025 | One-policy tracking of 3-minute LAFAN1 sequences including "jumping spins, sprinting, and cartwheel". Code: `HybridRobotics/whole_body_tracking`, MIT **[read: https://beyondmimic.github.io/, GitHub API]** | Our chosen method family; a proof that jumps and spins are trackable on a human-proportioned body |
| **KungfuBot (PBHC)** | Xie et al., NeurIPS 2025 | Video → reference cleanup → tracking with an adaptive curriculum for highly dynamic kung-fu and dance on a G1. Code `TeleHuman/PBHC` (no licence file) **[read: https://arxiv.org/abs/2506.12851, GitHub API]** | Physical-feasibility filtering of references before tracking |
| **RobotDancing** | Sun et al., arXiv 2509.20717 (v2 Aug 2026, R-AL) | Residual-action tracking of 8 LAFAN1 dances, "long-horizon, high-energy" on a G1. It notes retargets are "kinematically plausible but dynamically inconsistent", so errors accumulate **[read: https://arxiv.org/abs/2509.20717]** | Explains why long dances destabilise; residual actions on top of the reference are the fix (Isaac-Robot-MMD also uses residuals) |
| **g1-dance / g1-dance-rtx3050** | `supat-roong` (Oct 2026), `Skura3` (Oct 2026), both MIT | Video → G1 dance in **MuJoCo** / **mjlab**; the second fine-tunes on a 4 GB RTX 3050 **[read: GitHub API descriptions]** | Shows MuJoCo-side tracking stacks run on very modest GPUs |
| **Olaf** | Disney Research (Müller et al.), arXiv 2512.16705, Dec 2025 / Apr 2026 | RL guided by **animator-authored** walk and stand cycles keeps a non-human-proportioned character "in character". Adds rewards for impact noise and actuator temperature; face, mouth and arms use classical control **[read: https://arxiv.org/abs/2512.16705]** | The best published case of stylised proportions + authored animation + RL tracking. Only walking was shown |
| **ReActor** | Disney Research, arXiv 2605.06593, May 2026 | Retargeting optimised *inside* the physics sim jointly with the RL tracker, for bodies that differ greatly from a human **[read: https://arxiv.org/abs/2605.06593]** | Directly addresses "a motion made for another body"; no code stated |
| **QuietWalk** | Hu et al., arXiv 2604.23702, Apr 2026 | Humanoid robot walking across footwear including **high heels**, in sim and on hardware **[read: abstract, https://arxiv.org/abs/2604.23702]** | The only heel-related RL result found; walking only, heel geometry not given in the abstract |
| **miu200521358 MMD tools** | Japanese MMD tool author, 2019 onward | `vmd_sizing` (MIT): regenerates a VMD fitted to a target model's proportions. Also `vrm2pmx`, auto motion trace from video, and an experimental `mmd-text-to-motion` built on MDM (MIT, 2023) **[read: GitHub API / READMEs, https://github.com/miu200521358/vmd_sizing]** | A ready, community-standard *kinematic* refit of FaSHioN to her shorter legs before physics; Windows GUI, so it may need porting **[inferred]** |

Research on skirts or long hair *coupled* to an RL-controlled body: none found. Garment papers (PhySkin, PhysDrape, Dress Anyone) simulate cloth on a kinematic body, and "Learning to Dress" (2018) is the only RL + cloth work. That supports keeping Secondary Physics one-way **[read: search results; inferred conclusion]**.

---

## 4. The "alive" side: who drives a 3D anime body with a Mind

| Project | Body | What drives the body | Voice and lip sync | Notes |
|---|---|---|---|---|
| **Project AIRI** (`moeru-ai/airi`, MIT, created Dec 2024, about 51.8k stars, pushed 2026-11-26) | Live2D, VRM, and since Jul 2026 an **MMD package** (`packages/stage-ui-mmd`) | Canned: a looping idle VMD, plus VMD one-shots mapped from 9 LLM emotions (happy, sad, angry, think, surprise, ...); morph expressions; procedural blink and gaze. Bullet (Ammo.js) hair and skirt physics, CCD IK | wLipSync vowels → MMD あいうえお morphs; pluggable TTS (ElevenLabs, Azure, local Kokoro, ...) | Self-hosted "Grok Companion" alternative; plays Minecraft and Factorio **[read: repo README and package source, https://github.com/moeru-ai/airi/tree/main/packages/stage-ui-mmd]** |
| **Open-LLM-VTuber** (about 15k stars, last push May 2026) | Live2D | Live2D expressions | Hands-free voice with interruption, offline | No 3D body **[read: GitHub API description]** |
| **Amica** (`semperai/amica`, MIT, pushed Nov 2026) and **ChatVRM** (pixiv, MIT, archived May 2025) | VRM | Canned VRM animations | TTS + viseme | **[read: GitHub API; AIRI README lists them as references]** |
| **Grok "Ani" / Animates** | Proprietary 3D anime companion | Unknown. A single X post claims an on-device full-body motion-generation model | n/a | Removed from Grok around Sept 2026; secondary sources only, not verified **[inferred]** |
| **Neuro-sama 3D** (Vedal) | 3D model since a Nov 2025 debut | Fan wikis say it moved "without preset motions". Mechanism undocumented | n/a | Not verified at any primary source **[inferred]** |
| **Conversational Virtual Agent with Physics-based Interactive Behaviour** (Llobera, Li, Nagorny, Charbonnier, Steinicke; Artanim + Univ. Hamburg; about 2025, VR demo) | Realistic human (Didimo), Quest 3, Unity | **Physics**: a DReCon-style RL policy in **MuJoCo** tracks per-frame Motion Matching targets. The LLM (GPT-4o / Gemini 2.5 Pro) emits function calls "walk towards player", "step back", "walk forward" plus facial-expression presets. When pushed, the agent stumbles and the LLM reacts ("please don't push me again") | Google STT → LLM → ElevenLabs / Google TTS, Oculus lip sync with 15 visemes | Calls itself "to our best knowledge, the first demo to couple emergent, physics-based reactions with LLM-driven intelligence". Only 3 locomotion behaviours **[read: PDF, https://www.artanim.ch/pdf/publications/136.pdf]** |
| **Text → physics humanoid research**: CLoSD (ICLR 2025), MaskedMimic, Humanoid-LLA (arXiv 2511.22963), SCRIPT (arXiv 2605.22894) | Simulated humanoid / G1 | Text → diffusion or token planner → physics tracking policy. Humanoid-LLA maps free-form language to whole-body motion with RL physical feedback, in sim and on real robots. SCRIPT is language-driven diffusion control trained on 1,200 h of motion | n/a | Code for SCRIPT is promised, not confirmed **[read: arXiv abstracts; CLoSD/MaskedMimic from search snippets only]** |

---

## 5. What this implies for this project

### 5.1 How realistic is a 27-second jump-heavy dance in high heels?

- **It has not been done.** The closest anime-physics project stopped at walking and a low-flight jog (about 4% airborne) on flat, box-like soles. It routed all real dance tracking through a robot body instead, and still lists long VMD dances as unstable **[read: §2.1]**. Our FaSHioN target (three jumps, two deep squats, a high kick, two jump half-turns) is well beyond anything shown on an anime body.
- **Human-proportioned bodies can do it.** BeyondMimic tracks jumping spins in 3-minute clips, and GMO put a full anime-song dance on a real G1 at about 1 GPU-day **[read: §3]**. So the *motion class* is feasible for a per-frame tracker; the novel risks are her proportions and her shoes.
- **Heels are the biggest unknown.** No physics character work on heels exists; QuietWalk only walks in them. **[inferred]** A heel shrinks the contact patch to a narrow forefoot plus a point. That makes landings from jumps and pivots in half-turns the likely failure points.
- **Reasonable fallbacks, in order** **[inferred]**:
  1. model the shoe as a forefoot box plus a small heel box and accept a lower-fidelity landing;
  2. give the sole a slightly larger collision footprint than the visible sandal (cheat invisibly);
  3. soften the jumps in the Reference Motion (lower apex, shorter flight) — permitted by the map's "physical validity outranks exact matching";
  4. as a last resort, split the 27 s into segments tracked by one policy with phase input, as GMO did.
- **Retarget kinematically first.** Fit FaSHioN to her shorter legs (MMD Tools / `vmd_sizing`-style sizing, foot IK) *before* RL. The Isaac-Robot-MMD author hit unreachable foot targets from a VMD made for a different model, and RobotDancing / ReActor show that dynamically inconsistent references are what destabilise long tracking **[read: §2.1, §3]**.
- **Expect many iterations, but modest compute.** Isaac-Robot-MMD's whole walking line took about 4 GPU-hours. A 27-second dance with jumps will likely need a rented GPU and reward tuning more than raw hours. This is consistent with ticket #4's estimate **[inferred]**.

### 5.2 Released tools worth adopting

- **Adopt the design, not the code, of Isaac-Robot-MMD.** Its code is Windows / Isaac / PhysX, while we chose MuJoCo on a Mac. Its decisions match ours and can be copied as checks **[inferred]**:
  - capsule limbs with box soles and non-load-bearing hair and clothes;
  - segment-fraction masses;
  - a skin bridge from simulated links to the full MMD bone set, including D-bones;
  - MMD hair and skirt chains particle-ised with body-capsule colliders, one-way;
  - acceptance by fall count, slip speed and contact ratio over a fixed scripted test.
- **BeyondMimic / whole_body_tracking (MIT)** and the MuJoCo-side stacks (mjlab, Apache-2.0; g1-dance examples, MIT) remain the training base already chosen. KungfuBot's reference filtering and RobotDancing's residual actions are worth borrowing **[read: §3]**.
- **`vmd_sizing` (MIT)** as a reference for proportion refitting of VMDs. **AIRI's `stage-ui-mmd` (MIT)** as a reference for VMD playback, あいうえお lip sync and emotion → motion mapping in a live viewer **[read: §3, §4]**.
- Nothing found converts PMX → MJCF with dynamics; ticket #5's own Blender-script route stands.

### 5.3 What the "alive" projects suggest for stages 2 and 3

- **Every shipping AI companion uses canned or kinematic motion; physics is research-only.** The one LLM-over-physics demo used the architecture already implied by our map: the LLM emits a small vocabulary of high-level behaviour calls, a kinematic target generator turns each into per-frame poses, and one RL tracking policy follows them under physics. Physical events (a push, a fall) are fed back to the LLM as text so it can react **[read: Artanim PDF]**. This matches a stage-2 Movement Repertoire behind one tracking policy, selected by the stage-3 Mind through named actions **[inferred]**.
- **Stage 2.** Keep the repertoire as named, discrete movements (stand, walk-to, turn, a few singer's gestures, the dance) chosen by name. AIRI's emotion → VMD mapping and Artanim's three function calls are both tiny vocabularies, and both work **[read/inferred]**. Text-to-motion diffusion feeding a tracker (CLoSD, SCRIPT, Humanoid-LLA) is the research path to open-ended movement later, but none ships ready-to-use code for an anime body **[read: abstracts]**.
- **Stage 3.** Speech and lip sync are solved off the shelf. AIRI drives MMD あいうえお morphs from TTS audio with wLipSync, and its pluggable TTS and LLM layers are the most complete open template for the Mind and voice loop **[read: §4]**. The gap is real-time rendering of the cel look with Secondary Physics outside Blender, which AIRI solves with three.js + Ammo.js (canned motion only) **[inferred]**.
- **Licensing.** Every serious project here keeps models and motions out of git and records the credits. Isaac-Robot-MMD's README explicitly excludes them, and AIRI loads user-supplied ZIPs at runtime. That confirms our "scripts and docs only" stance is the norm **[read: §2.1, §4]**.

## Open questions this research could not settle

- Whether any bilibili, YouTube, niconico or X creator has shown an RL-trained MMD body dancing without a repository. Those sites were not browsed directly.
- Exact heel modelling and results in QuietWalk (only the abstract was read).
- How Grok's Ani and Neuro-sama's 3D body are actually driven (no primary sources).
- Isaac-Robot-MMD's G1 jump-tracking quality (no metrics published) and whether Anon's model wears heels.
