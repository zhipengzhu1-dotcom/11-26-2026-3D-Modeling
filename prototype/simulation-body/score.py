"""PROTOTYPE (throwaway). The fixed scorecard for the stiff and soft figures, judged as humanoids.

  uv run --with numpy --with scipy python score.py <epoch_dir> <out_dir>

<epoch_dir> holds body.json, clips.json, sim/<clip>.npz and sim_diag/<clip>_<figure>.npz (written by
simulate.py). Writes <out_dir>/scorecard.json and scorecard.md. The scorecard was fixed before epoch 0 was
scored and must not change. Each line scores linearly between its "full" and "zero" values; every line is scored
per clip, and a figure's line score is the mean over the clips where the line can be measured.

Where a line could not be computed exactly as written, the nearest measurable thing is used (fixed from epoch 0):
- positions of hands, feet and head relative to the pelvis: the reference comes from her evaluated skeleton in
  Blender, the figures from MuJoCo, so the elbow's hinge-plus-twist model leaves a small floor under this error.
- "press with more than 20 N": the summed normal contact force between each pair of her solids, sampled once per
  output frame (30 per second), compared with 20 N.
- "held against a range end": the joint within 0.5 deg of a range end while the reference lies more than 0.5 deg
  inside the range; sampled once per output frame.
- planted foot: both floor-contact shapes of that foot (front pad, heel tip) with their lowest corner within 1 cm
  of the floor in the reference, and the reference foot (midpoint of the two shapes) moving under 5 cm/s.
  Slide = the figure's same midpoint moving across the floor (horizontal speed) in those frames.
- shake: a 2nd-order Butterworth high-pass at 8 Hz, run forwards and backwards, on the joint-angle error sampled
  at 30 per second (8 Hz is just under that rate's 15 Hz limit); RMS over joints and frames.
- lag: per joint, the time shift that best lines the figure's angle up with the reference's (cross-correlation
  over +-300 ms on angles logged 240 times a second, peak refined by a parabola); the mean of its size weighted by
  how much the reference moves that joint (standard deviation; joints moving under 1 deg are left out).
- overshoot: at each turning point of a joint in the reference that ends a swing of at least 10 deg, how far the
  figure goes past the reference's own extreme from 1/6 s before to the next turning point (at most 1/2 s after),
  as a share of the swing; only where neither that part nor anything below it touches anything in that window;
  the median over the clip's events.
- effort: the largest torque on any of her joints (servo plus gravity compensation), against her weight times
  her leg length (hip to knee to ankle at rest), both from the model.
"""
import json
import os
import sys

import numpy as np
from scipy.signal import butter, filtfilt

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS = ["pelvis", "waist", "chest", "neck", "head", "collar_L", "collar_R", "upper_arm_L", "upper_arm_R",
         "forearm_L", "forearm_R", "hand_L", "hand_R", "thigh_L", "thigh_R", "shin_L", "shin_R", "foot_L", "foot_R"]
PI = {p: i for i, p in enumerate(PARTS)}
PARENT = {"waist": "pelvis", "chest": "waist", "neck": "chest", "head": "neck"}
for _s in "LR":
    PARENT.update({f"collar_{_s}": "chest", f"upper_arm_{_s}": f"collar_{_s}", f"forearm_{_s}": f"upper_arm_{_s}",
                   f"hand_{_s}": f"forearm_{_s}", f"thigh_{_s}": "pelvis", f"shin_{_s}": f"thigh_{_s}",
                   f"foot_{_s}": f"shin_{_s}"})
CLIPS = ["dance", "walk", "cute_heart", "cute_peace", "sing"]
FPS = 30

