"""PROTOTYPE (throwaway). Her 19-part Simulation Body from the extracted rest data and motions.

  uv run --with mujoco --with numpy --with scipy python body.py [--quick]

Reads build/first-look/extract/{rest.npz, motions.json, motion/*.npz}; writes build/first-look/body.json
(the contract), build/first-look/body.xml (MJCF, freejoint root, floor) and build/first-look/body_info.json
(axes, ranges per kind of movement, fit numbers, exclusions; read by simulate.py).
All body frames are world-aligned in the rest pose, so a part's world rotation equals its rotation delta D.
"""
import json
import os
import sys
import time

import mujoco
import numpy as np
from scipy.optimize import minimize
from scipy.spatial import ConvexHull, cKDTree
from scipy.spatial.transform import Rotation as Rot

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.environ.get("FIRSTLOOK_DIR", os.path.join(REPO, "build", "first-look"))  # where the body is written
EX = os.path.join(REPO, "build", "first-look", "extract")

PARTS = ["pelvis", "waist", "chest", "neck", "head", "collar_L", "collar_R", "upper_arm_L", "upper_arm_R",
         "forearm_L", "forearm_R", "hand_L", "hand_R", "thigh_L", "thigh_R", "shin_L", "shin_R", "foot_L", "foot_R"]
PARENT = {"pelvis": None, "waist": "pelvis", "chest": "waist", "neck": "chest", "head": "neck"}
for _s in "LR":
    PARENT.update({f"collar_{_s}": "chest", f"upper_arm_{_s}": f"collar_{_s}", f"forearm_{_s}": f"upper_arm_{_s}",
                   f"hand_{_s}": f"forearm_{_s}", f"thigh_{_s}": "pelvis", f"shin_{_s}": f"thigh_{_s}",
                   f"foot_{_s}": f"shin_{_s}"})
PI = {p: i for i, p in enumerate(PARTS)}
SHARE = {"head": 16.8, "neck": 1.4, "chest": 12.8, "collar": 0.4, "waist": 7.3, "pelvis": 9.7, "thigh": 15.2,
         "shin": 5.9, "foot": 0.9, "upper_arm": 2.2, "forearm": 1.2, "hand": 0.3}
TOTAL_KG = 25.5
KINDS = ["dance", "walk", "cute", "sing"]
COLORS = {"pelvis": (0.85, 0.35, 0.35), "waist": (0.95, 0.6, 0.3), "chest": (0.95, 0.85, 0.35),
          "neck": (0.6, 0.85, 0.4), "head": (0.95, 0.75, 0.8), "collar_L": (0.35, 0.75, 0.75),
          "collar_R": (0.25, 0.6, 0.6), "upper_arm_L": (0.35, 0.55, 0.95), "upper_arm_R": (0.25, 0.4, 0.75),
          "forearm_L": (0.65, 0.45, 0.95), "forearm_R": (0.5, 0.3, 0.75), "hand_L": (0.95, 0.45, 0.85),
          "hand_R": (0.75, 0.3, 0.65), "thigh_L": (0.45, 0.8, 0.55), "thigh_R": (0.3, 0.6, 0.4),
          "shin_L": (0.85, 0.55, 0.3), "shin_R": (0.65, 0.4, 0.2), "foot_L": (0.55, 0.55, 0.6),
          "foot_R": (0.4, 0.4, 0.45)}
JTYPE = {p: "ball" for p in PARTS[1:]}
for _s in "LR":
    JTYPE[f"shin_{_s}"] = "knee"
    JTYPE[f"forearm_{_s}"] = "elbow"
SLABS = {"pelvis": 5, "waist": 2, "chest": 10, "neck": 2, "head": 6, "collar": 2, "upper_arm": 3, "forearm": 4,
         "hand": 3, "thigh": 4, "shin": 4}
SURF = None       # KD-tree over points sampled densely on her body surface (set in main)
# Which surface gets a solid (docs/adr/0004): loose parts are Secondary Physics and get none, however they are
# bound. Hair never; cloth and ornaments only where they lie within CLOSE of her core surface (skin, face,
# stocking, the bodice on her torso, shoes, and her cranium closed from the hair's innermost layer).
HAIR = {"前髮", "髮", "髮+"}
CORE = {"肌", "足", "颜", "颜2", "照れ", "鞋", "麦克风1", "麦克风2", "口舌", "齿", "目", "瞳", "白目", "目光", "目光2",
        "星目", "睫眉"}
CORE_ON_TORSO = {"体"}   # the bodice: core on chest and waist, an ornament elsewhere (the band round her head)
CLOSE = 0.012
# Final round switches (env): HEAD_SKULL_ONLY=1 keeps only her skull and face on the head (no band or ornament
# round her hair); SHOE_SIMPLE=1 covers the upper shoe with a handful of single shapes; ELBOW_PAST_DEG lets the
# elbows bend that far past the straight limb (knees stay strict).
HEAD_SKULL_ONLY = bool(os.environ.get("HEAD_SKULL_ONLY"))
SHOE_SIMPLE = bool(os.environ.get("SHOE_SIMPLE"))
ELBOW_PAST_DEG = float(os.environ.get("ELBOW_PAST_DEG", "0"))
# The upper arm meets the chest at the armpit seam: with the arm hanging (walk, singing) her drawn surfaces sit
# 0.5 mm apart there while the solids, which must stand a little off, go 22 mm into each other and hold the arm
# out by about 13 degrees. These pairs are excluded from the start.
SEAM_EXCLUDES = [("chest", "upper_arm_L"), ("chest", "upper_arm_R")]
# Trims (epoch 1 on, TRIM=1): pairs whose solids jam although her drawn surfaces stay apart (head and chest: never
# under 26 mm in any clip) or meet only as the motion crosses them (thighs, shins, feet): keep their solids at
# least this share of her own rest-pose gap apart, by taking the facing sides in toward her drawn surface.
TRIM = {("chest", "head"): 0.6, ("thigh_L", "thigh_R"): 0.8, ("shin_L", "shin_R"): 0.8, ("foot_L", "foot_R"): 0.8,
        ("foot_L", "shin_R"): 0.8, ("foot_R", "shin_L"): 0.8} if os.environ.get("TRIM") else {}
MARGIN_DEG, MARGIN_FRAC = 15.0, 0.20
CLEAR = 0.0105    # lowest point of any foot solid that is not a floor-contact shape (m)
PAD_TOP = 0.010   # top of the floor-contact boxes (m); their bottom is the floor, z = 0


def base(p):
    return p[:-2] if p.endswith(("_L", "_R")) else p


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


# ---------------------------------------------------------------- rotations and joint decomposition
def axis_rot(a, q):
    """Rotation matrices about unit axis a by angles q (array)."""
    return Rot.from_rotvec(np.outer(np.atleast_1d(q), a)).as_matrix()


