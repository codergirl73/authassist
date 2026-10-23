import pytest
from pydantic import BaseModel

from authassist import llm, tracing


class Thing(BaseModel):
    name: str
    count: int


@pytest.mark.parametrize(
    "raw",
    [
        '{"name": "a", "count": 1}',
        '```json\n{"name": "a", "count": 1}\n```',
        '<think>let me think {not json}</think>{"name": "a", "count": 1}',
        'Sure! Here you go: {"name": "a", "count": 1,} Hope this helps.',
        'reasoning trail...</think>\n```\n{"name": "a", "count": 1}\n```',
    ],
)
def test_extract_json_variants(raw):
    assert llm.extract_json(raw) == {"name": "a", "count": 1}


def test_extract_json_no_object():
    with pytest.raises(ValueError):
        llm.extract_json("no json here")


def test_chat_repairs_invalid_json_once(fake_llm):
    replies = iter(['{"name": "a"}', '{"name": "a", "count": 2}'])
    fake_llm.on("Thing", lambda m, model: next(replies))
    with tracing.tracing() as tracer:
        parsed, result = llm.chat_model("fast", [{"role": "user", "content": "go"}], Thing, step="t")
    assert parsed == Thing(name="a", count=2)
    assert len(fake_llm.calls) == 2
    assert "not valid" in fake_llm.calls[1]["messages"][-1]["content"]
    assert [e.step for e in tracer.entries] == ["t", "t (repair)"]


def test_retries_then_falls_back(fake_llm):
    def reply(messages, model):
        if model == "test/reasoning":
            return TimeoutError("boom")
        return "fine"

    fake_llm.on("hello", reply)
    with tracing.tracing() as tracer:
        result = llm.chat("reasoning", [{"role": "user", "content": "hello"}], step="s")
    assert result.model == "test/reasoning-fallback"
    assert [e.success for e in tracer.entries] == [False, False, False, True]
    assert tracer.entries[-1].note == "fallback model"


def test_all_models_fail(fake_llm):
    fake_llm.on("hello", TimeoutError("down"))
    with pytest.raises(llm.LLMError):
        llm.chat("fast", [{"role": "user", "content": "hello"}])
