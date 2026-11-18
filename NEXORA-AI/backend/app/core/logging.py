"""NEXORA ERP — Structured Logging & Request Correlation Middleware."""
from __future__ import annotations

import contextvars
import logging
import sys

correlation_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="system"
)


class CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_ctx.get()
        return True


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("nexora_erp")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | cid=%(correlation_id)s | %(name)s | %(message)s"
        )
        handler.setFormatter(formatter)
        handler.addFilter(CorrelationFilter())
        logger.addHandler(handler)
    return logger


logger = configure_logging()
