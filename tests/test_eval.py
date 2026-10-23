import importlib.util
from pathlib import Path

from tests.test_pipeline import CASES, setup

spec = importlib.util.spec_from_file_location(
    "run_eval", Path(__file__).resolve().parent.parent / "eval" / "run_eval.py"
)
run_eval = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_eval)


def test_eval_runs_and_reports(fake_llm):
    setup(
        fake_llm,
        {
            "symptom_duration": ("met", "low back pain for 10 weeks"),
            "conservative_therapy_6wk": ("met", "Completed 8 weeks of physical therapy"),
            "neuro_exam_documented": ("met", "left Achilles reflex diminished (1+)"),
        },
    )
    row = run_eval.run_case(CASES / "case_01")
    assert row["crit_checks"]["red_flag"] == ("missing", "missing")
    assert row["crit_checks"]["conservative_therapy"] == ("met", "met")
    report = run_eval.summarize([row])
    assert "## Failure cases" in report and "Per-criterion accuracy" in report
