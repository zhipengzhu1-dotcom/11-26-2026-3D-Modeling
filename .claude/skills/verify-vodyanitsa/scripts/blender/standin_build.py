"""STAND-IN BUILD. Not the real Build.

Imports her model from the local copy, plays the Reference Motion back on the armature as plain
keyframes, and saves the result in the Build contract shape (see common.py). It has no Simulation
Body, no trained controller, no toon look and no Secondary Physics: every rigid body and joint is
deleted after their bone list is recorded, so hair, skirt and ribbons are carried rigidly by their
parent bones.

Usage (via the CLI): Blender -b --python standin_build.py -- <pmx> <vmd> <out_dir>
"""
import os
import sys
import time

import bpy

sys.dont_write_bytecode = True  # keep __pycache__ out of the tracked skill folder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

SCALE = 0.08  # metres per MMD unit; she stands 1.58 m with soles at z = 0


def main():
    pmx, vmd, out = common.args()[:3]
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    common.enable_mmd_tools()
    bpy.ops.mmd_tools.import_model(filepath=pmx, scale=SCALE,
                                   types={"MESH", "ARMATURE", "PHYSICS", "MORPHS"}, log_level="ERROR")
    root = next(o for o in bpy.data.objects if getattr(o, "mmd_type", "") == "ROOT")
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and getattr(o, "mmd_type", "NONE") == "NONE"]
    if len(meshes) != 1:
        raise SystemExit(f"VERIFY-ERROR: expected one Visible Mesh object, found {len(meshes)}")
    mesh = meshes[0]

    # Bones that the model's own Secondary Physics moves (dynamic rigid bodies, type 1 and 2).
    trailing = sorted({o.mmd_rigid.bone for o in bpy.data.objects
                       if getattr(o, "mmd_type", "") == "RIGID_BODY" and o.mmd_rigid.type in ("1", "2")
                       and o.mmd_rigid.bone})

    # Stand-in: no physics at all. Remove rigid bodies, joints and the rigid body world.
    doomed = [o for o in bpy.data.objects
              if getattr(o, "mmd_type", "") in ("RIGID_BODY", "JOINT", "RIGID_GRP_OBJ", "JOINT_GRP_OBJ")]
    for o in doomed:
        bpy.data.objects.remove(o, do_unlink=True)
    if bpy.context.scene.rigidbody_world is not None:
        bpy.ops.rigidbody.world_remove()

    # Known look quirk: transparent face overlays import as Dithered and leave a dark lace-like patch.
    for name in ("颜2", "照れ"):
        m = bpy.data.materials.get(name)
        if m is not None and hasattr(m, "surface_render_method"):
            m.surface_render_method = "BLENDED"

    # Reference Motion as plain playback.
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    res = bpy.ops.mmd_tools.import_vmd(filepath=vmd, scale=SCALE, margin=0, bone_mapper="PMX",
                                       use_pose_mode=False, update_scene_settings=True, log_level="ERROR")
    if "FINISHED" not in res:
        raise SystemExit(f"VERIFY-ERROR: VMD import failed: {res}")
    scene = bpy.context.scene
    scene.render.fps = 30
    act = arm.animation_data.action if arm.animation_data else None
    if act is None:
        raise SystemExit("VERIFY-ERROR: the Reference Motion left no action on the armature")

    mesh["vodyanitsa_role"] = "visible_mesh"
    blend = os.path.join(out, "build.blend")
    os.makedirs(out, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend, compress=False)

    build = {
        "kind": "stand-in",
        "what": "Reference Motion played back on the imported model; no Simulation Body, no controller, "
                "no toon look, no Secondary Physics (rigid bodies deleted)",
        "blend": blend,
        "visible_mesh": mesh.name,
        "armature": arm.name,
        "frame_start": int(scene.frame_start),
        "frame_end": int(scene.frame_end),
        "fps": 30,
        "trailing_bones": trailing,
        "model_file": os.path.basename(pmx),
        "motion_file": os.path.basename(vmd),
        "vertices": len(mesh.data.vertices),
        "triangles": sum(len(p.vertices) - 2 for p in mesh.data.polygons),
        "materials": len(mesh.data.materials),
        "bones": len(arm.data.bones),
        "build_seconds": round(time.time() - t0, 1),
    }
    common.write_json(os.path.join(out, "build.json"), build)
    print(f"BUILD READY {blend} frames {build['frame_start']}..{build['frame_end']} "
          f"trailing_bones {len(trailing)} in {build['build_seconds']} s")


main()