def hinge_angle(h, t, R):
    """Signed angle about h that best carries direction t to R t (projected on the plane normal to h)."""
    x = R @ t
    p0 = t - h * (t @ h)
    p1 = x - np.outer(x @ h, h)
    return np.arctan2(np.cross(p0, p1) @ h, p1 @ p0)


def twist_angle(a, R):
    q = Rot.from_matrix(R).as_quat()  # x y z w
    return wrap(2 * np.arctan2(q[..., :3] @ a, q[..., 3]))


def wrap(q):
    return (q + np.pi) % (2 * np.pi) - np.pi


def decompose(j, R):
    """Joint angles (radians, [N, ndof]) of joint spec j for relative rotations R [N,3,3], and the rotation the
    angles reproduce [N,3,3]."""
    if j["type"] == "ball":
        B = np.array(j["axes"]).T
        ang = Rot.from_matrix(np.einsum("ji,njk,kl->nil", B, R, B)).as_euler("XYZ")
        return ang, R.copy()
    h, t = np.array(j["axes"][0]), np.array(j["limb_dir"])
    q1 = hinge_angle(h, t, R)
    H = axis_rot(h, q1)
    if j["type"] == "knee":
        return q1[:, None], H
    tw = np.array(j["axes"][1])
    q2 = twist_angle(tw, np.einsum("nji,njk->nik", H, R))
    return np.stack([q1, q2], 1), H @ axis_rot(tw, q2)


def rot_angle(Ra, Rb):
    """Angle (deg) between rotation stacks."""
    c = (np.einsum("nij,nij->n", Ra, Rb) - 1) / 2
    return np.degrees(np.arccos(np.clip(c, -1, 1)))


def fk_relative(joints, D):
    """Sequential decomposition of world deltas D [N,19,3,3] down the tree: each joint's angles are taken
    relative to the parent's *reproduced* rotation, so knee/elbow residuals do not pile up. Returns angles per
    joint and the reproduced world rotations."""
    Wm = np.zeros_like(D)
    Wm[:, 0] = D[:, 0]
    ang = {}
    for p in PARTS[1:]:
        i, pi = PI[p], PI[PARENT[p]]
        Rrel = np.einsum("nji,njk->nik", Wm[:, pi], D[:, i])
        a, Rrep = decompose(joints[p], Rrel)
        ang[p] = a
        Wm[:, i] = Wm[:, pi] @ Rrep
    return ang, Wm


# ---------------------------------------------------------------- data
def load_rest():
    r = np.load(os.path.join(EX, "rest.npz"))
    return r, json.loads(str(r["info"]))


def load_motions(step_sing=3):
    ms = json.load(open(os.path.join(EX, "motions.json"), encoding="utf-8"))
    out = []
    for m in ms:
        f = os.path.join(EX, "motion", m["key"] + ".npz")
        if not os.path.exists(f):
            print("missing motion", m["key"], m["name"])
            continue
        z = np.load(f)
        D = z["D"].astype(float)
        if m["kind"] == "sing":
            D = D[::step_sing]
        out.append((m, D))
    return out


def limb_dirs(r, info):
    jp = r["joint_pos"]
    lm = info["landmarks"]
    t = {"waist": jp[PI["chest"]] - jp[PI["waist"]], "chest": jp[PI["neck"]] - jp[PI["chest"]],
         "neck": jp[PI["head"]] - jp[PI["neck"]], "head": np.array([0, 0, 1.0])}
    for s in "LR":
        t[f"collar_{s}"] = jp[PI[f"upper_arm_{s}"]] - jp[PI[f"collar_{s}"]]
        t[f"upper_arm_{s}"] = jp[PI[f"forearm_{s}"]] - jp[PI[f"upper_arm_{s}"]]
        t[f"forearm_{s}"] = jp[PI[f"hand_{s}"]] - jp[PI[f"forearm_{s}"]]
        t[f"hand_{s}"] = np.array(lm[f"中指先.{s}"]) - jp[PI[f"hand_{s}"]]
        t[f"thigh_{s}"] = jp[PI[f"shin_{s}"]] - jp[PI[f"thigh_{s}"]]
        t[f"shin_{s}"] = jp[PI[f"foot_{s}"]] - jp[PI[f"shin_{s}"]]
        t[f"foot_{s}"] = np.array(lm[f"足先EX.{s}:tail"]) - jp[PI[f"foot_{s}"]]
    return {k: unit(v) for k, v in t.items()}


# ---------------------------------------------------------------- joint axes and ranges
def choose_axes(p, t, Rrel, upper_dir=None):
    """Pick the axes of one joint from its relative rotations over every frame of every motion."""
    if JTYPE[p] in ("knee", "elbow"):
        X = Rrel @ t
        c = np.cov(X.T)
        h = np.linalg.eigh(c)[1][:, 0]
        q = hinge_angle(h, t, Rrel)
        if np.mean(q) < 0:  # flexion positive
            h = -h
        j = {"type": JTYPE[p], "axes": [h.tolist()] + ([t.tolist()] if JTYPE[p] == "elbow" else []),
             "names": ["flex"] + (["twist"] if JTYPE[p] == "elbow" else []), "limb_dir": t.tolist()}
        a, Rrep = decompose(j, Rrel)
        j["hinge_departure_deg"] = {"max": float(rot_angle(Rrep, Rrel).max()),
                                    "p95": float(np.percentile(rot_angle(Rrep, Rrel), 95))}
        # the straight limb: angle about h at which the limb lines up with the part above it
        j["straight_deg"] = float(np.degrees(hinge_angle(h, t, Rot.align_vectors([upper_dir], [t])[0].as_matrix()[None])[0]))
        j["worst_middle_deg"] = None
        return j
    e = np.eye(3)[np.argmin(np.abs(t))]
    p0 = unit(np.cross(t, e))
    p1 = np.cross(t, p0)
    bests = {}
    for twist_last in (True, False):
        for psi in np.radians(np.arange(0, 180, 7.5)):
            u = np.cos(psi) * p0 + np.sin(psi) * p1
            w = np.cross(t, u)
            axes = [u, w, t] if twist_last else [t, u, w]
            B = np.array(axes).T
            ang = Rot.from_matrix(np.einsum("ji,njk,kl->nil", B, Rrel, B)).as_euler("XYZ")
            worst = np.degrees(np.abs(ang[:, 1]).max())
            if twist_last not in bests or worst < bests[twist_last]["worst"]:
                bests[twist_last] = {"worst": worst, "axes": axes, "twist_last": twist_last}
    # prefer twist last (twist about the limb's own axis after the swings) unless it comes within 75 deg of
    # the singular middle angle and twist first does better
    best = bests[True]
    if best["worst"] >= 75 and bests[False]["worst"] < best["worst"]:
        best = bests[False]
    names = ["swing1", "swing2", "twist"] if best["twist_last"] else ["twist", "swing1", "swing2"]
    return {"type": "ball", "axes": [list(map(float, a)) for a in best["axes"]], "names": names,
            "limb_dir": t.tolist(), "worst_middle_deg": float(best["worst"]), "twist_last": best["twist_last"]}


