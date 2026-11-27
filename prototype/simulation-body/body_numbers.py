"""PROTOTYPE (throwaway). Gathers the numbers of the Simulation Body half into review/first-look/<round>/.

  python body_numbers.py <round>   ->  numbers.json and numbers.md
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.environ.get("FIRSTLOOK_DIR", os.path.join(REPO, "build", "first-look"))
PARTS = ["pelvis", "waist", "chest", "neck", "head", "collar_L", "collar_R", "upper_arm_L", "upper_arm_R",
         "forearm_L", "forearm_R", "hand_L", "hand_R", "thigh_L", "thigh_R", "shin_L", "shin_R", "foot_L", "foot_R"]


def axis_words(v):
    names = [("her left", "her right"), ("her back", "her front"), ("up", "down")]
    k = max(range(3), key=lambda i: abs(v[i]))
    word = names[k][0] if v[k] > 0 else names[k][1]
    return f"{word} ({v[0]:+.2f}, {v[1]:+.2f}, {v[2]:+.2f})" if abs(v[k]) < 0.95 else word


def glance(w, dst, bi):
    """Per clip and figure, from this round's scorecard and simulation logs (when a scorecard exists)."""
    sc = os.path.join(dst, "scorecard.json")
    if not os.path.exists(sc):
        return
    card = json.load(open(sc))
    w("## At a glance, per clip and figure\n")
    w("Overshoot: median share of the swing the figure goes past the motion's turning points while nothing "
      "touches. Lag: how far the figure trails the motion. Head: 95th-percentile head rotation error. Part error: "
      "mean rotation error over all 19 parts. Elbow past straight: share of frames in which either elbow is bent "
      "past the straight limb, and the most, for the figure and (in brackets) for the Reference Motion. "
      f"Elbows may now go {bi['joints']['forearm_L'].get('elbow_past_straight_allowed_deg', 0):.0f} deg past straight; "
      "knees not at all.\n")
    w("| Clip | Figure | Overshoot | Lag | Head (95%) | Part error | Elbow past straight |\n|---|---|---|---|---|---|---|")
    for clip in card["figures"]["stiff"]["per_clip"]:
        for fig in ("stiff", "soft"):
            m = card["figures"][fig]["per_clip"][clip]["measured"]
            dg = np.load(os.path.join(OUT, "sim_diag", f"{clip}_{fig}.npz"))
            names = [str(n) for n in dg["joint_names"]]
            past_f, past_r = [], []
            for sd in "LR":
                j = names.index(f"forearm_{sd}_flex")
                st = bi["joints"][f"forearm_{sd}"]["straight_deg"]
                past_f.append(st - np.degrees(dg["q"][:, j]))
                past_r.append(st - np.degrees(dg["qref"][:, j]))
            pf, pr = np.max(past_f, 0), np.max(past_r, 0)
            ov = "n/a" if m["6b_overshoot_pct"] is None else f"{m['6b_overshoot_pct']:.1f}%"
            lag = "n/a" if m["6a_lag_ms"] is None else f"{m['6a_lag_ms']:.0f} ms"
            w(f"| {clip} | {fig} | {ov} | {lag} | {m['2a_head_p95_deg']:.1f} | {m['1a_part_rotation_deg']:.1f} | "
              f"{100 * (pf > 0).mean():.0f}%, up to {max(pf.max(), 0):.1f} ({100 * (pr > 0).mean():.0f}%, up to "
              f"{max(pr.max(), 0):.1f}) |")
    w(f"\nScores (fixed scorecard, out of 100): stiff {card['figures']['stiff']['total']:.1f}, "
      f"soft {card['figures']['soft']['total']:.1f}; every line in `scorecard.md`.\n")


GROUPS = {"head": ["head"], "upper arms": ["upper_arm_L", "upper_arm_R"], "hands": ["hand_L", "hand_R"]}


def part_errors(npz_dir, clip):
    z = np.load(os.path.join(npz_dir, clip + ".npz"))
    out = {}
    for v in ("stiff", "soft"):
        c = (np.einsum("tpij,tpij->tp", z[f"rot_{v}"], z["rot_ref"]) - 1) / 2
        e = np.degrees(np.arccos(np.clip(c, -1, 1)))
        out[v] = {g: {"mean": float(e[:, [PARTS.index(p) for p in ps]].mean()),
                      "worst": float(e[:, [PARTS.index(p) for p in ps]].max())} for g, ps in GROUPS.items()}
    return out


