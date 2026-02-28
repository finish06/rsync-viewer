"""Tests for NotificationLogRead schema — coverage for app/schemas/notification_log.py."""

from datetime import datetime
from uuid import uuid4

from app.schemas.notification_log import NotificationLogRead


class TestNotificationLogRead:
    """Exercise the NotificationLogRead Pydantic schema."""

    def test_creates_from_dict(self):
        data = {
            "id": uuid4(),
            "failure_event_id": uuid4(),
            "webhook_endpoint_id": uuid4(),
            "status": "sent",
            "http_status_code": 200,
            "error_message": None,
            "attempt_number": 1,
            "created_at": datetime(2026, 1, 15, 12, 0, 0),
        }
        schema = NotificationLogRead(**data)
        assert schema.status == "sent"
        assert schema.http_status_code == 200
        assert schema.attempt_number == 1

    def test_optional_fields_can_be_none(self):
        data = {
            "id": uuid4(),
            "failure_event_id": uuid4(),
            "webhook_endpoint_id": uuid4(),
            "status": "failed",
            "http_status_code": None,
            "error_message": None,
            "attempt_number": 3,
            "created_at": datetime(2026, 1, 15, 12, 0, 0),
        }
        schema = NotificationLogRead(**data)
        assert schema.http_status_code is None
        assert schema.error_message is None

    def test_error_message_populated(self):
        data = {
            "id": uuid4(),
            "failure_event_id": uuid4(),
            "webhook_endpoint_id": uuid4(),
            "status": "failed",
            "http_status_code": 500,
            "error_message": "Connection refused",
            "attempt_number": 2,
            "created_at": datetime(2026, 1, 15, 12, 0, 0),
        }
        schema = NotificationLogRead(**data)
        assert schema.error_message == "Connection refused"
        assert schema.http_status_code == 500

    def test_from_attributes_config(self):
        """Schema supports from_attributes for ORM model conversion."""
        assert NotificationLogRead.model_config.get("from_attributes") is True
