"""PROTOTYPE, throwaway. Blender side of the toon-look prototype (question: what should she look like?).

Imports her model with MMD Tools, puts her in a few poses from the stage 1 dance, applies one look
(a JSON parameter set) and renders stills plus a flat material-ID pass used for colour measurement.

Run by run.py:  Blender -b --python look.py -- <pmx> <vmd> <params.json> <out_dir>
"""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

sys.dont_write_bytecode = True
SCALE = 0.08

# Region groups used for measurement (material names from the PMX).
GROUPS = {
    "skin": ["颜", "肌", "足"],
    "hair": ["前髮", "髮", "髮+"],
    "dress": ["体", "裙", "裙2", "裙内", "裙2内", "裙2+", "裙2内+", "裙饰", "裙饰2", "饰", "饰2"],
    "sleeve": ["袖"],
    "iris": ["瞳"],
}
ID_COLORS = {"skin": (1, 0, 0), "hair": (0, 0, 1), "dress": (0, 1, 0), "sleeve": (1, 1, 0),
             "iris": (1, 0, 1), "bg": (0, 0, 0), "other": (0.5, 0.5, 0.5)}
EYE_MATS = {"目", "瞳", "目光", "目光2", "白目", "星目", "口舌", "齿", "睫眉"}
GLOW_MATS = {"宝石", "结晶", "麦克风1宝石"}
OVERLAYS = {"颜2", "照れ", "目光", "目光2", "星目"}

# Shots: (name, VMD frame, kind). Close-ups match the reference framing (head to waist, from slightly above).
SHOTS = [("close1", 1, "close"), ("close2", 211, "close"), ("close3", 781, "close"), ("full", 1, "full")]


