"""PROTOTYPE (throwaway). Moves her Simulation Body through the first-round clips: ref, soft, stiff.

  uv run --with mujoco --with numpy --with scipy python simulate.py

Reads build/first-look/{body.xml, body_info.json, extract/...}; writes build/first-look/clips.json,
build/first-look/sim/<name>.npz (the contract) and build/first-look/sim_info.json (checks and numbers).
Hips carried: the pelvis has six root joints (three slides, then hinges about z, x, y) held by stiff (20 Hz,
critically damped) position servos with the reference's velocity and acceleration fed forward, so the floor
cannot push her hips off the path. Her joints: position servos toward the reference angles, damping on the error velocity,
gravity compensated through the actuators (body gravcomp with actuator gravcomp on her joints).
"""
import json
import os
import sys
import time

import mujoco
import numpy as np
from scipy.interpolate import CubicSpline
from scipy.spatial.transform import Rotation as Rot

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import body as B  # noqa: E402

OUT = os.environ.get("FIRSTLOOK_DIR", B.OUT)   # where body.xml / body_info.json are read and results written
FPS = 30
SUB = 40                      # physics steps per output frame -> dt = 1/1200 s
VARIANTS = {"soft": (2.5, 0.35), "stiff": (10.0, 1.0)}  # natural frequency (Hz), damping ratio
# Soft only: distal joints carry light parts that the limb above whips about; at 2.5 Hz the feet flail
# (+-50-70 deg in the kick). These multiply the soft frequency and set the soft damping ratio per joint group.
SOFT_GROUPS = {"forearm": (1.4, 0.35), "shin": (1.4, 0.35), "hand": (2.0, 0.5), "foot": (2.0, 0.5)}
ROOT_HZ = 20.0                # the invisible hand
# Tuning per figure (epochs override it with TUNING=<json>). These defaults are round 2 exactly.
#   hz, zeta: natural frequency and damping ratio of her joint servos; groups: {joint group: [hz multiplier, zeta]}
#   ff_vel: share of the reference velocity fed forward into the servo's damping term (1 = damp the error only)
#   ff_id: share of the inverse-dynamics torque of the reference motion (inertia and Coriolis; gravity is already
#          compensated) fed forward
#   damping: {group: passive joint damping, N m s/rad}; armature: added rotor inertia per joint (kg m^2)
#   contact_solref: [time constant, damping ratio] for every solid of hers (None = MuJoCo default 0.02, 1)
#   torque_limit: N m cap on every joint servo of hers (absent or None = no cap)
DEFAULT_TUNING = {
    "stiff": {"hz": 10.0, "zeta": 1.0, "groups": {}, "ff_vel": 1.0, "ff_id": 0.0, "damping": {}, "armature": 0.0,
              "contact_solref": None},
    "soft": {"hz": 2.5, "zeta": 0.35, "groups": {k: list(v) for k, v in SOFT_GROUPS.items()}, "ff_vel": 1.0,
             "ff_id": 0.0, "damping": {}, "armature": 0.0, "contact_solref": None},
}
TUNING = json.load(open(os.environ["TUNING"], encoding="utf-8")) if os.environ.get("TUNING") else DEFAULT_TUNING
HI = 5                        # joint angles are also logged every HI physics steps (240 Hz) for the lag measure
DANCE = "toki-yo-tomare/時よ止まれ.vmd"
WALK = "2.歩き10L_乙女_(40f_前移動20).vmd"
WALK_FALLBACK = "walk-fuyuneko-aruku/unpacked/歩く/歩く.vmd"
HEART = "ターンしてハートモーション.vmd"
PEACE = "ピスピース_あぴミク.vmd"
SING = "Jackie Evancho  Ave Maria.vmd"


def find(motions, tail):
    return next(m for m in motions if m["name"].endswith(tail))


def load(m):
    z = np.load(os.path.join(B.EX, "motion", m["key"] + ".npz"))
    return z["frames"], z["D"].astype(float), z["P"].astype(float), z["mouth"].astype(float)


