## Inspiration

Before many procedures, US clinics need the insurer's approval first. Staff lose hours each week hunting for each insurer's rules and gathering evidence, and many requests are denied for an avoidable reason: the evidence *existed* in the chart but was never documented against the insurer's criteria. We wanted a tool that catches that gap **before** the insurer does.

The numbers behind that:

- **The burden is large.** In the AMA's 2025 survey of 1,000 physicians, doctors completed about **40 prior authorizations a week**, which took about **13 hours of physician and staff time**. **95%** said prior authorization delays access to necessary care. ([AMA, May 2026](https://www.ama-assn.org/press-center/ama-press-releases/ama-survey-prior-authorization-reform-pledge-falls-short-physicians))
- **Denials are common.** KFF's analysis of 2025 insurer data found insurers denied **12% of standard requests in Medicare Advantage, 14% in Medicaid managed care and 18% in the ACA Marketplace**. ([KFF, August 2026](https://www.kff.org/patient-consumer-protections/prior-authorization-metrics-provide-new-insights-into-insurer-practices-but-gaps-remain/))
- **Many denials do not hold up.** Denials are rarely appealed, but when they are, KFF found **67% (Medicare Advantage), 47% (Medicaid managed care) and 43% (Marketplace)** were overturned. We don't claim every denial is a documentation problem; AuthAssist targets the ones where the evidence existed but was never lined up against the criteria. (Same KFF source.)

## What it does

AuthAssist checks a clinical note against the insurer's *current* published policy and shows exactly what's missing.

![AuthAssist readiness review: score ring, key metrics and what's missing](https://raw.githubusercontent.com/codergirl73/authassist/main/assets/ui-results.jpg)

1. **Reads the note**: typed, PDF, or a faxed scan (a Nemotron vision model transcribes it).
2. **Extracts structured facts**: symptoms, duration, treatments, red flags, exam findings.
3. **Finds the insurer's policy** with Tavily search + extract, and turns it into a checklist.
4. **Matches each criterion to an exact quote** from the note. Code verifies every quote appears word-for-word; anything unverifiable is downgraded.
5. **Computes a readiness score in code** (never by the LLM) and lists what to add.
6. **Gap-fill loop** (guided flow: Choose note → Review → Fix gaps → Letter): staff add the missing detail as a labeled addendum, re-check, and watch the score move (e.g. 33 → 100).
7. **Drafts a letter of medical necessity and a request-summary PDF** for clinician review and signature. Nothing is ever submitted to an insurer.

![Fix the gaps and re-check: the score goes from 33 to 100](https://raw.githubusercontent.com/codergirl73/authassist/main/assets/ui-fixed.jpg)

Scope: MRI lumbar spine without contrast (CPT 72148) for low back pain, with Aetna, Molina and a Medicare fallback. More procedures are a config file away.

**Every piece of evidence is highlighted in the note and checked word-for-word.** Green is met, red is missing, and anything the model quotes that isn't really in the note is downgraded automatically.

![Annotated note: verified quotes highlighted in place on a scanned fax](https://raw.githubusercontent.com/codergirl73/authassist/main/assets/ui-annotated-note.jpg)

## How we built it

![Architecture: pipeline, Nebius Token Factory models, Tavily and local storage](https://raw.githubusercontent.com/codergirl73/authassist/main/assets/architecture.png)

- **All AI runs on Nebius Token Factory with NVIDIA Nemotron**, routed by role:
  - **Nemotron 3 Ultra** for the heavy reasoning (policy → criteria, evidence matching, the letter).
  - **Nemotron 3 Nano** for fast, frequent calls (fact extraction ~3s, short asks <1s).
  - **Nemotron 3.5 Super VL** to read faxed scans (~99% transcription accuracy on our noisy test faxes).
- **Tavily** supplies the live policy: domain-restricted search so results come from the insurer's own site, then extract for the full text. Policies and criteria are cached, with a committed criteria snapshot as a safety net.

**Live Tavily, runtime, you can trigger it:** every time the app fetches a policy live it makes real Tavily `search` (advanced) and `extract` calls at runtime, and the run log lists each one with its latency. In the live demo, sign in to the demo workspace (no account needed), open **Choose note → Advanced options** and tick **"Fetch the payer policy live via Tavily"**, then run the check. That bypasses the saved copy, pulls the insurer's current policy through Tavily, converts it to criteria with Nemotron, and scores the note against it (adds about 30-40 seconds). Without the box ticked, the demo reuses criteria that were originally fetched the same way, so the default check is fast. Try it: https://authassist.onrender.com/
- **Trust by design:** the model *proposes* evidence, code *verifies* it, and code *scores* it. A per-step model trace in the app shows which Nemotron model did what.
- Python, FastAPI, a vanilla JS web app (landing page, demo sign-in, guided workspace), Pydantic, ReportLab, Docker.

Who does what, step by step (the dashed line is the gap-fill loop):

![Swimlane: clinic staff, AuthAssist code, Nemotron on Token Factory, Tavily and the clinician](https://raw.githubusercontent.com/codergirl73/authassist/main/assets/swimlane.png)

The **How it works** page shows which Nemotron model did each step, with latency and tokens:

![How it works page: model table and a trace of every call with latency and tokens](https://raw.githubusercontent.com/codergirl73/authassist/main/assets/ui-model-trace.jpg)

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