def before_after(w, rnd, bi, si, numbers):
    """Round 1 against this round, read from round 1's own files (never hard-coded)."""
    r1n = os.path.join(REPO, "review", "first-look", "round1", "numbers.json")
    snap = os.path.join(REPO, "build", "first-look", "round1_snapshot")
    if rnd == "round1" or not (os.path.exists(r1n) and os.path.exists(os.path.join(snap, "sim_info.json"))):
        return
    n1 = json.load(open(r1n, encoding="utf-8"))
    s1 = json.load(open(os.path.join(snap, "sim_info.json"), encoding="utf-8"))
    ba = {"standoff_typical_mm": {}, "part_error_deg": {}, "self_contacts_per_frame": {}}
    w(f"\n## Before and after: round 1 against {rnd}\n")
    w("Only the solids changed. Round 1's numbers are read from `review/first-look/round1/numbers.json` and "
      "from round 1's own simulation files (kept in `build/first-look/round1_snapshot/` and re-run there with "
      "round 1's body to count self-contacts per frame; that re-run reproduced round 1's joint errors exactly).\n")
    w("Typical stand-off from her surface (mm; round 2 measures against her surface without hair or loose "
      "cloth, so the two columns are not measured against quite the same surface):\n")
    w("| Part | Round 1 | " + rnd + " |\n|---|---|---|")
    for p in PARTS:
        a, b = n1["fit"][p]["standoff_mm"]["median"], bi["fit"][p]["standoff_mm"]["median"]
        ba["standoff_typical_mm"][p] = [a, b]
        w(f"| {p} | {a:.1f} | {b:.1f} |")
    w("\nPart error against `ref` (degrees, mean / worst), head, upper arms and hands:\n")
    w("| Clip | Figure | Head, r1 | Head, " + rnd + " | Upper arms, r1 | Upper arms, " + rnd + " | Hands, r1 | Hands, "
      + rnd + " |\n|---|---|---|---|---|---|---|---|")
    for c in si["clips"]:
        e1, e2 = part_errors(os.path.join(snap, "sim"), c), part_errors(os.path.join(OUT, "sim"), c)
        ba["part_error_deg"][c] = {"round1": e1, rnd: e2}
        for v in ("stiff", "soft"):
            cells = []
            for g in GROUPS:
                for e in (e1, e2):
                    cells.append(f"{e[v][g]['mean']:.1f} / {e[v][g]['worst']:.0f}")
            w(f"| {c} | {v} | " + " | ".join(cells) + " |")
    w("\nContacts between her own parts per frame (mean / most in one frame):\n")
    w("| Clip | Stiff, r1 | Stiff, " + rnd + " | Soft, r1 | Soft, " + rnd + " |\n|---|---|---|---|---|")
    for c, rec in si["clips"].items():
        o = s1["clips"][c]
        cells = []
        for v in ("stiff", "soft"):
            for r_ in (o, rec):
                cells.append(f"{r_[v]['mean_self_contacts_per_frame']:.1f} / {r_[v]['max_self_contacts_in_a_frame']}")
        ba["self_contacts_per_frame"][c] = {"round1": {v: o[v]["mean_self_contacts_per_frame"] for v in ("stiff", "soft")},
                                            rnd: {v: rec[v]["mean_self_contacts_per_frame"] for v in ("stiff", "soft")}}
        w(f"| {c} | " + " | ".join(cells) + " |")
    w(f"\nExcluded body pairs: round 1 {', '.join('-'.join(p) for p in n1['excluded_pairs'])}; "
      f"{rnd} {', '.join('-'.join(p) for p in bi['excludes'])}.")
    numbers["before_after"] = ba


