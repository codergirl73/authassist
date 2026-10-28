"""Render the AuthAssist logo PNGs (mark, wordmark, favicon, social card) from the same geometry as
assets/logo/logo-mark.svg. Usage: python scripts/make_logo.py"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "assets" / "logo"
FONT = "/System/Library/Fonts/Helvetica.ttc"
SS = 4  # supersample


def gradient(size: int) -> Image.Image:
    """Diagonal #8fd400 -> #16a34a -> #0a6a33, same axis as the SVG."""
    stops = [(0, (143, 212, 0)), (0.5, (22, 163, 74)), (1, (10, 106, 51))]
    img = Image.new("RGB", (size, size))
    px = img.load()
    x1, y1, x2, y2 = (40 * size / 512, 0, 470 * size / 512, size)
    dx, dy = x2 - x1, y2 - y1
    for y in range(size):
        for x in range(size):
            t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
            for (a, ca), (b, cb) in zip(stops, stops[1:], strict=False):
                if a <= t <= b:
                    k = (t - a) / (b - a)
                    px[x, y] = tuple(round(ca[i] + (cb[i] - ca[i]) * k) for i in range(3))
                    break
    return img


def mark(px: int) -> Image.Image:
    s = px * SS
    k = s / 512
    sc = lambda pts: [(x * k, y * k) for x, y in pts]  # noqa: E731
    bg = gradient(s).convert("RGBA")
    base = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    m = Image.new("L", (s, s), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, s, s), radius=116 * k, fill=255)
    base.paste(bg, (0, 0), m)
    d = ImageDraw.Draw(base)

    def poly(pts, fill, w):
        d.polygon(sc(pts), fill=fill)
        d.line(sc(pts + [pts[0], pts[1]]), fill=fill, width=round(w * k), joint="curve")
        for x, y in pts:
            d.ellipse((x * k - w * k / 2, y * k - w * k / 2, x * k + w * k / 2, y * k + w * k / 2), fill=fill)

    poly([(146, 98), (296, 98), (366, 168), (366, 414), (146, 414)], (255, 255, 255, 255), 28)
    poly([(296, 98), (296, 168), (366, 168)], (207, 234, 219, 255), 12)
    for (x0, y0, x1), _ in (((178, 206, 338), 0), ((178, 250, 290), 0)):
        d.rounded_rectangle((x0 * k, y0 * k, x1 * k, (y0 + 22) * k), radius=11 * k, fill=(211, 219, 232, 255))
    ring = Image.new("L", (s, s), 0)
    ImageDraw.Draw(ring).ellipse(
        ((338 - 100) * k, (366 - 100) * k, (338 + 100) * k, (366 + 100) * k), fill=255
    )
    base.paste(bg, (0, 0), ring)  # cut-out ring in the background gradient
    d = ImageDraw.Draw(base)
    d.ellipse(((338 - 80) * k, (366 - 80) * k, (338 + 80) * k, (366 + 80) * k), fill=(15, 157, 69, 255))
    pts = sc([(300, 368), (330, 398), (384, 332)])
    d.line(pts, fill=(255, 255, 255, 255), width=round(28 * k), joint="curve")
    for x, y in (pts[0], pts[2]):
        r = 14 * k
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 255))
    return base.resize((px, px), Image.LANCZOS)


def wordmark(dark: bool) -> Image.Image:
    h = 256
    ink = (238, 242, 249) if dark else (11, 18, 32)
    f = ImageFont.truetype(FONT, 150, index=1)
    text_w = int(f.getlength("AuthAssist"))
    img = Image.new("RGBA", (h + 40 + text_w + 20, h), (0, 0, 0, 0))
    img.alpha_composite(mark(h), (0, 0))
    d = ImageDraw.Draw(img)
    d.text((h + 40, h / 2 + 4), "AuthAssist", font=f, fill=ink, anchor="lm")
    return img


def social_card() -> Image.Image:
    w, h = 1200, 630
    card = gradient(1200).crop((0, 0, w, h))
    base = Image.new("RGB", (w, h), (11, 18, 32))
    base.paste(card.resize((w, h)).point(lambda v: int(v * 0.22)))
    img = base.convert("RGBA")
    img.alpha_composite(mark(210), (90, 110))
    d = ImageDraw.Draw(img)
    d.text(
        (340, 170),
        "AuthAssist",
        font=ImageFont.truetype(FONT, 110, index=1),
        fill=(255, 255, 255),
        anchor="lm",
    )
    f = ImageFont.truetype(FONT, 36)
    d.text(
        (90, 400),
        "Catch the missing evidence",
        font=ImageFont.truetype(FONT, 62, index=1),
        fill=(255, 255, 255),
        anchor="ls",
    )
    d.text(
        (90, 470),
        "before the insurer does.",
        font=ImageFont.truetype(FONT, 62, index=1),
        fill=(143, 212, 0),
        anchor="ls",
    )
    d.text(
        (90, 550),
        "Prior-auth readiness check · NVIDIA Nemotron on Nebius · Tavily",
        font=f,
        fill=(190, 200, 218),
        anchor="ls",
    )
    return img.convert("RGB")


if __name__ == "__main__":
    mark(512).save(OUT / "logo-mark-512.png")
    mark(180).save(OUT / "apple-touch-icon.png")
    mark(64).save(OUT / "favicon-64.png")
    wordmark(False).save(OUT / "logo-wordmark-light.png")
    wordmark(True).save(OUT / "logo-wordmark-dark.png")
    social_card().save(OUT / "social-card.png")
    print(sorted(p.name for p in OUT.iterdir()))
