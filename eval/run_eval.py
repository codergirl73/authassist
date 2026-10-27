"""Run the pipeline on all synthetic cases and compare with expected.json.

Usage: python eval/run_eval.py [--cases case_01 case_04] [--out eval/results.md]
"""

from __future__ import annotations

import argparse
import difflib
import json
import logging
import sys
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from authassist import config, pipeline  # noqa: E402
from authassist.cli import load_case  # noqa: E402

CASES_DIR = ROOT / "data" / "synthetic_notes"
RANK = {"missing": 0, "unclear": 1, "met": 2}


def category_statuses(assessment) -> dict[str, str]:
    """Collapse criteria to canonical categories. red_flag: met if ANY red flag is met;
    other categories: the weakest status among their criteria."""
    by_id = {r.criterion_id: r.status for r in assessment.results}
    out: dict[str, str] = {}
    for c in assessment.criteria:
        status = by_id.get(c.id, "missing")
        if c.category not in out:
            out[c.category] = status
        elif c.category == "red_flag":
            out[c.category] = "met" if "met" in (status, out[c.category]) else "missing"
        else:
            out[c.category] = min(out[c.category], status, key=RANK.get)
    return out


def run_case(case_dir: Path) -> dict:
    expected = json.loads((case_dir / "expected.json").read_text())
    meta = json.loads((case_dir / "case.json").read_text())
    start = time.perf_counter()
    try:
        result = pipeline.run_pipeline(load_case(case_dir))
    except Exception as err:
        return {
            "case": case_dir.name,
            "meta": meta,
            "expected": expected,
            "error": f"{type(err).__name__}: {err}",
        }
    actual = category_statuses(result.assessment)
    crit_checks = {cat: (exp, actual.get(cat, "absent")) for cat, exp in expected["criteria"].items()}
    quotes = [r for r in result.assessment.results if r.evidence_quote]
    row = {
        "case": case_dir.name,
        "meta": meta,
        "expected": expected,
        "outcome": result.assessment.status,
        "score": result.assessment.readiness_score,
        "bypass": result.assessment.red_flag_bypass,
        "crit_checks": crit_checks,
        "quotes": len(quotes),
        "quotes_verified": sum(r.quote_verified for r in quotes),
        "traces": [t.model_dump() for t in result.traces],
        "seconds": time.perf_counter() - start,
        "policy_source": result.assessment.policy.source,
    }
    ref = case_dir / "reference_text.txt"
    if ref.exists():
        row["transcription_similarity"] = difflib.SequenceMatcher(
            None, " ".join(ref.read_text().split()), " ".join(result.note_text.split())
        ).ratio()
    return row


