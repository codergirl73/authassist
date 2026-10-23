"""Step 3: find the payer's current published policy with Tavily (search +
extract), cache it locally, and fall back to committed criteria snapshots.

Full policy text lives only in CACHE_DIR (git-ignored), never in the repo."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel

from authassist import config, llm, tracing
from authassist.schemas import Criterion, PolicyDoc

log = logging.getLogger(__name__)

SNAPSHOT_DIR = config.DATA_DIR / "policy_criteria_snapshots"
MIN_POLICY_CHARS = 1500


class PolicyBundle(BaseModel):
    policy: PolicyDoc
    text: str | None = None  # full text, only from Tavily/cache
    criteria: list[Criterion] | None = None
    notice: str | None = None  # shown in the UI, e.g. "Using cached policy from ..."


class Queries(BaseModel):
    queries: list[str]


def cache_path(payer: str, procedure: str) -> Path:
    return config.CACHE_DIR / "policies" / f"{payer}_{procedure}.json"


def snapshot_path(payer: str, procedure: str) -> Path:
    return SNAPSHOT_DIR / f"{payer}_{procedure}.json"


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def domain_matches(url: str, domains: list[str]) -> bool:
    host = urlparse(url).netloc.lower()
    return any(host == d or host.endswith("." + d) for d in domains)


# ---------------------------------------------------------------- cache


def load_cache(payer: str, procedure: str) -> PolicyBundle | None:
    path = cache_path(payer, procedure)
    if not path.exists():
        return None
    bundle = PolicyBundle.model_validate_json(path.read_text())
    bundle.policy.source = "cache"
    bundle.notice = (
        f"Using cached policy retrieved {bundle.policy.retrieved_at:%Y-%m-%d} (originally found via Tavily)"
    )
    return bundle


def save_cache(bundle: PolicyBundle, payer: str, procedure: str) -> None:
    path = cache_path(payer, procedure)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(bundle.model_dump_json(indent=1))


def save_criteria(payer: str, procedure: str, criteria: list[Criterion]) -> None:
    bundle = load_cache(payer, procedure)
    if bundle is None:
        return
    bundle.criteria = criteria
    bundle.notice = None
    bundle.policy.source = "tavily"
    save_cache(bundle, payer, procedure)


def load_snapshot(payer: str, procedure: str) -> PolicyBundle | None:
    path = snapshot_path(payer, procedure)
    if not path.exists():
        return None
    snap = json.loads(path.read_text())
    policy = PolicyDoc(
        payer=snap["payer"],
        procedure=snap["procedure"],
        title=snap["title"],
        url=snap["url"],
        retrieved_at=datetime.fromisoformat(snap["retrieved_at"]),
        text_hash=snap.get("text_hash", ""),
        source="snapshot",
        is_fallback=snap.get("is_fallback", False),
    )
    criteria = [Criterion.model_validate(c) for c in snap["criteria"]]
    return PolicyBundle(
        policy=policy,
        criteria=criteria,
        notice=f"Using cached policy criteria snapshot from {policy.retrieved_at:%Y-%m-%d} (live lookup unavailable)"
        + (
            " - curated seed criteria, not extracted from the policy text"
            if snap.get("origin") == "curated_seed"
            else ""
        ),
    )


def write_snapshot(payer: str, procedure: str, bundle: PolicyBundle, criteria: list[Criterion]) -> Path:
    """Commit-safe snapshot: metadata + extracted criteria only (no policy text)."""
    path = snapshot_path(payer, procedure)
    path.parent.mkdir(parents=True, exist_ok=True)
    p = bundle.policy
    path.write_text(
        json.dumps(
            {
                "payer": p.payer,
                "procedure": p.procedure,
                "title": p.title,
                "url": p.url,
                "retrieved_at": p.retrieved_at.isoformat(),
                "text_hash": p.text_hash,
                "is_fallback": p.is_fallback,
                "origin": "tavily+nemotron",
                "criteria": [c.model_dump() for c in criteria],
            },
            indent=2,
        )
    )
    return path


# ---------------------------------------------------------------- Tavily


def write_queries(payer_name: str, proc: dict) -> list[str]:
    template = [
        f"{payer_name} {proc['procedure']} medical policy clinical criteria",
        f"{payer_name} clinical policy bulletin {proc['condition']} imaging MRI",
    ]
    try:
        parsed, _ = llm.chat_model(
            "fast",
            [
                {
                    "role": "user",
                    "content": (
                        f"Write 2 short web search queries to find {payer_name}'s current published "
                        f"medical/clinical policy with coverage criteria for {proc['procedure']} "
                        f"(CPT {proc['cpt']}) for {proc['condition']}."
                    ),
                }
            ],
            Queries,
            step="policy: write search queries",
        )
        return parsed.queries[:2] or template
    except Exception as err:  # query writing is a nicety; templates are fine
        log.warning("Query writing failed (%s); using templates", type(err).__name__)
        return template


def _tavily():
    from tavily import TavilyClient

    return TavilyClient(api_key=config.tavily_api_key())


def search_candidates(queries: list[str], domains: list[str]) -> list[dict]:
    client = _tavily()
    seen: dict[str, dict] = {}
    for q in queries:
        with tracing.timed(
            "policy: Tavily search", "tavily", "tavily.search (advanced)", note=", ".join(domains)
        ):
            res = client.search(q, search_depth="advanced", max_results=5, include_domains=domains)
        for r in res.get("results", []):
            if domain_matches(r["url"], domains) and r["url"] not in seen:
                seen[r["url"]] = r
    return sorted(seen.values(), key=lambda r: r.get("score", 0), reverse=True)


def extract_text(url: str) -> str:
    with tracing.timed("policy: Tavily extract", "tavily", "tavily.extract", note=url[:80]):
        res = _tavily().extract(urls=[url])
    results = res.get("results", [])
    return (results[0].get("raw_content") or "") if results else ""


def fetch_live(payer_key: str, proc: dict) -> PolicyBundle | None:
    payer_cfg = proc["payers"][payer_key]
    attempts = [(payer_cfg["domains"], False)]
    if payer_key != proc["fallback_payer"]:
        attempts.append((proc["fallback_domains"], True))

    for domains, is_fallback in attempts:
        name = proc["payers"][proc["fallback_payer"]]["name"] if is_fallback else payer_cfg["name"]
        queries = write_queries(name, proc)
        if payer_cfg.get("search_hint") and not is_fallback:
            queries.insert(0, payer_cfg["search_hint"])
        for cand in search_candidates(queries[:3], domains)[:3]:
            text = extract_text(cand["url"])
            if len(text) < MIN_POLICY_CHARS:
                continue
            policy = PolicyDoc(
                payer=f"{name} (fallback for {payer_cfg['name']})" if is_fallback else name,
                procedure=proc["procedure"],
                title=cand.get("title") or cand["url"],
                url=cand["url"],
                retrieved_at=datetime.now(UTC),
                text_hash=text_hash(text),
                source="tavily",
                is_fallback=is_fallback,
            )
            return PolicyBundle(policy=policy, text=text)
    return None


def find_policy(
    payer_key: str, procedure_key: str = "lumbar_mri", force_refresh: bool = False
) -> PolicyBundle:
    proc = config.procedure_config(procedure_key)
    if payer_key not in proc["payers"]:
        raise ValueError(f"Unknown payer {payer_key!r}")

    if not force_refresh:
        cached = load_cache(payer_key, procedure_key)
        if cached:
            return cached

    try:
        live = fetch_live(payer_key, proc)
        if live:
            save_cache(live, payer_key, procedure_key)
            return live
        log.warning("Tavily found no usable policy for %s", payer_key)
    except Exception as err:
        log.warning("Live policy lookup failed for %s: %s", payer_key, type(err).__name__)

    snap = load_snapshot(payer_key, procedure_key) or load_snapshot(proc["fallback_payer"], procedure_key)
    if snap:
        return snap
    raise RuntimeError(f"No policy available for {payer_key}: live lookup failed and no snapshot exists")
