# What Isaac Lab and Isaac Sim can do for her on the RTX 5090 PC

Research for issue #23, a child of the map (#1). Every source was checked on **2026-11-26**. This area changes weekly, so check again before you rely on a version number.

The PC: Windows desktop, RTX 5090, Intel Core Ultra 9 285K, 64 GB RAM, assumed Windows 11, reachable from the Mac over the home network. No NVIDIA hardware was available for this research. Nothing here was measured. Each statement carries a tag:

- **[D] documented**: a primary source says it.
- **[I] inferred**: it follows from documented facts but no source says it outright.
- **[U] unknown**: the sources do not settle it.

This builds on two earlier write-ups, `docs/research/simulator-and-training-hardware.md` (branch `research/simulator-and-hardware`) and `docs/research/reference-motion-tracking.md` (branch `research/reference-motion-tracking`). Several of their version numbers have moved since. The corrections are listed in §7.

## Answer in brief

- **Use Isaac Lab's Newton engine (`physics=newton_mjwarp`), not PhysX.** Newton runs MuJoCo's own physics on the GPU. Isaac Lab now ships a built-in task that trains a humanoid to follow one Reference Motion, adapted from BeyondMimic, and that task runs only on Newton. Policies trained with that task have already been played back in ordinary CPU MuJoCo, including on a Mac.
- **The PhysX route has three costs here.** It is a different physics engine from the Mac's, which adds a sim-to-sim gap. It requires the full Isaac Sim install. And Isaac Lab's MJCF importer has a known fault on the PhysX side: it merges several joints between the same two parts into one and loses MuJoCo's spring settings. Her soft springy joints are exactly what that fault breaks.
- **Operating system: Windows 11 natively is documented to work.** Isaac Lab 3.0 lists Windows 11 as a supported platform and gives Windows commands for Newton, standalone PhysX and Isaac Sim. Isaac Sim also supports Windows 11. Ubuntu installed alongside Windows (22.04 or 24.04) is the other documented option, and the only one that runs the Linux-only tools (mjlab, ProtoMotions' Isaac Lab path, Docker images). WSL2 is not mentioned by Isaac Lab, and NVIDIA staff have said Isaac Sim is not supported under WSL2.
- **The RTX 5090 is not named in any Isaac document.** Isaac Sim lists the RTX 5080 (same Blackwell generation) as its "Good" GPU and the RTX PRO 6000 Blackwell as "Ideal". Required drivers: 595.97 or newer on Windows, 595.58.03 or newer on Linux.
- **Her body gets into Isaac Lab one way only: MJCF → USD.** For either engine, Isaac Lab converts the MJCF with the `mujoco-usd-converter`, a library that is still alpha. On the way it does not convert ellipsoids, `contype`/`conaffinity` collision filtering, `<contact><pair>` overrides, sensors or keyframes. Outside Isaac Lab, standalone Newton (used by MimicKit and ProtoMotions) reads MJCF directly with `add_mjcf`.
- **The MuJoCo version mismatch is real and changes weekly.** Isaac Lab 3.0.0 (the release) pins Newton 1.6.1, which pins **MuJoCo 3.12**. Isaac Lab's development branch pins a Newton revision still on **MuJoCo 3.17**. Newton's own development branch moved to **MuJoCo 4.0.1**, the Mac's version, on 19 Nov 2026, but no Newton release and no Isaac Lab version includes that change yet. Until one does, either the Mac runs the Newton-matched MuJoCo for her Measured Checks (3.12 and 3.17 both have macOS arm64 wheels), or someone overrides Isaac Lab's Newton pin (untested).
- **For her simple body, few MuJoCo 4.0 changes matter.** Two could change her behaviour. Force-limited actuators no longer add implicit damping under `implicitfast`, and MuJoCo itself says light models without armature may need armature or a smaller timestep; she weighs 25.5 kg. Contact pairs without their own `solref` now blend the two geoms' values. RK4 ball-joint changes matter only if she uses RK4.
- **Isaac Sim adds little that this project needs.** Isaac Lab without Isaac Sim already has a desktop viewer (Newton GL), a browser viewer (Viser, viewable from the Mac across the network) and headless video recording. Isaac Sim adds Isaac Sim PhysX, the Kit editor and its RTX renderer. Its minimum is 32 GB RAM and a 50 GB SSD, and it does not run under WSL2.

**Most important finding for the engine choice:** Isaac Lab's built-in motion-tracking task `Isaac-Motion-Tracking-G1` trains only on Newton with MuJoCo Warp. A third party has played policies trained with it back in plain CPU MuJoCo on macOS: six of the six clips that succeeded in training also finished the clip in MuJoCo. No comparable evidence exists for PhysX-trained policies with a custom MJCF body, and the PhysX import path is known to lose MuJoCo joint springs.

## 1. Installing on that PC

| Setup | Isaac Lab 3.0 (no Isaac Sim) | Isaac Sim 6.2 | Notes |
|---|---|---|---|
| **Windows 11, native** | **Supported** [D][IL-install]. The Windows tab gives commands for `physics=newton_mjwarp`, `physics=ovphysx` and `physics=isaacsim_physx` [D][IL-install-rst]. | **Supported** [D][IS-req]. "Windows 10 is not supported" [D][IS-req]. | Enable Windows long-path support before cloning [D][IL-install]. The 3.0.0 release notes list stabilisation work on "Windows wheel installation and Newton CUDA graph initialization" [D][IL-rel300]. |
| **Ubuntu alongside Windows** | **Supported**: "Ubuntu 22.04+ on x86_64" [D][IL-install]. | **Supported** on 22.04 and 24.04. 22.04 "is deprecated and will be removed" [D][IS-req]. | The only option that also runs the Linux-only stacks: mjlab (Linux x86_64 and macOS only [D][MJL-pyproject]), ProtoMotions' Isaac Lab backend ("Linux x86_64" [D][PM-install]) and the Isaac Lab Docker images [D][IL-install-rst]. |
| **WSL2** | **Not mentioned** by Isaac Lab's docs [U]. CUDA itself works in WSL2 on GeForce GPUs, but "OpenGL-CUDA interoperability is not yet supported" [D][CUDA-WSL]. Headless Newton training may well work [I], but nobody documents it. | **Not supported.** An NVIDIA staff reply (31 Oct 2025): "Isaac Sim containers are currently not supported under WSL2", because WSL2 lacks the GPU and rendering support Isaac Sim needs [D, forum][NV-forum-wsl]. Isaac Sim's own requirements page says nothing about WSL2 [D][IS-req]. | Least documented of the three. |

**GPU and driver.**
- Isaac Lab needs "a CUDA-capable NVIDIA GPU … Turing or newer (compute capability 7.5+)" [D][IL-install]. The 5090 meets that [I].
- Driver minimums: "`595.58.03` on Linux x86_64 … `595.97` on Windows x86_64". These come from the PyTorch CUDA 13.0 build in the default environment, not from Warp [D][IL-install-rst].
- Isaac Sim's GPU table:
  - Minimum: GeForce RTX 4080 (16 GB).
  - Good: GeForce RTX 5080 (16 GB).
  - Ideal: RTX PRO 6000 Blackwell (48 GB).

  Tested drivers are 595.58.03 on Linux and 595.97 on Windows [D][IS-req].
- **The RTX 5090 is not named anywhere** in Isaac Lab's or Isaac Sim's requirements [D, by absence]. It is the same Blackwell generation as the listed 5080 and RTX PRO 6000 and has 32 GB, so it should be supported [I]. Neither page lists a Blackwell-specific known issue [D][IS-req][IL-issues].

**Newton on Windows.**
- Newton itself supports "Linux (x86-64, aarch64), Windows (x86-64), or macOS (CPU only)" [D][N-readme].
- Newton's MuJoCo dependencies are excluded only on Windows ARM64 [D][N-pyproject].
- Isaac Lab's Windows install commands use Newton as the default engine [D][IL-install-rst].
- Conclusion: Newton inside Isaac Lab is documented for Windows x86-64, not Linux only.

**Known Windows issue.** With `physics=isaacsim_physx`, stop a run with Ctrl+Break, not Ctrl+C [D][IL-issues].

## 2. Engines in Isaac Lab 3.0

Isaac Lab 3.0.0 was released 2026-10-20. It targets "Isaac Sim 6.2, Python 3.12, PyTorch 2.11 with CUDA 13.0, NVIDIA Warp 1.17, Newton 1.6.1, and RSL-RL 5.5.1" [D][IL-rel300]. It offers three physics backends [D][IL-backends]:

| Backend | Selector | Needs Isaac Sim | Maturity as documented | Asset input |
|---|---|---|---|---|
| **Newton**, MuJoCo Warp solver | `physics=newton_mjwarp` (default install) | No | MJWarp is the "primary validated solver path" [D][IL-newton]. Other Newton solvers carry labels: Kamino "experimental" [D][IL-rel300], Steel "Experimental" [D][IL-newton]. The beta's warning "Newton backend is in active development — Not all environments have Newton presets yet" is not repeated in the 3.0.0 notes [D][IL-releases]. | USD (Isaac Lab spawns MJCF and URDF through USD converters) |
| **OVPhysX** (standalone PhysX library) | `physics=ovphysx`, `--extra ovphysx` | No | No experimental label. It has listed limits: deformables, legacy `PhysxJointAPI` no longer consumed, and identical layouts required for heterogeneous cloning [D][IL-ovphysx]. Supported tasks include `Isaac-Humanoid-Direct` and G1/H1 velocity tasks [D][IL-ovphysx]. | USD |
| **Isaac Sim PhysX** (Kit) | `physics=isaacsim_physx`, `--extra isaacsim` | **Yes** | Described as "the complete path when a workflow needs the full PhysX/RTX stack, ROS bridge, XR, livestreaming, or Kit tooling" [D][IL-rel300]. | USD |

**Which shipped tasks run on which engine.** Each task declares the presets it accepts, and `isaaclab train … --help` lists them [D][IL-backends]. The two tasks that matter here, read from source:

- **`Isaac-Humanoid-AMP-Dance/Run/Walk-Direct`** (`contrib/humanoid_amp`) hard-codes `physics=PhysxCfg(...)` with no Newton preset [D][IL-amp-cfg]. On `main`, `PhysxCfg` is the Isaac Sim PhysX config [D][IL-backends]. These tasks therefore need PhysX and, on `main`, Isaac Sim [I]. This resolves the open question in the earlier write-up. The AMP tasks are also the wrong method for stage 1, as the tracking write-up established.
- **`Isaac-Motion-Tracking-G1`** (`core/motion_tracking`) hard-codes `NewtonCfg(solver_cfg=MJWarpSolverCfg(... integrator="implicitfast" ...))`, with 50 Hz policy and 200 Hz physics [D][IL-mt-cfg][IL-mt-doc]. **Newton only.** See §4.

**Features that differ between engines.**
- Friction and contact models differ. PhysX uses patch-based friction, MJWarp uses MuJoCo's pyramidal or elliptic cone. "PhysX patch friction and MJWarp contact friction are not numerically interchangeable" [D][IL-solverdiff][IL-prep-newton].
- MJWarp does not enforce `actuator_velocity_limit` and drops `joint_velocity_limit` [D][IL-prep-newton].
- The renderers, visualizers and video recording that need no Isaac Sim all work with Newton (§6).

## 3. Bringing her MJCF body in

### Inside Isaac Lab, for both engines: MJCF → USD

- Isaac Lab's `MjcfFileCfg` spawner and `scripts/tools/convert_mjcf.py` both call `MjcfConverter` [D][IL-mjcf-conv].
- `MjcfConverter` wraps Isaac Sim's MJCF importer. Since Isaac Sim 5.0 that importer uses the `mujoco-usd-converter` library [D][IL-mjcf-conv].
- Conversion does not need Isaac Sim. It can run from the standalone `isaacsim-asset-isolated` wheel through the `importers` extra [D][IL-import][IL-mjcf-conv].
- With `run_multi_physics_conversion` on (the default), the USD carries a neutral base layer plus a PhysX overlay. "The MuJoCo/Newton variants still see the original per-DOF joints." The importer warns that "policies trained on one variant may not transfer directly to the other" [D][IS-mjcf].
- **Isaac Lab has no documented path that hands an MJCF straight to Newton's `add_mjcf`** [D, from source: `MjcfFileCfg` always converts to USD].

What the converter documents as lost or changed. `mujoco-usd-converter` 0.10.0, Apache-2.0, describes itself as "currently an Alpha product" [D][MUC-readme][MUC-changelog]. Its known limitations [D][MUC-changelog]:

- Not converted:
  - ellipsoid geoms
  - height fields
  - SDFs
  - collision filtering via `contype` and `conaffinity`
  - collision overrides via `<contact><pair>`
  - keyframes, sensors, cameras, lights, plugins
- `default` and `class` inheritance is baked into each element. The values are preserved.
- MuJoCo 4.0's `springyield` gives a warning and is not supported.
- Joint stiffness and damping are authored only from the linear term of MuJoCo's polynomial spring profile.
- Ball joints become `UsdPhysics.SphericalJoint` with cone-angle limits. `MjcJointAPI` carries armature, damping, friction loss and spring-damper values.
- Friction is authored as both static and dynamic from `geom/friction[0]`. Torsional and rolling friction go to `MjcMaterialAPI`. Contact `solref` becomes `newton:contactStiffness/Damping`. Joint-limit `solreflimit` becomes limit stiffness and damping.

What this means for her body [I]:

- Her ~19 capsules, spheres and boxes with hinge and ball joints are in the supported set.
- Ellipsoid geoms would be dropped. So would any reliance on `contype`/`conaffinity` or `<pair>` to choose which of her parts may touch. If her MJCF uses these, it would need an alternative inside Isaac Lab.

### PhysX side: a known fault that hits soft springy joints

- Isaac Sim's MJCF importer documents its PhysX limits [D][IS-mjcf]:
  - Drive stiffness and damping come only from actuator `gainprm`/`biasprm`. Only "fixed" gain and "affine" bias types are supported; otherwise "the physics drive stiffness and damping will not be created."
  - "MJCF uses min/max while PhysX uses maxForce", so asymmetric force ranges differ.
  - Several single-axis joints between the same two bodies are folded into one PhysX D6 joint. Duplicate-axis joints are dropped.
  - Off-axis joint directions are snapped to X, Y or Z and "can collide on the same token and lose a DOF."
- The page does not mention ball joints, joint `stiffness`/`springref`, `solref`/`solimp`, `condim` or sensors [D, by absence].
- **ProtoMotions documents the consequence.** "The IsaacLab 3 converter currently collapses multiple single-axis MJCF joints between the same bodies into a PhysX D6 joint." ProtoMotions ships a patch that "preserves the shared source frame, restores MuJoCo spring gains, and locks unused D6 axes" until upstream fixes it [D][PM-migration][PM-d6].
- Implication [I]: on PhysX, her soft springy joints are at risk of losing their spring settings unless patched like this. That holds whether a joint is written as three hinges or as a ball.

### Newton side

- Newton parses the converted USD's MuJoCo/Newton attributes [D][IL-prep-newton].
- The Isaac Lab guide warns that a property present in an asset "does not prove MJWarp uses it" [D][IL-prep-newton].
- [U]: whether every MuJoCo joint-spring attribute (`stiffness`, `springref`) survives MJCF → USD → Newton exactly. No source states this end to end.

### Outside Isaac Lab: standalone Newton `add_mjcf`

MimicKit's Newton engine and ProtoMotions' Newton backend use this route [D][MK-newton][PM-custom]. Per Newton's MuJoCo solver guide [D][N-mujoco]:

- **Mapped:**
  - joint `damping` → `joint_damping`, `stiffness` → `joint_stiffness`
  - `springref` → rest position
  - armature
  - `condim` 1/3/4/6
  - margin and gap with MuJoCo 3.9+ semantics
  - `contype`/`conaffinity` resolved
  - tendons
  - `<option><flag>`
- Hinge and slide joints on one body are combined into one Newton joint.
- **Dropped:** sensors, cameras, lights, keyframes, composite and flex, skins, plugins, user data.
- The guide does not describe how `solref`, `solimp` and geom `priority` are imported [D, by absence].

## 4. Motion tracking on Isaac Lab 3.0 today

| Implementation | Engine it uses | Custom body | Clips | Licence | Last activity | Notes |
|---|---|---|---|---|---|---|
| **Isaac Lab built-in `Isaac-Motion-Tracking-G1`** | **Newton / MuJoCo Warp only** [D][IL-mt-cfg] | The task is G1-specific. The robot, motor gains and tracked links live in `config/g1/env_cfg.py` [D][IL-mt-doc]. A new body means a new config: the body through `MjcfFileCfg`, plus its own gains and link list [I]. | **One clip per run** [D][IL-mt-doc] | BSD-3-Clause (Isaac Lab). Adapted from HybridRobotics/whole_body_tracking (MIT) and isaac-spinning-up [D][IL-mt-license] | Added 2026-11-18. RSL-RL "SuperMimic" variant added 2026-11-25 [D][IL-mt-commits] | **On `main` only, not in the v3.0.0 release** (absent from the tag) [D]. Default budget is 30,000 PPO iterations × 24 steps with adaptive sampling, as in BeyondMimic [D][IL-mt-doc]. Plays back with `--viz newton_gl` and records headless video [D][IL-mt-doc]. |
| Isaac Lab built-in `Isaac-Humanoid-AMP-*` | Isaac Sim PhysX only [D][IL-amp-cfg] | Built for the stock 28-DoF humanoid USD [D][IL-amp-cfg] | Dataset (AMP) | BSD-3-Clause | in v3.0.0 | AMP does not hold her to one clip, so it is wrong for stage 1 (earlier write-up). |
| **MimicKit** (xbpeng) | Its "Isaac Lab" engine uses **Isaac Sim PhysX** (`AppLauncher`, `PhysxCfg`) [D][MK-islab]. Its separate "Newton" engine uses **standalone Newton `SolverMuJoCo`**, not Isaac Lab [D][MK-newton]. | Yes. Bodies are MJCF `.xml`. The Newton engine calls `add_mjcf` on the `.xml`; the Isaac Lab engine loads a `.usd` with the same name, which you convert yourself [D][MK-islab][MK-newton] | Single clip **or a dataset** via `motion_file` [D][MK-readme] | Apache-2.0 | pushed 2026-11-18 | Tested with Isaac Lab **v3.0.0-EA** and Newton **v1.6.1** [D][MK-readme]. Methods: DeepMimic, AMP, ASE, ADD and others. Its sample humanoid writes each ball-like joint as three hinges with joint `stiffness`/`damping` [D][MK-xml]. |
| **ProtoMotions** (NVlabs) | IsaacLab backend uses **PhysX** (`PhysxCfg`) [D][PM-sim]. Separate Newton backend is pinned to **Newton 1.0.0 / MuJoCo 3.5.0** [D][PM-pyproject] | Yes. "MJCF is the source of truth"; its Isaac Lab path converts MJCF to USD automatically and patches the D6 spring fault [D][PM-custom][PM-migration] | Many clips (general tracker, MaskedMimic) | Apache-2.0 code | pushed 2026-11-10 | Isaac Lab pinned to a **2026-07-16 development commit**, not 3.0.0. Isaac Lab path "Linux x86_64" [D][PM-migration][PM-install]. MuJoCo backend pinned `mujoco>=3.0,<4`, so it excludes the Mac's 4.0.1 [D][PM-pyproject]. |
| **BeyondMimic successor: mjlab** | Not Isaac Lab. "Isaac Lab API, powered by MuJoCo-Warp" [D][MJL-pyproject] | Yes (MJCF native) | One clip per policy (earlier write-up) | Apache-2.0 | pushed 2026-11-26 | `HybridRobotics/whole_body_tracking` is archived: "BeyondMimic motion tracking lives on in mjlab" [D][WBT]. PyPI 1.6.1 pins `mujoco~=3.11.0`. `main` pins `mujoco-core~=4.0.1` since 2026-11-12 [D][MJL-pypi][MJL-pyproject]. Platforms: macOS arm64 and Linux x86_64 only, so **no Windows** [D][MJL-pyproject]. |

Summary [I]:

- **Newton route:** the only maintained tracking code that trains on Isaac Lab 3.x with Newton is Isaac Lab's own `Isaac-Motion-Tracking-G1`, on `main`.
- **PhysX route:** MimicKit and ProtoMotions both train on Isaac Lab with PhysX. ProtoMotions does so on a pre-3.0.0 commit.
- **Many clips:** MimicKit and ProtoMotions handle multi-clip datasets today. The Isaac Lab built-in task is one clip per run.

## 5. Back to the Mac

**What must match.** Isaac Lab's transfer guide [D][IL-transfer]:

- "The checkpoint maps ordered observations to actions; it does not include the physics engine."
- Observation and action terms must match: "Term order, ordered joint or body names, width, target type, scale, offset, and clipping."
- Physics `dt`, decimation and action hold must match.
- Joint and body ordering can differ between PhysX and MJWarp on branched robots, and setting only `joint_ordering` "silently leaves bodies in backend order."
- "Expect similar behavior, not identical trajectories."
- For the Mac: the same applies to CPU MuJoCo, including the gains (here implicit PD at 200 Hz, `implicitfast`, policy at 50 Hz) [I].

**Published evidence of an Isaac Lab policy running in CPU MuJoCo.**

- **Newton-trained, motion tracking (closest to this project).**
  - Source: `g1_deploy`, the third-party repo that Isaac Lab's motion-tracking doc links for deployment [D][IL-mt-doc]. It packages seven `Isaac-Motion-Tracking-G1` policies, "trained with Newton MJWarp", and plays them in MuJoCo, on macOS through `mjpython … --viz` [D][G1D-readme].
  - Result: six of seven clips completed all 32 Newton evaluation trials. All six "reached clip end" in one deterministic CPU-MuJoCo play each, with 2 ms physics and 50 Hz control, using Unitree's MJCF, "a different asset from the training USD". The seventh failed in Newton too [D][G1D-mimic].
  - Caveats stated by the authors: "Reaching the clip end does not establish tracking accuracy." `g1_deploy` declares no licence. Its MuJoCo version is unpinned (`mujoco>=3.1`) [D][G1D-mimic][G1D-pyproject].
- **Newton- and PhysX-trained, locomotion.** The same repo measured a 45-episode MuJoCo hold suite. When MuJoCo's leg geometry matched the training asset, success was 97.8% with 100% standing. With the current, 6 cm taller geometry it fell to 75.6% with 0% standing [D][G1D-readme].
  - Lesson [I]: an exact body match matters more than the engine for transfer. Her Mac MJCF and the USD Isaac Lab trains on must describe the same body.
- **PhysX-trained, tracking.** BeyondMimic (trained on Isaac Lab 2.1 / Isaac Sim 4.5 [D][WBT]) "compared success rates in sim-to-sim transfer using MuJoCo" for a cartwheel. The guided-diffusion model reached 95% success against 5% for the baseline [D][BM].
- No source measures a tracking-error gap between Isaac Lab (either engine) and CPU MuJoCo for a custom, non-robot humanoid [U].

**MuJoCo version: can Isaac Lab's Newton match the Mac's 4.0.1?**

| What | Pins | Source |
|---|---|---|
| Mac | MuJoCo 4.0.1 (released 2026-11-11) | [P-mujoco] |
| Isaac Lab **v3.0.0** (release) | `newton[sim]==1.6.1` → `mujoco~=3.12.0`, `mujoco-warp~=3.12.0` | [IL-pyproject-300][P-newton161] |
| Isaac Lab **main** (2026-11-26) | Newton git revision `d31603ff` (2026-11-17, "1.9.0.dev0") → `mujoco~=3.17.0`, `mujoco-warp~=3.17.0` | [IL-pyproject-main][N-pyproject-d316] |
| Newton **1.8.0** (latest PyPI release, 2026-11-11) | `mujoco~=3.17.0` | [P-newton180] |
| Newton **main** | `mujoco-core~=4.0.1`, `mujoco-warp~=4.0.1`, since PR #5337 merged 2026-11-19 | [N-pyproject-main][N-pr5337] |

- **Documented:** no released Newton, and no Isaac Lab release or `main`, runs MuJoCo 4.0 today.
- **Inferred:**
  - The next Newton release will carry 4.0.1, and Isaac Lab will follow when it bumps its pin. Neither date is announced [U].
  - Until then there are two options:
    - Override Isaac Lab's Newton pin to a Newton revision after 2026-11-19. This is untested and may break Isaac Lab, since PR #5337 changed Newton's solver code.
    - Run the Mac's Measured Checks of a 5090-trained Controller on the matching MuJoCo, 3.12 or 3.17. Both have macOS arm64 Python 3.12 wheels [D][P-mujoco].
  - Newton main's switch also changes how actuator damping and armature are applied in MuJoCo Warp ("now applies actuator armature … at runtime") [D][N-pr5337]. A Controller trained before and after that bump may behave differently even for the same MJCF [I].

**MuJoCo 4.0 breaking changes, applied to a primitive-shape body with hinge and ball joints** [D][MJ-changelog], with relevance [I]:

| Change | Affects her? |
|---|---|
| 4.0.0: "Actuators saturated by joint or tendon actuator force limits … no longer contribute implicit actuator derivatives, changing integration under `implicit`, `implicitfast`, and `discrete`." Light links without armature "may need joint armature or a smaller timestep." | **Possibly.** Isaac Lab's tracking task uses `implicitfast` [D][IL-mt-cfg]. She is light (25.5 kg) with soft joints. Set armature and test. |
| 4.0.0: contact pairs with undefined `solref` "now mix the `solref` of their geoms … using `solmix`", where previously they took "the element-wise minimum". | **Only** if she uses `<pair>` without `solref` and her geoms have different `solref`. |
| 4.0.0: RK4 "fourth-order accurate for the orientations of ball and free joints". | Only if she uses `integrator="RK4"`. |
| 4.0.0: new `springyield` elasto-plasticity. | No, unless used. The USD converter does not support it [D][MUC-changelog]. |
| 4.0.0: stricter compiler (duplicate includes rejected, invalid models rejected); `composite` and `cable` plugin removed; Python 3.10 dropped; package split into `mujoco-core` / `mujoco-studio` / `mujoco`. | Load-time and install issues only. |
| 3.17.0: position-actuator damping from `dampratio` "resolved only at compile time, not by `mj_setConst`". | Only if gains are edited at runtime. |

## 6. Isaac Sim: what it adds and what it costs

**What runs without Isaac Sim** [D]:

- **Viewers** [IL-viz]:
  - Newton GL window ("Lightweight, strong feature support … Recommended").
  - Viser, which "streams the Newton Warp renderer to a local web server". The Mac could watch training on the PC in a browser [I].
- **Video** [IL-video]: "With no `--viz`, `--video` records from a headless Newton visualizer."
- **Renderers** [IL-render]: Newton Warp, OptiX (Windows x64 and Linux) and OVRTX (RTX, kit-less, "the recommended RTX renderer") all run without Isaac Sim.
- **PhysX without Kit** [IL-ovphysx]: OVPhysX.

**What only Isaac Sim adds** [D][IL-rel300][IL-render][IL-viz]:

- Isaac Sim PhysX, which the AMP tasks, MimicKit's Isaac Lab engine and ProtoMotions' Isaac Lab backend use.
- Isaac RTX rendering ("legacy … only when the workflow must run in an Isaac Sim process").
- The Kit editor GUI (deprecated as a visualizer, "slated for removal in 3.2").
- ROS bridge, XR and livestreaming.

For this project, the video is made in Blender on the Mac and the checks run in MuJoCo on the Mac. Isaac Sim's renderer therefore adds nothing that is needed, beyond what the Newton viewers already give for looking at her during training [I].

**What it costs** [D][IS-req][IL-install-rst]:

- 32 GB RAM minimum (64 GB "good"), 16 GB VRAM minimum, 50 GB SSD minimum (500 GB "good").
- Windows 11 or Ubuntu 22.04/24.04 only. Not WSL2 (forum, above).
- RT-core GPUs only: "GPUs without RT Cores (A100, H100) are not supported".
- Isaac Sim 6.2 "pins dependencies that conflict with Isaac Lab", so Isaac Lab's docs use overrides.
- "The first launch downloads Isaac Sim extensions and can take more than ten minutes."
- The PC (64 GB RAM, 32 GB VRAM) meets these [I].

## 7. Corrections to the earlier write-ups

- **Version pin.** "Isaac Lab 3.0's Newton pins MuJoCo 3.17" was based on Newton 1.8.0. Isaac Lab 3.0.0 actually pins Newton **1.6.1**, which pins **MuJoCo 3.12**. Only Isaac Lab `main` is on 3.17. Newton `main` is now on 4.0.1.
- **mjlab pin.** mjlab 1.6.1 on PyPI pins 3.11, but mjlab `main` is on MuJoCo 4.0.1.
- **Newton's MJCF route.** "Isaac Lab reads MJCF through Newton" is not quite right. Isaac Lab always converts MJCF to USD first, for Newton as well. Only standalone Newton reads MJCF directly.
- **AMP tasks.** The open question about them is resolved: they need PhysX.

## Could not determine

- Whether Isaac Lab 3.0 trains correctly on an **RTX 5090** specifically. No Isaac document names the 5090, and nothing could be run here.
- Whether **headless Isaac Lab + Newton works under WSL2.** It is undocumented either way.
- Whether MuJoCo joint `stiffness`/`springref`, ball-joint limits, `solref`/`solimp` and actuator gains survive **MJCF → USD → Newton** unchanged for a body like hers. The pieces are documented separately, not end to end.
- Whether her body can be loaded in **Isaac Lab through Newton's `add_mjcf`** without the USD step. No documented path was found.
- **When** a Newton release and an Isaac Lab version will carry MuJoCo 4.0.1, and whether overriding Isaac Lab's Newton pin to Newton `main` works.
- The **size of the sim-to-sim gap** (tracking error, not just completion) for any Isaac Lab policy played in CPU MuJoCo. The `g1_deploy` evidence is one play per clip, on a robot, with an unpinned MuJoCo.
- Whether the built-in `Isaac-Motion-Tracking-G1` task, or its SuperMimic variant, accepts a **multi-clip dataset**. The docs say one clip per run.
- Install size of Isaac Lab without Isaac Sim, and actual install size of Isaac Sim 6.2 (only the 50 GB SSD minimum is documented).
- Training speed of any of these on a 5090.

## Sources

All accessed 2026-11-26.

- [IL-install] Isaac Lab installation (main docs) — https://isaac-sim.github.io/IsaacLab/main/source/isaaclab/installation.html
- [IL-install-rst] Same page, source — https://github.com/isaac-sim/IsaacLab/blob/main/docs/source/isaaclab/installation.rst
- [IL-releases] Isaac Lab releases (v3.0.0-beta … v3.0.0) — https://github.com/isaac-sim/IsaacLab/releases
- [IL-rel300] Isaac Lab v3.0.0 release notes (2026-10-20) — https://github.com/isaac-sim/IsaacLab/releases/tag/v3.0.0
- [IL-backends] Physics backends — https://isaac-sim.github.io/IsaacLab/main/source/concepts/physics_backends.html
- [IL-newton] Newton backend — https://isaac-sim.github.io/IsaacLab/main/source/concepts/physics-backends/newton.html
- [IL-ovphysx] OvPhysX backend — https://isaac-sim.github.io/IsaacLab/main/source/concepts/physics-backends/ovphysx.html
- [IL-solverdiff] Solver differences — https://isaac-sim.github.io/IsaacLab/main/source/concepts/solver_differences.html
- [IL-prep-newton] Prepare an asset for Newton with MJWarp — https://isaac-sim.github.io/IsaacLab/main/source/how-to/prepare_asset_for_newton.html
- [IL-transfer] Transfer policies between PhysX and Newton — https://isaac-sim.github.io/IsaacLab/main/source/how-to/transfer_policies_between_physx_and_newton.html
- [IL-import] Importing a new asset — https://isaac-sim.github.io/IsaacLab/main/source/how-to/import_new_asset.html
- [IL-mjcf-conv] `MjcfConverter` source — https://github.com/isaac-sim/IsaacLab/blob/main/source/isaaclab/isaaclab/sim/converters/mjcf_converter.py ; `MjcfFileCfg` — https://github.com/isaac-sim/IsaacLab/blob/main/source/isaaclab/isaaclab/sim/spawners/from_files/from_files_cfg.py
- [IL-issues] Known issues — https://isaac-sim.github.io/IsaacLab/main/source/refs/issues.html
- [IL-viz] Visualization — https://isaac-sim.github.io/IsaacLab/main/source/concepts/visualization.html
- [IL-video] Recording videos — https://isaac-sim.github.io/IsaacLab/main/source/how-to/record_video.html
- [IL-render] Renderers — https://isaac-sim.github.io/IsaacLab/main/source/concepts/renderers.html
- [IL-amp-cfg] Humanoid AMP env config (main and v3.0.0) — https://github.com/isaac-sim/IsaacLab/blob/main/source/isaaclab_tasks/isaaclab_tasks/contrib/humanoid_amp/humanoid_amp_env_cfg.py
- [IL-mt-doc] Training a G1 motion-tracking policy — https://github.com/isaac-sim/IsaacLab/blob/main/docs/source/how-to/train_g1_motion_tracking.rst
- [IL-mt-cfg] Motion-tracking env config — https://github.com/isaac-sim/IsaacLab/blob/main/source/isaaclab_tasks/isaaclab_tasks/core/motion_tracking/motion_tracking_env_cfg.py
- [IL-mt-commits] Commit history of `core/motion_tracking` (#8878, #9098, #9193) — https://github.com/isaac-sim/IsaacLab/commits/main/source/isaaclab_tasks/isaaclab_tasks/core/motion_tracking
- [IL-mt-license] Motion-tracking third-party notice — https://github.com/isaac-sim/IsaacLab/blob/main/docs/licenses/dependencies/motion-tracking-license.txt
- [IL-pyproject-300] Isaac Lab `pyproject.toml` at v3.0.0 — https://github.com/isaac-sim/IsaacLab/blob/v3.0.0/pyproject.toml
- [IL-pyproject-main] Isaac Lab `pyproject.toml` at main — https://github.com/isaac-sim/IsaacLab/blob/main/pyproject.toml
- [IS-req] Isaac Sim requirements — https://docs.isaacsim.omniverse.nvidia.com/latest/installation/requirements.html
- [IS-mjcf] Isaac Sim MJCF importer — https://docs.isaacsim.omniverse.nvidia.com/latest/importer_exporter/ext_isaacsim_asset_importer_mjcf.html
- [NV-forum-wsl] NVIDIA forum, "Is it possible to run Isaac Sim in WSL2?" (staff reply 2025-10-31) — https://forums.developer.nvidia.com/t/is-it-possible-to-run-isaac-sim-in-wsl2/349609
- [CUDA-WSL] NVIDIA CUDA on WSL user guide — https://docs.nvidia.com/cuda/wsl-user-guide/index.html
- [N-readme] Newton README — https://github.com/newton-physics/newton
- [N-mujoco] Newton MuJoCo solver guide — https://newton-physics.github.io/newton/latest/solvers/mujoco.html
- [N-pyproject] / [N-pyproject-main] Newton `pyproject.toml` at main — https://github.com/newton-physics/newton/blob/main/pyproject.toml
- [N-pyproject-d316] Newton `pyproject.toml` at d31603ff — https://github.com/newton-physics/newton/blob/d31603ff5e8389d1d6b2a5daef6ea2cb074c26ff/pyproject.toml
- [N-pr5337] Newton PR #5337 "Update MuJoCo and MuJoCo Warp to 4.0.1" (merged 2026-11-19) — https://github.com/newton-physics/newton/pull/5337
- [MUC-readme] / [MUC-changelog] mujoco-usd-converter README and CHANGELOG — https://github.com/newton-physics/mujoco-usd-converter
- [MJ-changelog] MuJoCo changelog — https://mujoco.readthedocs.io/en/latest/changelog.html
- [MK-readme] MimicKit README — https://github.com/xbpeng/MimicKit
- [MK-islab] MimicKit Isaac Lab engine — https://github.com/xbpeng/MimicKit/blob/main/mimickit/engines/isaac_lab_engine.py
- [MK-newton] MimicKit Newton engine — https://github.com/xbpeng/MimicKit/blob/main/mimickit/engines/newton_engine.py
- [MK-xml] MimicKit humanoid MJCF — https://github.com/xbpeng/MimicKit/blob/main/data/assets/humanoid/humanoid.xml
- [PM-install] ProtoMotions installation — https://nvlabs.github.io/ProtoMotions/getting_started/installation.html
- [PM-custom] ProtoMotions custom robot tutorial — https://github.com/NVlabs/ProtoMotions/blob/main/docs/source/tutorials/workflows/custom_robot.rst
- [PM-migration] ProtoMotions IsaacLab 3 migration pin — https://github.com/NVlabs/ProtoMotions/blob/main/docs/source/user_guide/isaaclab3_migration.rst
- [PM-d6] ProtoMotions D6 workaround — https://github.com/NVlabs/ProtoMotions/blob/main/protomotions/simulator/isaaclab/utils/mjcf_d6_workaround.py
- [PM-sim] ProtoMotions IsaacLab simulator — https://github.com/NVlabs/ProtoMotions/blob/main/protomotions/simulator/isaaclab/simulator.py
- [PM-pyproject] ProtoMotions `pyproject.toml` — https://github.com/NVlabs/ProtoMotions/blob/main/pyproject.toml
- [MJL-pyproject] mjlab `pyproject.toml` (main) — https://github.com/mujocolab/mjlab/blob/main/pyproject.toml
- [MJL-pypi] mjlab on PyPI — https://pypi.org/project/mjlab/
- [WBT] HybridRobotics/whole_body_tracking README (archived) — https://github.com/HybridRobotics/whole_body_tracking
- [BM] BeyondMimic paper — https://arxiv.org/html/2508.08241
- [G1D-readme] g1_deploy README — https://github.com/Double7sBurger/g1_deploy
- [G1D-mimic] g1_deploy motion-tracking policies README — https://github.com/Double7sBurger/g1_deploy/blob/main/policies/mimic/README.md
- [G1D-pyproject] g1_deploy `pyproject.toml` — https://github.com/Double7sBurger/g1_deploy/blob/main/pyproject.toml
- [P-mujoco] PyPI `mujoco` (4.0.1; 3.12.0 and 3.17.0 macOS arm64 cp312 wheels) — https://pypi.org/pypi/mujoco/json
- [P-newton161] / [P-newton180] PyPI `newton` 1.6.1 and 1.8.0 metadata — https://pypi.org/pypi/newton/1.6.1/json , https://pypi.org/pypi/newton/1.8.0/json
