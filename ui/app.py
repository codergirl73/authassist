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
EXAMPLE_ADDENDA = {  # synthetic text used by the demo-only "Fill with example answers" button
    "symptom_duration": "Low back pain for 9 weeks.",
    "conservative_therapy": "Completed 8 weeks of physical therapy from 08/20/2026 to 10/15/2026 with minimal improvement.",
    "neuro_exam": "Neuro exam: strength 5/5, reflexes 2+ symmetric, sensation intact, negative straight leg raise.",
    "prior_imaging": "No prior lumbar imaging.",
}
DEFAULT_CASE_INDEX = 3  # case 04: scanned fax, not ready -> the "aha" demo path

st.set_page_config(page_title="AuthAssist", page_icon="🩺", layout="wide")


def _mini_ring(score: int, color: str, label: str) -> str:
    circ = 2 * 3.14159265 * 40
    dash = circ * score / 100
    return (
        '<div><svg width="104" height="104" viewBox="0 0 100 100">'
        '<circle cx="50" cy="50" r="40" fill="none" stroke="rgba(128,128,128,.28)" stroke-width="10"/>'
        f'<circle cx="50" cy="50" r="40" fill="none" stroke="{color}" stroke-width="10" stroke-linecap="round" '
        f'stroke-dasharray="{dash:.1f} {circ:.1f}" transform="rotate(-90 50 50)"/>'
        f'<text x="50" y="58" text-anchor="middle" font-size="26" font-weight="700" fill="{color}">{score}</text></svg>'
        f'<div class="lab" style="color:{color}">{label}</div></div>'
    )


def landing_html() -> str:
    tiles = [
        ("👁️", "Reads faxed notes", "Nemotron vision turns a scan into text."),
        ("🔎", "Finds the live policy", "Tavily fetches the insurer's own criteria."),
        ("🛡️", "Proves every quote", "Evidence is verified word-for-word in code."),
        ("📄", "Drafts the letter", "Letter + PDF for the clinician to sign."),
    ]
    tiles_html = "".join(
        f'<div class="aa-tile"><div class="ic">{i}</div><b>{ti}</b><span>{d}</span></div>'
        for i, ti, d in tiles
    )
    stats = [
        ("8/8", "outcomes correct"),
        ("57/57", "quotes verified"),
        ("~99%", "fax read accuracy"),
        ("0", "claims sent to insurers"),
    ]
    stats_html = "".join(f'<div class="aa-stat"><b>{n}</b><span>{lb}</span></div>' for n, lb in stats)
    return (
        '<div class="aa-hero2"><div>'
        '<span class="aa-brand">🩺 AuthAssist</span>'
        '<div class="aa-h1">Catch the missing evidence <em>before</em> the insurer does.</div>'
        "<p class=\"aa-sub\">Check a clinical note against the insurer's current policy, see exactly what's missing, "
        "and draft the letter. Powered by NVIDIA Nemotron on Nebius Token Factory and Tavily.</p>"
        '<a class="aa-cta" href="#try-it">Try the demo ↓</a>'
        '<a class="aa-cta2" href="https://github.com/codergirl73/authassist" target="_blank">View source</a>'
        '</div><div class="aa-mock"><div class="aa-mock-title">Readiness score</div><div class="aa-mock-rings">'
        + _mini_ring(33, "#f85149", "Not ready")
        + '<div class="aa-mock-arrow">→</div>'
        + _mini_ring(100, "#2ea043", "Ready")
        + '</div><div class="aa-mock-rows">'
        '<div class="r bad"><div>✗ 6+ weeks of symptoms</div><span>missing</span></div>'
        '<div class="r bad"><div>✗ Conservative therapy trial</div><span>missing</span></div>'
        '<div class="r ok"><div>✓ Neuro exam documented</div><span>verified in note</span></div>'
        "</div></div></div>"
        f'<div class="aa-stats">{stats_html}</div><div class="aa-tiles">{tiles_html}</div>'
    )


