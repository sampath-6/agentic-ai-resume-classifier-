import logging
import logging.handlers
from pathlib import Path

from app.config import settings

_FORMAT = "%(asctime)s %(levelname)-8s %(name)s | %(message)s"


def setup_logging() -> None:
    """Configure root logging once: console + a rotating file at LOG_DIR/app.log.

    Idempotent — safe to call more than once (e.g. app startup and test setup)."""
    root = logging.getLogger()
    if getattr(root, "_resume_configured", False):
        return

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root.setLevel(level)
    formatter = logging.Formatter(_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    Path(settings.log_dir).mkdir(parents=True, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        Path(settings.log_dir) / "app.log",
        maxBytes=5_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # keep third-party chatter out of our logs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    root._resume_configured = True  # type: ignore[attr-defined]