def joint_ranges(joints, motions, info_t):
    """Per joint, per axis, per kind: [min, max] in degrees; then the range used = union + margin."""
    per = {p: {k: None for k in KINDS} for p in PARTS[1:]}
    mid = {p: {k: 0.0 for k in KINDS} for p in PARTS[1:]}
    for m, D in motions:
        ang, _ = fk_relative(joints, D)
        for p in PARTS[1:]:
            a = np.degrees(ang[p])
            lo, hi = a.min(0), a.max(0)
            cur = per[p][m["kind"]]
            per[p][m["kind"]] = [np.minimum(cur[0], lo), np.maximum(cur[1], hi)] if cur is not None else [lo, hi]
            if joints[p]["type"] == "ball":
                mid[p][m["kind"]] = max(mid[p][m["kind"]], float(np.abs(a[:, 1]).max()))
    for p in PARTS[1:]:
        j = joints[p]
        n = len(j["axes"])
        rng, setby, obs = [], [], []
        for k in range(n):
            los = {kd: per[p][kd][0][k] for kd in KINDS if per[p][kd] is not None}
            his = {kd: per[p][kd][1][k] for kd in KINDS if per[p][kd] is not None}
            klo, khi = min(los, key=los.get), max(his, key=his.get)
            lo, hi = los[klo], his[khi]
            mlo, mhi = max(MARGIN_DEG, MARGIN_FRAC * abs(lo)), max(MARGIN_DEG, MARGIN_FRAC * abs(hi))
            rlo, rhi = lo - mlo, hi + mhi
            if j["type"] in ("knee", "elbow") and k == 0:  # never backward: nothing past the straight limb
                rlo = max(rlo, j["straight_deg"])
            rlo, rhi = max(rlo, -180.0), min(rhi, 180.0)
            rng.append([float(rlo), float(rhi)])
            setby.append([klo, khi])
            obs.append([float(lo), float(hi)])
        j["range_deg"] = rng
        j["range_set_by"] = setby
        j["observed_deg"] = obs
        j["per_kind_deg"] = {kd: (np.array(per[p][kd]).T.tolist() if per[p][kd] is not None else None) for kd in KINDS}
        if j["type"] == "ball":
            j["worst_middle_per_kind_deg"] = mid[p]
    return joints


# ---------------------------------------------------------------- solids
def sd_geoms(P, geoms):
    """Signed distance of points P [N,3] to each geom -> [N, G] (negative inside)."""
    out = np.zeros((len(P), len(geoms)))
    for k, g in enumerate(geoms):
        R = np.array(g["rot"])
        L = (P - g["pos"]) @ R  # local coordinates
        s = g["size"]
        if g["type"] == "sphere":
            out[:, k] = np.linalg.norm(L, axis=1) - s[0]
        elif g["type"] == "capsule":
            z = np.clip(L[:, 2], -s[1], s[1])
            out[:, k] = np.linalg.norm(L - np.stack([0 * z, 0 * z, z], 1), axis=1) - s[0]
        else:
            q = np.abs(L) - np.array(s)
            out[:, k] = np.linalg.norm(np.maximum(q, 0), axis=1) + np.minimum(q.max(1), 0)
    return out


def frame_from_z(d):
    d = unit(d)
    e = np.eye(3)[np.argmin(np.abs(d))]
    x = unit(np.cross(e, d))
    y = np.cross(d, x)
    return np.stack([x, y, d], 1)


def hull_pts(P):
    try:
        return P[ConvexHull(P).vertices]
    except Exception:  # noqa: BLE001
        return P


