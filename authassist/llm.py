"""Nebius Token Factory client (OpenAI-compatible) with retries, fallback,
structured output and tracing. This is the ONLY place LLM calls are made."""

from __future__ import annotations

import json
import re
import time
from functools import lru_cache
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from authassist import config, tracing

T = TypeVar("T", bound=BaseModel)

MAX_ATTEMPTS = 3
TIMEOUT_S = 120


class LLMResult(BaseModel):
    text: str
    model: str
    parsed: dict | list | None = None
    latency_ms: int = 0
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class LLMError(RuntimeError):
    pass


@lru_cache
def client() -> OpenAI:
    return OpenAI(
        base_url=config.NEBIUS_BASE_URL,
        api_key=config.nebius_api_key(),
        timeout=TIMEOUT_S,
        max_retries=0,  # we retry ourselves so fallbacks and traces stay visible
    )


def role_settings(role: str) -> dict:
    cfg = config.models_config()
    if role not in cfg:
        raise KeyError(f"Unknown model role {role!r}; check config/models.yaml")
    return cfg[role]


def model_for(role: str) -> str:
    return role_settings(role)["model"]


# ---------------------------------------------------------------- JSON helpers

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def strip_reasoning(text: str) -> str:
    text = _THINK_RE.sub("", text)
    # Unterminated think block (truncated output): drop everything before </think> if present.
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    return text.strip()


def extract_json(text: str) -> dict | list:
    """Parse JSON from a model reply: strips think blocks and code fences, then
    falls back to the outermost {...} or [...] span."""
    text = strip_reasoning(text)
    fenced = _FENCE_RE.search(text)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if not starts:
        raise ValueError("No JSON object found in model output")
    start = min(starts)
    end = max(text.rfind("}"), text.rfind("]"))
    if end <= start:
        raise ValueError("No complete JSON object found in model output")
    candidate = text[start : end + 1]
    # Trailing commas are the most common small defect.
    candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
    return json.loads(candidate)


def schema_instructions(schema: type[BaseModel]) -> str:
    return (
        "Return ONLY a single JSON object (no prose, no markdown fences) that validates "
        "against this JSON Schema:\n" + json.dumps(schema.model_json_schema(), indent=None)
    )


# ---------------------------------------------------------------- core call


def _backoff(attempt: int) -> None:
    time.sleep(2**attempt)


def _call_once(model: str, settings: dict, messages: list[dict]) -> tuple[str, object]:
    resp = client().chat.completions.create(
        model=model,
        messages=messages,
        temperature=settings.get("temperature", 0.0),
        max_tokens=settings.get("max_tokens", 2000),
        **({"extra_body": settings["extra_body"]} if settings.get("extra_body") else {}),
    )
    content = resp.choices[0].message.content or ""
    return content, resp.usage


def _with_system_prefix(messages: list[dict], prefix: str | None) -> list[dict]:
    if not prefix:
        return messages
    if messages and messages[0]["role"] == "system" and isinstance(messages[0]["content"], str):
        return [{"role": "system", "content": f"{prefix}\n\n{messages[0]['content']}"}, *messages[1:]]
    return [{"role": "system", "content": prefix}, *messages]


def _raw_chat(role: str, messages: list[dict], step: str) -> LLMResult:
    settings = role_settings(role)
    fallbacks = config.models_config().get("fallbacks", {})
    models = [settings["model"]]
    if fallbacks.get(role):
        models.append(fallbacks[role])

    client()  # fail fast (no retries) on missing API key
    last_err: Exception | None = None
    for model in models:
        msgs = _with_system_prefix(messages, settings.get("system_prefix"))
        for attempt in range(MAX_ATTEMPTS):
            start = time.perf_counter()
            try:
                text, usage = _call_once(model, settings, msgs)
                latency = int((time.perf_counter() - start) * 1000)
                result = LLMResult(
                    text=text,
                    model=model,
                    latency_ms=latency,
                    prompt_tokens=getattr(usage, "prompt_tokens", None),
                    completion_tokens=getattr(usage, "completion_tokens", None),
                )
                tracing.current().add(
                    tracing.TraceEntry(
                        step=step,
                        role=role,
                        model=model,
                        latency_ms=latency,
                        prompt_tokens=result.prompt_tokens,
                        completion_tokens=result.completion_tokens,
                        note="fallback model" if model != models[0] else None,
                    )
                )
                return result
            except Exception as err:  # network, rate limit, 5xx, bad model id
                last_err = err
                tracing.current().add(
                    tracing.TraceEntry(
                        step=step,
                        role=role,
                        model=model,
                        latency_ms=int((time.perf_counter() - start) * 1000),
                        success=False,
                        note=f"attempt {attempt + 1}: {type(err).__name__}",
                    )
                )
                if attempt < MAX_ATTEMPTS - 1:
                    _backoff(attempt)
    raise LLMError(f"All models failed for role {role!r}: {last_err}") from last_err


def chat(
    role: str,
    messages: list[dict],
    json_schema: type[T] | None = None,
    step: str = "llm",
) -> LLMResult:
    """Call the model for `role`. With `json_schema`, the reply is parsed and
    validated; on a parse/validation failure we retry once with the error appended."""
    if json_schema is None:
        result = _raw_chat(role, messages, step)
        result.text = strip_reasoning(result.text)
        return result

    messages = list(messages)
    instructions = schema_instructions(json_schema)
    if messages and messages[0]["role"] == "system":
        messages[0] = {"role": "system", "content": f"{messages[0]['content']}\n\n{instructions}"}
    else:
        messages.insert(0, {"role": "system", "content": instructions})

    result = _raw_chat(role, messages, step)
    try:
        result.parsed = json_schema.model_validate(extract_json(result.text)).model_dump(mode="json")
        return result
    except (ValueError, ValidationError) as err:
        repair = [
            *messages,
            {"role": "assistant", "content": result.text[-6000:]},
            {
                "role": "user",
                "content": (
                    f"Your previous reply was not valid. Error:\n{err}\n\n"
                    "Return ONLY the corrected JSON object, nothing else."
                ),
            },
        ]
        result = _raw_chat(role, repair, f"{step} (repair)")
        result.parsed = json_schema.model_validate(extract_json(result.text)).model_dump(mode="json")
        return result


def chat_model(role: str, messages: list[dict], schema: type[T], step: str) -> tuple[T, LLMResult]:
    """Convenience wrapper returning the validated pydantic object."""
    result = chat(role, messages, json_schema=schema, step=step)
    return schema.model_validate(result.parsed), result


def image_message(prompt: str, images_b64_png: list[str]) -> dict:
    """OpenAI-style multimodal user message with base64 data-URL images."""
    content: list[dict] = [{"type": "text", "text": prompt}]
    for b64 in images_b64_png:
        content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})
    return {"role": "user", "content": content}
