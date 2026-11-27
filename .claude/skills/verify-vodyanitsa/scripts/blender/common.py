"""Shared Blender-side helpers for verify-vodyanitsa (run inside Blender, never imported by the CLI).

The Build contract every stage relies on (stand-in today, the real Build later):
  build.json next to build.blend, holding at least
    blend, visible_mesh, armature, frame_start, frame_end, fps, trailing_bones, kind
  build.blend: the Visible Mesh object (deformed by the armature), its armature with the
  Reference Motion (or the trained controller's output) baked or keyed over frame_start..frame_end,
  and the armature REST pose equal to her rest pose.
"""
import json
import math
import os
import sys

import bpy
from mathutils import Vector


def args():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def enable_mmd_tools():
    import addon_utils
    for m in addon_utils.modules():
        if m.__name__.endswith("mmd_tools"):
            addon_utils.enable(m.__name__, default_set=False)
            return m.__name__
    raise SystemExit("VERIFY-ERROR: the MMD Tools extension is not installed in this Blender")


def open_build(build_json):
    with open(build_json, encoding="utf-8") as f:
        build = json.load(f)
    bpy.ops.wm.open_mainfile(filepath=build["blend"])
    mesh = bpy.data.objects[build["visible_mesh"]]
    arm = bpy.data.objects[build["armature"]]
    return build, mesh, arm


def pick_engine(scene):
    ids = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    scene.render.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in ids else "BLENDER_EEVEE_NEXT"


