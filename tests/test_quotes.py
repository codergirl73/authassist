from authassist.matcher import normalize, quote_in_note, verify_results
from authassist.schemas import CriterionResult

NOTE = "HPI: 47-year-old male.\nCompleted 8 weeks of physical\ntherapy (2x/week) with minimal improvement."


def test_normalize():
    assert normalize("  “Hello” \n  World. ") == 'hello" world'  # edge quotes/punctuation trimmed


def test_quote_matching_ignores_whitespace_and_case():
    assert quote_in_note("completed 8 weeks of PHYSICAL therapy", NOTE)
    assert quote_in_note("Completed 8 weeks of physical therapy (2x/week) with minimal improvement.", NOTE)


def test_paraphrase_is_rejected():
    assert not quote_in_note("Completed eight weeks of PT", NOTE)
    assert not quote_in_note("", NOTE)
    assert not quote_in_note(None, NOTE)


def test_unverified_met_is_downgraded():
    results = [
        CriterionResult(criterion_id="a", status="met", evidence_quote="8 weeks of physical therapy"),
        CriterionResult(criterion_id="b", status="met", evidence_quote="12 weeks of chiropractic care"),
        CriterionResult(criterion_id="c", status="met", evidence_quote=None),
        CriterionResult(criterion_id="d", status="missing", evidence_quote=None),
    ]
    out = {r.criterion_id: r for r in verify_results(results, NOTE)}
    assert out["a"].status == "met" and out["a"].quote_verified
    assert out["b"].status == "unclear" and not out["b"].quote_verified
    assert out["c"].status == "unclear"
    assert out["d"].status == "missing"
