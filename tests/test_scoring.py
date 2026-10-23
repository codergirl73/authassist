from authassist.schemas import Criterion, CriterionResult
from authassist.scoring import readiness

EXCUSED = ["symptom_duration", "conservative_therapy"]
CRITERIA = [
    Criterion(id="dur", description="", policy_citation="", category="symptom_duration"),
    Criterion(id="ct", description="", policy_citation="", category="conservative_therapy"),
    Criterion(id="neuro", description="", policy_citation="", category="neuro_exam"),
    Criterion(id="img", description="", policy_citation="", category="prior_imaging"),
    Criterion(id="rf", description="", policy_citation="", category="red_flag", bypass_group="red_flags"),
]


def results(**statuses):
    return [CriterionResult(criterion_id=k, status=v) for k, v in statuses.items()]


def test_all_met_is_ready():
    assert readiness(
        CRITERIA, results(dur="met", ct="met", neuro="met", img="met", rf="missing"), EXCUSED
    ) == (100, "ready", False)


def test_score_formula_and_not_ready():
    score, status, bypass = readiness(
        CRITERIA, results(dur="missing", ct="missing", neuro="met", img="met", rf="missing"), EXCUSED
    )
    assert (score, status, bypass) == (50, "not_ready", False)


def test_unclear_counts_half_and_needs_attention():
    score, status, _ = readiness(
        CRITERIA, results(dur="met", ct="unclear", neuro="met", img="met", rf="missing"), EXCUSED
    )
    assert (score, status) == (88, "needs_attention")  # (1 + .5 + 1 + 1) / 4 = 87.5


def test_red_flag_bypass_excuses_conservative_therapy():
    score, status, bypass = readiness(
        CRITERIA, results(dur="missing", ct="missing", neuro="met", img="met", rf="met"), EXCUSED
    )
    assert (score, status, bypass) == (100, "ready", True)


def test_red_flag_does_not_excuse_neuro_exam():
    score, status, bypass = readiness(
        CRITERIA, results(dur="missing", ct="missing", neuro="missing", img="met", rf="met"), EXCUSED
    )
    assert bypass and status == "not_ready" and score == 50


def test_missing_result_counts_as_missing():
    score, status, _ = readiness(CRITERIA, results(dur="met", ct="met", neuro="met"), EXCUSED)
    assert (score, status) == (75, "not_ready")
