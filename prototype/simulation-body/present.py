"""Build the narrated first-look status video from clips and stills already on disk.

Run from anywhere:
    uv run --with pillow python prototype/simulation-body/present.py

Inputs come from review/first-look/ (git-ignored). Everything this makes goes to
build/first-look/presentation/ (intermediates) and review/first-look/presentation/
(the video and narration.txt), both git-ignored. Narration is spoken offline with
macOS `say`; nothing leaves the machine.

To change a line, edit SEGMENTS below and run again.
"""

from __future__ import annotations

import glob
import math
import shutil
import subprocess
import sys
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / "review" / "first-look"
FINAL = REVIEW / "final"
OUT_DIR = REVIEW / "presentation"
BUILD = ROOT / "build" / "first-look" / "presentation"
VIDEO_OUT = OUT_DIR / "vodyanitsa-first-look.mp4"
NARRATION_OUT = OUT_DIR / "narration.txt"

W, H, FPS = 1920, 1080, 30
SR = 48000  # audio sample rate; 1600 samples per frame
LEAD_S = 0.30  # silence before each segment's narration
TAIL_S = 0.55  # air after it
SENTENCE_GAP_S = 0.30  # between separately spoken sentences (segment 14)
VOICE_PREFERENCE = ["Premium", "Enhanced"]
FALLBACK_VOICE = "Samantha"
RATE_WPM = 170

# Spoken respellings, applied only to what the voice reads.
SAY_RESPELL = {"Vodyanitsa": "Voddyaneetsa"}

# Look
BG = (21, 23, 28)
INK = (238, 235, 228)
DIM_INK = (170, 168, 160)
ACCENT = (217, 201, 168)  # warm sand, close to the clips' label band
BAND_H = 114
BAND_RGBA = (18, 20, 24, 215)

CLIP = {
    "dance": FINAL / "clips" / "dance.mp4",
    "walk": FINAL / "clips" / "walk.mp4",
    "cute": FINAL / "clips" / "cute.mp4",
    "sing": FINAL / "clips" / "sing.mp4",
    "r1_dance": REVIEW / "round1" / "clips" / "dance.mp4",
    "r2_cute": REVIEW / "round2" / "clips" / "cute.mp4",
}
STILL = FINAL / "stills"

NOW, LACK, DONE, NEXT = "WHAT WE HAVE NOW", "STILL LACKING", "ACCOMPLISHED", "NEXT"

