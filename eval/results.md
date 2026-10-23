# AuthAssist evaluation results

**Not run yet.** The evaluation calls Nebius Token Factory and Tavily, and API keys
have not been configured at the time of writing. Run:

```bash
python eval/run_eval.py
```

This file will then contain: overall outcome accuracy, per-criterion accuracy,
red-flag bypass accuracy, evidence-quote verification rate, vision transcription
similarity for the scanned cases, average latency per step, total tokens, and an
honest list of failure cases.
