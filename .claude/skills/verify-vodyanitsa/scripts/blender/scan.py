"""穿模 scan, version 1: measure Overlaps on her Visible Mesh and hand a human the moments worth looking at.

It never declares a pass. Coverage (see KINDS / UNMEASURED below):
  kind 2  trailing parts (hair, skirt, other Secondary Physics parts) inside her body surface   MEASURED
  kind 3  forearm+hand inside the body without that arm; shank+foot inside the body without that leg  MEASURED
  kind 5  anything below the floor (z = 0)                                                        MEASURED
  kind 1  body through clothing                                                                   NOT MEASURED
  kind 4  one trailing family through another (hair through skirt)                                NOT MEASURED
  Overlaps between collision shapes of a Simulation Body                                          NOT MEASURED

Usage (via the CLI): Blender -b --python scan.py -- <build.json> <out_dir> <config.json>
"""
import json
import math
import os
import sys
import time
from collections import Counter, defaultdict

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.dont_write_bytecode = True  # keep __pycache__ out of the tracked skill folder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

KINDS = {
    2: "trailing part through body",
    3: "body through body (forearm/hand or shank/foot)",
    5: "through the floor",
}
UNMEASURED = [
    "kind 1, body through clothing (skin poking through her dress or sleeves): not measured in version 1",
    "kind 4, one trailing family through another (hair through skirt, ribbon through hair): not measured in version 1",
    "Overlaps between the collision shapes of a Simulation Body: not measured (the stand-in has none)",
    "upper arm into torso and thigh into thigh/torso: not measured (only forearm+hand and shank+foot are tested in kind 3)",
    "parts outside the solid body surface (ornaments, beads, gems, eyes, face overlays, microphone) are never the "
    "surface something passes through; they can only be the part that passes",
]

# Body regions, found by walking a bone's ancestors to the first anchor (MMD names, .L/.R after MMD Tools).
ANCHORS = {"頭": "head", "首": "head"}
for s in ("L", "R"):
    ANCHORS.update({
        f"ひじ.{s}": f"forearm_hand.{s}", f"腕.{s}": f"upper_arm.{s}", f"腕補助.{s}": f"upper_arm.{s}",
        f"ひざ.{s}": f"shank_foot.{s}", f"ひざD.{s}": f"shank_foot.{s}",
        f"足.{s}": f"thigh.{s}", f"足D.{s}": f"thigh.{s}", f"ひざ補助.{s}": f"thigh.{s}",
    })
# Materials that make the solid body surface other parts can pass through.
SOLID = {"颜", "肌", "体", "足", "鞋", "袖"}
# Kind 3 queries: part -> regions removed from the surface it is tested against.
KIND3 = {
    "forearm_hand.L": ("upper_arm.L", "forearm_hand.L"), "forearm_hand.R": ("upper_arm.R", "forearm_hand.R"),
    "shank_foot.L": ("thigh.L", "shank_foot.L"), "shank_foot.R": ("thigh.R", "shank_foot.R"),
}
MAX_DEPTH_SEARCH = 0.30  # m; nothing in her is thicker than this from the nearest surface point
VIS_TOL = 0.03  # m; a crossing counts as seen if the camera ray first hits her within this of it
VIS_TESTS = 40  # deepest candidates per part pair per frame that get a camera ray


def family_of(mat):
    if "髮" in mat or "髪" in mat:
        return "hair"
    if "裙" in mat:
        return "skirt"
    return "other"


def classify(mesh, arm, trailing_bones):
    bones = arm.data.bones
    trailing = {b for b in trailing_bones if not b.startswith("胸")}  # chest bones count as body

    def walk(name):
        is_trailing = False
        n = bones.get(name)
        while n is not None:
            if n.name in ANCHORS:
                return is_trailing, ANCHORS[n.name]
            if n.name in trailing:
                is_trailing = True
            n = n.parent
        return is_trailing, "torso"

    me = mesh.data
    gnames = {g.index: g.name for g in mesh.vertex_groups}
    nv = len(me.vertices)
    dom = [None] * nv
    for v in me.vertices:
        best, w = None, -1.0
        for g in v.groups:
            nm = gnames.get(g.group)
            if nm in bones and g.weight > w:
                best, w = nm, g.weight
        dom[v.index] = best
    cache = {}
    is_tr = np.zeros(nv, bool)
    region = np.empty(nv, object)
    for i, b in enumerate(dom):
        if b not in cache:
            cache[b] = walk(b) if b else (False, "torso")
        is_tr[i], region[i] = cache[b]
    mats = [m.name if m else "" for m in me.materials]
    vmat = np.empty(nv, object)
    vmat[:] = ""
    me.calc_loop_triangles()
    tris = np.zeros((len(me.loop_triangles), 3), np.int64)
    tri_mat = np.empty(len(me.loop_triangles), object)
    for k, lt in enumerate(me.loop_triangles):
        tris[k] = lt.vertices
        tri_mat[k] = mats[lt.material_index]
        for vi in lt.vertices:
            if not vmat[vi]:
                vmat[vi] = mats[lt.material_index]
    fam = np.array([family_of(m) for m in vmat], object)
    return is_tr, region, vmat, fam, tris, tri_mat


