import re
import shutil
from pathlib import Path

from app.config import settings
from app.state import GraphState

_UNSAFE = re.compile(r"[^A-Za-z0-9]+")


def _slug(part: str) -> str:
    return _UNSAFE.sub("", part) or "Unknown"


def _unique_destination(indexed_dir: Path, base_name: str, ext: str) -> Path:
    candidate = indexed_dir / f"{base_name}{ext}"
    suffix = 2
    while candidate.exists():
        candidate = indexed_dir / f"{base_name}_{suffix}{ext}"
        suffix += 1
    return candidate


def rename_agent(state: GraphState) -> dict:
    record = state["current_record"]
    classified = state["current_classified"]
    indexed_dir = Path(settings.indexed_dir)

    first = _slug(classified["first_name"])
    last = _slug(classified["last_name"])
    years = int(round(classified["years_experience"]))
    base_name = f"{first}_{last}_{years}"
    ext = Path(record["file_path"]).suffix.lower()

    dest = _unique_destination(indexed_dir, base_name, ext)
    shutil.move(record["file_path"], dest)

    return {
        "current_stored_path": str(dest),
        "current_display_name": f"{classified['first_name']} {classified['last_name']}",
        "indexed": [record["resume_id"]],
    }
