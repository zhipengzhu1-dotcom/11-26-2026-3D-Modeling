"""PROTOTYPE (throwaway). Test data in the contract formats, made from her rig at run time.

  Blender -b --python make_test_data.py -- body <out_body.json>
      A stand-in Simulation Body: one capsule per limb between joint positions, three hinges per joint
      (one at knee and elbow), two floor-contact spheres per shoe. For building the drawing code only.
  Blender -b --python make_test_data.py -- clip <name> <vmd> <start> <end> <out.npz> <clips.json> <kind> <framing> [tiles]
      A contract npz from plain VMD playback: the evaluated matrices of the 19 bones become pos_ref/rot_ref,
      copied into soft/stiff. Appends (or replaces) the entry <name> in <clips.json>.

Write these to test_* file names under build/first-look/ so the other worker's files are never overwritten.
"""
import json
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import numpy as np  # noqa: E402

import pic_util as U  # noqa: E402

COLORS = {"pelvis": (0.9, 0.5, 0.1), "waist": (0.9, 0.8, 0.1), "chest": (0.2, 0.7, 0.3), "neck": (0.1, 0.6, 0.7),
          "head": (0.3, 0.4, 0.9), "collar": (0.6, 0.3, 0.8), "upper_arm": (0.9, 0.3, 0.5), "forearm": (0.2, 0.5, 0.9),
          "hand": (0.5, 0.8, 0.2), "thigh": (0.1, 0.7, 0.9), "shin": (0.9, 0.6, 0.3), "foot": (0.4, 0.3, 0.2)}
RADIUS = {"waist": 0.075, "chest": 0.09, "neck": 0.03, "collar": 0.03, "upper_arm": 0.03, "forearm": 0.025,
          "hand": 0.03, "thigh": 0.06, "shin": 0.038}


def capsule_between(a, b, r):
    a, b = np.asarray(a), np.asarray(b)
    v = b - a
    L = np.linalg.norm(v)
    z = v / L
    x = np.cross([0, 0, 1], z) if abs(z[2]) < 0.9 else np.cross([1, 0, 0], z)
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    rot = np.stack([x, y, z], axis=1)
    return {"type": "capsule", "pos": ((a + b) / 2).tolist(), "rot": rot.tolist(),
            "size": [r, max(L / 2 - r, 0.001)], "floor_contact": False}


def body(out):
    U.reset()
    root, arm, mesh = U.import_her()
    H = lambda n: np.array(arm.data.bones[n].head_local)  # noqa: E731
    jp = {p: H(U.JOINT_BONE[p]) for p in U.PARTS}
    child = {"waist": "chest", "chest": "neck", "neck": "head"}
    for s in "LR":
        child.update({f"collar_{s}": f"upper_arm_{s}", f"upper_arm_{s}": f"forearm_{s}", f"forearm_{s}": f"hand_{s}",
                      f"thigh_{s}": f"shin_{s}", f"shin_{s}": f"foot_{s}"})
    parts, joints, geoms = [], [], []
    for p in U.PARTS:
        base = p[:-2] if p.endswith(("_L", "_R")) else p
        parts.append({"name": p, "parent": U.PARENT[p], "joint_pos": jp[p].tolist(), "mass": 1.0, "color": COLORS[base]})
        axes = [[1, 0, 0]] if base in ("shin", "forearm") else [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        if p != "pelvis":
            for k, ax in enumerate(axes):
                joints.append({"name": f"{p}_{'xyz'[k]}", "part": p, "pos": jp[p].tolist(), "axis": ax, "range_deg": [-90, 90]})
        if p in child:
            g = capsule_between(jp[p], jp[child[p]], RADIUS[base])
        elif base == "head":
            g = {"type": "sphere", "pos": (jp[p] + [0, 0, 0.09]).tolist(), "rot": np.eye(3).tolist(), "size": [0.09], "floor_contact": False}
        elif base == "hand":
            tip = jp[p] + (jp[p] - jp[f"forearm_{p[-1]}"]) * 0.8
            g = capsule_between(jp[p], tip, RADIUS["hand"])
        elif base == "pelvis":
            g = capsule_between(jp["thigh_L"], jp["thigh_R"], 0.09)
        elif base == "foot":
            s = p[-1]
            toe = H(f"足先EX.{s}")
            g = capsule_between(jp[p], toe, 0.03)
            geoms.append({"part": p, "type": "sphere", "pos": [toe[0], toe[1] - 0.02, 0.012], "rot": np.eye(3).tolist(),
                          "size": [0.012], "floor_contact": True})
            geoms.append({"part": p, "type": "sphere", "pos": [jp[p][0], jp[p][1] + 0.035, 0.006], "rot": np.eye(3).tolist(),
                          "size": [0.006], "floor_contact": True})
        g["part"] = p
        geoms.append(g)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump({"parts": parts, "joints": joints, "geoms": geoms, "note": "TEST stand-in body from make_test_data.py"}, f, indent=1, default=float)
    print("TEST BODY", out, len(parts), "parts", len(joints), "joints", len(geoms), "geoms")


def clip(name, vmd, start, end, out, clips_json, kind, framing, tiles=1):
    U.reset()
    root, arm, mesh = U.import_her()
    U.import_vmd(root, vmd)
    scene = bpy.context.scene
    if start < 0:  # whole file
        start, end = U.action_frame_range(arm)
        end = end if tiles == 1 else end - 1  # a loop's last key repeats its first
    src = list(range(start, end + 1)) * tiles
    pos = np.zeros((len(src), 19, 3), np.float32)
    rot = np.zeros((len(src), 19, 3, 3), np.float32)
    cache = {}
    for i, f in enumerate(src):
        if f not in cache:
            scene.frame_set(f)
            cache[f] = U.evaluated_parts(arm)
        pos[i], rot[i] = cache[f]
    if tiles > 1:  # a tiled loop: carry the travel of each tile forward so she keeps walking
        step = pos[len(src) // tiles - 1, 0] - pos[0, 0]
        step[2] = 0
        n = len(src) // tiles
        for k in range(1, tiles):
            pos[k * n:(k + 1) * n] += step * k
    os.makedirs(os.path.dirname(out), exist_ok=True)
    np.savez_compressed(out, parts=np.array(U.PARTS), src_frame=np.array(src, np.int32),
                        loop_len=np.int32(end - start + 1 if tiles > 1 else 0),
                        pos_ref=pos, rot_ref=rot, pos_soft=pos, rot_soft=rot, pos_stiff=pos, rot_stiff=rot)
    clips = []
    if os.path.exists(clips_json):
        with open(clips_json) as f:
            clips = [c for c in json.load(f) if c["name"] != name]
    clips.append({"name": name, "kind": kind, "title": f"TEST {name} (plain playback copied into all three)",
                  "npz": out, "vmd": vmd, "framing": framing, "hips": "carried", "credits": "test data"})
    with open(clips_json, "w") as f:
        json.dump(clips, f, ensure_ascii=False, indent=1)
    print("TEST CLIP", out, len(src), "frames")


a = U.args()
if a[0] == "body":
    body(a[1])
else:
    clip(a[1], a[2], int(a[3]), int(a[4]), a[5], a[6], a[7], a[8], int(a[9]) if len(a) > 9 else 1)
