"""Unit tests for the SMTP email service.

Covers: AC-004, AC-005, AC-008, AC-009
"""

from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from app.services.email import (
    decrypt_password,
    encrypt_password,
    get_smtp_config,
    send_email,
)


# Generate a real Fernet key for tests
_TEST_FERNET_KEY = Fernet.generate_key().decode()


@pytest.fixture(autouse=True)
def _mock_settings():
    """Override get_settings to provide a test encryption key."""
    mock_settings = MagicMock()
    mock_settings.smtp_encryption_key = _TEST_FERNET_KEY
    with patch("app.services.email.get_settings", return_value=mock_settings):
        yield mock_settings


class TestFernetEncryption:
    """AC-004: SMTP credentials encrypted at rest."""

    def test_ac004_encrypt_decrypt_roundtrip(self):
        """Encrypting then decrypting returns the original password."""
        original = "my-smtp-password-123!"
        encrypted = encrypt_password(original)
        assert encrypted != original
        assert decrypt_password(encrypted) == original

    def test_ac004_encrypted_value_is_not_plaintext(self):
        """Encrypted password must not contain the original value."""
        original = "super-secret"
        encrypted = encrypt_password(original)
        assert original not in encrypted

    def test_ac004_encrypt_raises_without_key(self, _mock_settings):
        """Encryption raises ValueError when key is not configured."""
        _mock_settings.smtp_encryption_key = ""
        with pytest.raises(ValueError, match="SMTP_ENCRYPTION_KEY is not configured"):
            encrypt_password("test")

    def test_ac004_decrypt_raises_without_key(self, _mock_settings):
        """Decryption raises ValueError when key is not configured."""
        _mock_settings.smtp_encryption_key = ""
        with pytest.raises(ValueError, match="SMTP_ENCRYPTION_KEY is not configured"):
            decrypt_password("gAAAAAB...")


class TestGetSmtpConfig:
    """AC-009: Singleton SMTP configuration."""

    def test_ac009_returns_none_when_no_config(self):
        """Returns None when no SMTP config exists."""
        mock_session = MagicMock()
        mock_exec = MagicMock()
        mock_exec.first.return_value = None
        mock_session.exec.return_value = mock_exec

        result = get_smtp_config(mock_session)
        assert result is None

    def test_ac009_returns_config_when_exists(self):
        """Returns the singleton SMTP config."""
        mock_config = MagicMock()
        mock_session = MagicMock()
        mock_exec = MagicMock()
        mock_exec.first.return_value = mock_config
        mock_session.exec.return_value = mock_exec

        result = get_smtp_config(mock_session)
        assert result is mock_config


class TestSendEmail:
    """AC-008: Graceful handling of missing SMTP config."""

    def test_ac008_raises_when_no_config(self):
        """send_email raises ValueError when SMTP is not configured."""
        mock_session = MagicMock()
        mock_exec = MagicMock()
        mock_exec.first.return_value = None
        mock_session.exec.return_value = mock_exec

        with pytest.raises(ValueError, match="SMTP is not configured"):
            send_email(
                mock_session,
                to_address="test@example.com",
                subject="Test",
                body_html="<p>Test</p>",
            )

    def test_ac008_raises_when_config_disabled(self):
        """send_email raises ValueError when SMTP config is disabled."""
        mock_config = MagicMock()
        mock_config.enabled = False
        mock_session = MagicMock()
        mock_exec = MagicMock()
        mock_exec.first.return_value = mock_config
        mock_session.exec.return_value = mock_exec

        with pytest.raises(ValueError, match="SMTP is not configured"):
            send_email(
                mock_session,
                to_address="test@example.com",
                subject="Test",
                body_html="<p>Test</p>",
            )

    @patch("app.services.email._send_via_smtp")
    def test_ac005_password_decrypted_for_sending(self, mock_send):
        """Password is decrypted before being passed to SMTP sender."""
        encrypted_pw = encrypt_password("real-password")

        mock_config = MagicMock()
        mock_config.enabled = True
        mock_config.encrypted_password = encrypted_pw
        mock_config.from_name = "Test"
        mock_config.from_address = "test@example.com"

        mock_session = MagicMock()
        mock_exec = MagicMock()
        mock_exec.first.return_value = mock_config
        mock_session.exec.return_value = mock_exec

        send_email(
            mock_session,
            to_address="recipient@example.com",
            subject="Hello",
            body_html="<p>Hi</p>",
        )

        mock_send.assert_called_once()
        _, call_password, _ = mock_send.call_args[0]
        assert call_password == "real-password"