LANDING = """
<style>
.block-container {padding-top: 3.4rem; max-width: 1180px;}
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
.aa-step {flex-wrap: wrap;}
@media (max-width: 640px) {
  .block-container {padding: .8rem .7rem 3rem .7rem;}
  .aa-hero {padding: .9rem 1rem;} .aa-hero h1 {font-size: 1.5rem;} .aa-hero p {font-size: .92rem;}
  .aa-kpi .v {font-size: 1.2rem;} .aa-note {font-size: .74rem; padding: .7rem;}
  .aa-step .m {flex-basis: 100%; order: 3;}
}
.aa-steps {display:flex; gap:.5rem; flex-wrap:wrap; margin:.2rem 0 1rem 0;}
.aa-step-pill {display:flex; align-items:center; gap:.5rem; padding:.35rem .85rem .35rem .4rem; border-radius:999px; font-size:.85rem;
  border:1px solid rgba(128,128,128,.28); opacity:.62;}
.aa-step-pill .n {width:1.5rem; height:1.5rem; border-radius:50%; display:flex; align-items:center; justify-content:center;
  font-weight:700; font-size:.78rem; background: rgba(128,128,128,.22);}
.aa-step-pill.done {opacity:1; border-color: rgba(46,160,67,.55);} .aa-step-pill.done .n {background:#2ea043; color:#fff;}
.aa-step-pill.active {opacity:1; border-color:#2ea043; box-shadow: 0 0 0 3px rgba(46,160,67,.16); font-weight:600;}
.aa-step-pill.active .n {background:#fff; border:2px solid #2ea043; color:#2ea043;}
.aa-foot {text-align:center; font-size:.8rem; opacity:.65; margin:2.2rem 0 .5rem 0;}
.aa-hero2 {display:grid; grid-template-columns: 1.2fr .9fr; gap:2rem; align-items:center; padding:2.1rem 2.3rem; border-radius:22px;
  margin-bottom:1rem; background: linear-gradient(125deg, rgba(118,185,0,.20), rgba(45,126,247,.16) 60%, rgba(118,80,255,.12));
  border:1px solid rgba(128,128,128,.24);}
.aa-brand {display:inline-flex; align-items:center; gap:.5rem; font-weight:700; font-size:1.05rem; padding:.3rem .8rem; border-radius:999px;
  background: rgba(128,128,128,.14); border:1px solid rgba(128,128,128,.28);}
.aa-h1 {font-size: clamp(2rem, 4.4vw, 3.15rem); line-height:1.07; font-weight:800; letter-spacing:-.03em; margin:.9rem 0 .8rem 0;}
.aa-h1 em {font-style:normal; color:#2ea043;}
.aa-sub {font-size:1.08rem; opacity:.86; max-width:34rem; margin:0 0 1rem 0;}
.aa-cta {display:inline-block; padding:.7rem 1.3rem; background:#2ea043; color:#fff !important; border-radius:12px; font-weight:700;
  text-decoration:none !important; box-shadow:0 6px 18px rgba(46,160,67,.35);}
.aa-cta2 {display:inline-block; margin-left:.7rem; font-size:.92rem; opacity:.85; text-decoration:underline;}
.aa-mock {border:1px solid rgba(128,128,128,.3); border-radius:18px; padding:1rem 1.1rem; background: rgba(128,128,128,.10);
  box-shadow:0 10px 30px rgba(0,0,0,.12);}
.aa-mock-title {font-size:.72rem; letter-spacing:.09em; text-transform:uppercase; opacity:.65; margin-bottom:.4rem;}
.aa-mock-rings {display:flex; align-items:center; justify-content:space-around; gap:.4rem;}
.aa-mock-rings .lab {text-align:center; font-weight:700; font-size:.92rem; margin-top:-.2rem;}
.aa-mock-arrow {font-size:1.6rem; opacity:.55;}
.aa-mock-rows {margin-top:.7rem; display:flex; flex-direction:column; gap:.35rem;}
.aa-mock-rows .r {display:flex; justify-content:space-between; gap:.6rem; font-size:.84rem; padding:.4rem .6rem; border-radius:9px;
  border-left:4px solid; background: rgba(128,128,128,.08);}
.aa-mock-rows .r span {opacity:.7; font-size:.76rem; white-space:nowrap;}
.aa-mock-rows .bad {border-color:#f85149;} .aa-mock-rows .ok {border-color:#2ea043;}
.aa-tiles {display:grid; grid-template-columns: repeat(4, 1fr); gap:.8rem; margin:.2rem 0 1rem 0;}
.aa-tile {border:1px solid rgba(128,128,128,.25); border-radius:14px; padding:.85rem .95rem; background: rgba(128,128,128,.05);}
.aa-tile .ic {font-size:1.5rem;} .aa-tile b {display:block; margin:.25rem 0 .15rem 0;} .aa-tile span {font-size:.84rem; opacity:.75;}
.aa-stats {display:flex; gap:2rem; flex-wrap:wrap; margin:0 0 1rem .2rem;}
.aa-stat b {font-size:1.55rem; color:#2ea043; display:block; line-height:1.1;} .aa-stat span {font-size:.78rem; opacity:.7;}
@media (max-width: 860px) {
  .aa-hero2 {grid-template-columns: 1fr; padding:1.3rem 1.2rem; gap:1.2rem;}
  .aa-tiles {grid-template-columns: repeat(2, 1fr);} .aa-stats {gap:1.2rem;}
}
</style>
{HERO}
<div class="aa-banner">⚠️ <b>Demo uses synthetic data only.</b> Do not upload real patient information.
Drafts require clinician review. AuthAssist never submits anything to an insurer.</div>
<div id="try-it"></div>"""
st.markdown(LANDING.replace("{HERO}", landing_html()), unsafe_allow_html=True)


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


