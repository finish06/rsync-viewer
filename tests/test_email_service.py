"""Tests for app/services/email.py — covers uncovered SMTP paths.

Targets:
  - send_email with body_text (line 82)
  - send_email_async wrapper (lines 102-103)
  - _send_via_smtp SSL/TLS and STARTTLS paths (lines 147-164)
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from app.services.email import (
    _send_via_smtp,
    send_email,
    send_email_async,
    send_test_email,
)


class FakeSmtpConfig:
    """Minimal stand-in for SmtpConfig model."""

    def __init__(
        self,
        *,
        host="mail.test.local",
        port=587,
        username="user@test.local",
        encrypted_password="encrypted-pw",
        from_address="noreply@test.local",
        from_name="Test Sender",
        enabled=True,
        encryption="starttls",
    ):
        self.host = host
        self.port = port
        self.username = username
        self.encrypted_password = encrypted_password
        self.from_address = from_address
        self.from_name = from_name
        self.enabled = enabled
        self.encryption = encryption


class TestSendViaSMTP:
    """Cover the _send_via_smtp function's branching paths."""

    @patch("app.services.email.smtplib.SMTP")
    def test_starttls_path(self, mock_smtp_cls):
        """STARTTLS: plain connection → starttls() → login → send."""
        server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        config = FakeSmtpConfig(encryption="starttls", port=587)
        msg = MagicMock()

        _send_via_smtp(config, "secret123", msg)

        mock_smtp_cls.assert_called_once_with(config.host, config.port, timeout=30)
        server.starttls.assert_called_once()
        server.login.assert_called_once_with(config.username, "secret123")
        server.send_message.assert_called_once_with(msg)

    @patch("app.services.email.smtplib.SMTP_SSL")
    def test_ssl_tls_path(self, mock_smtp_ssl_cls):
        """SSL/TLS: direct SSL connection → login → send."""
        server = MagicMock()
        mock_smtp_ssl_cls.return_value.__enter__ = MagicMock(return_value=server)
        mock_smtp_ssl_cls.return_value.__exit__ = MagicMock(return_value=False)

        config = FakeSmtpConfig(encryption="ssl_tls", port=465)
        msg = MagicMock()

        _send_via_smtp(config, "secret123", msg)

        mock_smtp_ssl_cls.assert_called_once()
        server.login.assert_called_once_with(config.username, "secret123")
        server.send_message.assert_called_once_with(msg)

    @patch("app.services.email.smtplib.SMTP")
    def test_no_encryption_path(self, mock_smtp_cls):
        """No encryption: plain SMTP, no starttls call."""
        server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        config = FakeSmtpConfig(encryption="none", port=25)
        msg = MagicMock()

        _send_via_smtp(config, "secret123", msg)

        server.starttls.assert_not_called()
        server.login.assert_called_once()
        server.send_message.assert_called_once_with(msg)

    @patch("app.services.email.smtplib.SMTP")
    def test_no_auth_when_no_password(self, mock_smtp_cls):
        """Skip login when password is None."""
        server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        config = FakeSmtpConfig(encryption="none", port=25)
        msg = MagicMock()

        _send_via_smtp(config, None, msg)

        server.login.assert_not_called()
        server.send_message.assert_called_once_with(msg)