def seg_dist(P, a, b):
    ab = b - a
    t = np.clip(((P - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
    return np.linalg.norm(P - (a + np.outer(t, ab)), axis=1)


def fit_capsule(P, d0, zmin=None):
    H = hull_pts(P)
    best = None
    for d_init in (unit(d0), unit(np.linalg.svd(H - H.mean(0))[2][0])):
        ext = (H - H.mean(0)) @ d_init
        c0 = H.mean(0) + d_init * (ext.max() + ext.min()) / 2
        th, ph = np.arccos(np.clip(d_init[2], -1, 1)), np.arctan2(d_init[1], d_init[0])
        x0 = np.r_[c0, th, ph, max((ext.max() - ext.min()) / 2 * 0.5, 1e-3)]

        def geom(x):
            d = np.array([np.sin(x[3]) * np.cos(x[4]), np.sin(x[3]) * np.sin(x[4]), np.cos(x[3])])
            h = abs(x[5])
            a, b = x[:3] - h * d, x[:3] + h * d
            r = seg_dist(H, a, b).max()
            return d, h, a, b, r

        def f(x):
            d, h, a, b, r = geom(x)
            v = np.pi * r * r * 2 * h + 4 / 3 * np.pi * r ** 3
            if zmin is not None:
                low = min(a[2], b[2]) - r
                v += 50.0 * max(0.0, zmin - low)
            return v

        res = minimize(f, x0, method="Nelder-Mead", options={"maxiter": 4000, "xatol": 1e-5, "fatol": 1e-9})
        res = minimize(f, res.x, method="Nelder-Mead", options={"maxiter": 4000, "xatol": 1e-6, "fatol": 1e-10})
        if best is None or res.fun < best[0]:
            best = (res.fun, res.x, geom)
    d, h, a, b, r = best[2](best[1])
    return {"type": "capsule", "pos": best[1][:3].copy(), "rot": frame_from_z(d), "size": [r, h], "vol": best[0]}


def fit_box(P, R0, zmin=None):
    H = hull_pts(P)

    def geom(x):
        R = R0 @ Rot.from_rotvec(x).as_matrix()
        L = H @ R
        lo, hi = L.min(0), L.max(0)
        return R, R @ ((lo + hi) / 2), (hi - lo) / 2

    def f(x):
        R, c, hs = geom(x)
        v = 8 * np.prod(hs)
        if zmin is not None:
            low = c[2] - np.abs(R[2]) @ hs
            v += 50.0 * max(0.0, zmin - low)
        return v

    best = None
    for x0 in (np.zeros(3), np.array([0, 0, np.pi / 4]), np.array([np.pi / 4, 0, 0]), np.array([0, np.pi / 4, 0])):
        res = minimize(f, x0, method="Nelder-Mead", options={"maxiter": 3000, "xatol": 1e-6, "fatol": 1e-11})
        if best is None or res.fun < best.fun:
            best = res
    R, c, hs = geom(best.x)
    return {"type": "box", "pos": c, "rot": R, "size": list(np.maximum(hs, 1e-4)), "vol": best.fun}


def fit_sphere(P, zmin=None):
    H = hull_pts(P)

    def f(x):
        r = np.linalg.norm(H - x, axis=1).max()
        v = 4 / 3 * np.pi * r ** 3
        if zmin is not None:
            v += 50.0 * max(0.0, zmin - (x[2] - r))
        return v

    res = minimize(f, H.mean(0), method="Nelder-Mead", options={"maxiter": 3000, "xatol": 1e-6, "fatol": 1e-11})
    return {"type": "sphere", "pos": res.x, "rot": np.eye(3), "size": [float(np.linalg.norm(H - res.x, axis=1).max())],
            "vol": res.fun}


def standoff_score(gs, axis, t0, t1, origin, ends):
    """Mean distance from the candidate's surface (within the slab, +-1 cm along the axis) to her surface, plus a
    quarter of how far the candidate hangs past the ends of its part (caps and spheres reaching into the next part)."""
    x = np.vstack([sample_surface(g, 400) for g in gs])
    if len(gs) > 1:
        x = x[sd_geoms(x, gs).min(1) > -1e-4]
    t = (x - origin) @ axis
    over = max(0.0, t.max() - ends[1]) + max(0.0, ends[0] - t.min()) if ends is not None else 0.0
    x = x[(t >= t0 - 0.01) & (t <= t1 + 0.01)]
    return (float(SURF.query(x)[0].mean()) if len(x) else 1.0) + 0.25 * over


def fit_slab(P, axis, zmin=None, t0=None, t1=None, origin=None, ends=None, smooth=False, single=False):
    """Best of capsule / box / two side-by-side capsules / sphere, each the smallest that holds every point;
    the one whose surface stands off her surface least wins."""
    R0 = frame_from_z(axis)
    L = (P - P.mean(0)) @ R0
    u, s, vt = np.linalg.svd(L[:, :2] - L[:, :2].mean(0), full_matrices=False)
    maj2 = vt[0]
    R0 = R0 @ np.array([[maj2[0], -maj2[1], 0], [maj2[1], maj2[0], 0], [0, 0, 1]])
    cands = [[fit_capsule(P, axis, zmin)], [fit_box(P, R0, zmin)], [fit_sphere(P, zmin)]]
    side = (P - P.mean(0)) @ R0[:, 0]
    if np.ptp(side) > 1.3 * np.ptp((P - P.mean(0)) @ R0[:, 1]) and len(P) > 20:
        m = np.median(side)
        a, b = P[side <= m + 0.003], P[side >= m - 0.003]
        if len(a) > 8 and len(b) > 8:
            cands.append([fit_capsule(a, axis, zmin), fit_capsule(b, axis, zmin)])
            cands.append([fit_box(a, R0, zmin), fit_box(b, R0, zmin)])
    if len(P) > 20:
        cands.append([fit_capsule(P, R0[:, 0], zmin)])
        cands.append([fit_capsule(P, R0[:, 1], zmin)])
    if single:  # one shape per slab
        cands = [gs for gs in cands if len(gs) == 1]
    if smooth:  # capsules and spheres only
        cands = [gs for gs in cands if all(g["type"] != "box" for g in gs)]
    if SURF is None or t0 is None:
        return min(cands, key=lambda gs: sum(g["vol"] for g in gs))
    return min(cands, key=lambda gs: standoff_score(gs, axis, t0, t1, origin, ends))


def fit_part(P, axis, k, zmin=None, overlap=0.004, penalise_ends=True, smooth=False, single=False):
    t = (P - P.mean(0)) @ axis
    edges = np.linspace(t.min(), t.max(), k + 1)
    geoms = []
    for i in range(k):
        sel = (t >= edges[i] - overlap) & (t <= edges[i + 1] + overlap)
        if sel.sum() < 4:
            continue
        geoms += fit_slab(P[sel], axis, zmin, edges[i], edges[i + 1], P.mean(0),
                          (edges[0], edges[-1]) if penalise_ends else None, smooth, single)
    return geoms


def fit_foot(r, info, s, P):
    """Front pad and heel tip boxes from the measured patches, then the stiletto and the rest of the shoe above."""
    V = r["verts"]
    fore, heel = V[r[f"patch_fore_{s}"]], V[r[f"patch_heel_{s}"]]
    f = unit(np.r_[(fore.mean(0) - heel.mean(0))[:2], 0])
    R = np.stack([f, np.cross([0, 0, 1.0], f), [0, 0, 1.0]], 1)
    geoms = []
    for name, pts in (("pad", fore), ("heel_tip", heel)):
        L = pts @ R
        lo, hi = L.min(0), L.max(0)
        c = R @ np.r_[(lo[:2] + hi[:2]) / 2, PAD_TOP / 2]
        geoms.append({"type": "box", "pos": c, "rot": R, "size": [*(hi[:2] - lo[:2]) / 2, PAD_TOP / 2],
                      "floor_contact": True, "what": name, "vol": float(np.prod(hi[:2] - lo[:2]) * PAD_TOP)})
    inside = (sd_geoms(P, geoms) <= 0.0005).any(1) | (P[:, 2] < CLEAR)
    rest = P[~inside]
    ank = r["joint_pos"][PI[f"foot_{s}"]]
    # stiletto: behind the ankle, below where the cross-section widens into the heel cup
    behind = rest[(rest - ank) @ f < -0.005]
    zc = None
    for z in np.arange(CLEAR, 0.1, 0.004):
        sl = behind[(behind[:, 2] >= z) & (behind[:, 2] < z + 0.004)]
        if len(sl) and np.ptp(sl @ R[:, 1]) > 0.028:
            zc = z
            break
    zc = zc if zc is not None else 0.06
    stil = ((rest - ank) @ f < -0.005) & (rest[:, 2] < zc)
    if stil.sum() > 8:
        sp = rest[stil]
        geoms += fit_part(sp, unit(np.linalg.svd(sp - sp.mean(0))[2][0]), 1 if SHOE_SIMPLE else 3, zmin=CLEAR,
                          single=SHOE_SIMPLE)
    body = rest[~stil]
    ax = unit(np.linalg.svd(body - body.mean(0))[2][0])  # along the pitched shoe, heel cup to toe
    geoms += fit_part(body, ax if ax @ f > 0 else -ax, 3 if SHOE_SIMPLE else 7, zmin=CLEAR, single=SHOE_SIMPLE)
    # nothing wider than the shoe: pull in any solid that sticks out past the shoe's sides
    side = R[:, 1]
    shoe = V[r[f"patch_shoe_{s}"]] @ side if s == "L" else (V[r["patch_shoe_R"]] * [-1, 1, 1]) @ side
    smin, smax = shoe.min(), shoe.max()
    for g in geoms[2:]:
        for _ in range(20):
            x = sample_surface(g, 800) @ side
            lo, hi = smin - x.min(), x.max() - smax
            if max(lo, hi) <= 0.0002:
                break
            n, e = (side, hi) if hi >= lo else (-side, lo)
            if g["type"] in ("capsule", "sphere"):
                g["size"] = [g["size"][0] - e / 2] + list(g["size"][1:])
                g["pos"] = np.array(g["pos"]) - n * e / 2
            else:
                Rg = np.array(g["rot"])
                k = int(np.argmax(np.abs(Rg.T @ n)))
                sz = list(g["size"])
                sz[k] -= e / 2 / abs(Rg[:, k] @ n)
                g["size"] = sz
                g["pos"] = np.array(g["pos"]) - n * e / 2
    for g in geoms:
        g.setdefault("floor_contact", False)
    return geoms, {"stiletto_top_m": float(zc), "pad_size_mm": [round(2000 * x, 1) for x in geoms[0]["size"][:2]],
                   "heel_tip_size_mm": [round(2000 * x, 1) for x in geoms[1]["size"][:2]]}


def own_standoff(P, gs):
    """Median distance from the outer surface of a part's solids to her surface (penalised if she pokes out)."""
    S = []
    for k, g in enumerate(gs):
        x = sample_surface(g, 500)
        mine = [h for i, h in enumerate(gs) if i != k]
        if mine:
            x = x[sd_geoms(x, mine).min(1) > 0.0005]
        S.append(x)
    S = np.vstack(S)
    poke = max(0.0, float(sd_geoms(P[::7], gs).min(1).max()))
    return float(np.median(SURF.query(S)[0])) + 3 * poke


def sample_surface(g, n=600):
    rng = np.random.default_rng(0)
    s = g["size"]
    if g["type"] == "sphere":
        v = rng.normal(size=(n, 3))
        L = unit_rows(v) * s[0]
    elif g["type"] == "capsule":
        r, h = s
        a_cyl, a_cap = 2 * np.pi * r * 2 * h, 4 * np.pi * r * r
        nc = int(n * a_cyl / (a_cyl + a_cap))
        th = rng.uniform(0, 2 * np.pi, nc)
        L1 = np.stack([r * np.cos(th), r * np.sin(th), rng.uniform(-h, h, nc)], 1)
        v = unit_rows(rng.normal(size=(n - nc, 3))) * r
        v[:, 2] += np.sign(v[:, 2]) * h
        L = np.vstack([L1, v])
    else:
        hs = np.array(s)
        L = rng.uniform(-1, 1, size=(n, 3)) * hs
        ax = rng.integers(0, 3, n)
        L[np.arange(n), ax] = np.sign(rng.uniform(-1, 1, n)) * hs[ax]
    return L @ np.array(g["rot"]).T + g["pos"]


def unit_rows(v):
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def fit_report(parts_pts, geoms, all_body):
    """Per part: how far her surface pokes out of the solids, and how far the solids stand off her surface."""
    tree = SURF
    rep = {}
    allg = [g for gs in geoms.values() for g in gs]
    for p in PARTS:
        P = parts_pts[p]
        poke = np.maximum(sd_geoms(P, allg).min(1), 0)
        own = sd_geoms(P, geoms[p]).min(1)
        S, others = [], [g for q in PARTS if q != p for g in geoms[q]]
        for k, g in enumerate(geoms[p]):
            x = sample_surface(g)
            mine = [h for i, h in enumerate(geoms[p]) if i != k]
            keep = np.ones(len(x), bool)
            if mine:
                keep &= sd_geoms(x, mine).min(1) > 0.0005
            if others:
                keep &= sd_geoms(x, others).min(1) > 0.0005
            S.append(x[keep])
        S = np.vstack(S) if S else np.zeros((0, 3))
        so = tree.query(S)[0] if len(S) else np.zeros(1)
        rep[p] = {"vertices": int(len(P)), "solids": len(geoms[p]),
                  "poke_out_mm": {"max": 1000 * float(poke.max()), "p95": 1000 * float(np.percentile(poke, 95)),
                                  "share_over_1mm": float((poke > 0.001).mean())},
                  "poke_out_of_own_solids_mm": {"max": 1000 * float(np.maximum(own, 0).max())},
                  "standoff_mm": {"max": 1000 * float(so.max()), "median": 1000 * float(np.median(so)),
                                  "p95": 1000 * float(np.percentile(so, 95))}}
    return rep


# ---------------------------------------------------------------- MuJoCo
def geom_quat(R):
    q = Rot.from_matrix(np.array(R)).as_quat()
    return [q[3], q[0], q[1], q[2]]


def build_spec(jp, joints, geoms, masses, excludes, root="free", floor=True):
    spec = mujoco.MjSpec()
    spec.modelname = "simulation_body_first_look"
    spec.compiler.degree = False  # joint ranges below are in radians
    spec.option.timestep = 0.001
    spec.option.integrator = mujoco.mjtIntegrator.mjINT_IMPLICITFAST
    if floor:
        spec.worldbody.add_geom(name="floor", type=mujoco.mjtGeom.mjGEOM_PLANE, size=[5, 5, 0.1],
                                rgba=[0.8, 0.8, 0.8, 1])
    bodies = {}
    for p in PARTS:
        par = PARENT[p]
        pos = jp[PI[p]] - (jp[PI[par]] if par else 0)
        b = (bodies[par] if par else spec.worldbody).add_body(name=p, pos=list(map(float, pos)))
        bodies[p] = b
        if par is None:
            if root == "free":
                b.add_freejoint(name="root")
            elif root == "carried":
                for nm, ax, typ in (("root_x", [1, 0, 0], "s"), ("root_y", [0, 1, 0], "s"), ("root_z", [0, 0, 1], "s"),
                                    ("root_rz", [0, 0, 1], "h"), ("root_rx", [1, 0, 0], "h"), ("root_ry", [0, 1, 0], "h")):
                    b.add_joint(name=nm, type=mujoco.mjtJoint.mjJNT_SLIDE if typ == "s" else mujoco.mjtJoint.mjJNT_HINGE,
                                axis=ax)
        else:
            j = joints[p]
            for k, ax in enumerate(j["axes"]):
                b.add_joint(name=f"{p}_{j['names'][k]}", type=mujoco.mjtJoint.mjJNT_HINGE, axis=list(map(float, ax)),
                            range=list(np.radians(j["range_deg"][k])), limited=mujoco.mjtLimited.mjLIMITED_TRUE,
                            armature=0.0005)
        vol = sum(g["vol"] for g in geoms[p])
        for k, g in enumerate(geoms[p]):
            typ = {"capsule": mujoco.mjtGeom.mjGEOM_CAPSULE, "box": mujoco.mjtGeom.mjGEOM_BOX,
                   "sphere": mujoco.mjtGeom.mjGEOM_SPHERE}[g["type"]]
            size = list(g["size"]) + [0] * (3 - len(g["size"]))
            b.add_geom(name=f"{p}_{k}", type=typ, size=size, pos=list(map(float, np.array(g["pos"]) - jp[PI[p]])),
                       quat=geom_quat(g["rot"]), mass=float(masses[p] * g["vol"] / vol),
                       rgba=list(COLORS[p]) + [1])
    for a, b in excludes:
        spec.add_exclude(bodyname1=a, bodyname2=b)
    return spec


def rest_contacts(m, d):
    mujoco.mj_forward(m, d)
    out = []
    for c in d.contact[:d.ncon]:
        out.append((mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, c.geom1),
                    mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, c.geom2), float(c.dist)))
    return out


def resolve_rest_overlaps(jp, joints, geoms, masses, parts_pts):
    """Keep non-adjacent parts' solids apart at rest. Where her own surfaces sit apart, shrink the two solids
    (radius, or the box side facing the other solid) so the solids keep a gap (2 mm, or half her own gap when
    that is under 4 mm). Where that would take more than 15 mm off a solid, exclude the body pair instead."""
    trees = {p: cKDTree(parts_pts[p]) for p in PARTS}
    adj = {frozenset((p, PARENT[p])) for p in PARTS[1:]}
    mesh_gap, excludes, log, shrunk, hist = {}, [tuple(sorted(p)) for p in SEAM_EXCLUDES], [], {}, {}
    trim_done = set()
    log += [f"exclude {a}-{b}: armpit seam (see SEAM_EXCLUDES)" for a, b in SEAM_EXCLUDES]
    for it in range(600):
        spec = build_spec(jp, joints, geoms, masses, excludes)
        m = spec.compile()
        d = mujoco.MjData(m)
        mujoco.mj_forward(m, d)
        gb = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, m.geom_bodyid[g]) for g in range(m.ngeom)]
        worst = None
        for g1 in range(m.ngeom):
            for g2 in range(g1 + 1, m.ngeom):
                b1, b2 = gb[g1], gb[g2]
                if b1 == "world" or b2 == "world" or b1 == b2 or frozenset((b1, b2)) in adj:
                    continue
                if tuple(sorted((b1, b2))) in excludes:
                    continue
                key = frozenset((b1, b2))
                if key not in mesh_gap:
                    mesh_gap[key] = float(trees[b1].query(parts_pts[b2])[0].min())
                need = 0.002 if mesh_gap[key] >= 0.004 else 0.5 * mesh_gap[key]
                tk = tuple(sorted((b1, b2)))
                if tk in TRIM and tk not in trim_done:
                    need = max(need, TRIM[tk] * mesh_gap[key])
                ft = np.zeros(6)
                dist = mujoco.mj_geomDistance(m, d, g1, g2, 0.05, ft)
                if dist < need and (worst is None or need - dist > worst[0]):
                    worst = (need - dist, g1, g2, b1, b2, ft.copy(), dist, need)
        if worst is None:
            break
        deficit, g1, g2, b1, b2, ft, dist, need = worst
        key = frozenset((b1, b2))
        k1 = int(mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, g1).split("_")[-1])
        k2 = int(mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, g2).split("_")[-1])
        s = deficit / 2 + 0.0002
        tk = tuple(sorted((b1, b2)))
        base_need = 0.002 if mesh_gap[key] >= 0.004 else 0.5 * mesh_gap[key]
        trimming = tk in TRIM and tk not in trim_done and dist >= base_need - 1e-4
        if tk in TRIM and not trimming:  # below the ordinary gap: shrink to that first, as without trims
            s = (base_need - dist) / 2 + 0.0002
        if trimming:
            s = min(s, 0.0015)  # small steps, each checked against her surface
            pk0 = [float(np.maximum(sd_geoms(parts_pts[b][::5], geoms[b]).min(1), 0).max()) for b in (b1, b2)]
            if shrunk.get((b1, k1), 0) + s > 0.015 or shrunk.get((b2, k2), 0) + s > 0.015:
                trim_done.add(tk)  # a trim never turns into an exclusion: stop trimming this pair
                log.append(f"trim {b1}-{b2} stopped at the 15 mm limit (solids {1000 * dist:.1f} mm apart)")
                continue
        if mesh_gap[key] < 0.001 or shrunk.get((b1, k1), 0) + s > 0.015 or shrunk.get((b2, k2), 0) + s > 0.015 \
                or geoms[b1][k1].get("floor_contact") or geoms[b2][k2].get("floor_contact"):
            mir = tuple(sorted(mirror(x) for x in (b1, b2)))
            for pair in {tuple(sorted((b1, b2))), mir}:  # the mirror pair goes too, so she stays symmetric
                for (b, k, size, pos, ds) in reversed(hist.pop(frozenset(pair), [])):  # undo the pair's shrinking
                    geoms[b][k]["size"], geoms[b][k]["pos"] = size, pos
                    shrunk[(b, k)] -= ds
                if pair not in excludes:
                    excludes.append(pair)
            log.append(f"exclude {b1}-{b2}" + (f" (and {mir[0]}-{mir[1]})" if mir != tuple(sorted((b1, b2))) else "")
                       + f": solids {1000 * dist:.1f} mm apart, her surfaces {1000 * mesh_gap[key]:.1f} mm")
            continue
        c1, c2 = np.array(geoms[b1][k1]["pos"]), np.array(geoms[b2][k2]["pos"])
        v = (ft[3:] - ft[:3]) * (1 if dist >= 0 else -1)
        n = unit(v) if np.linalg.norm(v) > 1e-7 else unit(c2 - c1)
        for b, k, sign in ((b1, k1, 1), (b2, k2, -1)):
            g = geoms[b][k]
            hist.setdefault(key, []).append((b, k, list(g["size"]), np.array(g["pos"]).copy(), s))
            if g["type"] in ("capsule", "sphere"):  # take s off the facing side, s/2 off the flanks, none off the back
                nn = n.copy()
                if g["type"] == "capsule":
                    ax = np.array(g["rot"])[:, 2]
                    nn = nn - ax * (nn @ ax)
                nn = unit(nn) if np.linalg.norm(nn) > 1e-6 else n
                g["size"] = [g["size"][0] - s / 2] + list(g["size"][1:])
                g["pos"] = np.array(g["pos"]) - sign * nn * s / 2
            else:
                R = np.array(g["rot"])
                ax = int(np.argmax(np.abs(R.T @ n)))
                sz = list(g["size"])
                sz[ax] -= s / 2
                g["size"] = sz
                g["pos"] = np.array(g["pos"]) - sign * np.sign(R[:, ax] @ n) * R[:, ax] * s / 2
            shrunk[(b, k)] = shrunk.get((b, k), 0) + s
        if trimming:  # a trim never goes inside her drawn surface: undo the step if she would poke out 2 mm more
            pk = [float(np.maximum(sd_geoms(parts_pts[b][::5], geoms[b]).min(1), 0).max()) for b in (b1, b2)]
            if max(a - b for a, b in zip(pk, pk0)) > 0.002 or max(pk) > max(max(pk0), 0.002):
                for (b, k, size, pos, ds) in hist[key][-2:]:
                    geoms[b][k]["size"], geoms[b][k]["pos"] = size, pos
                    shrunk[(b, k)] -= ds
                del hist[key][-2:]
                trim_done.add(tk)
                log.append(f"trim {b1}-{b2} stopped where her surface would poke out (solids {1000 * dist:.1f} mm apart)")
                continue
        log.append(f"shrink {b1}#{k1} and {b2}#{k2} by {1000 * s:.1f} mm (solids {1000 * dist:.1f} mm apart, "
                   f"keep {1000 * need:.1f}; her surfaces {1000 * mesh_gap[key]:.1f} mm)")
    return excludes, log, {"-".join(sorted(k)): v for k, v in mesh_gap.items()}, \
        {f"{b}#{k}": 1000 * v for (b, k), v in shrunk.items() if v > 1e-6}


