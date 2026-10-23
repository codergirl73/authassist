"""Per-run trace of every model / tool call, shown in the UI."""

from __future__ import annotations

import time
from contextlib import contextmanager
from contextvars import ContextVar

from pydantic import BaseModel


class TraceEntry(BaseModel):
    step: str
    role: str  # vision | fast | reasoning | tavily | code
    model: str
    latency_ms: int
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    success: bool = True
    note: str | None = None


class Tracer:
    def __init__(self) -> None:
        self.entries: list[TraceEntry] = []

    def add(self, entry: TraceEntry) -> None:
        self.entries.append(entry)

    def total_tokens(self) -> int:
        return sum((e.prompt_tokens or 0) + (e.completion_tokens or 0) for e in self.entries)


_current: ContextVar[Tracer | None] = ContextVar("tracer", default=None)


def current() -> Tracer:
    tracer = _current.get()
    if tracer is None:
        tracer = Tracer()
        _current.set(tracer)
    return tracer


@contextmanager
def tracing(tracer: Tracer | None = None):
    tracer = tracer or Tracer()
    token = _current.set(tracer)
    try:
        yield tracer
    finally:
        _current.reset(token)


@contextmanager
def timed(step: str, role: str, model: str, note: str | None = None):
    """Trace a non-LLM call (e.g. Tavily). Records failure if the block raises."""
    start = time.perf_counter()
    entry = TraceEntry(step=step, role=role, model=model, latency_ms=0, note=note)
    try:
        yield entry
    except Exception:
        entry.success = False
        raise
    finally:
        entry.latency_ms = int((time.perf_counter() - start) * 1000)
        current().add(entry)
