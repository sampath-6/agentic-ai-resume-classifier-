import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Settings:
    # uploads/resume/ tree
    upload_root: str = os.getenv("UPLOAD_ROOT", "./uploads/resume")
    inbox_dir: str = upload_root
    indexed_dir: str = os.path.join(upload_root, "indexed")
    rejected_dir: str = os.path.join(upload_root, "rejected")
    failed_dir: str = os.path.join(upload_root, "failed")

    max_file_size_bytes: int = int(os.getenv("MAX_FILE_SIZE_BYTES", str(2 * 1024 * 1024)))

    chroma_dir: str = os.getenv("CHROMA_DIR", "./chroma_db")
    chroma_collection: str = os.getenv("CHROMA_COLLECTION", "resumes")

    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

    # LLM backend: "anthropic" (Claude API, billed) or "ollama" (local model, free)
    llm_provider: str = os.getenv("LLM_PROVIDER", "anthropic").lower()
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # hieevas evaluation tracing: "" (off), "local" (spans to a JSONL file) or "cloud"
    hieevas_mode: str = os.getenv("HIEEVAS_MODE", "").lower()
    hieevas_trace_path: str = os.getenv("HIEEVAS_TRACE_PATH", "./traces/spans.jsonl")

    max_parse_retries: int = int(os.getenv("MAX_PARSE_RETRIES", "2"))
    max_broaden_attempts: int = int(os.getenv("MAX_BROADEN_ATTEMPTS", "2"))

    top_k: int = int(os.getenv("TOP_K", "20"))
    narration_count: int = int(os.getenv("NARRATION_COUNT", "5"))

    guardrail_keywords_path: str = os.getenv(
        "GUARDRAIL_KEYWORDS_PATH", "./config/guardrail_keywords.txt"
    )

    # each resume passes through several graph steps (analyzer, ingestion retries,
    # classifier, rename, indexer, re-scan) before the loop reaches the next file,
    # so the recursion limit must scale with inbox size, not step count of one file
    graph_recursion_limit: int = int(os.getenv("GRAPH_RECURSION_LIMIT", "1000"))

    allowed_email: str = os.getenv("ALLOWED_EMAIL", "your-email@example.com")
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret-change-me")
    jwt_expiry_minutes: int = int(os.getenv("JWT_EXPIRY_MINUTES", "1440"))

    cors_origins: list = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    ]

    # persistent LangGraph checkpointer (SQLite). Every graph run's state history is
    # written here and survives restarts, so it can be inspected after the fact.
    checkpoint_db: str = os.getenv("CHECKPOINT_DB", "./checkpoints.sqlite")

    # logging
    log_dir: str = os.getenv("LOG_DIR", "./logs")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # LangSmith tracing. When enabled, every llm.invoke and graph node execution is
    # traced to the LangSmith UI without touching call sites (LangChain reads env vars).
    langsmith_tracing: bool = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
    langsmith_api_key: str = os.getenv("LANGSMITH_API_KEY", "")
    langsmith_project: str = os.getenv("LANGSMITH_PROJECT", "resume-classifier")
    langsmith_endpoint: str = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")


settings = Settings()

# Propagate LangSmith config into the env var names LangChain/LangGraph read at runtime.
# We set both the modern LANGSMITH_* names and the legacy LANGCHAIN_* aliases so tracing
# works regardless of which the installed langchain-core version checks.
if settings.langsmith_tracing and settings.langsmith_api_key:
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)
    os.environ.setdefault("LANGCHAIN_API_KEY", settings.langsmith_api_key)
    os.environ.setdefault("LANGSMITH_PROJECT", settings.langsmith_project)
    os.environ.setdefault("LANGCHAIN_PROJECT", settings.langsmith_project)
    os.environ.setdefault("LANGSMITH_ENDPOINT", settings.langsmith_endpoint)
    os.environ.setdefault("LANGCHAIN_ENDPOINT", settings.langsmith_endpoint)

for path in (
    settings.inbox_dir,
    settings.indexed_dir,
    settings.rejected_dir,
    settings.failed_dir,
    settings.chroma_dir,
    settings.log_dir,
    os.path.dirname(settings.checkpoint_db) or ".",
):
    Path(path).mkdir(parents=True, exist_ok=True)
