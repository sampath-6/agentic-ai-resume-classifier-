import shutil
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import settings
from app.graph import resume_graph
from app.services.auth import get_current_user
from app.services.chroma_store import get_store

router = APIRouter(dependencies=[Depends(get_current_user)])

_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


@router.post("/upload")
async def upload_resumes(files: List[UploadFile] = File(...)):
    saved_paths = []
    for f in files:
        safe_name = Path(f.filename).name  # strip any path components, e.g. "../../etc/passwd"
        ext = Path(safe_name).suffix.lower()
        if ext not in _ALLOWED_EXTENSIONS:
            raise HTTPException(400, f"Unsupported file type: {safe_name}")

        dest = Path(settings.inbox_dir) / safe_name
        if not dest.resolve().is_relative_to(Path(settings.inbox_dir).resolve()):
            raise HTTPException(400, f"Invalid filename: {f.filename}")

        with dest.open("wb") as out:
            shutil.copyfileobj(f.file, out)
        saved_paths.append(str(dest))

    # this drains the ENTIRE inbox, not just the files from this request
    thread_id = str(uuid.uuid4())
    result = resume_graph.invoke(
        {"intent": "upload", "parse_retries": 0},
        config={
            "configurable": {"thread_id": thread_id},
            "recursion_limit": settings.graph_recursion_limit,
        },
    )

    return {
        "thread_id": thread_id,
        "uploaded": [Path(p).name for p in saved_paths],
        "indexed": result.get("indexed", []),
        "rejected": result.get("rejected_files", []),
        "failed": result.get("parse_failures", []),
    }


@router.post("/query")
async def query_resumes(query: str = Form(...), seniority: Optional[str] = Form(None)):
    where_filter = {"seniority": seniority} if seniority else None

    thread_id = str(uuid.uuid4())
    result = resume_graph.invoke(
        {
            "intent": "query",
            "query_text": query,
            "where_filter": where_filter,
            "broaden_attempts": 0,
        },
        config={"configurable": {"thread_id": thread_id}},
    )

    if result.get("guardrail_blocked"):
        raise HTTPException(400, result.get("guardrail_reason", "Query blocked by guardrail"))

    return {
        "answer": result.get("answer"),
        "matches": [
            {
                "resume_id": r["metadata"].get("resume_id"),
                "display_name": r["metadata"].get("display_name"),
                "seniority": r["metadata"].get("seniority"),
                "primary_role": r["metadata"].get("primary_role"),
                "skills": r["metadata"].get("skills"),
                "years_experience": r["metadata"].get("years_experience"),
                "download_url": f"/api/resumes/{r['metadata'].get('resume_id')}/download",
                "distance": r["distance"],
            }
            for r in result.get("retrieved", [])
        ],
    }


@router.get("/resumes")
async def list_resumes():
    store = get_store()
    data = store.list_all()
    ids = data.get("ids") or []
    metadatas = data.get("metadatas") or []

    return {
        "resumes": [
            {
                "resume_id": resume_id,
                "display_name": meta.get("display_name"),
                "seniority": meta.get("seniority"),
                "primary_role": meta.get("primary_role"),
                "skills": meta.get("skills"),
                "years_experience": meta.get("years_experience"),
                "download_url": f"/api/resumes/{resume_id}/download",
            }
            for resume_id, meta in zip(ids, metadatas)
        ]
    }


@router.get("/resumes/{resume_id}/download")
async def download_resume(resume_id: str):
    store = get_store()
    record = store.get_by_id(resume_id)

    metadatas = record.get("metadatas") or []
    if not metadatas:
        raise HTTPException(404, "Resume not found")

    stored_filename = metadatas[0].get("stored_filename")
    file_path = Path(settings.indexed_dir) / stored_filename
    if not file_path.is_file():
        raise HTTPException(404, "Resume file missing on disk")

    return FileResponse(file_path, filename=stored_filename)
