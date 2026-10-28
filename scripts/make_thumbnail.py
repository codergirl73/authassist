"""Generate the Devpost/README thumbnail (3:2, 1500x1000). Usage: python scripts/make_thumbnail.py

Drawn at 2x and downsampled for smooth edges. Coordinates below are in 1500x1000 space.
"""

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, S = 1500, 1000, 2
OUT = Path(__file__).resolve().parent.parent / "assets" / "thumbnail.png"
HELV = "/System/Library/Fonts/Helvetica.ttc"
MONO = "/System/Library/Fonts/Menlo.ttc"

GREEN, AMBER, RED = (46, 190, 80), (230, 170, 40), (248, 81, 73)
WHITE, SOFT = (255, 255, 255), (190, 202, 225)


def sc(v):
    return int(round(v * S))


def font(size, bold=False, mono=False):
    path = MONO if mono else HELV
    try:
        return ImageFont.truetype(path, sc(size), index=(1 if bold else 0))
    except OSError:
        return ImageFont.load_default(size=sc(size))


def layer(size=None):
    return Image.new("RGBA", size or (sc(W), sc(H)), (0, 0, 0, 0))


def shadow(img, box, radius, blur=30, alpha=120, dy=14):
    lay = layer(img.size)
    x0, y0, x1, y1 = (sc(v) for v in box)
    ImageDraw.Draw(lay).rounded_rectangle(
        (x0, y0 + sc(dy), x1, y1 + sc(dy)), radius=sc(radius), fill=(0, 0, 0, alpha)
    )
    return Image.alpha_composite(img, lay.filter(ImageFilter.GaussianBlur(sc(blur))))


def background():
    img = Image.new("RGB", (sc(W), sc(H)))
    px = img.load()
    for y in range(0, sc(H)):
        for x in range(0, sc(W), 1):
            t = x / sc(W) * 0.6 + y / sc(H) * 0.4
            px[x, y] = (int(8 + 12 * t), int(14 + 24 * t), int(30 + 42 * t))
    img = img.convert("RGBA")
    for cx, cy, r, col in [
        (1180, 300, 420, (46, 160, 67)),
        (180, 900, 400, (45, 110, 247)),
        (700, -60, 300, (118, 80, 255)),
    ]:
        lay = layer()
        ImageDraw.Draw(lay).ellipse((sc(cx - r), sc(cy - r), sc(cx + r), sc(cy + r)), fill=col + (85,))
        img = Image.alpha_composite(img, lay.filter(ImageFilter.GaussianBlur(sc(110))))
    dots = layer()
    d = ImageDraw.Draw(dots)
    for x in range(30, W, 44):
        for y in range(30, H, 44):
            d.ellipse((sc(x) - 2, sc(y) - 2, sc(x) + 2, sc(y) + 2), fill=(255, 255, 255, 22))
    return Image.alpha_composite(img, dots)


def glass(img, box, radius=28, fill=(255, 255, 255, 26), outline=(255, 255, 255, 70)):
    img = shadow(img, box, radius, blur=24, alpha=110, dy=10)
    lay = layer(img.size)
    x0, y0, x1, y1 = (sc(v) for v in box)
    ImageDraw.Draw(lay).rounded_rectangle(
        (x0, y0, x1, y1), radius=sc(radius), fill=fill, outline=outline, width=sc(2)
    )
    return Image.alpha_composite(img, lay)


def check(d, cx, cy, r, color, w=5):
    pts = [(cx - r * 0.55, cy + r * 0.0), (cx - r * 0.12, cy + r * 0.45), (cx + r * 0.6, cy - r * 0.45)]
    d.line([(sc(x), sc(y)) for x, y in pts], fill=color, width=sc(w), joint="curve")


def cross(d, cx, cy, r, color, w=5):
    for a, b in [((-1, -1), (1, 1)), ((-1, 1), (1, -1))]:
        d.line(
            (
                sc(cx + a[0] * r * 0.5),
                sc(cy + a[1] * r * 0.5),
                sc(cx + b[0] * r * 0.5),
                sc(cy + b[1] * r * 0.5),
            ),
            fill=color,
            width=sc(w),
        )


