"""SMTP email service with Fernet encryption for stored credentials."""

import asyncio
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from cryptography.fernet import Fernet
from sqlmodel import Session, select

from app.config import get_settings
from app.models.smtp_config import SmtpConfig

logger = logging.getLogger(__name__)


def _get_fernet() -> Optional[Fernet]:
    """Get Fernet cipher from encryption key setting."""
    settings = get_settings()
    key = settings.effective_encryption_key
    if not key:
        return None
    return Fernet(key.encode())


def encrypt_password(password: str) -> str:
    """Encrypt a password using Fernet symmetric encryption."""
    fernet = _get_fernet()
    if not fernet:
        raise ValueError("SMTP_ENCRYPTION_KEY is not configured")
    return fernet.encrypt(password.encode()).decode()


def decrypt_password(encrypted: str) -> str:
    """Decrypt a Fernet-encrypted password."""
    fernet = _get_fernet()
    if not fernet:
        raise ValueError("SMTP_ENCRYPTION_KEY is not configured")
    return fernet.decrypt(encrypted.encode()).decode()


def get_smtp_config(session: Session) -> Optional[SmtpConfig]:
    """Get the singleton SMTP configuration."""
    return session.exec(select(SmtpConfig).limit(1)).first()


def send_email(
    session: Session,
    *,
    to_address: str,
    subject: str,
    body_html: str,
    body_text: Optional[str] = None,
) -> None:
    """Send an email using the stored SMTP configuration.

    Raises ValueError if SMTP is not configured or disabled.
    Raises smtplib.SMTPException on send failure.
    """
    config = get_smtp_config(session)
    if not config or not config.enabled:
        logger.warning("Email send attempted but SMTP is not configured or disabled")
        raise ValueError("SMTP is not configured")

    password = None
    if config.encrypted_password:
        password = decrypt_password(config.encrypted_password)

    msg = MIMEMultipart("alternative")
    msg["From"] = (
        f"{config.from_name} <{config.from_address}>"
        if config.from_name
        else config.from_address
    )
    msg["To"] = to_address
    msg["Subject"] = subject

    if body_text:
        msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    _send_via_smtp(config, password, msg)

    logger.info(
        "Email sent",
        extra={"to": to_address, "subject": subject},
    )


async def send_email_async(
    session: Session,
    *,
    to_address: str,
    subject: str,
    body_html: str,
    body_text: Optional[str] = None,
) -> None:
    """Async wrapper for send_email — runs blocking SMTP in a thread pool."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: send_email(
            session,
            to_address=to_address,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
        ),
    )


def send_test_email(session: Session, *, to_address: str) -> None:
    """Send a test email to verify SMTP configuration."""
    send_email(
        session,
        to_address=to_address,
        subject="Rsync Viewer — Test Email",
        body_html=(
            "<h2>SMTP Configuration Test</h2>"
            "<p>This is a test email from Rsync Viewer.</p>"
            "<p>If you received this, your SMTP configuration is working correctly.</p>"
        ),
        body_text=(
            "SMTP Configuration Test\n\n"
            "This is a test email from Rsync Viewer.\n"
            "If you received this, your SMTP configuration is working correctly."
        ),
    )


async def send_test_email_async(session: Session, *, to_address: str) -> None:
    """Async wrapper for send_test_email — runs blocking SMTP in a thread pool."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: send_test_email(session, to_address=to_address),
    )


def _send_via_smtp(
    config: SmtpConfig, password: Optional[str], msg: MIMEMultipart
) -> None:
    """Connect to SMTP server and send the message."""
    timeout = 30

    if config.encryption == "ssl_tls":
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(
            config.host, config.port, timeout=timeout, context=context
        ) as server:
            if config.username and password:
                server.login(config.username, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(config.host, config.port, timeout=timeout) as server:
            if config.encryption == "starttls":
                context = ssl.create_default_context()
                server.starttls(context=context)
            if config.username and password:
                server.login(config.username, password)
            server.send_message(msg)
