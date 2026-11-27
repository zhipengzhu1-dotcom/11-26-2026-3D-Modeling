"""PROTOTYPE (throwaway). Her Visible Mesh moved by the Simulation Body's motion.

  Blender -b --python clips.py -- render <clips.json> <name> <frames_dir> <lo> <hi> <res_pct> <timing.json>
      Renders output frames lo..hi (inclusive, 0-based) of clip <name>: three copies of her side by side,
      left to right as authored (ref), soft joints, stiff joints, all driven from sim/<name>.npz.
      Face shapes and fingers come from the source VMD at src_frame[i].
  Blender -b --python clips.py -- roundtrip <npz> <vmd> <out.json> [every]
      Proves the write-back: plain VMD playback vs her driven from the npz's soft variant (which
      make_test_data.py fills with the same playback), compared vertex by vertex.
"""
import json
import math
import os
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import pic_util as U  # noqa: E402

VARIANTS = [("ref", "as authored"), ("soft", "soft joints"), ("stiff", "stiff joints")]


def set_src_frame(scene, f, lo_hi, loop_len):
    lo, hi = lo_hi
    f = float(f)
    if loop_len and f > hi:
        f = lo + (f - lo) % loop_len
    fi = int(math.floor(f))
    scene.frame_set(fi, subframe=f - fi)


