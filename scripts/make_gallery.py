"""Build the Devpost project-gallery images (1500x1000, 3:2) into assets/gallery/.

Usage: python scripts/make_gallery.py
Needs: assets/ui-*.jpg screenshots, out/case_04.pdf (sample PDF), eval/results.md.
Reuses the drawing helpers from make_thumbnail.py so every image matches.
"""

import re
import shutil
from pathlib import Path

import make_thumbnail as mt
import pymupdf
from make_thumbnail import GREEN, RED, SOFT, WHITE, font, glass, layer, sc
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
GALLERY = ASSETS / "gallery"
mt.W, mt.H = 1500, 1000


def canvas(title, subtitle):
    img = mt.background()
    d = ImageDraw.Draw(img)
    d.text((sc(70), sc(88)), title, font=font(52, True), fill=WHITE, anchor="ls")
    d.text((sc(72), sc(130)), subtitle, font=font(26), fill=SOFT, anchor="ls")
    return img


def paste_card(img, pic, box):
    """Paste `pic` (RGB) scaled to fit `box`, rounded corners + shadow, centred."""
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    scale = min(sc(bw) / pic.width, sc(bh) / pic.height)
    pic = pic.resize((int(pic.width * scale), int(pic.height * scale)), Image.LANCZOS).convert("RGBA")
    x = sc(x0) + (sc(bw) - pic.width) // 2
    y = sc(y0) + (sc(bh) - pic.height) // 2
    mask = Image.new("L", pic.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, pic.width, pic.height), radius=sc(18), fill=255)
    sh = layer(img.size)
    ImageDraw.Draw(sh).rounded_rectangle(
        (x, y + sc(14), x + pic.width, y + pic.height + sc(14)), radius=sc(18), fill=(0, 0, 0, 170)
    )
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(sc(24))))
    img.paste(pic, (x, y), mask)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(
        (x, y, x + pic.width, y + pic.height), radius=sc(18), outline=(255, 255, 255, 90), width=sc(2)
    )
    return img