def badge(d, x, y, text, color, icon):
    f = font(19, True)
    tw = d.textlength(text, font=f) / S
    w = tw + 62
    d.rounded_rectangle(
        (sc(x), sc(y), sc(x + w), sc(y + 42)),
        radius=sc(21),
        fill=(14, 22, 40, 245),
        outline=color,
        width=sc(3),
    )
    cx, cy = x + 24, y + 21
    d.ellipse((sc(cx - 11), sc(cy - 11), sc(cx + 11), sc(cy + 11)), fill=color)
    if icon == "check":
        check(d, cx, cy, 14, (14, 22, 40), 3)
    elif icon == "cross":
        cross(d, cx, cy, 14, (14, 22, 40), 3)
    else:
        d.text((sc(cx), sc(cy + 1)), "?", font=font(17, True), fill=(14, 22, 40), anchor="mm")
    d.text((sc(x + 44), sc(cy)), text, font=f, fill=WHITE, anchor="lm")


def note_card():
    """Tilted faxed note with highlighted evidence + status badges."""
    cw, ch, lw = 470, 540, 680
    lay = layer((sc(lw), sc(ch + 20)))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle((0, 0, sc(cw), sc(ch)), radius=sc(20), fill=(251, 248, 240, 255))
    d.rounded_rectangle((0, 0, sc(cw), sc(54)), radius=sc(20), fill=(236, 231, 218, 255))
    d.rectangle((0, sc(34), sc(cw), sc(54)), fill=(236, 231, 218, 255))
    d.text(
        (sc(26), sc(27)),
        "FAX  10/2026   p.1/1",
        font=font(17, False, True),
        fill=(120, 116, 105),
        anchor="lm",
    )
    d.text((sc(cw - 26), sc(27)), "SYNTHETIC", font=font(16, True), fill=(190, 70, 60), anchor="rm")

    ink = (38, 40, 52)
    mono = font(21, False, True)

    def line(y, text, hl=None):
        if hl:
            tw = d.textlength(text, font=mono) / S
            d.rounded_rectangle((sc(22), sc(y - 4), sc(22 + tw + 18), sc(y + 30)), radius=sc(7), fill=hl)
        d.text((sc(32), sc(y + 13)), text, font=mono, fill=ink, anchor="lm")

    d.text(
        (sc(26), sc(84)),
        "Test Patient 04 · Dr. Example",
        font=font(18, True),
        fill=(90, 90, 100),
        anchor="lm",
    )
    line(112, "HPI: 47-year-old male with")
    line(146, "low back pain for 10 weeks.")
    line(206, "8 weeks of physical therapy", hl=(176, 232, 178, 255))
    line(256, "Denies bowel/bladder change.")
    line(316, "took naproxen at times", hl=(247, 220, 140, 255))
    for i, wbar in enumerate((380, 300, 340)):
        d.rounded_rectangle(
            (sc(28), sc(380 + i * 26), sc(28 + wbar), sc(392 + i * 26)),
            radius=sc(6),
            fill=(214, 210, 198, 255),
        )
    # missing neuro exam: dashed red box
    x0, y0, x1, y1 = 22, 470, cw - 22, 514
    for t in range(0, int((x1 - x0) / 14)):
        xs = x0 + t * 14
        d.line((sc(xs), sc(y0), sc(xs + 8), sc(y0)), fill=RED + (255,), width=sc(3))
        d.line((sc(xs), sc(y1), sc(xs + 8), sc(y1)), fill=RED + (255,), width=sc(3))
    d.text(
        (sc(36), sc(492)), "EXAM: not documented", font=font(20, False, True), fill=(190, 60, 55), anchor="lm"
    )

    badge(d, 392, 198, "VERIFIED", GREEN, "check")
    badge(d, 392, 308, "UNCLEAR", AMBER, "q")
    badge(d, 330, 488, "MISSING", RED, "cross")
    return lay


