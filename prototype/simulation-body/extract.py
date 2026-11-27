"""PROTOTYPE (throwaway). Runs inside headless Blender.

  Blender -b --python extract.py -- rest   <out_dir>
  Blender -b --python extract.py -- motion <out_dir> <list.json>     list: [{"key", "path"}, ...]

rest:   her rest skeleton (the 19 part bones), every Visible Mesh vertex with its part (or trailing),
        material and the shoe's floor-contact patches  ->  <out_dir>/rest.npz
motion: for each VMD (or VPD) in the list, the model is imported fresh, the motion applied with
        import_vmd(margin=0), and per Blender frame the rotation delta D = R_eval(b) R_rest(b)^-1 of each
        part's rotation bone and the evaluated head of each part's joint bone are written
        ->  <out_dir>/motion/<key>.npz
Nothing derived from the model is written anywhere else.
"""
import glob
import json
import os
import sys
import time

import bpy
import numpy as np

SCALE = 0.08
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PARTS = ["pelvis", "waist", "chest", "neck", "head", "collar_L", "collar_R", "upper_arm_L", "upper_arm_R",
         "forearm_L", "forearm_R", "hand_L", "hand_R", "thigh_L", "thigh_R", "shin_L", "shin_R", "foot_L", "foot_R"]
JOINT_BONE = {"pelvis": "下半身", "waist": "上半身", "chest": "上半身2", "neck": "首", "head": "頭"}
ROT_BONE = dict(JOINT_BONE)
for s in ("L", "R"):
    JOINT_BONE.update({f"collar_{s}": f"肩.{s}", f"upper_arm_{s}": f"腕.{s}", f"forearm_{s}": f"ひじ.{s}",
                       f"hand_{s}": f"手首.{s}", f"thigh_{s}": f"足D.{s}", f"shin_{s}": f"ひざD.{s}",
                       f"foot_{s}": f"足首D.{s}"})
    ROT_BONE.update({f"collar_{s}": f"肩.{s}", f"upper_arm_{s}": f"腕捩.{s}", f"forearm_{s}": f"手捩.{s}",
                     f"hand_{s}": f"手首.{s}", f"thigh_{s}": f"足D.{s}", f"shin_{s}": f"ひざD.{s}",
                     f"foot_{s}": f"足首D.{s}"})
# bone -> part for the vertex split: walk up from a vertex's dominant bone to the first bone listed here
PART_OF_BONE = {}
for p in PARTS:
    PART_OF_BONE[JOINT_BONE[p]] = p
    PART_OF_BONE[ROT_BONE[p]] = p
PART_OF_BONE["上半身1"] = "waist"
for s in ("L", "R"):
    PART_OF_BONE.update({f"足.{s}": f"thigh_{s}", f"ひざ.{s}": f"shin_{s}", f"足首.{s}": f"foot_{s}"})
MOUTH = ["あ", "い", "う", "え", "お"]
LANDMARKS = ["頭", "足先EX.L", "足先EX.R", "中指３.L", "中指３.R", "中指先.L", "中指先.R", "首", "上半身2"]


def args():
    return sys.argv[sys.argv.index("--") + 1:]


def load_model():
    pmx = sorted(glob.glob(os.path.join(REPO, "沃雅妮莎_by_*", "沃雅妮莎.pmx")))[0]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import addon_utils
    for m in addon_utils.modules():
        if m.__name__.endswith("mmd_tools"):
            addon_utils.enable(m.__name__, default_set=False)
            break
    bpy.ops.mmd_tools.import_model(filepath=pmx, scale=SCALE,
                                   types={"MESH", "ARMATURE", "PHYSICS", "MORPHS"}, log_level="ERROR")
    root = next(o for o in bpy.data.objects if getattr(o, "mmd_type", "") == "ROOT")
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    mesh = next(o for o in bpy.data.objects if o.type == "MESH" and getattr(o, "mmd_type", "NONE") == "NONE")
    trailing = sorted({o.mmd_rigid.bone for o in bpy.data.objects
                       if getattr(o, "mmd_type", "") == "RIGID_BODY" and o.mmd_rigid.type in ("1", "2")
                       and o.mmd_rigid.bone})
    for o in [o for o in bpy.data.objects
              if getattr(o, "mmd_type", "") in ("RIGID_BODY", "JOINT", "RIGID_GRP_OBJ", "JOINT_GRP_OBJ")]:
        bpy.data.objects.remove(o, do_unlink=True)
    if bpy.context.scene.rigidbody_world is not None:
        bpy.ops.rigidbody.world_remove()
    assert np.allclose(np.array(arm.matrix_world), np.eye(4)) and np.allclose(np.array(mesh.matrix_world), np.eye(4))
    return root, arm, mesh, trailing