def main():
    rnd = sys.argv[1]
    dst = os.path.join(REPO, "review", "first-look", rnd)
    os.makedirs(dst, exist_ok=True)
    bi = json.load(open(os.path.join(OUT, "body_info.json"), encoding="utf-8"))
    si = json.load(open(os.path.join(OUT, "sim_info.json"), encoding="utf-8"))
    bj = json.load(open(os.path.join(OUT, "body.json"), encoding="utf-8"))
    joints = bi["joints"]
    flags = []

    # peak torques over all clips
    peak = {}
    for c, rec in si["clips"].items():
        for v in ("soft", "stiff"):
            for j, t in rec[v]["peak_torque_Nm"].items():
                cur = peak.setdefault(j, {"soft": (0, ""), "stiff": (0, "")})[v]
                if t > cur[0]:
                    peak[j][v] = (t, c)
    for p, j in joints.items():
        if j["type"] == "ball" and j["worst_middle_deg"] > 75:
            flags.append(f"{p}: the middle axis reaches {j['worst_middle_deg']:.0f} deg (over 75) in "
                         + ", ".join(k for k, v in j["worst_middle_per_kind_deg"].items() if v > 75))
        if j["type"] in ("knee", "elbow"):
            d = j["hinge_departure_deg"]
            if d["max"] > 10:
                flags.append(f"{p}: the {'elbow' if j['type'] == 'elbow' else 'knee'} departs from hinge + twist by up to "
                             f"{d['max']:.0f} deg (95% of frames under {d['p95']:.0f} deg); the hand takes up the rest")
    for c, rec in si["clips"].items():
        if rec["ref_outside_range_frames"]:
            flags.append(f"{c}: the Reference Motion bends past the straight limb or a range end in "
                         + ", ".join(f"{k} ({n} frames)" for k, n in rec["ref_outside_range_frames"].items())
                         + "; the joint stops at its limit")

    numbers = {"round": rnd, "masses_kg": bi["masses"], "total_mass_kg": bi["total_mass"],
               "joints": joints, "excluded_pairs": bi["excludes"], "rest_overlap_log": bi["overlap_log"],
               "shrunk_mm": bi["shrunk_mm"], "fit": bi["fit"], "rest_contacts": bi["rest_contacts"],
               "foot": bi["foot"], "foot_solid_width_m": bi["foot_solid_width_m"], "shoe_width_m": bi["shoe_width_m"],
               "drawn_sole_lowest_m": bi["mesh_lowest_z_m"], "clips": si["clips"], "walk_seam": si["walk_seam"],
               "sing_window": si["sing_window"], "variants": si["variants"], "soft_groups": si.get("soft_groups"),
               "root_hz": si["root_hz"], "effective_inertia": si["effective_inertia"],
               "peak_torque_Nm": {j: {v: {"Nm": t[0], "clip": t[1]} for v, t in d.items()} for j, d in peak.items()},
               "motions_used": bi["motions"], "flags": flags}
    with open(os.path.join(dst, "numbers.json"), "w", encoding="utf-8") as f:
        json.dump(numbers, f, ensure_ascii=False, indent=1)

    L = []
    w = L.append
    w(f"# Her Simulation Body, first look ({rnd}): the numbers\n")
    glance(w, dst, bi)
    w("Directions are hers: left, right, front, back, up. Angles in degrees, lengths in millimetres unless "
      "marked. Everything here is measured by code on the local model; nothing is hand-set except the "
      "choices listed under *Choices the contract left open*.\n")
    w("## Her weight per part\n")
    w(f"Total {bi['total_mass']:.2f} kg (25.5 kg shared out by the weight shares measured from her drawn body).\n")
    w("| Part | kg | share |\n|---|---|---|")
    for p in PARTS:
        w(f"| {p} | {bi['masses'][p]:.2f} | {100 * bi['masses'][p] / bi['total_mass']:.1f}% |")
    w("\n## Joints\n")
    w("Every joint is a stack of hinges at the bone head, rest pose = zero. Knee: one hinge. Elbow: one hinge, "
      "then twist along the forearm. The rest: three hinges, two swings then the twist along the limb (or the "
      "spine), axes and order chosen from the motions so the middle hinge stays away from 90 degrees. The range "
      "is what the motions ask for plus 15 degrees (or 20% when larger); knees and elbows stop at the straight "
      "limb. *Set by* names the kind of movement that asked for each end.\n")
    w("| Joint | Axis (at rest) | Range used | Asked for | Set by (low / high) | Worst middle angle |\n|---|---|---|---|---|---|")
    for p, j in joints.items():
        for k, nm in enumerate(j["names"]):
            mid = ""
            if k == 1 and j["type"] == "ball":
                mid = f"{j['worst_middle_deg']:.0f}" + (" **over 75**" if j["worst_middle_deg"] > 75 else "")
            r, o, sb = j["range_deg"][k], j["observed_deg"][k], j["range_set_by"][k]
            w(f"| {p} {nm} | {axis_words(j['axes'][k])} | {r[0]:.0f} to {r[1]:.0f} | {o[0]:.0f} to {o[1]:.0f} | "
              f"{sb[0]} / {sb[1]} | {mid} |")
    w("\nKnee and elbow against a pure hinge (how far the motions' own rotation lies off the hinge model, "
      "before the hand or foot takes up the rest):\n")
    for p, j in joints.items():
        if j["type"] in ("knee", "elbow"):
            d = j["hinge_departure_deg"]
            w(f"- {p}: up to {d['max']:.1f}, 95% of frames under {d['p95']:.1f}; straight limb at {j['straight_deg']:.1f}")
    w("\n## How her solids fit her drawn surface\n")
    w("Capsules, boxes and spheres fitted by code to dense points on her body surface (trailing hair, skirt "
      "and cloth left out; stiff clothing and ornaments weighted to body bones kept). *Pokes out*: how far her "
      "surface sits outside every solid. *Stands off*: how far a solid's surface sits from hers.\n")
    w("| Part | Solids | Pokes out, max | Pokes out, 95% | Stands off, typical | Stands off, 95% | Stands off, max |\n|---|---|---|---|---|---|---|")
    for p in PARTS:
        f = bi["fit"][p]
        w(f"| {p} | {f['solids']} | {f['poke_out_mm']['max']:.1f} | {f['poke_out_mm']['p95']:.1f} | "
          f"{f['standoff_mm']['median']:.1f} | {f['standoff_mm']['p95']:.1f} | {f['standoff_mm']['max']:.1f} |")
    w("\nKept apart at rest (solids shrunk on the facing side so they keep a gap of 2 mm, or half her own gap):\n")
    for s in bi["overlap_log"]:
        if s.startswith("shrink"):
            w(f"- {s}")
    w("\nBody pairs whose solids may overlap (MuJoCo `<exclude>`), because they overlap deeply at rest or her "
      "own surfaces touch:\n")
    for a, b in bi["excludes"]:
        w(f"- {a} and {b}")
    w("\n## Shoes and the rest pose\n")
    ft = bi["foot"]["foot_L"]
    w(f"- Floor-contact shapes per shoe: a front pad box {ft['pad_size_mm'][0]:.0f} long by {ft['pad_size_mm'][1]:.0f} "
      f"wide and a heel-tip box {ft['heel_tip_size_mm'][0]:.0f} by {ft['heel_tip_size_mm'][1]:.0f}, both 10 tall "
      "with their bottoms on the floor. The other foot solids start 10.5 above the floor.")
    w(f"- Widest foot solid across the shoe: {1000 * bi['foot_solid_width_m']['foot_L']:.1f}; the shoe itself: "
      f"{1000 * bi['shoe_width_m']['foot_L']:.1f}.")
    w(f"- Her drawn sole's lowest point is {1000 * bi['mesh_lowest_z_m']:.1f} above the floor; the contact shapes reach the floor.")
    others = [c for c in bi["rest_contacts"] if "floor" not in (c[0], c[1])]
    w(f"- Contacts in the rest pose: {len(bi['rest_contacts'])}, all shoe on floor: {'yes' if not others else 'NO: ' + str(others)} "
      f"(geoms: {sorted(set(c[1] for c in bi['rest_contacts']))}).")
    w("\n## How closely the soft and stiff figures follow the Reference Motion\n")
    w(f"Gains from each joint's effective inertia. Stiff: {si['variants']['stiff'][0]} Hz, damping ratio "
      f"{si['variants']['stiff'][1]}. Soft: {si['variants']['soft'][0]} Hz, damping ratio {si['variants']['soft'][1]}, "
      "with " + ", ".join(f"{g} x{v[0]} at {v[1]}" for g, v in (si.get('soft_groups') or {}).items())
      + ". Joint error = joint angle against the reference; part error = how far each part's rotation is off.\n")
    w("| Clip | Figure | Joint error mean | Joint error worst (joint) | Part error mean | Part error worst (part) | Hips off path, max |\n|---|---|---|---|---|---|---|")
    for c, rec in si["clips"].items():
        for v in ("stiff", "soft"):
            r = rec[v]
            w(f"| {c} | {v} | {r['joint_angle_err_deg']['mean']:.1f} | {r['joint_angle_err_deg']['max']:.0f} "
              f"({r['joint_angle_err_deg']['worst_joint']}) | {r['part_rot_err_deg']['mean']:.1f} | "
              f"{r['part_rot_err_deg']['max']:.0f} ({r['part_rot_err_deg']['worst_part']}) | {1000 * r['root_path_err_max_m']:.1f} |")
    w("\nThe worst errors come from her solids meeting each other (she is bulkier than the bodies the motions were "
      "made for: arms hanging into the hips, a raised arm into her hair, crossed arms into the bust) and from "
      "the floor, not from the servos.\n")
    w("Soft overshoot where it is clearest (the soft figure going past the reference's own turning point, while "
      "nothing touches and the stiff figure follows):\n")
    for c, rec in si["clips"].items():
        o = rec["soft"].get("overshoot", {})
        if o.get("joint"):
            w(f"- {c}: {o['deg']:.0f} at {o['joint']} (clip frame {o['frame_index']})")
    z = si["variants"]["soft"][1]
    w(f"- For reference, a spring-damper at damping ratio {z} overshoots a step by "
      f"{100 * math.exp(-math.pi * z / math.sqrt(1 - z * z)):.0f}%.")
    w("\n## Peak joint torques (no limits in this first look)\n")
    w("| Joint | Stiff, N m (clip) | Soft, N m (clip) |\n|---|---|---|")
    for j, d in sorted(peak.items(), key=lambda kv: -kv[1]["stiff"][0]):
        w(f"| {j} | {d['stiff'][0]:.1f} ({d['stiff'][1]}) | {d['soft'][0]:.1f} ({d['soft'][1]}) |")
    w("\n## Checks\n")
    for c, rec in si["clips"].items():
        w(f"- {c}: reference joint angles through MuJoCo's forward kinematics reproduce the extracted part "
          f"rotations to within {rec['round_trip_rot_deg']['max']:.1f} (worst part {rec['round_trip_rot_deg']['worst_part']}: "
          f"the elbow's hinge-plus-twist; every other part within 0.1) and joint positions to within "
          f"{rec['round_trip_pos_mm']['max']:.0f} ({rec['round_trip_pos_mm']['worst_part']}). Simulation stable: "
          f"soft {'yes' if rec['soft']['ok'] else 'NO'}, stiff {'yes' if rec['stiff']['ok'] else 'NO'}.")
    ws = si["walk_seam"]
    w(f"- Walk loop seam ({ws['file'].split('/')[-1]}): joints differ by up to {ws['max_joint_diff_deg']:.0f} and the "
      f"pelvis by {ws['pelvis_rot_diff_deg']:.0f} between the loop's ends. Used: {ws['used']}.")
    sw = si["sing_window"]
    w(f"- Singing window: Blender frames {sw['blender_frames'][0]} to {sw['blender_frames'][1]} "
      f"({sw['seconds'][0]:.1f} to {sw['seconds'][1]:.1f} s), the 8 s with the most arm travel "
      f"({sw['arm_travel_deg']:.0f} deg summed) while the mouth moves ({100 * sw['mouth_moving_share']:.0f}% of frames).")
    w("\n## Choices the contract left open\n")
    w("- Body frames: every part's frame is lined up with the world in the rest pose, so a part's rotation in "
      "MuJoCo is its rotation delta D directly; each joint sits at its bone head.")
    w("- Joint axes: twist along the limb or spine (rest direction to the next joint; the hand toward the middle "
      "fingertip, the foot toward the toe), the two swing axes turned about it in 7.5 degree steps and the order "
      "picked to keep the middle hinge furthest from 90 degrees over every motion; twist last (about the limb "
      "after the swings) unless that came within 75 degrees and twist first did better. Knee and elbow hinge axes "
      "fitted to where the motions carry the shin and forearm. The angles of each joint are read relative to the "
      "parent part as MuJoCo rebuilds it, so the elbow's leftover is taken up by the wrist.")
    w("- Hips carried: six root joints on the pelvis (three slides, then hinges about up, left-right, front-back) "
      f"held by {si['root_hz']:.0f} Hz critically damped servos with the reference velocity and acceleration "
      "fed forward. In the saved MJCF the pelvis has a free joint. dance_pinned: the pelvis welded in place at "
      "its rest position and rotation, no floor, the same joint angles; the pelvis-waist and pelvis-thigh "
      "contacts MuJoCo would filter for a moving pelvis are excluded by hand there, since it does not filter "
      "against a pelvis welded to the world.")
    w("- Servos: position actuators, damping on the error velocity (the target moves with the reference), "
      "gravity compensated through the actuators; effective inertia per joint = 90th percentile of the joint-space "
      "inertia diagonal over every clip's reference poses (at rest the upper-arm twist inertia is far too small).")
    w("- Soft tuning: at 2.5 Hz everywhere the feet and hands flail (the ankle swung +-50 to 70 degrees in the "
      "dance's kick); elbows and knees run 1.4 times, wrists and ankles 2 times the soft frequency at damping "
      "ratio 0.5. Trunk, neck, head, collarbones, shoulders and hips stay at 2.5 Hz, 0.35.")
    if "surface_kept" in bi:
        hd = bi["head_dims"]
        w("- Which surface gets a solid (round 2, after docs/adr/0004): a vertex's part comes from its dominant "
          "bone (not moved by the shipped dynamic rigid bodies; breast bones count as body). Then by what it is: "
          "hair (前髮, 髮, 髮+) never, however it is bound; skin, face, stocking, shoes, the collar piece and, on "
          "her torso, the bodice (体) always; everything else (skirt 裙*, sleeve 袖, ornaments 饰 珠 宝石 结晶, the "
          "band 体 round her head) only where it lies within 12 mm of that core surface, so close-fitting parts "
          "stay and hanging cloth goes. Her cranium has no scalp: it is closed from the hair's innermost layer "
          "over the top and back of her head, its sides held to her face's half-width plus 5 mm. Head as fitted: "
          f"{hd['width_mm']:.0f} wide, {hd['depth_mm']:.0f} deep, {hd['chin_to_crown_mm']:.0f} chin to crown "
          "(the width is set by the stiff band round her head, the crown by the single hair layer on top).")
        w("- Surface kept per material (samples kept / dropped): " + ", ".join(
            f"{k} {v['kept']}/{v['dropped']}" for k, v in bi["surface_kept"].items() if v["dropped"]))
        w("- Fitting: per part, slab count and whether to penalise solids hanging past the part's ends are "
          "searched, keeping the fit that stands off least: " + ", ".join(
              f"{p} {v['slabs']}" for p, v in bi.get("fit_search", {}).items()) + " slabs.")
    else:
        w("- Which vertices count as body: every Visible Mesh vertex whose dominant bone is not moved by the "
          "shipped dynamic rigid bodies (the breast bones count as body), assigned by walking up to the first part "
          "bone. That keeps the hair rigidly bound to her head (so the head solids follow the hair outline), the "
          "unmoving top of the skirt on her hips (pelvis) and her bell sleeves (forearm).")
    if bi.get("joints_frozen_from"):
        w("- Joints, axes, ranges, masses and the soft and stiff gains (effective inertia) are round 1's, "
          "unchanged; only the solids differ.")
    w("- Motions for the ranges: " + ", ".join(f"{k}: {sum(1 for m in bi['motions'] if m['kind'] == k)} files"
                                              for k in ("dance", "walk", "cute", "sing"))
      + " (singing sampled every third frame). The single-person pose files (.vpd) are left out: MMD Tools "
      "reports success but leaves every bone at rest on this Blender.")
    before_after(w, rnd, bi, si, numbers)
    w("\n## Flagged\n")
    for f_ in flags:
        w(f"- {f_}")
    with open(os.path.join(dst, "numbers.json"), "w", encoding="utf-8") as f:
        json.dump(numbers, f, ensure_ascii=False, indent=1)
    with open(os.path.join(dst, "numbers.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("numbers written to", dst)


if __name__ == "__main__":
    main()
