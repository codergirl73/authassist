"""Generate the 8 synthetic cases in data/synthetic_notes/.

Cases 04 and 07 are rendered as scanned-style PNGs (rotated, grayscale, noisy)
to exercise the vision step; their source text is kept as reference_text.txt
for evaluation only (the pipeline never reads it).

Usage: python scripts/make_synthetic_cases.py
"""

import json
import random
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "synthetic_notes"
BANNER = "*** SYNTHETIC - NOT A REAL PATIENT ***"

HEADER = """{banner}
Riverside Family Medicine (fictional clinic)
Patient: Test Patient {n:02d}    MRN: SYN-{n:04d}    DOB: {dob}
Visit date: {visit}    Provider: Dr. Example Clinician, MD
"""

CASES = [
    {
        "n": 1,
        "payer": "aetna",
        "dob": "1979-04-12",
        "visit": "2026-10-14",
        "scenario": "8 weeks PT + NSAIDs documented, neuro exam documented",
        "expected": {
            "outcome": "ready",
            "red_flag_bypass": False,
            "criteria": {
                "symptom_duration": "met",
                "conservative_therapy": "met",
                "neuro_exam": "met",
                "red_flag": "missing",
            },
        },
        "body": """
CHIEF COMPLAINT: Low back pain radiating to the left leg.

HPI: 47-year-old male with low back pain for 10 weeks, onset after lifting boxes at home.
Pain radiates to the left buttock and posterior thigh. Completed 8 weeks of physical therapy
(2x/week, 08/10/2026 to 10/05/2026) with minimal improvement. Has taken naproxen 500 mg
twice daily for 8 weeks without adequate relief. Pain 7/10, limits work as a warehouse lead.
Denies bowel or bladder changes, saddle numbness, fever, weight loss, or history of cancer.

PRIOR IMAGING: No prior lumbar imaging.

EXAM: Lumbar paraspinal tenderness. Straight leg raise positive on the left at 40 degrees.
Neuro: Strength 5/5 bilateral lower extremities except 4+/5 left ankle plantarflexion.
Reflexes: left Achilles reflex diminished (1+), right 2+. Sensation decreased over the
left lateral foot.

ASSESSMENT: Lumbar radiculopathy, left S1 distribution (M54.17). Failed 8 weeks of
conservative therapy.

PLAN: Request MRI lumbar spine without contrast (CPT 72148) to evaluate for disc herniation
and guide possible epidural steroid injection referral.
""",
    },
    {
        "n": 2,
        "payer": "molina",
        "dob": "1985-09-30",
        "visit": "2026-10-09",
        "scenario": "7 weeks conservative care, radiculopathy findings",
        "expected": {
            "outcome": "ready",
            "red_flag_bypass": False,
            "criteria": {
                "symptom_duration": "met",
                "conservative_therapy": "met",
                "neuro_exam": "met",
                "red_flag": "missing",
            },
        },
        "body": """
CHIEF COMPLAINT: Back pain with right leg numbness.

HPI: 41-year-old female with low back pain and right leg pain for 9 weeks. She has had
7 weeks of conservative care: physical therapy started 08/21/2026 (12 sessions to date) and
ibuprofen 600 mg three times daily since 08/18/2026, plus a daily home exercise program.
Symptoms persist and now include numbness on the top of the right foot.
No urinary retention, no saddle anesthesia, no fever, no trauma, no cancer history.

PRIOR IMAGING: None.

EXAM: Gait antalgic. Neuro exam: right extensor hallucis longus weakness 4/5; sensation
diminished in the right L5 dermatome; reflexes symmetric 2+. Positive straight leg raise
on the right at 45 degrees.

ASSESSMENT: Right L5 radiculopathy (M54.16) persisting despite 7 weeks of conservative
treatment.

PLAN: MRI lumbar spine without contrast (CPT 72148). Continue PT pending results.
""",
    },
    {
        "n": 3,
        "payer": "medicare",
        "dob": "1957-02-03",
        "visit": "2026-10-16",
        "scenario": "Persistent pain after PT, prior X-ray, good documentation",
        "expected": {
            "outcome": "ready",
            "red_flag_bypass": False,
            "criteria": {
                "symptom_duration": "met",
                "conservative_therapy": "met",
                "neuro_exam": "met",
                "prior_imaging": "met",
                "red_flag": "missing",
            },
        },
        "body": """
CHIEF COMPLAINT: Persistent low back pain and bilateral leg heaviness with walking.

HPI: 69-year-old male with low back pain for 4 months. Completed 10 weeks of physical
therapy (07/01/2026 to 09/09/2026) and took acetaminophen 1 g three times daily and
meloxicam 15 mg daily for 8 weeks, with no meaningful improvement. Reports bilateral leg
heaviness after walking two blocks, relieved by sitting (neurogenic claudication).
Denies bowel/bladder dysfunction, saddle anesthesia, fever, or unexplained weight loss.

PRIOR IMAGING: Lumbar spine X-ray 06/20/2026: multilevel degenerative disc disease,
facet arthropathy L4-L5, no fracture. No prior MRI.

EXAM: Neurological exam: strength 5/5 throughout lower extremities; patellar and Achilles
reflexes 1+ and symmetric; sensation intact to light touch; negative straight leg raise.
Pain reproduced with lumbar extension.

ASSESSMENT: Suspected lumbar spinal stenosis (M48.062) with neurogenic claudication,
failed conservative management.

PLAN: MRI lumbar spine without contrast (CPT 72148) for evaluation of stenosis prior to
spine surgery consultation.
""",
    },
    {
        "n": 4,
        "payer": "aetna",
        "dob": "1990-06-21",
        "visit": "2026-10-20",
        "scanned": True,
        "scenario": "Pain 3 weeks, no conservative therapy, no red flags",
        "expected": {
            "outcome": "not_ready",
            "red_flag_bypass": False,
            "criteria": {
                "symptom_duration": "missing",
                "conservative_therapy": "missing",
                "neuro_exam": "met",
                "red_flag": "missing",
            },
        },
        "body": """
CHIEF COMPLAINT: Low back pain.

HPI: 36-year-old male with low back pain for 3 weeks after yard work.
Pain is aching, 6/10, worse with bending. No radiation.
No treatment tried yet. Patient requests an MRI.
Denies numbness, weakness, bowel or bladder changes, fever, weight loss.
No history of cancer or trauma.

PRIOR IMAGING: None.

EXAM: Mild lumbar paraspinal tenderness. Neuro exam: strength 5/5,
reflexes 2+ symmetric, sensation intact. Negative straight leg raise.

ASSESSMENT: Acute low back pain, nonspecific (M54.50).

PLAN: Patient requests MRI lumbar spine without contrast (CPT 72148).
""",
    },
    {
        "n": 5,
        "payer": "molina",
        "dob": "1972-11-08",
        "visit": "2026-10-13",
        "scenario": "PT mentioned but no duration/dates",
        "expected": {
            "outcome": "needs_attention",
            "red_flag_bypass": False,
            "criteria": {
                "symptom_duration": "met",
                "conservative_therapy": "unclear",
                "neuro_exam": "met",
                "red_flag": "missing",
            },
        },
        "body": """
CHIEF COMPLAINT: Ongoing low back pain with left leg tingling.

HPI: 53-year-old female with low back pain for about 3 months. She did some physical
therapy and has been taking over-the-counter pain relievers. Still has pain 6/10 and
intermittent tingling down the left leg. No bowel or bladder symptoms, no saddle
numbness, no fever, no weight loss, no prior cancer.

PRIOR IMAGING: None.

EXAM: Neuro exam: strength 5/5 bilaterally, reflexes 2+ and symmetric, decreased light-touch
sensation over the left lateral calf. Straight leg raise positive on the left at 60 degrees.

ASSESSMENT: Low back pain with left lumbar radiculopathy (M54.16).

PLAN: MRI lumbar spine without contrast (CPT 72148).
""",
    },
    {
        "n": 6,
        "payer": "aetna",
        "dob": "1968-03-17",
        "visit": "2026-10-07",
        "scenario": "No neuro exam documented",
        "expected": {
            "outcome": "not_ready",
            "red_flag_bypass": False,
            "criteria": {
                "symptom_duration": "met",
                "conservative_therapy": "met",
                "neuro_exam": "missing",
                "red_flag": "missing",
            },
        },
        "body": """
VISIT TYPE: Telephone follow-up.

CHIEF COMPLAINT: Chronic low back pain, not improving.

HPI: 58-year-old male with low back pain for 12 weeks. Completed physical therapy for
6 weeks (08/04/2026 to 09/15/2026) and took diclofenac 75 mg twice daily for 6 weeks.
Pain unchanged at 7/10 with occasional pain into the right thigh. Denies bladder or bowel
problems, fever, weight loss, or cancer history.

PRIOR IMAGING: No prior lumbar imaging.

ASSESSMENT: Chronic low back pain with possible right-sided radicular symptoms (M54.41).

PLAN: Order MRI lumbar spine without contrast (CPT 72148). In-person visit to be scheduled.
""",
    },
    {
        "n": 7,
        "payer": "aetna",
        "dob": "1981-08-25",
        "visit": "2026-10-21",
        "scanned": True,
        "scenario": "Saddle anesthesia + new urinary retention (cauda equina), symptoms 1 week",
        "expected": {
            "outcome": "ready",
            "red_flag_bypass": True,
            "criteria": {"neuro_exam": "met", "red_flag": "met"},
        },
        "body": """
CHIEF COMPLAINT: Severe low back pain, numbness in groin, trouble urinating.

HPI: 45-year-old female with low back pain for 1 week, sudden worsening 2 days ago.
New urinary retention since yesterday; needed straight catheterization in urgent care
with 650 mL residual. Reports numbness in the groin and buttocks (saddle anesthesia).
Bilateral leg weakness. No treatment tried yet given acute onset.

PRIOR IMAGING: None.

EXAM: Neuro exam: decreased sensation in the perineal region (saddle anesthesia).
Bilateral ankle dorsiflexion 4/5. Achilles reflexes absent bilaterally.
Decreased rectal tone.

ASSESSMENT: Suspected cauda equina syndrome (G83.4). Red flag - emergent imaging.

PLAN: Urgent MRI lumbar spine without contrast (CPT 72148). Neurosurgery notified.
""",
    },
    {
        "n": 8,
        "payer": "molina",
        "dob": "1960-12-02",
        "visit": "2026-10-15",
        "scenario": "History of cancer + unexplained weight loss, 2 weeks pain",
        "expected": {
            "outcome": "ready",
            "red_flag_bypass": True,
            "criteria": {"neuro_exam": "met", "red_flag": "met"},
        },
        "body": """
CHIEF COMPLAINT: New low back pain, worse at night.

HPI: 65-year-old male with new low back pain for 2 weeks, constant, worse at night and
not relieved by rest. History of prostate cancer treated with radiation in 2019.
Unexplained weight loss of 12 lbs over the past 2 months. No trauma. No fever.
No bowel or bladder changes. Has not started any treatment.

PRIOR IMAGING: None.

EXAM: Focal midline tenderness over L3 spinous process. Neuro exam: strength 5/5,
reflexes 2+ symmetric, sensation intact.

ASSESSMENT: Low back pain with history of malignancy and unexplained weight loss;
suspected spinal metastasis (M54.50, Z85.46). Red flag.

PLAN: MRI lumbar spine without contrast (CPT 72148). PSA ordered.
""",
    },
]