class TestSendEmail:
    """Cover send_email including the body_text attachment path."""

    @patch("app.services.email._send_via_smtp")
    @patch("app.services.email.decrypt_password", return_value="plain-pw")
    @patch("app.services.email.get_smtp_config")
    def test_with_body_text(self, mock_get_cfg, mock_decrypt, mock_send):
        """When body_text is provided, it should be attached as text/plain."""
        mock_get_cfg.return_value = FakeSmtpConfig()
        session = MagicMock()

        send_email(
            session,
            to_address="user@example.com",
            subject="Test",
            body_html="<p>Hello</p>",
            body_text="Hello plain",
        )

        mock_send.assert_called_once()
        msg = mock_send.call_args[0][2]
        payloads = msg.get_payload()
        # Should have 2 parts: plain text + HTML
        assert len(payloads) == 2
        assert payloads[0].get_content_type() == "text/plain"
        assert payloads[1].get_content_type() == "text/html"

    @patch("app.services.email._send_via_smtp")
    @patch("app.services.email.decrypt_password", return_value="plain-pw")
    @patch("app.services.email.get_smtp_config")
    def test_without_body_text(self, mock_get_cfg, mock_decrypt, mock_send):
        """When body_text is None, only HTML part is attached."""
        mock_get_cfg.return_value = FakeSmtpConfig()
        session = MagicMock()

        send_email(
            session,
            to_address="user@example.com",
            subject="Test",
            body_html="<p>Hello</p>",
        )

        msg = mock_send.call_args[0][2]
        payloads = msg.get_payload()
        assert len(payloads) == 1
        assert payloads[0].get_content_type() == "text/html"

    @patch("app.services.email.get_smtp_config")
    def test_raises_when_smtp_not_configured(self, mock_get_cfg):
        mock_get_cfg.return_value = None
        session = MagicMock()

        with pytest.raises(ValueError, match="SMTP is not configured"):
            send_email(
                session,
                to_address="user@example.com",
                subject="Test",
                body_html="<p>Hello</p>",
            )

    @patch("app.services.email.get_smtp_config")
    def test_raises_when_smtp_disabled(self, mock_get_cfg):
        mock_get_cfg.return_value = FakeSmtpConfig(enabled=False)
        session = MagicMock()

        with pytest.raises(ValueError, match="SMTP is not configured"):
            send_email(
                session,
                to_address="user@example.com",
                subject="Test",
                body_html="<p>Hello</p>",
            )

    @patch("app.services.email._send_via_smtp")
    @patch("app.services.email.get_smtp_config")
    def test_no_password_decryption_when_empty(self, mock_get_cfg, mock_send):
        """No encrypted_password → password=None passed to _send_via_smtp."""
        config = FakeSmtpConfig(encrypted_password=None)
        mock_get_cfg.return_value = config
        session = MagicMock()

        send_email(
            session,
            to_address="user@example.com",
            subject="Test",
            body_html="<p>Hello</p>",
        )

        # password arg should be None
        assert mock_send.call_args[0][1] is None

    @patch("app.services.email._send_via_smtp")
    @patch("app.services.email.decrypt_password", return_value="plain-pw")
    @patch("app.services.email.get_smtp_config")
    def test_from_name_in_header(self, mock_get_cfg, mock_decrypt, mock_send):
        mock_get_cfg.return_value = FakeSmtpConfig(from_name="My App")
        session = MagicMock()

        send_email(
            session,
            to_address="user@example.com",
            subject="Test",
            body_html="<p>Hello</p>",
        )

        msg = mock_send.call_args[0][2]
        assert "My App" in msg["From"]

    @patch("app.services.email._send_via_smtp")
    @patch("app.services.email.decrypt_password", return_value="plain-pw")
    @patch("app.services.email.get_smtp_config")
    def test_no_from_name(self, mock_get_cfg, mock_decrypt, mock_send):
        mock_get_cfg.return_value = FakeSmtpConfig(from_name=None)
        session = MagicMock()

        send_email(
            session,
            to_address="user@example.com",
            subject="Test",
            body_html="<p>Hello</p>",
        )

        msg = mock_send.call_args[0][2]
        assert msg["From"] == "noreply@test.local"


class TestSendEmailAsync:
    """Cover the async wrappers."""

    @patch("app.services.email.send_email")
    def test_send_email_async_delegates(self, mock_send):
        """send_email_async runs send_email in a thread pool."""
        session = MagicMock()

        asyncio.get_event_loop().run_until_complete(
            send_email_async(
                session,
                to_address="user@example.com",
                subject="Test",
                body_html="<p>Hello</p>",
                body_text="Hello",
            )
        )

        mock_send.assert_called_once_with(
            session,
            to_address="user@example.com",
            subject="Test",
            body_html="<p>Hello</p>",
            body_text="Hello",
        )


class TestSendTestEmail:
    """Cover send_test_email (passes body_text to send_email)."""

    @patch("app.services.email.send_email")
    def test_sends_with_body_text(self, mock_send):
        session = MagicMock()
        send_test_email(session, to_address="admin@example.com")

        mock_send.assert_called_once()
        kwargs = mock_send.call_args
        assert kwargs[1]["body_text"] is not None
        assert "SMTP Configuration Test" in kwargs[1]["body_text"]
        assert kwargs[1]["to_address"] == "admin@example.com"
