# Submission notes

## Devpost description (~150 words)

Prior authorization costs US clinics hours per week, and many denials happen even though the evidence was in the chart; it just wasn't documented against the insurer's criteria. **AuthAssist** catches the gap *before* submission. Staff load a clinical note (typed, PDF, or a faxed scan) and pick the insurer. NVIDIA Nemotron models on Nebius Token Factory read the note, including scans via the Nemotron vision model, and extract structured facts. Tavily finds and extracts the insurer's current published policy, which Nemotron turns into a checklist. Each criterion is matched to a **verbatim quote** from the note, and code verifies every quote so the model can't invent evidence. A code-computed readiness score shows exactly what's missing. Staff add an addendum, re-check, and watch the score jump. Finally, AuthAssist drafts a letter of medical necessity and a request PDF for clinician signature. Every model call is traced in the UI.

## Built with

Nebius Token Factory · NVIDIA Nemotron 3.5 Super VL · Nemotron 3 Nano 30B-A3B · Nemotron 3 Ultra 550B-A55B · Tavily (search + extract) · Python · FastAPI · Streamlit · Pydantic · ReportLab · PyMuPDF · pypdf · Docker · Render

## 3-minute demo video script

- **0:00–0:20 Problem.** "Clinics lose hours to prior auth, and many denials are avoidable: the evidence was there but not documented against the payer's criteria."
- **0:20–0:50 Aha.** Load *Case 04 (scanned fax)* → Check readiness. Progress shows "Reading scanned note: Nemotron vision ✓". Result: **Not ready**; missing conservative therapy and symptom duration. Type the addendum "Low back pain for 9 weeks. Completed 8 weeks of physical therapy from 08/20/2026 to 10/15/2026." → **Add to note & re-check** → score jumps to Ready. Open the Letter tab → draft letter → download PDF.
- **0:50–1:50 Under the hood.** Model-trace tab: which Nemotron model did each step, latency, tokens. Policy source card: Aetna CPB found via Tavily, retrieval date, citations on each criterion. Show the "verified in note" badges and explain the verbatim-quote check. Show Case 07: red-flag bypass (cauda equina).
- **1:50–2:30 Evaluation and safety.** `eval/results.md` table: outcome accuracy, quote verification rate, failure cases. Synthetic data only, drafts only, never submits, not HIPAA yet.
- **2:30–3:00 Business and why now.** Per-request or subscription for small clinics. CMS-0057-F requires payer prior-auth APIs from Jan 2027; AuthAssist is the documentation-readiness layer in front of them.

## Feedback log

### Nebius Token Factory
- What we used: OpenAI-compatible chat completions for three model roles (vision, fast, reasoning); `GET /v1/models` for model ID discovery.
- What worked:
- What didn't:
- Onboarding experience:
- Would we use again:

### NVIDIA Nemotron models
- Models used: Nemotron-3.5-Super-VL (vision), NVIDIA-Nemotron-3-Nano-30B-A3B (fast), Nemotron-3-Ultra-550b-a55b (reasoning), nemotron-3-super-120b-a12b (fallback).
- What worked:
- What didn't:

### Tavily
- What we used: `search` (advanced depth, `include_domains` allow-list per payer) and `extract` for full policy text.
- What worked:
- What didn't:
- Onboarding experience:
- Would we use again:

### Running observations
- Model discovery: `GET /v1/models` returned exactly 5 Nemotron models. API IDs differ from catalog display names (e.g. `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`); the catalog page URL shows the real ID. Nano Omni and Nano V2 12B are dedicated-endpoint only, so vision uses Nemotron 3.5 Super VL.
- Nemotron 3 Nano with reasoning on burned all 3000 max_tokens thinking and returned empty `content` (finish_reason=length). `extra_body={"chat_template_kwargs":{"enable_thinking":False}}` fixed it (664 tokens, clean JSON); `reasoning_effort=low` did not. Big win for latency: extraction went to ~3s.
- Vision: OpenAI-style base64 `image_url` works unchanged on Nemotron-3.5-Super-VL; ~99% transcription similarity on noisy, rotated fax-style images.
- Ultra (reasoning) is ~11s per evidence-matching call; JSON output reliable, 1 repair retry needed once during policy -> criteria.
- Tavily: `include_domains` allow-listing returned the payer's own policy first try for Aetna and Molina. For CMS it returned quality-measure specs and a public-comment report, not coverage guidance; extraction from those was noisy (e.g. 20 exclusion-list criteria). `extract` is fast (<1s) and cheap; caching makes repeat runs free.
- Policy extraction needed prompt guidance to treat alternative pathways (trauma, hospitalization) as red flags, not required criteria; otherwise every ordinary case scored low.
- Model output varies slightly run to run at temperature 0.1 (one case flipped between runs), so we report it in the eval.
- 2026-10-23: Built the full pipeline offline against faked LLM/Tavily transports while waiting on API keys. Keeping every LLM call in a single module (`llm.py`) made this easy. Live validation is pending.
