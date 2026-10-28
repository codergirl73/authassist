"""Drive the Streamlit UI headlessly (fake LLM, snapshot policy)."""

from streamlit.testing.v1 import AppTest

from tests.test_pipeline import CASES, setup


def btn(at, text):
    return next(b for b in at.button if text in b.label)


def app(fake_llm):
    case04 = (CASES / "case_04" / "reference_text.txt").read_text()
    fake_llm.on("Transcribe this clinical note", case04)
    setup(fake_llm, {"neuro_exam_documented": ("met", "Neuro exam: strength 5/5")})
    at = AppTest.from_file("../ui/app.py", default_timeout=30)
    at.run()
    assert not at.exception
    return at


def test_full_ui_flow(fake_llm):
    at = app(fake_llm)
    assert at.session_state["view"] == "home"
    btn(at, "Start a check").click().run()
    assert at.session_state["view"] == "start"
    btn(at, "Run readiness check").click().run()  # case 04 (scanned fax) is preselected
    assert not at.exception and not at.error, [e.value for e in at.error]
    assert at.session_state["view"] == "review"
    md = " ".join(m.value for m in at.markdown)
    assert "Not ready" in md and "verified in note" in md and "Next: fix" in md

    btn(at, "Fix ").click().run()
    assert at.session_state["view"] == "fix"
    at.text_area[0].input("Low back pain for 9 weeks.")  # form values apply on submit, same run
    btn(at, "re-check").click().run()
    assert not at.exception, [e.value for e in at.error]
    result = at.session_state["result"]
    assert result.previous_score is not None and len(result.addenda) == 1
    assert at.session_state["view"] == "review"
    assert "went from" in " ".join(m.value for m in at.markdown)

    btn(at, "Skip to letter").click().run() if any("Skip to letter" in b.label for b in at.button) else btn(
        at, "Draft the letter"
    ).click().run()
    assert not at.exception, at.exception
    assert at.session_state["view"] == "letter"
    assert at.session_state["pdf"][:4] == b"%PDF"  # letter is drafted on entering the screen


def test_one_click_demo_runs_case_04(fake_llm):
    at = app(fake_llm)
    btn(at, "Run the demo in one click").click().run()
    assert not at.exception, at.exception
    assert at.session_state["view"] == "review"
    assert at.session_state["result"].case_id == "case_04"


def test_picking_a_case_and_back_navigation(fake_llm):
    at = app(fake_llm)
    btn(at, "Start a check").click().run()
    btn(at, "Use this note").click().run()  # first unselected card
    assert at.session_state["case_key"] != "case_04"
    btn(at, "How it works").click().run()
    assert at.session_state["view"] == "about"
    btn(at, "Back").click().run()
    assert at.session_state["view"] == "start"


def test_live_tavily_checkbox_forces_refresh(fake_llm, monkeypatch):
    from authassist import pipeline

    seen = {}
    real = pipeline.run_pipeline

    def spy(case, force_refresh=False, progress=None):
        seen["force_refresh"] = force_refresh
        return real(case, force_refresh=force_refresh, progress=progress)

    monkeypatch.setattr(pipeline, "run_pipeline", spy)
    at = app(fake_llm)
    btn(at, "Start a check").click().run()
    live = next(c for c in at.checkbox if "live via Tavily" in c.label)
    assert live.value is False
    live.check().run()
    btn(at, "Run readiness check").click().run()
    assert seen["force_refresh"] is True
    assert not at.exception


def test_annotate_note_highlights_verified_quotes():
    import importlib.util
    from pathlib import Path

    from authassist.schemas import Criterion, CriterionResult

    # import only the helper without executing the Streamlit page
    src = (Path(__file__).resolve().parent.parent / "ui" / "app.py").read_text()
    start = src.index("def annotate_note")
    end = src.index("def run_with_progress")
    ns = {"re": __import__("re"), "esc": __import__("html").escape}
    exec(src[start:end], ns)  # noqa: S102
    note = "HPI: pain for 10 weeks.\nCompleted 8 weeks of physical\ntherapy <b>x</b>."
    crit = {
        "a": Criterion(id="a", description="d", policy_citation="c"),
        "b": Criterion(id="b", description="e", policy_citation="c"),
    }
    results = [
        CriterionResult(
            criterion_id="a", status="met", evidence_quote="pain for 10 weeks", quote_verified=True
        ),
        CriterionResult(
            criterion_id="b", status="met", evidence_quote="8 weeks of physical therapy", quote_verified=True
        ),
    ]
    out, n = ns["annotate_note"](note, results, crit)
    assert n == 2 and out.count("<mark") == 2
    assert "&lt;b&gt;" in out and "<b>" not in out  # note text is HTML-escaped
    del importlib


def test_example_answers_button(fake_llm):
    at = app(fake_llm)
    btn(at, "Run the demo in one click").click().run()
    btn(at, "Fix ").click().run()
    btn(at, "example answers").click().run()
    assert not at.exception, at.exception
    filled = [t.value for t in at.text_area if t.value]
    assert any("9 weeks" in v for v in filled) and any("physical therapy" in v for v in filled)
