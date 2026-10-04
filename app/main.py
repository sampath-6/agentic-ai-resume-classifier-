import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.routes import router
from app.config import settings
from app.services.logging_config import setup_logging

setup_logging()
logger = logging.getLogger("resume.main")
logger.info(
    "startup: checkpoint_db=%s, langsmith_tracing=%s, project=%s, llm=%s",
    settings.checkpoint_db,
    settings.langsmith_tracing,
    settings.langsmith_project if settings.langsmith_tracing else "-",
    settings.ollama_model if settings.llm_provider == "ollama" else settings.anthropic_model,
)

# hieevas evaluation: every graph run (UI uploads and searches) is traced to
# settings.hieevas_trace_path; view it with `hieevas-dashboard --source file:<path>`
if settings.hieevas_mode:
    import hieevas

    hieevas.init(settings.hieevas_mode, service_name="resume-classifier", path=settings.hieevas_trace_path)
    logger.info("startup: hieevas tracing on (%s) -> %s", settings.hieevas_mode, settings.hieevas_trace_path)

app = FastAPI(title="Resume Classifier — Multi-Agent (LangGraph + Chroma)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(router, prefix="/api")


@app.get("/")
def health():
    return {"status": "ok"}
