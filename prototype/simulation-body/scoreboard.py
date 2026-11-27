"""PROTOTYPE (throwaway). review/first-look/epochs/scoreboard.md from every epoch's scorecard and the epoch notes.

  python scoreboard.py     (reads build/first-look/epochs/{notes.json,epoch*/tuning.json,best/tuning.json})
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
B = os.path.join(REPO, "build", "first-look", "epochs")
R = os.path.join(REPO, "review", "first-look", "epochs")
GROUPS = ["follows", "posture", "fight", "feet", "smooth", "spring", "effort"]
HEAD = ["Follows (30)", "Posture (15)", "No fighting (15)", "Feet (10)", "Smooth (10)", "Springs (15)", "Effort (5)"]
JG = ["waist", "chest", "neck", "head", "collar", "upper_arm", "forearm", "hand", "thigh", "shin", "foot"]


def words(t):
    out = []
    for g in JG:
        mult, z = t["groups"].get(g, [1.0, t["zeta"]])
        out.append(f"{g} {t['hz'] * mult:.1f} Hz / {z:.2f}")
    extra = [f"inverse-dynamics feed-forward {t['ff_id']:.1f}", f"reference velocity fed forward {t['ff_vel']:.1f}"]
    extra.append(f"torque cap {t['torque_limit']:.0f} N m" if t.get("torque_limit") else "no torque cap")
    extra.append(f"contact time constant {1000 * t['contact_solref'][0]:.0f} ms" if t.get("contact_solref")
                 else "contact time constant 20 ms (MuJoCo default)")
    return "; ".join(out) + ". " + "; ".join(extra) + "."


def main():
    notes = json.load(open(os.path.join(B, "notes.json"), encoding="utf-8"))
    L = ["# Scored tuning epochs: the stiff and soft figures judged as humanoids\n",
         "Each figure is scored out of 100 over the five carried clips (dance, walk, cute_heart, cute_peace, sing) "
         "with a scorecard fixed before epoch 0 (`prototype/simulation-body/score.py`; every line and its "
         "definition is there and in each epoch's `scorecard.md`). Each figure hill-climbs on its own: a change is "
         "kept only if that figure's total rose. Joints, ranges, masses, shoe contact shapes, motions, clips and how "
         "her hips are carried never change.\n",
         "| Epoch | Figure | Total | " + " | ".join(HEAD) + " | Kept? |", "|---|---|---|" + "---|" * len(HEAD) + "---|"]
    for n in range(6):
        c = json.load(open(os.path.join(R, f"epoch{n}", "scorecard.json")))
        for f in ("stiff", "soft"):
            F = c["figures"][f]
            L.append(f"| {n} | {f} | **{F['total']:.1f}** | " + " | ".join(f"{F['groups'][g]:.1f}" for g in GROUPS)
                     + f" | {notes[str(n)][f]} |")
    c = json.load(open(os.path.join(R, "best", "scorecard.json")))
    for f in ("stiff", "soft"):
        F = c["figures"][f]
        L.append(f"| best | {f} | **{F['total']:.1f}** | " + " | ".join(f"{F['groups'][g]:.1f}" for g in GROUPS) + " | |")
    L.append("\nBest: stiff from epoch 4, soft from epoch 5, both on the solids of epoch 1 "
             "(`build/first-look/epochs/best/`, re-run and re-scored there: identical totals).\n")
    for n in range(6):
        t = notes[str(n)]
        L.append(f"## Epoch {n}\n")
        L.append(f"- **Changed:** {t['what']}")
        L.append(f"- **Why:** {t['why']}")
        if t["did"]:
            L.append(f"- **What it did:** {t['did']}")
        L.append(f"- **Stiff:** {t['stiff']}. **Soft:** {t['soft']}.\n")
    r2 = json.load(open(os.path.join(B, "epoch0", "tuning.json")))
    best = json.load(open(os.path.join(B, "best", "tuning.json")))
    L.append("## Final settings in words (per joint group: spring strength as natural frequency / damping ratio)\n")
    for f in ("stiff", "soft"):
        L.append(f"**{f}, round 2:** {words(r2[f])}\n")
        L.append(f"**{f}, best:** {words(best[f])}\n")
    L.append("All servos act toward the reference angle with damping on the error velocity, gravity compensated "
             "through the servos; strength is scaled by each joint's own effective inertia (round 1's, unchanged).\n")
    L.append("## Solids changed (needs the human's approval)\n")
    bi = json.load(open(os.path.join(B, "best", "body_info.json"), encoding="utf-8"))
    for s in bi["overlap_log"]:
        if s.startswith(("shrink", "trim")) and any(k in s for k in ("chest#", "head", "thigh", "shin", "foot")):
            L.append(f"- {s}")
    L.append("\nExclusions are unchanged from round 2: " + ", ".join("-".join(p) for p in bi["excludes"]) + ".")
    with open(os.path.join(R, "scoreboard.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("wrote", os.path.join(R, "scoreboard.md"))


if __name__ == "__main__":
    main()
