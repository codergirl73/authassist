"""Drive the Streamlit UI headlessly (fake LLM, snapshot policy)."""

from streamlit.testing.v1 import AppTest

from tests.test_pipeline import CASES, setup


def test_full_ui_flow(fake_llm):
    case04 = (CASES / "case_04" / "reference_text.txt").read_text()
    fake_llm.on("Transcribe this clinical note", case04)
    setup(fake_llm, {"neuro_exam_documented": ("met", "Neuro exam: strength 5/5")})
    at = AppTest.from_file("../ui/app.py", default_timeout=30)
    at.run()
    assert not at.exception
    at.selectbox[0].select_index(3).run()  # case 04, scanned fax
    at.button[0].click().run()
    assert not at.exception and not at.error, [e.value for e in at.error]
    md = " ".join(m.value for m in at.markdown)
    assert (
        "Not ready" in md
        and "verified in note" in md
        and "Fill the gaps" in " ".join(s.value for s in at.subheader)
    )

    at.text_area[0].input("Low back pain for 9 weeks.")  # form values apply on submit, same run
    next(b for b in at.button if "re-check" in b.label).click().run()
    assert not at.exception, [e.value for e in at.error]
    result = at.session_state["result"]
    assert result.previous_score is not None and len(result.addenda) == 1
    assert any(m.label == "After addendum" for m in at.metric)

    next(b for b in at.button if "Draft letter" in b.label).click().run()
    assert not at.exception
    assert at.session_state["pdf"][:4] == b"%PDF"