# ---------------------------------------------------------------- models
def make_model(mode):
    spec = mujoco.MjSpec.from_file(os.path.join(OUT, "body.xml"))
    pel = spec.body("pelvis")
    spec.delete(spec.joint("root"))
    if mode == "carried":
        for nm, ax, slide in (("root_x", [1, 0, 0], 1), ("root_y", [0, 1, 0], 1), ("root_z", [0, 0, 1], 1),
                              ("root_rz", [0, 0, 1], 0), ("root_rx", [1, 0, 0], 0), ("root_ry", [0, 1, 0], 0)):
            pel.add_joint(name=nm, type=mujoco.mjtJoint.mjJNT_SLIDE if slide else mujoco.mjtJoint.mjJNT_HINGE, axis=ax)
        # the new joints must come first in the body: MjSpec appends, so re-add her (none on the pelvis anyway)
    else:
        spec.delete(spec.geom("floor"))
        # A pelvis welded to the world counts as world, and MuJoCo does not filter parent-child contacts
        # against the world; put back exactly the filtering a moving pelvis gets.
        for ch in ("waist", "thigh_L", "thigh_R"):
            spec.add_exclude(bodyname1="pelvis", bodyname2=ch)
    for b in spec.bodies:
        if b.name != "world":
            b.gravcomp = 1.0
    for j in spec.joints:
        if not j.name.startswith("root"):
            j.actgravcomp = 1
    spec.option.timestep = 1.0 / (FPS * SUB)
    m = spec.compile()
    return spec, m


def body_dofs(m):
    names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, j) for j in range(m.njnt)]
    bj = [j for j, n in enumerate(names) if not n.startswith("root")]
    rj = [j for j, n in enumerate(names) if n.startswith("root")]
    return names, bj, rj


def vr_full(v, m):
    """A reference velocity or acceleration laid out by qpos address -> by dof address (all hinges/slides)."""
    out = np.zeros(m.nv)
    for j in range(m.njnt):
        out[m.jnt_dofadr[j]] = v[m.jnt_qposadr[j]]
    return out


def mdiag(m, d):
    F = np.zeros((m.nv, m.nv))
    mujoco.mj_fullM(m, d, F)
    return np.diag(F)


def effective_inertia(m, qs):
    """Per joint: the 90th percentile over the given poses of the diagonal of the joint-space inertia (the
    inertia that joint moves when every other joint is held)."""
    d = mujoco.MjData(m)
    names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, j) for j in range(m.njnt)]
    vals = []
    for q in qs:
        d.qpos[:] = q
        mujoco.mj_forward(m, d)
        vals.append(mdiag(m, d))
    v = np.percentile(np.array(vals), 90, axis=0)
    return {names[j]: float(v[m.jnt_dofadr[j]]) for j in range(m.njnt)}


def add_servos(spec, m, tune, inertia):
    """Position actuators on every hinge of her body (and on the root joints when carried)."""
    hz, zeta = tune["hz"], tune["zeta"]
    names, bj, rj = body_dofs(m)
    gains = {}
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    Md = mdiag(m, d)
    for j in rj + bj:
        I = inertia.get(names[j], Md[m.jnt_dofadr[j]]) if j in bj else Md[m.jnt_dofadr[j]]
        w, z = (2 * np.pi * ROOT_HZ, 1.0) if j in rj else (2 * np.pi * hz, zeta)
        grp = B.base(names[j].rsplit("_", 1)[0]) if j in bj else None
        if j in bj and grp in tune["groups"]:
            w, z = w * tune["groups"][grp][0], tune["groups"][grp][1]
        kp, kv = I * w * w, 2 * z * I * w
        a = spec.add_actuator(name="act_" + names[j], target=names[j], trntype=mujoco.mjtTrn.mjTRN_JOINT)
        a.gaintype = mujoco.mjtGain.mjGAIN_FIXED
        a.biastype = mujoco.mjtBias.mjBIAS_AFFINE
        a.gainprm[0] = kp
        a.biasprm[0], a.biasprm[1], a.biasprm[2] = 0, -kp, -kv
        if j in bj and tune.get("torque_limit"):  # N m, servo force incl. gravity compensation
            a.forcelimited = mujoco.mjtLimited.mjLIMITED_TRUE
            a.forcerange = [-tune["torque_limit"], tune["torque_limit"]]
        gains[names[j]] = {"inertia": float(I), "kp": float(kp), "kv": float(kv)}
    return spec.compile(), gains


