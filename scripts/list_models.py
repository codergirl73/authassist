"""Print Nemotron model IDs available on Nebius Token Factory.

Usage: python scripts/list_models.py [--all]
"""

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from authassist import config  # noqa: E402


def main() -> None:
    url = config.NEBIUS_BASE_URL.rstrip("/") + "/models"
    resp = httpx.get(url, headers={"Authorization": f"Bearer {config.nebius_api_key()}"}, timeout=30)
    resp.raise_for_status()
    ids = sorted(m["id"] for m in resp.json().get("data", []))
    show_all = "--all" in sys.argv
    matches = [i for i in ids if show_all or "nemotron" in i.lower()]
    print(f"{len(matches)} model(s){'' if show_all else ' matching nemotron'} of {len(ids)} total:")
    for model_id in matches:
        print(" ", model_id)


if __name__ == "__main__":
    main()
