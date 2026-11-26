"""PROTOTYPE, throwaway. Region colour measurement for the toon-look prototype.

Compares her renders with frames of the colour reference by region, not by pixel position:
reference pixels come from hand-picked rectangles on each reference frame, render pixels from the
material-ID pass (teal panels: dress and sleeve materials); inside both, the same colour classifier and the same brightness split pick the
region. Colours are compared as mean CIELAB (D65) and Delta E*ab (CIE76).

  python3 measure.py <reference_dir> <round_dir> [--debug]   -> writes <round_dir>/table.json
"""
import json
import os
import sys

import numpy as np
from PIL import Image

# Reference rectangles (x0, y0, x1, y1) on the 360x640 reference frames, picked by looking at them.
# ref1 0.8 s, ref2 2.4 s (eyes closed), ref3 4.0 s, ref4 5.6 s (eyes closed), ref5 7.2 s, ref6 8.8 s.
RECTS = {
    "skin": {"ref1": [(95, 300, 265, 420), (140, 220, 225, 285)], "ref2": [(20, 330, 170, 470), (150, 250, 260, 330), (240, 330, 340, 470)],
             "ref3": [(95, 300, 265, 420), (160, 230, 230, 285)], "ref4": [(40, 330, 140, 470), (80, 250, 250, 340), (260, 330, 340, 470)],
             "ref5": [(40, 320, 140, 470), (130, 250, 280, 330), (240, 320, 340, 470)], "ref6": [(100, 290, 260, 410), (160, 230, 240, 290)]},
    "hair": {k: [(20, 20, 340, 300)] for k in ("ref1", "ref2", "ref3", "ref4", "ref5", "ref6")},
    "dress": {"ref1": [(40, 420, 320, 630)], "ref2": [(40, 520, 340, 635)], "ref3": [(40, 420, 320, 630)],
              "ref4": [(40, 520, 340, 635)], "ref5": [(40, 530, 340, 635)], "ref6": [(30, 410, 330, 630)]},
    "sleeve": {"ref1": [(0, 300, 70, 430), (290, 300, 360, 430)], "ref3": [(0, 280, 60, 420), (300, 280, 360, 400)],
               "ref6": [(0, 300, 90, 420), (290, 300, 360, 420)], "ref2": [(320, 380, 360, 520)], "ref4": [(0, 380, 50, 500), (320, 380, 360, 500)]},
    "iris": {"ref1": [(222, 200, 252, 232)], "ref3": [(205, 200, 235, 232)], "ref5": [(222, 215, 262, 255)], "ref6": [(225, 200, 255, 235)]},
    "bg": {"ref1": [(0, 0, 50, 70)], "ref3": [(0, 0, 50, 60)], "ref6": [(0, 0, 40, 200), (330, 220, 360, 300)],
           "ref2": [(0, 0, 30, 40)]},
}
ID_COLORS = {"skin": (255, 0, 0), "hair": (0, 0, 255), "dress": (0, 255, 0), "sleeve": (255, 255, 0),
             "iris": (255, 0, 255), "bg": (0, 0, 0)}
# Region = (group, low brightness percentile, high brightness percentile) within the classified pixels.
REGIONS = [
    ("skin lit", "skin", 50, 100), ("skin shadow", "skin", 0, 15),
    ("hair highlight", "hair", 92, 100), ("hair mid", "hair", 40, 60), ("hair shadow", "hair", 0, 15),
    ("dress lit", "dress", 50, 100), ("dress shadow", "dress", 0, 15),
    ("teal panels", "sleeve", 0, 100), ("iris", "iris", 25, 75), ("background", "bg", 0, 100),
]


def srgb_to_lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def lab_to_srgb(lab):
    L, a, b = lab
    fy = (L + 16) / 116
    f = np.array([fy + a / 500, fy, fy - b / 200])
    xyz = np.where(f > 0.2069, f ** 3, (f - 16 / 116) / 7.787) * np.array([0.95047, 1.0, 1.08883])
    Mi = np.array([[3.2406, -1.5372, -0.4986], [-0.9689, 1.8758, 0.0415], [0.0557, -0.2040, 1.0570]])
    c = np.clip(Mi @ xyz, 0, 1)
    c = np.where(c > 0.0031308, 1.055 * c ** (1 / 2.4) - 0.055, 12.92 * c)
    return [int(round(x * 255)) for x in c]


