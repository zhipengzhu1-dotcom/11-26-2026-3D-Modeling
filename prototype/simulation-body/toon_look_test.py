"""PROTOTYPE (throwaway). Renders her once in the settled toon look, to check toon_look.py by eye.

  Blender -b --python prototype/simulation-body/toon_look_test.py -- [out_dir] [figures]

Imports her (once by default; pass figures=3 to time three side by side), poses her from a mid-dance frame of the
stage 1 dance, applies the look and writes full.png (1920x1080, full body) and close.png (face and shoulders) plus
timing.json into out_dir (default build/first-look/toon_test/, git-ignored).
"""
import json
import math
import os
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import pic_util as U  # noqa: E402
import toon_look  # noqa: E402

FRAME = 400  # mid-dance
a = U.args()
out = os.path.abspath(a[0]) if a else os.path.join(U.BUILD, "toon_test")
n_fig = int(a[1]) if len(a) > 1 else 1
os.makedirs(out, exist_ok=True)
vmd = os.path.join(U.REPO, "assets", "motion", "toki-yo-tomare", "時よ止まれ.vmd")

t0 = time.time()
U.reset()
scene = bpy.context.scene
figs = []
for k in range(n_fig):
    root, arm, mesh = U.import_her()
    U.import_vmd(root, vmd)
    root.location.x = (k - (n_fig - 1) / 2) * 1.05
    figs.append((arm, mesh))
for o in bpy.data.objects:
    if o.type in ("EMPTY", "ARMATURE"):
        o.hide_render = True
scene.frame_set(FRAME)
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
scene.collection.objects.link(cam)
scene.camera = cam
cam.data.lens = 50
cam.data.sensor_fit = "HORIZONTAL"
cam.data.sensor_width = 36
cam.data.clip_end = 200


def aim(target, d, elev_deg, lens):
    e = math.radians(elev_deg)
    direction = Vector((0, -math.cos(e), math.sin(e)))
    cam.data.lens = lens
    cam.location = target + direction * d
    cam.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()


arm0 = figs[n_fig // 2][0]
head = arm0.matrix_world @ arm0.pose.bones["頭"].head
aim(Vector((0, head.y, 0.8)), 4.2 if n_fig == 1 else 5.2, 10, 50 if n_fig == 1 else 35)

t1 = time.time()
made = toon_look.apply(scene, [m for _, m in figs], cam)
t_apply = time.time() - t1
t_setup = time.time() - t0

times = {}


def shot(name):
    scene.render.filepath = os.path.join(out, name + ".png")
    t = time.time()
    bpy.ops.render.render(write_still=True)
    times[name] = round(time.time() - t, 2)


shot("full")           # first render includes shader compilation
shot("full_again")     # steady-state cost of one frame
scene.frame_set(FRAME + 1)
shot("full_next")      # next frame, pose changed
scene.frame_set(FRAME)
aim(Vector((head.x, head.y, head.z - 0.12)), 1.25, 8, 50)
shot("close")
os.remove(os.path.join(out, "full_again.png"))
os.remove(os.path.join(out, "full_next.png"))
res = {"figures": n_fig, "frame": FRAME, "materials_built": made["materials"], "setup_s": round(t_setup, 1),
       "apply_s": round(t_apply, 1), "render_s": times}
with open(os.path.join(out, "timing.json"), "w") as f:
    json.dump(res, f, indent=1)
print("TOON TEST", json.dumps(res), flush=True)
