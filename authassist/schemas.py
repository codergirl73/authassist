"""Pydantic data models shared by every pipeline step."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TreatmentEntry(BaseModel):
    treatment: str
    duration_weeks: float | None = None
    dates: str | None = None
    outcome: str | None = None


class ClinicalFacts(BaseModel):
    patient_age: int | None = None
    sex: str | None = None
    chief_complaint: str = ""
    diagnoses: list[str] = Field(default_factory=list)
    symptom_duration_weeks: float | None = None
    conservative_treatments: list[TreatmentEntry] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    neuro_exam_findings: list[str] = Field(default_factory=list)
    prior_imaging: list[str] = Field(default_factory=list)
    requested_procedure: str = ""
    requested_cpt: str | None = None
    source_spans: dict[str, str] = Field(default_factory=dict)


class PolicyDoc(BaseModel):
    payer: str
    procedure: str
    title: str
    url: str
    retrieved_at: datetime
    text_hash: str
    source: Literal["tavily", "cache", "snapshot"] = "tavily"
    is_fallback: bool = False  # True when Medicare/CMS guidance stands in for the payer


class Criterion(BaseModel):
    id: str
    description: str
    policy_citation: str
    bypass_group: str | None = None
    category: str = "other"


class CriterionList(BaseModel):
    criteria: list[Criterion]


class CriterionResult(BaseModel):
    criterion_id: str
    status: Literal["met", "missing", "unclear"]
    evidence_quote: str | None = None
    reasoning: str = ""
    quote_verified: bool = False


class MatchResponse(BaseModel):
    """What the LLM returns; quote_verified is always set by code afterwards."""

    results: list[CriterionResult]


class MissingItems(BaseModel):
    items: list[str]


class Assessment(BaseModel):
    payer: str
    procedure: str
    criteria: list[Criterion]
    results: list[CriterionResult]
    readiness_score: int
    status: Literal["ready", "needs_attention", "not_ready"]
    missing_items: list[str]
    red_flag_bypass: bool
    policy: PolicyDoc


class LetterDraft(BaseModel):
    body_markdown: str
    citations: list[str] = Field(default_factory=list)


class CaseInput(BaseModel):
    case_id: str = "adhoc"
    payer: str  # key in config/procedures/<procedure>.yaml payers
    procedure: str = "lumbar_mri"
    note_text: str | None = None
    file_bytes: bytes | None = None
    filename: str | None = None
