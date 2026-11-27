"""PROTOTYPE (throwaway). Blender-side helpers shared by stills.py, clips.py and make_test_data.py.

Run only inside Blender. Imports her from the local model copy at run time; nothing derived from
the model is stored here.
"""
import glob
import math
import os
import sys

sys.dont_write_bytecode = True  # keep __pycache__ out of the tracked folder

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Quaternion, Vector  # noqa: E402

SCALE = 0.08
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
BUILD = os.path.join(REPO, "build", "first-look")

PARTS = ["pelvis", "waist", "chest", "neck", "head", "collar_L", "collar_R", "upper_arm_L", "upper_arm_R",
         "forearm_L", "forearm_R", "hand_L", "hand_R", "thigh_L", "thigh_R", "shin_L", "shin_R", "foot_L", "foot_R"]
PARENT = {"pelvis": None, "waist": "pelvis", "chest": "waist", "neck": "chest", "head": "neck"}
JOINT_BONE = {"pelvis": "下半身", "waist": "上半身", "chest": "上半身2", "neck": "首", "head": "頭"}
ROT_BONE = dict(JOINT_BONE)
for _s in "LR":
    for part, parent, jb, rb in (("collar", "chest", "肩", "肩"), ("upper_arm", "collar", "腕", "腕捩"),
                                 ("forearm", "upper_arm", "ひじ", "手捩"), ("hand", "forearm", "手首", "手首"),
                                 ("thigh", "pelvis", "足D", "足D"), ("shin", "thigh", "ひざD", "ひざD"),
                                 ("foot", "shin", "足首D", "足首D")):
        PARENT[f"{part}_{_s}"] = parent if parent in ("chest", "pelvis") else f"{parent}_{_s}"
        JOINT_BONE[f"{part}_{_s}"] = f"{jb}.{_s}"
        ROT_BONE[f"{part}_{_s}"] = f"{rb}.{_s}"


def args():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def pmx_path():
    hits = sorted(glob.glob(os.path.join(REPO, "沃雅妮莎_by_*", "沃雅妮莎.pmx")))
    if not hits:
        raise SystemExit("PICTURE-ERROR: no 沃雅妮莎_by_*/沃雅妮莎.pmx at the repo root")
    return hits[0]


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import addon_utils
    for m in addon_utils.modules():
        if m.__name__.endswith("mmd_tools"):
            addon_utils.enable(m.__name__, default_set=False)
            return
    raise SystemExit("PICTURE-ERROR: MMD Tools is not installed")


def import_her():
    """Import one copy of her (scale 0.08), strip the shipped rigid bodies and joints. Returns (root, arm, mesh)."""
    before = set(bpy.data.objects)
    bpy.ops.mmd_tools.import_model(filepath=pmx_path(), scale=SCALE,
                                   types={"MESH", "ARMATURE", "PHYSICS", "MORPHS"}, log_level="ERROR")
    new = [o for o in bpy.data.objects if o not in before]
    root = next(o for o in new if getattr(o, "mmd_type", "") == "ROOT")
    arm = next(o for o in new if o.type == "ARMATURE")
    mesh = next(o for o in new if o.type == "MESH" and getattr(o, "mmd_type", "NONE") == "NONE")
    for o in [o for o in new if getattr(o, "mmd_type", "") in ("RIGID_BODY", "JOINT", "RIGID_GRP_OBJ", "JOINT_GRP_OBJ")]:
        bpy.data.objects.remove(o, do_unlink=True)
    if bpy.context.scene.rigidbody_world is not None:
        bpy.ops.rigidbody.world_remove()
    for name in ("颜2", "照れ"):
        for m in bpy.data.materials:
            if (m.name == name or m.name.startswith(name + ".")) and hasattr(m, "surface_render_method"):
                m.surface_render_method = "BLENDED"
    return root, arm, mesh


def import_vmd(root, vmd):
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    res = bpy.ops.mmd_tools.import_vmd(filepath=vmd, scale=SCALE, margin=0, bone_mapper="PMX",
                                       use_pose_mode=False, update_scene_settings=True, log_level="ERROR")
    if "FINISHED" not in res:
        raise SystemExit(f"PICTURE-ERROR: VMD import failed: {res}")
    bpy.context.scene.render.fps = 30


def iter_fcurves(act):
    """(container, fcurve) for every F-curve of an action, slotted (Blender 5) or legacy."""
    if act is None:
        return
    for layer in getattr(act, "layers", []):
        for strip in layer.strips:
            for cb in strip.channelbags:
                for fc in list(cb.fcurves):
                    yield cb, fc
    if hasattr(act, "fcurves"):
        try:
            for fc in list(act.fcurves):
                yield act, fc
        except Exception:
            pass


def action_frame_range(arm):
    act = arm.animation_data.action
    lo, hi = 1e9, -1e9
    for _, fc in iter_fcurves(act):
        if len(fc.keyframe_points):
            lo = min(lo, fc.keyframe_points[0].co[0])
            hi = max(hi, fc.keyframe_points[-1].co[0])
    return int(lo), int(hi)


