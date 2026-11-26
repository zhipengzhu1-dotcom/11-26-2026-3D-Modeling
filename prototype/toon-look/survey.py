"""PROTOTYPE, throwaway. Survey of ten other gosari videos (style reference, used privately).

  python3 survey.py <run_dir>     -> crops <run_dir>/survey/raw/*.jpg into <run_dir>/survey/<id>/f*.png
                                     and writes <run_dir>/survey/measure.json

The raw files are browser screenshots of canvases drawn from the paused video (see the run's
style-sheet.md): landscape videos as a 2x2 grid of 600x337 CSS px, Shorts as four 300x533 frames in a row.
Nothing here is fetched; the frames are someone else's video and never leave the git-ignored review/ folder.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from measure import srgb_to_lab  # noqa: E402

VIDEOS = {}  # filled from <run_dir>/survey/videos.json (title, URL, date, model, framing, credits; kept git-ignored)

# Hand-picked rectangles (x0, y0, x1, y1) on the cropped frames, for skin and hair on frames
# where the face is large enough. Picked by looking at the frames.
RECTS = {
    "YFBv2HfZTPM/f1": {"skin": [(355, 75, 400, 125)]},
    "SJRM1_RFLKQ/f1": {"skin": [(110, 120, 190, 175)], "hair:dark": [(65, 50, 110, 170), (195, 45, 240, 160)]},
    "SJRM1_RFLKQ/f2": {"skin": [(130, 100, 200, 160)], "hair:dark": [(85, 45, 130, 160), (200, 45, 250, 150)]},
    "SJRM1_RFLKQ/f4": {"skin": [(110, 100, 190, 170)], "hair:dark": [(60, 40, 110, 160), (190, 40, 240, 170)]},
    "0754iJisbyk/f3": {"skin": [(90, 150, 220, 250)]},
    "0754iJisbyk/f2": {"skin": [(60, 160, 200, 260)]},
    "NXEk7h71k4Q/f3": {"skin": [(100, 170, 190, 250)], "hair:light": [(60, 0, 240, 120)]},
    "NXEk7h71k4Q/f4": {"skin": [(100, 180, 200, 250)], "hair:light": [(60, 0, 240, 130)]},
    "UXWnGffJx0g/f1": {"skin": [(60, 150, 200, 240)], "hair:tinted": [(40, 20, 280, 120)]},
}


def crop_all(run):
    raw = os.path.join(run, "survey", "raw")
    frames = {}
    for f in sorted(os.listdir(raw)):
        if not f.endswith(".jpg"):
            continue
        vid, part = f[:-4].rsplit("_", 1)
        im = Image.open(os.path.join(raw, f)).convert("RGB")
        land = VIDEOS[vid]["orientation"] == "landscape"
        boxes = ([(0, 0, 600, 337), (600, 0, 1200, 337), (0, 337, 600, 674), (600, 337, 1200, 674)] if land
                 else [(i * 300, 0, i * 300 + 300, 533) for i in range(4)])
        d = os.path.join(run, "survey", vid)
        os.makedirs(d, exist_ok=True)
        n = len([x for x in frames if x.startswith(vid + "/")])
        for b in boxes:
            c = im.crop(b)
            a = np.asarray(c)
            if a.mean() < 3:  # empty slot (a seek that never finished)
                continue
            n += 1
            name = f"{vid}/f{n}"
            c.save(os.path.join(run, "survey", name + ".png"))
            frames[name] = os.path.join(run, "survey", name + ".png")
    return frames


def grad_energy(L):
    gx = np.abs(np.diff(L, axis=1))[:-1, :]
    gy = np.abs(np.diff(L, axis=0))[:, :-1]
    return gx + gy


def frame_stats(path):
    rgb = np.asarray(Image.open(path).convert("RGB")).astype(np.float64)
    lab = srgb_to_lab(rgb)
    L, A, B = lab[..., 0], lab[..., 1], lab[..., 2]
    C = np.hypot(A, B)
    h, w = L.shape
    clip = float(np.mean(rgb.min(-1) >= 250) * 100)
    near = float(np.mean(L >= 95) * 100)
    g = grad_energy(L)
    # centre third (the character, roughly) vs the outer columns (mostly stage); a crude depth-of-field cue
    cx = g[:, w // 3: 2 * w // 3].mean()
    bx = np.concatenate([g[:, : w // 8], g[:, -w // 8:]], 1).mean()
    return {"L_mean": round(float(L.mean()), 1), "L_p95": round(float(np.percentile(L, 95)), 1),
            "chroma_mean": round(float(C.mean()), 1), "clip_white_pct": round(clip, 2), "L95plus_pct": round(near, 1),
            "a_mean": round(float(A.mean()), 1), "b_mean": round(float(B.mean()), 1),
            "edge_centre_over_border": round(float(cx / max(bx, 1e-6)), 2)}


def lch(lab):
    L, a, b = lab
    return float(L), float(np.hypot(a, b)), float((np.degrees(np.arctan2(b, a)) + 360) % 360)


def shade_stats(path, rects, group):
    rgb = np.asarray(Image.open(path).convert("RGB")).astype(np.float64)
    lab = srgb_to_lab(rgb)
    m = np.zeros(rgb.shape[:2], bool)
    for x0, y0, x1, y1 in rects:
        m[y0:y1, x0:x1] = True
    if group == "skin":
        r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        m &= (r >= g) & (g >= b - 6) & (r - b >= 3) & (lab[..., 0] > 45)
    elif group == "hair:dark":
        m &= (lab[..., 0] > 5) & (lab[..., 0] < 62)
    elif group == "hair:tinted":
        m &= (lab[..., 0] > 12) & (np.hypot(lab[..., 1], lab[..., 2]) > 8)
    else:
        m &= lab[..., 0] > 12
    px = lab[m]
    if len(px) < 40:
        return None
    Ls = px[:, 0]
    lit = px[Ls >= np.percentile(Ls, 50)].mean(0)
    sh = px[Ls <= np.percentile(Ls, 15)].mean(0)
    l1, c1, h1 = lch(lit)
    l0, c0, h0 = lch(sh)
    dh = (h0 - h1 + 180) % 360 - 180
    return {"lit_LCh": [round(l1, 1), round(c1, 1), round(h1)], "shadow_LCh": [round(l0, 1), round(c0, 1), round(h0)],
            "dL": round(l0 - l1, 1), "dC": round(c0 - c1, 1), "dHue": round(dh), "n": int(len(px)),
            # how gradual is the transition: share of pixels in the middle 40 % of the lit-shadow L range
            "mid_share": round(float(np.mean((Ls > l0 + 0.3 * (l1 - l0)) & (Ls < l0 + 0.7 * (l1 - l0)))), 2)}


def main():
    run = sys.argv[1]
    with open(os.path.join(run, "survey", "videos.json"), encoding="utf-8") as f:
        VIDEOS.update(json.load(f))
    frames = crop_all(run)
    out = {"frames": {}, "shading": {}}
    for name, p in frames.items():
        out["frames"][name] = frame_stats(p)
    for name, rr in RECTS.items():
        p = os.path.join(run, "survey", name + ".png")
        if os.path.exists(p):
            out["shading"][name] = {g: shade_stats(p, r, g) for g, r in rr.items()}
    # the original reference frames of 6Cf1tnG-wVA, for comparison
    ref = os.path.join(os.path.dirname(run), "20261126-gosari", "reference")
    for i in range(1, 7):
        p = os.path.join(ref, f"ref{i}.png")
        if os.path.exists(p):
            out["frames"][f"6Cf1tnG-wVA/ref{i}"] = frame_stats(p)
    with open(os.path.join(run, "survey", "measure.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=0)[:6000])


if __name__ == "__main__":
    main()