def dance_track(scene, mesh, frame_start, frame_end, every=5):
    """Per-frame centre of her evaluated Visible Mesh (x, y) and the overall bounds, over the whole
    Reference Motion. Always sampled over the full range so the camera never depends on preview options."""
    mn = Vector((1e9,) * 3)
    mx = Vector((-1e9,) * 3)
    dg = bpy.context.evaluated_depsgraph_get()
    samples = []
    for f in sorted(set(list(range(frame_start, frame_end + 1, every)) + [frame_end])):
        scene.frame_set(f)
        ev = mesh.evaluated_get(dg)
        pts = [mesh.matrix_world @ Vector(c) for c in ev.bound_box]
        for w in pts:
            for i in range(3):
                mn[i] = min(mn[i], w[i])
                mx[i] = max(mx[i], w[i])
        c = sum(pts, Vector()) / 8
        samples.append((f, c.x, c.y))
    # linear interpolation to every frame, then a centred 1.5 s moving average
    track = {}
    for (f0, x0, y0), (f1, x1, y1) in zip(samples, samples[1:]):
        for f in range(f0, f1 + 1):
            t = (f - f0) / max(1, f1 - f0)
            track[f] = (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
    frames = sorted(track)
    half = int(scene.render.fps * 0.75)
    smooth = {}
    for i, f in enumerate(frames):
        win = frames[max(0, i - half): i + half + 1]
        smooth[f] = (sum(track[g][0] for g in win) / len(win), sum(track[g][1] for g in win) / len(win))
    return smooth, mn, mx


def fit_distance(scene, cam, half_w, half_d, height, direction, margin=0.05):
    """Smallest camera distance from a box centred on the origin (|x| <= half_w, |y| <= half_d,
    0 <= z <= height) that keeps every corner in frame, looking along -direction at the box centre."""
    from bpy_extras.object_utils import world_to_camera_view
    target = Vector((0, 0, height * 0.5))
    corners = [Vector((x, y, z)) for x in (-half_w, half_w) for y in (-half_d, half_d) for z in (0, height)]
    lo, hi = 0.5, 50.0
    for _ in range(40):
        d = (lo + hi) / 2
        cam.location = target + direction * d
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        bpy.context.view_layer.update()
        ok = all(margin <= v.x <= 1 - margin and margin <= v.y <= 1 - margin and v.z > 0
                 for v in (world_to_camera_view(scene, cam, c) for c in corners))
        hi, lo = (d, lo) if ok else (hi, d)
    return hi


def setup_stage(build, mesh, arm, res_pct=100, stamp_note=""):
    """Deterministic review stage: floor, light, world, and the review camera (a follow camera).
    The clip and the 穿模 scan stills both call this, so a still matches the clip frame exactly."""
    scene = bpy.context.scene
    pick_engine(scene)
    scene.view_settings.view_transform = "Standard"
    scene.render.fps = int(build["fps"])
    scene.frame_start, scene.frame_end = int(build["frame_start"]), int(build["frame_end"])
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = int(res_pct)
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False

    for o in bpy.data.objects:
        if o not in (mesh, arm) and o.type in ("EMPTY",):
            o.hide_render = True
    arm.hide_render = True

    world = bpy.data.worlds.new("verify_world")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.75, 0.78, 0.82, 1)
    bg.inputs[1].default_value = 1.0

    sun = bpy.data.objects.new("verify_sun", bpy.data.lights.new("verify_sun", "SUN"))
    sun.data.energy = 2.5
    sun.rotation_euler = (math.radians(55), 0, math.radians(-25))
    scene.collection.objects.link(sun)

    track, mn, mx = dance_track(scene, mesh, scene.frame_start, scene.frame_end)
    mn = Vector((mn.x, mn.y, min(mn.z, 0.0)))

    # floor: a checker plane at z = 0 so floor 穿模 is visible
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, 0.0))
    floor = bpy.context.active_object
    floor.name = "verify_floor"
    floor.scale = (mx.x - mn.x + 1.0, mx.y - mn.y + 1.0, 1)
    mat = bpy.data.materials.new("verify_floor")
    mat.use_nodes = True
    nt = mat.node_tree
    chk = nt.nodes.new("ShaderNodeTexChecker")
    chk.inputs["Color1"].default_value = (0.55, 0.56, 0.6, 1)
    chk.inputs["Color2"].default_value = (0.42, 0.43, 0.47, 1)
    bsdf = nt.nodes.get("Principled BSDF")
    nt.links.new(chk.outputs["Color"], bsdf.inputs["Base Color"])
    floor.data.materials.append(mat)

    chk.inputs["Scale"].default_value = max(floor.scale.x, floor.scale.y) / 0.25
    floor.scale.x = floor.scale.y = max(floor.scale.x, floor.scale.y)

    cam = bpy.data.objects.new("verify_camera", bpy.data.cameras.new("verify_camera"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.lens = 50
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.sensor_width = 36
    # Follow camera: fixed direction from her front (she faces -Y), slightly above; it slides with her
    # smoothed centre and keeps a 2.4 m wide, 1.85 m tall box in frame. Keyed on every frame.
    direction = Vector((0.0, -1.0, 0.25)).normalized()
    height = max(mx.z, 1.7) + 0.15
    dist = fit_distance(scene, cam, 1.2, 0.6, height, direction)
    rot = (-direction).to_track_quat("-Z", "Y").to_euler()
    for f, (x, y) in sorted(track.items()):
        cam.location = Vector((x, y, height * 0.5)) + direction * dist
        cam.rotation_euler = rot
        cam.keyframe_insert("location", frame=f)
    cam.keyframe_insert("rotation_euler", frame=scene.frame_start)
    cam.data.clip_end = dist * 6
    scene["verify_camera"] = {"kind": "follow", "distance_m": dist, "direction": list(direction)}

    scene.render.use_stamp = bool(stamp_note)
    if stamp_note:
        r = scene.render
        for k in ("use_stamp_date", "use_stamp_render_time", "use_stamp_camera", "use_stamp_lens",
                  "use_stamp_scene", "use_stamp_filename", "use_stamp_marker", "use_stamp_sequencer_strip",
                  "use_stamp_memory", "use_stamp_hostname", "use_stamp_frame_range"):
            if hasattr(r, k):
                setattr(r, k, False)
        r.use_stamp_time = True
        r.use_stamp_frame = True
        r.use_stamp_note = True
        r.stamp_note_text = stamp_note
        r.stamp_font_size = 28
        r.stamp_background = (0, 0, 0, 0.6)
        r.stamp_foreground = (1, 1, 1, 1)
    return scene, cam, floor