def mirror(p):
    return p[:-1] + {"L": "R", "R": "L"}[p[-1]] if p.endswith(("_L", "_R")) else p


def surface_samples(r, keep, n=300000):
    """Points spread evenly over her body triangles (all three corners body, not trailing), each labelled with
    the part of its nearest corner; her vertices are added too."""
    V, T = r["verts"], r["tris"]
    T = T[keep[T].all(1)]
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    rng = np.random.default_rng(1)
    idx = rng.choice(len(T), n, p=area / area.sum())
    u, v = rng.uniform(size=(2, n))
    flip = u + v > 1
    u[flip], v[flip] = 1 - u[flip], 1 - v[flip]
    pts = a[idx] + (b[idx] - a[idx]) * u[:, None] + (c[idx] - a[idx]) * v[:, None]
    corner = np.argmax(np.stack([1 - u - v, u, v], 1), 1)
    vi = T[idx, corner]
    lab = r["vpart"][vi]
    return (np.vstack([pts, V[keep]]), np.r_[lab, r["vpart"][keep]],
            np.r_[r["vmat"][vi], r["vmat"][keep]])


def cranium_shell(r, jp, step_deg=4.0):
    """Her skull has no scalp mesh: take, per direction from the middle of her head, the innermost hair point
    (the hair's layer that rests on the scalp), over the top and back of the head only."""
    V, names = r["verts"], r["mat_names"]
    hair = np.isin(names[np.maximum(r["vmat"], 0)], list(HAIR)) & (r["vmat"] >= 0)
    c = jp[PI["head"]] + np.array([0, 0, 0.08])
    H = V[hair] - c
    rad = np.linalg.norm(H, axis=1)
    el = np.degrees(np.arcsin(np.clip(H[:, 2] / rad, -1, 1)))
    az = np.degrees(np.arctan2(H[:, 1], H[:, 0]))
    front = H[:, 1] < 0
    ok = (rad < 0.13) & np.where(front, el > 15, el > -25)
    cell = (np.floor(az / step_deg) * 1000 + np.floor(el / step_deg)).astype(int)
    out = []
    for k in np.unique(cell[ok]):
        sel = np.nonzero(ok & (cell == k))[0]
        out.append(H[sel[np.argmin(rad[sel])]])
    out = np.array(out)
    # The hair's inner layer stands 10-25 mm off the skull at the sides (her temples), so it overstates the
    # width: hold the cranium's sides to her face's own half-width plus 5 mm.
    face = names[np.maximum(r["vmat"], 0)] == "颜"
    half = np.abs(V[face & (r["vmat"] >= 0), 0]).max() + 0.005
    out = out + c
    out[:, 0] = np.clip(out[:, 0], -half, half)
    return out