# ---------------------------------------------------------------- reference
def ref_angles(joints, D, P, m, mode):
    """qpos targets [T, nq] (unwrapped in time) in the model's joint order."""
    ang, _ = B.fk_relative(joints, D)
    names, bj, rj = body_dofs(m)
    T = len(D)
    q = np.zeros((T, m.nq))
    for j in bj:
        part, k = None, None
        for p in B.PARTS[1:]:
            if names[j].startswith(p + "_") and names[j][len(p) + 1:] in joints[p]["names"]:
                part, k = p, joints[p]["names"].index(names[j][len(p) + 1:])
        q[:, m.jnt_qposadr[j]] = ang[part][:, k]
    if mode == "carried":
        e = Rot.from_matrix(D[:, 0]).as_euler("ZXY")
        disp = P[:, 0] - m.body_pos[m.body("pelvis").id]
        vals = {"root_x": disp[:, 0], "root_y": disp[:, 1], "root_z": disp[:, 2],
                "root_rz": e[:, 0], "root_rx": e[:, 1], "root_ry": e[:, 2]}
        for j in rj:
            q[:, m.jnt_qposadr[j]] = vals[names[j]]
    for j in range(m.njnt):
        if m.jnt_type[j] == mujoco.mjtJoint.mjJNT_HINGE:
            a = m.jnt_qposadr[j]
            q[:, a] = np.unwrap(q[:, a])
            if not names[j].startswith("root"):  # keep inside (-pi, pi] at the start so limits apply sensibly
                q[:, a] -= 2 * np.pi * np.round(q[0, a] / (2 * np.pi))
    return q


def fk(m, q):
    d = mujoco.MjData(m)
    T = len(q)
    pos = np.zeros((T, 19, 3))
    rot = np.zeros((T, 19, 3, 3))
    ids = [m.body(p).id for p in B.PARTS]
    for t in range(T):
        d.qpos[:] = q[t]
        mujoco.mj_kinematics(m, d)
        pos[t] = d.xpos[ids]
        rot[t] = d.xmat[ids].reshape(-1, 3, 3)
    return pos, rot


