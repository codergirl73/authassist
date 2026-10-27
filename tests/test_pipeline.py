"""End-to-end pipeline with fake LLM + snapshot policy (no network)."""

import io
import json
from pathlib import Path

from pypdf import PdfReader

from authassist import pipeline
from authassist.cli import load_case

CASES = Path(__file__).resolve().parent.parent / "data" / "synthetic_notes"


def facts_reply(messages, model):
    return {
        "chief_complaint": "Low back pain",
        "requested_procedure": "MRI lumbar spine",
        "source_spans": {"chief_complaint": "low back pain", "bogus": "this text is not in the note"},
    }


def match_reply(statuses_and_quotes):
    def reply(messages, model):
        crit_ids = [
            c["criterion_id"]
            for c in json.loads(messages[1]["content"].split("CRITERIA:\n")[1].split("\n\nEXTRACTED")[0])
        ]
        results = []
        for cid in crit_ids:
            status, quote = statuses_and_quotes.get(cid, ("missing", None))
            results.append(
                {
                    "criterion_id": cid,
                    "status": status,
                    "evidence_quote": quote,
                    "reasoning": "r",
                    "quote_verified": True,
                }
            )
        return {"results": results}

    return reply


def setup(fake, matches):
    fake.on("web search queries", {"queries": ["q"]})
    fake.on("extract structured clinical facts", facts_reply)
    fake.on("prior-authorization documentation reviewer", match_reply(matches))
    fake.on("documentation gaps", {"items": ["Add dates and duration of physical therapy"]})
    fake.on(
        "letter of medical necessity",
        {
            "body_markdown": "To whom it may concern,\n\n**Request** for MRI.\n\n- point one\n\n[Signature]",
            "citations": [],
        },
    )
    fake.on(
        "Transcribe this clinical note",
        lambda m, model: (CASES / "case_07" / "reference_text.txt").read_text(),
    )


def test_case_01_ready(fake_llm):
    setup(
        fake_llm,
        {
            "symptom_duration": ("met", "low back pain for 10 weeks"),
            "conservative_therapy_6wk": ("met", "Completed 8 weeks of physical therapy"),
            "neuro_exam_documented": ("met", "left Achilles reflex diminished (1+)"),
            "no_recent_duplicate_imaging": ("met", "No prior lumbar imaging."),
        },
    )
    r = pipeline.run_pipeline(load_case(CASES / "case_01"))
    a = r.assessment
    assert (a.readiness_score, a.status, a.red_flag_bypass) == (100, "ready", False)
    assert all(x.quote_verified for x in a.results if x.evidence_quote)
    assert "bogus" not in r.facts.source_spans  # unverifiable span dropped
    assert any("source span" in w for w in r.warnings)
    assert r.policy_notice and "snapshot" in r.policy_notice
    assert {e.role for e in r.traces} >= {"fast", "reasoning"}


def test_hallucinated_quote_is_downgraded(fake_llm):
    setup(
        fake_llm,
        {
            "symptom_duration": ("met", "low back pain for 10 weeks"),
            "conservative_therapy_6wk": ("met", "Completed 12 weeks of chiropractic care"),  # not in note
            "neuro_exam_documented": ("met", "left Achilles reflex diminished (1+)"),
            "no_recent_duplicate_imaging": ("met", "No prior lumbar imaging."),
        },
    )
    a = pipeline.run_pipeline(load_case(CASES / "case_01")).assessment
    ct = next(x for x in a.results if x.criterion_id == "conservative_therapy_6wk")
    assert ct.status == "unclear" and not ct.quote_verified
    assert a.status == "needs_attention"


def test_case_07_scan_red_flag_bypass(fake_llm):
    setup(
        fake_llm,
        {
            "neuro_exam_documented": (
                "met",
                "decreased sensation in the perineal region (saddle anesthesia)",
            ),
            "no_recent_duplicate_imaging": ("met", "PRIOR IMAGING: None."),
            "rf_cauda_equina": ("met", "New urinary retention since yesterday"),
        },
    )
    r = pipeline.run_pipeline(load_case(CASES / "case_07"))
    assert r.ingest_method == "vision"
    assert any(e.role == "vision" for e in r.traces)
    assert r.assessment.red_flag_bypass and r.assessment.status == "ready"


def test_addendum_recheck_and_pdf(fake_llm):
    before = {
        "neuro_exam_documented": ("met", "Neuro exam: strength 5/5"),
        "no_recent_duplicate_imaging": ("met", "PRIOR IMAGING: None."),
    }
    setup(fake_llm, before)
    case = load_case(CASES / "case_04")
    case.note_text, case.file_bytes = (CASES / "case_04" / "reference_text.txt").read_text(), None
    first = pipeline.run_pipeline(case)
    assert first.assessment.status == "not_ready"

    fake_llm.handlers.clear()
    setup(
        fake_llm,
        {
            **before,
            "symptom_duration": ("met", "low back pain for 9 weeks"),
            "conservative_therapy_6wk": ("met", "8 weeks of physical therapy from 08/20/2026 to 10/15/2026"),
        },
    )
    second = pipeline.recheck_with_addendum(
        first,
        "Correction: low back pain for 9 weeks. Completed 8 weeks of physical therapy from 08/20/2026 to 10/15/2026.",
    )
    assert "--- ADDENDUM (entered by clinician on" in second.note_text
    assert second.previous_score == first.assessment.readiness_score
    assert second.assessment.readiness_score > first.assessment.readiness_score
    assert second.assessment.status == "ready"

    letter, pdf_bytes, traces = pipeline.make_letter(second)
    assert letter.body_markdown.startswith("**DRAFT")
    assert pdf_bytes[:4] == b"%PDF"
    text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf_bytes)).pages)
    for needle in [
        "Criteria checklist",
        "Letter of medical necessity",
        "Policy source",
        "aetna.com",
        "verified in note",
    ]:
        assert needle in text


def test_pdf_text_is_sanitised_for_helvetica():
    from authassist.pdf import pdf_safe

    raw = "36‑year‑old, ≥ 6 weeks 【Background - https://x.y】 → ok"
    out = pdf_safe(raw)
    assert out == "36-year-old, >= 6 weeks [Background - https://x.y] -> ok"
    assert out.encode("cp1252")  # everything left is drawable


def test_pdf_markdown_keeps_line_breaks():
    from reportlab.lib.styles import getSampleStyleSheet

    from authassist.pdf import markdown_flowables

    flow = markdown_flowables("[Clinician Name]\n[Clinician NPI]\n\nNext paragraph", getSampleStyleSheet())
    assert len(flow) == 2
    assert "<br/>" in flow[0].text and "Clinician NPI" in flow[0].text
