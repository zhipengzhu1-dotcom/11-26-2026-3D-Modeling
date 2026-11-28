# Casual clothes for her

Researched 2026-11-28. Nothing was downloaded. One read-only look at her Visible Mesh was run locally; its numbers stay in the git-ignored `build/` folder, and this file states only what they mean.

**Question.** Her in-game dress is made of layered skirt tiers and bell sleeves, and when she dances they swing as stiff pieces. Could she wear casual clothes instead? Which clothes could be used, under what terms, and how would code put them on her?

## Answer

1. **It is feasible.** She has a skin surface under almost all of her dress. Her legs, hips and waist are skin the whole way round, from her feet up to her waist. Her upper chest, shoulders, neck and both arms are skin too. Her upper arms exist under the sleeves. Two places have no skin:
   - **Her bust.** Around her bust, the bodice is the only surface in about half the directions. Any new top must cover her bust completely, or skin must be made there first.
   - **Her elbows.** At each elbow, the sleeve cuff is the innermost surface.

   Her feet exist inside her shoes, so her own heels can stay. See [What is under her dress](#what-is-under-her-dress).
2. **Try a code-made skirt first.** Generate it with GarmentCode's `pygarment` library (MIT licence) from measurements taken from her by script, drape it with Blender's own Cloth, and use it in place of her skirt tiers only. Keep her bodice, sleeves and shoes for now.
   - It needs no account and no download from a third party.
   - It raises no question about anyone else's terms.
   - It fits `0003` (everything that makes her is code).
   - It answers the complaint directly: the skirt is cloth that drapes, not stiff tiers.
   - The risk is that nobody has published GarmentCode used on an anime-proportioned body [S1][S4].
3. **Second route: a ready-made outfit.** The candidates whose published terms survive are listed in [Ready-made clothes](#ready-made-clothes). The two most worth trying:
   - **原神七国运动服** by TSHE. Already fitted to Genshin bodies, ships PMX and VRM, and allows modification. It is sportswear [S10].
   - **毛衣百褶裙配布** by 大聪明绞肉机. A winter sweater and pleated skirt, fitted to the TDA body [S8].

   Every 模之屋 download needs the human's account. Every TDA-fitted outfit has to be refitted to her by script. That refitting is the hard, unproven part; see [Dressing her by script](#dressing-her-by-script).
4. **What the human decides or does:**
   - **The licence call.** Whether a new skirt, or a whole new outfit, is still 适度更改衣装. No first-party text defines 适度 [S14][S15][S16]. A skirt-only change is the smaller step. The readme itself invites questions to 观海 ("联系我【BiliBili：观海子】"); whether to ask him is the human's choice.
   - **The 模之屋 sidebar.** Read her model page on 模之屋 with the site set to Chinese, and check whether 禁止用于制作视频之外的用途 is switched on for her [S14]. If it is, a Live Session would need thought.
   - **Downloads.** Any ready-made outfit is downloaded with the human's own account (模之屋, BOOTH, niconico), or with an email address (Gumroad).
5. **The smallest test.**
   1. A Build step generates one GarmentCode skirt from her waist and hip measurements.
   2. It hides her skirt materials (裙, 裙2, 裙内, 裙2内, 裙2+, 裙2内+, 裙饰) with a Mask modifier.
   3. It drapes the new skirt with Blender Cloth, pinned at her waist and colliding with her legs. Her skin is complete from feet to waist, so the skirt has a body to lie on.
   4. It plays the stage 1 Reference Motion and renders the clip for an Eye Check: does the skirt now flow?

   Her bodice and sleeves stay on, so no picture shows her without clothing.

**What rests on what:**
- **Verified at the source:**
  - Her terms, on the 模之屋 page.
  - The GarmentCode and Robust Weight Transfer licences and the GarmentCode code paths.
  - The MMD Tools behaviour, from its source code.
  - The 模之屋 rule labels, on each candidate's page.
- **Rests on someone's post:**
  - That GarmentCode's simulator runs on a Mac CPU (an open issue [S3]).
  - That GarmentCode drapes on a body other than its own (an open issue [S5]).
  - Every closed-source fitting tool's claims (shop pages).
- **Not found:** any first-party definition of 适度; any anime character dressed by GarmentCode; the readmes inside the outfit archives, which no one has read because nothing was downloaded.

## Constraints that shape the answer

- **Her terms, original wording.** From the readme and her 模之屋 page [S14]:
  - 允许完善物理，修正模型权重、表情等bug；允许改色，适度更改衣装，添加spa、toon等
  - 请勿二次配布，以及拆取部件以用于改造其他模型
  - 请勿用于18禁作品…；请勿用于商业用途
  - 最终解释权归属：miHoYo
- **Direction.** The direction is always clothes onto her. Nothing of hers goes onto another model, and no garment made by combining her parts leaves the project.
- **`0002`.** The model, the dressed model, and the measurements taken from her never enter git. Only scripts and this text do. Renders carry the full credit list. Credit for a third-party garment joins that list.
- **`0003`.** The dressing is a Build step, so every tool must run headless from code. Windows-only PMXEditor plugins, Unity tools and closed GUI add-ons are out, except as ideas.
- **`0004`.** Her Simulation Body follows her clothed outline where clothing is stiff or close-fitting. A new close-fitting top changes that outline, and a changed outline means retraining her Controller. A loose skirt does not change it, because the skirt is Secondary Physics. This is one more reason to change the skirt first.
- **Out of scope.** Her face and body proportions stay as they are. Nothing R18, nothing commercial, nothing published.

## What is under her dress

**How this was found.** Two read-only passes, both kept in the git-ignored `build/outfit-inspect/`:
- **Headless Blender with MMD Tools.** For each of her 36 materials: its texture, the bones that carry its faces, and the height band it occupies.
- **A plain Python read of the PMX.** Rays were cast outward from inside her torso (from the spine axis), her thighs, her shins, her upper arms and her forearms, 16 directions per ring. Each ray records which material it meets first. Where skin exists all round, every ray meets skin first.

Nothing was rendered.

**Which materials are skin.** These use the skin toon texture (`skin.bmp`):
- **肌:** chest above the bust, shoulders, neck, both arms and hands.
- **足:** feet, legs, hips and waist, up to just under the bust.
- **颜**, 口舌 and the eye and face overlays.

Note that **体** is not skin, despite its name. It is the bodice, and it shares a texture sheet named 体.

**Which materials are clothing:**
- **体:** bodice, plus pieces on her head.
- **袖:** bell sleeves, from the elbow.
- **Skirt tiers:** 裙, 裙内, 裙2, 裙2内, 裙2+, 裙2内+. The last two are the tier's highlight layers.
- **裙饰, 裙饰2:** skirt ornaments.
- **饰, 饰2:** headdress, the bands on her upper arms, a pendant and ribbons.
- **珠, 宝石, 结晶:** beads, jewels, crystals.
- **鞋:** shoes.

Hair is 髮, 前髮 and 髮+. The microphone is 麦克风1 and 麦克风2.

**Where her skin exists:**
- **Legs.** Skin all the way round at every point tested along both thighs and both shins. Her feet are skin inside her shoes.
- **Hips and waist.** Skin all the way round from her hips up to just below the bust. There is surface between her hips and her chest under the bodice up to that point.
- **Bust band.** The bodice is the first surface in about half the ray directions. Skin exists in the other half and above the bust. So she has no complete surface around her bust under the bodice.
- **Arms.** Skin all the way round along both upper arms and both forearms. The upper arms exist under the sleeves and carry ornament bands. At the elbow the sleeve is the first surface, so the skin is incomplete right at the elbow, under the sleeve cuff.

**What follows:**
- **A skirt, trousers or shorts** can replace her skirt tiers. The body beneath is complete, so cloth has something to collide with.
- **A new top** must cover the bust band entirely, as any sweater, coat or high-necked top does. Then the missing skin never shows. A low-cut or sheer top would need skin made there first, and that edges toward changing her body, which is out of scope.
- **Short sleeves** would show her elbows, where skin is incomplete. Long sleeves avoid that.
- **Her shoes** can stay. Her heel pose and her feet are untouched.

## Ready-made clothes

### Where MMD clothing is published

- **模之屋 / PlayBox (aplaybox.com).** The richest free source found, with many Genshin-fitted edits [S7].
  - Every page carries five fixed 配布规则: commercial use, redistribution, modification, credit list, and use beyond video. A download rule is attached too, usually 关注作者 or 点赞+收藏.
  - Downloading needs an account. Some files have a password, such as "密码为配布视频BV号".
  - With the site set to English, the rule labels are mistranslated. Read them in Chinese.
- **BowlRoll (bowlroll.net).** The main Japanese MMD host; the tag is MMD衣装配布. Its listings would not load for automated reading, so no BowlRoll outfit was checked. Files there often need a password posted in a video description. Terms live in the readme inside the archive.
- **ニコニ立体 (3d.nicovideo.jp).** A caption search for 衣装配布 lists 24 works. Without login, a work page shows only "この作品をご覧いただくには ニコニコ会員登録 が必要です。", which hides even the licence. A niconico account is needed to read terms.
- **BOOTH (booth.pm).** Mostly VRChat outfits (FBX and unitypackage, made for named avatars), about ¥500 to ¥2,500, often under the VN3 or UV licence. A few items include PMX. Buying needs a pixiv account.
- **Gumroad, reached from DeviantArt.** Many Western MMD outfit makers, usually fitted to "TDA" bases. Terms are on the product page. Free items are "$0+" and need an email address, not an account.

### Candidates and their terms

**How a candidate "survives":** its published terms allow the following:
- use on a different, game-derived, modified model;
- non-commercial use;
- no redistribution, since the project never publishes the dressed model;
- credited renders.

**The readmes inside the archives are unread** because nothing was downloaded. A candidate can still fail on its readme.

| # | Outfit and page | Maker | Made for | Format | Access | Terms (original) | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | 毛衣百褶裙配布 (sweater, pleated skirt) [S8] | 大聪明绞肉机 | TDA (tagged) | PMX | 模之屋 account, 关注作者 | 禁止商用 / 允许二次配布 / 允许修改模型 / 使用需书写完整借物表 / 允许用于制作视频之外的用途 | Survives. Winter look. |
| 2 | 毛衣破洞牛仔裤 (sweater, ripped jeans) [S9] | 大聪明绞肉机 | not stated | PMX | account, 点赞+收藏 | 禁止商用 / 禁止二次配布 / 允许修改模型 / 使用需书写完整借物表 / 允许用于制作视频之外的用途 | Survives. |
| 3 | 牛仔裤+大衣 (jeans, long coat) [S11] | 07nene | not stated; tagged 布料 | PMX | account, 点赞 | 允许商用 / 允许二次配布 / 允许修改模型 / 使用需书写完整借物表 / 允许用于制作视频之外的用途 | Survives. A coat suits a cold city. |
| 4 | 原神七国运动服 [S10] | TSHE, "模型改自@LILISIBJ莉莉丝编辑" | Genshin models | PMX and VRM | account | 允许商用 / 允许二次配布 / 允许修改模型 / 使用无需书写完整借物表 / 允许用于制作视频之外的用途 | Survives. Closest body. Credit the upstream maker too, whose terms are #5's. |
| 5 | 璃月人 outfits [S12] | 莉莉丝编辑 | Genshin | PMX | account, 关注作者, 点赞+收藏 | "你拿来怎么整就行二配都行 / 反正别商用别说是自己做的就行 / 用了写上我名就行了"; 禁止商用 / 允许修改模型 / 使用需书写完整借物表 | Survives. Liyue dress, not casual. |
| 6 | Carefree Rainbow Pastel Jumper Outfit [S17] | ThatAlex | not stated ("Base not included") | ZIP; "with skirt Physics" | Gumroad, $5 | "For non-profit use only / Edit all you want / Do not redistribute / Import to other games is allowed" | Survives. |
| 7 | Faux Coat (Free) [S18] | Zesshi_ | generic; "You may need to resize/reshape the mesh" | FBX (Unity, Poiyomi materials) | Gumroad, $0+ | "Redistribution and editing is OKAY. Can be used in public models, for sale models, personal, whatever. However, DO NOT sell it individually and DO NOT claim as your own work." "Credit me always…" | Survives. Its materials need redoing for Blender. |
| 8 | mmd jacket pack / varsity-bomber jackets [S19] | ciella-lune | "larigian's tda miku base" | PMX | Gumroad, from $2.50 | "for use in mmd or modelling softwares … for the purpose of editing, (re)modelling, or rendering only. credit ciella-lune if using." | Probably survives. The linked full terms were not read. |
| 9 | Xmas Dress [S20] | SAYUMIVI | TDA ("follow TDA rules if you use a TDA base") | PMX | Gumroad, $5 | "Allowed -Commercial use … -Editing -Convert to other programs … Prohibited -NO Redistribution…" | Survives. Festive rather than casual. |
| 10 | 冬のおめかし着 -Winter Onepiece- [S21] | ちょなの本舗 | ten VRChat avatars | FBX, unitypackage | BOOTH, ¥1,000+ | "本モデルはUVライセンスで公開されています" (seen only in a fetch tool's summary) | Unconfirmed. Read the UV licence text first. |

**Fails or needs care:**
- **常服outfit配布 [S13]: fails.**
  - The page says "请勿二次配布原模型，提取部件等" and "不允许将TDA的材质移植到其他式的模型上".
  - Its fixed rules include 禁止修改模型.
- **TDA-fitted outfits (#1, #8, #9).** Their makers point to the TDA base's own rules. Those rules were not read for this report. Read them before using a TDA-fitted garment.
- **Others found:** a padded floral winter jacket says 禁止用于制作视频之外的用途. A pink sweater fitted to PJSK bodies adds "禁止在日本社区公开使用".

**Fit.** Only #4 and #5 were made for Genshin bodies. The others were made for TDA, for VRChat avatars, or for no stated body, and need refitting.

## Clothes made by code

- **GarmentCode / `pygarment`** (ETH, SIGGRAPH Asia 2023) [S1][S2]. This is the only generator that fits this project today.
  - **Code licence.** MIT. Installs with `pip install pygarment`. The last push was 2025-06.
  - **Body input.** A YAML file of about 26 body measurements in cm, such as height, bust, waist, hips, `waist_line`, `hips_line`, `arm_length` and `arm_pose_angle`. Each is defined in the repository's measurement sheet. The author says they are "hand-crafted… not based on the existing sets of measurements for the SMPL body model" [S2]. So no SMPL fitting is needed: a Build step can measure her by slicing her Visible Mesh, and keep the numbers in `build/`.
  - **Pose.** The measurements also place the panels around the body in 3D. Her pose must match `arm_pose_angle`.
  - **Output.** A pattern JSON with printable SVG/PDF, a stitched "box mesh" OBJ, and a simulated OBJ. UVs come out as panel islands.
  - **Draping on another body.** Its draping code loads `<body>.obj`, `<body>.yaml` and a per-vertex segmentation JSON (body, arms, legs, face). So a body other than its own needs a segmentation file, which could be made from her bone weights. That reading comes from the code [S2]. One user reports draping on a MakeHuman body [S5].
  - **Simulator licence.** The draping uses the authors' fork of NVIDIA Warp, under the NVIDIA Source Code License: "may be used … non-commercially … for research or evaluation purposes only" [S3].
  - **Simulator on a Mac.** A user reports the fork builds on a Mac CPU. They also report that on macOS the simulation silently does nothing until a one-line fix is made (open issue #60) [S3].
  - **The cleaner path here.** Drape the box mesh with Blender's own Cloth (CPU, headless, no extra licence).
  - **Dataset.** GarmentCodeData is CC BY 4.0 according to ETH's repository metadata. It is useful as ready garments, but those were made on its own bodies [S2].
- **Learning-based generators.** These turn text or images into patterns, and none accepts an arbitrary character body [S4]:
  - **AIpparel (MIT)** and **ChatGarment (Apache-2.0)**. Both output GarmentCode patterns, need CUDA, and ChatGarment's text path calls GPT-4o.
  - **Design2GarmentCode (MIT).** Needs CUDA.
  - **SewingLDM (Apache-2.0).**
  - **Sewformer and DressCode.** No licence file, so all rights are reserved by default. Both need Maya and Qualoth on Windows.
  - **GarmentDiffusion.** Has no code.
- **Older ETH pattern dataset.** Garment Pattern Generator (2021): its code is MIT and its dataset is CC BY 4.0, but it needs Maya plus the commercial Qualoth plug-in.
- **Refitting research without code.**
  - **Dress Anyone (2024)** refits a pattern to a new body by differentiable simulation.
  - **Anime-Ready (ICLR 2026)** extends an anime body model with garments.
- **Blender's own sewing springs** [S6]. Loose edges between panels pull the panels together in Cloth: "Sewing springs are created by adding extra edges to a cloth mesh that are not included in any faces". Fully scriptable on the CPU.
- **Not usable in a code-only Build.**
  - Paid garment add-ons (Garment Tool, Simply Cloth, Garment Studio) have no documented scripting interface. Garment Studio is Windows/NVIDIA only.
  - Marvelous Designer's Python API reportedly has no headless mode.
  - VRoid Studio has no scripting at all.
- **Anime bodies.** No account was found anywhere of any of these tools being used on an MMD, VRM or anime-proportioned body. That includes GitHub issues, papers, and Chinese and Japanese searches [S4]. Her long legs and heels against GarmentCode's trouser and skirt programs are untested.

## Dressing her by script

Everything below can run headless with bpy, MMD Tools and Blender's built-in modifiers [S22][S23]. None of the open tools fits a garment made for another body to hers without hand work. The closed-source "fit" add-ons on BOOTH [S26] and the Unity tools (Modular Avatar, AAO) are ideas only.

1. **Remove the old clothing.**
   - Delete its faces by material index with bmesh, or hide them with a Mask modifier on a vertex group.
   - The MMD Tools exporter writes the evaluated mesh, so masks and other modifiers are baked into any export [S23].
   - Delete the old skirt's bones, the rigid bodies whose `mmd_rigid.bone` is one of those bones, and the joints attached to those bodies. All of this works on data directly, no operators [S22].
   - Material morphs only fade a material at render time, and leave its geometry and physics in place. Wrong for a swap [S23].
2. **Fit a garment made for another body.** This is the unproven step.
   - **Pose-to-pose by bone name.** Import the garment's PMX with the same options as hers, so bone names match: the importer renames 左足 to 足.L by default. Pose its armature so each joint sits on hers, segment by segment (thigh, shin, spine, arm), not with one uniform scale. Apply the Armature modifier, then apply the pose as rest. Modular Avatar does the bone-snapping half of this in Unity, and does not refit the mesh [S27].
   - **Then a light correction.** Shrinkwrap "Outside" with an offset, only on close-fitting regions. Or Surface Deform bound to a stand-in of the old body, if one with matching topology exists [S24].
   - **What a code-made garment skips.** It is cut to her measurements, so it needs none of this.
3. **Bind it to her bones.**
   - The Data Transfer modifier copies her vertex groups by nearest interpolated face [S24].
   - **Robust Weight Transfer (Blender port, GPL-3.0)** is better where she has no surface. It matches by distance and normal angle, then fills the unmatched vertices smoothly (inpainting). That is exactly the bust band. Its core is NumPy plus libigl, so it runs headless [S25]. The original paper code is MIT.
   - Then parent the garment to her armature (`FnModel.attach_mesh_objects`).
   - Do not use MMD Tools' model join for body bones: it does not merge same-name bones [S22].
4. **Hide the body under it.**
   - Delete or mask the skin faces that are always covered. Find them by casting rays from her skin to the garment.
   - Keep a ring of skin under every garment edge.
   - This is the same remedy the Secondary Physics study already lists [S28].
5. **What the garment needs for Secondary Physics.**
   - **Blender Cloth route.** A cloth garment needs a pin group at the waist or shoulders, and a Collision modifier on her body after its Armature modifier [S6][S28].
   - **MMD rigid-body route.** The garment needs its own bone chains (rings of chains hanging from 下半身), rigid bodies and joints. `FnRigidBody.new_rigid_body_object` and `new_joint_object` create them as data, but MMD Tools has no automatic skirt rigging [S22]. Ready-made PMX outfits sometimes ship their own ("with skirt Physics" [S17]).
6. **Toon look.**
   - A new mesh needs the MMD edge settings per material and the `mmd_edge_scale` vertex group. Without them it gets no outline, or a thick one on thin cloth [S23].
   - MMD Tools' edge preview Solidify must be removed before any export.

**What breaks:**
- **Rest pose.** MMD motion assumes an A-pose rest. VRChat FBX garments are usually in T-pose and must be posed to A-pose before any transfer [S29].
- **Heels.** Leave her own shoes and feet. Delete any shoes that come with a garment. Tights would need the ankle and toe bones posed to her heel pose first.
- **Her proportions.** Long legs and a different head-to-body ratio defeat any uniform scale. Each segment must be scaled to match.
- **No surface under the old clothing.** At her bust and elbows, nearest-surface transfer and Shrinkwrap pick wrong targets. Mask them out of Shrinkwrap, and use Robust Weight Transfer's inpainting there.
- **Double surfaces.** Garments with linings can be pushed through themselves by per-vertex snapping.
- **Normals.** The exporter keeps custom normals by default, and they go stale after deforming.
- **Weights.** More than four bone weights per vertex are silently cut to four [S23].

## The licence question

- **First-party, verified.** The model page carries the readme word for word, and adds: "◆他人使用本模型所造成的一切不良后果，不由模型改造者与miHoYo承担，请向使用者追究全部责任" [S14].
  - Its sidebar shows five rule labels. Modification and credit are lit; the other three are grey.
  - In English the labels read: "Commercial use is prohibited", "Secondary distribution is prohibited/ok", "Allows modification of the model", "Need complete credit list / no need credit", "Forbidden for use other than video production".
  - What grey means was not settled; see Answer 4.
- **观海子 (Bilibili space 17466365).** No post sets rules or an FAQ for the miHoYo models he converts [S15]. Community evidence only: in 2019 he reposted a video that put a third-party "Reburn" coat on his Honkai Impact 3rd model. The video's text says "在两者组合之后发生了化学反应", and he added "我晕了" [S15]. That reads as a welcome, not a rule.
- **miHoYo.** No first-party Genshin text on modifying or re-dressing its MMD models was found.
  - The 同人周边 guidelines, seen only through reposts, cover merchandise.
  - The Star Rail fan-work guideline, also seen only as a repost, says "用户可以自由对《崩坏：星穹铁道》系列作品已公开发表的内容进行二次创作". It bans extracting models for physical merchandise [S16].
- **模之屋's user agreement** has no clause on modifying downloaded models or combining them with other assets [S14].
- **Other official HoYoverse readmes on 模之屋 word it differently** [S16]:
  - **Star Rail 遐蝶 and ZZZ 菲欧妮** say "允许改造，优化骨骼和刚体，重制UV". Neither has the word 适度, and neither has a 拆取部件 clause. The ZZZ one adds a ban on AI training.
  - **An earlier ZZZ readme**, seen only in English translation, matched 观海's wording ("moderate clothing changes").

  So 观海's 适度 looks like a deliberate limit, and nothing defines it.
- **Community readings, not first-party.**
  - pixiv 百科 on 原神MMD: "規約内であれば着せ替えやモデル改造も許可されている" [S16].
  - A Nico 大百科 summary, seen only in a search snippet, reads outfit changes as allowed, but turning her into a *different character* as not.
  - No takedown over an outfit swap was found.
- **Direction.**
  - 拆取部件以用于改造其他模型 forbids taking her parts out for other models.
  - Clothes onto her is the opposite direction, and no text read forbids it.
  - Each garment's own terms must allow use on another model. The table above records that. #6's "forbid the editing taking parts" binds whoever distributes a finished model, which this project never does.

## What could not be determined

- Whether "适度更改衣装" covers a full outfit, or only a skirt. Only miHoYo, or 观海 by asking, can say.
- What the grey 模之屋 sidebar labels mean on her page.
- The readmes inside every outfit archive, the TDA base rules, the full terms of #8, and the UV licence text for #10.
- Any BowlRoll or ニコニ立体 outfit's terms. Listings would not load, or the terms needed a login.
- Whether GarmentCode's skirt and trouser programs behave on her long legs and heels, and whether its Warp fork really simulates on this Mac after the fix.
- Whether closed fitting add-ons do what their shop pages say.

## Sources

- [S1] GarmentCode repository, LICENSE (MIT), `test_garmentcode.py`, `test_garment_sim.py`, `docs/Installation.md`: https://github.com/maria-korosteleva/GarmentCode
- [S2] GarmentCode body measurements: `assets/bodies/mean_female.yaml`, `docs/Body Measurements GarmentCode.pdf`, `assets/bodies/Readme.md`, `pygarment/meshgen/sim_config.py`, `assets/garment_programs/sleeves.py`. Issues #6 (measurements are hand-made), #27 and #56 (no SMPL measuring), #33 (UVs). GarmentCodeData licence metadata: https://www.research-collection.ethz.ch/server/api/core/items/d9df8fe3-2add-49a2-bb58-21750ca7970c
- [S3] NvidiaWarp-GarmentCode fork and its LICENSE.md: https://github.com/maria-korosteleva/NvidiaWarp-GarmentCode. GarmentCode issue #60 (macOS "Darwin" no-op): https://github.com/maria-korosteleva/GarmentCode/issues/60. Issue #63 (PyTorch port): https://github.com/maria-korosteleva/GarmentCode/issues/63
- [S4] Learning-based generators:
  - AIpparel: https://github.com/georgeNakayama/AIpparel-Code
  - ChatGarment: https://github.com/biansy000/ChatGarment
  - Design2GarmentCode: https://github.com/Style3D/design2garmentcode-impl
  - SewingLDM: https://github.com/shengqiliu1/SewingLDM
  - Sewformer: https://github.com/sail-sg/sewformer
  - DressCode: https://github.com/IHe-KaiI/DressCode
  - GarmentDiffusion: https://github.com/Shenfu-Research/GarmentDiffusion
  - Garment Pattern Generator: https://github.com/maria-korosteleva/Garment-Pattern-Generator
  - Dress Anyone: https://arxiv.org/abs/2405.19148
  - Anime-Ready: https://www.iclr.cc/virtual/2026/poster/10010948
- [S5] GarmentCode issue #62 (custom MakeHuman body, licence of bundled bodies): https://github.com/maria-korosteleva/GarmentCode/issues/62
- [S6] Blender Manual, Cloth Shape (Pin Group, sewing springs): https://docs.blender.org/manual/en/latest/physics/cloth/settings/shape.html
- [S7] 模之屋 site and search: https://www.aplaybox.com/
- [S8] 毛衣百褶裙配布: https://www.aplaybox.com/details/model/Q1QOuaDqKVLn
- [S9] 毛衣破洞牛仔裤（服装配布）: https://www.aplaybox.com/details/model/Elf9npg9IiCa
- [S10] 【MMD、vrm衣服改模配布】原神七国运动服: https://www.aplaybox.com/details/model/aMvgwwHE34ju
- [S11] 牛仔裤+大衣: https://www.aplaybox.com/details/model/e8no7SVM2H1O
- [S12] 【MMD衣服配布】璃 月 人: https://www.aplaybox.com/details/model/5PujLp64NZaD
- [S13] 常服outfit配布: https://www.aplaybox.com/details/model/q8APtLiOcqwA
- [S14] Her model page, 【原神】沃雅妮莎: https://www.aplaybox.com/details/model/ZXUKJHsPeCEo. 模之屋 user agreement: https://www.aplaybox.com/agreeformwork/user-agreements
- [S15] 观海子's Bilibili space: https://space.bilibili.com/17466365. The reposted video: https://www.bilibili.com/video/BV114411v7aR/
- [S16] Other readmes and fan-work rules:
  - Star Rail 遐蝶: https://www.aplaybox.com/details/model/Eb6vXivegiZM
  - ZZZ 菲欧妮: https://www.aplaybox.com/details/model/ruG9HuID3O8q
  - Earlier ZZZ readme (English translation): https://80.lv/articles/grab-official-zenless-zone-zero-mmd-models-for-free
  - Star Rail fan-work guideline (repost): https://www.bilibili.com/read/cv23111427/
  - pixiv 百科 原神MMD: https://dic.pixiv.net/a/原神MMD
- [S17] ThatAlex, Carefree Rainbow Pastel Jumper Outfit: https://thatalex.gumroad.com/l/JKWnt
- [S18] Zesshi_, Faux Coat (Free): https://zesshi.gumroad.com/l/FauxCoatZ
- [S19] ciella-lune, jacket packs: https://ciellalune.gumroad.com/l/mmdjacketpack, https://ciellalune.gumroad.com/l/varsitybomberjackets
- [S20] SAYUMIVI, Xmas Dress: https://sayumivi.gumroad.com/l/DnmHl
- [S21] ちょなの本舗, 冬のおめかし着 -Winter Onepiece-: https://booth.pm/ja/items/6418406
- [S22] MMD Tools source:
  - `core/model.py`
  - `operators/rigid_body.py`
  - `operators/model_edit.py`
  - `operators/misc.py`

  https://github.com/MMD-Blender/blender_mmd_tools (read through the UuuNyaa/blender_mmd_tools path, which redirects to it)
- [S23] MMD Tools source: `core/pmx/exporter.py`, `operators/fileio.py`, `core/morph.py`, `operators/material.py`. Same repository.
- [S24] Blender source, `MOD_surfacedeform.cc` and `rna_modifier.cc` (Surface Deform, Shrinkwrap, Data Transfer options): https://github.com/blender/blender
- [S25] Robust Weight Transfer, Blender port (GPL-3.0), `weighttransfer.py`: https://github.com/sentfromspacevr/robust-weight-transfer. Original code (MIT): https://github.com/rin-23/RobustSkinWeightsTransferCode
- [S26] BOOTH fitting add-ons (shop pages, closed source): https://booth.pm/en/items/8930466, https://booth.pm/en/items/8647065
- [S27] Modular Avatar, Merge Armature: https://modular-avatar.nadena.dev/docs/reference/merge-armature
- [S28] This repo, Secondary Physics study: branch `research/secondary-physics-no-clipping`, `docs/research/secondary-physics-no-clipping.md`
- [S29] babylon-mmd, applying MMD animation to non-MMD models (A-pose): https://noname0310.github.io/babylon-mmd/docs/reference/runtime/apply-mmd-animation-on-non-mmd-model