# ---------------------------------------------------------------- simulation
def simulate(spec_base, mode, joints, q, tune, inertia):
    spec = spec_base.copy()
    for jt in spec.joints:
        if not jt.name.startswith("root"):
            grp = B.base(jt.name.rsplit("_", 1)[0])
            jt.damping = [float(tune["damping"].get(grp, 0.0)), 0.0, 0.0]
            jt.armature = jt.armature + float(tune["armature"])
    if tune["contact_solref"]:
        for g in spec.geoms:
            if g.name != "floor":
                g.solref = list(tune["contact_solref"])
    m0 = spec.compile()
    m, gains = add_servos(spec, m0, tune, inertia)
    d = mujoco.MjData(m)
    names, bj, rj = body_dofs(m)
    if tune["ff_id"]:  # inverse dynamics of the reference: no gravity (compensated), no contacts
        sid = spec_base.copy()
        sid.option.gravity = [0, 0, 0]
        sid.option.disableflags = int(mujoco.mjtDisableBit.mjDSBL_CONTACT)
        mid = sid.compile()
        did = mujoco.MjData(mid)
    bv = np.array([m.jnt_dofadr[j] for j in bj])
    bq = np.array([m.jnt_qposadr[j] for j in bj])
    lo_r, hi_r = m.jnt_range[bj, 0], m.jnt_range[bj, 1]
    q_hi, t_hi = [], []
    pair_f = np.zeros(T := len(q))
    depth = np.zeros(T)
    held = np.zeros((T, len(bj)), bool)
    tmax = np.zeros(T)
    f6 = np.zeros(6)
    pair_frames = {}
    T = len(q)
    t = np.arange(T) / FPS
    sp = CubicSpline(t, q, axis=0, bc_type="natural")
    dsp, ddsp = sp.derivative(1), sp.derivative(2)
    act_j = [m.actuator_trnid[a, 0] for a in range(m.nu)]
    act_q = np.array([m.jnt_qposadr[j] for j in act_j])
    act_v = np.array([m.jnt_dofadr[j] for j in act_j])
    ratio = np.array([m.actuator_biasprm[a, 2] / m.actuator_biasprm[a, 1] for a in range(m.nu)])  # kv/kp
    ratio = ratio * np.array([1.0 if names[j].startswith("root") else tune["ff_vel"] for j in act_j])
    rq = np.array([m.jnt_qposadr[j] for j in rj], int)
    rv = np.array([m.jnt_dofadr[j] for j in rj], int)
    w = 2 * np.pi * ROOT_HZ
    d.qpos[:] = q[0]
    d.qvel[:] = 0
    vel0 = dsp(0.0)
    for j in range(m.njnt):
        d.qvel[m.jnt_dofadr[j]] = vel0[m.jnt_qposadr[j]]
    mujoco.mj_forward(m, d)
    ids = [m.body(p).id for p in B.PARTS]
    pos = np.zeros((T, 19, 3))
    rot = np.zeros((T, 19, 3, 3))
    qlog = np.zeros((T, m.nq))
    peak = np.zeros(m.nv)
    cmask = np.zeros((T, 19), bool)  # parts touching another part or the floor, per frame
    root_err = 0.0
    max_self, max_floor_pen, sum_self = 0, 0.0, 0
    ok = True
    dt = m.opt.timestep
    for f in range(T):
        pos[f], rot[f] = d.xpos[ids], d.xmat[ids].reshape(-1, 3, 3)
        qlog[f] = d.qpos
        if mode == "carried":
            root_err = max(root_err, float(np.linalg.norm(d.qpos[rq[:3]] - q[f, rq[:3]])))
        if f == T - 1:
            break
        Mr = mdiag(m, d)[rv] if mode == "carried" else None
        for s in range(SUB):
            tt = (f * SUB + s) / (FPS * SUB)
            qr, vr = sp(tt), dsp(tt)
            d.ctrl[:] = qr[act_q] + ratio * vr[act_q]
            if mode == "carried":  # root servos above; here only the reference acceleration, fed forward
                d.qfrc_applied[rv] = Mr * ddsp(tt)[rq]
            if tune["ff_id"] and s % 4 == 0:
                did.qpos[:], did.qvel[:], did.qacc[:] = qr, vr_full(vr, m), vr_full(ddsp(tt), m)
                mujoco.mj_inverse(mid, did)
                d.qfrc_applied[bv] = tune["ff_id"] * did.qfrc_inverse[bv]
            mujoco.mj_step(m, d)
            peak = np.maximum(peak, np.abs(d.qfrc_actuator))
            tmax[f + 1] = max(tmax[f + 1], float(np.abs(d.qfrc_actuator[bv]).max()))
            if s % HI == HI - 1:
                q_hi.append(d.qpos[bq].copy())
                t_hi.append((f * SUB + s + 1) / (FPS * SUB))
        if not np.all(np.isfinite(d.qpos)) or np.abs(d.qvel).max() > 1e3:
            ok = False
            print("  BLEW UP at frame", f)
            break
        nself = 0
        pf = {}
        qb = d.qpos[bq]
        held[f + 1] = (qb < lo_r + np.radians(0.5)) | (qb > hi_r - np.radians(0.5))
        for ci, c in enumerate(d.contact[:d.ncon]):
            if m.geom_bodyid[c.geom1] != 0 and m.geom_bodyid[c.geom2] != 0:
                mujoco.mj_contactForce(m, d, ci, f6)
                key = (min(c.geom1, c.geom2), max(c.geom1, c.geom2))
                pf[key] = pf.get(key, 0.0) + abs(f6[0])
                depth[f + 1] = max(depth[f + 1], -float(c.dist))
                nself += 1
                cmask[f + 1, m.geom_bodyid[c.geom1] - 1] = cmask[f + 1, m.geom_bodyid[c.geom2] - 1] = True
            else:
                max_floor_pen = max(max_floor_pen, -float(c.dist))
                cmask[f + 1, max(m.geom_bodyid[c.geom1], m.geom_bodyid[c.geom2]) - 1] = True
        max_self = max(max_self, nself)
        sum_self += nself
        pair_f[f + 1] = max(pf.values()) if pf else 0.0
        bp = {}
        for (g1, g2), fv in pf.items():
            k2 = "-".join(sorted((m.body(m.geom_bodyid[g1]).name, m.body(m.geom_bodyid[g2]).name)))
            bp[k2] = max(bp.get(k2, 0.0), fv)
        for k2, fv in bp.items():
            if fv > 20:
                pair_frames[k2] = pair_frames.get(k2, 0) + 1
    torque = {names[j]: float(peak[m.jnt_dofadr[j]]) for j in bj}
    warn = int(sum(d.warning[i].number for i in range(len(d.warning))))
    tq = np.arange(T) / FPS
    diag = {"joint_names": np.array([names[j] for j in bj]), "range": m.jnt_range[bj], "q": qlog[:, bq],
            "qref": q[:, bq], "q_hi": np.array(q_hi), "t_hi": np.array(t_hi),
            "qref_hi": sp(np.array(t_hi))[:, bq] if t_hi else np.zeros((0, len(bj))),
            "contact_mask": cmask, "self_pair_force_max": pair_f, "self_depth_max": depth, "held_at_limit": held,
            "torque_max": tmax, "warnings": warn, "ok": ok, "t": tq,
            "pairs_over_20N_frames": json.dumps(pair_frames)}
    gains = {k: v for k, v in gains.items() if not k.startswith("root")}
    return pos, rot, qlog, {"ok": ok, "gains": gains, "peak_torque_Nm": torque, "root_path_err_max_m": root_err,
                            "max_self_contacts_in_a_frame": max_self,
                            "mean_self_contacts_per_frame": sum_self / max(1, T - 1), "max_floor_penetration_m": max_floor_pen,
                            "contact_mask": cmask, "warnings": warn, "diag": diag}


