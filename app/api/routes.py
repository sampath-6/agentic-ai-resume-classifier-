import json
import logging
import shutil
import uuid
from pathlib import Path
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import settings
from app.graph import resume_graph
from app.services.auth import get_current_user
from app.services.chroma_store import get_store

router = APIRouter(dependencies=[Depends(get_current_user)])

logger = logging.getLogger("resume.api")

_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def _thread_id(user: str, intent: str) -> str:
    """Per-user, per-run thread id: '<user>::<intent>::<uuid>'.

    The user/intent prefix groups a user's runs together for inspection via
    GET /checkpoints and in LangSmith; the uuid keeps each run's state isolated so
    the accumulating (add-reducer) fields don't bleed across separate requests."""
    return f"{user}::{intent}::{uuid.uuid4()}"


def _query_config(thread_id: str, eval_tags: Optional[str]) -> dict:
    """Graph config for a query. When hieevas tracing is on, an evaluation probe may send
    `eval_tags` (JSON, e.g. {"task_id": "Q1", "condition": "C1", "reference": "Jane Doe"})
    so its trace is scored against a known answer; normal UI searches send nothing."""
    config: dict = {"configurable": {"thread_id": thread_id}}
    if eval_tags and settings.hieevas_mode:
        import hieevas

        try:
            tags = json.loads(eval_tags)
            config = hieevas.run_config(config=config, **{k: v for k, v in tags.items() if v is not None})
        except (ValueError, TypeError, AttributeError) as exc:
            raise HTTPException(400, f"eval_tags is not valid: {exc}")
    return config


@router.post("/upload")
async def upload_resumes(
    files: List[UploadFile] = File(...),
    user: str = Depends(get_current_user),
):
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

    # this drains the ENTIRE inbox, not just the files from this request.
    # thread_id is grouped per user so a user's runs are traceable together in the
    # checkpoint viewer / LangSmith, while the uuid keeps each run's state isolated.
    thread_id = _thread_id(user, "upload")
    logger.info("upload: user=%s %d file(s) saved; run thread_id=%s", user, len(saved_paths), thread_id)
    result = resume_graph.invoke(
        {"intent": "upload", "parse_retries": 0},
        config={
            "configurable": {"thread_id": thread_id},
            "recursion_limit": settings.graph_recursion_limit,
        },
    )
    logger.info(
        "upload: thread_id=%s indexed=%d rejected=%d failed=%d",
        thread_id,
        len(result.get("indexed", [])),
        len(result.get("rejected_files", [])),
        len(result.get("parse_failures", [])),
    )

    return {
        "thread_id": thread_id,
        "uploaded": [Path(p).name for p in saved_paths],
        "indexed": result.get("indexed", []),
        "rejected": result.get("rejected_files", []),
        "failed": result.get("parse_failures", []),
    }


@router.post("/query")
async def query_resumes(
    query: str = Form(...),
    seniority: Optional[str] = Form(None),
    thread_id: Optional[str] = Form(None),
    eval_tags: Optional[str] = Form(None),
    user: str = Depends(get_current_user),
):
    where_filter = {"seniority": seniority} if seniority else None

    # A continuing chat session sends back the thread_id it was given, so the graph
    # resumes the same LangGraph thread (conversation continuity + one grouped trace).
    # We only honour ids namespaced to this user, so a client can't resume someone
    # else's thread; anything else mints a fresh one.
    if not (thread_id and thread_id.startswith(f"{user}::")):
        thread_id = _thread_id(user, "query")
    logger.info("query: thread_id=%s q=%r seniority=%s", thread_id, query[:100], seniority)
    result = resume_graph.invoke(
        {
            "intent": "query",
            "query_text": query,
            "where_filter": where_filter,
            "broaden_attempts": 0,
        },
        config=_query_config(thread_id, eval_tags),
    )

    if result.get("guardrail_blocked"):
        logger.info("query: thread_id=%s blocked by guardrail", thread_id)
        raise HTTPException(400, result.get("guardrail_reason", "Query blocked by guardrail"))

    logger.info("query: thread_id=%s matches=%d", thread_id, len(result.get("retrieved", [])))

    return {
        "thread_id": thread_id,
        "answer": result.get("answer"),
        "matches": [
            {
                "resume_id": r["metadata"].get("resume_id"),
                "display_name": r["metadata"].get("display_name"),
                "seniority": r["metadata"].get("seniority"),
                "primary_role": r["metadata"].get("primary_role"),
                "skills": r["metadata"].get("skills"),
                "years_experience": r["metadata"].get("years_experience"),
                "summary": r["metadata"].get("summary"),
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
                "summary": meta.get("summary"),
                "download_url": f"/api/resumes/{resume_id}/download",
            }
            for resume_id, meta in zip(ids, metadatas)
        ]
    }


def _truncate(obj: Any, limit: int = 500) -> Any:
    """Make a state value JSON-friendly by trimming long strings (e.g. resume text)."""
    if isinstance(obj, str):
        return obj if len(obj) <= limit else f"{obj[:limit]}... [{len(obj)} chars]"
    if isinstance(obj, dict):
        return {k: _truncate(v, limit) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_truncate(v, limit) for v in obj]
    return obj


def _serialize_snapshot(snapshot: Any) -> dict:
    cfg = (snapshot.config or {}).get("configurable", {})
    meta = snapshot.metadata or {}
    return {
        "checkpoint_id": cfg.get("checkpoint_id"),
        "created_at": snapshot.created_at,
        # 'input' = initial state, 'loop' = a graph superstep, 'update' = manual edit
        "source": meta.get("source"),
        "step": meta.get("step"),
        # nodes queued to run after this checkpoint; empty tuple means the run finished
        "next": list(snapshot.next),
        "state": _truncate(dict(snapshot.values)),
    }


@router.get("/checkpoints/{thread_id}")
async def get_checkpoints(thread_id: str):
    """Return the persisted LangGraph checkpoint timeline for a run (newest first).

    Each entry is one step of the graph: which node wrote it, what executes next, and
    the state at that point. For the full trace (LLM calls, latencies, token counts),
    open the same run in the LangSmith UI when tracing is enabled."""
    config = {"configurable": {"thread_id": thread_id}}
    history = list(resume_graph.get_state_history(config))
    if not history:
        raise HTTPException(404, f"No checkpoints found for thread {thread_id}")

    logger.info("checkpoints: thread_id=%s returned %d snapshot(s)", thread_id, len(history))
    return {
        "thread_id": thread_id,
        "count": len(history),
        "langsmith_enabled": settings.langsmith_tracing,
        "checkpoints": [_serialize_snapshot(s) for s in history],
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