def note_text(case: dict) -> str:
    head = HEADER.format(banner=BANNER, n=case["n"], dob=case["dob"], visit=case["visit"])
    return f"{head}{textwrap.dedent(case['body']).rstrip()}\n\n{BANNER}\n"


def _font(size: int):
    for path in [
        "/System/Library/Fonts/Courier.ttc",
        "/System/Library/Fonts/Supplemental/Courier New.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ]:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def render_scan(text: str, seed: int) -> Image.Image:
    rng = random.Random(seed)
    font = _font(22)
    lines = text.splitlines()
    img = Image.new("L", (1275, 60 + 30 * len(lines) + 60), 250)
    draw = ImageDraw.Draw(img)
    draw.text((70, 20), "FAX  10/2026  p.1/1", font=_font(16), fill=90)
    for i, line in enumerate(lines):
        draw.text((70 + rng.randint(-2, 2), 60 + 30 * i), line, font=font, fill=rng.randint(15, 45))
    img = img.rotate(rng.uniform(-1.4, 1.4), resample=Image.BICUBIC, expand=True, fillcolor=245)
    px = img.load()
    w, h = img.size
    for _ in range(w * h // 60):  # speckle noise
        x, y = rng.randrange(w), rng.randrange(h)
        px[x, y] = rng.choice([0, 60, 200, 255])
    return img.filter(ImageFilter.GaussianBlur(0.6))


def main() -> None:
    for case in CASES:
        d = OUT / f"case_{case['n']:02d}"
        d.mkdir(parents=True, exist_ok=True)
        for stale in ("note.txt", "note.png", "reference_text.txt"):
            (d / stale).unlink(missing_ok=True)
        text = note_text(case)
        if case.get("scanned"):
            render_scan(text, seed=case["n"]).save(d / "note.png")
            (d / "reference_text.txt").write_text(text)
        else:
            (d / "note.txt").write_text(text)
        (d / "case.json").write_text(
            json.dumps(
                {
                    "case_id": f"case_{case['n']:02d}",
                    "payer": case["payer"],
                    "procedure": "lumbar_mri",
                    "scenario": case["scenario"],
                    "input": "scanned_png" if case.get("scanned") else "text",
                },
                indent=2,
            )
        )
        (d / "expected.json").write_text(json.dumps(case["expected"], indent=2))
        print(f"wrote {d.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