def evaluated_parts(arm):
    """(pos[19,3], D[19,3,3]) from the evaluated pose, armature space (= world for an armature at the origin)."""
    pos = np.zeros((19, 3))
    D = np.zeros((19, 3, 3))
    for i, p in enumerate(PARTS):
        pos[i] = np.array(arm.pose.bones[JOINT_BONE[p]].matrix.translation)
        rb = ROT_BONE[p]
        Re = np.array(arm.pose.bones[rb].matrix.to_3x3())
        Rr = np.array(arm.data.bones[rb].matrix_local.to_3x3())
        D[i] = Re @ Rr.T
    return pos, D


def mesh_world_verts(mesh, out=None):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = mesh.evaluated_get(dg)
    me = ev.to_mesh()
    n = len(me.vertices)
    buf = np.empty(n * 3, np.float32)
    me.vertices.foreach_get("co", buf)
    ev.to_mesh_clear()
    mw = np.array(mesh.matrix_world)
    return buf.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]


# ---------------------------------------------------------------------------------------------
# Write-back: a set of rotation deltas D (one per part) and the pelvis position onto the MMD rig.
# ---------------------------------------------------------------------------------------------
ROOT_CHAIN = ["全ての親", "センター", "グルーブ", "腰"]
_SIDE_BONES = ["肩P", "肩", "肩C", "腕", "腕捩", "腕捩1", "腕捩2", "腕捩3", "ひじ", "手捩", "手捩1", "手捩2", "手捩3",
               "手首", "足", "ひざ", "足首", "つま先", "足D", "ひざD", "足首D", "足先EX", "腰キャンセル",
               "足ＩＫ", "つま先ＩＫ", "足IK親"]
BODY_BONES = ROOT_CHAIN + ["下半身", "上半身", "上半身1", "上半身2", "首", "頭"] + \
    [f"{b}.{s}" for s in "LR" for b in _SIDE_BONES]


def strip_body_keys(arm):
    """Remove the VMD's keys on the root chain, the 19 bones and the helpers between them; leg IK off.
    Fingers, eyes and everything else keep their keys. Returns the names of bones whose keys were removed."""
    removed = set()
    body = set(BODY_BONES)
    for cont, fc in iter_fcurves(arm.animation_data.action):
        dp = fc.data_path
        if dp.startswith('pose.bones["'):
            b = dp.split('"')[1]
            if b in body:
                cont.fcurves.remove(fc)
                removed.add(b)
    for pb in arm.pose.bones:
        if pb.name in body:
            pb.rotation_quaternion = (1, 0, 0, 0)
            pb.location = (0, 0, 0)
            pb.scale = (1, 1, 1)
        for c in pb.constraints:
            # IK off; the knee's IK limit (min 0.5 deg) would otherwise bend ひざ at rest and leak into ひざD
            if c.type == "IK" or c.name == "mmd_ik_limit_override":
                c.mute = True
    return sorted(removed)


def twist_axes_from_action(arm):
    """Local axis each twist bone (腕捩, 手捩) is keyed about in the imported VMD. MMD Tools' conversion puts it a
    few degrees off the bone's Y; twisting about the same axis reproduces where the elbow and wrist land.
    Call before strip_body_keys."""
    axes = {}
    names = [f"{b}.{s}" for b in ("腕捩", "手捩") for s in "LR"]
    keys = {n: {} for n in names}
    for _, fc in iter_fcurves(arm.animation_data.action):
        dp = fc.data_path
        if dp.startswith('pose.bones["') and dp.endswith("rotation_quaternion"):
            n = dp.split('"')[1]
            if n in keys:
                for k in fc.keyframe_points:
                    keys[n].setdefault(round(k.co[0], 3), [1.0, 0.0, 0.0, 0.0])[fc.array_index] = k.co[1]
    for n, d in keys.items():
        best = None
        for q in d.values():
            v = np.array(q[1:])
            if best is None or np.linalg.norm(v) > np.linalg.norm(best):
                best = v
        if best is not None and np.linalg.norm(best) > 0.05:  # > ~6 deg of twist somewhere
            a = best / np.linalg.norm(best)
            axes[n] = a if a[1] > 0 else -a
    return axes


def _swing_twist(X, axis):
    q = Matrix(X.tolist()).to_quaternion()
    a = Vector(axis).normalized()
    proj = Vector((q.x, q.y, q.z)).dot(a)
    tw = Quaternion((q.w, a.x * proj, a.y * proj, a.z * proj))
    if tw.magnitude < 1e-9:
        tw = Quaternion((1, 0, 0, 0))
    tw.normalize()
    sw = q @ tw.inverted()
    return np.array(sw.to_matrix()), np.array(tw.to_matrix())


