import logging
import os
from contextlib import contextmanager
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Iterator

LOG_CONTEXT: ContextVar[dict[str, str]] = ContextVar("log_context", default={})


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        context = LOG_CONTEXT.get()
        record.project_id = context.get("project_id", "-")
        record.run_id = context.get("run_id", "-")
        record.stage = context.get("stage", "-")
        return True


def setup_logging(
    service: str = "app",
    log_dir: Path | str | None = None,
    *,
    force: bool = False,
) -> None:
    logger = logging.getLogger("theNanGuos")
    if getattr(logger, "_the_nanguos_configured", False) and not force:
        return
    if force:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()

    directory = Path(log_dir or os.getenv("LOG_DIR", "_logs"))
    directory.mkdir(parents=True, exist_ok=True)
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    max_bytes = int(os.getenv("LOG_MAX_BYTES", str(5 * 1024 * 1024)))
    backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))

    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s "
        "project=%(project_id)s run=%(run_id)s stage=%(stage)s "
        "%(message)s"
    )
    context_filter = ContextFilter()

    file_handler = RotatingFileHandler(
        directory / f"{service}.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(context_filter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(context_filter)
    logger.addHandler(stream_handler)

    logger._the_nanguos_configured = True  # type: ignore[attr-defined]


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"theNanGuos.{name}")


@contextmanager
def log_context(**values: str | None) -> Iterator[None]:
    current = LOG_CONTEXT.get()
    next_context = {**current}
    for key, value in values.items():
        if value is None:
            next_context.pop(key, None)
        else:
            next_context[key] = value
    token = LOG_CONTEXT.set(next_context)
    try:
        yield
    finally:
        LOG_CONTEXT.reset(token)
