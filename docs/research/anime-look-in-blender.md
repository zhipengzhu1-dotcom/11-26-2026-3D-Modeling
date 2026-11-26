# The bright anime look in Blender

Research for issue #6. Question: how do you get a Genshin-style cel-shaded look in Blender for the official miHoYo MMD model of Vodyanitsa, covering shader approaches and existing shader packs (with their licences), outlines, face shadows, rim light, bloom and high-key lighting? It also covers the two known import problems and which Blender version and renderer suit an M4 Max Mac.

Checked on 2026-11-26 against Blender 5.2.2 LTS, the version installed on the target Mac. Some API facts were checked by running that Blender headless (`Blender -b --factory-startup --python probe.py`). Those are marked **[verified locally]**.

## Answer in one paragraph

Use **Blender 5.2 LTS + EEVEE (Metal) + MMD Tools 4.5.x**, and build **your own toon material** from the MMD diffuse textures. That material is a Diffuse BSDF → Shader to RGB → two-step colour ramp with a pale tinted shadow colour, which works like a hand-made MMD "toon" texture. Add a facing-ratio rim term and an emission term for the chest emblem. Draw outlines with an **inverted-hull Solidify** modifier. Fix face shading with **custom normals** plus **light/shadow linking**, not with a game face-shadow map. Use the **Standard** view transform instead of AgX, a bright pastel world, and the compositor **Glare node set to Bloom**.