def stepper_html() -> str:
    res = st.session_state.get("result")
    if not res:
        active = 2
    else:
        active = 4 if res.assessment.status == "ready" else 3
    labels = ["Choose a case", "Check readiness", "Fill the gaps", "Letter & PDF"]
    pills = []
    for i, label in enumerate(labels, start=1):
        cls = "done" if i < active else ("active" if i == active else "")
        mark = "&#10003;" if i < active else str(i)
        pills.append(f'<div class="aa-step-pill {cls}"><span class="n">{mark}</span>{label}</div>')
    return '<div class="aa-steps">' + "".join(pills) + "</div>"


stepper_slot = st.empty()  # filled at the end of the script so it reflects this run's result

tab_check, tab_letter, tab_trace, tab_about = st.tabs(
    ["① Check readiness", "② Letter & PDF", "How it works · Model trace", "About & limitations"]
)
ss = st.session_state

with tab_check:
    cases = case_options()
    payer_keys = list(PROC["payers"])

    with st.expander("👋 First time here? Take the 30-second tour", expanded=not ss.get("result")):
        st.markdown(
            """
1. **Case 04** (a scanned fax) is preselected. Click **Check readiness**.
2. Read the score, then open **Annotated note** to see each piece of evidence highlighted in the note.
3. Under **Fill the gaps**, click **Fill with example answers**, then **Add to note & re-check** and watch the score rise.
4. Open **② Letter & PDF** to draft the letter of medical necessity.

_All cases are synthetic. Nothing is ever sent to an insurer._
"""
        )

    ctrl, preview = st.columns([3, 2], gap="large")
    with ctrl:
        choice = st.selectbox("Load example case (synthetic)", list(cases), index=DEFAULT_CASE_INDEX)
        case = cases[choice]
        upload, pasted = None, None
        if not config.DEMO_MODE:
            with st.expander("…or use your own note (processed in memory only)"):
                upload = st.file_uploader(
                    "Clinical note (PDF, PNG, JPG, TXT)", type=["pdf", "png", "jpg", "jpeg", "txt"]
                )
                pasted = st.text_area("Or paste note text", height=140)
        pc1, pc2 = st.columns(2)
        with pc1:
            payer = st.selectbox(
                "Payer",
                payer_keys,
                index=payer_keys.index(case["payer"]),
                format_func=lambda k: PROC["payers"][k]["name"],
                key=f"payer_{case['case_id']}",
            )
        with pc2:
            st.text_input("Procedure", PROC["display_name"], disabled=True)

        live = st.checkbox(
            "🔎 Fetch the payer policy live via Tavily (ignore cache)",
            value=False,
            help="Runs a fresh Tavily search + extract, then converts the policy to criteria with Nemotron "
            "(adds ~20-40s). Leave off to reuse the cached policy for a fast check.",
        )
        if config.APP_ENV == "demo" and not live:
            st.caption(
                "⚡ Fast mode: uses the saved policy criteria (originally fetched with Tavily). Tick the box above to fetch the policy live (adds ~30-40s)."
            )
        if live and payer == "medicare":
            st.caption(
                "ℹ️ CMS pages are quality-measure specs, so live Medicare extraction is noisy; Aetna or Molina work best."
            )

        b1, b2 = st.columns([3, 1])
        with b1:
            go = st.button("Check readiness", type="primary", width="stretch")
        with b2:
            if st.button("Start over", width="stretch"):
                for k in ("result", "letter", "pdf", "letter_traces"):
                    ss.pop(k, None)
                st.rerun()

    with preview:
        st.markdown("**Clinical note** · synthetic")
        with st.container(height=420, border=True):
            if pasted or upload:
                st.caption("Your own note will be used when you click Check readiness.")
            elif (case["dir"] / "note.txt").exists():
                st.code((case["dir"] / "note.txt").read_text(), language=None)
            else:
                st.image(str(case["dir"] / "note.png"))
                st.caption("Scanned fax: read by the Nemotron vision model.")

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
            if config.DEMO_MODE:
                if st.button(
                    "✨ Fill with example answers",
                    help="Adds plausible synthetic text so you can see the re-check work.",
                ):
                    for c, _r in gaps:
                        example = EXAMPLE_ADDENDA.get(c.category)
                        if example:
                            ss[f"gap_{c.id}_{len(result.addenda)}"] = example
                    st.rerun()
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

stepper_slot.markdown(stepper_html(), unsafe_allow_html=True)

st.markdown(
    '<div class="aa-foot">Built for the Nebius x NVIDIA Global AI Hackathon · NVIDIA Nemotron on Nebius Token Factory · Tavily · '
    '<a href="https://github.com/codergirl73/authassist" target="_blank">Source (MIT)</a></div>',
    unsafe_allow_html=True,
)
