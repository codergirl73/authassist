"""Step 4: convert policy text into atomic, checkable criteria."""

from __future__ import annotations

import re

from authassist import llm
from authassist.schemas import Criterion, CriterionList, PolicyDoc

MAX_POLICY_CHARS = 60_000

SYSTEM = """You convert an insurer's medical policy into a prior-authorization checklist.
Produce criteria ONLY for: {procedure} (CPT {cpt}) for {condition}, initial imaging.
Rules:
- Each criterion must be atomic and checkable against a clinical note
  (e.g. ">= 6 weeks of conservative therapy documented", "Neurological exam documented").
- Typically 4-8 criteria. Do not include administrative items (member eligibility, forms, codes).
- For "any of" red-flag indications that justify imaging without conservative therapy
  (cauda equina, suspected malignancy, infection, fracture/trauma, progressive neurological deficit),
  create one criterion per red flag with bypass_group = "red_flags". All other criteria: bypass_group = null.
- category must be one of: {categories}.
- policy_citation: the section heading (or nearest heading) from the policy, followed by " - " and the URL.
- ids: short snake_case, unique.
- Base every criterion on the policy text; do not add requirements the policy does not state."""


def _clean_id(value: str, used: set[str]) -> str:
    base = re.sub(r"[^a-z0-9_]+", "_", value.lower()).strip("_") or "criterion"
    cid, n = base, 2
    while cid in used:
        cid, n = f"{base}_{n}", n + 1
    used.add(cid)
    return cid


def policy_to_criteria(policy_text: str, policy: PolicyDoc, proc: dict) -> list[Criterion]:
    system = SYSTEM.format(
        procedure=proc["procedure"],
        cpt=proc["cpt"],
        condition=proc["condition"],
        categories=", ".join(proc["categories"]),
    )
    user = f"POLICY: {policy.title}\nURL: {policy.url}\n\nPOLICY TEXT:\n<<<\n{policy_text[:MAX_POLICY_CHARS]}\n>>>"
    parsed, _ = llm.chat_model(
        "reasoning",
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        CriterionList,
        step="policy -> criteria",
    )
    used: set[str] = set()
    criteria = []
    for c in parsed.criteria:
        c.id = _clean_id(c.id, used)
        if c.category not in proc["categories"]:
            c.category = "other"
        if c.bypass_group and c.bypass_group != "red_flags":
            c.bypass_group = "red_flags" if c.category == "red_flag" else None
        if c.category == "red_flag":
            c.bypass_group = "red_flags"
        if policy.url not in c.policy_citation:
            c.policy_citation = f"{c.policy_citation} - {policy.url}"
        criteria.append(c)
    return criteria
