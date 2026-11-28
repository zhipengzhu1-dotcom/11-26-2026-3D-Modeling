# Community projects like ours: what to adopt

Researched 2026-11-28. Builds on `docs/research/similar-projects.md` (branch `research/similar-projects`, called "the earlier study" below) and does not repeat it. The movement side (fitting a motion to her body, training her Controller to follow it) belongs to a separate study running beside this one and is left to it. Nothing in this file is derived from her model, and nothing was installed or run: every finding comes from reading code, docs and repository data.

**Question.** Which public, well-supported projects are doing what we are doing more capably than we are, and which of their work should we adopt in place of our own? That means whole projects like ours, and every part of her except movement: bringing an MMD model into a real-time viewer, her look, her hair and clothes, her mouth shapes, her Voice, her Mind and live interaction.

## How far to trust this

| Label | Meaning |
|---|---|
| **P** | Read this session at the owner's own source: repository code, README, official docs, or GitHub's own repository data (licence, dates, commit counts) |
| **R** | Rests on a README's or product page's description, or a demo, not checked against the code |
| **S** | Read only in a secondary source or a search-result summary |
| **I** | My own inference from what was read |

## Answer

### The table

| Part of her | What we have or plan | Best community counterpart | Better for her? Why | Verdict |
|---|---|---|---|---|
| **The whole project** (physics dance, free movement, Mind and Voice) | Our own throwaway prototypes | None. Nearest: Isaac-Robot-MMD [1][2], a new Whale-chan project in MuJoCo [4]–[7], Project AIRI [8][9] | Nobody has an anime character dancing, or balancing in heels, under physics. Nobody joins a talking Mind to a physically simulated anime body with a trained Controller | **Keep ours** |
| **MMD model → Simulation Body** (a Build step) | Blender 5.2 + MMD Tools script → 19-part body in MuJoCo's format | Isaac-Robot-MMD's PMX → 27-body converter (Isaac Sim / PhysX) [2] | No. It targets PhysX, and the earlier work found PhysX would break her soft springy joints on import (issue #23). Our body is locked | **Keep ours** |
| **Visible Mesh follows the Simulation Body** | Write-back of part rotations onto the full MMD rig | Isaac-Robot-MMD's skin bridge (simulated links → all skin bones, including D-bones) [earlier study] | The same idea, already ours. Useful only as a cross-check on D-bones and twist | **Keep ours** |
| **MMD model in a real-time viewer, look and physics intact** | Nothing yet ("the live viewer" is open) | **babylon-mmd** (MIT): PMX/VMD, MMD IK and append transforms, SDEF, MMD morphs, an MMD toon shader, Bullet physics in WebAssembly [12][13] | Yes. It is the only maintained open runtime that runs the model's *own* rigid bodies and joints, which is how her Secondary Physics is built today. Everything is code. It loads local files, so nothing is uploaded | **Adopt** (trial 1) |
| **Anime look in real time** | Hand-built EEVEE recipe, offline | babylon-mmd's MMD toon shader as the base; our recipe ported onto it. Unity's lilToon is excellent but does not fit | Better only as a carrier. The look itself (two-step ramp, light outlines, rim, bloom, render-time tints) stays ours. The earlier look study already listed each part as portable | **Adopt in part** (same trial) |
| **Hair and dress physics in real time** | MMD rigid bodies in Blender (offline); cloth for the skirt being tried today | Rigid bodies: babylon-mmd's Bullet. Cloth: Newton's GPU cloth on the PC (per the cloth study) | Rigid bodies: yes, the same data runs live. Cloth: no web or Mac real-time counterpart found | **Adopt** rigid bodies (trial 1); **watch** cloth |
| **Mouth shapes from her speaking voice, live** | Nothing yet | **wLipSync** (MIT, a web port of uLipSync): MFCC vowel weights from audio, already driving MMD あいうえお morphs inside AIRI [9][24][23] | Yes, for live speech. It works on any audio, needs only a per-voice calibration, and is already wired to MMD morphs in code we can read | **Adopt** (trial 2) |
| **Mouth shapes for songs and prepared lines** | Plan: forced alignment of known lyrics (Qwen3-ForcedAligner), then syllable → vowel | Rhubarb (English recogniser, Western A–H mouths) [25]; NVIDIA Audio2Face-3D (realistic faces) [26] | No. Neither targets five anime vowel morphs or Mandarin singing. Alignment against the known text stays the most exact route | **Keep ours** |
| **Speech in → language model → speech out** (her Mind's loop) | Nothing yet | **Pipecat** (BSD-2, Python): local Whisper on Apple Silicon via MLX, Ollama, local TTS services, Silero voice detection, mem0 hook, local audio transport [27][28] | Yes. It is the best-supported open framework that fits a Python, headless, local-only project. AIRI is larger but is an app built around canned motion. Open-LLM-VTuber is Live2D only and its v1 is frozen. SGLang-Omni's cascade is Linux only | **Adopt** (trial 3) |
| **Her Voice** | Qwen3-TTS, designed from a description (settled) | The stacks' stock voices (Kokoro, ElevenLabs, GPT-SoVITS…) | No. Her Voice rule forbids cloning a real person; the stacks' value is the plumbing, not the voices | **Keep ours** |
| **Memory between Live Sessions** | Open | mem0 (Apache-2.0), Letta (Apache-2.0). AIRI's memory is still a stub [9] | Unknown until the loop runs. Her memories are a Kept Result in `~/Vodyanitsa/`, which favours something file-based and local | **Watch** |
| **Persona and Lore Fidelity scoring** | Persona written from the lore study; rubric open | PingPong-style judging: one model plays her, one plays a user, a panel of models scores [34] | The method fits the rubric question. No code is adopted | **Adopt in part** (method only) |
| **Mind → body** (choosing what she does) | Plan: the Mind picks named movements from her Movement Repertoire | The Whale-chan project's intent schema: the language model sees the Controller's current actions and state and may only pick from them, and gestures wait for stable support [5]. AIRI maps nine emotions onto canned VMD one-shots [9]. NVIDIA's Metatron takes goals from skill code at 50 Hz [31] | The Whale-chan pattern is the best published fit for a body that can fall, and it confirms our plan. AIRI's mapping assumes canned motion. Metatron is research on a robot | **Adopt in part** (pattern); **watch** Metatron |
| **An all-in-one native agent** | — | **MMDAgent-EX** (Apache-2.0, Nagoya Institute of Technology): MMD renderer with physics, socket control that can set any bone or morph, streamed-audio lip sync, Apple Silicon builds [15]–[19] | Close in kind, but quiet (no commits in the last three months), small (58 stars), and it cannot load PMX directly; it needs a conversion to PMD plus CSV [16] | **Watch** (fallback if trial 1 fails) |

### The smallest trial for each "adopt"

None of these puts her model in git. Each runs from a script, keeps its outputs in the git-ignored `review/` folder, and serves pages only on `localhost`. Serving her model on any public address would be redistribution.

1. **babylon-mmd as the live viewer, with her own rigid bodies.**
   - **Step A:** a local page loads her PMX from the machine, plays the stage 1 dance's VMD with Bullet physics on, and is filmed headlessly for 35.5 s. Compare its hair and skirt with the Blender clip at an Eye Check, and record frames per second on the M4 Max.
   - **Step B:** a Python MuJoCo process streams her Simulation Body's joint rotations over a WebSocket, and the page applies them to her bones with physics on.
   - **It passes when:** it holds 60 fps; her hair and dress follow without explosions; a first port of the toon recipe (ramp, outline, rim, tint) reads as her look at an Eye Check.
   - **Open point:** babylon-mmd's docs warn against posing bones directly on its model and document only a position setter [14]. Step B may have to feed poses in as a custom animation source.
2. **wLipSync on her designed Voice.**
   - Render ten Mandarin lines with her Qwen3-TTS voice.
   - Calibrate a wLipSync profile from her own synthetic vowels, then run it over the ten lines.
   - Compare its per-frame vowels with the vowels given by forced alignment of the same lines (a Measured Check: share of frames in agreement), and judge both on her face at an Eye Check.
   - **It passes when** the live route is close enough to the aligned route that the human cannot pick out which one is live.
3. **Pipecat as her Mind's loop, all local on the Mac.**
   - Wire MLX Whisper (large-v3-turbo, Mandarin), a local language model with the Persona as its instructions, and a custom TTS service wrapping her Qwen3-TTS voice prompt.
   - Give the language model one function, `perform(movement)`, restricted to a fixed list. Each call is only logged for now; nothing moves.
   - Measure time from the end of the human's speech to her first sound, check that interrupting her stops her voice, and check that every function call stays inside the list.

### In short

- **The earlier study's finding still holds.** Nobody has published an anime character that dances, jumps or balances in high heels under physics (§3).
- **One new near neighbour has appeared.** An MIT project from October 2026 puts an anime mascot, Whale-chan, into MuJoCo with 23 actuators and a DeepSeek text Mind [4].
  - Its walking is scripted (inverse kinematics and PD control), and its learned walking is still experimental [6].
  - It is the first public project to join a language model to an actuated anime body in MuJoCo. Its interface design is worth copying.
- **No whole project should replace ours.** Three parts should be adopted: babylon-mmd for the live viewer (with her own rigid bodies), wLipSync for live mouth shapes, and Pipecat for her Mind's loop.
- **Nothing found beats our offline Build.** That covers the Simulation Body, the write-back, the EEVEE look and the forced alignment for songs.

## Constraints that decide what is adoptable

- **Her terms.** No redistribution, no commercial use, no R18, no taking her parts for other models. Anything that uploads her model to a service, or publishes a converted copy, is out. Converting her locally (to BPMX, PMD or VRM) for a viewer on this machine is a local copy, not redistribution **[I]**, but such a copy is itself derived from the model and stays out of git (`docs/adr/0002-model-assets-stay-out-of-git.md`).
- **Made by code** (`docs/adr/0003-made-by-code-never-by-hand.md`). Tools built around a person working in an editor (Unity, Unreal, PMXEditor plugins, DanceXR) count only as far as they can be scripted.
- **A Live Session runs her under physics, never canned.** A talking-avatar stack is adoptable for its voice, Mind and rendering plumbing, never for its motion.
- **Machines.** An M4 Max MacBook Pro (36 GB) and a Windows RTX 5090 PC. Nothing rented.
- **Her Voice** is designed from words, never cloned. Her official songs keep their official recordings.

## 1. Whole projects like ours

### 1.1 Isaac-Robot-MMD: still the closest physical one

- **Activity [P, 35].** Apache-2.0, one author, 2 stars, 12 commits since 28 August 2026, the latest on 27 November. No issues have been filed.
- **What changed since the earlier study [P, 3].** The last two weeks went into the Unitree G1 robot's dance and jump training. On 14 November the author *removed* "garment adaptation, motion prior, cloth analysis" files.
- **What it does today [P, 1][P, 2].**
  - The anime body (Chihaya Anon) still dances only as kinematic playback: "身体继续由 VMD 驱动… 身体是运动学动画，不会因为头发或裙摆受力而改变舞步或维持平衡" (the body is still driven by the VMD; it is kinematic animation and does not change its steps or keep its balance because of forces from the hair or skirt).
  - Its trained walking (`train_anon_lab.py`, `play_anon_policy.py`) is unchanged.
  - Dance tracking under physics exists only on the G1. The README still lists "长序列训练稳定性" (stability of training on long sequences) as unfinished, and its one Iris Out acceptance result is a viewer's impression ("用户已认可 Iris Out 第 2500 次的观感", the user accepted the look of Iris Out at iteration 2500) with no numbers.
  - Its live preview (`physx_dance.py`, `preview_dance.py`) runs the model's hair and skirt chains in PhysX with a cel material (`cel_studio.mdl`), made the default look on 25 November.
- **Overlap with our stages.**
  - Stage 1: walking only on the anime body.
  - Stage 2: walking and turning on command.
  - Stage 3: none.
- **Whether users put their own characters in.** There is no sign of it. Every doc names one model, and its per-model fixes (skirt waist, side hair) are hand-tuned to it **[P, 2]**.
- **Verdict: keep ours, watch it.** Its real-time cel look with PhysX hair is the only live anime-physics viewer in the field. It is Isaac Sim on Windows, though, and issue #23 chose Newton and MuJoCo Warp over PhysX for her.

### 1.2 Whale-chan robot (`cyanseek/deepseek-whalechan-robot`): new since the earlier study

- **What it is [P, 4][P, 35].** MIT code, created 21 October 2026, one author, 35 commits, 4 stars, last commit 28 November 2026.
- **The character.** DeepSeek's community mascot, an anime girl with a whale tail. The project states it is unofficial. The model comes from a third-party VRM desktop-pet plugin and is "按各自许可处理" (handled under its own licence), installed from a release rather than kept in git **[P, 4]**. This is our stance on her model.
- **The body [P, 4][P, 6].** MuJoCo with "23 actuators, a free base, ground contact and torque limits". The training README describes the body as an estimated 1.267 kg, i.e. a small robot-scale figure, not a human-scale anime body.
- **How it moves [P, 4].** "当前使用显式 IK/PD 控制和理想仿真本体反馈，验证范围为平地场景" (it currently uses explicit IK/PD control with ideal simulated feedback, validated on flat ground).
  - Its motions are small steps, turning, waving, a tail swing, nodding and an experimental small hop.
- **Learned walking [P, 6].** A PPO pipeline on mjlab exports ONNX for plain CPU MuJoCo, on a flat-ground velocity task with no motion data. "the repository does not include trained weights", and "learned locomotion is experimental". It was trained on an RTX 5070 Ti.
- **Its Mind [P, 5].**
  - DeepSeek turns text into one of a fixed set of intents: approach, go to a marker, wave, wag the tail, stop.
  - Each request carries "the current controller's supported actions and its state at submission". "unsupported and multi-step requests do not start an arbitrary action"; gestures wait for support; "only the simulation thread writes actuator targets"; "raw joints and shell commands are not part of this interface".
  - The persona shapes words only; expressions come from the controller's state.
  - Voice is "future adapters".
- **Overlap with our stages.**
  - Stage 1: none (no dance, no learned movement).
  - Stage 2: a scripted repertoire chosen on request.
  - Stage 3: a text Mind with a safe action interface.
- **Look [R, 4].** OpenGL rendering with expressions and blinking. No toon pipeline is described.
- **Verdict: watch, and adopt in part.** The code does not fit her: its body is scripted, robot-scale and not trained on a Reference Motion. Its Mind-to-body contract is the clearest published one for a character that can fall, and it matches our plan, so copy it as a design: the Mind sees the Controller's current menu and state, chooses from a fixed list, and the simulation alone writes joint targets.

### 1.3 Project AIRI: the best-supported living character, canned body

- **Activity [P, 35].** MIT, about 51,900 stars, more than 100 commits from 18 authors in the last three months, release v0.15.4 on 12 November 2026, 302 open issues.
- **Platforms [R, 8].** Desktop (Electron) for macOS and Windows, plus the web.
- **What its MMD stage does [P, 9].**
  - It renders through `@moeru/three-mmd` with its Ammo.js (Bullet) physics adapter (`utils/ammo.ts`).
  - Mouth shapes: wLipSync vowel weights are written to the MMD あいうえお morphs after the VMD update "so lip-sync wins over VMD morphs" (`composables/mmd/lip-sync.ts`).
  - Body: nine emotions map to VMD names played as one-shot gestures, and "a missing name [is] a no-op" (`constants/actions.ts`).
  - A new `motion-driver-magic` package fits small statistical models (VAR, AR-HMM) to recorded motion and generates procedural idle frames. It is kinematic.
- **Memory [R, 8][P, 9].** The README marks "Memory Alaya (WIP)", and the `memory-pgvector` service's code is an empty event handler.
- **Users' own characters [P, 9].** Yes. It has a ZIP loader and an on-device file store (`mmd-zip-loader.ts`, `opfs-loader.ts`), and users load their own Live2D, VRM and MMD models.
- **Overlap with our stages.** Stage 3 talking and lip sync only; motion is canned.
- **Verdict: keep ours for the body; borrow its parts.** Its lip-sync wiring is the reference for trial 2. Its Mind loop is heavier than we need and is built for canned motion (an emotion picks a clip). Adopting the whole app would mean replacing its motion layer with a pose stream from MuJoCo inside a fast-moving Vue monorepo **[I]**. Pipecat (§2.5) is the lighter fit.

### 1.4 Other living-character projects examined

| Project | What it actually does | Why it does not fit her |
|---|---|---|
| **MMDAgent-EX** (Apache-2.0; Lee Lab, Nagoya Institute of Technology) | A native MMD renderer with physics; Julius speech recognition; Open JTalk speech; FST dialogue scripts. Socket and WebSocket control, including `MODEL_BINDBONE` and `MODEL_BINDFACE` to set any bone or morph. Streamed 16 kHz PCM with lip sync. Verified on an M2 MacBook Air **[P, 15–19]** | It is the closest all-in-one, and the only one whose docs show an outside program setting bones (bone positions and rotations through `MODEL_BINDBONE`). But it has had no commits since 22 February 2026 and has 58 stars. It "cannot load .pmx files directly" (conversion to PMD plus CSV is needed). Its docs warn that supported features are not guaranteed **[P, 16][P, 35]**. Fallback if trial 1 fails |
| **Open-LLM-VTuber** | Offline voice chat with interruption and many local speech recognisers and voices. Live2D only. Long-term memory "temporarily removed". A v2 rewrite is planned, and v1 feature requests are closed **[P, 29]** | No 3D body; no commits in the last three months **[P, 35]** |
| **Persona Engine** (now `elevenyellow/handcrafted-persona-engine`) | Live2D, language model, speech recognition, TTS and RVC; 1,401 stars; last commit May 2026 **[P, 35]** | Live2D only; voice conversion (RVC) is a cloning route we avoid |
| **Amica**, **ChatVRM** (archived 2025), **Lobe Vidol** (last release 2024), **Mate-Engine**, **ai-iris-avatar** | VRM or Unity companions with canned animation **[P, 35; descriptions only]** | Canned motion; ChatVRM is archived, and Lobe Vidol's last release dates from 2024 |
| **TalkingHead** (MIT, 1,721 stars) | A browser class for full-body avatars with lip sync in several languages, and a motion layer for language-model control **[R, search summary]** | Realistic avatars (not MMD); canned motion |
| **jakcm/mmd-agent-motion** | three.js r171 ("MMDLoader 最后支持版本", the last version that supports MMDLoader); plays VMD dances; Edge TTS lip sync **[P, 38]** | Personal, no licence, 0 stars |
| **DanceXR** (commercial) | Real-time PMX viewer with automatic PMX physics and XPBD cloth, on PC, mobile and Quest **[R, 22]** | Closed and not scriptable; an editor-style app |

## 2. Part by part

### 2.1 An MMD model in a real-time engine, look and physics intact

**What changed in the field.** three.js, which the earlier study assumed for AIRI, *deprecated its MMD modules in r170* and pointed users to an outside package "until r172" **[P, 11]**. A personal project confirms r171 was "the last version with MMDLoader" **[P, 38]**. Its successors are young:

| Runtime | Licence | Activity | What it keeps of an MMD model | Fit |
|---|---|---|---|---|
| **babylon-mmd** (Babylon.js) | MIT | One maintainer, 2,001 commits, v1.3.0 (23 July 2026), last commit 28 October 2026, 3 commits in the last three months, 1 open issue **[P, 12][P, 35]** | PMX, PMD, VMD and VPD; "Solve Append transform"; MMD IK; SDEF; MMD morphs; a "Custom MMD toon fragment shader"; WebGL and WebGPU. Bullet in WebAssembly is the recommended physics; the Ammo.js backend is "slightly unstable", and Havok has "low simulation reproduction" **[P, 12][P, 13]** | **Best.** It runs the model's own rigid bodies faithfully. Risk: one person, and slower lately |
| `@moeru/three-mmd` (AIRI's) | MIT | 2 authors, 19 commits in three months, v0.1.2 **[P, 35]** | Toon material; IK and grants; Ammo.js physics; a spring-bone package **[P, 10]** | Fine, but young and tied to AIRI's needs |
| `yohawing/three-mmd-loader` | MIT | 24 stars, v0.9.0 on 27 November 2026 **[P, 35]** | PMX and VMD, prebuilt Bullet, IK and append, SDEF; WebGPU experimental **[P, 21]** | Promising, very new |
| **Godot-MMD** (.NET) | MIT | 46 stars, 14 commits **[P, 20]** | PMX with Bullet rigid bodies (BulletSharp) and IK | "designed primarily for rendering and recording videos, so it may not be suitable for real-time gameplay" **[P, 20]** |
| **saba** (C++ OpenGL) | MIT | Last commit September 2023 **[P, 35]** | PMX with Bullet | Stale |
| **MMDAgent-EX** | Apache-2.0 | Quiet since February 2026 | See §1.4 | Fallback |

- **Why babylon-mmd and the web, and not Unity or Godot.**
  - Our Live Session already needs a MuJoCo process and the Controller. A browser page (or a WebView) fed over a socket keeps the viewer as code and works on both machines **[I]**.
  - Google DeepMind also publishes official MuJoCo WebAssembly bindings (`@mujoco/mujoco`, "still a WIP") **[S, 33]**, and NVIDIA's Metatron demo runs MuJoCo with a trained controller in the browser **[P, 31]**. Running the whole Live Session in one page is therefore a later option, not a requirement **[I]**.
- **VRM as an alternative route.** VRM Add-on for Blender (MIT, v4.10.5, November 2026) exports VRM from a script and sets MToon from Python **[P, 32]**, and pixiv's three-vrm (MIT, v3.6.0, 24 November 2026) renders it **[P, 35]**. But VRM spring bones would replace her MMD rigid bodies with a different, simpler system, throwing away the stage 1 Secondary Physics work **[I]**. **Watch**, not adopt.

### 2.2 Anime rendering in real time

- **What exists.** babylon-mmd's MMD toon shader, which is driven by the model's own toon and sphere textures **[P, 12]**. In Unity there are lilToon (MIT, 1,618 stars, v2.4.1, October 2026) and Unity Toon Shader **[P, 35]**: excellent, community standards for avatars, but Unity-editor tools.
- **What carries over.** The earlier look study already shows that every part of our recipe except Line Art carries over to an engine: ramp shading, inverted-hull outlines, rim, emission, bloom, the Standard view transform and alpha ordering (`docs/research/anime-look-in-blender.md` §8).
- **Verdict: adopt in part.** Take babylon-mmd's renderer, port our recipe onto it as custom material code, and judge it against the Blender stills at an Eye Check. No community shader reproduces our tuned look out of the box, and none needs ripped game textures that we lack **[I]**.

### 2.3 Hair and clothing physics in real time

- **Rigid bodies.** babylon-mmd's Bullet runs the shipped rigid bodies and joints, so collider fixes made for stage 1 apply unchanged. This agrees with the Secondary Physics study's "carry-over to real time" section.
- **Cloth.** The cloth study found no real-time counterpart for Blender Cloth. Newton's GPU cloth on the RTX 5090 is the path if her Live Session runs there, and DanceXR's XPBD cloth is closed **[R, 22]**. Isaac-Robot-MMD dropped its own cloth-analysis code on 14 November **[P, 3]**. **Watch.**
- **One-way coupling everywhere.** Every project read keeps hair and clothes driven by the body and never driving it: Isaac-Robot-MMD's PhysX preview, AIRI and babylon-mmd (both run physics after the pose) **[P, 2][P, 14]**. That matches our Secondary Physics definition.

### 2.4 Mouth shapes from audio

| Tool | How | For her |
|---|---|---|
| **wLipSync** (MIT, v1.3.1, August 2026) / **uLipSync** (MIT, 1,728 stars) | MFCC features compared with a per-voice calibrated profile of A, I, U, E, O and N. Real time. Phoneme labels are arbitrary, so the method is not tied to a language **[P, 23]**. AIRI drives MMD morphs with it **[P, 9]** | **Adopt for live speech.** Singing is not covered in its docs **[P, 23]** |
| **Forced alignment** of known text (our plan: Qwen3-ForcedAligner, from the voice study) | Character timestamps, then syllable → vowel morph | **Keep for songs and prepared lines.** It is exact where the words are known |
| **MMDAgent-EX lip sync** | Streamed PCM, or phonemes with durations mapped through `lip.txt` **[P, 18]** | Only with MMDAgent-EX |
| **Rhubarb** | PocketSphinx "only recognizes English"; the phonetic mode is "language-independent" but "less precise". Outputs Western A–H mouth shapes **[P, 25]** | No |
| **NVIDIA Audio2Face-3D** (SDK MIT; models under NVIDIA's Open Model licence) | Jaw, tongue, eyes and skin deformation from speech; NVIDIA GPU with CPU fallback; no Mandarin or singing statement **[P, 26]** | No. It is built for realistic faces, not five anime vowel morphs |

### 2.5 A speaking character stack

| Stack | Fit |
|---|---|
| **Pipecat** (BSD-2, 17,500 stars, v1.17.0 on 22 November 2026, 17 authors in three months) | A Python pipeline framework. Local Whisper on Apple Silicon through MLX ("runs entirely locally"; multilingual models such as large-v3-turbo) **[P, 28]**. Ollama; Kokoro, Piper and XTTS; Silero voice detection; mem0; a local transport **[P, 27]**. **Adopt** as the loop's skeleton, with our own Qwen3-TTS service plugged in **[I: custom services are the framework's design; not checked in its code]** |
| **LiveKit Agents** (Apache-2.0, 15,400 stars, v1.9.0 on 25 November 2026) **[P, 35]** | The same class of framework, built around a WebRTC server. Not read further; the extra server buys nothing on one machine **[I]** |
| **AIRI** | An app with a renderer; see §1.3 |
| **SGLang-Omni** voice cascade | Linux with an NVIDIA GPU only (voice study); usable on the PC under Linux, and not on the Mac |
| **Open-LLM-VTuber**, **Persona Engine** | Live2D; see §1.4 |

- **Memory.** mem0 (Apache-2.0, 69,600 stars) and Letta (Apache-2.0, 25,600 stars; last release May 2026) are the large projects **[P, 35]**. Neither was read in depth. **Watch** until the loop works, then decide against the Kept Result rule (local, backed up to the private repo).
- **Lore Fidelity.** PingPong's design (a player model, an interrogator model that plays the user, a panel of judge models) **[S, 34]** is a ready method for scoring the Persona against a rubric. PersonaEval and rp-benchmark warn that judge models disagree with people about half the time **[S, search summary]**, which supports keeping the human's judgement above any score, as with Eye Checks.

### 2.6 Driving a body's movements from the stack's decisions

- **Shipping companions.** AIRI picks a canned clip by emotion **[P, 9]**. Nothing more is on offer.
- **Physics, published.**
  - The Artanim demo (2025): three locomotion function calls over a MuJoCo tracker (earlier study).
  - The Whale-chan project (2026): a fixed intent list checked against the controller's current actions and state **[P, 5]**.
- **Research.** NVIDIA's ProtoMotions 3 (Apache-2.0, v3.3 on 10 November 2026, 2,522 stars) now couples Kimodo text-to-motion with physics training, and its Metatron controller takes "structured inputs, not text commands" (body targets, velocity, heading, style) from skill code at 50 Hz **[P, 30][P, 31]**. Metatron's weights are under NVIDIA's Open Model licence, on G1 and SOMA bodies only **[S, search summary of the model card]**.
- **Verdict: keep our plan; copy the contract.** The Mind names a movement, the Live Session checks it against what the Controller can do now, and only the simulation writes joint targets. Training belongs to the movement study. **Watch** Metatron as the research path to free movement without motion files.

## 3. Does "nobody has done this" still hold?

**Yes.** This search repeated and widened the earlier one:

- GitHub repository searches: `pmx mujoco`, `vrm mujoco`, `pmx physics humanoid`, `mmd isaac`, `mmd reinforcement`, `anime character reinforcement learning`, `vrm llm physics`, `mmd llm agent`.
- Web searches in English, Chinese and Japanese.

It found two new repositories, and neither is a counter-example:

- **Whale-chan robot**: a scripted anime mascot in MuJoCo. Its learned walking is experimental, and it has no dance and no heels **[P, 4][P, 6]**.
- **jakcm/mmd-agent-motion**: a three.js VMD player **[P, 38]**.

Isaac-Robot-MMD still plays its anime dances kinematically **[P, 2]**. No public anime or MMD character dances, jumps or balances in high heels under physics with a trained controller, and none couples a talking Mind to such a body.

**Not covered.** Bilibili, YouTube, niconico and X were not browsed directly; a video-only demo would have been missed. One Japanese hit, a pull request titled "PMX conversion tool… physics tuned for the engine" in `YamaguchiHayato/Project.DS`, returned 404 and could not be read.

## 4. What this changes in earlier studies and decision records

- **The earlier study said AIRI's MMD stage runs on three.js with Ammo.js.** It still uses Ammo.js, but through `@moeru/three-mmd`, because three.js dropped its own MMD modules after r171 **[P, 9][P, 11]**. Any plan to build the live viewer on three.js's built-in `MMDLoader` is out of date.
- **The earlier study recommended AIRI as "the most complete open template" for the Mind and voice loop.** This study narrows that. AIRI's memory is a stub **[P, 9]**, and its body layer assumes canned clips. For a Python, headless project, Pipecat is the better skeleton, and AIRI is the better reference for MMD lip sync.
- **No conflict with the decision records.**
  - babylon-mmd keeps the MMD rigid bodies that issue #7 chose.
  - The real-time look reuses the recipe from issue #16.
  - Mouth shapes still come from the sound, as `0007` requires.
  - Nothing found needs her model uploaded or published.
- **One caution for ADR 0002.** Every viewer trial must serve her model only on `localhost`. A GitHub Pages-style demo, the default deployment in several projects read (jakcm's deploys on every push **[P, 38]**), would publish her model.

## 5. What could not be verified

- **babylon-mmd's bone API.** Whether an outside pose stream can drive its bones each frame with physics following: the docs document only `setWorldTranslation` and warn against touching the model's skeleton directly **[P, 14]**.
- **Performance.** Its frame rate with her 77k-triangle model and 496 rigid bodies. Nothing was run.
- **MMDAgent-EX.** How faithfully it handles PMX after the PMD-plus-CSV conversion.
- **wLipSync on singing.** Its quality on a soprano singing; no source covers it.
- **Pipecat's TTS interface.** The exact interface for a custom TTS service (inferred from its design, not read in its code).
- **Whale-chan's rendering and model pipeline.** How its VRM is bound to the MuJoCo body; `EMBODIMENT.md` does not say **[P, 7]**.
- **Metatron.** Whether code is released, beyond the ONNX weights on Hugging Face **[S]**.
- **Bilibili and other video sites.** Not browsed.

## 6. Repositories examined

Licence, last commit and stars from GitHub's own repository data on 2026-11-28 **[P, 35]**.

| Repository | Licence | Last commit | One line |
|---|---|---|---|
| Jasy6307/Isaac-Robot-MMD | Apache-2.0 | 2026-11-27 | PMX anime body that walks under PhysX; dances kinematic; G1 robot dance training |
| cyanseek/deepseek-whalechan-robot | MIT | 2026-11-28 | Anime mascot in MuJoCo, scripted IK/PD, DeepSeek intent interface; new |
| moeru-ai/airi | MIT | 2026-11-28 | Largest open AI companion; MMD stage with Ammo.js physics, wLipSync, canned VMD |
| moeru-ai/three-mmd | MIT | 2026-11-21 | AIRI's MMD runtime for three.js after three.js dropped MMD |
| noname0310/babylon-mmd | MIT | 2026-10-28 | Most complete MMD runtime on the web; Bullet in WebAssembly, MMD toon |
| yohawing/three-mmd-loader | MIT | 2026-11-28 | New three.js MMD loader with prebuilt Bullet |
| culdo/web-mmd | MIT | 2026-07-18 | Browser MMD player (metadata only) |
| sselecirPyM/Godot-MMD | MIT | 2026-11-24 | Godot .NET MMD import with Bullet, made for video recording |
| benikabocha/saba | MIT | 2023-09-21 | C++ OpenGL PMX viewer; stale |
| mmdagent-ex/MMDAgent-EX | Apache-2.0 | 2026-02-22 | Native MMD spoken-dialogue agent with socket bone control |
| pixiv/three-vrm | MIT | 2026-11-24 | VRM with MToon and spring bones on three.js |
| saturday06/VRM-Addon-for-Blender | MIT | 2026-11-28 | Scriptable VRM export and MToon from Blender |
| vrm-c/UniVRM | MIT | 2026-10-19 | VRM in Unity |
| V-Sekai/godot-vrm | custom (NOASSERTION) | 2026-07-08 | VRM and MToon in Godot |
| lilxyzw/lilToon | MIT | 2026-10-20 | Community-standard avatar toon shader for Unity |
| hecomi/uLipSync | MIT | 2026-01-06 | MFCC vowel lip sync, Unity |
| mrxz/wLipSync | MIT | 2026-08-06 | uLipSync for WebAudio/WASM; used by AIRI |
| DanielSWolf/rhubarb-lip-sync | custom (NOASSERTION) | 2025-04-03 | English-first 2D mouth shapes from audio |
| NVIDIA/Audio2Face-3D | none on repo (parts MIT / Apache / NVIDIA Open Model) | 2025-09-24 | Realistic face animation from speech |
| pipecat-ai/pipecat | BSD-2-Clause | 2026-11-28 | Python voice-agent framework with local services |
| livekit/agents | Apache-2.0 | 2026-11-28 | Voice-agent framework around WebRTC |
| sgl-project/sglang-omni | Apache-2.0 | 2026-11-28 | Serving runtime with a voice cascade; Linux and NVIDIA |
| Open-LLM-VTuber/Open-LLM-VTuber | custom (NOASSERTION; README says MIT plus Live2D terms) | 2026-05-15 | Live2D voice companion; v1 frozen |
| elevenyellow/handcrafted-persona-engine | none | 2026-05-20 | Live2D persona engine |
| semperai/amica | MIT | 2026-11-12 | VRM companion |
| pixiv/ChatVRM | MIT | 2025-05-27 | VRM chat demo; archived |
| lobehub/lobe-vidol | Apache-2.0 | 2026-10-15 | Virtual idol app; last release 2024 (metadata only) |
| shinyflvre/Mate-Engine | custom (NOASSERTION) | 2026-01-20 | VRM desktop pet (metadata only) |
| Scthe/ai-iris-avatar | GPL-3.0 | 2024-12-22 | Unity talking avatar |
| met4citizen/TalkingHead | MIT | 2026-11-04 | Browser full-body talking avatar |
| kimjammer/Neuro | MIT | 2025-01-17 | Neuro-sama recreation (metadata only) |
| jakcm/mmd-agent-motion | none | — | three.js r171 VMD player with TTS lip sync |
| mem0ai/mem0 | Apache-2.0 | 2026-11-27 | Agent memory layer (metadata only) |
| letta-ai/letta | Apache-2.0 | 2026-10-18 | Stateful agents with memory (metadata only) |
| NVlabs/ProtoMotions | Apache-2.0 | 2026-11-10 | Physics humanoid training; Kimodo, MaskedMimic, Metatron |
| newton-physics/newton | Apache-2.0 | 2026-11-27 | GPU physics incl. cloth (from the cloth study) |
| MMD-Blender/blender_mmd_tools | GPL-3.0 | 2026-11-19 | Our importer (for reference) |

## Sources

Read on 2026-11-28.

1. Isaac-Robot-MMD README: https://github.com/Jasy6307/Isaac-Robot-MMD/blob/main/README.md
2. Isaac-Robot-MMD `source/pmx_prototype/README.md`: https://github.com/Jasy6307/Isaac-Robot-MMD/blob/main/source/pmx_prototype/README.md
3. Isaac-Robot-MMD commit history (GitHub API): https://api.github.com/repos/Jasy6307/Isaac-Robot-MMD/commits
4. Whale-chan robot README: https://github.com/cyanseek/deepseek-whalechan-robot
5. Whale-chan robot `docs/INTERACTION.md`: https://github.com/cyanseek/deepseek-whalechan-robot/blob/main/docs/INTERACTION.md
6. Whale-chan robot `training/README.md`: https://github.com/cyanseek/deepseek-whalechan-robot/blob/main/training/README.md
7. Whale-chan robot `docs/EMBODIMENT.md`: https://github.com/cyanseek/deepseek-whalechan-robot/blob/main/docs/EMBODIMENT.md
8. Project AIRI README: https://github.com/moeru-ai/airi
9. Project AIRI source: `packages/stage-ui-mmd/src/composables/mmd/lip-sync.ts`, `src/constants/actions.ts`, `src/constants/emotions.ts`, `src/utils/ammo.ts`; `packages/memory-pgvector/src/index.ts`; `packages/motion-driver-magic/README.md`: https://github.com/moeru-ai/airi/tree/main/packages
10. `@moeru/three-mmd` README: https://github.com/moeru-ai/three-mmd
11. three.js Migration Guide, r169 → r170 ("The MMD modules have been deprecated… until r172"): https://github.com/mrdoob/three.js/wiki/Migration-Guide
12. babylon-mmd README: https://github.com/noname0310/babylon-mmd
13. babylon-mmd docs, Runtime (physics backends): https://noname0310.github.io/babylon-mmd/docs/reference/runtime/
14. babylon-mmd docs, MMD Runtime (`MmdRuntimeBone`, `beforePhysics`/`afterPhysics`): https://noname0310.github.io/babylon-mmd/docs/reference/runtime/mmd-runtime/
15. MMDAgent-EX README: https://github.com/mmdagent-ex/MMDAgent-EX
16. MMDAgent-EX docs, PMX models: https://mmdagent-ex.dev/docs/pmx/
17. MMDAgent-EX docs, Direct Control: https://mmdagent-ex.dev/docs/motion-bind/
18. MMDAgent-EX docs, Streaming Audio Play: https://mmdagent-ex.dev/docs/remote-speech/
19. MMDAgent-EX docs, Getting & Building: https://mmdagent-ex.dev/docs/build/
20. Godot-MMD README: https://github.com/sselecirPyM/Godot-MMD
21. three-mmd-loader (yohawing) README: https://github.com/yohawing/three-mmd-loader
22. DanceXR product page: https://vrstormlab.com/jp/dancexr/
23. uLipSync README: https://github.com/hecomi/uLipSync
24. wLipSync repository: https://github.com/mrxz/wLipSync
25. Rhubarb Lip Sync README: https://github.com/DanielSWolf/rhubarb-lip-sync
26. NVIDIA Audio2Face-3D README: https://github.com/NVIDIA/Audio2Face-3D
27. Pipecat README: https://github.com/pipecat-ai/pipecat
28. Pipecat docs, Whisper STT (MLX): https://docs.pipecat.ai/server/services/stt/whisper
29. Open-LLM-VTuber README: https://github.com/Open-LLM-VTuber/Open-LLM-VTuber
30. ProtoMotions README: https://github.com/NVlabs/ProtoMotions
31. Metatron project page: https://research.nvidia.com/labs/par/projects/metatron/
32. VRM Add-on for Blender, scripting API: https://vrm-addon-for-blender.info/en-us/scripting-api/
33. MuJoCo JavaScript bindings README (via search index only): https://raw.githubusercontent.com/google-deepmind/mujoco/main/wasm/README.md
34. PingPong role-play benchmark (abstract via search index only): https://arxiv.org/abs/2409.06820
35. GitHub REST API repository, commit and release data for every repository in §6, unauthenticated: https://api.github.com/repos/{owner}/{repo}
36. Earlier studies on this repo's branches: `research/similar-projects`, `research/anime-look-in-blender`, `research/secondary-physics-no-clipping`, `research/cloth-on-her-body`, `research/her-voice-qwen3-tts-and-sglang-omni`, `research/synthetic-singing-voice`, `research/mmd-to-simulation-body`, `research/casual-clothes-for-her`
37. Project map, issue #1 (decisions and "Not yet specified")
38. jakcm/mmd-agent-motion README: https://github.com/jakcm/mmd-agent-motion
