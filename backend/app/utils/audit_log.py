from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from .request_id import get_request_id

AuditAction = Literal[
    "reservation.created",
    "reservation.cancelled",
    "reservation.rescheduled",
    "reservation.autocancelled",
    "reservation.shop_cancelled",
]
AuditInitiator = Literal["user", "system", "shop"]

_audit_logger = logging.getLogger("audit")
_audit_logger.setLevel(logging.INFO)
if not _audit_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    _audit_logger.addHandler(handler)
_audit_logger.propagate = False


def _enum_to_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "value"):
        try:
            return str(value.value)
        except Exception:
            return str(value)
    return str(value)


def emit_audit_log(
    *,
    action: AuditAction,
    initiator: AuditInitiator,
    reservation_id: int,
    slot_id: Optional[int],
    shop_id: Optional[int],
    user_id: Optional[int],
    party_size: Optional[int],
    status_from: Optional[str],
    status_to: Optional[str],
    version: Optional[int],
    message: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> None:
    """Emit structured JSON audit log. Raises RuntimeError if logging fails."""
    status_from_val = _enum_to_str(status_from)
    status_to_val = _enum_to_str(status_to)
    payload: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": "info",
        "action": action,
        "initiator": initiator,
        "request_id": get_request_id(),
        "reservation_id": reservation_id,
        "slot_id": slot_id,
        "shop_id": shop_id,
        "user_id": user_id,
        "party_size": party_size,
        "status_from": status_from_val,
        "status_to": status_to_val,
        "version": version,
    }
    if message is not None:
        payload["message"] = message
    if extra:
        payload.update(extra)

    # Drop None values to keep the log compact.
    compact_payload = {k: v for k, v in payload.items() if v is not None}
    try:
        _audit_logger.info(json.dumps(compact_payload, ensure_ascii=True))
    except Exception as exc:  # pragma: no cover - defensive
        raise RuntimeError("failed to emit audit log") from exc
