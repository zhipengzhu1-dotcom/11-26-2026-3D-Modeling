"""PROTOTYPE (throwaway). A plain close-up of her as-authored arm at one frame of a Reference Motion (headless Blender).

  Blender -b --python elbow_still.py -- <vmd> <frame> <L|R> <out.png> <label>

The camera looks at her elbow square-on to the plane of upper arm and forearm, from the side away from her body,
so a bend backward would show as a kink the wrong way. Prints the elbow's inner angle (shoulder-elbow-wrist,
from the evaluated bone heads) at that frame and at rest.
"""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = [sys.argv[0], "--"] + sys.argv[sys.argv.index("--") + 1:]
import extract  # noqa: E402

vmd, frame, side, out, label = sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5], sys.argv[6]
root, arm, mesh, _ = extract.load_model()
B = arm.data.bones


def inner(sh, el, wr):
    a, b = np.array(sh) - np.array(el), np.array(wr) - np.array(el)
    return math.degrees(math.acos(np.dot(a, b) / np.linalg.norm(a) / np.linalg.norm(b)))


rest = inner(B[f"腕.{side}"].head_local, B[f"ひじ.{side}"].head_local, B[f"手首.{side}"].head_local)
bpy.ops.object.select_all(action="DESELECT")
root.select_set(True)
bpy.context.view_layer.objects.active = root
bpy.ops.mmd_tools.import_vmd(filepath=vmd, scale=extract.SCALE, margin=0, bone_mapper="PMX", use_pose_mode=False,
                             update_scene_settings=True, log_level="ERROR")
scene = bpy.context.scene
scene.frame_set(frame)
P = arm.pose.bones
sh, el, wr = (Vector(P[f"{n}.{side}"].head) for n in ("腕", "ひじ", "手首"))
ang = inner(sh, el, wr)
n = (el - sh).cross(wr - el)
if n.length < 1e-6:
    n = (el - sh).cross(Vector((0, 0, 1)))
n.normalize()
chest = Vector(P["上半身2"].head)
if n.dot(el - chest) < 0:
    n = -n
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
scene.collection.objects.link(cam)
scene.camera = cam
cam.location = el + n * 0.75
cam.rotation_euler = (el - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 50
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 3
sun.rotation_euler = cam.rotation_euler
scene.collection.objects.link(sun)
ids = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
scene.render.engine = "BLENDER_WORKBENCH" if "BLENDER_WORKBENCH" in ids else ids[0]
scene.render.resolution_x = scene.render.resolution_y = 900
scene.render.film_transparent = False
scene.render.use_stamp = True
for k in ("use_stamp_date", "use_stamp_render_time", "use_stamp_camera", "use_stamp_lens", "use_stamp_scene",
          "use_stamp_filename", "use_stamp_memory", "use_stamp_hostname", "use_stamp_time"):
    if hasattr(scene.render, k):
        setattr(scene.render, k, False)
scene.render.use_stamp_frame = True
scene.render.use_stamp_note = True
scene.render.stamp_note_text = f"{label}: {side} arm, inner elbow angle {ang:.1f} deg (rest {rest:.1f}; 180 = straight)"
scene.render.stamp_font_size = 22
for o in bpy.data.objects:
    if o.type == "ARMATURE" or (o.type == "EMPTY"):
        o.hide_render = True
os.makedirs(os.path.dirname(out), exist_ok=True)
scene.render.filepath = out
bpy.ops.render.render(write_still=True)
print(f"ELBOW {label} side {side} frame {frame}: inner angle {ang:.2f} deg, rest {rest:.2f} deg -> {out}")
