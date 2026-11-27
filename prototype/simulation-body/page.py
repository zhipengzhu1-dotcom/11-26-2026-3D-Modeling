"""PROTOTYPE (throwaway). The local review page for the first look at her Simulation Body.

  python3 page.py <round> [clips.json] [body.json]

Writes review/first-look/<round>/index.html with relative links only (open it by double-click).
"""
import datetime
import glob
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
rnd = sys.argv[1]
clips_json = sys.argv[2] if len(sys.argv) > 2 else os.path.join(REPO, "build/first-look/clips.json")
body_json = sys.argv[3] if len(sys.argv) > 3 else os.path.join(REPO, "build/first-look/body.json")
out_dir = os.path.join(REPO, "review/first-look", rnd)
E = html.escape

STILLS = [("solids_front", "Solids over her, front"), ("solids_side", "Solids over her, side"),
          ("solids_back", "Solids over her, back"), ("solids_three_quarter", "Solids over her, three-quarter"),
          ("xray_front", "X-ray, front: every joint marked"), ("xray_side", "X-ray, side"),
          ("feet_side", "Left shoe from the side: floor contact in magenta"), ("feet_below", "Both shoes from below")]
LOOK_FOR = {
    "dance": "Through the quick turn, the kick and the crossed arms: does movement flow through spine, shoulders and wrists, "
             "and do the soft joints overshoot and settle (Q弹) without going rubbery or losing the pose?",
    "dance_pinned": "Hips held in the air with nothing under her: do the legs follow the dance without bending the wrong way, "
                    "and how far do soft and stiff drift from the authored legs?",
    "walk": "Light on her feet? Against the floor grid, watch knees and ankles: does each shoe land on its front pad and heel "
            "tip, without sinking (穿模) or hovering (浮空)?",
    "cute": "Do the poses close in (hands near her face, a tilted head), and does the soft version add a small overshoot and "
            "settle without spoiling the pose? The heart turn comes first, then the peace sign.",
    "sing": "Waist up: do the arm gestures read as a singer's, do the mouth shapes still read, and do soft joints add life "
            "to the gestures without wobbling?",
}
NOT_SHOWN = [
    "She is not balancing: her hips are carried by an invisible hand (or pinned in the air), so nothing here says she can stand or walk under her own forces.",
    "There is no trained Controller: soft and stiff are the Simulation Body following the motion through springy joints, not her deciding anything.",
    "Hair, dress and ornaments are carried rigidly by their bones, with no Secondary Physics (the model's shipped rigid bodies are removed).",
    "The motions are Reference Motions as authored, not yet Fitted Motions resized to her body and heels, so some 穿模 and 浮空 belongs to the source motion.",
]


def video(src, vid):
    return (f'<video id="{vid}" src="{E(src)}" controls loop muted playsinline preload="metadata"></video>'
            f'<div class="speed">speed: ' + "".join(
                f'<button onclick="sp(\'{vid}\',{r})">{r}&times;</button>' for r in (0.25, 0.5, 1)) + "</div>")


clips = []
if os.path.exists(clips_json):
    with open(clips_json, encoding="utf-8") as f:
        clips = json.load(f)
test_data = any("TEST" in c.get("title", "") or c.get("credits") == "test data" for c in clips)

parts = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width, initial-scale=1">',
         f"<title>First look {E(rnd)}</title><style>",
         "body{font:16px/1.5 -apple-system,Segoe UI,sans-serif;max-width:1400px;margin:0 auto;padding:16px;background:#f4f5f7;color:#1d1f24}",
         "h1{font-size:26px}h2{margin-top:40px;border-bottom:1px solid #ccd;padding-bottom:4px}",
         ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}",
         "figure{margin:0}figure img{width:100%;border:1px solid #ccd;background:#fff}figcaption{font-size:14px;color:#445}",
         "video{width:100%;background:#000}.speed button{margin:4px 6px 0 0;padding:4px 12px;font-size:14px}",
         ".look{color:#334;margin:2px 0 8px}pre{white-space:pre-wrap;background:#fff;border:1px solid #ccd;padding:12px;font-size:13px}",
         ".warn{background:#fff3cd;border:1px solid #e0c060;padding:8px 12px}.src{font-size:13px;color:#667}",
         "</style><script>function sp(id,r){var v=document.getElementById(id);v.playbackRate=r;v.loop=true;v.play();}</script></head><body>",
         "<h1>First look at her Simulation Body</h1>",
         "<p><b>The question:</b> does her 19-part Simulation Body sit right on her, and does it move with Anime Feel?</p>"]
if test_data:
    parts.append('<p class="warn">These clips were made from TEST data (plain playback copied into all three figures), '
                 'not from the simulated Simulation Body.</p>')