def select_surface(r, jp, S, lab, mat):
    """Keep her body surface by what it is (see HAIR / CORE / CLOSE); returns the kept samples, their parts,
    the cranium points and a per-material count of what was kept and dropped."""
    names = r["mat_names"][np.maximum(mat, 0)]
    shell = cranium_shell(r, jp)
    is_hair = np.isin(names, list(HAIR))
    torso = np.isin(lab, [PI["chest"], PI["waist"]])
    core = np.isin(names, list(CORE)) | (np.isin(names, list(CORE_ON_TORSO)) & torso)
    tree = cKDTree(np.vstack([S[core], shell]))
    other = ~core & ~is_hair
    near = np.zeros(len(S), bool)
    near[other] = tree.query(S[other], distance_upper_bound=CLOSE)[0] <= CLOSE
    keep = core | (other & near)
    if HEAD_SKULL_ONLY:
        keep &= core | (lab != PI["head"])
    stats = {}
    for nm in np.unique(names):
        sel = names == nm
        stats[str(nm)] = {"kept": int((sel & keep).sum()), "dropped": int((sel & ~keep).sum())}
    S2 = np.vstack([S[keep], shell])
    lab2 = np.r_[lab[keep], np.full(len(shell), PI["head"])]
    return S2, lab2, shell, stats


