"""Step 5: match each policy criterion to verbatim evidence in the note, then
verify every quote programmatically (anti-hallucination)."""

from __future__ import annotations

import json
import logging
import re

from authassist import llm
from authassist.schemas import ClinicalFacts, Criterion, CriterionResult, MatchResponse, MissingItems

log = logging.getLogger(__name__)

_TRANSLATE = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"})


def normalize(text: str) -> str:
    """Lowercase, unify smart quotes/dashes, collapse whitespace, trim edge punctuation."""
    text = text.translate(_TRANSLATE).lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text.strip(" .,;:\"'")


def quote_in_note(quote: str | None, note_text: str) -> bool:
    if not quote or not normalize(quote):
        return False
    return normalize(quote) in normalize(note_text)


SYSTEM = """You are a prior-authorization documentation reviewer.
For EACH criterion return status met|missing|unclear, an evidence_quote that is an
EXACT, verbatim substring of the NOTE (or null), and one-sentence reasoning.
Rules:
- Never invent or paraphrase evidence. Copy the quote character-for-character from the NOTE.
  Keep quotes short (one sentence or clause). If the note does not say it, status = missing.
- "unclear" only when the note mentions it but lacks a required detail (e.g., duration).
- If a criterion requires a quantity (e.g. ">= 6 weeks of therapy"), it is "met" ONLY when the note
  explicitly states that quantity or dates that prove it. A vague mention ("did some physical therapy",
  "tried over-the-counter pain relievers") with no duration or dates is "unclear", never "met".
- For red-flag criteria: "met" only if the note documents that red flag; otherwise "missing".
- Return one result per criterion, using the exact criterion_id given.
- Set quote_verified to false (it is checked by code).
- Return ONLY JSON matching the schema."""


def verify_results(results: list[CriterionResult], note_text: str) -> list[CriterionResult]:
    verified = []
    for r in results:
        r = r.model_copy()
        r.quote_verified = quote_in_note(r.evidence_quote, note_text)
        if r.evidence_quote and not r.quote_verified:
            log.warning("Unverified evidence quote for criterion %s; downgrading", r.criterion_id)
            if r.status == "met":
                r.status = "unclear"
                r.reasoning = f"[Quote not found verbatim in note - downgraded from met] {r.reasoning}"
        elif not r.evidence_quote and r.status == "met":
            r.status = "unclear"
            r.reasoning = f"[No evidence quote supplied - downgraded from met] {r.reasoning}"
        verified.append(r)
    return verified


def match_evidence(note_text: str, facts: ClinicalFacts, criteria: list[Criterion]) -> list[CriterionResult]:
    crit_payload = [
        {"criterion_id": c.id, "description": c.description, "red_flag": c.bypass_group == "red_flags"}
        for c in criteria
    ]
    user = (
        f"CRITERIA:\n{json.dumps(crit_payload, indent=1)}\n\n"
        f"EXTRACTED FACTS (helper only; quotes must come from the NOTE):\n"
        f"{facts.model_dump_json(exclude={'source_spans'})}\n\n"
        f"NOTE:\n<<<\n{note_text}\n>>>"
    )
    parsed, _ = llm.chat_model(
        "reasoning",
        [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
        MatchResponse,
        step="match evidence",
    )
    by_id = {r.criterion_id: r for r in parsed.results}
    # Every criterion gets exactly one result, in criteria order.
    ordered = [
        by_id.get(c.id)
        or CriterionResult(criterion_id=c.id, status="missing", reasoning="Model returned no result.")
        for c in criteria
    ]
    return verify_results(ordered, note_text)


MISSING_SYSTEM = """You help clinic staff fix prior-authorization documentation gaps.
For each gap, write ONE short, actionable ask for the clinician (max 15 words),
e.g. "Add dates and duration of physical therapy". No preamble."""


def missing_items(
    criteria: list[Criterion], results: list[CriterionResult], required_ids: set[str]
) -> list[str]:
    by_id = {c.id: c for c in criteria}
    gaps = [
        {"criterion": by_id[r.criterion_id].description, "status": r.status, "reasoning": r.reasoning}
        for r in results
        if r.criterion_id in required_ids and r.status != "met"
    ]
    if not gaps:
        return []
    parsed, _ = llm.chat_model(
        "fast",
        [
            {"role": "system", "content": MISSING_SYSTEM},
            {"role": "user", "content": json.dumps(gaps, indent=1)},
        ],
        MissingItems,
        step="write missing-item asks",
    )
    return parsed.items
