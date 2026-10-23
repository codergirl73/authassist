"""HTTP API exposing the same pipeline as the UI.

Run: uvicorn api.main:app --port 8000
"""

from __future__ import annotations

import base64

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from authassist import __version__, config, pipeline
from authassist.cli import load_case
from authassist.llm import LLMError
from authassist.schemas import CaseInput, LetterDraft
from authassist.tracing import TraceEntry

app = FastAPI(
    title="AuthAssist API",
    version=__version__,
    description="Prior-authorization readiness checks. Drafts only; never submits to insurers.",
)

CASES_DIR = config.DATA_DIR / "synthetic_notes"


class AssessRequest(BaseModel):
    payer: str | None = None  # aetna | molina | medicare (defaults to the example case's payer)
    example_case: str | None = None  # e.g. "case_04"
    note_text: str | None = None  # disabled when DEMO_MODE=true
    force_refresh: bool = False


class LetterResponse(BaseModel):
    letter: LetterDraft
    pdf_base64: str
    traces: list[TraceEntry]


class AddendumRequest(BaseModel):
    result: pipeline.PipelineResult
    addendum: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__, "demo_mode": config.DEMO_MODE}


@app.post("/assess", response_model=pipeline.PipelineResult)
def assess(req: AssessRequest) -> pipeline.PipelineResult:
    if req.example_case:
        case_dir = CASES_DIR / req.example_case
        if not case_dir.is_dir() or case_dir.parent != CASES_DIR:
            raise HTTPException(404, f"Unknown example case {req.example_case!r}")
        case = load_case(case_dir, req.payer)
    elif req.note_text:
        if config.DEMO_MODE:
            raise HTTPException(403, "DEMO_MODE is on: only example_case inputs are accepted")
        if not req.payer:
            raise HTTPException(422, "payer is required with note_text")
        case = CaseInput(case_id="api_note", payer=req.payer, note_text=req.note_text)
    else:
        raise HTTPException(422, "Provide example_case or note_text")
    try:
        return pipeline.run_pipeline(case, force_refresh=req.force_refresh)
    except ValueError as err:
        raise HTTPException(422, str(err)) from err
    except LLMError as err:
        raise HTTPException(502, f"Model call failed: {err}") from err
    except RuntimeError as err:  # e.g. missing API key
        raise HTTPException(503, str(err)) from err


@app.post("/recheck", response_model=pipeline.PipelineResult)
def recheck(req: AddendumRequest) -> pipeline.PipelineResult:
    return pipeline.recheck_with_addendum(req.result, req.addendum)


@app.post("/letter", response_model=LetterResponse)
def letter(result: pipeline.PipelineResult) -> LetterResponse:
    draft, pdf_bytes, traces = pipeline.make_letter(result)
    return LetterResponse(letter=draft, pdf_base64=base64.b64encode(pdf_bytes).decode(), traces=traces)
