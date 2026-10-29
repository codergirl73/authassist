import base64

from fastapi.testclient import TestClient

from api.main import app
from tests.test_pipeline import setup

client = TestClient(app)


def test_health():
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/_stcore/health").status_code == 200  # legacy Render health-check path


def test_assess_letter_roundtrip(fake_llm):
    setup(fake_llm, {"neuro_exam_documented": ("met", "left Achilles reflex diminished (1+)")})
    r = client.post("/assess", json={"example_case": "case_01"})
    assert r.status_code == 200, r.text
    result = r.json()
    assert result["assessment"]["status"] == "not_ready"
    assert any(t["role"] == "reasoning" for t in result["traces"])

    r2 = client.post("/recheck", json={"result": result, "addendum": "Extra info."})
    assert r2.status_code == 200 and r2.json()["previous_score"] is not None

    r3 = client.post("/letter", json=r2.json())
    assert r3.status_code == 200
    assert base64.b64decode(r3.json()["pdf_base64"])[:4] == b"%PDF"


def test_demo_mode_blocks_free_text(monkeypatch):
    monkeypatch.setattr("authassist.config.DEMO_MODE", True)
    assert client.post("/assess", json={"payer": "aetna", "note_text": "x"}).status_code == 403


def test_path_traversal_rejected():
    assert client.post("/assess", json={"example_case": "../../config"}).status_code == 404


def test_missing_key_is_503(monkeypatch):
    monkeypatch.setattr(
        "authassist.llm.client", lambda: (_ for _ in ()).throw(RuntimeError("NEBIUS_API_KEY is not set"))
    )
    r = client.post("/assess", json={"example_case": "case_01"})
    assert r.status_code == 503 and "NEBIUS_API_KEY" in r.json()["detail"]


def test_config_endpoint_lists_cases_and_payers():
    cfg = client.get("/api/config").json()
    assert {"aetna", "molina", "medicare"} <= set(cfg["payers"])
    assert len(cfg["cases"]) == 8
    scanned = next(c for c in cfg["cases"] if c["id"] == "case_04")
    assert scanned["note_text"] is None and scanned["image_url"] == "/api/cases/case_04/image"
    assert set(cfg["models"]) == {"vision", "fast", "reasoning"}


def test_case_image_and_traversal():
    assert client.get("/api/cases/case_04/image").headers["content-type"] == "image/png"
    assert client.get("/api/cases/case_01/image").status_code == 404  # typed note has no image
    assert client.get("/api/cases/..%2F..%2Fconfig/image").status_code == 404


def test_assess_stream_emits_progress_then_result(fake_llm):
    import json

    setup(fake_llm, {"neuro_exam_documented": ("met", "left Achilles reflex diminished (1+)")})
    with client.stream("POST", "/assess/stream", json={"example_case": "case_01"}) as r:
        events = [json.loads(line) for line in r.iter_lines() if line]
    kinds = [e["type"] for e in events]
    assert kinds[-1] == "result" and kinds.count("progress") >= 3
    assert events[-1]["data"]["assessment"]["status"] == "not_ready"


def test_stream_reports_errors_as_events(monkeypatch):
    import json

    from authassist import pipeline

    def boom(*a, **k):
        raise RuntimeError("NEBIUS_API_KEY is not set")

    monkeypatch.setattr(pipeline, "run_pipeline", boom)
    with client.stream("POST", "/assess/stream", json={"example_case": "case_01"}) as r:
        events = [json.loads(line) for line in r.iter_lines() if line]
    assert events[-1]["type"] == "error" and "NEBIUS_API_KEY" in events[-1]["message"]


def test_web_app_is_served():
    r = client.get("/")
    assert r.status_code == 200 and "AuthAssist" in r.text
    assert client.get("/app.js").status_code == 200