# ------------------------------------------------------------------------------------------- roundtrip
def roundtrip(npz_path, vmd, out, every=1, use_axes=True):
    U.reset()
    root, arm, mesh = U.import_her()
    U.import_vmd(root, vmd)
    scene = bpy.context.scene
    z = np.load(npz_path)
    src = z["src_frame"]
    idx = list(range(0, len(src), every))
    lo_hi = U.action_frame_range(arm)
    loop_len = int(z["loop_len"])

    # which bones does the VMD animate that the write-back leaves to the VMD?
    animated = set()
    for _, fc in U.iter_fcurves(arm.animation_data.action):
        if fc.data_path.startswith('pose.bones["') and len(fc.keyframe_points) > 1:
            vals = [k.co[1] for k in fc.keyframe_points]
            if max(vals) - min(vals) > 1e-5:
                animated.add(fc.data_path.split('"')[1])

    A = {}
    for i in idx:
        set_src_frame(scene, src[i], lo_hi, loop_len)
        A[i] = U.mesh_world_verts(mesh)
    axes = U.twist_axes_from_action(arm) if use_axes else {}
    removed = U.strip_body_keys(arm)
    drv = U.Driver(arm, axes)
    errs, pos_err, rot_err = [], [], []
    for i in idx:
        set_src_frame(scene, src[i], lo_hi, loop_len)
        drv.pose(z["rot_soft"][i], z["pos_soft"][i, 0])
        bpy.context.view_layer.update()
        Bv = U.mesh_world_verts(mesh)
        errs.append(np.linalg.norm(Bv - A[i], axis=1))
        p, D = U.evaluated_parts(arm)
        pos_err.append(np.linalg.norm(p - z["pos_soft"][i], axis=1))
        c = np.clip((np.einsum("kij,kij->k", D, z["rot_soft"][i]) - 1) / 2, -1, 1)
        rot_err.append(np.degrees(np.arccos(c)))
    errs = np.array(errs)          # [F, V] metres
    pos_err = np.array(pos_err)    # [F, 19]
    rot_err = np.array(rot_err)    # [F, 19]

    # carrier of each vertex: its heaviest bone, and the nearest body bone above it
    gname = {g.index: g.name for g in mesh.vertex_groups}
    bones = arm.data.bones
    body = set(U.BODY_BONES)
    dom = []
    for v in mesh.data.vertices:
        gs = [(g.weight, gname[g.group]) for g in v.groups if gname[g.group] in bones]
        dom.append(max(gs)[1] if gs else "")
    carrier = []
    for d in dom:
        b = bones.get(d)
        while b is not None and b.name not in body:
            b = b.parent
        carrier.append(b.name if b is not None else "(none)")
    dom, carrier = np.array(dom), np.array(carrier)
    direct = np.array([d in body for d in dom])
    vmax = errs.max(axis=0)
    mm = lambda x: round(float(x) * 1000, 2)  # noqa: E731
    by_dom = {}
    for d in set(dom):
        sel = dom == d
        by_dom[d] = {"verts": int(sel.sum()), "max_mm": mm(vmax[sel].max()), "p99_mm": mm(np.percentile(errs[:, sel], 99)),
                     "mean_mm": mm(errs[:, sel].mean())}
    worst_frames = np.argsort(-errs[:, direct].max(axis=1))[:5]
    res = {
        "npz": npz_path, "vmd": os.path.basename(vmd), "frames_compared": len(idx),
        "twist_axes_local": {k: [round(float(x), 4) for x in v] for k, v in axes.items()},
        "vmd_animated_bones_left_to_vmd": sorted(animated - set(removed)),
        "vmd_bones_whose_keys_were_removed": removed,
        "body_vertices": {"count": int(direct.sum()), "max_mm": mm(errs[:, direct].max()),
                          "p99_mm": mm(np.percentile(errs[:, direct], 99)), "mean_mm": mm(errs[:, direct].mean())},
        "body_vertices_away_from_shoulders_and_upper_arms": (lambda sel: {
            "count": int(sel.sum()), "max_mm": mm(errs[:, sel].max()), "p99_mm": mm(np.percentile(errs[:, sel], 99)),
            "mean_mm": mm(errs[:, sel].mean())})(direct & ~np.array([d.split(".")[0] in ("肩", "腕", "腕捩", "腕捩1", "腕捩2", "腕捩3") for d in dom])),
        "all_vertices": {"count": int(errs.shape[1]), "max_mm": mm(errs.max()), "p99_mm": mm(np.percentile(errs, 99)),
                         "mean_mm": mm(errs.mean())},
        "joint_pos_err_mm": {p: mm(pos_err[:, k].max()) for k, p in enumerate(U.PARTS)},
        "part_rot_err_deg": {p: round(float(rot_err[:, k].max()), 3) for k, p in enumerate(U.PARTS)},
        "worst_heaviest_bones": sorted(([d, s] for d, s in by_dom.items()), key=lambda x: -x[1]["max_mm"])[:15],
        "worst_body_frames": [[int(idx[k]), int(src[idx[k]]), mm(errs[k, direct].max())] for k in worst_frames],
    }
    U_write(out, res)
    print("ROUNDTRIP", json.dumps({k: res[k] for k in ("body_vertices", "all_vertices")}))


def U_write(path, data):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


# ------------------------------------------------------------------------------------------- render
def grid_floor(size=40.0):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0))
    floor = bpy.context.active_object
    floor.name = "pic_floor"
    mat = bpy.data.materials.new("pic_floor")
    try:
        mat.use_nodes = True
    except Exception:
        pass
    nt = mat.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    fine = nt.nodes.new("ShaderNodeTexChecker")      # 0.25 m squares
    fine.inputs["Scale"].default_value = 4.0
    fine.inputs["Color1"].default_value = (0.62, 0.63, 0.66, 1)
    fine.inputs["Color2"].default_value = (0.47, 0.48, 0.52, 1)
    coarse = nt.nodes.new("ShaderNodeTexChecker")    # 1 m squares, a gentle tint on top
    coarse.inputs["Scale"].default_value = 1.0
    coarse.inputs["Color1"].default_value = (1.0, 1.0, 1.0, 1)
    coarse.inputs["Color2"].default_value = (0.82, 0.85, 0.95, 1)
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    nt.links.new(tc.outputs["Object"], fine.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], coarse.inputs["Vector"])
    nt.links.new(fine.outputs["Color"], mix.inputs["A"])
    nt.links.new(coarse.outputs["Color"], mix.inputs["B"])
    bsdf = nt.nodes.get("Principled BSDF")
    nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    floor.data.materials.append(mat)
    return floor


