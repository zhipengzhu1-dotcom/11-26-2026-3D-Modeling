"""PROTOTYPE (throwaway). Stills of the Simulation Body drawn over her in her rest pose.

  Blender -b --python stills.py -- <body.json> <out_dir> [res_pct]

Writes to <out_dir>: solids_{front,side,back,three_quarter}.png (her as usual, each part's solids as
translucent coloured shells), xray_{front,side}.png (her ghosted, solids clearer, every joint marked with a
ball and short sticks along its hinge axes), feet_{side,below}.png (floor-contact shapes in loud magenta,
floor line visible), and contact_sheet.png.
"""
import json
import math
import os
import subprocess
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import pic_util as U  # noqa: E402

LOUD = (1.0, 0.0, 0.85)
AXIS_COLORS = [(0.95, 0.1, 0.1), (0.1, 0.8, 0.1), (0.1, 0.3, 1.0), (0.9, 0.7, 0.0), (0.0, 0.8, 0.8)]


def mesh_object(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def make_geom(i, g):
    bm = bmesh.new()
    t, s = g["type"], g["size"]
    if t == "capsule":
        r, hl = s[0], s[1]
        bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=15, radius=r)  # odd rings: no equator verts
        for v in bm.verts:
            v.co.z += hl if v.co.z > 0 else -hl
    elif t == "sphere":
        bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=s[0])
    elif t == "box":
        bmesh.ops.create_cube(bm, size=2.0)
        for v in bm.verts:
            v.co = Vector((v.co.x * s[0], v.co.y * s[1], v.co.z * s[2]))
    else:
        raise SystemExit(f"PICTURE-ERROR: unknown geom type {t}")
    ob = mesh_object(f"geom_{i:02d}_{g['part']}", bm)
    R = Matrix(g.get("rot", np.eye(3).tolist()))
    ob.matrix_world = Matrix.Translation(Vector(g["pos"])) @ R.to_4x4()
    ob.visible_shadow = False
    return ob


def cylinder_between(name, a, b, r, mat):
    a, b = Vector(a), Vector(b)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=r, radius2=r, depth=(b - a).length)
    ob = mesh_object(name, bm)
    ob.matrix_world = Matrix.Translation((a + b) / 2) @ (b - a).to_track_quat("Z", "Y").to_matrix().to_4x4()
    ob.data.materials.append(mat)
    ob.visible_shadow = False
    return ob


def ball(name, c, r, mat):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=10, radius=r)
    ob = mesh_object(name, bm)
    ob.location = Vector(c)
    ob.data.materials.append(mat)
    ob.visible_shadow = False
    return ob


def rgb(c):
    c = [float(x) for x in c[:3]]
    return tuple(x / 255.0 for x in c) if max(c) > 1.0 else tuple(c)


