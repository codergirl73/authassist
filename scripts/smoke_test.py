"""M1 connectivity check: one call per model role + one Tavily search.

Usage: python scripts/smoke_test.py
"""

import base64
import io
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from authassist import config, llm, tracing  # noqa: E402


def tiny_note_png() -> str:
    img = Image.new("RGB", (520, 90), "white")
    ImageDraw.Draw(img).text((10, 30), "Patient reports low back pain for 8 weeks.", fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def main() -> int:
    ok = True
    with tracing.tracing() as tracer:
        for role, messages in [
            ("fast", [{"role": "user", "content": "Reply with exactly: OK"}]),
            ("reasoning", [{"role": "user", "content": "In one sentence: what is CPT 72148?"}]),
            ("vision", [llm.image_message("Transcribe the text in this image exactly.", [tiny_note_png()])]),
        ]:
            try:
                result = llm.chat(role, messages, step=f"smoke:{role}")
                print(f"[OK]   {role:9} {result.model} {result.latency_ms}ms -> {result.text[:100]!r}")
            except Exception as err:
                ok = False
                print(f"[FAIL] {role:9} {err}")

        try:
            from tavily import TavilyClient

            with tracing.timed("smoke:tavily", "tavily", "tavily.search"):
                res = TavilyClient(api_key=config.tavily_api_key()).search(
                    "Aetna lumbar spine MRI clinical policy bulletin", max_results=3
                )
            top = res["results"][0]
            print(f"[OK]   tavily    {top['title'][:70]} — {top['url']}")
        except Exception as err:
            ok = False
            print(f"[FAIL] tavily    {err}")

    print("\nTrace:")
    for e in tracer.entries:
        print(f"  {e.step:16} {e.role:9} {e.model:45} {e.latency_ms:6}ms ok={e.success} {e.note or ''}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
