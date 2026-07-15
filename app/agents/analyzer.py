import shutil
from pathlib import Path

from app.config import settings
from app.state import GraphState


def analyzer_agent(state: GraphState) -> dict:
    current_file = state["file_paths"][0]
    size = Path(current_file).stat().st_size

    if size > settings.max_file_size_bytes:
        dest = Path(settings.rejected_dir) / Path(current_file).name
        shutil.move(current_file, dest)
        return {"current_file": current_file, "oversized": True, "rejected_files": [current_file]}

    return {"current_file": current_file, "oversized": False}
