"""Render the stage 1 clip frames: the Build's Reference Motion from the fixed review camera.

Usage (via the CLI): Blender -b --python clip.py -- <build.json> <frames_dir> <timing.json> <step> <res_pct> <start> <end> <note>
Writes <frames_dir>/f_NNNNNN.png for frames start, start+step, ... end, and a timing JSON.
"""
import os
import sys
import time

import bpy

sys.dont_write_bytecode = True  # keep __pycache__ out of the tracked skill folder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402


def main():
    build_json, frames_dir, timing_json, step, res_pct, start, end, note = common.args()[:8]
    step, res_pct, start, end = int(step), int(res_pct), int(start), int(end)
    build, mesh, arm = common.open_build(build_json)
    scene, cam, floor = common.setup_stage(build, mesh, arm, res_pct=res_pct, stamp_note=note)
    os.makedirs(frames_dir, exist_ok=True)
    frames = list(range(start, end + 1, step))
    times = []
    for i, f in enumerate(frames):
        t = time.time()
        scene.frame_set(f)
        scene.render.filepath = os.path.join(frames_dir, f"f_{i:06d}.png")
        bpy.ops.render.render(write_still=True)
        times.append(time.time() - t)
        if i % 25 == 0:
            print(f"CLIP frame {f} ({i + 1}/{len(frames)}) {times[-1]:.2f} s", flush=True)
    common.write_json(timing_json, {
        "frames_rendered": len(frames), "frame_step": step, "res_pct": res_pct,
        "resolution": [scene.render.resolution_x * res_pct // 100, scene.render.resolution_y * res_pct // 100],
        "first_frame": start, "last_frame": frames[-1],
        "seconds_total": round(sum(times), 2),
        "seconds_per_frame_mean": round(sum(times) / len(times), 3),
        "seconds_first_frame": round(times[0], 3),
        "camera": {"location": list(cam.location), "rotation_euler": list(cam.rotation_euler), "lens": cam.data.lens},
    })
    print(f"CLIP DONE {len(frames)} frames in {sum(times):.1f} s", flush=True)


main()