src = []
for label, p in (("Simulation Body", body_json), ("clips", clips_json)):
    if os.path.exists(p):
        t = datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M")
        src.append(f"{label}: {E(os.path.relpath(p, REPO))} ({t})")
parts.append(f'<p class="src">Made from {"; ".join(src) or "nothing yet"}.</p>')

# stills
parts.append("<h2>Stills: the Simulation Body on her, rest pose</h2>")
parts.append('<p class="look">Tint shows where a solid stands off her; bare surface shows where she pokes out of it. '
             'In the x-ray every joint is a dark ball with a short stick along each hinge axis. The shoes should touch the '
             'floor on the front pad and the heel tip only.</p>')
if os.path.exists(os.path.join(out_dir, "stills", "contact_sheet.png")):
    parts.append('<figure><a href="stills/contact_sheet.png"><img src="stills/contact_sheet.png" alt="contact sheet"></a>'
                 '<figcaption>All stills on one sheet</figcaption></figure><div class="grid" style="margin-top:12px">')
    for name, cap in STILLS:
        if os.path.exists(os.path.join(out_dir, "stills", f"{name}.png")):
            parts.append(f'<figure><a href="stills/{name}.png"><img src="stills/{name}.png" alt="{E(cap)}" loading="lazy"></a>'
                         f"<figcaption>{E(cap)}</figcaption></figure>")
    parts.append("</div>")
else:
    parts.append("<p>No stills yet.</p>")

# clips
parts.append("<h2>Clips: her moved by the Simulation Body</h2>")
parts.append('<p class="look">Left to right: as authored, soft joints, stiff joints. Her face and fingers follow the '
             "source motion; her body follows the Simulation Body.</p>")
seen = set()
n = 0
for c in clips:
    name = "cute" if c["name"] in ("cute_heart", "cute_peace") else c["name"]
    if name in seen:
        continue
    seen.add(name)
    mp4 = os.path.join(out_dir, "clips", f"{name}.mp4")
    title = c.get("title", name) if name != "cute" else "Cute poses: turn and heart, then peace sign"
    parts.append(f"<h3>{E(title)}</h3><p class=\"look\">{E(LOOK_FOR.get(name, LOOK_FOR.get(c.get('kind', ''), '')))}</p>")
    if os.path.exists(mp4):
        n += 1
        parts.append(video(f"clips/{name}.mp4", f"v{n}"))
    else:
        parts.append("<p>Not rendered.</p>")

alone = sorted(glob.glob(os.path.join(out_dir, "body_alone_*.mp4")))
if alone:
    parts.append("<h2>The Simulation Body alone</h2>")
    for p in alone:
        n += 1
        parts.append(f"<h3>{E(os.path.basename(p)[len('body_alone_'):-4])}</h3>" + video(os.path.basename(p), f"v{n}"))

numbers = os.path.join(out_dir, "numbers.md")
if os.path.exists(numbers):
    with open(numbers, encoding="utf-8") as f:
        parts.append("<h2>Numbers</h2><pre>" + E(f.read()) + "</pre>")

parts.append("<h2>What this first look does not show</h2><ul>" + "".join(f"<li>{E(x)}</li>" for x in NOT_SHOWN) + "</ul>")

walk = next((c for c in clips if c.get("kind") == "walk"), None)
walk_vmd = (walk or {}).get("vmd", "")
walk_credit = ("walk by フユネコ＆朱雀 (歩く)" if ("fuyuneko" in walk_vmd or walk_vmd.endswith("歩く.vmd"))
               else "walk by むつごろう (移動モーションv1.3)")
credits = ["Model: miHoYo, converted to MMD by 观海.",
           "Dance motion: Kei (@Kei_MMD_), choreography traced from @ellendance; song: ILLIT '時よ止まれ (Toki Yo Tomare)'.",
           walk_credit[0].upper() + walk_credit[1:] + ".",
           "Cute gestures: グレイ.",
           "Singing motion: 盗賊@つばきP, mouth shapes by i7 made with LipFaceMaker, timed to Jackie Evancho's recording of "
           "Schubert's Ave Maria."]
extra = sorted({c["credits"] for c in clips if c.get("credits") and c.get("credits") != "test data"})
parts.append("<h2>Credits</h2><ul>" + "".join(f"<li>{E(x)}</li>" for x in credits) + "</ul>")
if extra:
    parts.append('<p class="src">As named in clips.json: ' + E(" / ".join(extra)) + "</p>")
parts.append("<p class=\"src\">Prototype for issue 20; private review only, not for redistribution.</p></body></html>")

os.makedirs(out_dir, exist_ok=True)
with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
    f.write("\n".join(parts))
print("PAGE", os.path.join(out_dir, "index.html"))
