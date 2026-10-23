# Submission notes

## Devpost description (~150 words)

Prior authorization costs US clinics hours per week, and many denials happen even though the evidence was in the chart; it just wasn't documented against the insurer's criteria. **AuthAssist** catches the gap *before* submission. Staff load a clinical note (typed, PDF, or a faxed scan) and pick the insurer. NVIDIA Nemotron models on Nebius Token Factory read the note, including scans via the Nemotron vision model, and extract structured facts. Tavily finds and extracts the insurer's current published policy, which Nemotron turns into a checklist. Each criterion is matched to a **verbatim quote** from the note, and code verifies every quote so the model can't invent evidence. A code-computed readiness score shows exactly what's missing. Staff add an addendum, re-check, and watch the score jump. Finally, AuthAssist drafts a letter of medical necessity and a request PDF for clinician signature. Every model call is traced in the UI.

## Built with

Nebius Token Factory · NVIDIA Nemotron (vision / fast / reasoning, exact IDs in `config/models.yaml`) · Tavily (search + extract) · Python · FastAPI · Streamlit · Pydantic · ReportLab · PyMuPDF · pypdf · Docker · Render

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
- Models used: _(fill after model discovery)_
- What worked:
- What didn't:

### Tavily
- What we used: `search` (advanced depth, `include_domains` allow-list per payer) and `extract` for full policy text.
- What worked:
- What didn't:
- Onboarding experience:
- Would we use again:

### Running observations
- 2026-10-23: Built the full pipeline offline against faked LLM/Tavily transports while waiting on API keys. Keeping every LLM call in a single module (`llm.py`) made this easy. Live validation is pending.