def lin(c):
    return [((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c[:3]]


def group_of(name):
    for g, names in GROUPS.items():
        if name in names:
            return g
    return "other"


def enable_mmd():
    import addon_utils
    for m in addon_utils.modules():
        if m.__name__.endswith("mmd_tools"):
            addon_utils.enable(m.__name__, default_set=False)
            return
    raise SystemExit("MMD Tools missing")


def load(pmx, vmd):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    enable_mmd()
    bpy.ops.mmd_tools.import_model(filepath=pmx, scale=SCALE, types={"MESH", "ARMATURE", "MORPHS"},
                                   log_level="ERROR")
    root = next(o for o in bpy.data.objects if getattr(o, "mmd_type", "") == "ROOT")
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.mmd_tools.import_vmd(filepath=vmd, scale=SCALE, margin=0, bone_mapper="PMX", use_pose_mode=False,
                                 update_scene_settings=True, log_level="ERROR")
    mesh = next(o for o in bpy.data.objects if o.type == "MESH" and getattr(o, "mmd_type", "NONE") == "NONE")
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    # Known quirk: transparent face overlays import as Dithered and leave a dark lace patch.
    for m in mesh.data.materials:
        if is_overlay(m):
            m.surface_render_method = "BLENDED"
    return mesh, arm


def is_overlay(m):
    """Layers that sit on top of another surface (alpha-textured or alpha < 1). Under Dithered they
    render black where they overlap the surface below (the dark-patch quirk), so they go Blended."""
    img = base_tex(m)
    return m.name in OVERLAYS or m.mmd_material.alpha < 0.999 or (img is not None and img.alpha_mode != "NONE")


def base_tex(m):
    n = m.node_tree.nodes.get("mmd_base_tex")
    return n.image if n is not None else None


def sphere_tex(m):
    n = m.node_tree.nodes.get("mmd_sphere_tex")
    return n.image if n is not None and n.image else None


def alpha_chain(nt, img_node, mmd_alpha):
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = mmd_alpha
    nt.links.new(img_node.outputs["Alpha"] if hasattr(img_node, "outputs") else img_node, mul.inputs[0])
    return mul.outputs[0]


def soft_alpha(nt, img, radius, taps, gain):
    """Average the texture alpha over a ring of UV offsets: joins the dashed hair-shine strokes of 髮+ into a soft
    band and fades its pin-point specks (the dotted look), without touching the image."""
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
    """Shader to RGB toon material built from the model's own diffuse texture (texture untouched)."""
    T = P["toon"]
    g = group_of(src.name)
    gk = g if g in ("skin", "hair") else "cloth"
    m = bpy.data.materials.new("toon_" + src.name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    img = base_tex(src)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    mmd_a = 0.0 if src.name in P.get("hide", []) else src.mmd_material.alpha

    diff = nt.nodes.new("ShaderNodeBsdfDiffuse")
    diff.inputs["Color"].default_value = (1, 1, 1, 1)
    s2r = nt.nodes.new("ShaderNodeShaderToRGB")
    nt.links.new(diff.outputs[0], s2r.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    pos, w = T["ramp_pos"], T["ramp_width"]
    ramp.color_ramp.interpolation = "EASE" if w > 0.1 else "LINEAR"
    e = ramp.color_ramp.elements
    e[0].position, e[1].position = max(0.0, pos - w / 2), min(1.0, pos + w / 2)
    sh = lin(T["shadow"][gk])
    e[0].color = (*sh, 1)
    e[1].color = (*lin(T.get("lit", [1, 1, 1])), 1)
    fac = s2r.outputs["Color"]
    AO = T.get("ao", {}).get(g) or T.get("ao", {}).get(gk)
    if AO:  # ambient occlusion pushes crevices and undersides into the shadow band (hair undersides)
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
    if TS and gk == "cloth":  # recolour only the dark teal panels: a colour key on the texture, no image edited
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        sep.mode = "HSV"
        nt.links.new(texcol, sep.inputs[0])

        def cmp(sock, op, v):
            m = nt.nodes.new("ShaderNodeMath")
            m.operation = op
            m.inputs[1].default_value = v
            nt.links.new(sock, m.inputs[0])
            return m.outputs[0]

        def mul(a, b):
            m = nt.nodes.new("ShaderNodeMath")
            m.operation = "MULTIPLY"
            nt.links.new(a, m.inputs[0])
            nt.links.new(b, m.inputs[1])
            return m.outputs[0]
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
        gm.inputs[7].default_value = (*gain, 1)  # linear multiplier
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
    if R["strength"] > 0 and src.name not in EYE_MATS:
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
    em.inputs["Strength"].default_value = (T["emblem"] if src.name in GLOW_MATS
                                           else T.get("eye_glow", {}).get(src.name, 1.0))
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    HS = T.get("hairshine")
    a_src = soft_alpha(nt, img, HS["radius"], HS["taps"], HS["gain"]) if (HS and src.name == "髮+") else tex
    if HS and src.name == "髮+":
        em.inputs["Strength"].default_value = HS.get("strength", 1.0)
    nt.links.new(alpha_chain(nt, a_src, mmd_a), mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    m.surface_render_method = "BLENDED" if is_overlay(src) else "DITHERED"
    m.use_backface_culling = src.use_backface_culling  # single-sided PMX materials: inner skirt layers must stay culled
    return m


def outline_material(src, O):
    m = bpy.data.materials.new("outline_" + src.name)
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
    a = 0.0 if (src.name in EYE_MATS or is_overlay(src)) else src.mmd_material.alpha
    nt.links.new(alpha_chain(nt, tex, a), mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    m.use_backface_culling = True
    m.surface_render_method = "DITHERED"
    return m


def id_material(src):
    m = bpy.data.materials.new("id_" + src.name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*ID_COLORS[group_of(src.name)], 1)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    img = base_tex(src)
    if img is not None:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        a = alpha_chain(nt, tex, src.mmd_material.alpha)
    else:
        v = nt.nodes.new("ShaderNodeValue")
        v.outputs[0].default_value = src.mmd_material.alpha
        a = v.outputs[0]
    step = nt.nodes.new("ShaderNodeMath")
    step.operation = "GREATER_THAN"
    step.inputs[1].default_value = 0.5
    nt.links.new(a, step.inputs[0])
    nt.links.new(step.outputs[0], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    m.surface_render_method = "BLENDED" if is_overlay(src) else "DITHERED"
    m.use_backface_culling = src.use_backface_culling
    return m


def world(scene, light_rgb, strength, backdrop_rgb, exposure=0.0, gamma=1.0):
    # backdrop_rgb is the wanted displayed colour; undo exposure and view gamma so it lands there.
    backdrop_rgb = [x / 2 ** exposure for x in lin([c ** gamma for c in backdrop_rgb])]
    w = bpy.data.worlds.new("look_world")
    scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    b1 = nt.nodes.new("ShaderNodeBackground")
    b1.inputs[0].default_value = (*lin(light_rgb), 1)
    b1.inputs[1].default_value = strength
    b2 = nt.nodes.new("ShaderNodeBackground")
    b2.inputs[0].default_value = (*backdrop_rgb, 1)
    b2.inputs[1].default_value = 1.0
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(b1.outputs[0], mix.inputs[1])
    nt.links.new(b2.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    if hasattr(w, "use_sun_shadow"):
        w.use_sun_shadow = False
    return w


def set_in(node, keys, val):
    for k in keys:
        try:
            node.inputs[k].default_value = val
            return
        except Exception:
            continue


def compositor(scene, P, bg_image=None):
    ng = bpy.data.node_groups.new("look_comp", "CompositorNodeTree")
    scene.compositing_node_group = ng
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl = ng.nodes.new("CompositorNodeRLayers")
    out = ng.nodes.new("NodeGroupOutput")
    cur = rl.outputs["Image"]
    BG = P.get("stage")
    if BG and bg_image is not None:  # generated stage plate, blurred like a depth-of-field background
        im = ng.nodes.new("CompositorNodeImage")
        im.image = bg_image
        bl = ng.nodes.new("CompositorNodeBlur")
        set_in(bl, ("Size", 0), (BG["blur"], BG["blur"]))
        try:
            bl.inputs["Type"].default_value = "Gaussian"
        except Exception:
            pass
        ng.links.new(im.outputs["Image"], bl.inputs["Image"])
        ao = ng.nodes.new("CompositorNodeAlphaOver")
        ng.links.new(bl.outputs["Image"], ao.inputs[0 if "Background" not in ao.inputs else "Background"])
        ng.links.new(cur, ao.inputs[1 if "Foreground" not in ao.inputs else "Foreground"])
        cur = ao.outputs["Image"]
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
    if D:  # soft-focus glow: a blurred copy screened over the image (the MMD "diffusion" effect)
        bl = ng.nodes.new("CompositorNodeBlur")
        set_in(bl, ("Size", 0), (D["size"], D["size"]))
        ng.links.new(cur, bl.inputs["Image"])
        mx = ng.nodes.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        mx.blend_type = "SCREEN"
        mx.inputs["Factor"].default_value = D["factor"]
        ng.links.new(cur, mx.inputs[6])
        ng.links.new(bl.outputs["Image"], mx.inputs[7])
        cur = mx.outputs[2]
    H = P.get("haze")
    if H:
        mx = ng.nodes.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        mx.blend_type = "MIX"
        mx.inputs["Factor"].default_value = H["factor"]
        ng.links.new(cur, mx.inputs[6])
        mx.inputs[7].default_value = (*lin(H["color"]), 1)
        cur = mx.outputs[2]
    S = P.get("huesat")
    if S:
        hs = ng.nodes.new("CompositorNodeHueSat")
        hs.inputs["Saturation"].default_value = S["sat"]
        hs.inputs["Value"].default_value = S["value"]
        ng.links.new(cur, hs.inputs["Image"])
        cur = hs.outputs["Image"]
    ng.links.new(cur, out.inputs[0])


def stage_pixels(P, w, h, contact=None):
    """A warm stage plate made by code: vertical gradient, a floor band and soft bokeh discs (blurred later in the
    compositor), plus an optional soft contact shadow ellipse under her feet. Returns linear RGBA floats."""
    import numpy as np
    S = P["stage"]
    ex, ga = P.get("exposure", 0.0), P.get("gamma", 1.0)
    y = np.linspace(1, 0, h)[:, None, None]  # 1 at the top of the image
    top, bot = np.array(S["top"]), np.array(S["bottom"])
    img = bot + (top - bot) * y ** S.get("curve", 1.0)
    img = np.repeat(img, w, 1)
    fy = S.get("floor_y")
    if fy is not None:  # floor band (from the bottom), slightly lighter and cooler
        yy = np.linspace(1, 0, h)[:, None]
        fl = np.clip((fy - yy) / 0.02, 0, 1)[..., None]
        img = img * (1 - fl) + np.array(S["floor"]) * fl
    yy, xx = np.mgrid[0:h, 0:w]
    rng = np.random.default_rng(S.get("seed", 3))
    for (cx, cy, r, col, a) in S.get("bokeh", []):
        d = np.hypot(xx - cx * w, yy - (1 - cy) * h) / (r * w)
        m = np.clip((1 - d) / 0.08, 0, 1)[..., None] * a
        img = img * (1 - m) + np.array(col) * m
    for _ in range(S.get("specks", 0)):  # small bright bokeh
        cx, cy, r = rng.random(), rng.random() * 0.75 + 0.25, 0.012 + 0.02 * rng.random()
        d = np.hypot(xx - cx * w, yy - (1 - cy) * h) / (r * w)
        m = np.clip((1 - d) / 0.15, 0, 1)[..., None] * 0.55
        img = img * (1 - m) + np.array([1.0, 0.98, 0.93]) * m
    if contact is not None:
        (cx, cy, rx, ry), C = contact, S["contact"]
        d = np.hypot((xx - cx * w) / max(rx * w, 1), (yy - (1 - cy) * h) / max(ry * h, 1))
        m = np.clip((1 - d) / C.get("soft", 0.5), 0, 1)[..., None] * C["opacity"]
        img = img * (1 - m) + img * np.array(C["color"]) * m
    img = np.clip(img, 0, 1)
    lin_img = np.where(img > 0.04045, ((img ** ga + 0.055) / 1.055) ** 2.4, img ** ga / 12.92) / 2 ** ex
    out = np.concatenate([lin_img, np.ones((h, w, 1))], -1)[::-1]  # Blender images start at the bottom row
    return out.astype(np.float32).ravel()


def contact_ellipse(scene, cam, arm, P):
    """Screen position and size of a contact shadow on the floor (z = 0) under her feet."""
    from bpy_extras.object_utils import world_to_camera_view
    bpy.context.view_layer.update()  # the camera was just moved; its matrix must be current
    pts = [arm.matrix_world @ arm.pose.bones[b].head for b in ("足首.L", "足首.R", "足先EX.L", "足先EX.R")
           if b in arm.pose.bones]
    if not pts:
        return None
    c = sum(pts, Vector()) / len(pts)
    span = max(0.16, (pts[0] - pts[1]).length / 2 + 0.1) * P["stage"]["contact"].get("scale", 1.0)
    p0 = world_to_camera_view(scene, cam, Vector((c.x, c.y, 0)))
    px = world_to_camera_view(scene, cam, Vector((c.x + span, c.y, 0)))
    py = world_to_camera_view(scene, cam, Vector((c.x, c.y + span, 0)))
    return (p0.x, p0.y, abs(px.x - p0.x), max(abs(py.y - p0.y), 0.006))


def apply_morphs(mesh, M, keep):
    """Override face shape keys (her smile) for the still; the dance's own keys are put back afterwards."""
    sk = mesh.data.shape_keys
    if not M or sk is None:
        return
    if keep is not None:
        keep["action"] = sk.animation_data.action if sk.animation_data else None
        if sk.animation_data:
            sk.animation_data.action = None
    for k, v in M.items():
        if k in sk.key_blocks:
            sk.key_blocks[k].value = v


def frame_camera(scene, cam, arm, kind):
    head = arm.pose.bones.get("頭")
    hp = arm.matrix_world @ head.head
    cam.data.sensor_fit = "VERTICAL"
    cam.data.sensor_height = 24
    cam.data.lens = 50
    if kind == "close":
        target = Vector((hp.x, hp.y, hp.z - 0.13))
        d, elev = 1.55, math.radians(14)
    else:
        target = Vector((hp.x, hp.y, 0.82))
        d, elev = 4.2, math.radians(6)
    direction = Vector((0, -math.cos(elev), math.sin(elev)))
    cam.location = target + direction * d
    cam.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()


def main():
    a = sys.argv[sys.argv.index("--") + 1:]
    pmx, vmd, params_path, out = a[:4]
    with open(params_path, encoding="utf-8") as f:
        P = json.load(f)
    os.makedirs(out, exist_ok=True)
    mesh, arm = load(pmx, vmd)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = 540, 960
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    vs = scene.view_settings
    vs.view_transform = P["view_transform"]
    vs.look = P.get("look", "None")
    vs.exposure = P.get("exposure", 0.0)
    vs.gamma = P.get("gamma", 1.0)
    world(scene, P["world_light"], P["world_strength"], P["backdrop"], P.get("exposure", 0.0), P.get("gamma", 1.0))
    S = P["sun"]
    sun = bpy.data.objects.new("key", bpy.data.lights.new("key", "SUN"))
    sun.data.energy = S["energy"]
    sun.data.color = lin(S["color"])
    sun.data.angle = math.radians(S["angle"])
    sun.data.use_shadow = S["shadow"]
    sun.rotation_euler = [math.radians(x) for x in S["rot"]]
    scene.collection.objects.link(sun)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam

    originals = list(mesh.data.materials)
    if P["shading"] == "toon":
        toon = [toon_material(m, P) for m in originals]
        for i, m in enumerate(toon):
            mesh.data.materials[i] = m
    beauty = list(mesh.data.materials)
    O = P.get("outline")
    if O:
        for m in originals:
            mesh.data.materials.append(outline_material(m, O))
        sol = mesh.modifiers.new("outline", "SOLIDIFY")
        sol.thickness = O["thickness"]
        sol.offset = 1.0
        sol.use_flip_normals = True
        sol.use_rim = False
        sol.material_offset = len(originals)
    ids = [id_material(m) for m in originals]

    bg_image = None
    if P.get("stage"):
        bg_image = bpy.data.images.new("stage", 540, 960, alpha=True, float_buffer=True)
        scene.render.film_transparent = True
    if P.get("bloom") or P.get("haze") or P.get("huesat") or P.get("stage") or P.get("diffusion"):
        compositor(scene, P, bg_image)
    print("LOOK params", json.dumps(P, ensure_ascii=False))
    sk = mesh.data.shape_keys
    dance_keys = sk.animation_data.action if sk is not None and sk.animation_data else None
    for name, frame, kind in SHOTS:
        if dance_keys is not None:
            sk.animation_data.action = dance_keys  # the dance's own face keys, then the smile override on top
        scene.frame_set(frame)
        frame_camera(scene, cam, arm, kind)
        if P.get("morphs"):
            apply_morphs(mesh, P["morphs"], {})
        if bg_image is not None:
            ce = contact_ellipse(scene, cam, arm, P) if (kind == "full" and P["stage"].get("contact")) else None
            print("LOOK contact", name, ce)
            bg_image.pixels.foreach_set(stage_pixels(P, 540, 960, ce))
            bg_image.update()
            scene.render.film_transparent = True
        # beauty pass
        for i, m in enumerate(beauty):
            mesh.data.materials[i] = m
        if O:
            sol.show_render = True
        scene.render.use_compositing = True
        scene.eevee.taa_render_samples = 32
        scene.render.filter_size = 1.5
        vs.view_transform, vs.exposure = P["view_transform"], P.get("exposure", 0.0)
        scene.render.filepath = os.path.join(out, name + ".png")
        scene.render.image_settings.color_mode = "RGB"
        bpy.ops.render.render(write_still=True)
        if kind != "close":
            continue
        # flat material-ID pass, same camera
        for i, m in enumerate(ids):
            mesh.data.materials[i] = m
        if O:
            sol.show_render = False
        scene.render.use_compositing = False
        scene.render.film_transparent = False
        scene.eevee.taa_render_samples = 1
        scene.render.filter_size = 0.0
        vs.view_transform, vs.exposure, vs.look, vs.gamma = "Standard", 0.0, "None", 1.0
        bgc = scene.world.node_tree.nodes  # make camera-ray background black for the ID pass
        bk = [n for n in bgc if n.type == "BACKGROUND"][1]
        keep = tuple(bk.inputs[0].default_value)
        bk.inputs[0].default_value = (0, 0, 0, 1)
        scene.render.filepath = os.path.join(out, name + "_id.png")
        bpy.ops.render.render(write_still=True)
        bk.inputs[0].default_value = keep
        vs.look = P.get("look", "None")
        vs.gamma = P.get("gamma", 1.0)
    print("LOOK DONE", out)


main()