def ring(d, cx, cy, r, score, color, label):
    box = (sc(cx - r), sc(cy - r), sc(cx + r), sc(cy + r))
    d.arc(box, 0, 360, fill=(70, 84, 114, 255), width=sc(15))
    d.arc(box, -90, -90 + 360 * score / 100, fill=color, width=sc(15))
    d.text(
        (sc(cx), sc(cy - 2)),
        str(score),
        font=font(round(r * 0.78) if score < 100 else round(r * 0.6), True),
        fill=color,
        anchor="mm",
    )
    d.text((sc(cx), sc(cy + r + 30)), label, font=font(22, True), fill=color, anchor="mm")


def stat(img, x, y, num, label):
    img = glass(img, (x, y, x + 212, y + 116), radius=22)
    d = ImageDraw.Draw(img)
    d.text((sc(x + 22), sc(y + 40)), num, font=font(46, True), fill=(120, 222, 130), anchor="lm")
    d.text((sc(x + 22), sc(y + 86)), label, font=font(21), fill=SOFT, anchor="lm")
    return img


def icon(d, kind, cx, cy):
    c = (230, 238, 252)
    w = sc(4)
    if kind == "doc":
        d.rounded_rectangle(
            (sc(cx - 14), sc(cy - 18), sc(cx + 14), sc(cy + 18)), radius=sc(4), outline=c, width=w
        )
        for i in range(3):
            d.line((sc(cx - 7), sc(cy - 8 + i * 8), sc(cx + 7), sc(cy - 8 + i * 8)), fill=c, width=sc(3))
    elif kind == "search":
        d.ellipse((sc(cx - 15), sc(cy - 17), sc(cx + 9), sc(cy + 7)), outline=c, width=w)
        d.line((sc(cx + 6), sc(cy + 5), sc(cx + 18), sc(cy + 17)), fill=c, width=sc(5))
    elif kind == "check":
        d.ellipse((sc(cx - 19), sc(cy - 19), sc(cx + 19), sc(cy + 19)), outline=c, width=w)
        check(d, cx, cy, 24, c, 4)
    else:  # letter
        d.rounded_rectangle(
            (sc(cx - 18), sc(cy - 14), sc(cx + 18), sc(cy + 14)), radius=sc(4), outline=c, width=w
        )
        d.line(
            (
                sc(cx - 18),
                sc(cy - 12),
                sc(cx),
                sc(cy + 2),
            ),
            fill=c,
            width=sc(3),
        )
        d.line((sc(cx), sc(cy + 2), sc(cx + 18), sc(cy - 12)), fill=c, width=sc(3))


def pipeline(img):
    steps = [
        ("doc", "Read the note", "Nemotron vision"),
        ("search", "Find the policy", "Tavily search + extract"),
        ("check", "Match evidence", "Nemotron Ultra + code"),
        ("letter", "Draft the letter", "Nemotron + PDF"),
    ]
    xs = [150, 490, 830, 1170]
    img = glass(img, (70, 850, 1430, 975), radius=30, fill=(255, 255, 255, 18))
    d = ImageDraw.Draw(img)
    for i, ((kind, title, sub), x) in enumerate(zip(steps, xs, strict=True)):
        d.ellipse(
            (sc(x - 34), sc(912 - 34), sc(x + 34), sc(912 + 34)),
            fill=(40, 56, 92, 255),
            outline=(120, 136, 172, 255),
            width=sc(2),
        )
        icon(d, kind, x, 912)
        d.text((sc(x + 46), sc(900)), title, font=font(25, True), fill=WHITE, anchor="lm")
        d.text((sc(x + 46), sc(931)), sub, font=font(18), fill=SOFT, anchor="lm")
        if i < 3:
            ax = x + 272
            d.line((sc(ax), sc(912), sc(ax + 36), sc(912)), fill=(150, 165, 195, 200), width=sc(3))
            d.polygon(
                [(sc(ax + 36), sc(903)), (sc(ax + 50), sc(912)), (sc(ax + 36), sc(921))],
                fill=(150, 165, 195, 220),
            )
    return img


def logo_mark(px: int) -> Image.Image:
    from make_logo import mark

    return mark(px)