def summarize(rows: list[dict]) -> str:
    ok_rows = [r for r in rows if "error" not in r]
    # "absent" = this payer's policy has no criterion in that category (e.g. Molina has no separate
    # neuro-exam requirement), so the expectation cannot be tested. Reported separately, not as errors.
    scored = [(e, a) for r in ok_rows for e, a in r["crit_checks"].values() if a != "absent"]
    crit_total = len(scored)
    crit_ok = sum(e == a for e, a in scored)
    n_a = sum(a == "absent" for r in ok_rows for _, a in r["crit_checks"].values())
    outcome_ok = sum(r["outcome"] == r["expected"]["outcome"] for r in ok_rows)
    bypass_ok = sum(r["bypass"] == r["expected"]["red_flag_bypass"] for r in ok_rows)
    q_total = sum(r["quotes"] for r in ok_rows)
    q_ok = sum(r["quotes_verified"] for r in ok_rows)

    step_lat: dict[tuple[str, str], list[int]] = defaultdict(list)
    tokens = 0
    for r in ok_rows:
        for t in r["traces"]:
            if t["success"]:
                step_lat[(t["step"], t["model"])].append(t["latency_ms"])
            tokens += (t["prompt_tokens"] or 0) + (t["completion_tokens"] or 0)

    models_line = ", ".join(
        f"{k}=`{v['model']}`"
        for k, v in config.models_config().items()
        if isinstance(v, dict) and "model" in v
    )
    pct = lambda a, b: f"{a}/{b} ({100 * a / b:.0f}%)" if b else "n/a"  # noqa: E731
    lines = [
        "# AuthAssist evaluation results",
        "",
        f"Run date: {date.today().isoformat()} - {len(rows)} synthetic cases - procedure: MRI lumbar spine (CPT 72148)",
        f"Models: {models_line}",
        "",
        "## Summary",
        "",
        "| Metric | Result |",
        "|---|---|",
        f"| Overall outcome accuracy (ready / needs attention / not ready) | {pct(outcome_ok, len(ok_rows))} |",
        f"| Per-criterion accuracy (key criteria in expected.json) | {pct(crit_ok, crit_total)} |",
        f"| Expectations not applicable (payer policy has no such criterion) | {n_a} |",
        f"| Red-flag bypass accuracy | {pct(bypass_ok, len(ok_rows))} |",
        f"| Evidence quotes verified verbatim in note | {pct(q_ok, q_total)} |",
        f"| Cases that errored | {len(rows) - len(ok_rows)} |",
        f"| Total tokens | {tokens:,} |",
        "",
        "## Per case",
        "",
        "| Case | Scenario | Input | Expected | Actual | Score | Bypass | Criteria correct | Time |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        if "error" in r:
            lines.append(
                f"| {r['case']} | {r['meta']['scenario']} | {r['meta']['input']} | {r['expected']['outcome']} | ERROR | - | - | - | - |"
            )
            continue
        c_ok = sum(e == a for e, a in r["crit_checks"].values() if a != "absent")
        c_tot = sum(a != "absent" for _, a in r["crit_checks"].values())
        mark = "OK" if r["outcome"] == r["expected"]["outcome"] else "MISS"
        lines.append(
            f"| {r['case']} | {r['meta']['scenario']} | {r['meta']['input']} | {r['expected']['outcome']} | "
            f"{r['outcome']} ({mark}) | {r['score']} | {'yes' if r['bypass'] else 'no'} | "
            f"{c_ok}/{c_tot} | {r['seconds']:.1f}s |"
        )
    sims = [(r["case"], r["transcription_similarity"]) for r in ok_rows if "transcription_similarity" in r]
    if sims:
        lines += [
            "",
            "## Vision transcription (scanned cases)",
            "",
            "| Case | Similarity to source text |",
            "|---|---|",
        ]
        lines += [f"| {c} | {s:.1%} |" for c, s in sims]

    lines += [
        "",
        "## Average latency per step",
        "",
        "| Step | Model | Calls | Avg latency |",
        "|---|---|---|---|",
    ]
    for (step, model), lats in sorted(step_lat.items()):
        lines.append(f"| {step} | `{model}` | {len(lats)} | {sum(lats) / len(lats) / 1000:.1f}s |")

    failures = []
    notes: list[str] = []
    for r in rows:
        if "error" in r:
            failures.append(f"- **{r['case']}** errored: `{r['error']}`")
            continue
        if r["outcome"] != r["expected"]["outcome"]:
            failures.append(
                f"- **{r['case']}** outcome: expected `{r['expected']['outcome']}`, got `{r['outcome']}` (score {r['score']})."
            )
        for cat, (exp, act) in r["crit_checks"].items():
            if act == "absent":
                notes.append(
                    f"- {r['case']} `{cat}`: not applicable - the payer's policy has no such criterion."
                )
            elif exp != act:
                failures.append(f"- **{r['case']}** `{cat}`: expected `{exp}`, got `{act}`.")
        if r["quotes"] != r["quotes_verified"]:
            failures.append(
                f"- **{r['case']}**: {r['quotes'] - r['quotes_verified']} evidence quote(s) failed verbatim verification (downgraded automatically)."
            )
    lines += ["", "## Failure cases", ""] + (failures or ["- None in this run."])
    if notes:
        lines += ["", "## Not applicable (not counted as errors)", ""] + notes
    lines += [
        "",
        "_Policy criteria source per case: "
        + ", ".join(f"{r['case']}={r.get('policy_source', '-')}" for r in rows)
        + "._",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", nargs="*", help="subset, e.g. case_01 case_04")
    ap.add_argument("--out", type=Path, default=ROOT / "eval" / "results.md")
    args = ap.parse_args()
    logging.basicConfig(level=logging.ERROR)

    dirs = sorted(d for d in CASES_DIR.iterdir() if d.is_dir() and (not args.cases or d.name in args.cases))
    rows = []
    for d in dirs:
        print(f"running {d.name} ...", flush=True)
        rows.append(run_case(d))
    report = summarize(rows)
    print("\n" + report)
    args.out.write_text(report)
    print(f"\nwrote {args.out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
