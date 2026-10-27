"""Generate assets/architecture.png and assets/swimlane.png (1800x1200, 3:2).

Usage: python scripts/make_diagrams.py
Reuses the drawing helpers from make_thumbnail.py so the visuals match.
"""

import make_thumbnail as mt
from make_thumbnail import AMBER, GREEN, SOFT, WHITE, font, glass, layer, sc
from PIL import Image, ImageDraw

mt.W, mt.H = 1800, 1200
BLUE = (70, 150, 255)
CYAN = (60, 195, 225)
PURPLE = (170, 125, 255)
INK = (14, 22, 40)


def mix(color, amount=0.28, base=(18, 28, 52)):
    return tuple(int(base[i] * (1 - amount) + color[i] * amount) for i in range(3))


def arrow(d, pts, color=(185, 198, 224), width=4, dashed=False, head=True):
    segs = list(zip(pts, pts[1:], strict=False))
    for (x0, y0), (x1, y1) in segs:
        if not dashed:
            d.line((sc(x0), sc(y0), sc(x1), sc(y1)), fill=color + (255,), width=sc(width))
            continue
        length = max(abs(x1 - x0), abs(y1 - y0))
        n = int(length // 16)
        for i in range(n + 1):
            t0, t1 = i * 16 / length, min((i * 16 + 9) / length, 1)
            d.line(
                (
                    sc(x0 + (x1 - x0) * t0),
                    sc(y0 + (y1 - y0) * t0),
                    sc(x0 + (x1 - x0) * t1),
                    sc(y0 + (y1 - y0) * t1),
                ),
                fill=color + (255,),
                width=sc(width),
            )
    if head:
        (x0, y0), (x1, y1) = segs[-1]
        dx, dy = (x1 > x0) - (x1 < x0), (y1 > y0) - (y1 < y0)
        s = 11
        if dx:
            poly = [(x1, y1), (x1 - dx * 2 * s, y1 - s), (x1 - dx * 2 * s, y1 + s)]
        else:
            poly = [(x1, y1), (x1 - s, y1 - dy * 2 * s), (x1 + s, y1 - dy * 2 * s)]
        d.polygon([(sc(x), sc(y)) for x, y in poly], fill=color + (255,))


def centered(d, cx, cy, text, size, bold=False, fill=WHITE, gap=6):
    lines = text.split("\n")
    f = font(size, bold)
    total = len(lines) * size + (len(lines) - 1) * gap
    y = cy - total / 2 + size / 2
    for ln in lines:
        d.text((sc(cx), sc(y)), ln, font=f, fill=fill, anchor="mm")
        y += size + gap


def header(img, title, subtitle):
    d = ImageDraw.Draw(img)
    d.text((sc(60), sc(78)), title, font=font(52, True), fill=WHITE, anchor="ls")
    d.text((sc(62), sc(118)), subtitle, font=font(24), fill=SOFT, anchor="ls")
    return img


def legend(img, y, items):
    d = ImageDraw.Draw(img)
    x = 60
    for color, label in items:
        d.rounded_rectangle((sc(x), sc(y), sc(x + 26), sc(y + 26)), radius=sc(7), fill=color + (255,))
        d.text((sc(x + 38), sc(y + 13)), label, font=font(21), fill=SOFT, anchor="lm")
        x += 38 + d.textlength(label, font=font(21)) / mt.S + 44
    return img


def tag(d, x, y, text, color):
    f = font(19, True)
    w = d.textlength(text, font=f) / mt.S + 28
    d.rounded_rectangle(
        (sc(x), sc(y), sc(x + w), sc(y + 36)),
        radius=sc(18),
        fill=mix(color, 0.55) + (255,),
        outline=color + (255,),
        width=sc(2),
    )
    d.text((sc(x + 14), sc(y + 18)), text, font=f, fill=WHITE, anchor="lm")


# ------------------------------------------------------------------ architecture


def architecture():
    img = mt.background()
    img = header(
        img,
        "Architecture",
        "Models propose, code verifies and scores. All LLM calls go to Nebius Token Factory.",
    )

    # Left column
    for box, _title, _sub in [
        ((60, 170, 380, 270), "Clinic staff", "browser"),
        ((60, 320, 380, 430), "Streamlit UI", "check · fill gaps · letter"),
        ((60, 480, 380, 590), "FastAPI", "/assess  /recheck  /letter"),
        ((60, 860, 380, 1090), "", ""),
    ]:
        img = glass(img, box, radius=24)
    # Pipeline box
    img = glass(img, (450, 150, 1110, 1100), radius=30, fill=(255, 255, 255, 18))
    # Right column
    img = glass(img, (1190, 150, 1740, 570), radius=30, fill=(46, 190, 80, 24), outline=GREEN + (150,))
    img = glass(img, (1190, 620, 1740, 860), radius=30, fill=(60, 195, 225, 24), outline=CYAN + (150,))
    img = glass(img, (1190, 910, 1740, 1100), radius=30)

    d = ImageDraw.Draw(img)
    centered(d, 220, 211, "Clinic staff", 28, True)
    centered(d, 220, 241, "browser", 20, fill=SOFT)
    centered(d, 220, 362, "Streamlit UI", 28, True)
    centered(d, 220, 398, "check · fill gaps · letter", 20, fill=SOFT)
    centered(d, 220, 522, "FastAPI", 28, True)
    centered(d, 220, 558, "/assess · /recheck · /letter", 20, fill=SOFT)
    centered(d, 220, 905, "Outputs", 28, True)
    for i, line in enumerate(
        ["Readiness score (code)", "Criteria checklist + quotes", "Draft letter + request PDF"]
    ):
        centered(d, 220, 960 + i * 38, line, 21, fill=SOFT)

    d.text((sc(480), sc(196)), "AuthAssist pipeline", font=font(30, True), fill=WHITE, anchor="ls")
    d.text((sc(485), sc(226)), "Python package: authassist/", font=font(20), fill=SOFT, anchor="ls")
    rows = [
        ("Ingest note", "text · PDF · fax image", "Nemotron VL", GREEN),
        ("Extract facts", "spans verified in note", "Nemotron Nano", GREEN),
        ("Find payer policy", "domain-restricted, cached", "Tavily", CYAN),
        ("Policy to criteria", "atomic, checkable rules", "Nemotron Ultra", GREEN),
        ("Match evidence", "verbatim quote per criterion", "Nemotron Ultra", GREEN),
        ("Verify + score", "gap-fill re-runs 2 + 5", "pure code", AMBER),
        ("Letter + PDF", "verified facts only", "Ultra + ReportLab", GREEN),
    ]
    y = 262
    for i, (title, sub, who, color) in enumerate(rows, start=1):
        d.rounded_rectangle(
            (sc(480), sc(y), sc(1080), sc(y + 100)),
            radius=sc(20),
            fill=mix(color, 0.16) + (255,),
            outline=color + (210,),
            width=sc(2),
        )
        d.ellipse((sc(498), sc(y + 28), sc(542), sc(y + 72)), fill=color + (255,))
        d.text((sc(520), sc(y + 51)), str(i), font=font(24, True), fill=INK, anchor="mm")
        d.text((sc(562), sc(y + 38)), title, font=font(26, True), fill=WHITE, anchor="lm")
        d.text((sc(562), sc(y + 72)), sub, font=font(19), fill=SOFT, anchor="lm")
        tag(d, 1080 - 24 - (d.textlength(who, font=font(19, True)) / mt.S + 28), y + 32, who, color)
        y += 118

    # Token Factory
    d.text(
        (sc(1220), sc(200)), "Nebius Token Factory", font=font(32, True), fill=(150, 235, 155), anchor="ls"
    )
    d.text(
        (sc(1222), sc(232)),
        "steps 1 · 2 · 4 · 5 · 7 · retries · fallback · trace",
        font=font(19),
        fill=SOFT,
        anchor="ls",
    )
    for i, (role, model, use) in enumerate(
        [
            ("vision", "nvidia/Nemotron-3.5-Super-VL", "reads faxed scans"),
            ("fast", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B", "extraction · short asks"),
            ("reasoning", "nvidia/Nemotron-3-Ultra-550b-a55b", "criteria · matching · letter"),
        ]
    ):
        yy = 262 + i * 100
        d.rounded_rectangle(
            (sc(1215), sc(yy), sc(1715), sc(yy + 86)),
            radius=sc(16),
            fill=mix(GREEN, 0.2) + (255,),
            outline=GREEN + (200,),
            width=sc(2),
        )
        d.text((sc(1235), sc(yy + 26)), role.upper(), font=font(19, True), fill=(150, 235, 155), anchor="lm")
        d.text((sc(1375), sc(yy + 26)), use, font=font(19), fill=SOFT, anchor="lm")
        d.text((sc(1235), sc(yy + 60)), model, font=font(21, False, True), fill=WHITE, anchor="lm")

    d.text((sc(1220), sc(668)), "Tavily", font=font(32, True), fill=(130, 220, 240), anchor="ls")
    centered(d, 1465, 750, "search (advanced, include_domains)\nextract (full policy text)", 22, fill=SOFT)
    d.text((sc(1220), sc(958)), "Local storage", font=font(30, True), fill=WHITE, anchor="ls")
    centered(
        d,
        1465,
        1030,
        "policy cache (.cache, git-ignored)\ncriteria snapshots (committed) · model trace",
        21,
        fill=SOFT,
    )

    # Arrows
    arrow(d, [(220, 270), (220, 320)])
    arrow(d, [(220, 430), (220, 480)])
    arrow(d, [(380, 375), (450, 375)])
    arrow(d, [(380, 535), (450, 535)])
    arrow(d, [(450, 975), (380, 975)])
    arrow(d, [(1110, 360), (1190, 360)], GREEN)
    arrow(d, [(1190, 440), (1110, 440)], GREEN)
    arrow(d, [(1080, 528), (1145, 528), (1145, 715), (1190, 715)], CYAN)
    arrow(d, [(1190, 775), (1125, 775), (1125, 572), (1080, 572)], CYAN)
    d.text((sc(1220), sc(805)), "used by step 3", font=font(19), fill=(130, 220, 240), anchor="lm")
    arrow(d, [(1110, 990), (1190, 990)], (185, 198, 224))
    arrow(d, [(1190, 1040), (1110, 1040)], (185, 198, 224))

    img = legend(
        img, 1130, [(GREEN, "Nemotron on Token Factory"), (CYAN, "Tavily"), (AMBER, "Pure code (no LLM)")]
    )
    return img


# ------------------------------------------------------------------ swimlane

LANES = [
    ("Clinic staff", BLUE),
    ("AuthAssist\n(code)", AMBER),
    ("Nemotron on\nToken Factory", GREEN),
    ("Tavily", CYAN),
    ("Clinician", PURPLE),
]
LANE_Y0, LANE_H = 150, 198
COL_X0, COL_PITCH, BOX_W, BOX_H = 256, 150, 142, 104


def box_pos(col, lane):
    x = COL_X0 + col * COL_PITCH
    y = LANE_Y0 + lane * LANE_H + (LANE_H - BOX_H) / 2
    return x, y


def swimlane():
    img = mt.background()
    img = header(
        img,
        "Swimlane",
        "Who does what, step by step. The gap-fill loop re-runs extraction and matching only.",
    )
    for i in range(len(LANES)):
        img = glass(
            img,
            (40, LANE_Y0 + i * LANE_H + 4, 1760, LANE_Y0 + (i + 1) * LANE_H - 4),
            radius=22,
            fill=(255, 255, 255, 12),
            outline=(255, 255, 255, 40),
        )
    d = ImageDraw.Draw(img)
    for i, (name, color) in enumerate(LANES):
        cy = LANE_Y0 + i * LANE_H + LANE_H / 2
        d.rounded_rectangle(
            (sc(56), sc(cy - 40), sc(236), sc(cy + 40)),
            radius=sc(18),
            fill=mix(color, 0.5) + (255,),
            outline=color + (255,),
            width=sc(2),
        )
        centered(d, 146, cy, name, 22, True, gap=4)

    steps = [  # (col, lane, text)
        (0, 0, "Upload note,\npick insurer"),
        (1, 1, "Ingest note\n(any format)"),
        (2, 2, "Vision model\nreads the fax"),
        (3, 2, "Extract facts\n(Nano)"),
        (4, 3, "Search +\nextract policy"),
        (5, 2, "Policy to\ncriteria (Ultra)"),
        (6, 2, "Match evidence\nquotes (Ultra)"),
        (7, 1, "Verify quotes,\ncompute score"),
        (8, 0, "Add addendum,\nre-check"),
        (8, 2, "Draft letter\n(Ultra)"),
        (9, 1, "Build request\nPDF"),
        (9, 4, "Review\n& sign"),
    ]
    centers = {}
    for n, (col, lane, _) in enumerate(steps, start=1):
        x, y = box_pos(col, lane)
        centers[n] = (x, y)

    def right(n):
        x, y = centers[n]
        return x + BOX_W, y + BOX_H / 2

    def left(n):
        x, y = centers[n]
        return x, y + BOX_H / 2

    def top(n):
        x, y = centers[n]
        return x + BOX_W / 2, y

    def bottom(n):
        x, y = centers[n]
        return x + BOX_W / 2, y + BOX_H

    def elbow(a, b):
        (x0, y0), (x1, y1) = right(a), left(b)
        mid = (x0 + x1) / 2
        return [(x0, y0), (mid, y0), (mid, y1), (x1, y1)]

    # connectors first (under boxes)
    for a, b in [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (8, 9)]:
        arrow(d, elbow(a, b))
    arrow(d, [bottom(9), (bottom(9)[0], top(10)[1])], (185, 198, 224))  # staff -> draft letter (ready)
    arrow(d, elbow(10, 11))
    arrow(d, [bottom(11), (bottom(11)[0], top(12)[1])])
    # Tavily returns policy to the criteria step
    # gap-fill loop: addendum -> extract facts (dashed)
    x9, y9 = top(9)
    x4, y4 = top(4)
    loop_y = LANE_Y0 + 30
    arrow(d, [(x9, y9), (x9, loop_y), (x4, loop_y), (x4, y4)], AMBER, dashed=True)
    d.text(
        (sc((x9 + x4) / 2), sc(loop_y - 14)),
        "gap-fill loop: re-run extract (4) + match (7)",
        font=font(20, True),
        fill=AMBER,
        anchor="mm",
    )
    d.text(
        (sc(centers[9][0] + BOX_W / 2 + 8), sc(centers[9][1] + BOX_H + 34)),
        "when ready",
        font=font(18),
        fill=SOFT,
        anchor="lm",
    )

    # boxes
    bl = layer()
    bd = ImageDraw.Draw(bl)
    for n, (_col, lane, _) in enumerate(steps, start=1):
        x, y = centers[n]
        color = LANES[lane][1]
        bd.rounded_rectangle(
            (sc(x), sc(y), sc(x + BOX_W), sc(y + BOX_H)),
            radius=sc(16),
            fill=mix(color, 0.3) + (255,),
            outline=color + (255,),
            width=sc(3),
        )
    img = Image.alpha_composite(img, bl)
    d = ImageDraw.Draw(img)
    for n, (_col, lane, text) in enumerate(steps, start=1):
        x, y = centers[n]
        color = LANES[lane][1]
        centered(d, x + BOX_W / 2, y + BOX_H / 2 + 8, text, 16, True, gap=4)
        d.ellipse(
            (sc(x - 12), sc(y - 12), sc(x + 18), sc(y + 18)),
            fill=color + (255,),
            outline=INK + (255,),
            width=sc(2),
        )
        d.text((sc(x + 3), sc(y + 3)), str(n), font=font(17, True), fill=INK, anchor="mm")

    img = legend(
        img,
        1150,
        [
            (AMBER, "Code only (verification, scoring, PDF)"),
            (GREEN, "Nemotron via Token Factory"),
            (CYAN, "Tavily"),
            (BLUE, "Human steps"),
        ],
    )
    return img


def save(img, name):
    out = mt.OUT.parent / name
    img.convert("RGB").resize((mt.W, mt.H), Image.LANCZOS).save(out, optimize=True)
    print(out, out.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    save(architecture(), "architecture.png")
    save(swimlane(), "swimlane.png")