def save(img, name):
    out = GALLERY / name
    img.convert("RGB").resize((mt.W, mt.H), Image.LANCZOS).save(out, optimize=True)
    print(out.name, out.stat().st_size // 1024, "KB")


def screenshot_frame(src, title, subtitle, name):
    pic = Image.open(ASSETS / src).convert("RGB")
    save(paste_card(canvas(title, subtitle), pic, (70, 170, 1430, 930)), name)


def pdf_frame(name):
    doc = pymupdf.open(ROOT / "out" / "case_04.pdf")
    pages = []
    for i in range(min(2, len(doc))):
        pix = doc[i].get_pixmap(dpi=130)
        pages.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
    img = canvas(
        "Draft letter + request PDF",
        "Checklist with verbatim quotes, the letter, and the policy source. For clinician review and signature.",
    )
    slots = [(180, 165, 730, 940), (770, 165, 1320, 940)]
    for pic, box in zip(pages, slots, strict=False):
        img = paste_card(img, pic, box)
    save(img, name)


def eval_frame(name):
    text = (ROOT / "eval" / "results.md").read_text()

    def metric(label):
        m = re.search(rf"\| {re.escape(label)}[^|]*\| ([^|]+) \|", text)
        return m.group(1).strip() if m else "n/a"

    rows = [
        [c.strip() for c in ln.strip("|\n").split("|")]
        for ln in text.splitlines()
        if ln.startswith("| case_")
    ]
    img = canvas(
        "Evaluation on 8 synthetic cases",
        "Two are scanned faxes. Failures and run-to-run variation are listed in the repo.",
    )
    tiles = [
        (metric("Overall outcome accuracy").split(" ")[0], "outcomes correct"),
        (metric("Evidence quotes verified").split(" ")[0], "quotes verified"),
        (metric("Per-criterion accuracy").split(" ")[0], "criteria correct"),
        ("~99%", "fax read accuracy"),
    ]
    for i, (big, label) in enumerate(tiles):
        x = 70 + i * 340
        img = glass(img, (x, 170, x + 320, 290), radius=22)
        d = ImageDraw.Draw(img)
        d.text((sc(x + 26), sc(222)), big, font=font(50, True), fill=(120, 222, 130), anchor="lm")
        d.text((sc(x + 26), sc(266)), label, font=font(21), fill=SOFT, anchor="lm")

    img = glass(img, (70, 320, 1430, 930), radius=26, fill=(18, 28, 52, 215))
    d = ImageDraw.Draw(img)
    heads = [
        ("Case", 100),
        ("Scenario", 220),
        ("Expected", 860),
        ("Actual", 1030),
        ("Score", 1230),
        ("Bypass", 1320),
    ]
    for h, x in heads:
        d.text((sc(x), sc(362)), h.upper(), font=font(18, True), fill=SOFT, anchor="lm")
    d.line((sc(95), sc(386), sc(1405), sc(386)), fill=(255, 255, 255, 60), width=sc(2))
    for i, r in enumerate(rows[:8]):
        y = 426 + i * 62
        case, scenario, inp, exp, act, score, bypass = r[0], r[1], r[2], r[3], r[4], r[5], r[6]
        ok = "(OK)" in act
        scenario = scenario if len(scenario) <= 52 else scenario[:49] + "..."
        d.text((sc(100), sc(y)), case.replace("case_", "Case "), font=font(23, True), fill=WHITE, anchor="lm")
        d.text(
            (sc(220), sc(y)),
            scenario + ("  [fax]" if "scanned" in inp else ""),
            font=font(21),
            fill=(215, 224, 242),
            anchor="lm",
        )
        d.text((sc(860), sc(y)), exp.replace("_", " "), font=font(21), fill=SOFT, anchor="lm")
        color = GREEN if ok else RED
        d.ellipse((sc(1030), sc(y - 9), sc(1048), sc(y + 9)), fill=color)
        mt.check(d, 1039, y, 14, (14, 22, 40), 2.5) if ok else mt.cross(d, 1039, y, 14, (14, 22, 40), 2.5)
        d.text(
            (sc(1060), sc(y)),
            act.replace(" (OK)", "").replace(" (MISS)", "").replace("_", " "),
            font=font(21, True),
            fill=color,
            anchor="lm",
        )
        d.text((sc(1230), sc(y)), score, font=font(22, True), fill=WHITE, anchor="lm")
        d.text((sc(1320), sc(y)), bypass, font=font(21), fill=SOFT, anchor="lm")
    save(img, name)


def main():
    GALLERY.mkdir(parents=True, exist_ok=True)
    for old in GALLERY.glob("*.png"):
        old.unlink()
    shutil.copy(ASSETS / "thumbnail.png", GALLERY / "01-overview.png")
    screenshot_frame(
        "ui-landing.jpg",
        "A real web app, not a notebook",
        "Landing page, demo sign-in, and a guided workspace.",
        "02-landing.png",
    )
    screenshot_frame(
        "ui-choose.jpg",
        "Pick a note, typed or a scanned fax",
        "Eight synthetic cases. Nemotron vision reads the fax.",
        "03-choose-note.png",
    )
    screenshot_frame(
        "ui-results.jpg",
        "Readiness check",
        "Score, key metrics, what's missing, and the policy source.",
        "04-readiness-result.png",
    )
    screenshot_frame(
        "ui-annotated-note.jpg",
        "Evidence, verified in the note",
        "Green is met, red is missing. Every quote is checked word-for-word in code.",
        "05-annotated-note.png",
    )
    screenshot_frame(
        "ui-fixed.jpg",
        "Fill the gaps, re-check, 33 to 100",
        "Add the missing documentation as an addendum and the score updates.",
        "06-gap-fill-100.png",
    )
    shutil.copy(ASSETS / "architecture.png", GALLERY / "07-architecture.png")
    shutil.copy(ASSETS / "swimlane.png", GALLERY / "08-swimlane.png")
    screenshot_frame(
        "ui-model-trace.jpg",
        "Which model did what",
        "Nemotron on Nebius Token Factory, with latency and tokens for every call.",
        "09-model-trace.png",
    )
    screenshot_frame(
        "ui-letter.jpg",
        "Draft letter + request PDF",
        "For clinician review and signature. Never submitted to an insurer.",
        "10-letter.png",
    )
    pdf_frame("11-letter-and-pdf.png")
    eval_frame("12-evaluation.png")


if __name__ == "__main__":
    main()
