"""PROTOTYPE (throwaway). The motion sets behind the joint ranges, and the batch lists for extract.py.

  python motions.py <out_dir> <n_batches>   -> <out_dir>/batch_<i>.json and <out_dir>/motions.json
"""
import glob
import json
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
M = os.path.join(REPO, "assets", "motion")

# (kind, glob relative to assets/motion). Clip sources are among these, so each VMD is evaluated once.
SETS = [
    ("dance", "toki-yo-tomare/時よ止まれ.vmd"),
    ("walk", "walk-mutsugorou-idou-v1.3/unpacked/*/1.歩く(女)/*.vmd"),
    ("walk", "walk-fuyuneko-aruku/unpacked/歩く/歩く.vmd"),
    ("walk", "walk-hophead-kidotta-hokou/unpacked/walking.vmd"),
    ("cute", "cute-gray-turn-heart/unpacked/*/*.vmd"),
    ("cute", "cute-gray-peace/unpacked/*/*.vmd"),
    ("cute", "cute-gray-curtsey/unpacked/*/カーツィ_*.vmd"),  # the curtseys (not the men's scrapes)
    ("cute", "cute-herushana-wave/unpacked/*/*.vmd"),
    ("cute", "cute-herushana-bow/unpacked/*/[0-9]*.vmd"),
    ("cute", "kei-redreaming-angel/unpacked/*/Chinatsu idle animation/chinatsu_idle_animation_chinatsu.vmd"),
    # The single-person pose files (.vpd) are left out: MMD Tools import_vpd reports FINISHED on this
    # Blender 5.2 but leaves every bone at rest (tried with and without pose mode).
    ("sing", "sing-i7-ave-maria/unpacked/*/*.vmd"),
]


def motions():
    out = []
    for kind, g in SETS:
        for p in sorted(glob.glob(os.path.join(M, g))):
            out.append({"key": f"{kind}_{len(out):03d}", "kind": kind, "path": p,
                        "name": os.path.relpath(p, M)})
    return out


if __name__ == "__main__":
    out_dir, n = sys.argv[1], int(sys.argv[2])
    os.makedirs(out_dir, exist_ok=True)
    ms = motions()
    with open(os.path.join(out_dir, "motions.json"), "w", encoding="utf-8") as f:
        json.dump(ms, f, ensure_ascii=False, indent=1)
    # long files first, spread round-robin so batches take similar time
    ms_sorted = sorted(ms, key=lambda m: -os.path.getsize(m["path"]))
    for i in range(n):
        with open(os.path.join(out_dir, f"batch_{i}.json"), "w", encoding="utf-8") as f:
            json.dump(ms_sorted[i::n], f, ensure_ascii=False)
    print(len(ms), "motions;", {k: sum(m["kind"] == k for m in ms) for k in ("dance", "walk", "cute", "sing")})
