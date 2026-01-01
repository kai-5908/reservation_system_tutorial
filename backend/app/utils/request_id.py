from __future__ import annotations

import uuid
from contextvars import ContextVar
from typing import Optional

_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def generate_request_id() -> str:
    """Generate a random request id."""
    return uuid.uuid4().hex


def set_request_id(request_id: str | None) -> None:
    """Store request id in context (None to clear)."""
    _request_id_ctx.set(request_id)


def get_request_id() -> Optional[str]:
    """Return current request id if set."""
    return _request_id_ctx.get()
