from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from alembic import context

# Import ALL model modules so their tables register on SQLModel.metadata
import app.models.sync_log  # noqa: F401 — SyncLog, ApiKey
import app.models.monitor  # noqa: F401 — SyncSourceMonitor
import app.models.failure_event  # noqa: F401 — FailureEvent
import app.models.webhook  # noqa: F401 — WebhookEndpoint
import app.models.webhook_options  # noqa: F401 — WebhookOptions
import app.models.notification_log  # noqa: F401 — NotificationLog
import app.models.smtp_config  # noqa: F401 — SmtpConfig
import app.models.oidc_config  # noqa: F401 — OidcConfig
import app.models.user  # noqa: F401 — User, RefreshToken, PasswordResetToken
import app.models.synthetic_check_config  # noqa: F401 — SyntheticCheckConfig
import app.models.synthetic_check_result  # noqa: F401 — SyntheticCheckResultRecord

from app.config import get_settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def get_url() -> str:
    """Get database URL from application settings."""
    return get_settings().database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just a URL and not an Engine.
    Calls to context.execute() emit the given string to the script output.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates an Engine and associates a connection with the context.
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
