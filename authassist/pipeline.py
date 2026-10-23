"""Chains steps 1-5 (assessment), the gap-fill re-check, and step 7 (letter + PDF)."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import date

from pydantic import BaseModel, Field

from authassist import config, criteria, extract, ingest, letter, matcher, pdf, policy, scoring, tracing
from authassist.schemas import Assessment, CaseInput, ClinicalFacts, Criterion, LetterDraft, PolicyDoc

log = logging.getLogger(__name__)

# progress(label, detail) is called after each step, e.g. ("Reading fax", "nemotron-... ✓ 3.1s")
Progress = Callable[[str, str], None]


class PipelineResult(BaseModel):
    case_id: str
    payer_key: str
    procedure_key: str
    note_text: str
    ingest_method: str
    facts: ClinicalFacts
    assessment: Assessment
    policy_notice: str | None = None
    traces: list[tracing.TraceEntry] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    addenda: list[str] = Field(default_factory=list)
    previous_score: int | None = None


class _WarningCollector(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def _run_step(label: str, fn, progress: Progress | None):
    tracer = tracing.current()
    before = len(tracer.entries)
    start = time.perf_counter()
    out = fn()
    secs = time.perf_counter() - start
    models = sorted({e.model for e in tracer.entries[before:] if e.success})
    if progress:
        progress(label, f"{', '.join(models) or 'code'} ✓ {secs:.1f}s")
    return out


def assess(
    note_text: str,
    facts: ClinicalFacts,
    crits: list[Criterion],
    policy_doc: PolicyDoc,
    procedure_key: str,
    progress: Progress | None = None,
) -> Assessment:
    proc = config.procedure_config(procedure_key)
    results = _run_step(
        "Matching evidence to criteria", lambda: matcher.match_evidence(note_text, facts, crits), progress
    )
    score, status, bypass = scoring.readiness(crits, results, proc["bypass_excuses"])
    required_ids = {c.id for c in scoring.required_criteria(crits, bypass, proc["bypass_excuses"])}
    asks = _run_step(
        "Writing missing-item asks", lambda: matcher.missing_items(crits, results, required_ids), progress
    )
    return Assessment(
        payer=policy_doc.payer,
        procedure=proc["display_name"],
        criteria=crits,
        results=results,
        readiness_score=score,
        status=status,
        missing_items=asks,
        red_flag_bypass=bypass,
        policy=policy_doc,
    )


def run_pipeline(
    case: CaseInput, force_refresh: bool = False, progress: Progress | None = None
) -> PipelineResult:
    collector = _WarningCollector()
    logging.getLogger("authassist").addHandler(collector)
    proc = config.procedure_config(case.procedure)
    try:
        with tracing.tracing() as tracer:
            reading = "Reading scanned note" if case.file_bytes and not case.note_text else "Reading note"
            note_text, method = _run_step(
                reading, lambda: ingest.ingest(case.note_text, case.file_bytes, case.filename), progress
            )
            facts = _run_step("Extracting clinical facts", lambda: extract.extract_facts(note_text), progress)
            bundle = _run_step(
                "Finding payer policy",
                lambda: policy.find_policy(case.payer, case.procedure, force_refresh),
                progress,
            )
            crits = bundle.criteria
            if crits is None:
                crits = _run_step(
                    "Converting policy to criteria",
                    lambda: criteria.policy_to_criteria(bundle.text or "", bundle.policy, proc),
                    progress,
                )
                policy.save_criteria(case.payer, case.procedure, crits)
            assessment = assess(note_text, facts, crits, bundle.policy, case.procedure, progress)
        return PipelineResult(
            case_id=case.case_id,
            payer_key=case.payer,
            procedure_key=case.procedure,
            note_text=note_text,
            ingest_method=method,
            facts=facts,
            assessment=assessment,
            policy_notice=bundle.notice,
            traces=tracer.entries,
            warnings=collector.messages,
        )
    finally:
        logging.getLogger("authassist").removeHandler(collector)


def addendum_block(text: str, on: date | None = None) -> str:
    return f"--- ADDENDUM (entered by clinician on {(on or date.today()).isoformat()}) ---\n{text.strip()}"


def recheck_with_addendum(
    prev: PipelineResult, addendum_text: str, progress: Progress | None = None
) -> PipelineResult:
    """Step 6: append the clinician's addendum and re-run steps 2 and 5 only
    (policy and criteria are reused)."""
    collector = _WarningCollector()
    logging.getLogger("authassist").addHandler(collector)
    block = addendum_block(addendum_text)
    note_text = f"{prev.note_text}\n\n{block}"
    try:
        with tracing.tracing() as tracer:
            facts = _run_step(
                "Re-extracting clinical facts", lambda: extract.extract_facts(note_text), progress
            )
            assessment = assess(
                note_text,
                facts,
                prev.assessment.criteria,
                prev.assessment.policy,
                prev.procedure_key,
                progress,
            )
        return prev.model_copy(
            update={
                "note_text": note_text,
                "facts": facts,
                "assessment": assessment,
                "traces": [*prev.traces, *tracer.entries],
                "warnings": [*prev.warnings, *collector.messages],
                "addenda": [*prev.addenda, block],
                "previous_score": prev.assessment.readiness_score,
            }
        )
    finally:
        logging.getLogger("authassist").removeHandler(collector)


def make_letter(result: PipelineResult) -> tuple[LetterDraft, bytes, list[tracing.TraceEntry]]:
    with tracing.tracing() as tracer:
        draft = letter.draft_letter(result.assessment, result.facts, result.case_id)
        with tracing.timed("build PDF", "code", "reportlab"):
            pdf_bytes = pdf.build_pdf(result.assessment, draft, result.case_id)
    return draft, pdf_bytes, tracer.entries
