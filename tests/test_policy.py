import pytest

from authassist import policy
from authassist.schemas import Criterion

LONG_TEXT = "Aetna considers MRI of the lumbar spine medically necessary when ... " * 40


class FakeTavily:
    def __init__(self) -> None:
        self.searches = 0
        self.extracts = 0

    def search(self, query, search_depth, max_results, include_domains):
        self.searches += 1
        return {
            "results": [
                {
                    "url": "https://www.aetna.com/cpb/medical/data/200_299/0236.html",
                    "title": "CPB 0236",
                    "score": 0.9,
                },
                {"url": "https://random-blog.example.com/mri", "title": "Blog", "score": 0.99},
            ]
        }

    def extract(self, urls):
        self.extracts += 1
        return {"results": [{"url": urls[0], "raw_content": LONG_TEXT}]}


@pytest.fixture
def tavily(monkeypatch, fake_llm):
    fake_llm.on("web search queries", {"queries": ["aetna lumbar mri policy"]})
    client = FakeTavily()
    monkeypatch.setattr(policy, "_tavily", lambda: client)
    return client


def test_live_lookup_prefers_payer_domain_and_caches(tavily):
    bundle = policy.find_policy("aetna")
    assert bundle.policy.source == "tavily"
    assert "aetna.com" in bundle.policy.url
    assert bundle.text == LONG_TEXT and bundle.criteria is None
    assert policy.cache_path("aetna", "lumbar_mri").exists()

    again = policy.find_policy("aetna")
    assert again.policy.source == "cache" and "cached" in again.notice
    assert tavily.extracts == 1  # cache reused, no new credits spent


def test_force_refresh_bypasses_cache(tavily):
    policy.find_policy("aetna")
    policy.find_policy("aetna", force_refresh=True)
    assert tavily.extracts == 2


def test_criteria_saved_into_cache(tavily):
    policy.find_policy("aetna")
    crit = [Criterion(id="x", description="d", policy_citation="c")]
    policy.save_criteria("aetna", "lumbar_mri", crit)
    assert policy.find_policy("aetna").criteria == crit


def test_tavily_down_uses_snapshot(fake_llm):
    fake_llm.on("web search queries", {"queries": ["q"]})
    bundle = policy.find_policy("molina")  # conftest makes Tavily raise
    assert bundle.policy.source == "snapshot"
    assert bundle.criteria and "snapshot" in bundle.notice


def test_unknown_payer():
    with pytest.raises(ValueError):
        policy.find_policy("nope")


def test_domain_matching():
    assert policy.domain_matches("https://www.aetna.com/x", ["aetna.com"])
    assert not policy.domain_matches("https://notaetna.com/x", ["aetna.com"])
