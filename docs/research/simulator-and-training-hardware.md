# Simulator and training hardware options

Research for issue #4. All versions, platform support and prices were checked on **2026-11-26**. This area changes fast, so check again before you rely on a figure.

**Question.** We train on the M4 Max Mac first and on a rented cloud GPU later. How do these options compare: MuJoCo on CPU, MuJoCo's GPU variants (MJX, MuJoCo Warp, and whether any of them run on Apple Silicon), Isaac Lab, and Newton? For each one, what hardware does it need, how many parallel simulations does it reach, how portable are a Simulation Body and a trained controller between them, and what does cloud GPU rental cost?

The workload is a Simulated Character of roughly 15 to 20 rigid parts. Its Simulation Body learns by reinforcement learning to follow Reference Motions (dance and locomotion). Training methods are covered by a sibling ticket. Ticket #14 makes the actual decision on where training runs.

## Answer in brief

- **On the Mac, only CPU MuJoCo is practical.** No GPU path in the MuJoCo family runs on Apple Silicon today:
  - MuJoCo Warp, MJX-Warp and Newton accelerate only on NVIDIA CUDA.
  - Apple's JAX Metal plug-in has not been updated since October 2024. With current MJX it fails (tested here).
  - CPU MuJoCo is fast on this machine. It measured **about 0.8 million physics steps per second** with 14 threads, on a 17-body humanoid.
- **Every candidate cloud stack is the same physics engine on NVIDIA GPUs.** MJX-Warp, MuJoCo Warp, mjlab, MuJoCo Playground, Newton's MuJoCo solver and Isaac Lab 3.0's default Newton backend all run MuJoCo Warp underneath. Each reaches thousands of parallel worlds on one GPU.
  - Isaac Lab 3.0 installs and trains headless without Isaac Sim and without RTX hardware. The "no Isaac on a Mac" limit still applies, but only to local use.
  - Isaac Sim itself needs an RTX GPU and does not support A100 or H100.
- **Keep the Simulation Body in MJCF.** MJCF is MuJoCo's XML model format and the common format for all of these stacks. MuJoCo, MJX, MuJoCo Warp, mjlab and Playground read it natively. Newton reads it with `add_mjcf`, though it drops sensors, keyframes and plugins. Isaac Lab reads it through Newton or through its MJCF-to-USD importer.
- **A trained controller moves between stacks only if four things match exactly:** its observations, action definition, control rate and PD gains. Different contact physics still opens a sim-to-sim gap. The MuJoCo-Warp family shares MuJoCo's solver, so that gap should be small within the family. Isaac Lab on its PhysX backend is a different engine.
- **Cloud GPUs are cheap for this workload.** On-demand prices on 2026-11-26:
  - RTX 4090: about **$0.34–0.89/h** on RunPod, about $0.46/h median on Vast.ai.
  - A100 80 GB: about **$1.19–2.19/h**.
  - H100: about **$2–4.89/h**.

  A published humanoid locomotion policy trained in under 30 minutes on two RTX 4090s, which is roughly $0.35–1.80 of rental. A single-motion tracking run plausibly costs **from a few cents to about $15** on a 4090-class GPU. A large Movement Repertoire costs tens of dollars. All of these figures are estimates, explained below.

## 1. Options compared

| | MuJoCo (CPU) | MJX-JAX | MuJoCo Warp / MJX-Warp | Newton | Isaac Lab 3.0 |
|---|---|---|---|---|---|
| Current version | 4.0.1 (2026-11-11) [R1][P1] | mujoco-mjx 4.0.1 [P2] | mujoco-warp 4.0.1 [P3] | 1.8.0 (2026-11-11) [P4] | v3.0.0 (20 Oct), targets Isaac Sim 6.2 [I1] |
| Runs on this Mac | **Yes, native arm64 wheels** [P1] | CPU only. Metal is broken (tested, §2) | CPU only, "for development and debugging" [W1] | "macOS (CPU only)" [N1][P4] | No macOS listed; Ubuntu, Linux aarch64, Windows 11 [I2] |
| GPU it needs | none | NVIDIA/AMD GPU or TPU [M1] | NVIDIA GPU [W1] | NVIDIA Turing+ (CC 7.5), driver R580+ [P4] | NVIDIA Turing+ (CC 7.5), driver ≥ 595.58 on Linux; headless Newton needs no RTX [I2] |
| Parallel worlds | One per thread; batched rollouts across cores [measured] | "thousands or tens of thousands", benchmarked at batch 8192 on A100 [M1] | `nworld` set at creation; examples use 4096–8192 [M1][G1][PG1] | Multi-world through MuJoCo Warp [N2] | 4096 is typical (mjlab, which uses the Isaac Lab API) [G1] |
| Published throughput | M3 Max and 64-core AMD used in MuJoCo's own benchmark [M1] | ~0.65–2.7M steps/s for one humanoid on A100 / TPU (figure not broken out per device) [M1] | Humanoid: 3.35M steps/s pure Warp, 2.96M through JAX (GPU not stated) [M1] | not stated | not stated |
| Model input | MJCF | MJCF | MJCF | URDF, MJCF, USD [N2] | USD natively; MJCF through importer or Newton [I1] |