# ---------------------------------------------------------------- main
def main():
    t0 = time.time()
    r, info = load_rest()
    jp = r["joint_pos"]
    V = r["verts"]
    keep = (r["vpart"] >= 0) & ~r["vtrail"] & (r["vmat"] >= 0)
    S, lab, mat = surface_samples(r, keep)
    S, lab, shell, surf_stats = select_surface(r, jp, S, lab, mat)
    H = parts_pts_head = S[lab == PI["head"]]
    head_dims = {"width_mm": 1000 * float(np.ptp(H[:, 0])), "depth_mm": 1000 * float(np.ptp(H[:, 1])),
                 "chin_to_crown_mm": 1000 * float(H[:, 2].max() - H[:, 2].min()),
                 "crown_z_m": float(H[:, 2].max()), "cranium_points": int(len(shell))}
    print("head as fitted:", head_dims, flush=True)
    parts_pts = {p: S[lab == PI[p]] for p in PARTS}
    all_body = S
    tdir = limb_dirs(r, info)
    global SURF
    SURF = cKDTree(S)

    # ---- solids
    # Her mesh is mirror-symmetric (bar a few left-side crystals): each left part is fitted to its own points
    # plus the mirrored right part's, and the right part's solids are the mirror image, so she stays symmetric.
    geoms, foot_info, search = {}, {}, {}
    S_ = np.diag([-1.0, 1, 1])
    for p in PARTS:
        if p.endswith("_R"):
            continue
        P = parts_pts[p]
        if p.endswith("_L"):
            P = np.vstack([P, parts_pts[mirror(p)] @ S_])
        if base(p) == "foot":
            geoms[p], foot_info[p] = fit_foot(r, info, "L", P)
        else:
            ax = np.array([0, 0, 1.0]) if base(p) in ("pelvis", "waist", "chest", "head") else tdir[p]
            # a small search: slab count and whether to penalise solids hanging past the part's ends; keep
            # whichever stands off her surface least (typical), with nothing of hers poking out
            best = None
            # (hands: no extra slabs; many small solids on both hands snag on each other when the arms cross)
            for k in ((SLABS[base(p)],) if base(p) == "hand" else (SLABS[base(p)], SLABS[base(p)] + 2)):
                for pen in (True, False):
                    gs = fit_part(P, ax, k, penalise_ends=pen)
                    sc = own_standoff(P, gs)
                    if best is None or sc < best[0]:
                        best = (sc, gs, k, pen)
            if base(p) == "head":  # a stack of thin boxes reads badly on a round head: take capsules and
                for k in (3, 4):   # spheres when they stand off at most 3 mm more
                    gs = fit_part(P, ax, k, penalise_ends=True, smooth=True)
                    sc = own_standoff(P, gs)
                    if sc <= best[0] + 0.003 and (len(best) < 5 or sc < best[0]):
                        best = (sc, gs, k, True, "smooth")
            geoms[p] = best[1]
            search[p] = {"slabs": best[2], "end_penalty": best[3], "typical_standoff_mm": 1000 * best[0],
                         "smooth": len(best) > 4}
            for g in geoms[p]:
                g["floor_contact"] = False
        if p.endswith("_L"):
            geoms[mirror(p)] = [dict(g, pos=S_ @ np.array(g["pos"]), rot=S_ @ np.array(g["rot"]) @ S_,
                                     size=list(g["size"])) for g in geoms[p]]
            if p in foot_info:
                foot_info[mirror(p)] = foot_info[p]
    geoms = {p: geoms[p] for p in PARTS}
    masses = {p: TOTAL_KG * SHARE[base(p)] / 100 for p in PARTS}

    frozen = os.environ.get("FREEZE_JOINTS")  # round 2 on: the joints of an earlier round, unchanged
    if not frozen:  # early rough body.json for the other worker (identity-axis joints, no ranges yet)
        rough = {p: {"type": "ball", "axes": np.eye(3).tolist(), "names": ["x", "y", "z"],
                     "range_deg": [[-180, 180]] * 3} for p in PARTS[1:]}
        write_body_json(jp, rough, geoms, masses)
        print(f"rough body.json written ({time.time() - t0:.0f}s)", flush=True)

    # ---- joint axes and ranges
    if frozen:
        old = json.load(open(frozen, encoding="utf-8"))
        joints, motions_info = old["joints"], old["motions"]
        if ELBOW_PAST_DEG:
            for s_ in "LR":
                j = joints[f"forearm_{s_}"]
                j["range_deg"][0][0] = j["straight_deg"] - ELBOW_PAST_DEG
                j["elbow_past_straight_allowed_deg"] = ELBOW_PAST_DEG
    else:
        joints, motions_info = fit_joints(tdir, t0)
    print(f"axes and ranges done ({time.time() - t0:.0f}s){' (frozen from ' + frozen + ')' if frozen else ''}", flush=True)
    return finish(t0, r, jp, V, joints, geoms, masses, parts_pts, all_body, foot_info, motions_info,
                  {"surface_kept": surf_stats, "head_dims": head_dims, "joints_frozen_from": frozen,
                   "fit_search": search})