# Each segment: tag, caption, picture, narration (list of sentences spoken as one take
# unless "split" is set, in which case each sentence is spoken separately so the
# picture can follow it).
SEGMENTS = [
    dict(
        id="00_title", tag=None, caption=None, picture=("title",),
        say=["Vodyanitsa. A first look at her Simulation Body. This is what we have now, "
             "what is still lacking, what has been accomplished, and what comes next."],
    ),
    dict(
        id="01_body", tag=NOW, caption="19 parts, joints at her bones, 107 solids",
        picture=("stills", "solids_front.png", "xray_front.png"),
        say=["First, what we have now. She has a body the simulator understands: nineteen rigid "
             "parts, with joints placed exactly where her bones are, and one hundred and seven "
             "simple solids that follow her drawn surface. Her hair, her skirt and her hanging "
             "sleeves get no solid. They are left for Secondary Physics."],
    ),
    dict(
        id="02_feet", tag=NOW, caption="Shoe contact: front pad and heel tip only",
        picture=("stills", "feet_side.png", "feet_below.png"),
        say=["Her shoes meet the floor only where they are drawn to: the front pad and the heel "
             "tip, shown here in magenta."],
    ),
    dict(
        id="03_dance", tag=NOW,
        caption="As authored, soft joints, stiff joints. Hips carried: she is not balancing",
        picture=("clip", "dance", 0, None),
        say=["And she moves under physics. On the left, the dance exactly as its maker authored "
             "it. In the middle and on the right, her Simulation Body following that dance, once "
             "with soft joints and once with stiff ones. Her hips are carried by an invisible "
             "hand, so she is not balancing."],
    ),
    dict(
        id="04_four", tag=NOW, caption="Dance, walk, cute gestures, singing",
        picture=("sequence", [("walk", 0, None), ("cute", 0, None), ("sing", 0, None)]),
        say=["She does this across four kinds of movement: the dance, a walk, cute gestures, and "
             "a singing passage, all rendered in her settled look."],
    ),
    dict(
        id="05_balance", tag=LACK, caption="No balance, no trained Controller",
        picture=("clip", "walk", 0, None),
        say=["Now, what is still lacking. She cannot balance, and nothing here is a trained "
             "Controller. Springs simply pull each joint toward the motion."],
    ),
    dict(
        id="06_rigid", tag=LACK, caption="Hair and dress carried rigidly: no Secondary Physics",
        picture=("clip", "cute", 1.0, 4.0),
        say=["Her hair and dress are carried rigidly. There is no Secondary Physics yet."],
    ),
    dict(
        id="07_fit", tag=LACK, caption="Motions not yet fitted to her body and heels",
        picture=("clip", "walk", 0, None),
        say=["The motions play as authored. The walk was made for flat shoes, so her feet catch "
             "the floor, and some motions cross her legs. They still have to be fitted to her "
             "body and her heels."],
    ),
    dict(
        id="08_spring", tag=LACK, caption="Soft spring is small; a raised arm still catches",
        picture=("clip", "dance", 5.0, 8.0),
        say=["And the soft figure's spring is small: an overshoot of about four percent in the "
             "dance. Near the end, a raised arm still catches beside her head."],
    ),
    dict(
        id="09_round1", tag=DONE, caption="Round 1: solids wrapped hair, skirt and sleeves",
        picture=("clip", "r1_dance", 3.0, 6.0),
        say=["What has been accomplished. Round one went wrong: the solids wrapped her hair, "
             "skirt and sleeves, and that bulk shoved her around."],
    ),
    dict(
        id="10_round2", tag=DONE, caption="Round 2: body-only solids; the soft head folds",
        picture=("clip", "r2_cute", 4.5, 8.0),
        say=["Round two gave solids only to her body and close-fitting pieces. The stiff figure "
             "followed the motion well, but with soft joints her head folded forward."],
    ),
    dict(
        id="11_scores", tag=DONE, caption=None, picture=("scores",),
        say=["Then came five scored rounds, judging each figure as a humanoid out of one "
             "hundred. The stiff figure rose from eighty-two to eighty-eight. The soft figure "
             "rose from sixty-three to seventy-nine, but it got there by becoming exact, and it "
             "lost its spring."],
    ),
    dict(
        id="12_final", tag=DONE,
        caption="Final round: firm spine, neck and ankles; soft arms and legs",
        picture=("clip", "cute", 4.5, 8.0),
        say=["So the final round keeps her spine, neck and ankles firm, and her arms and legs "
             "soft. Her head stays up, and she still springs a little. Along the way, her "
             "settled look now renders in moving clips, and her drawn surface follows the "
             "simulated body to within a few millimetres over most of her."],
    ),
    dict(
        id="13_eyecheck", tag=NEXT, caption="Your Eye Check locks her structure",
        picture=("stills", "solids_three_quarter.png", "xray_side.png"),
        say=["What comes next is your Eye Check. If you confirm, her structure is locked: "
             "nineteen parts, solids on her body only, a head without hair, shoe contact at the "
             "pad and heel tip, elbows that may pass straight by fifteen degrees, and hips "
             "carried while she is judged."],
    ),
    dict(
        id="14_map", tag=NEXT, caption="After the Eye Check", split=True,
        picture=("map", [
            "Fit the motions to her body and heels",
            "Choose how her Controller is trained, with Q弹 asked for in training",
            "Decide what she does first under real physics",
            "Secondary Physics for her hair and dress",
        ]),
        say=["Then the map moves on.",
             "The motions are fitted to her heels.",
             "Her Controller's training is chosen, with her springiness asked for in training.",
             "We decide what she does first under real physics.",
             "And her hair and dress get their Secondary Physics."],
    ),
    dict(
        id="15_credits", tag=None, caption=None, picture=("credits",), say=[], hold_s=5.0,
    ),
]