def classify(group, rgb, lab):
    """Same pixel classifier for reference and render: keeps the pixels that belong to the region."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(-1), rgb.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1)
    L, A, B = lab[..., 0], lab[..., 1], lab[..., 2]
    hue = (np.degrees(np.arctan2(B, A)) + 360) % 360
    if group == "skin":
        return (r >= g) & (g >= b - 6) & (r - b >= 3) & (L > 55) & (sat < 0.45)
    if group == "hair":
        return (b > r + 25) & (sat > 0.25) & (L > 15) & ((hue > 200) & (hue < 300))
    if group == "dress":
        return (sat < 0.16) & (L > 55)
    if group == "sleeve":
        return (b >= r) & (L < 60) & (L > 8) & (sat > 0.25)
    if group == "iris":
        return (L > 25) & (b >= r)
    return np.ones(r.shape, bool)


def region_stats(pix_by_group):
    out = {}
    for name, grp, lo, hi in REGIONS:
        lab = pix_by_group.get(grp)
        if lab is None or len(lab) < 20:
            out[name] = None
            continue
        L = lab[:, 0]
        a, b = np.percentile(L, lo), np.percentile(L, hi)
        sel = lab[(L >= a) & (L <= b)]
        out[name] = {"lab": [round(float(x), 1) for x in sel.mean(0)], "n": int(len(sel))}
        out[name]["rgb"] = lab_to_srgb(sel.mean(0))
    return out


def load(path):
    return np.asarray(Image.open(path).convert("RGB")).astype(np.float64)


def reference_pixels(ref_dir):
    pix = {}
    for grp, per in RECTS.items():
        acc = []
        for ref, rects in per.items():
            rgb = load(os.path.join(ref_dir, ref + ".png"))
            lab = srgb_to_lab(rgb)
            m = np.zeros(rgb.shape[:2], bool)
            for x0, y0, x1, y1 in rects:
                m[y0:y1, x0:x1] = True
            m &= classify(grp, rgb, lab)
            acc.append(lab[m])
        pix[grp] = np.concatenate(acc)
    return pix


def erode(m, n=2):
    for _ in range(n):
        e = m.copy()
        e[1:, :] &= m[:-1, :]
        e[:-1, :] &= m[1:, :]
        e[:, 1:] &= m[:, :-1]
        e[:, :-1] &= m[:, 1:]
        m = e
    return m


def render_pixels(round_dir, debug=False):
    acc = {g: [] for g in ID_COLORS}
    for f in sorted(os.listdir(round_dir)):
        if not (f.startswith("close") and f.endswith("_id.png")):
            continue
        rgb = load(os.path.join(round_dir, f.replace("_id", "")))
        idp = load(os.path.join(round_dir, f))
        lab = srgb_to_lab(rgb)
        dbg = np.full_like(rgb, 0)
        for grp, col in ID_COLORS.items():
            m = np.all(np.abs(idp - np.array(col)) < 40, -1)
            if grp == "sleeve":  # the dark teal panels sit on several dress and sleeve materials
                m |= np.all(np.abs(idp - np.array(ID_COLORS["dress"])) < 40, -1)
            m = erode(m, 3 if grp != "iris" else 1)
            # The ID pass already says which material a pixel is; dress (white vs ornament), teal and iris need the colour
            # classifier here. The others just drop outline and edge pixels, so clipped whites still count.
            m &= classify(grp, rgb, lab) if grp in ("sleeve", "iris", "dress") else (lab[..., 0] > 30)
            acc[grp].append(lab[m])
            dbg[m] = rgb[m]
        if debug:
            Image.fromarray(dbg.astype(np.uint8)).save(os.path.join(round_dir, "debug_" + f))
    return {g: np.concatenate(v) for g, v in acc.items() if v}


def table(ref, ren):
    rows = []
    for name, *_ in REGIONS:
        r, y = ref.get(name), ren.get(name)
        de = None
        if r and y:
            de = round(float(np.linalg.norm(np.array(r["lab"]) - np.array(y["lab"]))), 1)
        rows.append({"region": name, "ref": r, "render": y, "dE": de})
    des = [x["dE"] for x in rows if x["dE"] is not None]
    return {"rows": rows, "mean_dE": round(float(np.mean(des)), 1), "worst_dE": max(des),
            "worst_region": max((x for x in rows if x["dE"] is not None), key=lambda x: x["dE"])["region"]}


# Style checks against the gosari style sheet (survey of ten other videos, see survey.py). Ranges are the spread
# measured on the bright close-up survey frames plus the six reference frames; (lo, hi).
STYLE_TARGETS = {
    "L_mean": (72, 84), "clip_white_pct": (0.4, 5.0), "L95plus_pct": (14, 32),
    "skin_lit_L": (96, 99), "skin_lit_C": (2.5, 5.0),
    "skin_shadow_dL": (-20, -10), "skin_shadow_dC": (2, 10.5), "skin_shadow_hue": (10, 25),
    "skin_mid_share": (0, 0.12), "edge_centre_over_border": (0.6, 2.9),
}


def lch(lab):
    return float(lab[0]), float(np.hypot(lab[1], lab[2])), float((np.degrees(np.arctan2(lab[2], lab[1])) + 360) % 360)


def style(round_dir):
    acc = {"L": [], "clip": [], "L95": [], "edge": [], "skin": []}
    for f in sorted(os.listdir(round_dir)):
        if not (f.startswith("close") and f.endswith("_id.png")):
            continue
        rgb = load(os.path.join(round_dir, f.replace("_id", "")))
        idp = load(os.path.join(round_dir, f))
        lab = srgb_to_lab(rgb)
        L = lab[..., 0]
        acc["L"].append(L.mean())
        acc["clip"].append(np.mean(rgb.min(-1) >= 250) * 100)
        acc["L95"].append(np.mean(L >= 95) * 100)
        g = np.abs(np.diff(L, axis=1))[:-1, :] + np.abs(np.diff(L, axis=0))[:, :-1]
        w = g.shape[1]
        acc["edge"].append(g[:, w // 3: 2 * w // 3].mean() / max(np.concatenate([g[:, :w // 8], g[:, -w // 8:]], 1).mean(), 1e-6))
        m = erode(np.all(np.abs(idp - np.array(ID_COLORS["skin"])) < 40, -1), 3) & (L > 30)
        acc["skin"].append(lab[m])
    sk = np.concatenate(acc["skin"])
    Ls = sk[:, 0]
    lit, sh = sk[Ls >= np.percentile(Ls, 50)].mean(0), sk[Ls <= np.percentile(Ls, 15)].mean(0)
    (l1, c1, h1), (l0, c0, h0) = lch(lit), lch(sh)
    mid = np.mean((Ls > l0 + 0.3 * (l1 - l0)) & (Ls < l0 + 0.7 * (l1 - l0)))
    vals = {"L_mean": np.mean(acc["L"]), "clip_white_pct": np.mean(acc["clip"]), "L95plus_pct": np.mean(acc["L95"]),
            "skin_lit_L": l1, "skin_lit_C": c1, "skin_shadow_dL": l0 - l1, "skin_shadow_dC": c0 - c1,
            "skin_shadow_hue": h0, "skin_mid_share": mid, "edge_centre_over_border": np.mean(acc["edge"])}
    rows = []
    for k, (lo, hi) in STYLE_TARGETS.items():
        v = round(float(vals[k]), 2)
        rows.append({"check": k, "value": v, "target": [lo, hi], "ok": bool(lo <= v <= hi)})
    return {"rows": rows, "passed": sum(r["ok"] for r in rows), "of": len(rows)}


def main():
    ref_dir, round_dir = sys.argv[1], sys.argv[2]
    debug = "--debug" in sys.argv
    ref = region_stats(reference_pixels(ref_dir))
    ren = region_stats(render_pixels(round_dir, debug))
    t = table(ref, ren)
    t["style"] = style(round_dir)
    with open(os.path.join(round_dir, "table.json"), "w", encoding="utf-8") as f:
        json.dump(t, f, ensure_ascii=False, indent=1)
    print(f"{'region':16} {'reference':>16} {'render':>16}  dE   (L a b)")
    for row in t["rows"]:
        r, y = row["ref"], row["render"]
        print(f"{row['region']:16} {str(r and r['rgb']):>16} {str(y and y['rgb']):>16} {row['dE']!s:>5}  "
              f"{r and r['lab']} {y and y['lab']}")
    print(f"mean dE {t['mean_dE']}  worst {t['worst_dE']} ({t['worst_region']})")
    print("style:", ", ".join(f"{r['check']}={r['value']}{'' if r['ok'] else ' (off ' + str(r['target']) + ')'}"
                              for r in t["style"]["rows"]), f"-> {t['style']['passed']}/{t['style']['of']}")


if __name__ == "__main__":
    main()
