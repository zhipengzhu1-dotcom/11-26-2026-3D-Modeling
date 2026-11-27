"""PROTOTYPE (throwaway). A plain view of her Simulation Body alone, from MuJoCo's own offscreen renderer.

  uv run --with mujoco --with numpy --with scipy --with pillow python body_alone_clip.py <round> [clip ...]

For each clip in build/first-look/clips.json: review/first-look/<round>/body_alone_<name>.mp4, soft (left)
beside stiff (right), a camera from her front following her, a checker floor; plus three stills per clip and
two rest-pose stills (body_alone_rest_front.png, body_alone_rest_side.png).
"""
import json
import os
import subprocess
import sys

import mujoco
import numpy as np
from PIL import Image, ImageDraw
from scipy.spatial.transform import Rotation as Rot

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import body as B  # noqa: E402

W, H = 1280, 720
GAP = 1.0  # m between the two figures


def view_model(n_fig, floor=True):
    """n_fig copies of her 19 parts as mocap bodies carrying her solids (geoms placed relative to the joint)."""
    bj = json.load(open(os.path.join(B.OUT, "body.json")))
    spec = mujoco.MjSpec()
    spec.compiler.degree = False
    spec.visual.global_.offwidth, spec.visual.global_.offheight = W, H
    spec.visual.quality.shadowsize = 4096
    spec.visual.headlight.ambient = [0.35, 0.35, 0.35]
    spec.visual.headlight.diffuse = [0.5, 0.5, 0.5]
    tex = spec.add_texture(name="grid", type=mujoco.mjtTexture.mjTEXTURE_2D, builtin=mujoco.mjtBuiltin.mjBUILTIN_CHECKER,
                           rgb1=[0.82, 0.82, 0.85], rgb2=[0.62, 0.62, 0.68], width=512, height=512)
    mat = spec.add_material(name="grid", texrepeat=[10, 10], reflectance=0.05)
    mat.textures[mujoco.mjtTextureRole.mjTEXROLE_RGB] = "grid"
    if floor:
        spec.worldbody.add_geom(name="floor", type=mujoco.mjtGeom.mjGEOM_PLANE, size=[6, 6, 0.1], material="grid")
    spec.worldbody.add_light(pos=[0.5, -2, 3], dir=[-0.2, 0.6, -1], diffuse=[0.6, 0.6, 0.6], castshadow=True)
    jp = {p["name"]: np.array(p["joint_pos"]) for p in bj["parts"]}
    for k in range(n_fig):
        for p in B.PARTS:
            b = spec.worldbody.add_body(name=f"f{k}_{p}", mocap=True, pos=list(jp[p]))
            for i, g in enumerate(bj["geoms"]):
                if g["part"] != p:
                    continue
                typ = {"capsule": mujoco.mjtGeom.mjGEOM_CAPSULE, "box": mujoco.mjtGeom.mjGEOM_BOX,
                       "sphere": mujoco.mjtGeom.mjGEOM_SPHERE}[g["type"]]
                q = Rot.from_matrix(np.array(g["rot"])).as_quat()
                rgba = list(B.COLORS[p]) + [1]
                if g["floor_contact"]:
                    rgba = [0.95, 0.15, 0.15, 1]
                b.add_geom(type=typ, size=list(g["size"]) + [0] * (3 - len(g["size"])),
                           pos=list(np.array(g["pos"]) - jp[p]), quat=[q[3], q[0], q[1], q[2]], rgba=rgba,
                           contype=0, conaffinity=0)
            b.add_geom(type=mujoco.mjtGeom.mjGEOM_SPHERE, size=[0.008, 0, 0], rgba=[0.1, 0.1, 0.1, 1],
                       contype=0, conaffinity=0, group=0)  # joint marker
    m = spec.compile()
    return m, mujoco.MjData(m)


def pose(m, d, k, pos, rot, shift):
    for i, p in enumerate(B.PARTS):
        mid = m.body_mocapid[m.body(f"f{k}_{p}").id]
        d.mocap_pos[mid] = pos[i] + shift
        q = Rot.from_matrix(rot[i]).as_quat()
        d.mocap_quat[mid] = [q[3], q[0], q[1], q[2]]