class Surfaces:
    """Index sets of triangles for each tested body surface."""

    def __init__(self, is_tr, region, fam, tris, tri_mat):
        solid = np.array([m in SOLID for m in tri_mat]) & ~is_tr[tris].any(1)
        treg = region[tris[:, 0]]
        self.tri_region = treg
        self.sets = {"body": np.nonzero(solid)[0]}
        for part, drop in KIND3.items():
            self.sets[part] = np.nonzero(solid & ~np.isin(treg, drop))[0]
        self.sets["all"] = np.arange(len(tris))
        self.tris = tris
        self.lists = {k: tris[v].tolist() for k, v in self.sets.items()}


def inside_depth(tree, tris_sub, co, vn, q_idx):
    """Depth inside the surface for each query vertex (0 if outside) and the nearest surface point / triangle."""
    n = len(q_idx)
    depth = np.zeros(n)
    near = np.zeros((n, 3))
    tri = np.full(n, -1, np.int64)
    if n == 0:
        return depth, near, tri
    loc = np.zeros((n, 3))
    idx = np.full(n, -1, np.int64)
    for k, vi in enumerate(q_idx):
        r = tree.find_nearest(co[vi], MAX_DEPTH_SEARCH)
        if r[0] is not None:
            loc[k] = r[0]
            idx[k] = r[2]
    hit = idx >= 0
    if not hit.any():
        return depth, near, tri
    h = np.nonzero(hit)[0]
    t = np.asarray(tris_sub)[idx[h]]
    a, b, c = co[t[:, 0]], co[t[:, 1]], co[t[:, 2]]
    p = loc[h]
    # barycentric weights of the nearest point, then the interpolated vertex normal (robust sign near edges)
    v0, v1, v2 = b - a, c - a, p - a
    d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1)
    d20 = (v2 * v0).sum(1); d21 = (v2 * v1).sum(1)
    den = d00 * d11 - d01 * d01
    den[np.abs(den) < 1e-18] = 1e-18
    wv = (d11 * d20 - d01 * d21) / den
    ww = (d00 * d21 - d01 * d20) / den
    wu = 1 - wv - ww
    nrm = vn[t[:, 0]] * wu[:, None] + vn[t[:, 1]] * wv[:, None] + vn[t[:, 2]] * ww[:, None]
    q = co[np.asarray(q_idx)[h]]
    d = q - p
    s = (d * nrm).sum(1)
    dist = np.linalg.norm(d, axis=1)
    cand = np.nonzero((s < 0) & (dist > 1e-4))[0]
    for k in cand:
        # confirm: heading further in, the ray must leave her through the back of a face
        di = d[k] / dist[k]
        r = tree.ray_cast(Vector(q[k] + di * 1e-4), Vector(di), 0.6)
        if r[0] is not None and Vector(r[1]).dot(Vector(di)) > 0:
            depth[h[k]] = dist[k]
    near[h] = p
    tri[h] = idx[h]
    return depth, near, tri


