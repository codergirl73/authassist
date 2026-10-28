"""HTTP API exposing the same pipeline as the UI.

Run: uvicorn api.main:app --port 8000
"""

from __future__ import annotations

import base64
import json
import queue
import threading
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
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
WEB_DIR = Path(__file__).resolve().parent.parent / "web"


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


def _case_from_request(req: AssessRequest) -> CaseInput:
    if req.example_case:
        case_dir = CASES_DIR / req.example_case
        if not case_dir.is_dir() or case_dir.parent != CASES_DIR:
            raise HTTPException(404, f"Unknown example case {req.example_case!r}")
        return load_case(case_dir, req.payer)
    if req.note_text:
        if config.DEMO_MODE:
            raise HTTPException(403, "DEMO_MODE is on: only example_case inputs are accepted")
        if not req.payer:
            raise HTTPException(422, "payer is required with note_text")
        return CaseInput(case_id="api_note", payer=req.payer, note_text=req.note_text)
    raise HTTPException(422, "Provide example_case or note_text")


@app.post("/assess", response_model=pipeline.PipelineResult)
def assess(req: AssessRequest) -> pipeline.PipelineResult:
    case = _case_from_request(req)
    try:
        return pipeline.run_pipeline(case, force_refresh=req.force_refresh)
    except ValueError as err:
        raise HTTPException(422, str(err)) from err
    except LLMError as err:
        raise HTTPException(502, f"Model call failed: {err}") from err
    except RuntimeError as err:  # e.g. missing API key
        raise HTTPException(503, str(err)) from err


def _error_message(err: Exception) -> str:
    if isinstance(err, LLMError):
        return f"Model call failed: {err}"
    if isinstance(err, RuntimeError):
        return f"Service not configured: {err}"
    return str(err)


def _ndjson(job: Callable[[pipeline.Progress], pipeline.PipelineResult]) -> StreamingResponse:
    """Run `job` in a thread and stream its progress as newline-delimited JSON events."""
    events: queue.Queue = queue.Queue()

    def work() -> None:
        try:
            result = job(
                lambda label, detail: events.put({"type": "progress", "label": label, "detail": detail})
            )
            events.put({"type": "result", "data": result.model_dump(mode="json")})
        except Exception as err:  # noqa: BLE001 - reported to the client as an error event
            events.put({"type": "error", "message": _error_message(err)})
        finally:
            events.put(None)

    threading.Thread(target=work, daemon=True).start()

    def lines():
        while (item := events.get()) is not None:
            yield json.dumps(item) + "\n"

    return StreamingResponse(lines(), media_type="application/x-ndjson")


@app.post("/assess/stream")
def assess_stream(req: AssessRequest) -> StreamingResponse:
    case = _case_from_request(req)
    return _ndjson(
        lambda progress: pipeline.run_pipeline(case, force_refresh=req.force_refresh, progress=progress)
    )


@app.post("/recheck/stream")
def recheck_stream(req: AddendumRequest) -> StreamingResponse:
    return _ndjson(
        lambda progress: pipeline.recheck_with_addendum(req.result, req.addendum, progress=progress)
    )


@app.get("/api/config")
def api_config() -> dict:
    """Everything the web app needs to render: payers, example cases, models, mode flags."""
    proc = config.procedure_config("lumbar_mri")
    models = config.models_config()
    cases = []
    for d in sorted(p for p in CASES_DIR.iterdir() if p.is_dir()):
        meta = json.loads((d / "case.json").read_text())
        txt = d / "note.txt"
        cases.append(
            {
                "id": d.name,
                "scenario": meta["scenario"],
                "payer": meta["payer"],
                "input": meta["input"],
                "note_text": txt.read_text() if txt.exists() else None,
                "image_url": None if txt.exists() else f"/api/cases/{d.name}/image",
            }
        )
    return {
        "demo_mode": config.DEMO_MODE,
        "app_env": config.APP_ENV,
        "procedure": proc["display_name"],
        "cpt": "72148",
        "payers": {k: v["name"] for k, v in proc["payers"].items()},
        "bypass_excuses": proc["bypass_excuses"],
        "models": {role: models[role]["model"] for role in ("vision", "fast", "reasoning")},
        "cases": cases,
    }


@app.get("/api/cases/{case_id}/image")
def case_image(case_id: str) -> FileResponse:
    path = CASES_DIR / case_id / "note.png"
    if path.parent.parent != CASES_DIR or not path.is_file():
        raise HTTPException(404, "No such image")
    return FileResponse(path, media_type="image/png")


@app.post("/recheck", response_model=pipeline.PipelineResult)
def recheck(req: AddendumRequest) -> pipeline.PipelineResult:
    return pipeline.recheck_with_addendum(req.result, req.addendum)


@app.post("/letter", response_model=LetterResponse)
def letter(result: pipeline.PipelineResult) -> LetterResponse:
    draft, pdf_bytes, traces = pipeline.make_letter(result)
    return LetterResponse(letter=draft, pdf_base64=base64.b64encode(pdf_bytes).decode(), traces=traces)


# The single-page web app (landing, sign-in, workspace). Mounted last so API routes win.
if WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
