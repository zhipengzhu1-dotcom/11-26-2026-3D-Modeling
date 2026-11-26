#!/usr/bin/env python3
"""PROTOTYPE, throwaway. One command for the toon-look prototype (question: what should she look like?).

  python3 prototype/toon-look/run.py [--run-id ID] [name ...]

Renders every look in params/ (round0..round5, then variants A, B, C; or only the names given) in
headless Blender, measures each round against the reference frames, and writes the tables,
report.md and a single-file index.html viewer to review/look/<run-id>/ (git-ignored).
The reference frames must already sit in review/look/<run-id>/reference/ref1.png .. ref6.png.
Needs: Blender 5.2 with MMD Tools, python3 with numpy and Pillow.
"""
import base64
import glob
import io
import json
import os
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = subprocess.run(["git", "-C", HERE, "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
sys.path.insert(0, HERE)
import measure  # noqa: E402
import survey  # noqa: E402

BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
VERIFY = os.path.join(ROOT, ".claude/skills/verify-vodyanitsa/scripts/verify")
ORDER = ["round0", "round1", "round2", "round3", "round4", "round5", "variantA", "variantB", "variantC"]
# Second pass (after the Eye Check picked B): style learned from ten other gosari videos, rounds 6 to 11 on B,
# then sub-variants of B. Round 4 is re-rendered there as the best earlier round, for comparison.
CHANNEL = "20261126-gosari-channel"
ORDER2 = ["round4", "round6", "round7", "round8", "round9", "round10", "round11",
          "subB1", "subB2", "subB3", "subB4", "subB5"]
SETS = {"20261126-gosari": ORDER, CHANNEL: ORDER2}
CREDITS = [
    "Model: 【原神】沃雅妮莎 (Vodyanitsa) by miHoYo, converted by 观海",
    "Motion: 時よ止まれ by Kei (@Kei_MMD_), traced from @ellendance; song by ILLIT",
    "Colour reference: gosari ごさり's video 'Vodyanitsa pompom 【Genshin Impact MMD】' "
    "(youtube.com/shorts/6Cf1tnG-wVA), used privately as a colour reference only",
]


CREDITS2 = CREDITS[:2] + [
    "Style reference: gosari ごさり's videos (youtube.com/@gosari542): the Vodyanitsa pompom Short (6Cf1tnG-wVA) "
    "and the ten videos listed in the survey, used privately as a style reference only",
]


def guard(path):
    r = subprocess.run([VERIFY, "guard", path], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(r.stderr or r.stdout)


def params(name):
    with open(os.path.join(HERE, "params", name + ".json"), encoding="utf-8") as f:
        return json.load(f)


def render(name, out):
    pmx = sorted(glob.glob(os.path.join(ROOT, "沃雅妮莎_by_*", "沃雅妮莎.pmx")))[0]
    vmd = os.path.join(ROOT, "assets/motion/toki-yo-tomare/時よ止まれ.vmd")
    d = os.path.join(out, name)
    os.makedirs(d, exist_ok=True)
    log = os.path.join(d, "blender.log")
    with open(log, "w") as lf:
        r = subprocess.run([BLENDER, "-b", "--python-exit-code", "1", "--python", os.path.join(HERE, "look.py"), "--",
                            pmx, vmd, os.path.join(HERE, "params", name + ".json"), d], stdout=lf, stderr=subprocess.STDOUT)
    if r.returncode != 0:
        sys.exit(f"Blender failed for {name}; see {log}")
    return d


def fmt_rgb(c):
    return "#%02x%02x%02x" % tuple(c) if c else "n/a"


def table_md(name, t, change):
    lines = [f"| region | reference | render | dE |", "|---|---|---|---|"]
    for r in t["rows"]:
        lines.append(f"| {r['region']} | {fmt_rgb(r['ref'] and r['ref']['rgb'])} | "
                     f"{fmt_rgb(r['render'] and r['render']['rgb'])} | {r['dE']} |")
    lines.append(f"\nMean dE {t['mean_dE']}, worst {t['worst_dE']} ({t['worst_region']}).")
    if change:
        lines.append(f"\nChanged for the next round: {change}")
    return "\n".join(lines)


def jpeg_uri(path, w=540):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    if im.width > w:
        im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


def survey_views(out):
    vf = os.path.join(out, "survey", "videos.json")
    if not os.path.exists(vf):
        return []
    with open(vf, encoding="utf-8") as f:
        videos = json.load(f)
    mf = os.path.join(out, "survey", "measure.json")
    meas = json.load(open(mf, encoding="utf-8")) if os.path.exists(mf) else {"frames": {}, "shading": {}}
    views = []
    for vid, v in videos.items():
        fr = sorted(glob.glob(os.path.join(out, "survey", vid, "f*.png")))
        shots = {os.path.basename(p)[:-4]: jpeg_uri(p, 600) for p in fr}
        m = {k.split("/")[1]: x for k, x in meas["frames"].items() if k.startswith(vid + "/")}
        sh = {k.split("/")[1]: x for k, x in meas["shading"].items() if k.startswith(vid + "/")}
        views.append({"key": "survey-" + vid, "label": "Survey: " + v["title"][:48], "shots": shots, "state": {
            "what": f"<b>{v['title']}</b> ({v['date']}) · {v['url']}<br>Model: {v['model']} · Framing: {v['framing']}"
                    f"<br>Scene: {v['scene']}<br>Credits: {v['credits']}<br><i>Someone else's video: private style "
                    f"reference, never commit or publish.</i>",
            "survey": {"frames": m, "shading": sh}}})
    return views


def build_viewer(out, names):
    ref_dir = os.path.join(out, "reference")
    refs = [jpeg_uri(p) for p in sorted(glob.glob(os.path.join(ref_dir, "ref*.png")))]
    views = survey_views(out)
    views += [{"key": f"ref{i + 1}", "label": f"Reference frame {i + 1} (6Cf1tnG-wVA)", "shots": {"frame": u}, "state": {
        "what": "Frame of gosari's Vodyanitsa video (private colour reference, never commit or publish)"}}
        for i, u in enumerate(refs)]
    for n in names:
        d = os.path.join(out, n)
        if not os.path.isdir(d):
            continue
        shots = {s: jpeg_uri(os.path.join(d, s + ".png")) for s in ("close1", "close2", "close3", "full")
                 if os.path.exists(os.path.join(d, s + ".png"))}
        t = None
        if os.path.exists(os.path.join(d, "table.json")):
            with open(os.path.join(d, "table.json"), encoding="utf-8") as f:
                t = json.load(f)
        views.append({"key": n, "label": label(n) + (" (best earlier round)" if n == "round4" and out.endswith(CHANNEL) else ""),
                      "shots": shots, "state": {"params": params(n), "table": t}})
    html = VIEWER.replace("__VIEWS__", json.dumps(views, ensure_ascii=False)).replace(
        "__REFS__", json.dumps(refs)).replace("__CREDITS__", " · ".join(CREDITS2 if out.endswith(CHANNEL) else CREDITS))
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)


def label(n):
    if n.startswith("subB"):
        return "Sub-variant " + n[3:] + (": " + params(n)["name"] if params(n).get("name") else "")
    return {"variantA": "Variant A, soft", "variantB": "Variant B, cel", "variantC": "Variant C, stage"}.get(
        n, n.replace("round", "Round "))


def build_report(out, names):
    parts = ["# Toon look prototype: what should she look like?", "",
             "PROTOTYPE output, throwaway. Five rounds of render, measure and adjust against frames of gosari's video, "
             "then three variants for an Eye Check. Open `index.html` (arrow keys flip views; R toggles the reference).", ""]
    rounds = [n for n in names if n.startswith("round")]
    summary = ["| round | mean dE | worst dE (region) | main change into this round |", "|---|---|---|---|"]
    for n in rounds:
        p = os.path.join(out, n, "table.json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                t = json.load(f)
            summary.append(f"| {n} | {t['mean_dE']} | {t['worst_dE']} ({t['worst_region']}) | {params(n).get('change', 'baseline')} |")
    parts += ["## Summary", ""] + summary + [""]
    for i, n in enumerate(names):
        p = os.path.join(out, n, "table.json")
        nxt = names[i + 1] if i + 1 < len(names) and names[i + 1].startswith("round") and n.startswith("round") else None
        parts += [f"## {label(n)}", "", params(n).get("note", ""), ""]
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                t = json.load(f)
            parts += [table_md(n, t, nxt and params(nxt).get("change")), ""]
        pp = {k: v for k, v in params(n).items() if k not in ("note", "change")}
        parts += ["<details><summary>parameters</summary>", "", "```json", json.dumps(pp, ensure_ascii=False, indent=1),
                  "```", "</details>", ""]
    notes = os.path.join(out, "notes.md")
    if os.path.exists(notes):
        with open(notes, encoding="utf-8") as f:
            parts += [f.read(), ""]
    parts += ["## Credits", ""] + [f"- {c}" for c in CREDITS]
    with open(os.path.join(out, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(parts) + "\n")


def style_md(t):
    st = t.get("style")
    if not st:
        return ""
    lines = [f"Style checks against the gosari style sheet: {st['passed']}/{st['of']} in the survey range.", "",
             "| check | value | survey range | |", "|---|---|---|---|"]
    for r in st["rows"]:
        lines.append(f"| {r['check']} | {r['value']} | {r['target'][0]} to {r['target'][1]} | {'in' if r['ok'] else '**off**'} |")
    return "\n".join(lines)


def build_report2(out, names):
    """Report for the second pass: survey, style sheet, rounds 6 to 11 and the sub-variants."""
    def read(n):
        p = os.path.join(out, n)
        return open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    tables = {}
    for n in names:
        p = os.path.join(out, n, "table.json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                tables[n] = json.load(f)
    parts = ["# Toon look, second pass: gosari's channel, rounds 6 to 11 on variant B", "",
             "PROTOTYPE output, throwaway. Open `index.html` (arrow keys or the bottom bar flip views; R toggles a "
             "reference beside the image; 1 to 9 pick a still).", "", read("notes-head.md"), "",
             read("style-sheet.md"), "", "## Rounds at a glance", "",
             "| look | mean dE | worst dE (region) | style checks in range | main change |", "|---|---|---|---|---|"]
    for n in names:
        t = tables.get(n)
        if t:
            parts.append(f"| {label(n)} | {t['mean_dE']} | {t['worst_dE']} ({t['worst_region']}) | "
                         f"{t['style']['passed']}/{t['style']['of']} | {params(n).get('change', '')} |")
    parts.append("")
    for n in names:
        parts += [f"## {label(n)}", "", params(n).get("note", ""), ""]
        if params(n).get("change"):
            parts += [f"Changed going into this look: {params(n)['change']}", ""]
        if n in tables:
            parts += [table_md(n, tables[n], None), "", style_md(tables[n]), ""]
        pp = {k: v for k, v in params(n).items() if k not in ("note", "change", "name")}
        parts += ["<details><summary>parameters</summary>", "", "```json", json.dumps(pp, ensure_ascii=False, indent=1),
                  "```", "</details>", ""]
    parts += [read("notes-tail.md"), "", "## Credits", ""] + [f"- {c}" for c in CREDITS2]
    with open(os.path.join(out, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(parts) + "\n")


def run_set(run_id, names):
    out = os.path.join(ROOT, "review", "look", run_id)
    guard(out)
    if not glob.glob(os.path.join(out, "reference", "ref*.png")):
        sys.exit(f"reference frames missing in {out}/reference (see README)")
    order = SETS.get(run_id, ORDER)
    if run_id == CHANNEL and os.path.exists(os.path.join(out, "survey", "videos.json")):
        sys.argv = ["survey", out]
        survey.main()  # crop and measure the survey frames (already captured by hand, see style-sheet.md)
    for n in names or order:
        if n.startswith("viewer"):
            continue
        d = render(n, out)
        print(f"== {n}: rendered")
        if n.startswith(("round", "variant", "subB")):
            sys.argv = ["measure", os.path.join(out, "reference"), d]
            measure.main()
    present = [n for n in order if os.path.isdir(os.path.join(out, n))]
    (build_report2 if run_id == CHANNEL else build_report)(out, present)
    build_viewer(out, present)
    print("viewer:", os.path.relpath(os.path.join(out, "index.html"), ROOT))


def main():
    a = sys.argv[1:]
    run_ids = list(SETS)
    if "--run-id" in a:
        i = a.index("--run-id")
        run_ids = [a[i + 1]]
        del a[i:i + 2]
    for r in run_ids:
        names = [n for n in a if n in SETS.get(r, ORDER) or n.startswith("viewer")] if a else None
        if a and not names:
            continue
        run_set(r, names)


VIEWER = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Toon Look Prototype</title>
<style>
:root{--bg:#f4f2ee;--fg:#1d1d22;--muted:#6a6a75;--card:#fff;--line:#ddd8cf;--bar:#1d1d22;--barfg:#fff}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#18181c;--fg:#ececf1;--muted:#a0a0ab;--card:#232329;--line:#34343c;--bar:#ececf1;--barfg:#18181c}}
:root[data-theme="dark"]{--bg:#18181c;--fg:#ececf1;--muted:#a0a0ab;--card:#232329;--line:#34343c;--bar:#ececf1;--barfg:#18181c}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,sans-serif;padding:16px 16px 90px}
h1{font-size:18px;margin:0 0 4px}.sub{color:var(--muted);font-size:12px;margin-bottom:12px}
.main{display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start}
.imgs{display:flex;gap:8px;flex-wrap:wrap}.imgs figure{margin:0}.imgs img{display:block;max-height:72vh;max-width:100%;border-radius:6px;border:1px solid var(--line)}
figcaption{font-size:11px;color:var(--muted)}
.thumbs{display:flex;gap:6px;margin:8px 0;flex-wrap:wrap}.thumbs button{border:1px solid var(--line);background:var(--card);color:var(--fg);border-radius:6px;padding:4px 10px;cursor:pointer}
.thumbs button.on{background:var(--fg);color:var(--bg)}
.state{flex:1;min-width:300px;max-width:640px;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px}
table{border-collapse:collapse;width:100%;font-size:12px}td,th{border-bottom:1px solid var(--line);padding:3px 6px;text-align:left}
.sw{display:inline-block;width:14px;height:14px;border-radius:3px;vertical-align:middle;margin-right:4px;border:1px solid var(--line)}
pre{white-space:pre-wrap;font-size:11px;max-height:40vh;overflow:auto;background:var(--bg);padding:8px;border-radius:6px}
.bar{position:fixed;left:50%;bottom:16px;transform:translateX(-50%);background:var(--bar);color:var(--barfg);border-radius:999px;padding:6px 10px;display:flex;gap:8px;align-items:center;box-shadow:0 4px 18px rgba(0,0,0,.25);max-width:calc(100vw - 32px)}
.bar button{background:transparent;color:var(--barfg);border:0;font-size:18px;cursor:pointer;padding:2px 8px}
.bar .lab{min-width:180px;text-align:center;font-weight:600}.bar label{font-size:12px;white-space:nowrap}
.foot{color:var(--muted);font-size:11px;margin-top:16px}
</style></head><body>
<h1>Toon look prototype: what should she look like?</h1>
<div class="sub">PROTOTYPE, throwaway. ←/→ flip views · 1–9 pick still · R toggles the reference beside the image</div>
<div class="thumbs" id="thumbs"></div>
<div class="main"><div class="imgs" id="imgs"></div><div class="state" id="state"></div></div>
<div class="foot">__CREDITS__</div>
<div class="bar"><button id="prev" aria-label="previous">←</button><span class="lab" id="lab"></span><button id="next" aria-label="next">→</button>
<label><input type="checkbox" id="showref"> reference beside</label></div>
<script>
const V=__VIEWS__, R=__REFS__; let i=0, shot=null, ri=0;
const $=id=>document.getElementById(id);
function sw(c){return c?`<span class="sw" style="background:rgb(${c.join(',')})"></span>${'#'+c.map(x=>x.toString(16).padStart(2,'0')).join('')}`:'n/a'}
function draw(){const v=V[i];const ks=Object.keys(v.shots);if(!ks.includes(shot))shot=ks[0];
 $('lab').textContent=`${i+1}/${V.length} · ${v.label}`;
 $('thumbs').innerHTML=ks.map((k,j)=>`<button class="${k===shot?'on':''}" data-k="${k}">${j+1} ${k}</button>`).join('');
 $('thumbs').querySelectorAll('button').forEach(b=>b.onclick=()=>{shot=b.dataset.k;draw()});
 let h=`<figure><img src="${v.shots[shot]}" alt="${v.label} ${shot}"><figcaption>${v.label} · ${shot}</figcaption></figure>`;
 if($('showref').checked&&R.length&&!v.key.startsWith('ref')&&!v.key.startsWith('survey')){h+=`<figure><img src="${R[ri%R.length]}" alt="reference"><figcaption>reference frame ${ri%R.length+1} (click to cycle)</figcaption></figure>`}
 $('imgs').innerHTML=h;const f=$('imgs').querySelectorAll('figure')[1];if(f)f.onclick=()=>{ri++;draw()};
 const s=v.state;let t='';
 if(s.table){t+=`<b>Colour difference (CIELAB ΔE*ab, region means)</b> mean ${s.table.mean_dE}, worst ${s.table.worst_dE} (${s.table.worst_region})<table><tr><th>region</th><th>reference</th><th>render</th><th>ΔE</th></tr>`+
  s.table.rows.map(r=>`<tr><td>${r.region}</td><td>${sw(r.ref&&r.ref.rgb)}</td><td>${sw(r.render&&r.render.rgb)}</td><td>${r.dE??''}</td></tr>`).join('')+`</table>`}
 if(s.table&&s.table.style){t+=`<b>Style checks against the gosari style sheet</b> ${s.table.style.passed}/${s.table.style.of} in range<table><tr><th>check</th><th>value</th><th>survey range</th><th></th></tr>`+
  s.table.style.rows.map(r=>`<tr><td>${r.check}</td><td>${r.value}</td><td>${r.target.join(' to ')}</td><td>${r.ok?'in':'<b>off</b>'}</td></tr>`).join('')+`</table>`}
 if(s.survey){const f=s.survey.frames[shot];if(f)t+=`<b>Measured on ${shot}</b><table>`+Object.entries(f).map(([k,x])=>`<tr><td>${k}</td><td>${x}</td></tr>`).join('')+`</table>`;
  const h=s.survey.shading[shot];if(h)t+=`<b>Shadow vs lit (hand-picked rectangles)</b><pre>${JSON.stringify(h,null,1)}</pre>`}
 if(s.params){t+=`<p>${s.params.note||''}</p>${s.params.change?`<p><b>Change into this view:</b> ${s.params.change}</p>`:''}<b>Parameters</b><pre>${JSON.stringify(Object.fromEntries(Object.entries(s.params).filter(([k])=>k!=='note'&&k!=='change')),null,1)}</pre>`}
 if(s.what)t=`<p>${s.what}</p>`+t;
 $('state').innerHTML=t;}
function go(d){i=(i+d+V.length)%V.length;draw()}
$('prev').onclick=()=>go(-1);$('next').onclick=()=>go(1);$('showref').onchange=draw;
addEventListener('keydown',e=>{if(e.target.closest('input,textarea,[contenteditable]')&&e.target.type!=='checkbox')return;
 if(e.key==='ArrowLeft')go(-1);else if(e.key==='ArrowRight')go(1);else if(e.key==='r'||e.key==='R'){$('showref').checked=!$('showref').checked;draw()}
 else if(/^[1-9]$/.test(e.key)){const ks=Object.keys(V[i].shots);if(ks[+e.key-1]){shot=ks[+e.key-1];draw()}}});
draw();
</script></body></html>"""

if __name__ == "__main__":
    main()
