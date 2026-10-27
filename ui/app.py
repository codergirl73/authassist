"""AuthAssist Streamlit UI. Run: streamlit run ui/app.py"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from authassist import config, pipeline, scoring  # noqa: E402
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
ROLE_ICON = {"vision": "👁️", "fast": "⚡", "reasoning": "🧠", "tavily": "🔎", "code": "⚙️"}
DEFAULT_CASE_INDEX = 3  # case 04: scanned fax, not ready -> the "aha" demo path

st.set_page_config(page_title="AuthAssist", page_icon="🩺", layout="wide")

st.markdown(
    """
<style>
.block-container {padding-top: 1.2rem; max-width: 1180px;}
.aa-hero {padding: 1.3rem 1.5rem; border-radius: 16px; margin-bottom: .9rem;
  background: linear-gradient(120deg, rgba(118,185,0,.16), rgba(45,126,247,.14));
  border: 1px solid rgba(128,128,128,.22);}
.aa-hero h1 {margin: 0; font-size: 2rem; letter-spacing: -.02em;}
.aa-hero p {margin: .25rem 0 .7rem 0; opacity: .85; font-size: 1.02rem;}
.aa-chip {display:inline-block; font-size:.76rem; padding:.18rem .65rem; border-radius:999px; margin:0 .35rem .3rem 0;
  background: rgba(128,128,128,.16); border:1px solid rgba(128,128,128,.25);}
.aa-banner {border:1px solid rgba(245,194,122,.8); background: rgba(245,194,122,.16); padding:.5rem .85rem;
  border-radius:10px; font-size:.86rem; margin-bottom:.9rem;}
.aa-card {border:1px solid rgba(128,128,128,.25); border-radius:12px; padding:.85rem 1rem; margin-bottom:.6rem;
  background: rgba(128,128,128,.05);}
