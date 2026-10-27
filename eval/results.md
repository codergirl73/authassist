# AuthAssist evaluation results

Run date: 2026-10-27 - 8 synthetic cases - procedure: MRI lumbar spine (CPT 72148)
Models: vision=`nvidia/Nemotron-3.5-Super-VL`, fast=`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, reasoning=`nvidia/Nemotron-3-Ultra-550b-a55b`

## Summary

| Metric | Result |
|---|---|
| Overall outcome accuracy (ready / needs attention / not ready) | 8/8 (100%) |
| Per-criterion accuracy (key criteria in expected.json) | 23/24 (96%) |
| Expectations not applicable (payer policy has no such criterion) | 5 |
| Red-flag bypass accuracy | 7/8 (88%) |
| Evidence quotes verified verbatim in note | 57/57 (100%) |
| Cases that errored | 0 |
| Total tokens | 51,921 |

## Per case

| Case | Scenario | Input | Expected | Actual | Score | Bypass | Criteria correct | Time |
|---|---|---|---|---|---|---|---|---|
| case_01 | 8 weeks PT + NSAIDs documented, neuro exam documented | text | ready | ready (OK) | 100 | no | 4/4 | 11.8s |
| case_02 | 7 weeks conservative care, radiculopathy findings | text | ready | ready (OK) | 100 | yes | 1/2 | 19.7s |
| case_03 | Persistent pain after PT, prior X-ray, good documentation | text | ready | ready (OK) | 100 | no | 5/5 | 19.8s |
| case_04 | Pain 3 weeks, no conservative therapy, no red flags | scanned_png | not_ready | not_ready (OK) | 33 | no | 4/4 | 11.9s |
| case_05 | PT mentioned but no duration/dates | text | needs_attention | needs_attention (OK) | 75 | no | 2/2 | 15.8s |
| case_06 | No neuro exam documented | text | not_ready | not_ready (OK) | 67 | no | 4/4 | 15.2s |
| case_07 | Saddle anesthesia + new urinary retention (cauda equina), symptoms 1 week | scanned_png | ready | ready (OK) | 100 | yes | 2/2 | 15.4s |
| case_08 | History of cancer + unexplained weight loss, 2 weeks pain | text | ready | ready (OK) | 100 | yes | 1/1 | 12.9s |

## Vision transcription (scanned cases)

| Case | Similarity to source text |
|---|---|
| case_04 | 98.9% |
| case_07 | 98.8% |

## Average latency per step

| Step | Model | Calls | Avg latency |
|---|---|---|---|
| extract facts | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | 8 | 5.5s |
| ingest: read scan p1 | `nvidia/Nemotron-3.5-Super-VL` | 2 | 2.6s |
| match evidence | `nvidia/Nemotron-3-Ultra-550b-a55b` | 8 | 8.8s |
| write missing-item asks | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | 3 | 0.7s |

## Failure cases

- **case_02** `red_flag`: expected `missing`, got `met`.

## Not applicable (not counted as errors)

- case_02 `symptom_duration`: not applicable - the payer's policy has no such criterion.
- case_02 `neuro_exam`: not applicable - the payer's policy has no such criterion.
- case_05 `symptom_duration`: not applicable - the payer's policy has no such criterion.
- case_05 `neuro_exam`: not applicable - the payer's policy has no such criterion.
- case_08 `neuro_exam`: not applicable - the payer's policy has no such criterion.

_Policy criteria source per case: case_01=cache, case_02=cache, case_03=snapshot, case_04=cache, case_05=cache, case_06=cache, case_07=cache, case_08=cache._