def fit_joints(tdir, t0):
    motions = load_motions()
    Dall = np.concatenate([D for _, D in motions])
    joints = {}
    for p in PARTS[1:]:
        Rrel = np.einsum("nji,njk->nik", Dall[:, PI[PARENT[p]]], Dall[:, PI[p]])
        upper = tdir.get(PARENT[p], np.array([0, 0, 1.0]))
        joints[p] = choose_axes(p, tdir[p], Rrel, upper)
    # middle-axis angle after sequential decomposition (the one MuJoCo will see)
    joints = joint_ranges(joints, motions, tdir)
    for p in PARTS[1:]:
        if joints[p]["type"] == "ball":
            joints[p]["worst_middle_deg"] = max(joints[p]["worst_middle_per_kind_deg"].values())
    return joints, [{"key": mm["key"], "kind": mm["kind"], "name": mm["name"], "frames": int(len(D))}
                    for mm, D in motions]


def finish(t0, r, jp, V, joints, geoms, masses, parts_pts, all_body, foot_info, motions_info, extra):
    # ---- rest-pose overlaps
    excludes, log, mesh_gap, shrunk = resolve_rest_overlaps(jp, joints, geoms, masses, parts_pts)
    spec = build_spec(jp, joints, geoms, masses, excludes)
    m = spec.compile()
    d = mujoco.MjData(m)
    contacts = rest_contacts(m, d)
    fit = fit_report(parts_pts, geoms, all_body)
    foot_w = {p: float(np.ptp(np.vstack([sample_surface(g, 300) for g in geoms[p]]) @ np.cross([0, 0, 1.0], unit(np.r_[(V[r[f"patch_fore_{p[-1]}"]].mean(0) - V[r[f"patch_heel_{p[-1]}"]].mean(0))[:2], 0])))) for p in ("foot_L", "foot_R")}
    shoe_w = {p: float(np.ptp(V[r[f"patch_shoe_{p[-1]}"]] @ np.cross([0, 0, 1.0], unit(np.r_[(V[r[f"patch_fore_{p[-1]}"]].mean(0) - V[r[f"patch_heel_{p[-1]}"]].mean(0))[:2], 0])))) for p in ("foot_L", "foot_R")}

    with open(os.path.join(OUT, "body.xml"), "w", encoding="utf-8") as f:
        f.write(spec.to_xml())
    write_body_json(jp, joints, geoms, masses)
    body_mass = {mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, b): float(m.body_mass[b]) for b in range(1, m.nbody)}
    infoj = {"joints": joints, "excludes": excludes, "overlap_log": log, "mesh_gap_m": mesh_gap, "shrunk_mm": shrunk,
             "rest_contacts": contacts, "fit": fit, "foot": foot_info, "foot_solid_width_m": foot_w,
             "shoe_width_m": shoe_w, "masses": body_mass, "total_mass": float(sum(body_mass.values())),
             "mesh_lowest_z_m": float(all_body[:, 2].min()),
             "motions": motions_info, **extra}
    with open(os.path.join(OUT, "body_info.json"), "w", encoding="utf-8") as f:
        json.dump(infoj, f, ensure_ascii=False, indent=1, default=float)
    print(f"body done ({time.time() - t0:.0f}s): {sum(len(g) for g in geoms.values())} solids, "
          f"{len(excludes)} excluded pairs, rest contacts {contacts}")


def write_body_json(jp, joints, geoms, masses):
    out = {"parts": [], "joints": [], "geoms": []}
    for p in PARTS:
        out["parts"].append({"name": p, "parent": PARENT[p], "joint_pos": jp[PI[p]].tolist(), "mass": masses[p],
                             "color": list(COLORS[p])})
    for p in PARTS[1:]:
        j = joints[p]
        for k, ax in enumerate(j["axes"]):
            out["joints"].append({"name": f"{p}_{j['names'][k]}", "part": p, "pos": jp[PI[p]].tolist(),
                                  "axis": list(map(float, ax)), "range_deg": list(map(float, j["range_deg"][k]))})
    for p in PARTS:
        for g in geoms[p]:
            out["geoms"].append({"part": p, "type": g["type"], "pos": list(map(float, g["pos"])),
                                 "rot": np.array(g["rot"]).tolist(), "size": list(map(float, g["size"])),
                                 "floor_contact": bool(g.get("floor_contact", False))})
    tmp = os.path.join(OUT, "body.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    os.replace(tmp, os.path.join(OUT, "body.json"))


if __name__ == "__main__":
    main()