.aa-card.met {border-left: 5px solid #2ea043;} .aa-card.unclear {border-left: 5px solid #d29922;}
.aa-card.missing {border-left: 5px solid #f85149;} .aa-card.flag {border-left: 5px solid #f85149;}
.aa-card.neutral {border-left: 5px solid rgba(128,128,128,.4);}
.aa-crit-title {font-weight:600; margin-bottom:.25rem;}
.aa-quote {background:rgba(255,213,79,.38); padding:.1rem .3rem; border-radius:4px; font-style:italic;}
.aa-badge {display:inline-block; font-size:.72rem; padding:.05rem .5rem; border-radius:999px; margin-left:.35rem;
  border:1px solid currentColor; vertical-align:middle; white-space:nowrap;}
.aa-ok {color:#2ea043;} .aa-warn {color:#d29922;} .aa-bad {color:#f85149;} .aa-muted {color:#8b949e;}
.aa-small {font-size:.8rem; opacity:.75;}
.aa-kpi {border:1px solid rgba(128,128,128,.25); border-radius:12px; padding:.7rem .9rem; height:100%;
  background: rgba(128,128,128,.05);}
.aa-kpi .v {font-size:1.45rem; font-weight:700; line-height:1.2;} .aa-kpi .l {font-size:.74rem; opacity:.7;
  text-transform:uppercase; letter-spacing:.05em;} .aa-kpi .s {font-size:.78rem; opacity:.7;}
.aa-note {white-space:pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size:.82rem;
  line-height:1.55; border:1px solid rgba(128,128,128,.25); border-radius:10px; padding:.9rem 1rem;
  background: rgba(128,128,128,.05);}
.aa-note mark {padding:.05rem .15rem; border-radius:4px; color:inherit;}
.aa-note mark.met {background: rgba(46,160,67,.35);} .aa-note mark.unclear {background: rgba(210,153,34,.4);}
.aa-note mark.flag {background: rgba(248,81,73,.35);} .aa-note mark.missing {background: rgba(248,81,73,.22);}
.aa-step {display:flex; gap:.6rem; align-items:center; padding:.3rem 0; font-size:.86rem;
  border-bottom:1px dashed rgba(128,128,128,.2);}
.aa-step .m {opacity:.7; font-size:.78rem;} .aa-step .t {margin-left:auto; opacity:.7; font-variant-numeric: tabular-nums;}
</style>
<div class="aa-hero">
  <h1>🩺 AuthAssist</h1>
  <p>Catch the missing evidence in a prior-authorization request — before the insurer does.</p>
  <span class="aa-chip">🟢 NVIDIA Nemotron on Nebius Token Factory</span>
  <span class="aa-chip">🔎 Live payer policy via Tavily</span>
  <span class="aa-chip">🛡️ Every quote verified in code</span>
  <span class="aa-chip">📄 Draft letter + PDF</span>
</div>
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
            label += " 📠 scanned fax"
        out[label] = {"dir": d, **meta}
    return out


def status_style(status: str) -> tuple[str, str]:
    return {
        "ready": ("Ready to submit", "#2ea043"),
        "needs_attention": ("Needs attention", "#d29922"),
        "not_ready": ("Not ready", "#f85149"),
    }[status]


def esc(s: str | None) -> str:
    return html.escape(s or "")


def gauge(score: int, status: str) -> str:
    label, color = status_style(status)
    circ = 2 * 3.14159265 * 52
    dash = circ * score / 100
    return f"""
<div style="text-align:center">
<svg width="170" height="170" viewBox="0 0 130 130">
  <circle cx="65" cy="65" r="52" fill="none" stroke="rgba(128,128,128,.22)" stroke-width="12"/>
  <circle cx="65" cy="65" r="52" fill="none" stroke="{color}" stroke-width="12" stroke-linecap="round"
    stroke-dasharray="{dash:.1f} {circ:.1f}" transform="rotate(-90 65 65)"/>
  <text x="65" y="68" text-anchor="middle" font-size="34" font-weight="700" fill="{color}">{score}</text>
  <text x="65" y="88" text-anchor="middle" font-size="11" fill="currentColor" opacity=".6">out of 100</text>
</svg>
<div style="font-weight:700; color:{color}; font-size:1.1rem; margin-top:-.2rem">{label}</div></div>"""


def kpi(label: str, value: str, sub: str = "") -> str:
    return f'<div class="aa-kpi"><div class="l">{esc(label)}</div><div class="v">{value}</div><div class="s">{sub}</div></div>'


def link_from_citation(citation: str) -> str:
    parts = citation.rsplit(" - ", 1)
    if len(parts) == 2 and parts[1].startswith("http"):
        return f'{esc(parts[0])} — <a href="{esc(parts[1])}" target="_blank">source</a>'
    return esc(citation)


def criterion_card(c, r, excused: bool = False) -> str:
    if c.bypass_group:
        icon, cls, label, edge = (
            ("🚩", "aa-bad", "Present", "flag")
            if r.status == "met"
            else ("◻️", "aa-muted", "Not present", "neutral")
        )
    else:
        icon, cls, label = {
            "met": ("✅", "aa-ok", "Met"),
            "unclear": ("⚠️", "aa-warn", "Unclear"),
            "missing": ("❌", "aa-bad", "Missing"),
        }[r.status]
        edge = r.status
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
    return f"""<div class="aa-card {edge}"{style}>
<div class="aa-crit-title">{icon} {esc(c.description)} <span class="aa-badge {cls}">{label}</span></div>
{quote}<div class="aa-small">{esc(r.reasoning)}</div>
<div class="aa-small" style="margin-top:.25rem">📄 {link_from_citation(c.policy_citation)}</div>{note}</div>"""


def annotate_note(note: str, results, crit: dict) -> tuple[str, int]:
    """Return the note as HTML with each verified evidence quote highlighted in place."""
    spans: list[tuple[int, int, str, str]] = []
    for r in results:
        if not (r.evidence_quote and r.quote_verified):
            continue
        tokens = r.evidence_quote.strip(" .,;:\"'“”").split()
        if not tokens:
            continue
        match = re.search(r"\s+".join(re.escape(t) for t in tokens), note, flags=re.IGNORECASE)
        if not match:
            continue
        c = crit[r.criterion_id]
        kind = ("flag" if r.status == "met" else None) if c.bypass_group else r.status
        if kind:
            spans.append((match.start(), match.end(), kind, c.description))
    spans.sort()
    out, pos, used = [], 0, 0
    for start, end, kind, desc in spans:
        if start < pos:  # overlapping quote: keep the first
            continue
        out.append(esc(note[pos:start]))
        out.append(f'<mark class="{kind}" title="{esc(desc)}">{esc(note[start:end])}</mark>')
        pos, used = end, used + 1
    out.append(esc(note[pos:]))
    return "".join(out), used


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


def run_log(entries) -> str:
    rows = []
    for e in entries:
        status = "" if e.success else " ❌"
        rows.append(
            f'<div class="aa-step"><span>{ROLE_ICON.get(e.role, "•")}</span><span>{esc(e.step)}{status}</span>'
            f'<span class="m">{esc(e.model)}</span><span class="t">{e.latency_ms / 1000:.1f}s</span></div>'
        )
    return "".join(rows)


# ---------------------------------------------------------------- app

tab_check, tab_letter, tab_trace, tab_about = st.tabs(
    ["① Check readiness", "② Letter & PDF", "How it works · Model trace", "About & limitations"]
)
ss = st.session_state

with tab_check:
    cases = case_options()
    payer_keys = list(PROC["payers"])
    left, right = st.columns([3, 2])
    with left:
        choice = st.selectbox("Load example case (synthetic)", list(cases), index=DEFAULT_CASE_INDEX)
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

    live = st.checkbox(
        "🔎 Fetch the payer policy live via Tavily (ignore cache)",
        value=False,
        help="Runs a fresh Tavily search + extract, then converts the policy to criteria with Nemotron "
        "(adds ~20-40s). Leave off to reuse the cached policy for a fast check.",
    )
    if live and payer == "medicare":
        st.caption(
            "ℹ️ CMS pages are quality-measure specs, so live Medicare extraction is noisy; Aetna or Molina work best."
        )

    if not (pasted or upload):
        with st.expander("View the clinical note before checking"):
            if (case["dir"] / "note.txt").exists():
                st.code((case["dir"] / "note.txt").read_text(), language=None)
            else:
                st.image(str(case["dir"] / "note.png"), caption="Scanned fax — read by the vision model")

    b1, b2 = st.columns([4, 1])
    with b1:
        go = st.button("Check readiness", type="primary", width="stretch")
    with b2:
        if st.button("Start over", width="stretch"):
            for k in ("result", "letter", "pdf", "letter_traces"):
                ss.pop(k, None)
            st.rerun()

    if go:
        if pasted and pasted.strip():
            case_input = CaseInput(case_id="user_note", payer=payer, note_text=pasted)
        elif upload is not None:
            case_input = CaseInput(
                case_id="user_upload", payer=payer, file_bytes=upload.getvalue(), filename=upload.name
            )
        else:
            case_input = load_case(case["dir"], payer)
        result = run_with_progress(
            "Checking readiness",
            lambda p: pipeline.run_pipeline(case_input, force_refresh=live, progress=p),
        )
        if result:
            ss.result, ss.letter = result, None
            ss.letter_traces = []

    result = ss.get("result")
    if result:
        a = result.assessment
        crit = {c.id: c for c in a.criteria}
        excused = PROC["bypass_excuses"] if a.red_flag_bypass else []
        required = [(crit[r.criterion_id], r) for r in a.results if not crit[r.criterion_id].bypass_group]
        flags = [(crit[r.criterion_id], r) for r in a.results if crit[r.criterion_id].bypass_group]
        req_ids = {
            c.id for c in scoring.required_criteria(a.criteria, a.red_flag_bypass, PROC["bypass_excuses"])
        }
        counted = [r for c, r in required if c.id in req_ids]
        met_n = sum(r.status == "met" for r in counted)
        quotes = [r for r in a.results if r.evidence_quote]
        verified_n = sum(r.quote_verified for r in quotes)
        total_s = sum(e.latency_ms for e in result.traces) / 1000
        total_tok = sum((e.prompt_tokens or 0) + (e.completion_tokens or 0) for e in result.traces)
        p = a.policy
        src = {
            "tavily": "Found live via Tavily",
            "cache": "Cached Tavily result",
            "snapshot": "Cached snapshot",
        }[p.source]

        st.divider()
        g_col, k_col = st.columns([1, 2.4])
        with g_col:
            st.markdown(gauge(a.readiness_score, a.status), unsafe_allow_html=True)
            if result.previous_score is not None:
                st.metric(
                    "After addendum",
                    f"{a.readiness_score}",
                    f"{a.readiness_score - result.previous_score:+d} (was {result.previous_score})",
                )
        with k_col:
            k1, k2, k3, k4 = st.columns(4)
            k1.markdown(
                kpi("Criteria met", f"{met_n}/{len(counted)}", "required criteria"),
                unsafe_allow_html=True,
            )
            k2.markdown(
                kpi("Quotes verified", f"{verified_n}/{len(quotes)}", "verbatim in note"),
                unsafe_allow_html=True,
            )
            k3.markdown(
                kpi("Run", f"{total_s:.0f}s", f"{total_tok:,} tokens · {len(result.traces)} calls"),
                unsafe_allow_html=True,
            )
            k4.markdown(
                kpi("Policy", "🔎 Live" if p.source == "tavily" else "🗂️ Cached", esc(src)),
                unsafe_allow_html=True,
            )
            st.markdown("")
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
            st.markdown(
                f"""<div class="aa-card neutral"><div class="aa-small">POLICY SOURCE · {esc(src)}</div>
<div class="aa-crit-title">{esc(p.payer)} — <a href="{esc(p.url)}" target="_blank">{esc(p.title)}</a></div>
<div class="aa-small">Retrieved {p.retrieved_at:%Y-%m-%d}{" · Medicare/CMS guidance used as fallback" if p.is_fallback else ""}</div></div>""",
                unsafe_allow_html=True,
            )
            if result.policy_notice:
                st.caption(f"ℹ️ {result.policy_notice}")

        t_check, t_note, t_facts, t_log = st.tabs(
            ["Criteria checklist", "Annotated note", "Extracted facts", "Run log"]
        )

        with t_check:
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

        with t_note:
            body, n_hl = annotate_note(result.note_text, a.results, crit)
            st.caption(
                f"{n_hl} verified quote(s) highlighted in place — "
                "🟩 met  🟨 unclear  🟥 missing / red flag. Hover a highlight to see the criterion."
            )
            st.markdown(f'<div class="aa-note">{body}</div>', unsafe_allow_html=True)
            if result.ingest_method == "vision":
                st.caption("Text above was transcribed from the scanned image by the Nemotron vision model.")

        with t_facts:
            f = result.facts
            fa, fb = st.columns(2)
            with fa:
                st.markdown(f"**Chief complaint:** {f.chief_complaint or '—'}")
                st.markdown(f"**Age / sex:** {f.patient_age or '—'} / {f.sex or '—'}")
                st.markdown(
                    f"**Symptom duration:** {f'{f.symptom_duration_weeks:g} weeks' if f.symptom_duration_weeks else '—'}"
                )
                st.markdown("**Diagnoses:** " + (", ".join(f.diagnoses) or "—"))
                st.markdown("**Prior imaging:** " + ("; ".join(f.prior_imaging) or "—"))
            with fb:
                st.markdown("**Conservative treatments:**")
                for t in f.conservative_treatments or []:
                    bits = [t.treatment, f"{t.duration_weeks:g} wk" if t.duration_weeks else None, t.dates]
                    st.markdown("- " + " · ".join(x for x in bits if x))
                if not f.conservative_treatments:
                    st.markdown("- none documented")
                st.markdown("**Red flags:** " + ("; ".join(f.red_flags) or "none documented"))
                st.markdown("**Neuro exam:** " + ("; ".join(f.neuro_exam_findings) or "not documented"))

        with t_log:
            st.caption("Every model and tool call in this run, in order.")
            st.markdown(run_log(result.traces), unsafe_allow_html=True)
            tav = [e for e in result.traces if e.role == "tavily"]
            if tav:
                st.success(f"🔎 {len(tav)} live Tavily call(s) made in this run (search + extract).")
            else:
                st.info(
                    "No Tavily call in this run: the policy came from cache. Tick “Fetch the payer policy live” to run one."
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
        elif a.status == "ready":
            st.info("Next: open the **② Letter & PDF** tab to draft the letter of medical necessity.")

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
        label, color = status_style(a.status)
        st.markdown(
            f'<span class="aa-chip" style="border-color:{color};color:{color}">{label} · {a.readiness_score}/100</span>'
            f'<span class="aa-chip">{esc(a.payer)}</span><span class="aa-chip">CPT 72148</span>',
            unsafe_allow_html=True,
        )
        if a.status != "ready":
            st.warning(
                "This request is not ready yet — the letter will only cite criteria with verified evidence."
            )
        if st.button("Draft letter of medical necessity", type="primary"):
            out = run_with_progress("Drafting letter", lambda p: pipeline.make_letter(result))
            if out:
                ss.letter, ss.pdf, ss.letter_traces = out
        if ss.get("letter"):
            d1, d2, _ = st.columns([1.4, 1.4, 3])
            d1.download_button(
                "⬇️ Download PDF",
                ss.pdf,
                file_name=f"authassist_{result.case_id}.pdf",
                mime="application/pdf",
                type="primary",
                width="stretch",
            )
            d2.download_button(
                "⬇️ Letter (.md)",
                ss.letter.body_markdown,
                file_name=f"authassist_{result.case_id}_letter.md",
                mime="text/markdown",
                width="stretch",
            )
            with st.container(border=True):
                st.markdown(ss.letter.body_markdown)
            st.caption("Citations: " + " · ".join(ss.letter.citations))
            st.caption(
                "Draft only — requires clinician review and signature. Nothing is sent to any insurer."
            )

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
