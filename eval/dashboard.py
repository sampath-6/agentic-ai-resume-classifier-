"""Live hieevas dashboard for the resume classifier.

    .venv\\Scripts\\python -m eval.dashboard          # http://localhost:8051

Reads the spans the backend writes (HIEEVAS_TRACE_PATH) and re-evaluates them on every
page load (60 s cache). Probe searches are scored with `top_match`: correct when the
expected candidate is the first one the answer names.
"""
from __future__ import annotations

import argparse

from hieevas.serve import serve

from app.config import settings
from app.services.chroma_store import get_store


def candidate_names() -> list[str]:
    metas = get_store().collection.get(include=["metadatas"])["metadatas"]
    return sorted({m.get("display_name") for m in metas if m.get("display_name")})


def top_match(answer, reference) -> bool:
    """True when `reference` is the earliest-mentioned indexed candidate in the answer."""
    text = str(answer or "").lower()
    positions = {n: text.find(n.lower()) for n in candidate_names() + [reference]}
    named = {n: p for n, p in positions.items() if p >= 0}
    return bool(named) and min(named, key=named.get).lower() == str(reference).lower()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8051)
    ap.add_argument("--hours", type=float, default=24 * 7)
    args = ap.parse_args()
    serve(f"file:{settings.hieevas_trace_path}", port=args.port, hours=args.hours,
          group_by=("condition",), architecture="resume-graph", scorer=top_match,
          title="Resume classifier – live evaluation (hieevas)")


if __name__ == "__main__":
    main()