def camera(lookat, dist=3.2, az=90, el=-8):
    cam = mujoco.MjvCamera()
    cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.lookat[:] = lookat
    cam.distance, cam.azimuth, cam.elevation = dist, az, el
    return cam


def label(img, texts):
    im = Image.fromarray(img)
    dr = ImageDraw.Draw(im)
    for (x, y), t in texts:
        dr.rectangle([x - 4, y - 2, x + 8 * len(t) + 4, y + 14], fill=(0, 0, 0))
        dr.text((x, y), t, fill=(255, 255, 255))
    return np.array(im)


def main():
    rnd = sys.argv[1]
    only = sys.argv[2:]
    out = os.path.join(B.REPO, "review", "first-look", rnd)
    os.makedirs(out, exist_ok=True)
    clips = json.load(open(os.path.join(B.OUT, "clips.json"), encoding="utf-8"))

    # rest-pose stills
    m, d = view_model(1)
    r = mujoco.Renderer(m, H, W)
    pose(m, d, 0, np.array([p["joint_pos"] for p in json.load(open(os.path.join(B.OUT, "body.json")))["parts"]]),
         np.tile(np.eye(3), (19, 1, 1)), np.zeros(3))
    mujoco.mj_kinematics(m, d)
    for nm, az in (("front", 90), ("side", 0), ("back", 270)):
        r.update_scene(d, camera([0, 0, 0.8], 2.4, az, -5))
        Image.fromarray(label(r.render(), [((20, 20), f"Simulation Body, rest pose, {nm}")])).save(
            os.path.join(out, f"body_alone_rest_{nm}.png"))
    r.update_scene(d, camera([0, 0, 0.08], 0.6, 60, -15))
    Image.fromarray(label(r.render(), [((20, 20), "shoes: red = floor-contact shapes (front pad, heel tip)")])).save(
        os.path.join(out, "body_alone_rest_shoes.png"))
    r.update_scene(d, camera([0.03, 0, 0.07], 0.45, 0, -3))
    Image.fromarray(label(r.render(), [((20, 20), "left shoe from the side (her front is to the right)")])).save(
        os.path.join(out, "body_alone_rest_shoe_side.png"))
    r.close()

    for c in clips:
        if only and c["name"] not in only:
            continue
        z = np.load(os.path.join(B.OUT, c["npz"]))
        floor = c["hips"] != "pinned"
        m, d = view_model(2, floor)
        r = mujoco.Renderer(m, H, W)
        T = len(z["src_frame"])
        pel = (z["pos_soft"][:, 0] + z["pos_stiff"][:, 0]) / 2
        k = 30
        track = np.array([pel[max(0, t - k):t + k + 1].mean(0) for t in range(T)])
        dst = os.path.join(out, f"body_alone_{c['name']}.mp4")
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                               f"{W}x{H}", "-r", "30", "-i", "-", "-pix_fmt", "yuv420p", "-vcodec", "libx264",
                               "-crf", "20", dst], stdin=subprocess.PIPE)
        stills = {T // 4, T // 2, (3 * T) // 4}
        for t in range(T):
            for kf, v in ((0, "soft"), (1, "stiff")):
                pose(m, d, kf, z[f"pos_{v}"][t], z[f"rot_{v}"][t], np.array([(-1 if kf == 0 else 1) * GAP / 2, 0, 0]))
            mujoco.mj_kinematics(m, d)
            look = np.array([track[t, 0], track[t, 1], 0.85 if c["framing"] == "full" else 1.05])
            r.update_scene(d, camera(look, 3.0 if c["framing"] == "full" else 2.4))
            img = label(r.render(), [((W // 4, 20), "soft"), ((3 * W // 4, 20), "stiff"),
                                     ((20, H - 30), f"{c["name"]}  frame {t}/{T} (source {int(z['src_frame'][t])})")])
            ff.stdin.write(img.tobytes())
            if t in stills:
                Image.fromarray(img).save(os.path.join(out, f"body_alone_{c['name']}_t{t:03d}.png"))
        ff.stdin.close()
        ff.wait()
        r.close()
        print("wrote", dst, T, "frames", flush=True)


if __name__ == "__main__":
    main()
