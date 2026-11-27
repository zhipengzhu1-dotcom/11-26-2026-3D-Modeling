"""PROTOTYPE (throwaway). Her settled toon look (issue 16: round 11 + subB1's thin outlines) for animated,
moving-camera clips. Ported from look.py on the unmerged branch prototype/toon-look, minus everything that
only made sense for stills (her smile, the stage plate, the contact ellipse, the fixed cameras, the ID pass).

Run only inside Blender. Settings come from look_params.json beside this file; nothing derived from the model
is stored here.

    import toon_look
    toon_look.apply(scene, [mesh1, mesh2, mesh3], camera)          # after import and camera, before rendering

It makes the materials (once per source material, shared by every figure), the outline shells, the lights,
the world, the colour management, the compositor (bloom, diffusion, saturation) and, unless floor=False,
a light floor with a faint grid and a crisp shadow that falls only on the floor.
"""
import json
import math
import os
import re
import sys

sys.dont_write_bytecode = True

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

GROUPS = {
    "skin": ["颜", "肌", "足"],
    "hair": ["前髮", "髮", "髮+"],
    "dress": ["体", "裙", "裙2", "裙内", "裙2内", "裙2+", "裙2内+", "裙饰", "裙饰2", "饰", "饰2"],
    "sleeve": ["袖"],
    "iris": ["瞳"],
}
EYE_MATS = {"目", "瞳", "目光", "目光2", "白目", "星目", "口舌", "齿", "睫眉"}
GLOW_MATS = {"宝石", "结晶", "麦克风1宝石"}
OVERLAYS = {"颜2", "照れ", "目光", "目光2", "星目"}


def load_params(path=None):
    with open(path or os.path.join(HERE, "look_params.json"), encoding="utf-8") as f:
        return json.load(f)