### Notes per option

**MuJoCo on CPU**
- 4.0.0 (2026-11-06) is a major release with breaking changes. Tendon sidesite semantics changed, the RK4 integrator changed, `composite` and the `cable` plugin were removed, and the compiler is stricter. It also drops Python 3.10 [M2].
- The Python package is now split into `mujoco-core`, `mujoco-studio` and others [M2][P1].

**MJX**
- MJX now has two implementations. MJX-JAX runs on "Nvidia and AMD GPUs, Apple Silicon, and Google Cloud TPUs". MJX-Warp is NVIDIA-only and is not differentiable [M1].
- The "Apple Silicon" in that list does not survive testing; see §2.
- MJX-JAX has collision gaps. One example: cylinder against box or mesh is unsupported. Convex meshes should stay small, about 200 vertices or fewer [M1].

**MuJoCo Warp**
- It is maintained by Google DeepMind and NVIDIA, as part of Newton [W1].
- It requires an NVIDIA GPU for speed. CPU is for debugging only [W1].
- PLUGIN actuators and sensors, the PGS solver and the IMPLICITFAST midpoint integrator are not supported [W1].

**MuJoCo Playground**
- Version 1.1.0 is now built on MuJoCo Warp and PyTorch (with `rsl-rl-lib`), not on JAX [P5][PG1].
- Its paper reports humanoid locomotion training in "under 15 minutes" for Berkeley Humanoid. Unitree G1 and Booster T1 train in "under 30 minutes … on two RTX 4090" [PG2].

**mjlab**
- mjlab is the "Isaac Lab API, powered by MuJoCo-Warp". It ships a motion-imitation task for the Unitree G1 and uses 4096 environments in its examples.
- It "requires an NVIDIA GPU for training". macOS is supported for evaluation only [G1].

**Newton**
- Newton is a Linux Foundation project, started by Disney Research, Google DeepMind and NVIDIA. MuJoCo Warp is its "primary backend" [N1].
- It has other solvers too: XPBD, VBD, Featherstone, Kamino, MPM and Style3D [N2].
- Its `SolverMuJoCo` can use native CPU MuJoCo (`use_mujoco_cpu=True`), but only for a single world [N3].
- Newton 1.8.0 pins `mujoco~=3.17.0` and `mujoco-warp~=3.17.0` in its `sim` extra [P4]. It therefore lags the MuJoCo 4.0 release by one major version, along with that release's breaking changes.

**Isaac Lab 3.0**
- It "installs Newton by default", and "the standard installation runs without Isaac Sim". "Headless Newton simulation does not require RTX hardware" [I2].
- The Newton physics backend is selected with `physics=newton_mjwarp` [I1].
- It still includes humanoid AMP tasks: `Isaac-Humanoid-AMP-Dance/Run/Walk-Direct-v0` [I3].
- Isaac Sim, when you add it, needs Ubuntu or Windows and an RTX 4080-class GPU or better with 16 GB or more. "GPUs without RT Cores (A100, H100) are not supported" [I4].

## 2. Apple Silicon: what actually runs (measured on this machine)

Machine: M4 Max (14 CPU cores), 36 GB, macOS 15.5, Python 3.12, MuJoCo 4.0.1. The model is MuJoCo's reference `humanoid.xml`: 17 bodies, 27 DoF, 21 actuators, 5 ms timestep. Its size is close to our 15–20-part Simulation Body. The controls were random, so the humanoid falls and makes many contacts.

| Path | Result |
|---|---|
| MuJoCo CPU, Python `mj_step` loop, 1 thread | ~65,000 steps/s |
| MuJoCo CPU, `mujoco.rollout`, 1 / 10 / 14 threads (1024 rollouts × 200 steps) | ~80,000 / ~685,000 / **~794,000 steps/s** |
| MuJoCo Warp 4.0.1 on Warp CPU device (64 worlds) | ~16,000 steps/s. Warp reports "CUDA not enabled in this build" |
| MJX-JAX 4.0.1 on JAX 0.12.1 CPU (batch 1024) | ~10,000 steps/s |
| MJX-JAX on `jax-metal` 0.1.1 (Metal GPU) | **Fails.** Device auto-selection raises `Unsupported device: METAL:0`. Forcing `impl="jax"` on the Metal device fails with `UNIMPLEMENTED: default_memory_space is not supported` |

