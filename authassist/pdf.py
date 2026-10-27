"""Step 7b: request-summary PDF (summary, checklist, letter, policy source)."""

from __future__ import annotations

import io
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter as LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from authassist.letter import DRAFT_HEADER
from authassist.schemas import Assessment, LetterDraft

STATUS_LABEL = {"met": "MET", "unclear": "UNCLEAR", "missing": "MISSING"}
STATUS_COLOR = {
    "met": colors.HexColor("#1b7f3b"),
    "unclear": colors.HexColor("#b26a00"),
    "missing": colors.HexColor("#b3261e"),
}


_PDF_CHARS = {
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2212": "-",  # hyphen variants the model likes
    "\u3010": "[",
    "\u3011": "]",
    "\u300c": '"',
    "\u300d": '"',  # CJK brackets used as citations
    "\u2265": ">=",
    "\u2264": "<=",
    "\u2192": "->",
    "\u00a0": " ",
    "\u202f": " ",
    "\u2009": " ",
}


def pdf_safe(text: str) -> str:
    """Helvetica (WinAnsi) cannot draw many Unicode characters; map them, then drop anything left."""
    for bad, good in _PDF_CHARS.items():
        text = text.replace(bad, good)
    return text.encode("cp1252", errors="replace").decode("cp1252")


def _inline(text: str) -> str:
    text = escape(pdf_safe(text))
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    return re.sub(r"(?<!\*)\*(?!\*)(.+?)\*", r"<i>\1</i>", text)


def markdown_flowables(md: str, styles) -> list:
    out, para = [], []

    def flush():
        if para:
            out.append(
                Paragraph("<br/>".join(_inline(x) for x in para), styles["BodyText"])
            )  # keep address-block line breaks
            para.clear()

    for line in md.splitlines():
        s = line.strip()
        if not s:
            flush()
        elif s.startswith("#"):
            flush()
            out.append(Paragraph(_inline(s.lstrip("#").strip()), styles["Heading4"]))
        elif s[:2] in ("- ", "* "):
            flush()
            out.append(Paragraph(_inline(s[2:]), styles["BodyText"], bulletText="•"))
        else:
            para.append(s)
    flush()
    return out


def build_pdf(assessment: Assessment, letter: LetterDraft | None, case_id: str) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=LETTER,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title=f"AuthAssist - {case_id}",
    )
    styles = getSampleStyleSheet()
    small = ParagraphStyle("small", parent=styles["BodyText"], fontSize=8, leading=10)
    warn = ParagraphStyle("warn", parent=styles["BodyText"], textColor=colors.HexColor("#b3261e"))
    p = assessment.policy
    crit = {c.id: c for c in assessment.criteria}

    story = [
        Paragraph("AuthAssist - Prior Authorization Request Summary", styles["Title"]),
        Paragraph(f"<b>{DRAFT_HEADER}</b> Not submitted to any insurer. Synthetic data only.", warn),
        Spacer(1, 8),
        Table(
            [
                ["Case ID (synthetic)", case_id],
                ["Payer", assessment.payer],
                ["Procedure", assessment.procedure],
                ["CPT", "72148"],
                [
                    "Readiness score",
                    f"{assessment.readiness_score}/100 ({assessment.status.replace('_', ' ')})",
                ],
                ["Red-flag bypass", "Yes" if assessment.red_flag_bypass else "No"],
            ],
            colWidths=[1.8 * inch, 5.0 * inch],
            style=TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f2f5")),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            ),
        ),
        Spacer(1, 12),
        Paragraph("Criteria checklist", styles["Heading2"]),
    ]

    rows = [
        [
            Paragraph("<b>Criterion</b>", small),
            Paragraph("<b>Status</b>", small),
            Paragraph("<b>Evidence (verbatim from note)</b>", small),
        ]
    ]
    for r in assessment.results:
        c = crit[r.criterion_id]
        label = STATUS_LABEL[r.status]
        color = "#7a7f87" if c.bypass_group else STATUS_COLOR[r.status].hexval().replace("0x", "#")
        if c.bypass_group:
            label = "PRESENT" if r.status == "met" else "not present"
        quote = r.evidence_quote or "-"
        if r.evidence_quote:
            quote = f"“{r.evidence_quote}” " + (
                "(verified in note)" if r.quote_verified else "(NOT verified)"
            )
        rows.append(
            [
                Paragraph(
                    escape(pdf_safe(c.description))
                    + ("<br/><i>red-flag indication</i>" if c.bypass_group else ""),
                    small,
                ),
                Paragraph(f'<font color="{color}"><b>{label}</b></font>', small),
                Paragraph(escape(pdf_safe(quote)), small),
            ]
        )
    table = Table(rows, colWidths=[2.6 * inch, 0.9 * inch, 3.3 * inch], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f2f5")),
            ]
        )
    )
    story += [table, Spacer(1, 8)]

    if assessment.missing_items:
        story.append(Paragraph("Missing documentation", styles["Heading3"]))
        story += [
            Paragraph(escape(pdf_safe(m)), styles["BodyText"], bulletText="•")
            for m in assessment.missing_items
        ]

    if letter:
        story += [Spacer(1, 12), Paragraph("Letter of medical necessity (draft)", styles["Heading2"])]
        story += markdown_flowables(letter.body_markdown, styles)

    source = {
        "tavily": "found via Tavily",
        "cache": "cached Tavily result",
        "snapshot": "cached criteria snapshot",
    }[p.source]
    story += [
        Spacer(1, 12),
        Paragraph("Policy source", styles["Heading2"]),
        Paragraph(
            f"{escape(p.title)}<br/>{escape(p.url)}<br/>Retrieved {p.retrieved_at:%Y-%m-%d} ({source})"
            + ("<br/>Medicare/CMS guidance used as fallback." if p.is_fallback else ""),
            small,
        ),
        Paragraph("Policies change; verify against the payer's current policy before submission.", small),
    ]
    doc.build(story)
    return buf.getvalue()