CREDITS = [
    "Model 【原神】沃雅妮莎 by miHoYo, converted to MMD by 观海",
    "Dance 時よ止まれ: motion by ケイ (@Kei_MMD_), choreography traced from @ellendance, song by ILLIT",
    "Walk 歩く by フユネコ＆朱雀",
    "Cute gestures ターンしてハート and ピスピース by グレイ",
    "Singing: body motion by 盗賊@つばきP, mouth shapes by i7 with LipFaceMaker, "
    "timed to Jackie Evancho's recording of Schubert's Ave Maria",
    "Prototype for private review. Not for redistribution.",
]


# ---------------------------------------------------------------- helpers

def run(cmd: list[str]) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"command failed: {' '.join(map(str, cmd))}\n{r.stderr[-3000:]}")
    return r.stdout


def ffmpeg(*args: str) -> None:
    run(["ffmpeg", "-hide_banner", "-v", "error", "-y", *map(str, args)])


def clip_seconds(path: Path) -> float:
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                      "-of", "csv=p=0", str(path)]).strip())


def find_font() -> str:
    hits = sorted(glob.glob("/System/Library/AssetsV2/com_apple_MobileAsset_Font*/*/AssetData/PingFang.ttc"))
    for p in hits + ["/System/Library/Fonts/PingFang.ttc"]:
        if Path(p).exists():
            return p
    return "/System/Library/Fonts/Hiragino Sans GB.ttc"


FONT_PATH = find_font()
PINGFANG = "PingFang" in FONT_PATH
WEIGHT_INDEX = {"light": 15, "regular": 3, "medium": 7, "semibold": 11}  # PingFang SC faces


def font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    if PINGFANG:
        return ImageFont.truetype(FONT_PATH, size, index=WEIGHT_INDEX[weight])
    return ImageFont.truetype(FONT_PATH, size, index=1 if weight in ("medium", "semibold") else 0)


def fit_font(text: str, size: int, weight: str, max_w: int) -> ImageFont.FreeTypeFont:
    while size > 18:
        f = font(size, weight)
        if f.getlength(text) <= max_w:
            return f
        size -= 2
    return font(size, weight)


def draw_spaced(d: ImageDraw.ImageDraw, xy, text, f, fill, spacing):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += f.getlength(ch) + spacing


