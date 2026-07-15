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


settings = Settings()

for path in (
    settings.inbox_dir,
    settings.indexed_dir,
    settings.rejected_dir,
    settings.failed_dir,
    settings.chroma_dir,
):
    Path(path).mkdir(parents=True, exist_ok=True)
