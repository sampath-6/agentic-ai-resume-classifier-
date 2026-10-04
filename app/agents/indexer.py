from pathlib import Path

from app.services.chroma_store import get_store
from app.state import GraphState


def indexer_agent(state: GraphState) -> dict:
    store = get_store()
    record = state["current_record"]
    classified = state["current_classified"]

    doc_text = (
        f"Skills: {', '.join(classified['skills'])}\n"
        f"Role: {classified['primary_role']}\n"
        f"Seniority: {classified['seniority']}\n"
        f"Summary: {classified['summary']}\n\n"
        f"{record['text']}"
    )

    store.upsert_resume(
        doc_id=classified["resume_id"],
        text=doc_text,
        metadata={
            "resume_id": classified["resume_id"],
            "display_name": state["current_display_name"],
            "stored_filename": Path(state["current_stored_path"]).name,
            "skills": ", ".join(classified["skills"]),
            "seniority": classified["seniority"],
            "primary_role": classified["primary_role"],
            "years_experience": classified["years_experience"],
            "summary": classified["summary"],
        },
    )

    return {}
