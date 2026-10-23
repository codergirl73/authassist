import base64

from fastapi.testclient import TestClient

from api.main import app
from tests.test_pipeline import setup

client = TestClient(app)


def test_health():
    assert client.get("/health").json()["status"] == "ok"


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