All of the existing Genshin shader packs (Festivity's, HoyoToon-Blender, the michael-gh1 setup wizard) are built for datamined game assets: lightmaps, shadow ramps and face shadow maps. They say outright that they are *not* for the MMD variants, so the project should not use them. Everything above works with the MMD release's own textures, and most of it carries over to a real-time engine.

## 1. Blender version, renderer and importer

| Item | Finding | Source |
|---|---|---|
| Blender | 5.2 LTS, released 14 July 2026 and maintained until July 2028. 5.2.2 LTS is installed. 5.3 came out on 10 November 2026. | [5.2 notes](https://developer.blender.org/docs/release_notes/5.2/), [5.3 notes](https://developer.blender.org/docs/release_notes/5.3/) |
| GPU backend | Blender 5.2 on this Mac runs on `METAL` **[verified locally]** | `bpy.context.preferences.system.gpu_backend` |
| Render engine | Only one EEVEE remains: the engine enum is `['BLENDER_EEVEE']` **[verified locally]**. MMD Tools maps the old `BLENDER_EEVEE_NEXT` (4.2–4.5) to `EEVEE` for 5.0+. | [mmd_tools `core/material.py`](https://github.com/MMD-Blender/blender_mmd_tools/blob/main/mmd_tools/core/material.py) |
| Why EEVEE, not Cycles | The Shader to RGB node, which is the base of ramp toon shading, is **EEVEE only**. Cycles does support Metal on Apple Silicon, but you lose that node, and a path tracer adds nothing to a flat-lit anime look. EEVEE also previews the final frame in real time. | [Shader to RGB](https://docs.blender.org/manual/en/latest/render/shader_nodes/color/shader_to_rgb.html), [Cycles GPU rendering](https://docs.blender.org/manual/en/latest/render/cycles/gpu_rendering.html) |
| Importer | **MMD Tools** (GPL-3.0) is on the official Extensions platform. The current version is 4.5.14 (2 September 2026), listed as "Blender 4.2 LTS and newer". The repo is active (last push 19 November 2026). | [Extensions version history](https://extensions.blender.org/add-ons/mmd-tools/versions/), [GitHub](https://github.com/MMD-Blender/blender_mmd_tools) |
| 5.2 or 5.3? | Stay on 5.2 LTS. 5.3 adds *Material Lighting* nodes (Light Accumulation / Light Info / Light Evaluation) that the notes say suit "toon and stylized shading". They give per-light toon control, so they are worth a look later, but nothing below needs them. | [5.3 EEVEE notes](https://developer.blender.org/docs/release_notes/5.3/eevee/) |

Changes since older tutorials, which matter because most Genshin/MMD tutorials predate them:
- **Blend Mode → Render Method (4.2).** "Material > Blend Mode was replaced by Material > Render Method. Blended corresponds to the former Alpha Blend". Dithered behaves like the old Alpha Hashed. Shadow Mode moved to Object > Visibility > Ray Visibility > Shadow. ([4.2 EEVEE notes](https://developer.blender.org/docs/release_notes/4.2/eevee/))
- **The EEVEE Bloom checkbox is gone (4.2).** It was "removed in favor of the realtime compositor Glare node with Bloom glare type". You can preview it in the viewport by enabling the compositor in the Shading popover. ([4.2 migration](https://developer.blender.org/docs/release_notes/4.2/eevee_migration/))
- **Light & shadow linking in EEVEE (4.3)**, matching Cycles. ([4.3 EEVEE notes](https://developer.blender.org/docs/release_notes/4.3/eevee/))
- **Raycast shader node (5.1)**, described as enabling "NPR stylization integrated with scene shading". In EEVEE it is screen-space only. 5.1 also added transparency evaluation for Shader to RGB. ([5.1 EEVEE notes](https://developer.blender.org/docs/release_notes/5.1/eevee/), [Raycast node](https://docs.blender.org/manual/en/latest/render/shader_nodes/input/raycast.html))
- **Official NPR project.** The Goo-Engine-derived NPR prototype branch has not been merged as a whole. Only pieces of it reached main: light linking, the Raycast node and the 5.3 lighting nodes. Do not plan around the prototype. ([NPR design task](https://projects.blender.org/blender/blender/issues/120403))

## 2. Existing shader packs and what they need

| Project | Licence | Status | Inputs it needs | Fit for this project |
|---|---|---|---|---|
| [festivities/Blender-miHoYo-Shaders](https://github.com/festivities/Blender-miHoYo-Shaders) (Festivity's Genshin shader) | GPL-3.0 | **Archived** (read-only) | Game textures. The description says: "These are for datamined assets, not custom-made ones nor the MMD variants." | **No.** It depends on ripped assets. |
| [Hoyotoon/HoyoToon-Blender](https://github.com/Hoyotoon/HoyoToon-Blender) | HoyoToon Shader License HTSL-1.1 (custom: attribution required, group exclusions, content prohibitions) | Last push October 2024. Targets **Goo Engine**, and the setup steps say "Open Blender 4.1". | The same description: "for datamined assets, not custom-made ones nor the MMD variants" | **No.** Ripped assets, a forked Blender, and stale. |
| [Hoyotoon/HoyoToon](https://github.com/Hoyotoon/HoyoToon) | GPL-3.0 file in the repo, while the README points to the HoyoToon licence | Active | Unity only, datamined assets | Not Blender. Relevant only to the later real-time viewer, and it has the same ripped-asset problem. |
| [michael-gh1/Addons-And-Tools-For-Blender-miHoYo-Shaders](https://github.com/michael-gh1/Addons-And-Tools-For-Blender-miHoYo-Shaders) (setup wizard) | GPL-3.0 | Active | Its wizard asks for "the folder with the character model and textures (lightmaps, diffuses, etc.)" and imports `.fbx` game rips plus outline lightmaps. | **No.** It is built around the ripped-asset pipeline. |
| [dillongoostudios/goo-engine](https://github.com/dillongoostudios/goo-engine) | GPL (Blender fork) | Release branches up to `goo-engine-v4.4-release`. Prebuilt binaries come only through Patreon. No confirmed Apple Silicon build. | Any textures (it is an engine, not a material) | Not needed. Stock 5.2 now has light linking and Shader to RGB. |
| **MMD Tools' own MMD shader** | GPL-3.0 | Ships with the importer | Diffuse, plus the optional **toon** texture (a shadow-colour ramp) and **sphere** texture (a matcap), as stored in the PMX | **Yes, as a starting point.** Out of the box it gives the classic MMD look. The model's licence explicitly allows adding sphere and toon textures. |
| **A hand-built EEVEE toon material** (Section 3) | Yours | n/a | Only the MMD diffuse textures, plus optional hand-made ramps | **Recommended.** |

**Ripped-asset flag.** The real Genshin look depends on per-texel game data: a lightmap whose channels hold shadow threshold, specular mask and material ID, plus shadow ramps and an SDF face shadow map. Official MMD releases do not ship these, and every Genshin-accurate pack needs them. Using such a pack would mean game-ripped textures, which the licence and the project rule out. A good approximation of the *mood* the owner wants (bright, soft, pastel, bloom) does not need them, because most of the high-key look comes from lighting and post-processing, not the lightmap.

## 3. The recommended material (MMD textures only)

Per material, starting from the MMD diffuse texture:

1. **Toon bands.** Diffuse BSDF (white) → **Shader to RGB** → Color Ramp (Constant or a narrow Linear step) → Mix (Multiply) with the diffuse texture. For a pastel look, make the shadow colour a **light tint** (lavender or cool aqua at roughly 80–90 % value), not grey. That is the same job an MMD toon texture does, so a hand-painted 1×N ramp image works just as well and is allowed by the licence. Warning from the manual: Shader to RGB "breaks the PBR pipeline", so results are unpredictable with AO and other screen-space effects. Keep Fast GI and AO off for character materials. ([Shader to RGB](https://docs.blender.org/manual/en/latest/render/shader_nodes/color/shader_to_rgb.html))
2. **Transparency.** Feed the MMD alpha (material alpha × texture alpha) through a Mix Shader with a Transparent BSDF *after* the toon stage. On an upstream BSDF, alpha is invisible to hashed or dithered transparency once it has gone through Shader to RGB (same page; 5.1 added transparency evaluation, but wiring alpha after the node is the robust choice).
3. **Rim light.** Layer Weight (Facing) or Fresnel → ramp → add a pale cyan or white rim, masked to the lit side with the same Shader to RGB term. For a depth-based rim like Genshin's, the 5.1 **Raycast** node can trace a short ray along the view-space offset, but in EEVEE it has the screen-space limitations listed in the manual. ([Raycast node](https://docs.blender.org/manual/en/latest/render/shader_nodes/input/raycast.html)) A **light-linked rim light** that hits only the character is the simplest option. ([4.3 notes](https://developer.blender.org/docs/release_notes/4.3/eevee/))
4. **Chest emblem.** Add an Emission term with strength above 1, so the Bloom glare picks it up selectively (Section 6).
5. **Specular and hair highlight.** The MMD sphere texture, used as a matcap via the MMD shader's Sphere input or a hand-made one, gives the anime hair sheen without the game's specular mask.

## 4. Outlines

- **Inverted hull (recommended).** Add a Solidify modifier with **Flip Normals** and a **Material Offset** pointing at a black or dark-tinted outline material that has backface culling on. ([Solidify modifier](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/solidify.html)) MMD Tools ships exactly this as "Edge Preview": its `mmd_tools.edge_preview_setup` operator previews the PMX's own per-material edge colour and size "using 'Solidify' modifier" ([operators/material.py](https://github.com/MMD-Blender/blender_mmd_tools/blob/main/mmd_tools/operators/material.py)). That gives artist-authored outline widths straight from the model data. For Genshin-like lines, tint the outline per material (dark teal on hair, darker skin tone on the face) rather than using pure black. Use a vertex group to thin or remove lines on the face.
- **Line Art (Grease Pencil modifier).** Gives cleaner silhouettes and intersection lines from the camera, but it runs the full occlusion calculation per modifier and needs an active camera. It is fine offline and slow for long dance clips. ([Line Art](https://docs.blender.org/manual/en/latest/grease_pencil/modifiers/generate/line_art.html))
- The local API has a `GreasePencilLineartModifier` type **[verified locally]**.

## 5. Face shadows

Genshin hides ugly face shading with an SDF face-shadow texture driven by the head direction. That texture is game data, so it is ripped and not used here. Alternatives:

- **Custom normals.** Transfer smooth normals from a sphere or ellipsoid proxy onto the face with the **Data Transfer** modifier (Custom Normals), so the toon threshold sweeps cleanly across the face. ([Data Transfer](https://docs.blender.org/manual/en/latest/modeling/modifiers/modify/data_transfer.html)) This changes shading only, not the mesh shape, so it stays within "no face proportion changes".
- **Light and shadow linking.** Give the face its own key light and exclude hair and bangs as shadow blockers, so the forehead and cheeks do not get hair-shadow blotches. ([4.3 notes](https://developer.blender.org/docs/release_notes/4.3/eevee/))
- **High-key cheat.** For this bright look, push the face ramp threshold so the face is nearly always in the lit band, and optionally switch off shadow casting for the hair object (Object > Visibility > Ray Visibility > Shadow, per the [4.2 notes](https://developer.blender.org/docs/release_notes/4.2/eevee/)).
- A hand-authored SDF map driven by the head bone's forward vector (from a driver) is possible later. It would be your own new texture, not a ripped one. Inference: not needed for stage 1.

## 6. High-key lighting, colour and bloom

- **View transform: Standard.** The default in 5.2 is AgX **[verified locally]**. The manual says AgX "desaturates highly exposed colors to mimic film", while Standard "does no extra conversion… often used for non-photorealistic results". Standard keeps her texture colours exact. Available transforms in 5.2: Standard, ACES 1.3, ACES 2.0, Khronos PBR Neutral, AgX, Filmic, Filmic Log, False Color, Raw **[verified locally]**. ([Displays & Views](https://docs.blender.org/manual/en/latest/render/color_management/displays_views.html))
- **Lighting.** Use a bright pastel World colour as soft fill, which lifts the shadows and drops contrast. Add one Sun as the key, with a slightly raised angle for soft shadow edges, and a light-linked rim light. Keep exposure high but below clipping on the dress whites.
- **Bloom.** Compositor → **Glare** node, Type **Bloom** (or **Fog Glow**, "a more physically accurate version of Bloom… softer… at the cost of increased computation time"). The controls are Threshold, Smoothness, Clamp/Maximum, Strength, Saturation, Tint and Size. A low threshold with high Size gives the dreamy overall glow, and a high threshold catches only the emblem and highlights. ([Glare node](https://docs.blender.org/manual/en/latest/compositing/types/filter/glare.html)) In 5.2 the Glare type is a node *input* with values `Bloom, Ghosts, Streaks, Fog Glow, Simple Star, Sun Beams, Kernel`, and the scene compositor is `scene.compositing_node_group` **[verified locally]**. Scripts from before 4.x that set `glare_type` no longer work.

## 7. The two known import problems

These were reported by commenters on the model page. The model was not downloaded (project rule), so the exact contents of its materials were **not inspected**. What follows is the mechanism, verified from MMD Tools' source and the Blender docs, together with fixes that work whichever variant applies.

### 7a. Eyes vanish or look squinted ("颜2")

**What it is (partly inference).** "颜2" ("face 2") is, judging by the name and the reported symptom, a second face material: an overlay layer just in front of the eyes, carrying alternate expression drawings. Its visibility at rest depends on its material alpha being 0 or its texture alpha being cut out, and a **material morph** switches it on. The PMX format applies material morphs only when the morph is driven. In MMD Tools, morphs take effect only after **Model Setup → Assembly → Morph (Bind)**, which is the `mmd_tools.morph_slider_setup` operator with type `BIND` ([model_setup.py](https://github.com/MMD-Blender/blender_mmd_tools/blob/main/mmd_tools/panels/sidebar/model_setup.py)).

**How Blender ends up showing it.** If anything forces that overlay's alpha to 1, the alternate (closed or squinting) eye drawing covers the real eyes:
- MMD Tools' **"Show Transparent Material"** button (`toggle_transparent_materials`, action SHOW) literally sets `Alpha = 1.0` on every material ([operators/material.py](https://github.com/MMD-Blender/blender_mmd_tools/blob/main/mmd_tools/operators/material.py)).
- A replacement toon shader that ignores the MMD alpha also does it.
- So does an exporter or converter that drops the texture alpha.

**Fix.**
1. In the Material list, find 颜2. Press **"Restore"** (`toggle_transparent_materials` RESTORE, which reruns `update_alpha()` from the PMX value), or set its MMD alpha to 0.
2. In any custom material, wire alpha through as described in Section 3, step 2.
3. If you never need the alternate expressions, select the 颜2 faces by material in Edit Mode and hide them, or delete them in your local working copy. If you need them, Bind morphs and drive the material morph instead.

### 7b. Dark patches on cheeks and forehead (Dithered → Blended)

**Verified facts.**
- MMD Tools sets **every** material to `blend_method = "HASHED"` on import ([core/material.py, `update_alpha`](https://github.com/MMD-Blender/blender_mmd_tools/blob/main/mmd_tools/core/material.py)).
- In Blender 5.2 that legacy property maps to `surface_render_method = "DITHERED"`, and setting `"BLEND"` gives `"BLENDED"` **[verified locally]**.
- The manual says Dithered is "compatible with render passes and raytracing… also known as deferred rendering". Blended is "incompatible with render passes and raytracing… forward rendering", sorts per object, and has a Transparency Overlap option. ([EEVEE material settings](https://docs.blender.org/manual/en/latest/render/eevee/material_settings.html))
- In 4.2, Blended materials stopped appearing in reflections. ([4.2 notes](https://developer.blender.org/docs/release_notes/4.2/eevee/))

**Mechanism (inference from those facts).** The blush and face-shading decal layers sit a hair above the skin, and so do the eye-area overlays. Under Dithered they are deferred surfaces: they write depth and take part in screen-space ray tracing, Fast GI/AO and shadow maps. The near-coplanar layer then occludes or shadows the skin underneath, which shows up as dark blotches, and partial alpha also turns into dither noise. Under Blended they are forward-composited on top of the finished skin, so they cannot occlude it. Separately, 5.3 fixed a Dithered artifact ("Dithered transparency no longer shows line artifacts when slightly further from origin", [5.3 notes](https://developer.blender.org/docs/release_notes/5.3/eevee/)). 5.2 still has that bug.

**Fix.**
1. Material → Settings → **Render Method: Blended** on the face overlay materials (blush, 颜2, eye highlights, any semi-transparent face layer). Keep the opaque skin on Dithered, which handles opaque sorting correctly either way.
2. Turn off shadow casting for those overlays. Since 4.2 this is Object > Visibility > Ray Visibility > Shadow, plus the material's Transparent Shadows option.
3. If two Blended layers overlap in the wrong order, untick **Transparency Overlap**, or move them to separate objects so per-object sorting applies.
4. Keep Fast GI and AO off for the character.

## 8. What carries over to the later real-time viewer

| Technique | Carries over? |
|---|---|
| Ramp/toon-texture shading from N·L, tinted shadow colour | Yes. This is the standard toon shader in every engine. |
| Inverted-hull outlines (Solidify / MMD edge data) | Yes. This is the standard real-time outline method. |
| Facing-ratio rim, emission emblem, matcap (sphere) highlights | Yes |
| Custom face normals | Yes. Baked into the mesh. |
| Light/shadow linking | Partly. Most engines have light layers or culling masks. |
| Glare Bloom | Yes, as the engine's post-process bloom. Threshold and intensity settings map across. |
| Standard view transform | Yes. Use no tonemapping or a neutral one. |
| Blended vs Dithered overlay fix | Yes, as alpha-blended vs alpha-tested materials with render-queue ordering. |
| Line Art, the Raycast node, Shader-to-RGB-specific quirks | No. Line Art is a CPU offline modifier. Raycast becomes a depth-buffer rim in an engine. |

## Could not determine

- What the reference video (YouTube Shorts `6Cf1tnG-wVA`) actually uses. A video cannot be inspected, and the shader or effects used there are not stated in any source checked. The recipe above comes from the described look.
- The model's actual material list, 颜2's PMX alpha value, and which morph drives it. The model was deliberately not downloaded, so Section 7 explains the mechanism and gives fixes for every variant.
- Whether the dark patches come mainly from screen-space GI/AO or from shadow-map self-shadowing. Both are removed by the Blended + no-shadow fix.
- Whether Goo Engine has a current Apple Silicon build (Patreon-gated).
- Whether MMD Tools 4.5.14 has been tested on Blender 5.3. It is listed as "4.2 LTS and newer", and its code handles 5.0+ engine names.