def main():
    a = U.args()
    body_json, out = a[0], a[1]
    res_pct = int(a[2]) if len(a) > 2 else 100
    t0 = time.time()
    with open(body_json) as f:
        body = json.load(f)
    U.reset()
    root, arm, mesh = U.import_her()
    scene = bpy.context.scene
    U.pick_engine(scene)
    scene.eevee.taa_render_samples = 32
    sun = U.plain_world(scene)
    scene.render.resolution_x, scene.render.resolution_y = 1080, 1350
    scene.render.resolution_percentage = res_pct
    scene.render.image_settings.file_format = "PNG"
    for o in bpy.data.objects:
        if o.type in ("EMPTY", "ARMATURE"):
            o.hide_render = True

    verts = U.mesh_world_verts(mesh)
    mn, mx = verts.min(axis=0), verts.max(axis=0)
    centre = (mn + mx) / 2

    # floor: a thin slab with its top at z = 0 (its edge is the floor line in the side views)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    floor = mesh_object("floor", bm)
    floor.scale = (30, 30, 0.003)
    floor.location = (0, 0, -0.0015)
    floor.data.materials.append(U.flat_material("floor", (0.42, 0.43, 0.46), cull=False))

    part_rgb = {p["name"]: rgb(p.get("color", (0.5, 0.5, 0.5))) for p in body["parts"]}
    solid_mats = {}
    geoms = []
    for i, g in enumerate(body["geoms"]):
        ob = make_geom(i, g)
        key = ("contact" if g.get("floor_contact") else g["part"])
        if key not in solid_mats:
            col = LOUD if key == "contact" else part_rgb.get(g["part"], (0.5, 0.5, 0.5))
            solid_mats[key] = U.flat_material(f"solid_{key}", col, alpha=0.4, emission=0.15)
        ob.data.materials.append(solid_mats[key])
        geoms.append((ob, g))

    # joint markers (hidden except in the x-ray)
    markers = []
    dark = U.flat_material("joint_ball", (0.05, 0.05, 0.05))
    axis_mats = [U.flat_material(f"axis_{k}", c, emission=0.6) for k, c in enumerate(AXIS_COLORS)]
    by_pos = {}
    for j in body["joints"]:
        by_pos.setdefault(tuple(round(x, 4) for x in j["pos"]), []).append(j)
    for k, (pos, js) in enumerate(by_pos.items()):
        markers.append(ball(f"joint_{k}", pos, 0.013, dark))
        for n, j in enumerate(js):
            ax = Vector(j["axis"]).normalized() * 0.045
            p = Vector(pos)
            markers.append(cylinder_between(f"axis_{k}_{n}", p - ax, p + ax, 0.0035, axis_mats[n % len(axis_mats)]))
    for m in markers:
        m.hide_render = True

    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.type = "ORTHO"
    cam.data.clip_end = 20

    def aim(direction, target, scale):
        d = Vector(direction).normalized()
        cam.location = Vector(target) + d * 20  # outside the 30 m floor, so its edge draws the floor line
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        cam.data.ortho_scale = scale

    full = (mx[2] - min(mn[2], 0)) * 1.08
    mid = (centre[0], centre[1], (mx[2] + min(mn[2], 0)) / 2)
    fl = np.array(arm.data.bones["足首D.L"].head_local)
    fr = np.array(arm.data.bones["足首D.R"].head_local)
    shots = [
        ("solids_front", "Solids over her - front", (0, -1, 0), mid, full, "solids"),
        ("solids_side", "Solids over her - side (her left)", (1, 0, 0), mid, full, "solids"),
        ("solids_back", "Solids over her - back", (0, 1, 0), mid, full, "solids"),
        ("solids_three_quarter", "Solids over her - three-quarter", (0.65, -0.75, 0.15), mid, full, "solids"),
        ("xray_front", "X-ray: joints and solids - front", (0, -1, 0), mid, full, "xray"),
        ("xray_side", "X-ray: joints and solids - side (her left)", (1, 0, 0), mid, full, "xray"),
        ("feet_side", "Left shoe from the side: magenta = floor contact", (1, 0, 0), (fl[0], fl[1] - 0.02, 0.075), 0.26, "feet"),
        ("feet_below", "Both shoes from below (toes up, her left on the right)", (0, 0, -1),
         ((fl[0] + fr[0]) / 2, fl[1] - 0.03, 0.0), 0.30, "below"),
    ]
    original = [s.material for s in mesh.material_slots]
    ghost = U.flat_material("ghost", (0.85, 0.85, 0.9), alpha=0.09, cull=True)
    ghost.use_transparency_overlap = True  # the ghost writes no depth, so it never hides a solid or a joint
    under = bpy.data.objects.new("under_sun", bpy.data.lights.new("under_sun", "SUN"))
    under.data.energy = 2.0
    under.rotation_euler = (math.radians(180), 0, 0)
    scene.collection.objects.link(under)
    under.hide_render = True

    os.makedirs(out, exist_ok=True)
    made = []
    for fname, title, direction, target, scale, mode in shots:
        t = time.time()
        xray = mode == "xray"
        for s, m in zip(mesh.material_slots, original):
            s.material = ghost if xray else m
        for m in markers:
            m.hide_render = not xray
        for key, m in solid_mats.items():
            m.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.55 if xray else (0.85 if key == "contact" else 0.4)
            m.use_transparency_overlap = xray  # x-ray: no depth prepass, so solids never hide one another
        floor.hide_render = mode == "below"
        under.hide_render = mode != "below"
        if direction == (0, 0, -1):
            cam.location = Vector(target) + Vector((0, 0, -5))
            cam.rotation_euler = (math.radians(180), 0, 0)  # looking up; image up = her toes (-Y)
            cam.data.ortho_scale = scale
            cam.data.clip_end = 5.12  # only what lies below 12 cm: shoes and ankles, not the dress above
            scene.render.resolution_x, scene.render.resolution_y = 1350, 1080
        else:
            aim(direction, target, scale)
            cam.data.clip_end = 60
            scene.render.resolution_x, scene.render.resolution_y = 1080, 1350
        U.stamp(scene, title, size=max(14, int(30 * res_pct / 100)))
        path = os.path.join(out, f"{fname}.png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        if xray:
            # second pass: the joint markers alone on a transparent film, laid over the x-ray so no solid hides them
            hidden = [o for o in bpy.data.objects if o.type == "MESH" and o not in markers and not o.hide_render]
            for o in hidden:
                o.hide_render = True
            scene.render.film_transparent = True
            scene.render.use_stamp = False
            scene.render.image_settings.color_mode = "RGBA"
            mpath = os.path.join(out, f"_{fname}_markers.png")
            scene.render.filepath = mpath
            bpy.ops.render.render(write_still=True)
            for o in hidden:
                o.hide_render = False
            scene.render.film_transparent = False
            scene.render.image_settings.color_mode = "RGB"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-i", mpath, "-filter_complex",
                            "[0:v][1:v]overlay=0:0", "-frames:v", "1", path + ".tmp.png"], check=True)
            os.replace(path + ".tmp.png", path)
            os.remove(mpath)
        made.append(path)
        print(f"STILL {fname} {time.time() - t:.1f} s", flush=True)

    # contact sheet: 4 x 2, each tile 540 x 675 (the landscape below-view letterboxed)
    tiles = []
    for p in made:
        tiles += ["-i", p]
    filt = ";".join(f"[{k}:v]scale=540:675:force_original_aspect_ratio=decrease,pad=540:675:(ow-iw)/2:(oh-ih)/2:color=0xbfc6d1[t{k}]"
                    for k in range(len(made)))
    layout = "|".join(f"{(k % 4) * 540}_{(k // 4) * 675}" for k in range(len(made)))
    filt += ";" + "".join(f"[t{k}]" for k in range(len(made))) + f"xstack=inputs={len(made)}:layout={layout}"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *tiles, "-filter_complex", filt, "-frames:v", "1",
                    os.path.join(out, "contact_sheet.png")], check=True)
    print(f"STILLS DONE {len(made)} stills + contact sheet in {time.time() - t0:.1f} s -> {out}", flush=True)


main()
