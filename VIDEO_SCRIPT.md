# Demo video: script, shot list, recording checklist

Rules recap: **under 3:00**, **public on YouTube**, shows the project running, no copyrighted music,
no third-party logos. Target **2:40-2:50**. Narration below is ~390 words (about 2:40 at a natural pace).

## Before you record
- [ ] Use the **deployed Render URL** (judges see the real thing). If it isn't live yet, use `streamlit run ui/app.py` locally.
- [ ] Open the app a minute early to wake the free instance, and run **Case 04** once so the policy is cached and the model is warm.
- [ ] Browser: new window, 1920x1080, zoom 110-125%, hide bookmarks bar, close other tabs, light theme.
- [ ] Turn on Do Not Disturb (Focus). Close Slack/mail. Hide desktop clutter. Never show `.env` or API keys.
- [ ] Mic: quiet room, headset or AirPods close to your mouth. Do a 10-second test and listen back.
- [ ] Click path rehearsed twice. Keep the text in the addendum ready to paste (below).

Addendum to paste: `Low back pain for 9 weeks. Completed 8 weeks of physical therapy from 08/20/2026 to 10/15/2026 with minimal improvement.`

## How to record (macOS, no extra software)
1. Press **Cmd+Shift+5** -> "Record Selected Portion" (or Entire Screen) -> Options -> Microphone: your mic -> Record.
2. Record in **3-4 short takes** (one per section) so a mistake only costs one take.
3. Stop with the menu-bar button. Join and trim in **iMovie** (free) or CapCut. Cut dead air (the waits while models run).
4. Export 1080p. Upload to YouTube as **Public**. Check the YouTube length shows under 3:00.
Better audio option: record the screen silently first, then record the voice-over while watching it (QuickTime -> New Audio Recording) and lay it under the video.

## Script (what to say + what to do)

### 0:00-0:20  Problem  (screen: the AuthAssist home page / thumbnail)
> "Before many procedures, US clinics need the insurer's approval first. Staff spend hours hunting for each insurer's rules,
> and requests get denied for a fixable reason: the evidence was in the chart, but never documented against the insurer's criteria.
> This is AuthAssist. It catches those gaps before the insurer does."

### 0:20-0:55  The aha: scanned fax, live Tavily  (screen: Check readiness tab)
Do: Case 04 is preselected (scanned fax). **Tick "Fetch the payer policy live via Tavily"**. Click **Check readiness**.
> "Here's a faxed clinical note. I'll check it against Aetna's policy, fetching that policy live with Tavily.
> Nemotron's vision model reads the scan, Nemotron Nano extracts the facts, Tavily finds and extracts Aetna's own policy,
> and Nemotron Ultra turns it into a checklist and matches the evidence.
> Result: thirty-three out of a hundred. Not ready, and it says exactly what's missing: six weeks of symptoms, and a conservative therapy trial."
(Narrate the pipeline *while it runs*; cut or speed up any extra waiting in the edit.)

### 0:55-1:25  Verified evidence  (screen: Annotated note tab, then the checklist)
Do: click **Annotated note**; point at the green and red highlights; scroll to a "verified in note" badge.
> "Every quote is verified in code. Green is met, red is missing. If the model quotes something that isn't word-for-word in the note,
> code downgrades it, so the model can't invent evidence. And the score isn't computed by the model. It's plain code."

### 1:25-1:50  Gap-fill and letter  (screen: Fill the gaps form, then Letter tab)
Do: paste the addendum into the first box, click **Add to note & re-check**. Then open **Letter & PDF** -> **Draft letter** -> show **Download PDF**.
> "Now the clinician fills the gap: eight weeks of physical therapy with dates, and nine weeks of pain. Only extraction and matching re-run.
> Thirty-three becomes one hundred. Ready. Then Nemotron drafts a letter of medical necessity, with placeholders for the clinician's name and signature, plus a PDF.
> Nothing is ever submitted to an insurer."

### 1:50-2:15  Model trace + Tavily proof  (screen: Run log, then How it works / Model trace tab)
Do: open **Run log** (point at the green "live Tavily call" line), then the **Model trace** tab.
> "The trace shows which Nemotron model did what. Super VL reads scans, Nano handles fast extraction in about three seconds,
> and Ultra does the heavy reasoning, all through one Nebius Token Factory endpoint. And the run log shows the live Tavily call."

### 2:15-2:35  Evaluation + safety  (screen: GitHub README eval table or the evaluation image)
> "On eight synthetic cases, including two scanned faxes, outcomes were eight for eight, and every evidence quote was verified.
> We list the failures honestly in the repo. It's synthetic data only, drafts need clinician review, and it's not HIPAA-compliant yet."

### 2:35-2:50  Business + close  (screen: thumbnail or home page)
> "A per-request or subscription tool for small clinics. With payers required to offer prior-authorization APIs from twenty twenty-seven,
> AuthAssist is the documentation-readiness layer in front of them. AuthAssist: fix the gaps before the insurer finds them."

## Tips
- Speak slightly slower than normal; leave a half-second pause before each section so cutting is easy.
- If you run long, cut the business paragraph first, then trim the evaluation section.
- Don't show real patient data (only the synthetic cases) or any key/secret.
- Put these in the YouTube description: repo link, demo link, "Built with Nebius Token Factory, NVIDIA Nemotron, Tavily".