def band_layer(tag: str | None, caption: str | None) -> Image.Image:
    """Full-frame transparent layer with the bottom band: section tag above the caption."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if not tag and not caption:
        return im
    d = ImageDraw.Draw(im)
    top = H - BAND_H
    d.rectangle([0, top, W, H], fill=BAND_RGBA)
    d.rectangle([0, top, W, top + 2], fill=(*ACCENT, 140))
    x = 64
    if tag:
        tf = font(24, "semibold")
        d.rectangle([x, top + 20, x + 6, top + 40], fill=ACCENT)
        draw_spaced(d, (x + 20, top + 14), tag, tf, ACCENT, 4)
    if caption:
        cf = fit_font(caption, 42, "medium", W - 2 * x)
        d.text((x, top + 48), caption, font=cf, fill=INK)
    return im


def fit_into(img: Image.Image, box_w: int, box_h: int) -> Image.Image:
    s = min(box_w / img.width, box_h / img.height)
    return img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)


def card_base() -> Image.Image:
    return Image.new("RGB", (W, H), BG)


def still_pair(a: str, b: str) -> Image.Image:
    im = card_base()
    area_h = H - BAND_H - 40
    gap = 40
    imgs = [Image.open(STILL / n).convert("RGB") for n in (a, b)]
    box_w = (W - 3 * gap) // 2
    imgs = [fit_into(i, box_w, area_h) for i in imgs]
    total = sum(i.width for i in imgs) + gap
    x = (W - total) // 2
    for i in imgs:
        y = 20 + (area_h - i.height) // 2
        im.paste(i, (x, y))
        x += i.width + gap
    return im


def title_card() -> Image.Image:
    frame = BUILD / "title_bg.png"
    ffmpeg("-ss", "4", "-i", CLIP["dance"], "-frames:v", "1", frame)
    bg = Image.open(frame).convert("RGB").filter(ImageFilter.GaussianBlur(6))
    bg = ImageEnhance.Brightness(bg).enhance(0.22)
    tint = Image.new("RGB", (W, H), BG)
    im = Image.blend(bg, tint, 0.35)
    d = ImageDraw.Draw(im)
    t1 = "Vodyanitsa: first look at her Simulation Body"
    f1 = fit_font(t1, 80, "semibold", W - 240)
    f2 = font(40, "light")
    t2 = "Where we are, 27 November 2026"
    y = H // 2 - 90
    d.text(((W - f1.getlength(t1)) / 2, y), t1, font=f1, fill=INK)
    d.rectangle([W // 2 - 60, y + 130, W // 2 + 60, y + 133], fill=ACCENT)
    d.text(((W - f2.getlength(t2)) / 2, y + 160), t2, font=f2, fill=DIM_INK)
    return im


def scores_card() -> Image.Image:
    im = card_base()
    d = ImageDraw.Draw(im)
    head = "Five scored rounds, each figure judged as a humanoid out of 100"
    fh = fit_font(head, 46, "medium", W - 240)
    y0 = 200
    d.text(((W - fh.getlength(head)) / 2, y0), head, font=fh, fill=INK)
    # table
    tx, tw = 560, 800
    ty = y0 + 130
    row_h = 120
    fl = font(56, "medium")
    fn = font(64, "light")
    d.line([tx, ty, tx + tw, ty], fill=(*DIM_INK,), width=2)
    for i, (name, a, b) in enumerate([("Stiff", "82.1", "87.6"), ("Soft", "62.6", "79.2")]):
        y = ty + i * row_h
        d.text((tx + 20, y + 26), name + ":", font=fl, fill=ACCENT)
        nums = f"{a}  →  {b}"
        d.text((tx + tw - 20 - fn.getlength(nums), y + 20), nums, font=fn, fill=INK)
        d.line([tx, y + row_h, tx + tw, y + row_h], fill=DIM_INK, width=2)
    note = "Soft gained by becoming exact, and lost its spring"
    fnote = font(40, "light")
    d.text(((W - fnote.getlength(note)) / 2, ty + 2 * row_h + 70), note, font=fnote, fill=DIM_INK)
    return im


def map_layers(lines: list[str]) -> tuple[Image.Image, list[Image.Image]]:
    base = card_base()
    d = ImageDraw.Draw(base)
    head = "Then the map moves on"
    fh = font(52, "semibold")
    d.text((300, 190), head, font=fh, fill=INK)
    d.rectangle([300, 275, 420, 278], fill=ACCENT)
    fl = font(44, "regular")
    fnum = font(44, "semibold")
    layers = []
    for i, line in enumerate(lines):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lay)
        y = 350 + i * 120
        ld.text((300, y), f"{i + 1}", font=fnum, fill=ACCENT)
        ld.text((370, y), line, font=fit_font(line, 44, "regular", W - 370 - 200) if fl.getlength(line) > W - 570 else fl, fill=INK)
        layers.append(lay)
    return base, layers


def credits_card() -> Image.Image:
    im = card_base()
    d = ImageDraw.Draw(im)
    fh = font(30, "semibold")
    draw_spaced(d, (120, 150), "CREDITS", fh, ACCENT, 6)
    f = font(31, "regular")
    y = 240
    max_w = W - 240
    for i, line in enumerate(CREDITS):
        last = i == len(CREDITS) - 1
        if last:
            y += 40
        # wrap on spaces
        words, cur, rows = line.split(" "), "", []
        for w_ in words:
            trial = (cur + " " + w_).strip()
            if f.getlength(trial) > max_w and cur:
                rows.append(cur)
                cur = w_
            else:
                cur = trial
        rows.append(cur)
        for r in rows:
            d.text((120, y), r, font=f, fill=DIM_INK if last else INK)
            y += 50
        y += 26
    return im


# ---------------------------------------------------------------- audio

def pick_voice() -> str:
    voices = run(["say", "-v", "?"]).splitlines()
    english = [v for v in voices if " en_" in v or " en-" in v]
    for marker in VOICE_PREFERENCE:
        for v in english:
            if f"({marker})" in v or marker in v.split("#")[0]:
                return v.split("  ")[0].strip()
    return FALLBACK_VOICE


def speak(text: str, voice: str, stem: Path) -> bytes:
    """Speak text offline, return 16-bit stereo PCM at SR."""
    spoken = text
    for k, v in SAY_RESPELL.items():
        spoken = spoken.replace(k, v)
    txt = stem.with_suffix(".txt")
    txt.write_text(spoken, encoding="utf-8")
    aiff = stem.with_suffix(".aiff")
    run(["say", "-v", voice, "-r", str(RATE_WPM), "-f", str(txt), "-o", str(aiff)])
    raw = stem.with_suffix(".pcm")
    ffmpeg("-i", aiff, "-ar", SR, "-ac", 2, "-f", "s16le", "-acodec", "pcm_s16le", raw)
    return raw.read_bytes()


def silence(seconds: float) -> bytes:
    return b"\x00\x00\x00\x00" * round(seconds * SR)


# ---------------------------------------------------------------- video

X264 = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-r", str(FPS), "-video_track_timescale", "15360", "-an"]


def render_still(img: Image.Image, overlay: Image.Image, n: int, out: Path,
                 reveals: list[tuple[Image.Image, float]] | None = None) -> None:
    base = BUILD / f"{out.stem}_base.png"
    ov = BUILD / f"{out.stem}_band.png"
    img.convert("RGB").save(base)
    overlay.save(ov)
    inputs = ["-loop", "1", "-framerate", FPS, "-i", base, "-loop", "1", "-framerate", FPS, "-i", ov]
    chain = "[0:v][1:v]overlay=0:0[v0]"
    last = "v0"
    for k, (lay, t) in enumerate(reveals or []):
        p = BUILD / f"{out.stem}_reveal{k}.png"
        lay.save(p)
        inputs += ["-loop", "1", "-framerate", FPS, "-i", p]
        chain += f";[{last}][{k + 2}:v]overlay=0:0:enable='gte(t,{t:.3f})'[v{k + 1}]"
        last = f"v{k + 1}"
    ffmpeg(*inputs, "-filter_complex", chain, "-map", f"[{last}]", "-frames:v", n, *X264, out)


def clip_window(key: str, start: float, end: float | None, n: int, label: str) -> str:
    """Filter producing exactly n frames from a clip window, looped as needed."""
    path = CLIP[key]
    total = round(clip_seconds(path) * FPS)
    a = round(start * FPS)
    b = total if end is None else min(total, round(end * FPS))
    size = b - a
    loops = max(0, math.ceil(n / size) - 1)
    return (f"trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS,"
            f"loop=loop={loops}:size={size}:start=0,setpts=N/{FPS}/TB,"
            f"trim=end_frame={n}[{label}]")


def render_clip(parts: list[tuple[str, float, float | None, int]], overlay: Image.Image,
                n: int, out: Path) -> None:
    ov = BUILD / f"{out.stem}_band.png"
    overlay.save(ov)
    inputs, chains, labels = [], [], []
    for i, (key, s, e, k) in enumerate(parts):
        inputs += ["-i", CLIP[key]]
        chains.append(f"[{i}:v]" + clip_window(key, s, e, k, f"p{i}"))
        labels.append(f"[p{i}]")
    ov_idx = len(parts)
    inputs += ["-loop", "1", "-framerate", FPS, "-i", ov]
    if len(parts) > 1:
        chains.append("".join(labels) + f"concat=n={len(parts)}:v=1:a=0[cat]")
        src = "[cat]"
    else:
        src = labels[0]
    chains.append(f"{src}[{ov_idx}:v]overlay=0:0,setsar=1[out]")
    ffmpeg(*inputs, "-filter_complex", ";".join(chains), "-map", "[out]",
           "-frames:v", n, *X264, out)


# ---------------------------------------------------------------- main

def main() -> None:
    if shutil.which("say") is None or shutil.which("ffmpeg") is None:
        sys.exit("needs macOS `say` and ffmpeg on PATH")
    for p in CLIP.values():
        if not p.exists():
            sys.exit(f"missing source clip: {p}")
    BUILD.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    voice = pick_voice()
    print(f"voice: {voice} at {RATE_WPM} wpm; font: {FONT_PATH}")

    all_pcm = bytearray()
    seg_files = []
    timeline = []
    t_cursor = 0
    for seg in SEGMENTS:
        sid = seg["id"]
        # audio: one take, or sentence by sentence
        starts = []
        pcm = bytearray(silence(LEAD_S)) if seg["say"] else bytearray()
        if seg["say"]:
            takes = seg["say"] if seg.get("split") else [" ".join(seg["say"])]
            for k, line in enumerate(takes):
                if k:
                    pcm += silence(SENTENCE_GAP_S)
                starts.append(len(pcm) / 4 / SR)
                pcm += speak(line, voice, BUILD / f"{sid}_say{k}")
            spoken_s = len(pcm) / 4 / SR + TAIL_S
        else:
            spoken_s = seg.get("hold_s", 5.0)
        n = math.ceil(spoken_s * FPS)
        pcm += b"\x00" * (n * (SR // FPS) * 4 - len(pcm))
        all_pcm += pcm

        band = band_layer(seg["tag"], seg["caption"])
        out = BUILD / f"{sid}.mp4"
        pic = seg["picture"]
        kind = pic[0]
        if kind == "title":
            render_still(title_card(), band, n, out)
        elif kind == "stills":
            render_still(still_pair(pic[1], pic[2]), band, n, out)
        elif kind == "scores":
            render_still(scores_card(), band, n, out)
        elif kind == "credits":
            render_still(credits_card(), band, n, out)
        elif kind == "map":
            base, layers = map_layers(pic[1])
            # line i appears as sentence i+1 begins (sentence 0 is the lead-in)
            reveals = [(lay, starts[i + 1] if i + 1 < len(starts) else 0) for i, lay in enumerate(layers)]
            render_still(base, band, n, out, reveals)
        elif kind == "clip":
            render_clip([(pic[1], pic[2], pic[3], n)], band, n, out)
        elif kind == "sequence":
            subs = pic[1]
            each = [n // len(subs)] * len(subs)
            each[-1] += n - sum(each)
            render_clip([(k, s, e, c) for (k, s, e), c in zip(subs, each)], band, n, out)
        seg_files.append(out)
        timeline.append((sid, t_cursor / FPS, (t_cursor + n) / FPS))
        t_cursor += n
        print(f"{sid}: {n / FPS:6.2f} s  (starts {timeline[-1][1]:6.2f} s)")

    wav = BUILD / "narration.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(all_pcm))

    lst = BUILD / "segments.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in seg_files))
    silent = BUILD / "video_only.mp4"
    ffmpeg("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent)
    ffmpeg("-i", silent, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
           "-c:a", "aac", "-b:a", "192k", "-ar", SR, "-shortest", "-movflags", "+faststart", VIDEO_OUT)

    NARRATION_OUT.write_text(
        "\n\n".join(" ".join(s["say"]) for s in SEGMENTS if s["say"]) + "\n", encoding="utf-8")
    (BUILD / "timeline.tsv").write_text(
        "".join(f"{sid}\t{a:.3f}\t{b:.3f}\n" for sid, a, b in timeline))
    print(f"wrote {VIDEO_OUT} ({t_cursor / FPS:.2f} s) and {NARRATION_OUT}")


if __name__ == "__main__":
    main()