# ---------------------------------------------------------------- clips
def clip_sources(motions, joints):
    info = {}
    md, D, P, mo = load(find(motions, DANCE))
    i0, i1 = list(md).index(286), list(md).index(525)
    dance = dict(src=md[i0:i1 + 1], D=D[i0:i1 + 1], P=P[i0:i1 + 1], loop=0, vmd="assets/motion/" + DANCE)
    # walk: check the loop seam (pose difference between the loop's ends) before tiling
    wm = find(motions, WALK)
    wf, wD, wP, _ = load(wm)
    ang, _ = B.fk_relative(joints, wD[[0, -1]])
    seam = max(float(np.degrees(np.abs(B.wrap(a[1] - a[0]))).max()) for a in ang.values())
    pel = float(B.rot_angle(wD[[0]][:, 0], wD[[-1]][:, 0])[0])
    dz = float(abs(wP[-1, 0, 2] - wP[0, 0, 2]))
    info["walk_seam"] = {"file": wm["name"], "frames": [int(wf[0]), int(wf[-1])], "max_joint_diff_deg": seam,
                         "pelvis_rot_diff_deg": pel, "pelvis_height_diff_m": dz}
    if seam < 3.0 and pel < 3.0 and dz < 0.005:
        L = len(wf) - 1
        disp = wP[-1, 0] - wP[0, 0]
        idx = np.tile(np.arange(L), 4)
        tile = np.repeat(np.arange(4), L)
        walk = dict(src=wf[idx], D=wD[idx], P=wP[idx] + (tile[:, None, None] * disp[None, None, :]), loop=L,
                    vmd="assets/motion/" + wm["name"])
        info["walk_seam"]["used"] = f"tiled 4 x {L} frames, each tile moved on by the loop's own travel"
    else:
        fm = find(motions, WALK_FALLBACK)
        ff, fD, fP, _ = load(fm)
        walk = dict(src=ff[:160], D=fD[:160], P=fP[:160], loop=0, vmd="assets/motion/" + fm["name"])
        info["walk_seam"]["used"] = "fallback: フユネコ 歩く.vmd, first 160 frames"
    hm = find(motions, HEART)
    hf, hD, hP, _ = load(hm)
    pm = find(motions, PEACE)
    pf, pD, pP, _ = load(pm)
    # sing: the 8 s window with the most arm travel while the mouth is moving
    sm = find(motions, SING)
    sf, sD, sP, smo = load(sm)
    travel = np.zeros(len(sf))
    for s in "LR":
        for p in (f"upper_arm_{s}", f"forearm_{s}", f"hand_{s}"):
            Rr = np.einsum("nji,njk->nik", sD[:, B.PI["chest"]], sD[:, B.PI[p]])
            travel[1:] += B.rot_angle(Rr[1:], Rr[:-1])
    score = np.convolve(travel * (smo > 0.05), np.ones(240), "valid")
    k = int(np.argmax(score))
    info["sing_window"] = {"blender_frames": [int(sf[k]), int(sf[k + 239])], "seconds": [float(sf[k] / FPS), float(sf[k + 239] / FPS)],
                           "arm_travel_deg": float(travel[k:k + 240].sum()),
                           "mouth_moving_share": float((smo[k:k + 240] > 0.05).mean())}
    sing = dict(src=sf[k:k + 240], D=sD[k:k + 240], P=sP[k:k + 240], loop=0, vmd="assets/motion/" + sm["name"])
    clips = [
        ("dance", "dance", "Dance: the quick turn, the kick, the crossed arms (時よ止まれ, frames 286-525)", dance,
         "full", "carried", "ケイ (時よ止まれ)"),
        ("dance_pinned", "dance", "Dance, hips pinned in the air, no floor (時よ止まれ, frames 286-525)", dance,
         "full", "pinned", "ケイ (時よ止まれ)"),
        ("walk", "walk", "Walk (むつごろう 歩き10L_乙女, tiled four times)" if walk["loop"] else "Walk (フユネコ 歩く)",
         walk, "full", "carried", "むつごろう (移動モーション配布 v1.3)" if walk["loop"] else "フユネコ＆朱雀 (歩く)"),
        ("cute_heart", "cute", "Cute: turn into a finger heart (グレイ)", dict(src=hf, D=hD, P=hP, loop=0,
         vmd="assets/motion/" + hm["name"]), "full", "carried", "グレイ (ターンしてハート)"),
        ("cute_peace", "cute", "Cute: double peace sign (グレイ)", dict(src=pf, D=pD, P=pP, loop=0,
         vmd="assets/motion/" + pm["name"]), "full", "carried", "グレイ (ピスピース)"),
        ("sing", "sing", f"Singing: Ave Maria, {sf[k] / FPS:.0f}-{sf[k + 239] / FPS:.0f} s", sing, "bust", "carried",
         "盗賊@つばきP (body motion), i7 (mouth shapes, made with LipFaceMaker)"),
    ]
    return clips, info