def lin(c):
    return [((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c[:3]]


def base_name(name):
    """'颜.002' -> '颜' (each extra import of her suffixes her material names)."""
    return re.sub(r"\.\d{3}$", "", name)


def group_of(name):
    for g, names in GROUPS.items():
        if name in names:
            return g
    return "other"


def base_tex(m):
    n = m.node_tree.nodes.get("mmd_base_tex") if m.node_tree else None
    return n.image if n is not None else None


def sphere_tex(m):
    n = m.node_tree.nodes.get("mmd_sphere_tex") if m.node_tree else None
    return n.image if n is not None and n.image else None


def is_overlay(m):
    """Layers on top of another surface. Under Dithered they leave a dark lace patch on her face; Blended fixes it."""
    img = base_tex(m)
    return (base_name(m.name) in OVERLAYS or m.mmd_material.alpha < 0.999
            or (img is not None and img.alpha_mode != "NONE"))


def alpha_chain(nt, img_out, mmd_alpha):
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = mmd_alpha
    nt.links.new(img_out, mul.inputs[0])
    return mul.outputs[0]


def soft_alpha(nt, img, radius, taps, gain):
    """Average the hair-shine texture alpha over a ring of UV offsets (joins its dashes; image untouched)."""
    uv = nt.nodes.new("ShaderNodeTexCoord")
    acc = None
    pts = [(0.0, 0.0)] + [(radius * math.cos(2 * math.pi * k / taps) * r, radius * math.sin(2 * math.pi * k / taps) * r)
                          for r in (0.5, 1.0) for k in range(taps)]
    for dx, dy in pts:
        add = nt.nodes.new("ShaderNodeVectorMath")
        add.operation = "ADD"
        add.inputs[1].default_value = (dx, dy, 0)
        nt.links.new(uv.outputs["UV"], add.inputs[0])
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = img
        nt.links.new(add.outputs[0], t.inputs[0])
        if acc is None:
            acc = t.outputs["Alpha"]
            continue
        m = nt.nodes.new("ShaderNodeMath")
        m.operation = "ADD"
        nt.links.new(acc, m.inputs[0])
        nt.links.new(t.outputs["Alpha"], m.inputs[1])
        acc = m.outputs[0]
    sc = nt.nodes.new("ShaderNodeMath")
    sc.operation = "MULTIPLY"
    sc.use_clamp = True
    sc.inputs[1].default_value = gain / len(pts)
    nt.links.new(acc, sc.inputs[0])
    return sc.outputs[0]


def toon_material(src, P):
    """Shader-to-RGB toon material from the model's own diffuse texture (texture untouched). As look.py."""
    T = P["toon"]
    name = base_name(src.name)
    g = group_of(name)
    gk = g if g in ("skin", "hair") else "cloth"
    m = bpy.data.materials.new("toon_" + name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    img = base_tex(src)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    mmd_a = src.mmd_material.alpha

    diff = nt.nodes.new("ShaderNodeBsdfDiffuse")
    diff.inputs["Color"].default_value = (1, 1, 1, 1)
    s2r = nt.nodes.new("ShaderNodeShaderToRGB")
    nt.links.new(diff.outputs[0], s2r.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    pos, w = T["ramp_pos"], T["ramp_width"]
    ramp.color_ramp.interpolation = "EASE" if w > 0.1 else "LINEAR"
    e = ramp.color_ramp.elements
    e[0].position, e[1].position = max(0.0, pos - w / 2), min(1.0, pos + w / 2)
    e[0].color = (*lin(T["shadow"][gk]), 1)
    e[1].color = (*lin(T.get("lit", [1, 1, 1])), 1)
    fac = s2r.outputs["Color"]
    AO = T.get("ao", {}).get(g) or T.get("ao", {}).get(gk)
    if AO:  # ambient occlusion pushes crevices and undersides into the shadow band (stands in for cast shadows)
        bw = nt.nodes.new("ShaderNodeRGBToBW")
        nt.links.new(fac, bw.inputs[0])
        ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
        ao.inputs["Distance"].default_value = AO["distance"]
        ao.samples = 16
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = AO["lo"]
        mr.inputs["From Max"].default_value = AO["hi"]
        nt.links.new(ao.outputs["AO"], mr.inputs["Value"])
        mn = nt.nodes.new("ShaderNodeMath")
        mn.operation = "MINIMUM"
        nt.links.new(bw.outputs[0], mn.inputs[0])
        nt.links.new(mr.outputs["Result"], mn.inputs[1])
        fac = mn.outputs[0]
    nt.links.new(fac, ramp.inputs["Fac"])

    mulc = nt.nodes.new("ShaderNodeMix")
    mulc.data_type = "RGBA"
    mulc.blend_type = "MULTIPLY"
    mulc.inputs["Factor"].default_value = 1.0
    texcol = tex.outputs["Color"]
    TS = T.get("teal_shift")
    if TS and gk == "cloth":  # recolour only the dark teal panels: a colour key on the texture
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        sep.mode = "HSV"
        nt.links.new(texcol, sep.inputs[0])

        def cmp(sock, op, v):
            n = nt.nodes.new("ShaderNodeMath")
            n.operation = op
            n.inputs[1].default_value = v
            nt.links.new(sock, n.inputs[0])
            return n.outputs[0]

        def mul(a, b):
            n = nt.nodes.new("ShaderNodeMath")
            n.operation = "MULTIPLY"
            nt.links.new(a, n.inputs[0])
            nt.links.new(b, n.inputs[1])
            return n.outputs[0]
        h, sat, val = sep.outputs[0], sep.outputs[1], sep.outputs[2]
        mask = mul(mul(cmp(h, "GREATER_THAN", TS["h_lo"]), cmp(h, "LESS_THAN", TS["h_hi"])),
                   mul(cmp(sat, "GREATER_THAN", TS["s_lo"]), cmp(val, "LESS_THAN", TS["v_hi"])))
        hsv = nt.nodes.new("ShaderNodeHueSaturation")
        hsv.inputs["Hue"].default_value = 0.5 + TS["hue"]
        hsv.inputs["Saturation"].default_value = TS["sat"]
        hsv.inputs["Value"].default_value = TS["val"]
        nt.links.new(texcol, hsv.inputs["Color"])
        tm = nt.nodes.new("ShaderNodeMix")
        tm.data_type = "RGBA"
        nt.links.new(mask, tm.inputs["Factor"])
        nt.links.new(texcol, tm.inputs[6])
        nt.links.new(hsv.outputs[0], tm.inputs[7])
        texcol = tm.outputs[2]
    nt.links.new(texcol, mulc.inputs[6])
    nt.links.new(ramp.outputs["Color"], mulc.inputs[7])
    col = mulc.outputs[2]

    gain = T["gain"].get(g, T["gain"].get(gk, [1, 1, 1]))
    if gain != [1, 1, 1]:
        gm = nt.nodes.new("ShaderNodeMix")
        gm.data_type = "RGBA"
        gm.blend_type = "MULTIPLY"
        gm.inputs["Factor"].default_value = 1.0
        nt.links.new(col, gm.inputs[6])
        gm.inputs[7].default_value = (*gain, 1)
        col = gm.outputs[2]

    sph = sphere_tex(src)
    stype = src.mmd_material.sphere_texture_type
    if sph is not None and T["sphere"] > 0 and stype in ("1", "2"):
        tc = nt.nodes.new("ShaderNodeTexCoord")
        vt = nt.nodes.new("ShaderNodeVectorTransform")
        vt.vector_type, vt.convert_from, vt.convert_to = "NORMAL", "WORLD", "CAMERA"
        nt.links.new(tc.outputs["Normal"], vt.inputs[0])
        mp = nt.nodes.new("ShaderNodeVectorMath")
        mp.operation = "MULTIPLY_ADD"
        mp.inputs[1].default_value = (0.5, 0.5, 0.5)
        mp.inputs[2].default_value = (0.5, 0.5, 0.5)
        nt.links.new(vt.outputs[0], mp.inputs[0])
        st = nt.nodes.new("ShaderNodeTexImage")
        st.image = sph
        nt.links.new(mp.outputs[0], st.inputs[0])
        sm = nt.nodes.new("ShaderNodeMix")
        sm.data_type = "RGBA"
        sm.blend_type = "ADD" if stype == "2" else "MULTIPLY"
        sm.inputs["Factor"].default_value = T["sphere"]
        nt.links.new(col, sm.inputs[6])
        nt.links.new(st.outputs["Color"], sm.inputs[7])
        col = sm.outputs[2]

    R = T["rim"]
    if R["strength"] > 0 and name not in EYE_MATS:
        lw = nt.nodes.new("ShaderNodeLayerWeight")
        lw.inputs["Blend"].default_value = R["width"]
        rr = nt.nodes.new("ShaderNodeValToRGB")
        rr.color_ramp.elements[0].position = R.get("lo", 0.5)
        rr.color_ramp.elements[1].position = R.get("hi", 0.75)
        nt.links.new(lw.outputs["Facing"], rr.inputs["Fac"])
        rm = nt.nodes.new("ShaderNodeMix")
        rm.data_type = "RGBA"
        rm.blend_type = "ADD"
        nt.links.new(rr.outputs["Color"], rm.inputs["Factor"])
        rm.inputs[7].default_value = (*[c * R["strength"] for c in lin(R["color"])], 1)
        nt.links.new(col, rm.inputs[6])
        col = rm.outputs[2]

    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(col, em.inputs["Color"])
    em.inputs["Strength"].default_value = (T["emblem"] if name in GLOW_MATS else T.get("eye_glow", {}).get(name, 1.0))
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    HS = T.get("hairshine")
    shine = HS and name == "髮+"
    a_src = soft_alpha(nt, img, HS["radius"], HS["taps"], HS["gain"]) if shine else tex.outputs["Alpha"]
    if shine:
        em.inputs["Strength"].default_value = HS.get("strength", 1.0)
    nt.links.new(alpha_chain(nt, a_src, mmd_a), mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    m.surface_render_method = "BLENDED" if is_overlay(src) else "DITHERED"
    m.use_backface_culling = src.use_backface_culling  # inner skirt layers must stay culled
    return m


def outline_material(src, O):
    """Inverted-hull outline coloured from the surface texture (lighter and more saturated, not black)."""
    m = bpy.data.materials.new("outline_" + base_name(src.name))
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = base_tex(src)
    hs = nt.nodes.new("ShaderNodeHueSaturation")
    hs.inputs["Saturation"].default_value = O["saturate"]
    hs.inputs["Value"].default_value = O["darken"]
    nt.links.new(tex.outputs["Color"], hs.inputs["Color"])
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(hs.outputs[0], em.inputs["Color"])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    a = 0.0 if (base_name(src.name) in EYE_MATS or is_overlay(src)) else src.mmd_material.alpha
    nt.links.new(alpha_chain(nt, tex.outputs["Alpha"], a), mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    m.use_backface_culling = True
    m.surface_render_method = "DITHERED"
    return m


def display_to_emission(rgb, P):
    """Linear emission that lands on the wanted displayed sRGB colour after the look's exposure and gamma."""
    ex, ga = P.get("exposure", 0.0), P.get("gamma", 1.0)
    return [x / 2 ** ex for x in lin([c ** ga for c in rgb])]


def world(scene, P):
    w = bpy.data.worlds.new("toon_world")
    scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    b1 = nt.nodes.new("ShaderNodeBackground")  # what lights her: a bright white fill
    b1.inputs[0].default_value = (*lin(P["world_light"]), 1)
    b1.inputs[1].default_value = P["world_strength"]
    b2 = nt.nodes.new("ShaderNodeBackground")  # what the camera sees behind her
    b2.inputs[0].default_value = (*display_to_emission(P["backdrop"], P), 1)
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(b1.outputs[0], mix.inputs[1])
    nt.links.new(b2.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    if hasattr(w, "use_sun_shadow"):
        w.use_sun_shadow = False
    return w


def compositor(scene, P):
    ng = bpy.data.node_groups.new("toon_comp", "CompositorNodeTree")
    scene.compositing_node_group = ng
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl = ng.nodes.new("CompositorNodeRLayers")
    out = ng.nodes.new("NodeGroupOutput")
    cur = rl.outputs["Image"]
    B = P.get("bloom")
    if B:
        gl = ng.nodes.new("CompositorNodeGlare")
        gl.inputs["Type"].default_value = "Bloom"
        gl.inputs["Quality"].default_value = "High"
        gl.inputs["Threshold"].default_value = B["threshold"]
        gl.inputs["Smoothness"].default_value = B["smooth"]
        gl.inputs["Strength"].default_value = B["strength"]
        gl.inputs["Size"].default_value = B["size"]
        ng.links.new(cur, gl.inputs["Image"])
        cur = gl.outputs["Image"]
    D = P.get("diffusion")
    if D:  # soft-focus glow: a blurred copy screened over the image. Size is in pixels at the 540x960 stills;
        # scale it with the output height so the softness looks the same at any resolution.
        h = scene.render.resolution_y * scene.render.resolution_percentage / 100
        s = max(1, round(D["size"] * h / 960))
        bl = ng.nodes.new("CompositorNodeBlur")
        bl.inputs["Size"].default_value = (s, s)
        ng.links.new(cur, bl.inputs["Image"])
        mx = ng.nodes.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        mx.blend_type = "SCREEN"
        mx.inputs["Factor"].default_value = D["factor"]
        ng.links.new(cur, mx.inputs[6])
        ng.links.new(bl.outputs["Image"], mx.inputs[7])
        cur = mx.outputs[2]
    S = P.get("huesat")
    if S:
        hs = ng.nodes.new("CompositorNodeHueSat")
        hs.inputs["Saturation"].default_value = S["sat"]
        hs.inputs["Value"].default_value = S["value"]
        ng.links.new(cur, hs.inputs["Image"])
        cur = hs.outputs["Image"]
    ng.links.new(cur, out.inputs[0])
    scene.render.use_compositing = True


def floor_material(P):
    """Light floor with a faint grid. Lit only by the floor shadow sun (light linking); a hard threshold on that
    light turns her shadow into one crisp flat tone, like the cel shading."""
    F = P["floor"]
    m = bpy.data.materials.new("toon_floor")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])

    def line(sock):  # 1 on a grid line, 0 between
        a = nt.nodes.new("ShaderNodeMath")
        a.operation = "PINGPONG"  # distance to the nearest multiple of line_every, times 1
        a.inputs[1].default_value = F["line_every"] / 2
        nt.links.new(sock, a.inputs[0])
        b = nt.nodes.new("ShaderNodeMath")
        b.operation = "LESS_THAN"
        b.inputs[1].default_value = F["line_width"] / 2
        nt.links.new(a.outputs[0], b.inputs[0])
        return b.outputs[0]
    mx = nt.nodes.new("ShaderNodeMath")
    mx.operation = "MAXIMUM"
    nt.links.new(line(sep.outputs["X"]), mx.inputs[0])
    nt.links.new(line(sep.outputs["Y"]), mx.inputs[1])
    base = nt.nodes.new("ShaderNodeMix")
    base.data_type = "RGBA"
    nt.links.new(mx.outputs[0], base.inputs["Factor"])
    base.inputs[6].default_value = (*display_to_emission(F["color"], P), 1)
    base.inputs[7].default_value = (*display_to_emission(F["line_color"], P), 1)

    diff = nt.nodes.new("ShaderNodeBsdfDiffuse")
    diff.inputs["Color"].default_value = (1, 1, 1, 1)
    s2r = nt.nodes.new("ShaderNodeShaderToRGB")
    nt.links.new(diff.outputs[0], s2r.inputs[0])
    bw = nt.nodes.new("ShaderNodeRGBToBW")
    nt.links.new(s2r.outputs["Color"], bw.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")  # shadowed floor gets world light only; lit floor gets the sun too
    ramp.color_ramp.interpolation = "CONSTANT"
    e = ramp.color_ramp.elements
    e[0].position = 0.0
    e[0].color = (*[a / b for a, b in zip(lin(F["shadow_color"]), lin(F["color"]))], 1)
    e[1].position = F["threshold"]
    e[1].color = (1, 1, 1, 1)
    nt.links.new(bw.outputs[0], ramp.inputs["Fac"])
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    nt.links.new(base.outputs[2], mul.inputs[6])
    nt.links.new(ramp.outputs["Color"], mul.inputs[7])
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(mul.outputs[2], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def make_floor(scene, P, camera, _unused=None):
    F = P["floor"]
    me = bpy.data.meshes.new("toon_floor")
    s = F["size"] / 2
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    floor = bpy.data.objects.new("toon_floor", me)
    scene.collection.objects.link(floor)
    me.materials.append(floor_material(P))

    # Floor shadow sun: casts shadows, lights only the floor (light linking), so nothing of it reaches her.
    S = F["shadow_sun"]
    recv = bpy.data.collections.new("toon_floor_receivers")  # not linked to the scene: a linking set only
    recv.objects.link(floor)
    sun = bpy.data.objects.new("toon_floor_sun", bpy.data.lights.new("toon_floor_sun", "SUN"))
    sun.data.energy = S["energy"]
    sun.data.angle = math.radians(S["angle"])
    sun.data.use_shadow = True
    if hasattr(sun.data, "shadow_maximum_resolution"):
        sun.data.shadow_maximum_resolution = 0.001
    fwd = Vector((0, 1, 0))
    if camera is not None:  # light from the camera's side, so her shadow falls behind her, a little to one side
        f = camera.matrix_world.to_3x3() @ Vector((0, 0, -1))
        f.z = 0
        if f.length > 1e-6:
            fwd = f.normalized()
    right = Vector((fwd.y, -fwd.x, 0))
    az, el = math.radians(S["azimuth_from_camera"]), math.radians(S["elevation"])
    d = (fwd * math.cos(az) + right * math.sin(az)) * math.cos(el) + Vector((0, 0, -math.sin(el)))
    sun.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(sun)
    sun.light_linking.receiver_collection = recv
    return floor, sun, recv


def apply(scene, mesh_objects, camera=None, floor=True, samples=16, params=None):
    """Give every figure's Visible Mesh the settled look and set up the scene around it.

    scene: the scene to render. mesh_objects: each figure's Visible Mesh (the MMD mesh object, already imported,
    armature-deformed; any number of copies). camera: the scene camera, already placed; used only to aim the floor
    shadow away from it at apply time. floor: make the floor (False for the pinned clip). samples: EEVEE samples.
    Returns a dict of what it made."""
    P = params or load_params()
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = samples
    scene.render.filter_size = 1.5
    scene.render.film_transparent = False
    vs = scene.view_settings
    vs.view_transform = P["view_transform"]
    vs.look = "None"
    vs.exposure = P.get("exposure", 0.0)
    vs.gamma = P.get("gamma", 1.0)
    world(scene, P)

    S = P["sun"]
    key = bpy.data.objects.new("toon_key", bpy.data.lights.new("toon_key", "SUN"))
    key.data.energy = S["energy"]
    key.data.color = lin(S["color"])
    key.data.angle = math.radians(S["angle"])
    key.data.use_shadow = S["shadow"]
    key.rotation_euler = [math.radians(x) for x in S["rot"]]
    scene.collection.objects.link(key)

    # One toon and one outline material per source material, shared by every figure.
    toon, outline = {}, {}
    O = P.get("outline")
    done_data = set()
    for ob in mesh_objects:
        me = ob.data
        if me.name not in done_data:
            done_data.add(me.name)
            srcs = list(me.materials)
            for i, src in enumerate(srcs):
                k = base_name(src.name)
                if k not in toon:
                    toon[k] = toon_material(src, P)
                    if O:
                        outline[k] = outline_material(src, O)
                me.materials[i] = toon[k]
            if O:
                for src in srcs:
                    me.materials.append(outline[base_name(src.name)])
            me["toon_n_slots"] = len(srcs)
        if O and "toon_outline" not in ob.modifiers:
            # Inverted hull. Added last, so it runs after the armature and shape keys: it follows the animation.
            sol = ob.modifiers.new("toon_outline", "SOLIDIFY")
            sol.thickness = O["thickness"]
            sol.offset = 1.0
            sol.use_flip_normals = True
            sol.use_rim = False
            sol.use_even_offset = False
            sol.material_offset = me["toon_n_slots"]
            ob.visible_shadow = True

    made = {"key": key, "materials": len(toon)}
    if floor:
        made["floor"], made["floor_sun"], recv = make_floor(scene, P, camera, None)
        # The key sun skips the floor (a receiver set holding only the floor, marked EXCLUDE), so the floor's
        # light is world fill plus the floor sun and its threshold separates shadow from light cleanly.
        excl = bpy.data.collections.new("toon_key_receivers")
        excl.objects.link(made["floor"])
        key.light_linking.receiver_collection = excl
        excl.collection_objects[0].light_linking.link_state = "EXCLUDE"
    compositor(scene, P)
    return made
