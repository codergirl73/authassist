"""AuthAssist Streamlit UI. Run: streamlit run ui/app.py"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from authassist import config, pipeline  # noqa: E402
from authassist.cli import load_case  # noqa: E402
from authassist.schemas import CaseInput  # noqa: E402

CASES_DIR = config.DATA_DIR / "synthetic_notes"
PROC = config.procedure_config("lumbar_mri")
ROLE_LABEL = {
    "vision": "Vision",
    "fast": "Fast",
    "reasoning": "Reasoning",
    "tavily": "Tavily",
    "code": "Code",
}

st.set_page_config(page_title="AuthAssist", page_icon="🩺", layout="wide")

st.markdown(
    """
<style>
.block-container {padding-top: 1.6rem; max-width: 1200px;}
.aa-banner {background:#fff4e5; border:1px solid #f5c27a; color:#6b3d00; padding:.6rem .9rem;
  border-radius:8px; font-size:.92rem; margin-bottom:1rem;}
.aa-card {border:1px solid rgba(128,128,128,.25); border-radius:10px; padding:.85rem 1rem; margin-bottom:.6rem;}
.aa-crit-title {font-weight:600; margin-bottom:.25rem;}
.aa-quote {background:rgba(255,213,79,.35); padding:.1rem .3rem; border-radius:4px; font-style:italic;}
.aa-badge {display:inline-block; font-size:.72rem; padding:.05rem .45rem; border-radius:999px; margin-left:.35rem;
  border:1px solid currentColor; vertical-align:middle;}