def overshoot(qs, qr, names, bj, m, cmask, qstiff):
    """Largest amount the soft figure goes past the reference's extreme around a turning point (from 1/6 s before
    to 1/2 s after it), where neither
    the moving part nor anything below it touches another part or the floor, and the stiff figure follows (so it is the
    spring, not a collision or a joint limit)."""
    best = (0.0, None, None)
    sub = {p: {p} for p in B.PARTS}
    for p in reversed(B.PARTS[1:]):
        sub[B.PARENT[p]] |= sub[p]
    for j in bj:
        a = m.jnt_qposadr[j]
        part = next(p for p in B.PARTS[1:] if names[j].startswith(p + "_"))
        cols = [B.PI[x] for x in sub[part]]
        free = ~cmask[:, cols].any(1)
        okstiff = np.degrees(np.abs(qstiff[:, a] - qr[:, a])) < 5
        r, s = np.degrees(qr[:, a]), np.degrees(qs[:, a])
        v = np.gradient(r)
        for f in range(2, len(r) - 2):
            if v[f - 1] * v[f + 1] < 0 and abs(r[f] - r[max(0, f - 10)]) > 15:  # a turning point after a real move
                sign = 1 if v[f - 1] > 0 else -1
                w = slice(max(0, f - 5), min(len(r), f + 15))
                if not (free[w].all() and okstiff[w].all()):
                    continue
                o = float(np.max(sign * s[w]) - np.max(sign * r[w]))  # past the reference's own extreme
                if o > best[0]:
                    best = (o, names[j], f)
    return {"deg": best[0], "joint": best[1], "frame_index": best[2]}


