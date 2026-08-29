"""add media_items

Revision ID: af991c7168e1
Revises: b7c2d9e1f3a4
Create Date: 2026-08-29 11:51:57.349194

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "af991c7168e1"
down_revision: Union[str, Sequence[str], None] = "b7c2d9e1f3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "media_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sqlmodel.sql.sqltypes.AutoString(length=10), nullable=False),
        sa.Column(
            "title", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False
        ),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("season", sa.Integer(), nullable=True),
        sa.Column("episode", sa.Integer(), nullable=True),
        sa.Column(
            "path", sqlmodel.sql.sqltypes.AutoString(length=1024), nullable=False
        ),
        sa.Column(
            "source_name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False
        ),
        sa.Column("sync_log_id", sa.UUID(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        sa.Column(
            "dedupe_key", sqlmodel.sql.sqltypes.AutoString(length=300), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["sync_log_id"], ["sync_logs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key"),
    )
    op.create_index(
        op.f("ix_media_items_first_seen_at"),
        "media_items",
        ["first_seen_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_media_items_source_name"), "media_items", ["source_name"], unique=False
    )
    op.create_index(
        op.f("ix_media_items_title"), "media_items", ["title"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_media_items_title"), table_name="media_items")
    op.drop_index(op.f("ix_media_items_source_name"), table_name="media_items")
    op.drop_index(op.f("ix_media_items_first_seen_at"), table_name="media_items")
    op.drop_table("media_items")
