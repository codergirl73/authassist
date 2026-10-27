## Inspiration

Before many procedures, US clinics need the insurer's approval first. Staff lose hours each week hunting for each insurer's rules and gathering evidence, and many requests are denied for an avoidable reason: the evidence *existed* in the chart but was never documented against the insurer's criteria. We wanted a tool that catches that gap **before** the insurer does.

<!-- ADD: 2-3 sourced statistics on prior-authorization burden / avoidable denials, with links -->

## What it does

AuthAssist checks a clinical note against the insurer's *current* published policy and shows exactly what's missing.

1. **Reads the note**: typed, PDF, or a faxed scan (a Nemotron vision model transcribes it).
2. **Extracts structured facts**: symptoms, duration, treatments, red flags, exam findings.
3. **Finds the insurer's policy** with Tavily search + extract, and turns it into a checklist.
4. **Matches each criterion to an exact quote** from the note. Code verifies every quote appears word-for-word; anything unverifiable is downgraded.
5. **Computes a readiness score in code** (never by the LLM) and lists what to add.
6. **Gap-fill loop**: staff add the missing detail as a labeled addendum, re-check, and watch the score move (e.g. 33 → 100).
7. **Drafts a letter of medical necessity and a request-summary PDF** for clinician review and signature. Nothing is ever submitted to an insurer.

Scope: MRI lumbar spine without contrast (CPT 72148) for low back pain, with Aetna, Molina and a Medicare fallback. More procedures are a config file away.

## How we built it

- **All AI runs on Nebius Token Factory with NVIDIA Nemotron**, routed by role:
  - **Nemotron 3 Ultra** for the heavy reasoning (policy → criteria, evidence matching, the letter).
  - **Nemotron 3 Nano** for fast, frequent calls (fact extraction ~3s, short asks <1s).
  - **Nemotron 3.5 Super VL** to read faxed scans (~99% transcription accuracy on our noisy test faxes).
- **Tavily** supplies the live policy: domain-restricted search so results come from the insurer's own site, then extract for the full text. Policies and criteria are cached, with a committed criteria snapshot as a safety net.
- **Trust by design:** the model *proposes* evidence, code *verifies* it, and code *scores* it. A per-step model trace in the UI shows which Nemotron model did what.
- Python, FastAPI, Streamlit, Pydantic, ReportLab, Docker.

## Challenges we ran into

- **Nemotron's hidden reasoning ate the token budget.** With thinking on, Nano spent all 3,000 tokens reasoning and returned empty content. Turning thinking off for extraction and vision roles fixed it and cut extraction to ~3s.
- **Policies list alternative pathways.** Our first extraction made things like "required hospitalization" mandatory, so ordinary cases scored low. We taught the extractor to treat sub-population pathways as red flags instead.
- **Vague evidence.** "Did some physical therapy" was marked as met when the policy needs 6 weeks. A quantity-aware matching rule fixed it.
- **Model API IDs differ from catalog names**, and the spec's preferred vision model was dedicated-endpoint only, so we adapted to Nemotron 3.5 Super VL.

## Accomplishments we're proud of

On 8 synthetic cases (2 of them scanned faxes): **8/8 correct outcomes, 100% of evidence quotes verified verbatim, ~99% fax transcription accuracy**, including two red-flag bypass cases. We also publish the failures: results vary slightly run to run, and one case triggers a bypass because Molina's own policy lists abnormal reflexes as an indication.

## What we learned

Letting a model propose and code verify is a simple pattern that makes LLM output trustworthy enough for a regulated workflow. Matching Nemotron model size to the job keeps the app responsive and credits stretched.

## What's next

HIPAA controls and BAAs, EHR/FHIR integration, payer prior-authorization APIs (required of many payers from Jan 1, 2027 under CMS-0057-F), more procedures, and a policy watcher that flags when a payer's policy changes.

**Track:** Best Apps and Agents. **Built during the Submission Period** as a new project. Synthetic data only; drafts require clinician review.