def iter_fcurves(a):
    if a is None:
        return
    if hasattr(a, "fcurves") and len(getattr(a, "fcurves", [])):
        yield from a.fcurves
        return
    for layer in getattr(a, "layers", []):
        for strip in layer.strips:
            for cb in strip.channelbags:
                yield from cb.fcurves


def rest(out):
    root, arm, mesh, trailing = load_model()
    B = arm.data.bones
    chains = {}
    for p in PARTS:
        for b in (JOINT_BONE[p], ROT_BONE[p]):
            n, ch = B[b].parent, []
            while n is not None:
                ch.append(n.name)
                n = n.parent
            chains[b] = ch
    joint_pos = np.array([np.array(B[JOINT_BONE[p]].head_local) for p in PARTS])
    rest_rot = np.array([np.array(B[ROT_BONE[p]].matrix_local)[:3, :3] for p in PARTS])
    lm = {n: np.array(B[n].head_local).tolist() for n in LANDMARKS if n in B}
    lm.update({n + ":tail": np.array(B[n].tail_local).tolist() for n in LANDMARKS if n in B})

    dg = bpy.context.evaluated_depsgraph_get()
    ev = mesh.evaluated_get(dg)
    me = ev.to_mesh()
    nv = len(me.vertices)
    co = np.empty(nv * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    me.calc_loop_triangles()
    tris = np.empty(len(me.loop_triangles) * 3, np.int64)
    me.loop_triangles.foreach_get("vertices", tris)
    tris = tris.reshape(-1, 3)
    tmat = np.empty(len(me.loop_triangles), np.int64)
    me.loop_triangles.foreach_get("material_index", tmat)
    ev.to_mesh_clear()
    mats = [m.name if m else "" for m in mesh.data.materials]
    vmat = np.full(nv, -1, np.int64)
    for k in range(3):
        sel = vmat[tris[:, k]] < 0
        vmat[tris[sel, k]] = tmat[sel]

    gn = {g.index: g.name for g in mesh.vertex_groups}
    tr_set = {t for t in trailing if not t.startswith("胸")}  # breast bones count as body
    cache = {}

    def walk(name):
        if name in cache:
            return cache[name]
        n, is_tr, part = B.get(name), False, None
        while n is not None:
            if n.name in tr_set:
                is_tr = True
            if part is None and n.name in PART_OF_BONE:
                part = PART_OF_BONE[n.name]
            n = n.parent
        cache[name] = (is_tr, part or "pelvis")
        return cache[name]

    vpart = np.full(nv, -1, np.int64)
    vtrail = np.zeros(nv, bool)
    vdom = []
    for v in mesh.data.vertices:
        best, w = None, -1.0
        for g in v.groups:
            nm = gn.get(g.group)
            if nm in B and g.weight > w:
                best, w = nm, g.weight
        vdom.append(best or "")
        if best is None:
            continue
        t, p = walk(best)
        vtrail[v.index] = t
        vpart[v.index] = PARTS.index(p)

    # shoe floor-contact patches (as assets/inspect/motion/dump.py): shoe-material vertices within 6 mm
    # of the lowest, split at the ankle into front pad (toward -Y) and heel tip
    shoe_slots = [i for i, m in enumerate(mats) if m.startswith("鞋")]
    shoe_v = np.nonzero(np.isin(vmat, shoe_slots))[0]
    patches = {}
    for s, sgn in (("L", 1), ("R", -1)):
        sv = shoe_v[np.sign(co[shoe_v, 0]) == sgn]
        low = sv[co[sv, 2] < co[sv, 2].min() + 0.006]
        ank_y = B[f"足首D.{s}"].head_local.y
        patches[f"heel_{s}"] = low[co[low, 1] > ank_y]
        patches[f"fore_{s}"] = low[co[low, 1] <= ank_y]
        patches[f"shoe_{s}"] = sv

    os.makedirs(out, exist_ok=True)
    np.savez_compressed(os.path.join(out, "rest.npz"), parts=np.array(PARTS), joint_pos=joint_pos,
                        rest_rot=rest_rot, verts=co, tris=tris, vmat=vmat, vpart=vpart, vtrail=vtrail,
                        mat_names=np.array(mats), vdom=np.array(vdom),
                        **{f"patch_{k}": v for k, v in patches.items()},
                        info=json.dumps({"chains": chains, "joint_bone": JOINT_BONE, "rot_bone": ROT_BONE,
                                         "landmarks": lm, "trailing_bones": trailing,
                                         "shape_keys": [k.name for k in mesh.data.shape_keys.key_blocks]
                                         if mesh.data.shape_keys else []}, ensure_ascii=False))
    print("REST DONE", nv, "verts", int((vpart >= 0).sum()), "with a part,", int(vtrail.sum()), "trailing")


def motion(out, lst):
    os.makedirs(os.path.join(out, "motion"), exist_ok=True)
    for item in lst:
        t0 = time.time()
        key, path = item["key"], item["path"]
        dst = os.path.join(out, "motion", key + ".npz")
        root, arm, mesh, _ = load_model()
        scene = bpy.context.scene
        for mod in mesh.modifiers:  # bones only: skip deforming the mesh on every frame
            mod.show_viewport = False
        bpy.ops.object.select_all(action="DESELECT")
        root.select_set(True)
        bpy.context.view_layer.objects.active = root
        try:
            if path.lower().endswith(".vpd"):
                arm.select_set(True)
                bpy.context.view_layer.objects.active = arm
                res = bpy.ops.mmd_tools.import_vpd(filepath=path, scale=SCALE, bone_mapper="PMX")
                frames = [scene.frame_current]
            else:
                res = bpy.ops.mmd_tools.import_vmd(filepath=path, scale=SCALE, margin=0, bone_mapper="PMX",
                                                   use_pose_mode=False, update_scene_settings=True,
                                                   log_level="ERROR")
                act = arm.animation_data.action if arm.animation_data else None
                lo, hi = (int(np.floor(act.frame_range[0])), int(np.ceil(act.frame_range[1]))) if act else (0, 0)
                frames = list(range(lo, hi + 1))
            if "FINISHED" not in res:
                raise RuntimeError(str(res))
        except Exception as e:  # noqa: BLE001
            print("MOTION FAILED", key, e, flush=True)
            continue
        scene.render.fps = 30
        mouth_fc = []
        sk = mesh.data.shape_keys
        if sk is not None and sk.animation_data is not None:
            for fc in iter_fcurves(sk.animation_data.action):
                if any(fc.data_path == f'key_blocks["{m}"].value' for m in MOUTH):
                    mouth_fc.append(fc)
        rest_inv = np.array([np.linalg.inv(np.array(arm.data.bones[ROT_BONE[p]].matrix_local)[:3, :3])
                             for p in PARTS])
        T = len(frames)
        D = np.zeros((T, 19, 3, 3), np.float32)
        P = np.zeros((T, 19, 3), np.float32)
        mouth = np.zeros(T, np.float32)
        pbr = [arm.pose.bones[ROT_BONE[p]] for p in PARTS]
        pbj = [arm.pose.bones[JOINT_BONE[p]] for p in PARTS]
        for i, f in enumerate(frames):
            if len(frames) > 1:
                scene.frame_set(f)
            else:
                bpy.context.view_layer.update()
            for j in range(19):
                D[i, j] = np.array(pbr[j].matrix)[:3, :3] @ rest_inv[j]
                P[i, j] = np.array(pbj[j].head)
            mouth[i] = sum(max(0.0, fc.evaluate(f)) for fc in mouth_fc)
        np.savez_compressed(dst, key=key, path=os.path.relpath(path, REPO), frames=np.array(frames), D=D, P=P,
                            mouth=mouth, n_mouth_curves=len(mouth_fc))
        print(f"MOTION DONE {key} frames {frames[0]}..{frames[-1]} ({T}) mouth curves {len(mouth_fc)} "
              f"{time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    a = args()
    if a[0] == "rest":
        rest(a[1])
    else:
        with open(a[2], encoding="utf-8") as f:
            motion(a[1], json.load(f))