def evaluate(mesh, dg):
    ev = mesh.evaluated_get(dg)
    me = ev.to_mesh()
    n = len(me.vertices)
    co = np.empty(n * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(n, 3)
    vn = np.empty(n * 3)
    me.vertex_normals.foreach_get("vector", vn)
    vn = vn.reshape(n, 3)
    ev.to_mesh_clear()
    mw = np.array(mesh.matrix_world)
    co = co @ mw[:3, :3].T + mw[:3, 3]
    vn = vn @ mw[:3, :3].T
    return co, vn


def measure(mesh, dg, surf, queries):
    """One pose: per query group, (depth, near point, part-pair label per vertex)."""
    co, vn = evaluate(mesh, dg)
    cl = co.tolist()
    trees = {k: BVHTree.FromPolygons(cl, surf.lists[k], all_triangles=True) for k in surf.lists}
    out = {}
    for name, (kind, surface, q_idx) in queries.items():
        if kind == 5:
            depth = np.clip(-co[q_idx, 2], 0, None)
            near = co[q_idx].copy()
            near[:, 2] = 0.0
            out[name] = (depth, near, None)
        else:
            d, p, t = inside_depth(trees[surface], surf.lists[surface], co, vn, q_idx)
            treg = np.where(t >= 0, surf.tri_region[surf.sets[surface][np.maximum(t, 0)]], "")
            out[name] = (d, p, treg)
    return out, trees["all"], co


def main():
    build_json, out_dir, cfg_json = common.args()[:3]
    with open(cfg_json, encoding="utf-8") as f:
        cfg = json.load(f)
    t_setup = time.time()
    build, mesh, arm = common.open_build(build_json)
    scene, cam, floor = common.setup_stage(build, mesh, arm, res_pct=cfg["still_res_pct"], stamp_note=cfg["note"])
    fps = build["fps"]
    f0 = build["frame_start"]
    is_tr, region, vmat, fam, tris, tri_mat = classify(mesh, arm, build["trailing_bones"])
    surf = Surfaces(is_tr, region, fam, tris, tri_mat)
    nv = len(is_tr)
    like_skip = np.isin(fam, ["hair", "skirt"])  # hair/skirt materials never query kind 3 (they are not limbs)
    queries = {
        "k2": (2, "body", np.nonzero(is_tr)[0]),
        "k5": (5, None, np.arange(nv)),
    }
    for part in KIND3:
        queries["k3:" + part] = (3, part, np.nonzero(~is_tr & (region == part) & ~like_skip)[0])
    part_of = np.where(is_tr, fam, region)  # name of the passing part, per vertex

    # Rest-pose baseline: Overlap is depth beyond how she sits in her rest pose.
    dg = bpy.context.evaluated_depsgraph_get()
    arm.data.pose_position = "REST"
    scene.frame_set(f0)
    dg.update()
    base, _, _ = measure(mesh, dg, surf, queries)
    arm.data.pose_position = "POSE"
    dg.update()
    setup_s = time.time() - t_setup

    frames = list(range(cfg["start"], cfg["end"] + 1, cfg["step"]))
    noise = cfg["noise_mm"] / 1000.0
    per_frame = []  # (frame, {pair: record})
    t_scan = time.time()
    for fi, f in enumerate(frames):
        scene.frame_set(f)
        res, tree_all, co = measure(mesh, dg, surf, queries)
        camloc = cam.matrix_world.translation.copy()
        recs = {}
        for name, (kind, surface, q_idx) in queries.items():
            d, p, treg = res[name]
            ov = d - base[name][0]
            hits = np.nonzero(ov > noise)[0]
            if len(hits) == 0:
                continue
            groups = defaultdict(list)
            for k in hits:
                vi = q_idx[k]
                other = "floor" if kind == 5 else treg[k]
                groups[(kind, part_of[vi], other)].append(k)
            for pair, ks in groups.items():
                ks = sorted(ks, key=lambda k: -ov[k])
                vis_depth, vis_pt = 0.0, None
                for k in ks[:VIS_TESTS]:
                    pt = Vector(p[k])
                    v = world_to_camera_view(scene, cam, pt)
                    if not (0 <= v.x <= 1 and 0 <= v.y <= 1 and v.z > 0):
                        continue
                    dvec = pt - camloc
                    L = dvec.length
                    r = tree_all.ray_cast(camloc, dvec.normalized(), L + 1.0)
                    if r[0] is None or r[3] >= L - VIS_TOL:
                        vis_depth, vis_pt = float(ov[k]), (v.x, v.y)
                        break
                recs[pair] = {"max_mm": float(ov[ks[0]]) * 1000, "n": len(ks),
                              "vis_mm": vis_depth * 1000, "vis_xy": vis_pt}
        per_frame.append((f, recs))
        if fi % 25 == 0:
            el = time.time() - t_scan
            print(f"SCAN frame {f} ({fi + 1}/{len(frames)}) {el / (fi + 1):.2f} s/frame, pairs {len(recs)}", flush=True)
    scan_s = time.time() - t_scan

    # Events: per (kind, part, other) runs of scanned frames where a visible Overlap exceeds the noise floor.
    events = []
    runs = defaultdict(list)
    for f, recs in per_frame:
        for pair, r in recs.items():
            if r["vis_mm"] > cfg["noise_mm"]:
                runs[pair].append((f, r))
    for pair, seq in runs.items():
        cur = []
        for f, r in seq:
            if cur and f - cur[-1][0] > cfg["step"]:
                events.append((pair, cur))
                cur = []
            cur.append((f, r))
        if cur:
            events.append((pair, cur))
    ev_out = []
    for (kind, part, other), seq in events:
        peak_f, peak = max(seq, key=lambda x: x[1]["vis_mm"])
        dur = (seq[-1][0] - seq[0][0] + cfg["step"]) / fps
        flagged = peak["vis_mm"] >= cfg["min_depth_mm"] or dur > cfg["min_duration_s"]
        ev_out.append({
            "kind": kind, "kind_name": KINDS[kind], "part": part, "other": other,
            "start_s": round((seq[0][0] - f0) / fps, 3), "end_s": round((seq[-1][0] - f0) / fps, 3),
            "duration_s": round(dur, 3), "peak_time_s": round((peak_f - f0) / fps, 3), "peak_frame": peak_f,
            "peak_visible_depth_mm": round(peak["vis_mm"], 1), "peak_any_depth_mm": round(max(r["max_mm"] for _, r in seq), 1),
            "vertices_at_peak": peak["n"], "mark_xy": peak["vis_xy"],
            "score": round(peak["vis_mm"] / 10 * (1 + dur), 3), "flagged": flagged,
        })
    flagged = sorted([e for e in ev_out if e["flagged"]], key=lambda e: -e["score"])
    for i, e in enumerate(flagged):
        e["rank"] = i + 1

    # Stills of the worst moments, from the clip's camera, with a ring where the deepest visible Overlap crosses.
    os.makedirs(os.path.join(out_dir, "moments"), exist_ok=True)
    t_st = time.time()
    for e in flagged[:cfg["top"]]:
        scene.frame_set(e["peak_frame"])
        fn = f"moment_{e['rank']:02d}_t{e['peak_time_s']:05.2f}s_kind{e['kind']}_{e['part']}-{e['other']}.png"
        path = os.path.join(out_dir, "moments", fn)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        if e["mark_xy"]:
            ring(path, e["mark_xy"])
        e["still"] = os.path.join("moments", fn)
    stills_s = time.time() - t_st

    kinds_count = Counter(e["kind"] for e in flagged)
    data = {
        "build_kind": build["kind"],
        "frames_scanned": len(frames), "frame_step": cfg["step"], "first_frame": frames[0], "last_frame": frames[-1],
        "clip_time_of_frame": f"(frame - {f0}) / {fps} s",
        "settings": {k: cfg[k] for k in ("noise_mm", "min_depth_mm", "min_duration_s", "top", "still_res_pct")},
        "rule": "flag an event whose deepest visible Overlap >= min_depth_mm OR which lasts longer than min_duration_s; "
                "score = peak visible depth (cm) x (1 + duration s)",
        "measured_kinds": {str(k): v for k, v in KINDS.items()},
        "not_measured": UNMEASURED,
        "classification": {
            "vertices": nv, "trailing_vertices": int(is_tr.sum()),
            "trailing_by_family": dict(Counter(fam[is_tr].tolist())),
            "body_vertices_by_region": dict(Counter(region[~is_tr].tolist())),
            "solid_surface_triangles": int(len(surf.sets["body"])), "all_triangles": int(len(tris)),
        },
        "events_total": len(ev_out), "events_flagged": len(flagged),
        "flagged_by_kind": {str(k): kinds_count.get(k, 0) for k in KINDS},
        "frames_with_any_visible_overlap": sum(1 for _, r in per_frame if any(x["vis_mm"] > cfg["noise_mm"] for x in r.values())),
        "timing": {"setup_s": round(setup_s, 1), "scan_s": round(scan_s, 1),
                   "scan_s_per_frame": round(scan_s / len(frames), 3),
                   "stills_s": round(stills_s, 1), "stills": min(cfg["top"], len(flagged))},
        "worst": flagged[:cfg["top"]],
        "beyond_top": flagged[cfg["top"]:],
        "per_frame_max_visible_mm": {
            str(f): {f"kind{k}": round(max([r["vis_mm"] for (kk, _, _), r in recs.items() if kk == k] or [0]), 1) for k in KINDS}
            for f, recs in per_frame},
    }
    common.write_json(os.path.join(out_dir, "numbers.json"), data)
    print(f"SCAN DONE frames {len(frames)} events {len(ev_out)} flagged {len(flagged)} "
          f"by kind {dict(kinds_count)} in {scan_s:.1f} s ({scan_s / len(frames):.2f} s/frame)", flush=True)


def ring(path, xy, radius=0.035):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)
    cx, cy = xy[0] * w, xy[1] * h
    r = radius * h
    yy, xx = np.mgrid[0:h, 0:w]
    dd = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    m = np.abs(dd - r) < max(2.0, h / 360)
    px[m] = (1.0, 0.0, 0.85, 1.0)
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


main()
