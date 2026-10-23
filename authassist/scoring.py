"""Readiness score. Computed in code, never by the LLM.

score = round(100 * mean(weight(status)) over REQUIRED criteria)
  weight: met = 1.0, unclear = 0.5, missing = 0.0
REQUIRED = criteria without a bypass_group, minus the categories excused by a
red-flag bypass (symptom_duration, conservative_therapy) when any red-flag
criterion is met.
status: ready = every required criterion met; not_ready = any required
criterion missing; otherwise needs_attention.
"""

from __future__ import annotations

from authassist.schemas import Criterion, CriterionResult

WEIGHTS = {"met": 1.0, "unclear": 0.5, "missing": 0.0}
RED_FLAG_GROUP = "red_flags"


def red_flag_bypass(criteria: list[Criterion], results: list[CriterionResult]) -> bool:
    by_id = {r.criterion_id: r for r in results}
    return any(
        c.bypass_group == RED_FLAG_GROUP and by_id.get(c.id) and by_id[c.id].status == "met" for c in criteria
    )


def required_criteria(criteria: list[Criterion], bypass: bool, excused: list[str]) -> list[Criterion]:
    required = [c for c in criteria if c.bypass_group is None]
    if bypass:
        required = [c for c in required if c.category not in excused]
    return required


def readiness(
    criteria: list[Criterion], results: list[CriterionResult], excused: list[str]
) -> tuple[int, str, bool]:
    """Return (score 0-100, status, red_flag_bypass)."""
    bypass = red_flag_bypass(criteria, results)
    required = required_criteria(criteria, bypass, excused)
    by_id = {r.criterion_id: r for r in results}
    statuses = [by_id[c.id].status if c.id in by_id else "missing" for c in required]
    if not statuses:
        return (100 if bypass else 0), ("ready" if bypass else "not_ready"), bypass
    score = round(100 * sum(WEIGHTS[s] for s in statuses) / len(statuses))
    if all(s == "met" for s in statuses):
        status = "ready"
    elif "missing" in statuses:
        status = "not_ready"
    else:
        status = "needs_attention"
    return score, status, bypass
