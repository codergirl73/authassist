"""Step 7a: draft a letter of medical necessity from verified evidence only."""

from __future__ import annotations

import json
from datetime import date

from authassist import llm
from authassist.schemas import Assessment, ClinicalFacts, LetterDraft

DRAFT_HEADER = "DRAFT - requires clinician review and signature."

SYSTEM = """You draft a letter of medical necessity for a prior-authorization request.
Rules:
- Use ONLY the verified facts and verified evidence quotes provided. Do not add clinical details.
- Cite the payer policy criteria each point satisfies, including the policy URL.
- Use these exact placeholders and never invent values for them:
  [Clinician Name], [Clinician NPI], [Practice Name], [Practice Address], [Signature], [Date].
- Refer to the patient only by the synthetic case ID given (no names).
- Professional, concise (about 250-400 words), Markdown formatting.
- If a red-flag indication is documented, state it clearly as the reason imaging is urgent.
- Do not claim the request is approved."""


def draft_letter(assessment: Assessment, facts: ClinicalFacts, case_id: str) -> LetterDraft:
    crit = {c.id: c for c in assessment.criteria}
    verified = [
        {
            "criterion": crit[r.criterion_id].description,
            "policy_citation": crit[r.criterion_id].policy_citation,
            "evidence_quote": r.evidence_quote,
        }
        for r in assessment.results
        if r.status == "met" and r.quote_verified
    ]
    payload = {
        "case_id": case_id,
        "payer": assessment.payer,
        "procedure": assessment.procedure,
        "cpt": "72148",
        "policy": {"title": assessment.policy.title, "url": assessment.policy.url},
        "red_flag_bypass": assessment.red_flag_bypass,
        "facts": facts.model_dump(exclude={"source_spans"}),
        "verified_evidence": verified,
        "today": date.today().isoformat(),
    }
    letter, _ = llm.chat_model(
        "reasoning",
        [{"role": "system", "content": SYSTEM}, {"role": "user", "content": json.dumps(payload, indent=1)}],
        LetterDraft,
        step="draft letter",
    )
    if DRAFT_HEADER.lower() not in letter.body_markdown.lower():
        letter.body_markdown = f"**{DRAFT_HEADER}**\n\n{letter.body_markdown}"
    if assessment.policy.url not in letter.citations:
        letter.citations.append(assessment.policy.url)
    return letter