def fit_distance(scene, cam, box_lo, box_hi, target, direction, margin=0.04):
    from bpy_extras.object_utils import world_to_camera_view
    corners = [Vector((x, y, zz)) for x in (box_lo[0], box_hi[0]) for y in (box_lo[1], box_hi[1]) for zz in (box_lo[2], box_hi[2])]
    lo, hi = 0.3, 60.0
    rot = (-direction).to_track_quat("-Z", "Y").to_euler()
    for _ in range(40):
        d = (lo + hi) / 2
        cam.location = target + direction * d
        cam.rotation_euler = rot
        bpy.context.view_layer.update()
        ok = all(margin <= v.x <= 1 - margin and margin <= v.y <= 1 - margin and v.z > 0
                 for v in (world_to_camera_view(scene, cam, c) for c in corners))
        hi, lo = (d, lo) if ok else (hi, d)
    return hi


def label(text, cam, local, size, mat):
    cu = bpy.data.curves.new(f"label_{text}", "FONT")
    cu.body = text
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.size = size
    ob = bpy.data.objects.new(f"label_{text}", cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    ob.parent = cam
    ob.location = local
    ob.visible_shadow = False
    return ob


def render(clips_json, name, frames_dir, lo, hi, res_pct, timing_json):
    t_setup = time.time()
    with open(clips_json) as f:
        clip = next(c for c in json.load(f) if c["name"] == name)
    cdir = os.path.dirname(os.path.abspath(clips_json))
    npz = next((p for p in (clip["npz"], os.path.join(cdir, clip["npz"]), os.path.join(U.REPO, clip["npz"]),
                            os.path.join(U.BUILD, "sim", f"{name}.npz")) if os.path.exists(p)), None)
    vmd = next((p for p in (clip["vmd"], os.path.join(U.REPO, clip["vmd"]), os.path.join(cdir, clip["vmd"]))
                if os.path.exists(p)), None)
    if npz is None or vmd is None:
        raise SystemExit(f"PICTURE-ERROR: clip {name}: npz {clip['npz']} or vmd {clip['vmd']} not found")
    z = np.load(npz)
    T = len(z["src_frame"])
    hi = min(hi, T - 1)
    bust = clip.get("framing") == "bust"
    pinned = clip.get("hips") == "pinned"
    spacing = 0.7 if bust else 1.05

    U.reset()
    scene = bpy.context.scene
    toon = os.environ.get("LOOK", "toon") != "plain"   # her settled look (toon_look.py) unless LOOK=plain
    figs, meshes = [], []
    for k, (v, _) in enumerate(VARIANTS):
        root, arm, mesh = U.import_her()
        U.import_vmd(root, vmd)
        axes = U.twist_axes_from_action(arm)
        U.strip_body_keys(arm)
        root.location.x = (k - 1) * spacing
        figs.append((v, arm, U.Driver(arm, axes)))
        meshes.append(mesh)
    lo_hi = U.action_frame_range(figs[0][1])
    loop_len = int(z["loop_len"])

    U.pick_engine(scene)
    if not toon:
        scene.eevee.taa_render_samples = 16
        U.plain_world(scene)
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = res_pct
    scene.render.image_settings.file_format = "PNG"
    scene.render.fps = 30
    for o in bpy.data.objects:
        if o.type in ("EMPTY", "ARMATURE"):
            o.hide_render = True
    if not pinned and not toon:
        grid_floor()

    # camera: from her front, following the smoothed mean pelvis of the three figures
    pel = np.stack([z[f"pos_{v}"][:, 0] for v, _ in VARIANTS]).mean(axis=0)  # [T,3]
    half = 22
    sm = np.array([pel[max(0, i - half): i + half + 1].mean(axis=0) for i in range(T)])
    zp = float(np.median(pel[:, 2]))
    if bust:
        box_lo = (-spacing - 0.4, -0.3, zp - 0.08)
        box_hi = (spacing + 0.4, 0.3, zp + 0.7)
        direction = Vector((0.0, -1.0, 0.04)).normalized()
    else:
        box_lo = (-spacing - 0.5, -0.45, min(0.0, float(pel[:, 2].min()) - 1.05))
        box_hi = (spacing + 0.5, 0.45, float(pel[:, 2].max()) + 1.0)  # room for raised hands under the labels
        direction = Vector((0.0, -1.0, 0.22)).normalized()
    cam = bpy.data.objects.new("pic_camera", bpy.data.cameras.new("pic_camera"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.lens = 50
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.sensor_width = 36
    zc = (box_lo[2] + box_hi[2]) / 2
    rel_lo = (box_lo[0], box_lo[1], box_lo[2] - zc)
    rel_hi = (box_hi[0], box_hi[1], box_hi[2] - zc)
    dist = fit_distance(scene, cam, rel_lo, rel_hi, Vector((0, 0, 0)), direction)
    cam.data.clip_end = dist * 10
    rot = (-direction).to_track_quat("-Z", "Y").to_euler()
    cam.rotation_euler = rot
    if toon:
        import toon_look
        cam.location = Vector((float(sm[lo, 0]), float(sm[lo, 1]), zc)) + direction * dist
        bpy.context.view_layer.update()
        toon_look.apply(scene, meshes, cam, floor=not pinned, samples=16)

    half_w = dist * 18.0 / cam.data.lens
    half_h = half_w * 9 / 16
    ink = U.flat_material("pic_ink", (0.02, 0.02, 0.03))
    for k, (_, txt) in enumerate(VARIANTS):
        label(txt, cam, Vector(((k - 1) * spacing, half_h * 0.86, -dist)), half_h * 0.07, ink)
    note = "PROTOTYPE: hips pinned in the air (no floor)" if pinned else "PROTOTYPE: hips carried, she is not balancing"

    os.makedirs(frames_dir, exist_ok=True)
    t_setup = time.time() - t_setup
    times = []
    for i in range(lo, hi + 1):
        t = time.time()
        set_src_frame(scene, z["src_frame"][i], lo_hi, loop_len)
        for v, arm, drv in figs:
            drv.pose(z[f"rot_{v}"][i], z[f"pos_{v}"][i, 0])
        cam.location = Vector((float(sm[i, 0]), float(sm[i, 1]), zc)) + direction * dist
        U.stamp(scene, f"{note}   |   {name}   |   frame {i + 1}/{T}", size=max(12, int(24 * res_pct / 100)))
        bpy.context.view_layer.update()
        scene.render.filepath = os.path.join(frames_dir, f"f_{i:06d}.png")
        bpy.ops.render.render(write_still=True)
        times.append(time.time() - t)
        if (i - lo) % 20 == 0:
            print(f"CLIP {name} frame {i + 1}/{T} {times[-1]:.2f} s", flush=True)
    U_write(timing_json, {"clip": name, "frames": [lo, hi], "res_pct": res_pct, "setup_s": round(t_setup, 1),
                          "seconds_per_frame_mean": round(sum(times) / len(times), 3),
                          "seconds_first_frame": round(times[0], 2), "seconds_total": round(sum(times), 1)})
    print(f"CLIP DONE {name} {lo}..{hi} in {sum(times):.1f} s (+{t_setup:.1f} s setup)", flush=True)


a = U.args()
if a[0] == "roundtrip":
    roundtrip(a[1], a[2], a[3], int(a[4]) if len(a) > 4 else 1, (a[5] != "noaxes") if len(a) > 5 else True)
else:
    render(a[1], a[2], a[3], int(a[4]), int(a[5]), int(a[6]), a[7])