.aa-ok {color:#1b7f3b;} .aa-warn {color:#b26a00;} .aa-bad {color:#b3261e;} .aa-muted {color:#7a7f87;}
.aa-small {font-size:.8rem; color:#7a7f87;}
.aa-gauge {width:150px; height:150px; border-radius:50%; display:flex; align-items:center; justify-content:center; margin:auto;}
.aa-gauge-inner {width:118px; height:118px; border-radius:50%; background:var(--background-color, #fff);
  display:flex; flex-direction:column; align-items:center; justify-content:center;}
.aa-gauge-num {font-size:2.3rem; font-weight:700; line-height:1;}
</style>
<div class="aa-banner">⚠️ <b>Demo uses synthetic data only.</b> Do not upload real patient information.
Drafts require clinician review. AuthAssist never submits anything to an insurer.</div>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------- helpers


def case_options() -> dict[str, dict]:
    out = {}
    for d in sorted(p for p in CASES_DIR.iterdir() if p.is_dir()):
        meta = json.loads((d / "case.json").read_text())
        label = f"{d.name.replace('_', ' ').title()} — {meta['scenario']}"
        if meta["input"] == "scanned_png":
            label += " (scanned fax)"
        out[label] = {"dir": d, **meta}
    return out


def status_style(status: str) -> tuple[str, str, str]:
    return {
        "ready": ("Ready to submit", "#1b7f3b", "aa-ok"),
        "needs_attention": ("Needs attention", "#b26a00", "aa-warn"),
        "not_ready": ("Not ready", "#b3261e", "aa-bad"),
    }[status]


def gauge(score: int, status: str) -> str:
    label, color, _ = status_style(status)
    return f"""
<div class="aa-gauge" style="background:conic-gradient({color} {score * 3.6}deg, rgba(128,128,128,.18) 0deg);">
  <div class="aa-gauge-inner"><div class="aa-gauge-num" style="color:{color}">{score}</div>
  <div class="aa-small">/ 100</div></div></div>
<div style="text-align:center; font-weight:700; color:{color}; margin-top:.4rem; font-size:1.1rem">{label}</div>"""


def esc(s: str | None) -> str:
    return html.escape(s or "")


def link_from_citation(citation: str) -> str:
    parts = citation.rsplit(" - ", 1)
    if len(parts) == 2 and parts[1].startswith("http"):
        return f'{esc(parts[0])} — <a href="{esc(parts[1])}" target="_blank">source</a>'
    return esc(citation)


def criterion_card(c, r, excused: bool = False) -> str:
    if c.bypass_group:
        icon, cls, label = (
            ("🚩", "aa-bad", "Present") if r.status == "met" else ("◻️", "aa-muted", "Not present")
        )
    else:
        icon, cls, label = {
            "met": ("✅", "aa-ok", "Met"),
            "unclear": ("⚠️", "aa-warn", "Unclear"),
            "missing": ("❌", "aa-bad", "Missing"),
        }[r.status]
    quote = ""
    if r.evidence_quote:
        badge = (
            '<span class="aa-badge aa-ok">✓ verified in note</span>'
            if r.quote_verified
            else '<span class="aa-badge aa-bad">✗ not found in note</span>'
        )
        quote = f'<div style="margin:.3rem 0">“<span class="aa-quote">{esc(r.evidence_quote)}</span>”{badge}</div>'
    note = "<div class='aa-small'>Excused by red-flag bypass</div>" if excused else ""
    style = ' style="opacity:.55"' if excused else ""
    return f"""<div class="aa-card"{style}>
<div class="aa-crit-title">{icon} {esc(c.description)} <span class="aa-badge {cls}">{label}</span></div>
{quote}<div class="aa-small">{esc(r.reasoning)}</div>
<div class="aa-small" style="margin-top:.25rem">📄 {link_from_citation(c.policy_citation)}</div>{note}</div>"""


def run_with_progress(title: str, fn):
    with st.status(title, expanded=True) as box:

        def progress(label: str, detail: str) -> None:
            box.write(f"**{label}** — {detail}")

        try:
            out = fn(progress)
        except Exception as err:
            box.update(label="Something went wrong", state="error")
            st.error(f"{type(err).__name__}: {err}")
            if "API_KEY" in str(err):
                st.info("Set NEBIUS_API_KEY and TAVILY_API_KEY in the environment (see .env.example).")
            return None
        box.update(label=f"{title} — done", state="complete", expanded=False)
        return out


def traces_table(entries) -> list[dict]:
    return [
        {
            "Step": e.step,
            "Role": ROLE_LABEL.get(e.role, e.role),
            "Model / tool": e.model,
            "Latency (s)": round(e.latency_ms / 1000, 2),
            "Prompt tok": e.prompt_tokens,
            "Completion tok": e.completion_tokens,
            "OK": "✓" if e.success else "✗",
            "Note": e.note or "",
        }
        for e in entries
    ]


# ---------------------------------------------------------------- header + input

st.title("🩺 AuthAssist")
st.caption("Catch the missing evidence in a prior-authorization request — before the insurer does.")

tab_check, tab_letter, tab_trace, tab_about = st.tabs(
    ["① Check readiness", "② Letter & PDF", "How it works · Model trace", "About & limitations"]
)
ss = st.session_state

with tab_check:
    cases = case_options()
    payer_keys = list(PROC["payers"])
    left, right = st.columns([3, 2])
    with left:
        choice = st.selectbox("Load example case (synthetic)", list(cases))
        case = cases[choice]
        upload, pasted = None, None
        if not config.DEMO_MODE:
            with st.expander("…or use your own note (processed in memory only)"):
                upload = st.file_uploader(
                    "Clinical note (PDF, PNG, JPG, TXT)", type=["pdf", "png", "jpg", "jpeg", "txt"]
                )
                pasted = st.text_area("Or paste note text", height=140)
    with right:
        payer = st.selectbox(
            "Payer",
            payer_keys,
            index=payer_keys.index(case["payer"]),
            format_func=lambda k: PROC["payers"][k]["name"],
            key=f"payer_{case['case_id']}",
        )
        st.text_input("Procedure", PROC["display_name"], disabled=True)

    with st.expander("View the clinical note"):
        if pasted or upload:
            st.caption("Using your uploaded / pasted note.")
        elif (case["dir"] / "note.txt").exists():
            st.code((case["dir"] / "note.txt").read_text(), language=None)
        else:
            st.image(str(case["dir"] / "note.png"), caption="Scanned fax — will be read by the vision model")

    if st.button("Check readiness", type="primary", width="stretch"):
        if pasted and pasted.strip():
            case_input = CaseInput(case_id="user_note", payer=payer, note_text=pasted)
        elif upload is not None:
            case_input = CaseInput(
                case_id="user_upload", payer=payer, file_bytes=upload.getvalue(), filename=upload.name
            )
        else:
            case_input = load_case(case["dir"], payer)
        result = run_with_progress(
            "Checking readiness", lambda p: pipeline.run_pipeline(case_input, progress=p)
        )
        if result:
            ss.result, ss.letter = result, None
            ss.letter_traces = []

    result = ss.get("result")
    if result:
        a = result.assessment
        crit = {c.id: c for c in a.criteria}
        st.divider()
        g_col, info_col = st.columns([1, 2])
        with g_col:
            st.markdown(gauge(a.readiness_score, a.status), unsafe_allow_html=True)
            if result.previous_score is not None:
                st.metric(
                    "After addendum",
                    f"{a.readiness_score}",
                    f"{a.readiness_score - result.previous_score:+d} (was {result.previous_score})",
                )
        with info_col:
            if a.red_flag_bypass:
                st.error(
                    "🚩 **Red-flag indication documented** — conservative-therapy requirements are excused; imaging is justified now."
                )
            if a.missing_items:
                st.markdown("**What's missing**")
                for m in a.missing_items:
                    st.markdown(f"- {m}")
            elif a.status == "ready":
                st.success("All required criteria are documented with verified evidence.")
            p = a.policy
            src = {
                "tavily": "🔎 Found via Tavily",
                "cache": "🗂️ Cached Tavily result",
                "snapshot": "🗂️ Cached snapshot",
            }[p.source]
            st.markdown(
                f"""<div class="aa-card"><div class="aa-small">POLICY SOURCE · {src}</div>
<div class="aa-crit-title">{esc(p.payer)} — <a href="{esc(p.url)}" target="_blank">{esc(p.title)}</a></div>
<div class="aa-small">Retrieved {p.retrieved_at:%Y-%m-%d}{" · Medicare/CMS guidance used as fallback" if p.is_fallback else ""}</div></div>""",
                unsafe_allow_html=True,
            )
            if result.policy_notice:
                st.caption(f"ℹ️ {result.policy_notice}")

        required = [(crit[r.criterion_id], r) for r in a.results if not crit[r.criterion_id].bypass_group]
        flags = [(crit[r.criterion_id], r) for r in a.results if crit[r.criterion_id].bypass_group]
        st.subheader("Criteria checklist")
        excused = PROC["bypass_excuses"] if a.red_flag_bypass else []
        for c, r in required:
            st.markdown(criterion_card(c, r, excused=c.category in excused), unsafe_allow_html=True)
        with st.expander(
            f"Red-flag indications ({sum(r.status == 'met' for _, r in flags)} present)",
            expanded=a.red_flag_bypass,
        ):
            for c, r in flags:
                st.markdown(criterion_card(c, r), unsafe_allow_html=True)

        unverified = [r for r in a.results if r.evidence_quote and not r.quote_verified]
        if unverified:
            st.warning(
                f"🛡️ {len(unverified)} model-proposed quote(s) were not found verbatim in the note and were downgraded automatically."
            )

        gaps = [(c, r) for c, r in required if r.status != "met" and c.category not in excused]
        if gaps:
            st.subheader("Fill the gaps")
            st.caption(
                "Additions are appended to the note as a labeled clinician addendum, then facts and evidence are re-checked (policy and criteria are reused)."
            )
            with st.form("gapfill"):
                entries = []
                for c, _r in gaps:
                    entries.append(
                        st.text_area(
                            f"{c.description}",
                            key=f"gap_{c.id}_{len(result.addenda)}",
                            height=70,
                            placeholder="e.g. Completed 8 weeks of physical therapy from 08/20/2026 to 10/15/2026.",
                        )
                    )
                if st.form_submit_button("Add to note & re-check", type="primary"):
                    text = "\n".join(e.strip() for e in entries if e.strip())
                    if not text:
                        st.warning("Enter at least one addition.")
                    else:
                        new = run_with_progress(
                            "Re-checking with addendum",
                            lambda p: pipeline.recheck_with_addendum(result, text, progress=p),
                        )
                        if new:
                            ss.result, ss.letter = new, None
                            st.rerun()

        if result.addenda:
            with st.expander("Clinician addenda"):
                for block in result.addenda:
                    st.code(block, language=None)

with tab_letter:
    result = ss.get("result")
    if not result:
        st.info("Run a readiness check first.")
    else:
        a = result.assessment
        if a.status != "ready":
            st.warning(
                "This request is not ready yet — the letter will only cite criteria with verified evidence."
            )
        if st.button("Draft letter of medical necessity", type="primary"):
            out = run_with_progress("Drafting letter", lambda p: pipeline.make_letter(result))
            if out:
                ss.letter, ss.pdf, ss.letter_traces = out
        if ss.get("letter"):
            st.download_button(
                "⬇️ Download request summary PDF",
                ss.pdf,
                file_name=f"authassist_{result.case_id}.pdf",
                mime="application/pdf",
                type="primary",
            )
            st.markdown('<div class="aa-card">', unsafe_allow_html=True)
            st.markdown(ss.letter.body_markdown)
            st.markdown("</div>", unsafe_allow_html=True)
            st.caption("Citations: " + " · ".join(ss.letter.citations))

with tab_trace:
    st.subheader("Which model does what")
    models = config.models_config()
    st.table(
        [
            {
                "Role": "Vision",
                "Model": models["vision"]["model"],
                "Used for": "Reading scanned notes / fax images",
            },
            {
                "Role": "Fast",
                "Model": models["fast"]["model"],
                "Used for": "Fact extraction, search queries, missing-item asks",
            },
            {
                "Role": "Reasoning",
                "Model": models["reasoning"]["model"],
                "Used for": "Policy → criteria, evidence matching, letter drafting",
            },
            {
                "Role": "Tavily",
                "Model": "search (advanced) + extract",
                "Used for": "Finding and reading the payer's current policy",
            },
        ]
    )
    st.caption(
        "All LLM calls go to Nebius Token Factory (NVIDIA Nemotron models). The readiness score and quote verification are computed in code, not by the LLM."
    )
    result = ss.get("result")
    entries = (result.traces if result else []) + ss.get("letter_traces", [])
    if entries:
        st.subheader("Trace of the last run")
        st.dataframe(traces_table(entries), width="stretch", hide_index=True)
        total = sum((e.prompt_tokens or 0) + (e.completion_tokens or 0) for e in entries)
        st.caption(
            f"{len(entries)} calls · {total:,} tokens · {sum(e.latency_ms for e in entries) / 1000:.1f}s total"
        )
    else:
        st.info("Run a readiness check to see the live trace.")
    st.markdown(
        """
```
Note (text / PDF / fax image)
  └─ 1. Ingest ............ Nemotron vision (scans) / pypdf
  └─ 2. Extract facts ..... Nemotron fast → ClinicalFacts (spans verified in code)
  └─ 3. Find policy ....... Tavily search + extract → cache (snapshot fallback)
  └─ 4. Policy → criteria . Nemotron reasoning (cached)
  └─ 5. Match evidence .... Nemotron reasoning → quotes verified verbatim in code
        Readiness score ... computed in code
  └─ 6. Gap-fill .......... clinician addendum → re-run 2 + 5
  └─ 7. Letter + PDF ...... Nemotron reasoning + reportlab
```"""
    )

with tab_about:
    st.subheader("Limitations")
    st.markdown(
        """
- **Synthetic data only** in this demo. Uploads are disabled on the public deployment (`DEMO_MODE=true`).
- **Not HIPAA-compliant yet.** Not legal or medical advice.
- **One procedure** (MRI lumbar spine without contrast, CPT 72148), tested on 2–3 payers plus Medicare/CMS fallback.
- **Human in the loop:** every output is a draft for clinician review and signature. Nothing is ever submitted to an insurer.
- **Evidence quotes are verified** to appear verbatim in the note; unverifiable quotes are downgraded automatically.
- **Policies change.** Every criterion shows its policy source and retrieval date; verify before submission.
- Criteria extraction and matching are model-based and can be wrong — see the evaluation results for known failure cases.
"""
    )
    st.subheader("Data handling")
    st.markdown(
        "Note text and uploads are processed in memory only and never written to disk or logs; only metadata (case ID, timings) is logged."
    )
