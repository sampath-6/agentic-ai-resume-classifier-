import logging
import shutil
import uuid
from pathlib import Path

from app.config import settings
from app.services.parsing import extract_text
from app.state import GraphState

logger = logging.getLogger("resume.ingestion")


def ingestion_agent(state: GraphState) -> dict:
    current_file = state["current_file"]
    attempt = state.get("parse_retries", 0) + 1
    name = Path(current_file).name

    try:
        text = extract_text(current_file, attempt=attempt)
        if not text.strip():
            raise ValueError("empty extraction")

        record = {"resume_id": str(uuid.uuid4()), "file_path": current_file, "text": text}
        logger.info("ingestion: parsed %s on attempt %d (%d chars)", name, attempt, len(text))
        return {
            "raw_texts": [record],
            "current_record": record,
            "parse_retries": 0,
            "last_ingestion_result": "success",
        }
    except Exception as exc:
        if attempt < settings.max_parse_retries:
            logger.warning("ingestion: attempt %d failed for %s (%s); retrying", attempt, name, exc)
            return {"parse_retries": attempt, "last_ingestion_result": "retry"}

        dest = Path(settings.failed_dir) / Path(current_file).name
        shutil.move(current_file, dest)
        logger.error("ingestion: exhausted retries for %s (%s); moved to failed/", name, exc)
        return {
            "parse_failures": [current_file],
            "parse_retries": 0,
            "last_ingestion_result": "exhausted",
        }
