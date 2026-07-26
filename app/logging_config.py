"""Structured JSON logging.

Every request-scoped log line carries request_id / partner_id / a hashed
member_id so on-call can grep CloudWatch Logs Insights by any of those without
ever having a raw member identifier at rest in logs.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
from contextvars import ContextVar

from app.config import settings

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_partner_id: ContextVar[str | None] = ContextVar("partner_id", default=None)
_member_id_hash: ContextVar[str | None] = ContextVar("member_id_hash", default=None)


def hash_member_id(member_id: str) -> str:
    return hashlib.sha256(member_id.encode()).hexdigest()[:16]


def bind_context(
    *, request_id: str, partner_id: str | None = None, member_id: str | None = None
) -> None:
    _request_id.set(request_id)
    if partner_id is not None:
        _partner_id.set(partner_id)
    if member_id is not None:
        _member_id_hash.set(hash_member_id(member_id))


def clear_context() -> None:
    _request_id.set(None)
    _partner_id.set(None)
    _member_id_hash.set(None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": _request_id.get(),
            "partner_id": _partner_id.get(),
            "member_id_hash": _member_id_hash.get(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        extra = getattr(record, "extra_fields", None)
        if extra:
            payload.update(extra)
        return json.dumps(payload)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