class Driver:
    """Poses one armature from (D[19,3,3], pelvis position). Helpers stay at rest; the D bones
    (足D/ひざD/足首D) carry the leg rotations directly while 足/ひざ/足首 stay at rest (the mesh is
    weighted to the D bones only, and their grants then add nothing)."""

    def __init__(self, arm, twist_axes=None):
        self.arm = arm
        self.twist_axes = twist_axes or {}
        self.bones = arm.data.bones
        self.R = {b.name: np.array(b.matrix_local.to_3x3()) for b in self.bones}
        self.H = {b.name: np.array(b.head_local) for b in self.bones}

    def pose(self, D, p_pelvis):
        R, bones, pbs = self.R, self.bones, self.arm.pose.bones
        Dn = dict(zip(PARTS, D))
        E = {}   # evaluated rotation each bone will have
        B = {}   # basis rotation written

        def ev(name):
            if name not in E:
                b = bones[name]
                if b.parent is None:
                    E[name] = R[name] @ B.get(name, np.eye(3))
                else:
                    pn = b.parent.name
                    E[name] = ev(pn) @ R[pn].T @ R[name] @ B.get(name, np.eye(3))
            return E[name]

        def e0(name):  # evaluated rotation with identity basis
            pn = bones[name].parent.name
            return ev(pn) @ R[pn].T @ R[name]

        def drive(name, part):
            B[name] = e0(name).T @ Dn[part] @ R[name]
            E[name] = Dn[part] @ R[name]

        def drive_pair(swing_bone, twist_bone, part):
            E0 = e0(swing_bone)
            C = R[swing_bone].T @ R[twist_bone]
            N = E0.T @ Dn[part] @ R[twist_bone]
            S, T = _swing_twist(N @ C.T, C @ self.twist_axes.get(twist_bone, np.array([0.0, 1.0, 0.0])))
            B[swing_bone] = S
            E[swing_bone] = E0 @ S
            B[twist_bone] = C.T @ T @ C
            E[twist_bone] = Dn[part] @ R[twist_bone]

        # pelvis on センター: rotation D_pelvis, translated so 下半身's head lands on p_pelvis
        c = "センター"
        Dp = Dn["pelvis"]
        B[c] = R[c].T @ Dp @ R[c]
        E[c] = Dp @ R[c]
        t = np.asarray(p_pelvis, float) - Dp @ (self.H["下半身"] - self.H[c])
        loc_c = R[c].T @ (t - self.H[c])
        drive("上半身", "waist")
        drive("上半身2", "chest")
        drive("首", "neck")
        drive("頭", "head")
        for s in "LR":
            drive(f"肩.{s}", f"collar_{s}")
            drive_pair(f"腕.{s}", f"腕捩.{s}", f"upper_arm_{s}")
            drive_pair(f"ひじ.{s}", f"手捩.{s}", f"forearm_{s}")
            drive(f"手首.{s}", f"hand_{s}")
            drive(f"足D.{s}", f"thigh_{s}")
            drive(f"ひざD.{s}", f"shin_{s}")
            drive(f"足首D.{s}", f"foot_{s}")
        for name, M in B.items():
            pbs[name].rotation_quaternion = Matrix(M.tolist()).to_quaternion()
        pbs[c].location = Vector(loc_c)


def pick_engine(scene):
    ids = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    scene.render.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in ids else "BLENDER_EEVEE_NEXT"


def plain_world(scene, rgb=(0.75, 0.78, 0.82), strength=1.0):
    world = bpy.data.worlds.new("pic_world")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (*rgb, 1)
    bg.inputs[1].default_value = strength
    sun = bpy.data.objects.new("pic_sun", bpy.data.lights.new("pic_sun", "SUN"))
    sun.data.energy = 2.5
    sun.rotation_euler = (math.radians(55), 0, math.radians(-25))
    scene.collection.objects.link(sun)
    scene.view_settings.view_transform = "Standard"
    return sun


def flat_material(name, rgb, alpha=1.0, emission=0.0, cull=True):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = 0.6
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*rgb, 1)
        bsdf.inputs["Emission Strength"].default_value = emission
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        if hasattr(m, "surface_render_method"):
            m.surface_render_method = "BLENDED"
        if hasattr(m, "use_transparency_overlap"):
            m.use_transparency_overlap = False
    m.use_backface_culling = cull
    m.diffuse_color = (*rgb, alpha)
    return m


def stamp(scene, note, size=28):
    r = scene.render
    r.use_stamp = bool(note)
    for k in ("use_stamp_date", "use_stamp_render_time", "use_stamp_camera", "use_stamp_lens", "use_stamp_time",
              "use_stamp_scene", "use_stamp_filename", "use_stamp_marker", "use_stamp_sequencer_strip",
              "use_stamp_memory", "use_stamp_hostname", "use_stamp_frame_range", "use_stamp_frame"):
        if hasattr(r, k):
            setattr(r, k, False)
    r.use_stamp_note = True
    r.stamp_note_text = note
    r.stamp_font_size = size
    r.stamp_background = (0, 0, 0, 0.65)
    r.stamp_foreground = (1, 1, 1, 1)
