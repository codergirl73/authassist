"""CLI: python -m authassist.cli --case data/synthetic_notes/case_04 [--addendum "..."] [--letter out.pdf]"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from authassist import pipeline
from authassist.schemas import CaseInput

ICON = {"met": "[MET]    ", "unclear": "[UNCLEAR]", "missing": "[MISSING]"}


def load_case(case_dir: Path, payer: str | None = None) -> CaseInput:
    meta = json.loads((case_dir / "case.json").read_text())
    txt, png = case_dir / "note.txt", case_dir / "note.png"
    if txt.exists():
        return CaseInput(
            case_id=meta["case_id"],
            payer=payer or meta["payer"],
            procedure=meta["procedure"],
            note_text=txt.read_text(),
        )
    return CaseInput(
        case_id=meta["case_id"],
        payer=payer or meta["payer"],
        procedure=meta["procedure"],
        file_bytes=png.read_bytes(),
        filename="note.png",
    )


def print_result(r: pipeline.PipelineResult) -> None:
    a = r.assessment
    crit = {c.id: c for c in a.criteria}
    print(f"\n=== {r.case_id} | {a.payer} | {a.procedure}")
    print(
        f"Policy: {a.policy.title}\n        {a.policy.url} (retrieved {a.policy.retrieved_at:%Y-%m-%d}, {a.policy.source})"
    )
    if r.policy_notice:
        print(f"NOTE: {r.policy_notice}")
    prev = f"{r.previous_score} -> " if r.previous_score is not None else ""
    print(
        f"\nREADINESS: {prev}{a.readiness_score}/100  [{a.status.upper()}]"
        + ("  (red-flag bypass)" if a.red_flag_bypass else "")
    )
    print("\nCriteria:")
    for res in a.results:
        c = crit[res.criterion_id]
        tag = (
            ("[RED FLAG PRESENT]" if res.status == "met" else "[no red flag]     ")
            if c.bypass_group
            else ICON[res.status]
        )
        print(f"  {tag} {c.description}")
        if res.evidence_quote:
            print(f'      "{res.evidence_quote}" {"(verified)" if res.quote_verified else "(NOT VERIFIED)"}')
    if a.missing_items:
        print("\nMissing:")
        for m in a.missing_items:
            print(f"  - {m}")
    print("\nTrace:")
    for e in r.traces:
        print(f"  {e.step:32} {e.role:9} {e.model:42} {e.latency_ms:6}ms {'ok' if e.success else 'FAIL'}")
    for w in r.warnings:
        print(f"  warning: {w}")


def main() -> None:
    ap = argparse.ArgumentParser(description="AuthAssist prior-auth readiness check")
    ap.add_argument("--case", required=True, type=Path, help="case folder, e.g. data/synthetic_notes/case_04")
    ap.add_argument("--payer", help="override payer key (aetna | molina | medicare)")
    ap.add_argument("--addendum", help="clinician addendum text; re-checks after the first pass")
    ap.add_argument("--letter", type=Path, help="write letter + summary PDF to this path")
    ap.add_argument("--refresh", action="store_true", help="force a fresh Tavily policy lookup")
    args = ap.parse_args()
    logging.basicConfig(level=logging.ERROR)

    result = pipeline.run_pipeline(
        load_case(args.case, args.payer),
        force_refresh=args.refresh,
        progress=lambda label, detail: print(f"  {label} - {detail}"),
    )
    print_result(result)
    if args.addendum:
        result = pipeline.recheck_with_addendum(
            result, args.addendum, progress=lambda label, detail: print(f"  {label} - {detail}")
        )
        print_result(result)
    if args.letter:
        draft, pdf_bytes, _ = pipeline.make_letter(result)
        args.letter.write_bytes(pdf_bytes)
        print(f"\nLetter draft:\n{draft.body_markdown}\n\nPDF written to {args.letter}")


if __name__ == "__main__":
    main()
