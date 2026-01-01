import json
from typing import Any, List

import pytest
from app.models import ReservationStatus
from app.utils import audit_log
from app.utils.request_id import set_request_id


def test_emit_audit_log_outputs_json(monkeypatch) -> None:
    messages: List[str] = []

    class DummyLogger:
        def info(self, message: str) -> None:
            messages.append(message)

    dummy_logger = DummyLogger()
    monkeypatch.setattr(audit_log, "_audit_logger", dummy_logger)

    set_request_id("req-123")
    audit_log.emit_audit_log(
        action="reservation.created",
        initiator="user",
        reservation_id=1,
        slot_id=2,
        shop_id=3,
        user_id=4,
        party_size=2,
        status_from=None,
        status_to=ReservationStatus.BOOKED,
        version=1,
    )
    assert len(messages) == 1
    payload = json.loads(messages[0])
    assert payload["action"] == "reservation.created"
    assert payload["initiator"] == "user"
    assert payload["request_id"] == "req-123"
    assert payload["status_to"] == "booked"
    assert "timestamp" in payload


def test_emit_audit_log_raises_on_logger_failure(monkeypatch) -> None:
    class DummyLogger:
        def info(self, _: Any) -> None:
            raise ValueError("fail")

    dummy_logger = DummyLogger()
    monkeypatch.setattr(audit_log, "_audit_logger", dummy_logger)

    with pytest.raises(RuntimeError):
        audit_log.emit_audit_log(
            action="reservation.cancelled",
            initiator="user",
            reservation_id=1,
            slot_id=2,
            shop_id=3,
            user_id=4,
            party_size=2,
            status_from=ReservationStatus.BOOKED,
            status_to=ReservationStatus.CANCELLED,
            version=2,
        )
