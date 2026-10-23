"""Re-fetch each payer's policy via Tavily, convert to criteria with Nemotron,
and write commit-safe snapshots (criteria + URL + date only, no policy text).

Usage: python scripts/refresh_snapshots.py [payer ...]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from authassist import config, criteria, policy, tracing  # noqa: E402


def main() -> None:
    proc = config.procedure_config("lumbar_mri")
    payers = sys.argv[1:] or list(proc["payers"])
    for payer in payers:
        with tracing.tracing() as tracer:
            bundle = policy.find_policy(payer, "lumbar_mri", force_refresh=True)
            if bundle.policy.source == "snapshot":
                print(f"[SKIP] {payer}: live lookup failed; snapshot left unchanged")
                continue
            crits = criteria.policy_to_criteria(bundle.text or "", bundle.policy, proc)
            policy.save_criteria(payer, "lumbar_mri", crits)
            path = policy.write_snapshot(payer, "lumbar_mri", bundle, crits)
        print(
            f"[OK] {payer}: {bundle.policy.url}\n     {len(crits)} criteria -> {path.relative_to(config.ROOT)}"
        )
        for e in tracer.entries:
            print(f"     {e.step:30} {e.model:40} {e.latency_ms}ms")


if __name__ == "__main__":
    main()