Why the Metal path is dead:
- `jax-metal`'s latest release is 0.1.1, from 2024-10-08 [P6].
- Apple calls the plug-in "experimental", and it lacks float64 [A1].
- JAX's own install page says "JAX is not supported on Mac/OSX GPU; instead use the standard CPU installation commands" [J1].
- Current JAX is 0.12.1 [P7].

On this Mac, batched CPU MuJoCo is roughly 50–80× faster than MuJoCo Warp or MJX on CPU. **The Mac pipeline should therefore be native MuJoCo with multithreaded rollouts, not a GPU framework running in CPU mode.**

These figures measure physics only. Training also spends time on the policy network and on PPO updates. Read 0.8M steps/s as a ceiling, not a training speed.

## 3. Portability

### Simulation Body

MJCF is the format all of these stacks share.

- **MuJoCo, MJX, MuJoCo Warp, mjlab, Playground:** they read the same MJCF file directly [M1][W1][G1].
- **Newton:** `add_mjcf` maps hinge, slide and ball joints, spring and damping, `condim` friction, collision masks and `<general>` actuators [N3].
  - It does **not** import sensors, keyframes, composite or flex elements, plugins, cameras or lights [N3].
  - Non-convex collision meshes are convex-hulled [N3].
  - A Simulation Body made of primitive capsules and boxes, with hinge or ball joints, transfers cleanly.
- **Isaac Lab:** loads MJCF through Newton, or converts it to USD with the Isaac Sim MJCF importer (an MJCF spawner arrived in v2.3.2) [I1].
- **Version drift is the practical risk.** The breaking changes in MuJoCo 4.0 (§1) mean one MJCF file can behave differently in Newton 1.8, which pins 3.17, and in MuJoCo 4.0.1 [M2][P4]. Pin one MuJoCo version across Mac and cloud.

### Trained controller

The controller is a neural network, usually PyTorch, which can be exported to ONNX. It maps observations to joint targets. It runs in another simulator only if these match exactly:

- the observation vector: joint order, frames and normalisation
- the action meaning: PD targets and their scale
- the control rate
- the actuator gains

When those match, the remaining difference is contact and solver behaviour.

- **Within the MuJoCo-Warp family, the gap should be small.** That family is MuJoCo, MJX-Warp, mjlab, Playground, Newton's `SolverMuJoCo` and Isaac Lab on `newton_mjwarp`. MuJoCo Warp is built to reproduce MuJoCo [W1][N1]. This is inferred from the shared solver and was not measured here.
- **Moving to Isaac Lab on PhysX, or to a non-MuJoCo Newton solver, changes the engine.** Plan for a sim-to-sim check. BeyondMimic, for example, validated its tracking policies by sim-to-sim transfer into MuJoCo [B1].
- A policy trained on GPU runs on the Mac's CPU MuJoCo for playback and rendering. mjlab supports exactly this, with evaluation on macOS [G1].

## 4. Cloud GPU prices (checked 2026-11-26, on-demand, per GPU-hour)

| GPU | RunPod Secure / Community [C1] | Lambda 1× [C2] | Vast.ai marketplace, min / median of live offers [C3] |
|---|---|---|---|
| RTX 4090 24 GB | $0.89 / $0.34 | — | $0.30 / $0.46 (6 offers) |
| RTX 5090 32 GB | $1.39 / $0.69 | — | $0.21 / $0.62 (7 offers) |
| L40S 48 GB | $1.09 / $0.79 | — | $0.80 (1 offer) |
| RTX A6000 48 GB | $0.69 / $0.33 | $1.09 | — |
| A100 80 GB (SXM) | $2.19 / $1.39 | $1.99 (40 GB) | $0.40 / $0.53 (2 offers) |
| H100 SXM 80 GB | $4.39 / $2.69 | $4.89 | — |
| RTX PRO 6000 96 GB | $2.69 / $1.69 | — | $1.47 / $1.58 (3 offers) |

- RunPod bills per second, and its storage costs $0.07–0.20 per GB-month [C1].
- Lambda prices exclude tax [C2].
- Vast.ai prices are "set by supply and demand" [C3]. The numbers above are a small snapshot from its public offers API on the check date, not a price list.

All of these GPUs are Turing or newer and meet the CC 7.5 floor that MuJoCo Warp, Newton and Isaac Lab require. For headless training, consumer RTX cards (4090, 5090) are the cheapest fit. Only Isaac Sim's renderer would rule out the A100 and H100 [I4].

### Plausible training-run cost (estimate)

Published anchors:

- Playground's G1 locomotion policy took under 30 minutes on 2× RTX 4090, or **about 1 GPU-hour** [PG2]. That costs about $0.35–0.90 on a RunPod 4090, or about $0.45 on Vast.ai.
- BeyondMimic's motion-tracking PPO uses 24 steps per environment per iteration. Easy motions converge in 2k–4k iterations, and hard ones take up to 30k [B1].
- With the 4096 environments typical of mjlab and Isaac Lab [G1], that works out to about **0.2–0.4 billion** environment steps for an easy single motion. Hard motions take up to **about 3 billion**. The 4096 figure is an assumption, because BeyondMimic does not state its environment count.

| Scenario | Env steps | Single RTX 4090-class GPU (assumed 50k–200k env steps/s end to end) | Cost at $0.34–0.89/h |
|---|---|---|---|
| Easy single motion (walk, simple gesture) | ~0.3 B | ~0.4–1.7 h | ~$0.15–1.50 |
| Hard single motion (full dance) | ~3 B | ~4–17 h | ~$1.40–15 |
| Movement Repertoire (one policy, many clips) | several B | ~1–2 days | ~$10–45 |

The Mac comparison is also an estimate:
- At 50 Hz control with a 5 ms physics step, the physics ceiling is about 200k control steps/s (§2).
- With network inference and PPO updates added, 50k–100k steps/s is a guess, not a measurement.
- At that speed, an easy motion takes about 1–2 h and a hard dance about 8–17 h, which is overnight.
- The throughput assumptions in this section are not measured. A short benchmark on the Mac and on one rented 4090 would replace them, and it belongs to ticket #14.

## Could not determine

- MJX-Warp's published 3.35M steps/s figure does not say which GPU it ran on [M1].
- No primary source gives end-to-end RL training throughput (physics plus PPO) for a ~17-body humanoid tracking task on a named GPU. The figures in §4 are assumptions.
- No measured sim-to-sim gap between MuJoCo CPU and MuJoCo Warp, or between MuJoCo and Isaac Lab PhysX, was found for our kind of body.
- Whether Isaac Lab 3.0's AMP humanoid tasks run on the Newton backend or need PhysX was not established from the docs.
- Vast.ai prices are a small live sample and move daily. AWS, GCP and Azure prices were not checked.

## Sources

Accessed 2026-11-26.

- [R1] MuJoCo releases — https://github.com/google-deepmind/mujoco/releases
- [M1] MJX documentation — https://mujoco.readthedocs.io/en/latest/mjx.html
- [M2] MuJoCo changelog (4.0.0, 4.0.1) — https://mujoco.readthedocs.io/en/latest/changelog.html
- [W1] MuJoCo Warp README — https://github.com/google-deepmind/mujoco_warp
- [N1] Newton README — https://github.com/newton-physics/newton
- [N2] Newton overview — https://newton-physics.github.io/newton/latest/guide/overview.html
- [N3] Newton MuJoCo solver guide — https://newton-physics.github.io/newton/latest/solvers/mujoco.html
- [I1] Isaac Lab releases (v3.0.0, v3.0.0-EA, v2.3.2) — https://github.com/isaac-sim/IsaacLab/releases
- [I2] Isaac Lab installation — https://isaac-sim.github.io/IsaacLab/main/source/isaaclab/installation.html
- [I3] Isaac Lab tasks changelog — https://github.com/isaac-sim/IsaacLab/blob/main/source/isaaclab_tasks/docs/CHANGELOG.rst
- [I4] Isaac Sim system requirements — https://docs.isaacsim.omniverse.nvidia.com/latest/installation/requirements.html
- [G1] mjlab README — https://github.com/mujocolab/mjlab
- [PG1] MuJoCo Playground README — https://github.com/google-deepmind/mujoco_playground
- [PG2] MuJoCo Playground paper — https://arxiv.org/html/2502.08844
- [B1] BeyondMimic paper — https://arxiv.org/html/2508.08241
- [A1] Apple, Accelerated JAX on Mac — https://developer.apple.com/metal/jax/
- [J1] JAX installation — https://docs.jax.dev/en/latest/installation.html
- [P1–P7] PyPI JSON metadata for `mujoco` / `mujoco-core`, `mujoco-mjx`, `mujoco-warp`, `newton`, `playground`, `jax-metal`, `jax` — https://pypi.org/pypi/<package>/json
- [C1] RunPod pricing — https://www.runpod.io/pricing
- [C2] Lambda pricing — https://lambda.com/pricing
- [C3] Vast.ai pricing, https://vast.ai/pricing, and public offers API, https://console.vast.ai/api/v0/bundles/
- [measured] Local benchmarks: scripts run in a scratch venv with `mujoco==4.0.1`, `mujoco-warp==4.0.1`, `mujoco-mjx==4.0.1`, `jax==0.12.1`, `jax-metal==0.1.1`, on MuJoCo's `model/humanoid/humanoid.xml`