# line: (group, points, full, zero)  -- lower is better unless noted
LINES = {
    "1a_part_rotation_deg": ("follows", 15, 3, 20),
    "1b_end_position_cm": ("follows", 15, 1.5, 12),
    "2a_head_p95_deg": ("posture", 10, 8, 45),
    "2b_spine_p95_deg": ("posture", 5, 5, 25),
    "3a_pressing_frames_pct": ("fight", 8, 2, 30),
    "3b_deepest_overlap_mm": ("fight", 4, 2, 15),
    "3c_held_at_limit_pct": ("fight", 3, 0.2, 5),
    "4a_planted_foot_rot_deg": ("feet", 5, 3, 25),
    "4b_planted_foot_slide_cm_s": ("feet", 5, 1, 10),
    "5_shake_deg": ("smooth", 10, 0.3, 3),
    "6a_lag_ms": ("spring", 8, 30, 250),
    "6b_overshoot_pct": ("spring", 7, None, None),
    "7_effort_ratio": ("effort", 5, 0.5, 2.5),
}
GROUPS = ["follows", "posture", "fight", "feet", "smooth", "spring", "effort"]
GROUP_NAMES = {"follows": "Follows the motion (30)", "posture": "Holds her posture (15)",
               "fight": "Does not fight herself (15)", "feet": "Feet and floor (10)", "smooth": "Moves smoothly (10)",
               "spring": "Springs the right amount (15)", "effort": "Believable effort (5)"}


def lin(x, full, zero, pts):
    return float(pts * np.clip((zero - x) / (zero - full), 0, 1))


def overshoot_points(x, fig):
    if fig == "stiff":  # full 0-5 %, zero at 25 % or more
        return lin(max(x, 5.0), 5.0, 25.0, 7)
    if x < 5:  # soft: full 5-20 %, zero at 0 % and at 45 % or more
        return float(7 * np.clip(x / 5.0, 0, 1))
    return lin(max(x, 20.0) if x >= 20 else 20.0, 20.0, 45.0, 7)


def rot_err(Ra, Rb):
    c = (np.einsum("...ij,...ij->...", Ra, Rb) - 1) / 2
    return np.degrees(np.arccos(np.clip(c, -1, 1)))


