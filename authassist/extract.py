"""Step 2: extract structured clinical facts strictly from the note."""

from __future__ import annotations

import logging

from authassist import llm
from authassist.matcher import quote_in_note
from authassist.schemas import ClinicalFacts

log = logging.getLogger(__name__)

SYSTEM = """You extract structured clinical facts from a clinical note for a
prior-authorization request.
Rules:
- Use ONLY what the note states. If the note does not state it, use null or an empty list. Never infer.
- conservative_treatments: each therapy tried (PT, NSAIDs, chiropractic, home exercise, etc.)
  with duration_weeks and dates only if stated.
- red_flags: only documented red flags (cauda equina signs such as saddle anesthesia or urinary
  retention, progressive neurological deficit, suspected malignancy, infection, fracture/trauma).
- source_spans: map field names to the EXACT supporting text copied verbatim from the note."""


def extract_facts(note_text: str) -> ClinicalFacts:
    facts, _ = llm.chat_model(
        "fast",
        [{"role": "system", "content": SYSTEM}, {"role": "user", "content": f"NOTE:\n<<<\n{note_text}\n>>>"}],
        ClinicalFacts,
        step="extract facts",
    )
    kept = {}
    for field, span in facts.source_spans.items():
        if quote_in_note(span, note_text):
            kept[field] = span
        else:
            log.warning("Dropping unverifiable source span for field %s", field)
    facts.source_spans = kept
    return facts
