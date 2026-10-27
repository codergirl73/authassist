"""Generate the Devpost/README thumbnail (3:2, 1500x1000). Usage: python scripts/make_thumbnail.py"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1500, 1000
OUT = Path(__file__).resolve().parent.parent / "assets" / "thumbnail.png"
FONT = "/System/Library/Fonts/Helvetica.ttc"


def font(size: int, bold: bool = False):
    try:
        return ImageFont.truetype(FONT, size, index=1 if bold else 0)
    except OSError:
        return ImageFont.load_default(size=size)


def gradient() -> Image.Image:
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        for x in range(W):
            t = x / W * 0.6 + y / H * 0.4
            px[x, y] = (int(9 + 14 * t), int(16 + 26 * t), int(32 + 44 * t))
    return img


def glow(img: Image.Image, cx: int, cy: int, r: int, color: tuple) -> None:
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse((cx - r, cy - r, cx + r, cy + r), fill=color + (90,))
    layer = layer.filter(ImageFilter.GaussianBlur(120))
    img.paste(layer, (0, 0), layer)


def ring(d: ImageDraw.ImageDraw, cx: int, cy: int, r: int, score: int, color: tuple, label: str) -> None:
    box = (cx - r, cy - r, cx + r, cy + r)
    d.arc(box, 0, 360, fill=(255, 255, 255, 40), width=26)
    d.arc(box, -90, -90 + 360 * score / 100, fill=color, width=26)
    f = font(92 if score < 100 else 70, True)
    d.text((cx, cy - 12), str(score), font=f, fill=color, anchor="mm")
    d.text((cx, cy + 52), "/ 100", font=font(30), fill=(150, 165, 190), anchor="mm")
    d.text((cx, cy + r + 52), label, font=font(36, True), fill=color, anchor="mm")


def chip(d, x, y, text, fill=(255, 255, 255, 28)):
    f = font(30)
    w = d.textlength(text, font=f) + 44
    d.rounded_rectangle((x, y, x + w, y + 56), radius=28, fill=fill, outline=(255, 255, 255, 70), width=2)
    d.text((x + 22, y + 28), text, font=f, fill=(225, 232, 245), anchor="lm")
    return x + w + 16


def main() -> None:
    img = gradient()
    glow(img, 1150, 380, 380, (46, 160, 67))
    glow(img, 260, 880, 360, (45, 126, 247))
    d = ImageDraw.Draw(img, "RGBA")

    # Left: title + pitch
    d.text((90, 150), "AuthAssist", font=font(130, True), fill=(255, 255, 255))
    d.text((94, 300), "Catch the missing evidence in a", font=font(48), fill=(205, 215, 235))
    d.text((94, 362), "prior-authorization request —", font=font(48), fill=(205, 215, 235))
    d.text((94, 424), "before the insurer does.", font=font(48, True), fill=(118, 214, 122))

    x = 90
    for t in ("NVIDIA Nemotron", "Nebius Token Factory"):
        x = chip(d, x, 560, t)
    x = 90
    for t in ("Tavily live policy", "Quotes verified in code"):
        x = chip(d, x, 640, t)

    # Right: before -> after card
    d.rounded_rectangle(
        (820, 130, 1420, 760), radius=36, fill=(255, 255, 255, 22), outline=(255, 255, 255, 60), width=2
    )
    d.text((1120, 185), "Readiness check", font=font(34, True), fill=(235, 240, 250), anchor="mm")
    ring(d, 960, 400, 105, 33, (248, 81, 73), "Not ready")
    ring(d, 1280, 400, 105, 100, (46, 190, 80), "Ready")
    # arrow
    d.line((1085, 400, 1150, 400), fill=(200, 210, 230), width=6)
    d.polygon([(1150, 380), (1182, 400), (1150, 420)], fill=(200, 210, 230))
    d.text((1120, 640), "after adding the missing evidence", font=font(30), fill=(170, 185, 210), anchor="mm")
    d.text(
        (1120, 690),
        "every quote checked verbatim in the note",
        font=font(28),
        fill=(118, 214, 122),
        anchor="mm",
    )

    # Bottom strip
    d.line((90, 860, 1410, 860), fill=(255, 255, 255, 40), width=2)
    d.text(
        (90, 905),
        "Reads faxed scans  ·  Finds the insurer's policy  ·  Drafts the letter + PDF",
        font=font(34),
        fill=(190, 202, 225),
        anchor="lm",
    )
    d.text(
        (90, 952),
        "Synthetic data only · Drafts require clinician review · Nothing is submitted to an insurer",
        font=font(24),
        fill=(130, 145, 170),
        anchor="lm",
    )

    OUT.parent.mkdir(exist_ok=True)
    img.save(OUT, optimize=True)
    print(OUT, OUT.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