def main():
    t0 = time.time()
    binfo = json.load(open(os.path.join(OUT, "body_info.json"), encoding="utf-8"))
    joints = binfo["joints"]
    motions = json.load(open(os.path.join(B.EX, "motions.json"), encoding="utf-8"))
    clips, info = clip_sources(motions, joints)
    if os.environ.get("NO_PINNED"):  # final round: the five carried clips only
        clips = [c for c in clips if c[5] != "pinned"]
    os.makedirs(os.path.join(OUT, "sim"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "sim_diag"), exist_ok=True)
    models = {mode: make_model(mode) for mode in ("carried", "pinned")}
    clips_json, per_clip = [], {}
    # effective inertia per joint along every clip's reference poses (one set of gains for her whole body)
    m_p = models["pinned"][1]
    poses = []
    for name, kind, title, c, framing, hips, credits in clips:
        if hips == "pinned":
            poses.append(ref_angles(joints, c["D"], c["P"], m_p, "pinned")[::5])
    for name, kind, title, c, framing, hips, credits in clips:
        if hips == "carried":
            poses.append(ref_angles(joints, c["D"], c["P"], m_p, "pinned")[::5])
    inertia = effective_inertia(m_p, np.concatenate(poses))
    if os.environ.get("FREEZE_INERTIA"):  # the gains of an earlier round, unchanged
        inertia = json.load(open(os.environ["FREEZE_INERTIA"], encoding="utf-8"))["effective_inertia"]
    for name, kind, title, c, framing, hips, credits in clips:
        spec, m = models[hips]
        names, bj, rj = body_dofs(m)
        D, P = c["D"], c["P"]
        if hips == "pinned":  # the same joint angles, the pelvis held at its rest rotation
            D = np.einsum("nji,npjk->npik", D[:, 0], D)
        q = ref_angles(joints, D, P, m, hips)
        pos_fk, rot_fk = fk(m, q)
        if hips == "carried":
            pos_ref, rot_ref = P, c["D"]
        else:
            pos_ref, rot_ref = pos_fk, rot_fk
        rt_rot = B.rot_angle(rot_fk.reshape(-1, 3, 3), D.reshape(-1, 3, 3)).reshape(len(D), 19)
        rt_pos = np.linalg.norm(pos_fk - (P if hips == "carried" else pos_fk), axis=2)
        out = {"parts": np.array(B.PARTS), "src_frame": np.asarray(c["src"], np.int32),
               "loop_len": np.int32(c["loop"]), "pos_ref": pos_ref.astype(np.float32), "rot_ref": rot_ref.astype(np.float32)}
        rec = {"frames": len(D), "round_trip_rot_deg": {"max": float(rt_rot.max()),
                                                         "worst_part": B.PARTS[int(np.argmax(rt_rot.max(0)))]},
               "round_trip_pos_mm": {"max": 1000 * float(rt_pos.max()),
                                     "worst_part": B.PARTS[int(np.argmax(rt_pos.max(0)))]}}
        lim_hits = {}
        for j in bj:
            lo, hi = m.jnt_range[j]
            a = q[:, m.jnt_qposadr[j]]
            n = int(((a < lo - 1e-6) | (a > hi + 1e-6)).sum())
            if n:
                lim_hits[names[j]] = n
        rec["ref_outside_range_frames"] = lim_hits
        qlogs = {}
        for v in ("soft", "stiff"):
            pos, rot, qs, sinfo = simulate(spec, hips, joints, q, TUNING[v], inertia)
            np.savez_compressed(os.path.join(OUT, "sim_diag", f"{name}_{v}.npz"), **sinfo.pop("diag"))
            out[f"pos_{v}"], out[f"rot_{v}"] = pos.astype(np.float32), rot.astype(np.float32)
            err_part = B.rot_angle(rot.reshape(-1, 3, 3), rot_ref.reshape(-1, 3, 3)).reshape(len(D), 19)
            jerr = np.degrees(np.abs(qs[:, [m.jnt_qposadr[j] for j in bj]] - q[:, [m.jnt_qposadr[j] for j in bj]]))
            sinfo.update({"part_rot_err_deg": {"mean": float(err_part[:, 1:].mean()), "max": float(err_part[:, 1:].max()),
                                               "worst_part": B.PARTS[1 + int(np.argmax(err_part[:, 1:].max(0)))]},
                          "joint_angle_err_deg": {"mean": float(jerr.mean()), "max": float(jerr.max()),
                                                  "worst_joint": names[bj[int(np.argmax(jerr.max(0)))]]},
                          "joint_pos_err_mm": {"mean": 1000 * float(np.linalg.norm(pos - pos_ref, axis=2).mean()),
                                               "max": 1000 * float(np.linalg.norm(pos - pos_ref, axis=2).max())}})
            qlogs[v] = (qs, sinfo.pop("contact_mask"))
            rec[v] = sinfo
            print(f"{name} {v}: ok={sinfo['ok']} joint err mean {sinfo['joint_angle_err_deg']['mean']:.1f} "
                  f"max {sinfo['joint_angle_err_deg']['max']:.1f} deg, root err {1000 * sinfo['root_path_err_max_m']:.1f} mm, "
                  f"self contacts {sinfo['max_self_contacts_in_a_frame']} ({time.time() - t0:.0f}s)", flush=True)
        rec["soft"]["overshoot"] = overshoot(qlogs["soft"][0], q, names, bj, m, qlogs["soft"][1], qlogs["stiff"][0])
        np.savez_compressed(os.path.join(OUT, "sim", name + ".npz"), **out)
        per_clip[name] = rec
        clips_json.append({"name": name, "kind": kind, "title": title, "npz": f"sim/{name}.npz", "vmd": c["vmd"],
                           "framing": framing, "hips": hips, "credits": credits})
    with open(os.path.join(OUT, "clips.json"), "w", encoding="utf-8") as f:
        json.dump(clips_json, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "sim_info.json"), "w", encoding="utf-8") as f:
        json.dump({"clips": per_clip, **info, "variants": {v: (TUNING[v]["hz"], TUNING[v]["zeta"]) for v in ("soft", "stiff")},
                   "soft_groups": TUNING["soft"]["groups"], "tuning": TUNING, "root_hz": ROOT_HZ, "effective_inertia": inertia,
                   "timestep_s": 1 / (FPS * SUB)}, f, ensure_ascii=False, indent=1)
    print(f"simulate done ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