def main() -> None:
    random.seed(4)
    img = background()
    d = ImageDraw.Draw(img)

    # Top-left pill
    pill = "NEBIUS TOKEN FACTORY  ×  NVIDIA NEMOTRON"
    f = font(21, True)
    pw = d.textlength(pill, font=f) / S + 44
    pl = layer()
    ImageDraw.Draw(pl).rounded_rectangle(
        (sc(160), sc(48), sc(160 + pw), sc(96)),
        radius=sc(25),
        fill=(118, 214, 122, 40),
        outline=(118, 214, 122, 170),
        width=sc(2),
    )
    img = Image.alpha_composite(img, pl)
    d = ImageDraw.Draw(img)
    img.alpha_composite(logo_mark(sc(64)), (sc(80), sc(40)))
    d.text((sc(182), sc(72)), pill, font=f, fill=(150, 235, 155), anchor="lm")

    # Headline
    d.text((sc(78), sc(212)), "AuthAssist", font=font(116, True), fill=WHITE, anchor="ls")
    d.text((sc(82), sc(300)), "Catch the missing evidence", font=font(44), fill=(212, 222, 240), anchor="ls")
    d.text(
        (sc(82), sc(358)), "before the insurer does.", font=font(44, True), fill=(118, 214, 122), anchor="ls"
    )
    d.text(
        (sc(84), sc(412)), "Prior-auth readiness check for lumbar MRI:", font=font(26), fill=SOFT, anchor="ls"
    )
    d.text(
        (sc(84), sc(448)),
        "a note in, a verified checklist + draft letter out.",
        font=font(26),
        fill=SOFT,
        anchor="ls",
    )

    # Proof tiles (real eval numbers)
    img = stat(img, 80, 520, "8/8", "cases correct")
    img = stat(img, 312, 520, "100%", "quotes verified")
    img = stat(img, 544, 520, "~99%", "fax read accuracy")
    d = ImageDraw.Draw(img)
    d.text(
        (sc(84), sc(678)),
        "Eval on 8 synthetic cases, incl. 2 scanned faxes",
        font=font(19),
        fill=(130, 145, 172),
        anchor="ls",
    )

    # Tilted note card
    lay = note_card()
    rot = lay.rotate(4, resample=Image.BICUBIC, expand=True)
    sh = Image.new("RGBA", rot.size, (0, 0, 0, 0))
    sh.paste((0, 0, 0, 150), mask=rot.split()[3])
    sh = sh.filter(ImageFilter.GaussianBlur(sc(22)))
    px, py = sc(755), sc(40)
    img.alpha_composite(sh, (px + sc(6), py + sc(18)))
    img.alpha_composite(rot, (px, py))

    # Score card (before -> after)
    img = glass(img, (960, 650, 1430, 835), radius=30, fill=(18, 28, 52, 215), outline=(255, 255, 255, 80))
    d = ImageDraw.Draw(img)
    d.text((sc(1195), sc(676)), "READINESS SCORE", font=font(18, True), fill=SOFT, anchor="mm")
    ring(d, 1060, 738, 44, 33, RED, "Not ready")
    ring(d, 1330, 738, 44, 100, GREEN, "Ready")
    d.line((sc(1125), sc(740), sc(1190), sc(740)), fill=(200, 210, 232, 255), width=sc(5))
    d.polygon([(sc(1190), sc(729)), (sc(1212), sc(740)), (sc(1190), sc(751))], fill=(200, 210, 232, 255))
    d.text((sc(1160), sc(768)), "add the", font=font(19), fill=SOFT, anchor="mm")
    d.text((sc(1160), sc(790)), "evidence", font=font(19), fill=SOFT, anchor="mm")

    img = pipeline(img)
    d = ImageDraw.Draw(img)
    d.text(
        (sc(750), sc(990)),
        "Synthetic data only · Drafts require clinician review · Nothing is ever submitted to an insurer",
        font=font(15),
        fill=(120, 135, 162),
        anchor="mm",
    )

    OUT.parent.mkdir(exist_ok=True)
    img.convert("RGB").resize((W, H), Image.LANCZOS).save(OUT, optimize=True)
    print(OUT, OUT.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