def foot_boxes(body):
    jp = {p["name"]: np.array(p["joint_pos"]) for p in body["parts"]}
    out = {}
    for s in "LR":
        gs = [g for g in body["geoms"] if g["part"] == f"foot_{s}" and g["floor_contact"]]
        corners = []
        for g in gs:
            R, h = np.array(g["rot"]), np.array(g["size"])
            c = np.array([[sx, sy, sz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]) * h
            corners.append(c @ R.T + np.array(g["pos"]) - jp[f"foot_{s}"])  # in the foot's rest frame, from its joint
        out[s] = corners
    return out


def foot_track(pos, rot, s, boxes):
    """Per frame: lowest z of each floor-contact shape, and the midpoint of the shapes' centres."""
    i = PI[f"foot_{s}"]
    lows, mids = [], []
    for c in boxes[s]:
        w = np.einsum("tij,kj->tki", rot[:, i], c) + pos[:, i][:, None, :]
        lows.append(w[:, :, 2].min(1))
        mids.append(w.mean(1))
    return np.stack(lows, 1), np.mean(mids, 0)


def lag_ms(dg):
    q, r, t = np.degrees(dg["q_hi"]), np.degrees(dg["qref_hi"]), dg["t_hi"]
    if len(t) < 50:
        return None
    dt = t[1] - t[0]
    K = int(round(0.3 / dt))
    num = den = 0.0
    for j in range(q.shape[1]):
        a, b = q[:, j] - q[:, j].mean(), r[:, j] - r[:, j].mean()
        sd = b.std()
        if sd < 1.0:
            continue
        cc = np.array([np.dot(a[k:], b[:len(b) - k]) if k >= 0 else np.dot(a[:k], b[-k:]) for k in range(-K, K + 1)])
        i = int(np.argmax(cc))
        sh = 0.0
        if 0 < i < len(cc) - 1:
            den_ = cc[i - 1] - 2 * cc[i] + cc[i + 1]
            sh = 0.5 * (cc[i - 1] - cc[i + 1]) / den_ if den_ != 0 else 0.0
        lag = (i - K + sh) * dt  # positive: the figure trails the reference
        num += sd * abs(lag)
        den += sd
    return 1000 * num / den if den else None


def overshoot_pct(dg):
    q, r, cm = np.degrees(dg["q"]), np.degrees(dg["qref"]), dg["contact_mask"]
    names = [str(n) for n in dg["joint_names"]]
    sub = {p: {p} for p in PARTS}
    for p in reversed(PARTS[1:]):
        sub[PARENT[p]] |= sub[p]
    ev = []
    for j, nm in enumerate(names):
        part = next(p for p in PARTS[1:] if nm.startswith(p + "_"))
        free = ~cm[:, [PI[x] for x in sub[part]]].any(1)
        rr, ss = r[:, j], q[:, j]
        v = np.gradient(rr)
        tp = [f for f in range(1, len(rr) - 1) if v[f - 1] * v[f + 1] < 0 or (v[f] == 0 and v[f - 1] * v[f + 1] <= 0)]
        tp = sorted(set(tp))
        prev = 0
        for k, f in enumerate(tp):
            swing = abs(rr[f] - rr[prev])
            nxt = tp[k + 1] if k + 1 < len(tp) else len(rr) - 1
            prev = f
            if swing < 10:
                continue
            w = slice(max(0, f - 5), min(nxt, f + 15) + 1)
            if not free[w].all():
                continue
            sign = 1 if v[f - 1] > 0 else -1
            o = max(0.0, float(np.max(sign * ss[w]) - np.max(sign * rr[w])))
            ev.append(100 * o / swing)
    return (float(np.median(ev)) if ev else None), len(ev)


def score_clip(edir, clip, fig, body, boxes, weight_len):
    z = np.load(os.path.join(edir, "sim", clip + ".npz"))
    dg = np.load(os.path.join(edir, "sim_diag", f"{clip}_{fig}.npz"))
    R, Rr = z[f"rot_{fig}"].astype(float), z["rot_ref"].astype(float)
    P, Pr = z[f"pos_{fig}"].astype(float), z["pos_ref"].astype(float)
    e = rot_err(R, Rr)
    m = {}
    m["1a_part_rotation_deg"] = float(e.mean())
    ends = [PI[p] for p in ("hand_L", "hand_R", "foot_L", "foot_R", "head")]
    rel = (P[:, ends] - P[:, :1]) - (Pr[:, ends] - Pr[:, :1])
    m["1b_end_position_cm"] = 100 * float(np.linalg.norm(rel, axis=2).mean())
    m["2a_head_p95_deg"] = float(np.percentile(e[:, PI["head"]], 95))
    m["2b_spine_p95_deg"] = float(np.percentile(e[:, [PI["waist"], PI["chest"]]], 95))
    m["3a_pressing_frames_pct"] = 100 * float((dg["self_pair_force_max"] > 20).mean())
    m["3b_deepest_overlap_mm"] = 1000 * float(dg["self_depth_max"].max())
    lo, hi = dg["range"][:, 0], dg["range"][:, 1]
    inside = (dg["qref"] > lo + np.radians(0.5)) & (dg["qref"] < hi - np.radians(0.5))
    m["3c_held_at_limit_pct"] = 100 * float((dg["held_at_limit"] & inside).mean())
    rots, slides = [], []
    for s in "LR":
        low_r, mid_r = foot_track(Pr, Rr, s, boxes)
        low_f, mid_f = foot_track(P, R, s, boxes)
        sp_r = np.linalg.norm(np.gradient(mid_r, axis=0), axis=1) * FPS
        planted = (low_r.max(1) <= 0.01) & (sp_r < 0.05)
        if planted.any():
            rots.append(e[planted, PI[f"foot_{s}"]])
            slides.append(np.linalg.norm(np.gradient(mid_f[:, :2], axis=0), axis=1)[planted] * FPS)
    m["4a_planted_foot_rot_deg"] = float(np.concatenate(rots).mean()) if rots else None
    m["4b_planted_foot_slide_cm_s"] = 100 * float(np.concatenate(slides).mean()) if slides else None
    err = np.degrees(dg["q"] - dg["qref"])
    b, a = butter(2, 8.0 / (FPS / 2), btype="high")
    m["5_shake_deg"] = float(np.sqrt(np.mean(filtfilt(b, a, err, axis=0) ** 2)))
    unstable = int(dg["warnings"]) > 0 or not bool(dg["ok"])
    m["6a_lag_ms"] = lag_ms(dg)
    m["6b_overshoot_pct"], n_ev = overshoot_pct(dg)
    m["7_effort_ratio"] = float(dg["torque_max"].max()) / weight_len
    pts = {}
    for k, (g, p, full, zero) in LINES.items():
        x = m[k]
        if x is None:
            pts[k] = None
        elif k == "6b_overshoot_pct":
            pts[k] = overshoot_points(x, fig)
        elif k == "5_shake_deg" and unstable:
            pts[k] = 0.0
        else:
            pts[k] = lin(x, full, zero, p)
    return {"measured": m, "points": pts, "overshoot_events": n_ev, "unstable": unstable}


def main():
    edir, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    body = json.load(open(os.path.join(edir, "body.json"), encoding="utf-8"))
    boxes = foot_boxes(body)
    jp = {p["name"]: np.array(p["joint_pos"]) for p in body["parts"]}
    leg = float(np.linalg.norm(jp["shin_L"] - jp["thigh_L"]) + np.linalg.norm(jp["foot_L"] - jp["shin_L"]))
    mass = float(sum(p["mass"] for p in body["parts"]))
    weight_len = mass * 9.81 * leg
    card = {"weight_times_leg_Nm": weight_len, "leg_m": leg, "mass_kg": mass, "figures": {}}
    for fig in ("stiff", "soft"):
        per = {c: score_clip(edir, c, fig, body, boxes, weight_len) for c in CLIPS}
        lines = {}
        for k in LINES:
            vals = [per[c]["points"][k] for c in CLIPS if per[c]["points"][k] is not None]
            lines[k] = float(np.mean(vals)) if vals else 0.0
        groups = {g: sum(v for k, v in lines.items() if LINES[k][0] == g) for g in GROUPS}
        card["figures"][fig] = {"total": sum(groups.values()), "groups": groups, "lines": lines, "per_clip": per}
    with open(os.path.join(out, "scorecard.json"), "w", encoding="utf-8") as f:
        json.dump(card, f, indent=1)
    L = [f"# Scorecard: {os.path.basename(os.path.normpath(out))}\n",
         f"Her weight times her leg length: {weight_len:.0f} N m ({mass:.1f} kg, leg {100 * leg:.1f} cm).\n",
         "| Figure | Total | " + " | ".join(GROUP_NAMES[g] for g in GROUPS) + " |",
         "|---|---|" + "---|" * len(GROUPS)]
    for fig in ("stiff", "soft"):
        F = card["figures"][fig]
        L.append(f"| {fig} | **{F['total']:.1f}** | " + " | ".join(f"{F['groups'][g]:.1f}" for g in GROUPS) + " |")
    for fig in ("stiff", "soft"):
        F = card["figures"][fig]
        L.append(f"\n## {fig}: every line, per clip (measured value, points)\n")
        L.append("| Line (points) | " + " | ".join(CLIPS) + " | Mean points |")
        L.append("|---|" + "---|" * (len(CLIPS) + 1))
        for k, (g, p, full, zero) in LINES.items():
            cells = []
            for c in CLIPS:
                x, pt = F["per_clip"][c]["measured"][k], F["per_clip"][c]["points"][k]
                cells.append("n/a" if x is None else f"{x:.2f} ({pt:.1f})")
            L.append(f"| {k} ({p}) | " + " | ".join(cells) + f" | {F['lines'][k]:.2f} |")
    with open(os.path.join(out, "scorecard.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    for fig in ("stiff", "soft"):
        F = card["figures"][fig]
        print(f"{fig}: total {F['total']:.1f}  " + "  ".join(f"{g} {F['groups'][g]:.1f}" for g in GROUPS))


if __name__ == "__main__":
    main()
